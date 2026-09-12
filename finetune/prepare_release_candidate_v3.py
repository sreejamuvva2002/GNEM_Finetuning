"""Prepare a reviewable inventory only. Never write TRAINING_RELEASE_A002.json."""
import json,hashlib,datetime
from pathlib import Path
import train_v3 as T
ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'validation_v3/TRAINING_RELEASE_CANDIDATE_A002.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    proposal=ROOT/T.PROPOSED_SCHEDULE
    schedule=json.loads(proposal.read_text())['run_schedule']
    pairs=[(r['variant'],r['seed']) for r in schedule]
    assert len(pairs)==18==len(set(pairs))
    assert all(T.valid_seed(seed) for _,seed in pairs)
    paths=set(T.REQUIRED_RELEASE_INPUTS)|{
      'datasets_v3/EVALUATION_INPUT_MANIFEST_A002_r2.json',
      'finetune/phase17b_build_dev_structured_r2.py','finetune/phase16_build_bd.py',
      'finetune/structured_answer_v3.py','finetune/structured_prompt_v3.py',
      'finetune/final_eval_v3.py','finetune/final_eval_tests.py',
      'finetune/answer_parser_v3.py','finetune/grade_v3.py','finetune/sqlexec_v3.py',
      'validation_v3/resumption/TRAINING_ENVIRONMENT.lock',
      'validation_v3/resumption/TRAINING_LABEL_AUDIT_CURRENT.json',
      'validation_v3/resumption/REHEARSAL_RELOAD_A002.json',
      'results_v3/dev/VERIFIED_BASELINES_A002_r3.json',
      'validation_v3/PRE_TRAINING_GATES_A002.md'}
    d={'status':'CANDIDATE_ONLY_NOT_APPROVED','approved':False,'q42_approval':'pending',
       'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'run_schedule_source':T.PROPOSED_SCHEDULE,'run_schedule_sha256':sha(proposal),
       'run_schedule':schedule,'sha256':{p:sha(ROOT/p) for p in sorted(paths)},
       'limitations':['Cannot satisfy final release gate: approved is false.',
          'Requires genuine Q42 approval evidence and completed gate evidence.',
          'Final evaluation driver and backup destination remain unresolved.',
          'Configured training defaults are not approved final hyperparameters.']}
    DEST.write_text(json.dumps(d,indent=2)+'\n')
    try:T.check_release('B_facts',61,release_path=DEST)
    except RuntimeError as e:assert 'not approved' in str(e)
    else:raise AssertionError('Candidate unexpectedly released training')
    assert not T.RELEASE.exists()
    print('PASS: reviewable candidate written; final release correctly rejected.')
if __name__=='__main__':main()
