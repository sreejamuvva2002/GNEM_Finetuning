"""Pinned LoRA training with shared audited labels; final runs require release gates."""
import argparse,hashlib,json,math,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
ROOT=Path(__file__).resolve().parent.parent
from training_tokens_v3 import encode_chat,supervised_tokens,MAX_SEQUENCE_LENGTH
MODEL='Qwen/Qwen2.5-14B-Instruct';REVISION='cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8'
FILES={'A_cpt':'train_A_cpt_v3.jsonl','B_facts':'train_B_facts_v3.jsonl','C_answers':'train_C_answers_v3.jsonl',
       'D_sql':'train_D_sql_v3.jsonl','BC':'train_BC_facts_answers_v3.jsonl',
       'BD_controlled':'train_BD_controlled_v3.jsonl','D_repeat_budgetmatched':'train_D_repeat_budgetmatched_v3.jsonl',
       'BD_full':'train_BD_facts_sql_v3.jsonl'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return [json.loads(l) for l in Path(p).read_text().splitlines()]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=FILES,required=True)
    parser.add_argument('--seed',type=int,required=True);parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if not args.smoke:
        release=json.loads((ROOT/'validation_v3/TRAINING_RELEASE_A002.json').read_text())
        if release.get('approved') is not True:raise RuntimeError('Training release is not approved')
        for name,h in release['sha256'].items():
            if sha(ROOT/name)!=h:raise RuntimeError(f'Release input drift: {name}')
    import torch
    import transformers,peft
    from transformers import AutoTokenizer,AutoModelForCausalLM,Trainer,TrainingArguments,set_seed
    from peft import LoraConfig,get_peft_model
    from datasets import Dataset
    assert transformers.__version__=='4.56.2' and peft.__version__=='0.17.1'
    set_seed(args.seed)
    out=ROOT/('validation_v3/smoke_models' if args.smoke else 'adapters_v3')/f'{args.variant}.seed{args.seed}'
    if out.exists() and any(out.iterdir()):raise RuntimeError(f'Refusing to overwrite run: {out}')
    out.mkdir(parents=True)
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
        for start in range(0,len(stream),MAX_SEQUENCE_LENGTH):
            ids=stream[start:start+MAX_SEQUENCE_LENGTH]
            if len(ids)<2:raise RuntimeError('Unsupervisable final CPT fragment')
            encoded.append({'input_ids':ids,'attention_mask':[1]*len(ids),'labels':ids.copy()})
    else:
        for row in rows:
            e=encode_chat(tok,row['messages']);encoded.append(e)
            source_tokens.append({'example_id':row['example_id'],'tokens':len(e['input_ids']),'supervised_tokens':supervised_tokens(e)})
    devrows=read(ROOT/'datasets_v3/dev_fact_v3.jsonl')
    from phase11_build_b_facts import CLOSED_BOOK_SYSTEM
    from phase14_build_d_sql import SQL_SYSTEM
    facts_dev=[encode_chat(tok,r['messages']) for r in devrows]
    queries_dev=read(ROOT/'datasets_v3/dev_structured_v3.jsonl')
    sql_arm=args.variant in {'D_sql','BD_controlled','D_repeat_budgetmatched','BD_full'}
    structured_dev=[]
    for r in queries_dev:
        answer=r['gold_sql'] if sql_arm else ('The companies are: '+ '; '.join(str(v[0]) for v in r['gold_value']['rows'])+'.' if r['gold_value']['rows'] else 'No companies match.')
        messages=[{'role':'system','content':SQL_SYSTEM if sql_arm else CLOSED_BOOK_SYSTEM},
                  {'role':'user','content':r['question']},{'role':'assistant','content':answer}]
        structured_dev.append(encode_chat(tok,messages))
    if args.variant in {'A_cpt','B_facts'}:dev=facts_dev
    elif args.variant in {'C_answers','D_sql','D_repeat_budgetmatched'}:dev=structured_dev
    else:dev=facts_dev+structured_dev
    epochs=4 if args.variant=='A_cpt' else 3
    if args.smoke:
        # Spread selection over the entire recipe: prefix-only sampling misses
        # the C/D component of concatenated factual mixtures.
        train_indices=sorted({round(i*(len(encoded)-1)/7) for i in range(8)})
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
    manifest={'variant':args.variant,'seed':args.seed,'smoke_only':args.smoke,'source_sha256':sha(source),
       'model':MODEL,'revision':REVISION,'trainer_sha256':sha(__file__),
       'smoke_train_indices':train_indices if args.smoke else None,
       'smoke_dev_indices':dev_indices if args.smoke else None,
       'dev_source_sha256':{name:sha(ROOT/'datasets_v3'/name) for name in ('dev_fact_v3.jsonl','dev_structured_v3.jsonl')},
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
