"""Run all eight two-step pipeline smoke tests; never launches final training."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
variants=['A_cpt','B_facts','C_answers','D_sql','BC','BD_controlled','D_repeat_budgetmatched','BD_full']
results={}
for variant in variants:
    output=ROOT/'validation_v3/smoke_models'/f'{variant}.seed61'
    log=ROOT/'validation_v3/resumption'/f'smoke_{variant}_seed61.log'
    if not (output/'METRICS.json').exists():
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f'Incomplete run retained at {output}; inspect before retry')
        with log.open('w') as stream:
            result=subprocess.run([sys.executable,str(ROOT/'finetune/train_v3.py'),'--variant',variant,'--seed','61','--smoke'],stdout=stream,stderr=subprocess.STDOUT)
        if result.returncode:
            print(log.read_text()[-4000:],flush=True);raise SystemExit(result.returncode)
    metrics=json.loads((output/'METRICS.json').read_text());assert metrics['global_step']==2
    results[variant]=metrics
    print(variant,'PASS',metrics['train_loss'],metrics['eval']['eval_loss'],flush=True)
(ROOT/'validation_v3/resumption/SMOKE_TRAINING_RESULTS_A002.json').write_text(json.dumps(results,indent=2)+'\n')
