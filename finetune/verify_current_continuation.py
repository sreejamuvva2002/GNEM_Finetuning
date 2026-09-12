"""Read-only source/result checks plus a new current verification snapshot."""
import ast,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    before=json.loads((ROOT/'validation_v3/resumption/CLEANUP_RUNTIME_2026-09-11.json').read_text())
    allowed={'datasets_v3/train_BD_controlled_v3.jsonl','datasets_v3/train_D_repeat_budgetmatched_v3.jsonl','datasets_v3/BD_SAMPLING_MANIFEST_v3.json'}
    preserved=[];changed=[]
    for name,h in before['protected_source_dataset_result_files'].items():
        if sha(ROOT/name)==h:preserved.append(name)
        else:
            assert name in allowed,('Unexpected protected artifact change',name)
            archived=ROOT/'archive/pre_stratified_BD_2026-09-12'/name
            assert sha(archived)==h
            changed.append(name)
    assert set(changed)==allowed
    for p in (ROOT/'finetune').glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    from answer_parser_v3 import grade_answer
    lookup={r['example_id']:r for name in ('dev_fact_v3.jsonl','dev_structured_r2_v3.jsonl') for r in map(json.loads,(ROOT/'datasets_v3'/name).read_text().splitlines())}
    n=0
    for condition in ('base','base_ctx_oracle'):
        path=ROOT/'results_v3/dev'/condition/'protocol_A002_dev_r3/predictions.jsonl'
        for r in map(json.loads,path.read_text().splitlines()):
            g,_=grade_answer(r['raw_output'],lookup[r['example_id']],r['stopped_at_max_new_tokens'])
            assert (g.status,g.task_result_correctness,g.strict_result_schema_accuracy)==(r['status'],r['task_result_correctness'],r['strict_result_schema_accuracy'])
            n+=1
    assert not (ROOT/'validation_v3/TRAINING_RELEASE_A002.json').exists()
    assert not (ROOT/'adapters_v3').exists()
    q42=list(map(json.loads,(ROOT/'datasets_v3/probe_42_v3.jsonl').read_text().splitlines()))
    for r in q42:
        if r['answer_type']=='multi_part':
            assert set(r['gold_value'])==set(r['gold_sql'])=={p['part_id'] for p in r['parts']}
            for p in r['parts']:assert p['target_columns']==r['gold_value'][p['part_id']]['columns']
    paths=list((ROOT/'finetune').glob('*.py'))+[ROOT/'results_v3/dev/VERIFIED_BASELINES_A002_r3.json',ROOT/'validation_v3/resumption/TRAINING_LABEL_AUDIT_CURRENT.json',ROOT/'validation_v3/resumption/REHEARSAL_RELOAD_A002.json',ROOT/'validation_v3/PRE_TRAINING_GATES_A002.md',ROOT/'validation_v3/PROPOSED_RUN_SCHEDULE_A002.json']
    report={'preserved_protected_files':len(preserved),'intentionally_changed_and_archived':changed,'extended_parser_identical_dev_verdicts':n,'q42_multipart_schema_checked':True,'q42_approval':'pending','final_training_runs':0,'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}}
    (ROOT/'validation_v3/resumption/CURRENT_CONTINUATION_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
if __name__=='__main__':main()
