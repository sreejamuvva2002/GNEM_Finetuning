"""Pinned LoRA training with shared audited labels; final runs require release gates."""
import argparse,hashlib,json,math,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
ROOT=Path(__file__).resolve().parent.parent
from training_tokens_v3 import encode_chat,supervised_tokens,MAX_SEQUENCE_LENGTH,pack_cpt_stream
MODEL='Qwen/Qwen2.5-14B-Instruct';REVISION='cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8'
# Checkpoint-selection development inputs. DEV_STRUCTURED replaces the tautological
# dev_structured_v3.jsonl, whose gold was quoted inside its own question.
DEV_FACT='datasets_v3/dev_fact_v3.jsonl'
DEV_STRUCTURED='datasets_v3/dev_structured_r2_v3.jsonl'
DEV_STRUCTURED_LEGACY='datasets_v3/dev_structured_v3.jsonl'
FILES={'A_cpt':'train_A_cpt_v3.jsonl','B_facts':'train_B_facts_v3.jsonl','C_answers':'train_C_answers_v3.jsonl',
       'D_sql':'train_D_sql_v3.jsonl','BC':'train_BC_facts_answers_v3.jsonl',
       'BD_controlled':'train_BD_controlled_v3.jsonl','D_repeat_budgetmatched':'train_D_repeat_budgetmatched_v3.jsonl',
       'BD_full':'train_BD_facts_sql_v3.jsonl'}
RELEASE=ROOT/'validation_v3/TRAINING_RELEASE_A002.json'
# Claim status per PROVENANCE_v3.md Phase 0: five primary arms at >=3 seeds,
# three diagnostic arms at one seed, 18 runs total.
PRIMARY_ARMS=('B_facts','C_answers','D_sql','BD_controlled','D_repeat_budgetmatched')
DIAGNOSTIC_ARMS=('A_cpt','BC','BD_full')
MINIMUM_SEEDS={**{a:3 for a in PRIMARY_ARMS},**{a:1 for a in DIAGNOSTIC_ARMS}}
TOTAL_RUNS=18
# The pre-registered schedule artifact. An approved release must name it and pin its
# hash, and its pairs must agree EXACTLY -- otherwise a release could satisfy the
# count and minimum-seed checks while quietly running seeds the proposal never
# declared, which is the post-hoc seed choice the pre-registration exists to prevent.
PROPOSED_SCHEDULE='validation_v3/PROPOSED_RUN_SCHEDULE_A002.json'
# numpy's legacy seeding accepts [0, 2**32); transformers.set_seed feeds it directly.
SEED_MIN,SEED_MAX=0,2**32-1
# Every input whose bytes can change a final run. An approved release must pin
# ALL of them: an empty or partial sha256 map previously satisfied the gate
# vacuously, which is the opposite of a freeze.
REQUIRED_RELEASE_INPUTS=tuple(sorted(
    ['datasets_v3/'+f for f in FILES.values()]+[
    'datasets_v3/dev_fact_v3.jsonl','datasets_v3/dev_structured_r2_v3.jsonl',
    'datasets_v3/PROMPT_TEMPLATES_A002.json','datasets_v3/HOLDOUT_REGISTRY_A002.json',
    'datasets_v3/canonical_records_v3.jsonl','datasets_v3/company_split_groups_v3.csv',
    'datasets_v3/gnem_v3.sqlite','kb/GNEM_Final_Combined_Dataset.xlsx',
    'finetune/templates/qwen_a002.jinja','finetune/training_tokens_v3.py',
    'finetune/train_v3.py','finetune/phase13_build_c_answers.py',
    'finetune/phase14_build_d_sql.py','finetune/phase11_build_b_facts.py']))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return [json.loads(l) for l in Path(p).read_text().splitlines()]

def valid_seed(seed):
    # bool is a subclass of int; True would silently seed as 1.
    return (isinstance(seed,int) and not isinstance(seed,bool)
            and SEED_MIN<=seed<=SEED_MAX)

