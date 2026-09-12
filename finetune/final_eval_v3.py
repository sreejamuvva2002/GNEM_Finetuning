"""Phase-40-only offline grading of frozen model outputs.

No inference, no implicit unsealing. CLI requires an independently approved
Phase-40 release pinning every file BEFORE reading protected JSONL contents.
Pure grading functions are exercised on synthetic data without a release.
"""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import answer_parser_v3 as A
import grade_v3 as G
import sqlexec_v3 as X
import eval_records_v3 as R
import eval_verify_v3 as V
import eval_stats_v3 as S
from structured_prompt_v3 import output_instruction
ROOT=Path(__file__).resolve().parent.parent
RELEASE=ROOT/'validation_v3/PHASE40_RELEASE_A002.json'
DEPENDENCIES=('finetune/final_eval_v3.py','finetune/answer_parser_v3.py',
 'finetune/structured_answer_v3.py','finetune/structured_prompt_v3.py',
 'finetune/grade_v3.py','finetune/sqlexec_v3.py','finetune/eval_records_v3.py',
 'finetune/eval_verify_v3.py','finetune/eval_stats_v3.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return list(map(json.loads,Path(p).read_text().splitlines()))
def authorize(release,inputs,predictions,db):
    """Validate identities before callers parse protected contents."""
    if release.get('approved') is not True or release.get('phase')!=40:
        raise RuntimeError('Explicit approved Phase 40 release required')
    pins=release.get('sha256',{})
    for path in [inputs,predictions,db]+[ROOT/p for p in DEPENDENCIES]:
        path=Path(path).resolve()
        try:name=str(path.relative_to(ROOT))
        except ValueError:raise RuntimeError('Artifacts must be inside the repository')
        if name not in pins or sha(path)!=pins[name]:raise RuntimeError('Unpinned or drifted input: '+name)
    name=str(Path(inputs).resolve().relative_to(ROOT))
    if release.get('classification',{}).get(name)!='sealed_inputs':
        raise RuntimeError('Input not classified as protected by release')
    approval=ROOT/'validation_v3/Q42_HUMAN_APPROVAL_A002.json'
    benchmark=ROOT/'datasets_v3/probe_42_v3.jsonl'
    for p in (approval,benchmark):
        if not p.is_file() or pins.get(str(p.relative_to(ROOT)))!=sha(p):
            raise RuntimeError('Missing or unpinned Q42 approval evidence')
    a=json.loads(approval.read_text())
    if a.get('approved') is not True or a.get('benchmark_sha256')!=sha(benchmark):
        raise RuntimeError('Q42 approval is absent or stale')

def grade_run(items,predictions,*,condition,seed,mode,db,scope):
    if mode not in ('memory','sql'):raise ValueError('Explicit memory or sql mode required')
    ids=[t['example_id'] for t in items];pids=[p['example_id'] for p in predictions]
    if not items or len(ids)!=len(set(ids)) or len(pids)!=len(set(pids)) or set(ids)!=set(pids):
        raise ValueError('Require every expected ID exactly once; missing outputs must be explicit records')
    byid={p['example_id']:p for p in predictions};records=[];telemetry=[]
    digest=sha(__file__)
    for item in items:
        item_scope=item.get('scope',scope)
        if item_scope not in ('train_kb','train_dev_kb','full_kb'):raise ValueError('Invalid declared scope')
        p=byid[item['example_id']]
        if p['condition']!=condition or p['seed']!=seed or p['question']!=item['question']:
            raise ValueError('Prediction condition, seed or question mismatch')
        if not isinstance(p['prompt_hash'],str) or len(p['prompt_hash'])!=64:raise ValueError('Missing prompt identity')
        text=p['raw_output'];truncated=p.get('stopped_at_max_new_tokens',False)
        # Dataset-insufficiency answers have no executable SQL gold.
        if mode=='sql' and item.get('gold_sql') is not None:
            g=G.grade_structured(item,text,item['gold_sql'],item_scope,db_path=db,stopped_at_max_new_tokens=truncated);parsed=text
        else:g,parsed=A.grade_answer(text,item,truncated)
        execution=None
        if mode=='sql' and item.get('gold_sql') is not None and g.status in ('correct','incorrect'):
            statements=G.split_top_level_statements(text) if item['answer_type']=='multi_part' else [text]
            if item['answer_type']=='multi_part':statements=statements[:len(item['parts'])]
            execution=[]
            for statement in statements:
                result=X.run_sql(statement,item_scope,db_path=db)
                execution.append({'columns':list(result.columns),'rows':[list(r) for r in result.rows]})
        record=R.EvalRecord(example_id=item['example_id'],family=item['family'],condition=condition,
            question=item['question'],raw_output=text,parsed_output=json.dumps(parsed,ensure_ascii=False),
            generated_sql=text if mode=='sql' and item.get('gold_sql') is not None else None,
            execution_result=execution,gold=item['gold_value'],answer_type=item['answer_type'],
            target_columns=item.get('target_columns'),task_result_correctness=g.task_result_correctness,
            strict_result_schema_accuracy=g.strict_result_schema_accuracy,status=g.status,
            error_type=None if g.status=='correct' else g.status,error_detail=g.detail,
            prompt_hash=p['prompt_hash'],adapter_hash=p.get('adapter_hash'),seed=seed,
            grader_version='final_eval_A002.1',grader_sha256=digest,parts=tuple(item['parts']) if item.get('parts') is not None else None)
        records.append(record)
        no_match=(item['answer_type']=='set' and (item['gold_value']==[] or isinstance(item['gold_value'],dict) and item['gold_value'].get('rows')==[]))
        telemetry.append({'example_id':item['example_id'],'metrics':g.metrics,
                          'scope':item_scope,'no_match':no_match,'valid_no_match_answer':bool(no_match and g.task_result_correctness==1),
                          'expected_output_contract':output_instruction(item) if mode=='memory' else 'SQL result contract',
                          'primary_eligible_proposal':item.get('primary_eligible_proposal')})
    verify=V.verify(records,expected_count=len(items),grader_sha256=digest)
    # Diagnostic-only Q42 proposals never silently become primary evidence.
    slices=defaultdict(list)
    for item,r in zip(items,records):
        slices[item['family']].append(r.task_result_correctness)
    summary={'condition':condition,'seed':seed,'mode':mode,'verification':verify,
             'n':len(records),'correct':sum(r.status=='correct' for r in records),
             'statuses':dict(Counter(r.status for r in records)),
             'families':{k:{'n':len(v),'accuracy':S.mean(v)} for k,v in slices.items()},
             'no_match_n':sum(t['no_match'] for t in telemetry),
             'valid_no_match_n':sum(t['valid_no_match_answer'] for t in telemetry),
             'interpretation':'All-item descriptive scores; primary Q42 inclusion requires separately approved adjudication.'}
    return records,telemetry,summary

def summarize_independent_runs(runs, *, deterministic=False):
    """One score per independent seed; reject duplicate seeds or changed IDs.
    No pooled-item pseudo-replication or significance claim is made here.
    """
    if not runs:raise ValueError('No runs')
    seen=set();expected=None;condition=None;scores={}
    for records in runs:
        if not records:raise ValueError('Empty run')
        seeds={r.seed for r in records};conditions={r.condition for r in records}
        if len(seeds)!=1 or len(conditions)!=1:raise ValueError('Mixed run identities')
        seed=next(iter(seeds));current=next(iter(conditions))
        if seed in seen:raise ValueError('Duplicate independent seed')
        if not deterministic and (type(seed) is not int):raise ValueError('Independent training seed required')
        if condition is not None and current!=condition:raise ValueError('Mixed conditions')
        condition=current;seen.add(seed)
        ids=[r.example_id for r in records]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate item')
        if expected is not None and set(ids)!=expected:raise ValueError('Different item sets across seeds')
        expected=set(ids);scores[str(seed)]=S.mean([r.task_result_correctness for r in records])
    return {'condition':condition,'per_seed':scores,'summary':S.mean_sd(scores.values(),deterministic=deterministic),
            'items_per_seed':len(expected),'note':'Descriptive independent-run summary; paired contrasts and multiplicity require the frozen analysis plan.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--predictions',required=True)
    p.add_argument('--condition',required=True);p.add_argument('--seed',type=int)
    p.add_argument('--mode',choices=['memory','sql'],required=True);p.add_argument('--unseal',action='store_true')
    p.add_argument('--out',required=True);a=p.parse_args()
    if not a.unseal or not RELEASE.exists():raise RuntimeError('Phase 40 remains sealed')
    inputs=(ROOT/a.inputs).resolve();pred=(ROOT/a.predictions).resolve();db=ROOT/'datasets_v3/gnem_v3.sqlite'
    release=json.loads(RELEASE.read_text());authorize(release,inputs,pred,db)
    run={'condition':a.condition,'seed':a.seed,'mode':a.mode,'predictions':str(pred.relative_to(ROOT))}
    if run not in release.get('runs',[]):raise RuntimeError('Run not listed in approved evaluation schedule')
    out=(ROOT/a.out).resolve()
    if not out.is_relative_to(ROOT/'results_v3/test'):raise RuntimeError('Final outputs belong under results_v3/test')
    records,telemetry,summary=grade_run(load(inputs),load(pred),condition=a.condition,seed=a.seed,mode=a.mode,db=db,scope='full_kb')
    out.mkdir(parents=True,exist_ok=False)
    (out/'records.jsonl').write_text(''.join(json.dumps(r.to_dict(),ensure_ascii=False)+'\n' for r in records))
    (out/'telemetry.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in telemetry))
    summary['release_sha256']=sha(RELEASE);summary['input_sha256']=sha(inputs);summary['prediction_sha256']=sha(pred)
    summary['dependencies']={n:sha(ROOT/n) for n in DEPENDENCIES}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
if __name__=='__main__':main()
