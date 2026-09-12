"""Verify and report only the four registered development baseline artifacts."""
import hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'finetune'))
import eval_records_v3 as R
import eval_verify_v3 as V

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    report={}
    for condition in ('base','base_ctx_oracle','base_sql','base_sql_5shot'):
        directory=ROOT/'results_v3/dev'/condition/'protocol_A002'
        metadata=json.loads((directory/'manifest.json').read_text())
        assert metadata['development_only'] is True and metadata['micro_only'] is False
        summary=json.loads((directory/'summary.json').read_text())
        predpath=directory/'predictions.jsonl';assert sha(predpath)==summary['prediction_sha256']
        inputs={}
        for name,h in metadata['input_hashes'].items():
            assert name in {'dev_fact_v3.jsonl','dev_structured_v3.jsonl'}
            path=ROOT/'datasets_v3'/name;assert sha(path)==h
            for line in path.read_text().splitlines():
                row=json.loads(line);inputs[row['example_id']]=row
        raw=[json.loads(line) for line in predpath.read_text().splitlines()]
        assert len(raw)==metadata['expected_count']==len(inputs)
        assert {r['example_id'] for r in raw}==set(inputs)
        assert metadata['prompt_sha256']==sha(ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json')
        core=[];telemetry=[]
        for row in raw:
            item=inputs[row['example_id']]
            assert row['question']==item['question'] and row['gold']==item['gold_value']
            assert row['condition']==condition
            canonical={key:row[key] for key in R.ALL_FIELDS}
            # Preserve runtime extras separately, never silently throw away evidence.
            telemetry.append({'example_id':row['example_id'],**{k:v for k,v in row.items() if k not in R.ALL_FIELDS}})
            core.append(R.from_dict(canonical))
        verification=V.verify(core,expected_count=len(inputs),expected_families={r['family'] for r in inputs.values()})
        (directory/'canonical_records.jsonl').write_text(''.join(json.dumps(r.to_dict(),ensure_ascii=False)+'\n' for r in core))
        (directory/'runtime_telemetry.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in telemetry))
        byfamily=defaultdict(list);byattribute=defaultdict(list)
        for row in raw:
            byfamily[row['family']].append(row)
            if 'attribute' in inputs[row['example_id']]:byattribute[inputs[row['example_id']]['attribute']].append(row)
        def stats(rows):
            return {'n':len(rows),'correct':sum(r['status']=='correct' for r in rows),
                    'statuses':dict(Counter(r['status'] for r in rows)),
                    'exact_score':sum(r['task_result_correctness'] for r in rows)/len(rows)}
        report[condition]={'verification':verification,'overall':stats(raw),
            'by_family':{k:stats(v) for k,v in byfamily.items()},'by_attribute':{k:stats(v) for k,v in byattribute.items()},
            'predictions_sha256':sha(predpath),'canonical_sha256':sha(directory/'canonical_records.jsonl'),
            'telemetry_sha256':sha(directory/'runtime_telemetry.jsonl')}
    dest=ROOT/'results_v3/dev';(dest/'VERIFIED_BASELINES_A002.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# V3 development baselines — not final test results','','These are unchanged-base-model development runs. There are no completed final fine-tuning runs. Q42 approval remains pending.','','| Condition | Family | Exact correct / total | Score |','|---|---|---:|---:|']
    for condition,data in report.items():
        for family,s in data['by_family'].items():lines.append(f"| {condition} | {family} | {s['correct']} / {s['n']} | {s['exact_score']:.1%} |")
    lines+=['','The factual metric is conservative normalized exact-value/set scoring under a JSON response contract. Extra certification/process/service entries fail exact-set accuracy. Semantically equivalent prose or different descriptions of missing evidence can still be rejected; raw outputs remain available for separate adjudication. SQL conditions execute against train_dev_kb with identical full-source vocabulary catalogues. Oracle context provides the correct record by construction. These information-access conditions must not be compared as pure weight memorization.','',
      'The current 51 structured development questions are entity-conditioned filters, not a comprehensive analytical benchmark. Their scores cannot establish aggregation or supplier-risk competence. A separate real-model micro battery exercises count, ranking, grouping, composition, empty results and multipart SQL, but its six hand-constructed items are a plumbing check, not a generalization estimate.','',
      'Every input ID and gold was verified against its declared development artifact. Canonical records use the existing EvalRecord schema; additional runtime fields are retained in sidecar telemetry. No failed prediction was removed from a denominator. Earlier initial/json_contract runs are pilots and are excluded from this table.']
    (dest/'REPORT_A002.md').write_text('\n'.join(lines)+'\n')
    print('PASS: all four development baselines verified; canonical records and telemetry retained.')
if __name__=='__main__':main()
