"""Fixed synthetic GPU rehearsal; no option accepts benchmark inputs."""
import json
from pathlib import Path
import generation_core_v3 as C
import prediction_export_v3 as E
import final_eval_v3 as F

ROOT=Path(__file__).resolve().parents[2]

def main():
    out=ROOT/'validation_v3/generation_rehearsal_2026-09-15/base'
    if out.exists():raise RuntimeError('Rehearsal already exists; preserve its evidence')
    config=json.loads((ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    config['decoding']={'do_sample':False,'max_new_tokens':64}
    items=[{'example_id':'synthetic_scalar','question':'For this synthetic test, return the number 7.','answer_type':'scalar'},
           {'example_id':'synthetic_set','question':'For this synthetic test, return the values alpha and beta.','answer_type':'set'}]
    backend=C.LocalTransformersBackend(config)
    first=C.generate_records(items,backend,prompt_config=config,condition='synthetic_base',seed=None)
    second=C.generate_records(items,backend,prompt_config=config,condition='synthetic_base',seed=None)
    repeat=all(a['output_token_ids']==b['output_token_ids'] for a,b in zip(first,second))
    runtime={**backend.runtime,'effective_prompt_config':config,
             'packages':{name:__import__('importlib.metadata',fromlist=['version']).version(name)
                         for name in ('torch','transformers','peft','accelerate')},
             'runner_sha256':E.sha(Path(__file__)),
             'code_sha256':{name:E.sha(ROOT/'finetune'/name) for name in
                ('generation_core_v3.py','prediction_export_v3.py','rehearse_generation_v3.py')}}
    registration=E.export_predictions(ROOT,out,first,expected_ids=[i['example_id'] for i in items],
        model_kind='base',model_revision=config['model_revision'],runtime=runtime)
    F.validate_prediction_identities(registration,out/'predictions.jsonl',F.load(out/'predictions.jsonl'))
    report={'synthetic_only':True,'items':len(items),'repeated_token_ids_equal':repeat,
            'identity_validation_passed':True,'runtime_sha256':E.sha(out/'runtime.json'),
            'predictions_sha256':E.sha(out/'predictions.jsonl'),
            'training_performed':False,'protected_inputs_read':False,
            'limitation':'Same-loaded-model repeat, not reload reproducibility or model competence.'}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    if not repeat:raise RuntimeError('Repeated greedy generations differ')

if __name__=='__main__':main()
