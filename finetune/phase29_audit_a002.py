"""Global pre-training audit; does not fabricate human benchmark approval."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import holdout_v3 as H
import sqlexec_v3 as X
import phase13_build_c_answers as C
from audit_full_field_v3 import main as coverage,load
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'datasets_v3'

def main():
    coverage();reg=H.load_registry()
    pool=load('STRUCTURED_TASK_POOL_v3.jsonl')
    for t in pool:
        for scope in ('train_kb','train_dev_kb','full_kb'):
            r=X.run_sql(t['gold_sql'],scope,db_path=OUT/'gnem_v3.sqlite')
            assert {'columns':list(r.columns),'rows':[list(x) for x in r.rows]}==t[scope+'_gold'],t['task_id']
    for t in pool:
        C.is_eligible(t,H.held_out_values(reg))
    example=next(t for t in pool if t['operation_family']=='filter' and t['join_arity']==0)
    for badsql in ("SELECT county, COUNT(*) FROM companies GROUP/**/BY county", "SELECT * FROM `companies`", "SELECT * FROM companies, services", "WITH x AS (SELECT * FROM companies) SELECT * FROM x"):
        bad=dict(example,gold_sql=badsql)
        try:C.is_eligible(bad,H.held_out_values(reg))
        except C.Gate:pass
        else:raise AssertionError('Stale metadata/unsupported shape accepted: '+badsql)
    inputs=json.loads((OUT/'EVALUATION_INPUT_MANIFEST_A002.json').read_text())
    for name,sha in inputs['sha256'].items():assert H.sha256_file(OUT/name)==sha
    q42=load('probe_42_v3.jsonl'); assert len(q42)==42
    # Human adjudication is a separate gate; generated proposals cannot satisfy it.
    approval=ROOT/'validation_v3/Q42_HUMAN_APPROVAL_A002.json'
    approved=False
    if approval.exists():
        a=json.loads(approval.read_text());approved=a.get('approved') is True and a.get('benchmark_sha256')==H.sha256_file(OUT/'probe_42_v3.jsonl')
    paths=[p for p in OUT.iterdir() if p.is_file() and p.suffix in {'.json','.jsonl','.csv','.sqlite'}]
    manifest={'engineering_checks_passed':True,'q42_human_approval':approved,
        'full_training_released':False,'pool_queries_verified':len(pool)*3,
        'remaining_gates':['Q42 human adjudication and approval','real micro end-to-end evaluation','baseline dev evaluation','training smoke and checkpoint reload'],
        'sha256':{str(p.relative_to(ROOT)):H.sha256_file(p) for p in sorted(paths)},
        'code_sha256':{str(p.relative_to(ROOT)):H.sha256_file(p) for p in sorted((ROOT/'finetune').glob('*.py'))}}
    (ROOT/'validation_v3/GLOBAL_AUDIT_A002.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'PASS: engineering checks, {len(pool)*3} scoped gold executions and mutation rejection. Full training remains gated.')
if __name__=='__main__':main()
