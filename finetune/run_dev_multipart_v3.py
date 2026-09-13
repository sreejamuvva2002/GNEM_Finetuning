"""Fixed dev-only unchanged-base baseline for the new multipart diagnostic set."""
import json
from pathlib import Path
from generation_core_v3 import LocalTransformersBackend,generate_records
from prediction_export_v3 import export_predictions,sha
from final_contract_v3 import grade_final_answer
ROOT=Path(__file__).resolve().parent.parent

def main():
    out=ROOT/'results_v3/dev/base_multipart_r1'
    if out.exists():raise RuntimeError('Preserve prior results')
    path=ROOT/'datasets_v3/dev_multipart_r1_v3.jsonl'
    manifest=json.loads((ROOT/'validation_v3/DEV_MULTIPART_R1_MANIFEST.json').read_text())
    assert sha(path)==manifest['dataset_sha256'] and manifest['classification']=='dev'
    items=[json.loads(l) for l in path.read_text().splitlines()]
    # Confirm the scorer accepts executable gold values before model inference.
    for item in items:
        value={}
        for p in item['parts']:
            g=item['gold_value'][p['part_id']]
            value[p['part_id']]=g['rows'][0][0] if p['answer_type']=='scalar' else [r[0] for r in g['rows']]
        assert grade_final_answer(json.dumps(value),item)[0].task_result_correctness==1
    config=json.loads((ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    backend=LocalTransformersBackend(config)
    records=generate_records(items,backend,prompt_config=config,condition='base',seed=None)
    export_predictions(ROOT,out,records,expected_ids=[i['example_id'] for i in items],
        model_kind='base',model_revision=config['model_revision'],
        runtime={**backend.runtime,'effective_prompt_config':config,'input_sha256':sha(path),
                 'runner_sha256':sha(Path(__file__)),'grader_sha256':{n:sha(ROOT/'finetune'/n) for n in
                 ('final_contract_v3.py','answer_parser_v3.py','structured_answer_v3.py')}})
    scores=[]
    for item,record in zip(items,records):
        g,_=grade_final_answer(record['raw_output'],item,record['stopped_at_max_new_tokens'])
        scores.append({'example_id':item['example_id'],'status':g.status,
            'correct':g.task_result_correctness,'strict':g.strict_result_schema_accuracy,'metrics':g.metrics})
    (out/'scores.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in scores))
    summary={'items':len(scores),'correct':sum(x['correct'] for x in scores),
        'strict_correct':sum(x['strict'] for x in scores),'expected_parts':30,
        'predictions_sha256':sha(out/'predictions.jsonl'),'input_sha256':sha(path),
        'limitation':'Recombined existing development components; diagnostic only, no checkpoint selection change.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