def check_release(variant,seed,release_path=None):
    """Fail closed. A release must be approved, complete, undrifted, and must
    pre-declare the exact (variant, seed) pair being run.

    `release_path` is injectable so the regression suite can exercise rejection
    paths without ever writing an approved release into the repository."""
    release_path=Path(release_path or RELEASE)
    if not release_path.exists():
        raise RuntimeError(f'No training release at {release_path}; final training is not released')
    release=json.loads(release_path.read_text())
    if release.get('approved') is not True:
        raise RuntimeError('Training release is not approved')
    if release.get('q42_approval')!='approved':
        raise RuntimeError('Q42 adjudication is not approved; final training is gated on it')
    pinned=release.get('sha256')
    if not isinstance(pinned,dict) or not pinned:
        raise RuntimeError('Release pins no input hashes; an empty map is not a freeze')
    missing=[n for n in REQUIRED_RELEASE_INPUTS if n not in pinned]
    if missing:
        raise RuntimeError(f'Release does not pin required inputs: {missing}')
    for name,digest in sorted(pinned.items()):
        path=ROOT/name
        if not path.exists():
            raise RuntimeError(f'Release pins a missing input: {name}')
        if sha(path)!=digest:
            raise RuntimeError(f'Release input drift: {name}')
    schedule=release.get('run_schedule')
    if not isinstance(schedule,list) or not schedule:
        raise RuntimeError('Release declares no run_schedule; seeds must be pre-registered')
    if not all(isinstance(e,dict) for e in schedule):
        raise RuntimeError('run_schedule entries must be objects')
    pairs=[(entry.get('variant'),entry.get('seed')) for entry in schedule]
    if len(pairs)!=len(set(pairs)):
        raise RuntimeError('run_schedule contains duplicate (variant, seed) pairs')
    unknown=sorted({v for v,_ in pairs}-set(FILES))
    if unknown:
        raise RuntimeError(f'run_schedule names unknown variants: {unknown}')
    bad=[(v,sd) for v,sd in pairs if not valid_seed(sd)]
    if bad:
        raise RuntimeError(f'run_schedule contains invalid seeds (need int in '
                           f'[{SEED_MIN}, {SEED_MAX}]): {bad}')
    if not valid_seed(seed):
        raise RuntimeError(f'--seed {seed!r} is not an integer in [{SEED_MIN}, {SEED_MAX}]')
    # The release must agree exactly with the pre-registered proposal.
    source=release.get('run_schedule_source')
    if source!=PROPOSED_SCHEDULE:
        raise RuntimeError(f'Release must set run_schedule_source to {PROPOSED_SCHEDULE}')
    proposal_path=ROOT/source
    if not proposal_path.exists():
        raise RuntimeError(f'Pre-registered schedule is missing: {source}')
    if release.get('run_schedule_sha256')!=sha(proposal_path):
        raise RuntimeError('run_schedule_sha256 does not match the pre-registered schedule')
    proposed=json.loads(proposal_path.read_text()).get('run_schedule')
    if not isinstance(proposed,list) or not proposed:
        raise RuntimeError('Pre-registered schedule declares no runs')
    proposed_pairs={(e.get('variant'),e.get('seed')) for e in proposed}
    if proposed_pairs!=set(pairs):
        added=sorted(set(pairs)-proposed_pairs); dropped=sorted(proposed_pairs-set(pairs))
        raise RuntimeError(f'run_schedule disagrees with the pre-registered schedule; '
                           f'added={added} dropped={dropped}')
    for arm,minimum in sorted(MINIMUM_SEEDS.items()):
        actual=sum(1 for v,_ in pairs if v==arm)
        if actual<minimum:
            raise RuntimeError(f'run_schedule gives {arm} {actual} seed(s); claim status requires >={minimum}')
    if len(pairs)!=TOTAL_RUNS:
        raise RuntimeError(f'run_schedule declares {len(pairs)} runs; the confirmed budget is {TOTAL_RUNS}')
    if (variant,seed) not in pairs:
        raise RuntimeError(f'({variant}, seed {seed}) is not in the approved run_schedule')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=FILES,required=True)
    parser.add_argument('--seed',type=int,required=True);parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--rehearsal',action='store_true',help='Small diagnostic run with final accumulation, epoch saving and best-checkpoint reload')
    args=parser.parse_args()
    if args.smoke and args.rehearsal:raise ValueError('Choose smoke or rehearsal')
    if not args.smoke and not args.rehearsal:
        check_release(args.variant,args.seed)
    import torch
    import transformers,peft
    from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,set_seed
    from peft import LoraConfig,get_peft_model
    from datasets import Dataset
    assert transformers.__version__=='4.56.2' and peft.__version__=='0.17.1'
    set_seed(args.seed)
    out=ROOT/('validation_v3/rehearsal_models' if args.rehearsal else 'validation_v3/smoke_models' if args.smoke else 'adapters_v3')/f'{args.variant}.seed{args.seed}'
    if out.exists() and any(out.iterdir()):raise RuntimeError(f'Refusing to overwrite run: {out}')
    out.mkdir(parents=True,exist_ok=True)
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
    tok.pad_token=tok.eos_token
    source=ROOT/'datasets_v3'/FILES[args.variant];rows=read(source)
    encoded=[];source_tokens=[]
    if args.variant=='A_cpt':
        stream=[]
        for row in rows:
            ids=tok(row['text'],add_special_tokens=False)['input_ids']+[tok.eos_token_id]
            source_tokens.append({'example_id':row['example_id'],'tokens':len(ids)})
            stream.extend(ids)
        encoded=pack_cpt_stream(stream)
    else:
        for row in rows:
            e=encode_chat(tok,row['messages']);encoded.append(e)
            source_tokens.append({'example_id':row['example_id'],'tokens':len(e['input_ids']),'supervised_tokens':supervised_tokens(e)})
    devrows=read(ROOT/'datasets_v3/dev_fact_v3.jsonl')
    from phase11_build_b_facts import CLOSED_BOOK_SYSTEM
    from phase14_build_d_sql import SQL_SYSTEM
    from phase13_build_c_answers import render_answer
    facts_dev=[encode_chat(tok,r['messages']) for r in devrows]
    # dev_structured_v3.jsonl quoted its complete gold answer inside every question,
    # so selecting on its loss rewarded echoing the prompt. It is retained as a
    # historical artifact; DEV_STRUCTURED is the non-tautological replacement.
    queries_dev=read(ROOT/DEV_STRUCTURED)
    sql_arm=args.variant in {'D_sql','BD_controlled','D_repeat_budgetmatched','BD_full'}
    structured_dev=[]
    for r in queries_dev:
        # Reuse Phase 13's frozen renderer so the development target is formatted
        # exactly like the C training targets -- including counts, which the old
        # inline rendering turned into "The companies are: 3.".
        answer=r['gold_sql'] if sql_arm else render_answer(
            {'answer_type':r['answer_type'],'train_kb_gold':r['gold_value'],
             'task_id':r['example_id']})
        messages=[{'role':'system','content':SQL_SYSTEM if sql_arm else CLOSED_BOOK_SYSTEM},
                  {'role':'user','content':r['question']},{'role':'assistant','content':answer}]
        structured_dev.append(encode_chat(tok,messages))
    if args.variant in {'A_cpt','B_facts'}:dev=facts_dev
    elif args.variant in {'C_answers','D_sql','D_repeat_budgetmatched'}:dev=structured_dev
    else:dev=facts_dev+structured_dev
    epochs=4 if args.variant=='A_cpt' else 3
    if args.smoke or args.rehearsal:
        # Spread selection over the entire recipe: prefix-only sampling misses
        # the C/D component of concatenated factual mixtures.
        sample_count=16 if args.rehearsal else 8
        train_indices=sorted({round(i*(len(encoded)-1)/(sample_count-1)) for i in range(sample_count)})
        dev_indices=sorted({round(i*(len(dev)-1)/3) for i in range(4)})
        encoded=[encoded[i] for i in train_indices]
        dev=[dev[i] for i in dev_indices]
    def collate(batch):
        size=max(len(r['input_ids']) for r in batch)
        return {key:torch.tensor([r[key]+[(-100 if key=='labels' else 0 if key=='attention_mask' else tok.pad_token_id)]*(size-len(r[key])) for r in batch],dtype=torch.long) for key in ('input_ids','attention_mask','labels')}
    model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,local_files_only=True,
        torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
    model.config.use_cache=False
    model=get_peft_model(model,LoraConfig(r=32,lora_alpha=64,lora_dropout=.05,bias='none',task_type='CAUSAL_LM',
        target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']))
    model.enable_input_require_grads()
    trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert trainable>0
    config=TrainingArguments(output_dir=str(out),per_device_train_batch_size=1,per_device_eval_batch_size=1,
        gradient_accumulation_steps=1 if args.smoke else 8,learning_rate=1e-4,num_train_epochs=epochs,
        max_steps=2 if args.smoke else -1,bf16=True,gradient_checkpointing=True,
        gradient_checkpointing_kwargs={'use_reentrant':False},optim='paged_adamw_8bit',
        lr_scheduler_type='cosine',warmup_ratio=.03,logging_steps=1 if args.smoke else 10,
        eval_strategy='steps' if args.smoke else 'epoch',eval_steps=2 if args.smoke else None,
        save_strategy='steps' if args.smoke else 'epoch',save_steps=2 if args.smoke else 500,
        save_total_limit=None,load_best_model_at_end=True,metric_for_best_model='eval_loss',
        greater_is_better=False,report_to=[],seed=args.seed,data_seed=args.seed,
        remove_unused_columns=False,dataloader_num_workers=0)
    manifest={'variant':args.variant,'seed':args.seed,'smoke_only':args.smoke,'rehearsal_only':args.rehearsal,'source_sha256':sha(source),
       'model':MODEL,'revision':REVISION,'trainer_sha256':sha(__file__),
       'smoke_train_indices':train_indices if (args.smoke or args.rehearsal) else None,
       'smoke_dev_indices':dev_indices if (args.smoke or args.rehearsal) else None,
       'dev_source_sha256':{name:sha(ROOT/name) for name in (DEV_FACT,DEV_STRUCTURED)},
       'dev_structured_superseded':{DEV_STRUCTURED_LEGACY:sha(ROOT/DEV_STRUCTURED_LEGACY),
           'reason':'gold answer quoted inside every question; unusable for selection'},
       'trainable_parameters':trainable,'training_rows':len(encoded),
       'supervised_tokens_per_pass':sum(supervised_tokens(e) for e in encoded),
       'source_tokens':source_tokens,'configuration':config.to_dict(),
       'preprocessor_sha256':sha(ROOT/'finetune/training_tokens_v3.py'),
       'template_sha256':sha(ROOT/'finetune/templates/qwen_a002.jinja'),
       'selection':'minimum development assistant-token loss across epoch checkpoints; no test/Q42 access'}
    (out/'RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2,default=str)+'\n')
    trainer=Trainer(model=model,args=config,train_dataset=Dataset.from_list(encoded),
                    eval_dataset=Dataset.from_list(dev),data_collator=collate,processing_class=tok)
    result=trainer.train()
    trainer.save_model(str(out/'selected_adapter'));tok.save_pretrained(out/'selected_adapter')
    metrics=dict(result.metrics);metrics['eval']=trainer.evaluate();metrics['global_step']=trainer.state.global_step
    metrics['best_model_checkpoint']=trainer.state.best_model_checkpoint
    metrics['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated()
    (out/'METRICS.json').write_text(json.dumps(metrics,indent=2)+'\n');trainer.save_state()
    print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
