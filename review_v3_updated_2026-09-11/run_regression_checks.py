from pathlib import Path
import shutil, subprocess, json, os
root=Path('/home/sm11926/GNEM_Finetuning'); out=root/'review_v3_updated_2026-09-11'
copy=Path('/tmp/gnem_v3_updated_review_worktree'); copy.mkdir(exist_ok=True)
for name in ('finetune','datasets_v3','validation_v3','kb'):
    shutil.copytree(root/name,copy/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ('README.md','CLAUDE.md','PROVENANCE_v3.md'): shutil.copy2(root/name,copy/name)
checks=[('phase5_fault_tests.py',[]),('phase6_fault_tests.py',[]),('phase7_grader_tests.py',[]),('phase8_eval_stack_tests.py',[]),('phase12_fault_tests.py',[]),('phase9_fault_tests.py',[]),('phase9_independent_recomputation.py',[]),('phase9_freeze_holdouts.py',['--check'])]
summary=[]; env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for file,args in checks:
    r=subprocess.run([str(root/'.venv-v3/bin/python'),str(copy/'finetune'/file),*args],cwd=copy,env=env,capture_output=True,text=True,timeout=90)
    log=r.stdout+r.stderr; (out/(file.removesuffix('.py')+'.log')).write_text(log)
    summary.append({'script':file,'args':args,'exit_code':r.returncode,'last_lines':log.splitlines()[-5:]})
    print(file,r.returncode, '\n'.join(log.splitlines()[-3:]),flush=True)
(out/'check_results.json').write_text(json.dumps(summary,indent=2)+'\n')
