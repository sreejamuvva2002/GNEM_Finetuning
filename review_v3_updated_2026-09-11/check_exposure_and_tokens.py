"""Read-only artifact/mask screen. Historical TRL template is a diagnostic, not a V3 runtime certificate."""
from pathlib import Path
import collections, copy, hashlib, importlib.util, json, re, sqlite3, sys
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'finetune'))
import holdout_v3 as H, phase13_build_c_answers as C, eval_stats_v3 as S, grade_v3 as G
from phase10_build_a_cpt import load_real_tokenizer
from phase16_build_bd import completion_and_total_tokens
from sqlexec_v3 import run_sql
reg=H.load_registry(); tok,_=load_real_tokenizer()
template=(ROOT/'review_training_2026-09-11/library_sources/qwen2_5_training.jinja').read_text()
def jl(p): return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
results={}
for path in sorted((ROOT/'datasets_v3').glob('train_*.jsonl')):
    rows=jl(path); texts=[]; lens=[]; diffs=[]; target_tokens=0; zero1024=0; renderchanges=0
    for r in rows:
        if 'messages' not in r:
            texts.append(r['text']); lens.append(len(tok(r['text'],add_special_tokens=False)['input_ids'])); continue
        msgs=r['messages']; texts.extend(m['content'] for m in msgs)
        masked=tok.apply_chat_template(msgs,chat_template=template,tokenize=True,return_dict=True,return_assistant_tokens_mask=True)
        ids=masked['input_ids']; masks=masked['assistant_masks']
        plain=tok.apply_chat_template(msgs,tokenize=True,return_dict=False)
        renderchanges+=ids!=plain
        n=sum(masks[1:]); target_tokens+=n; lens.append(len(ids)); diffs.append(n-completion_and_total_tokens(tok,msgs)[0]); zero1024+=not any(masks[1:1024])
    scan=H.scan_strings(texts,reg)
    results[path.name]={'examples':len(rows),'strings_scanned':len(texts),'heldout_literal_exposures':scan['total_exposures'],'length_min':min(lens),'length_max':max(lens),'over_1024':sum(n>1024 for n in lens),'over_2048':sum(n>2048 for n in lens),'historical_template_zero_supervision_at_1024':zero1024,'historical_template_supervised_tokens':target_tokens,'mask_minus_length_difference_counts':dict(collections.Counter(diffs)),'historical_template_changes_tokens':renderchanges}
    print(path.name,results[path.name],flush=True)
pool=jl(ROOT/'datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl'); t=copy.deepcopy(next(t for t in pool if 'GROUP BY' in t['gold_sql'] and not any(set(t['values_used'])&set(v) for v in H.held_out_values(reg).values())))
t['operation_family']='filter'; t['required_constructs']=[]
findings={'stale_metadata_groupby_accepted':C.is_eligible(t,H.held_out_values(reg))[0],'effect_size_constant_positive':S.effect_size([1,1,1])}
item={'answer_type':'scalar','target_columns':['n']}
findings['alias_only_grade']=G.grade_structured(item,'SELECT COUNT(DISTINCT company) AS company_count FROM companies','SELECT COUNT(DISTINCT company) AS n FROM companies','train_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite').__dict__
manifest=json.loads((ROOT/'datasets_v3/BD_SAMPLING_MANIFEST_v3.json').read_text()); D=jl(ROOT/'datasets_v3/train_D_sql_v3.jsonl'); repeats=jl(ROOT/'datasets_v3/train_D_repeat_budgetmatched_v3.jsonl'); source={x['example_id']:x for x in D}
mapping=manifest['d_repeat_budgetmatched']['source_task_id_by_example_id']
findings['repeat_mapping_mismatches']=sum(mapping[x['example_id']]!=x['task_id'] for x in repeats)
b=jl(ROOT/'datasets_v3/train_B_facts_v3.jsonl'); ctrl=jl(ROOT/'datasets_v3/train_BD_controlled_v3.jsonl')
findings['controlled_missing_B_companies']=sorted({r['company'] for r in b}-{r['company'] for r in ctrl if 'company' in r})
# Independently verify every retained child term against canonical semicolon membership.
canon=jl(ROOT/'datasets_v3/canonical_records_v3.jsonl'); sentinels={'Not specified','Not applicable','None identified after search'}
with sqlite3.connect(f'file:{ROOT}/datasets_v3/gnem_v3.sqlite?mode=ro',uri=True) as con:
    child_checks={}
    for table,col in [('processes','process'),('services','service'),('certifications','standard_family')]:
        expected={(r['row_id'],r['company'],v.strip()) for r in canon for v in r[table].split(';') if v.strip() and v.strip() not in sentinels}
        actual=set(con.execute(f'SELECT row_id,company,{col} FROM {table}'))
        child_checks[table]={'expected':len(expected),'actual':len(actual),'missing':len(expected-actual),'extra':len(actual-expected)}
findings['child_roundtrip']=child_checks
findings['environment']={m:importlib.util.find_spec(m) is not None for m in ['torch','openpyxl','pandas','pytest','transformers','trl','peft']}
(OUT/'exposure_and_token_results.json').write_text(json.dumps({'scope':'Current V3 files, tokenizer pinned; labels reconstructed with historical TRL template, NOT an implemented V3 trainer','artifacts':results,'findings':findings},indent=2,default=str)+'\n')
print(json.dumps(findings,indent=2,default=str))
