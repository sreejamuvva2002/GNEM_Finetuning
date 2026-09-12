"""Run original Phase 2/3 gates in isolation; verify unchanged retained source/split."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
records=[]
with tempfile.TemporaryDirectory(prefix='gnem-source-revalidation-') as work:
    dest=Path(work)
    for d in ['finetune','datasets_v3','validation_v3','kb']:
        shutil.copytree(ROOT/d,dest/d,ignore=shutil.ignore_patterns('__pycache__'))
    for f in ['README.md','CLAUDE.md']:shutil.copy2(ROOT/f,dest/f)
    # The generators call git only for read-only context metadata. Keep that
    # metadata tied to the real checkout; all generated artifacts go to dest.
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',GIT_DIR=str(ROOT/'.git'),GIT_WORK_TREE=str(ROOT))
    for phase,script,outputs in [(2,'phase2_clean_records.py',['datasets_v3/canonical_records_v3.jsonl','validation_v3/CLEANING_AUDIT_v3.csv']), (3,'phase3_split_identity.py',['datasets_v3/company_split_groups_v3.csv'])]:
        r=subprocess.run([str(ROOT/'.venv-v3/bin/python'),str(dest/'finetune'/script)],cwd=dest,env=env,capture_output=True,text=True,timeout=60)
        log=r.stdout+r.stderr;(OUT/f'phase{phase}_source.log').write_text(log)
        comparisons={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==hashlib.sha256((dest/p).read_bytes()).hexdigest() for p in outputs}
        records.append({'phase':phase,'exit_code':r.returncode,'byte_identical_outputs':comparisons,'scope':'Existing normalization/split gates; source and company holdout retained by A-002. No amended downstream dataset certification.'})
        print(phase,r.returncode,comparisons,flush=True)
        if r.returncode!=0:print(log[-3000:]);raise SystemExit(r.returncode)
        assert all(comparisons.values())
(OUT/'source_phase_results.json').write_text(json.dumps(records,indent=2)+'\n')
