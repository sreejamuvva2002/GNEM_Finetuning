"""Verify current development runs and report disaggregated scores; never regrade."""
import json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import eval_records_v3 as R
import eval_verify_v3 as V
ROOT=Path(__file__).resolve().parent.parent
RUN='protocol_A002_dev_r3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    report={}
    for c in ('base','base_ctx_oracle','base_sql','base_sql_5shot'):
        out=ROOT/'results_v3/dev'/c/RUN
        m=json.loads((out/'manifest.json').read_text());summary=json.loads((out/'summary.json').read_text())
        assert sha(out/'predictions.jsonl')==summary['prediction_sha256']
        inputs={}
        for name,h in m['input_hashes'].items():
            p=ROOT/'datasets_v3'/name;assert sha(p)==h
            inputs.update({r['example_id']:r for r in map(json.loads,p.read_text().splitlines())})
        rows=list(map(json.loads,(out/'predictions.jsonl').read_text().splitlines()))
        assert len(rows)==len(inputs)==m['expected_count'] and {r['example_id'] for r in rows}==set(inputs)
        for r in rows:
            t=inputs[r['example_id']];assert r['gold']==t['gold_value'] and r['question']==t['question'] and r['condition']==c
        core=[R.from_dict({k:r[k] for k in R.ALL_FIELDS}) for r in rows]
        grader=m['sql_grader_sha256'] if 'sql' in c else m['parser_sha256']
        verify=V.verify(core,expected_count=len(inputs),expected_families={r['family'] for r in inputs.values()},grader_sha256=grader)
        (out/'canonical_records.jsonl').write_text(''.join(json.dumps(r.to_dict(),ensure_ascii=False)+'\n' for r in core))
        (out/'runtime_telemetry.jsonl').write_text(''.join(json.dumps({'example_id':r['example_id'],**{k:v for k,v in r.items() if k not in R.ALL_FIELDS}},ensure_ascii=False)+'\n' for r in rows))
        groups=defaultdict(list)
        for r in rows:
            t=inputs[r['example_id']];groups['family:'+r['family']].append(r)
            if 'join_arity' in t:
                groups['arity:'+str(t['join_arity'])].append(r)
                groups['answer_type:'+t['answer_type']].append(r)
                if t['answer_type']=='set':groups['set_size:'+('1' if len(t['gold_value']['rows'])==1 else '2-10' if len(t['gold_value']['rows'])<=10 else '11+')].append(r)
        def stats(a):return {'n':len(a),'correct':sum(r['status']=='correct' for r in a),'semantic':sum(r['task_result_correctness'] for r in a)/len(a),'strict':sum(r['strict_result_schema_accuracy'] for r in a)/len(a),'format':None if 'sql' in c else sum(bool(r['metrics'].get('output_contract_compliant')) for r in a)/len(a),'statuses':dict(Counter(r['status'] for r in a))}
        report[c]={'verification':verify,'groups':{k:stats(v) for k,v in groups.items()},'overall':stats(rows),'predictions_sha256':sha(out/'predictions.jsonl'),'manifest_sha256':sha(out/'manifest.json')}
    dest=ROOT/'results_v3/dev'
    payload={'run_id':RUN,'reporter_sha256':sha(__file__),'conditions':report,'final_training_runs':0,'q42_approval':'pending'}
    (dest/'VERIFIED_BASELINES_A002_r3.json').write_text(json.dumps(payload,indent=2)+'\n')
    lines=['# Corrected development-set baselines — r3','',
      'These are fresh unchanged-base runs. Structured questions use dev_structured_r2_v3.jsonl (120 items); factual questions retain the 255-item input. Old r1/r2 outputs are preserved. Scores across different benchmarks are not evidence of model improvement.','',
      'Oracle context covers factual questions only and supplies the correct source record. SQL conditions execute against train_dev_kb. These conditions do not measure pure weight memorization. SQL strictness measures column-schema equality; natural-language strictness requires correct content without repair in the JSON contract. Format is not applicable to SQL.','',
      '| Condition | Slice | Correct / total | Semantic | Format | Strict |','|---|---|---:|---:|---:|---:|']
    for c,d in report.items():
        for key,s in d['groups'].items():
            fmt='N/A' if s['format'] is None else f"{s['format']:.1%}"
            lines.append(f"| {c} | {key} | {s['correct']}/{s['n']} | {s['semantic']:.1%} | {fmt} | {s['strict']:.1%} |")
    lines+=['','All expected IDs and golds checked, all failures retained in denominators. Machine report includes per-slice statuses. This is still a small dataset with repeated source companies and related templates; slices are descriptive, not independent trials. It does not evaluate supplier qualification, capacity, import vulnerability or broad reasoning. Final training and protected evaluation have not run; Q42 approval remains pending.']
    (dest/'REPORT_A002_r3.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({c:d['overall'] for c,d in report.items()},indent=2))
if __name__=='__main__':main()
