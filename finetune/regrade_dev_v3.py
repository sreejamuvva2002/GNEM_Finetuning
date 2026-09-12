"""Re-score RETAINED development raw predictions under answer_parser_A002.2.

No model inference is repeated: a grader change does not invalidate the sampled
text, only the verdict computed from it. Every original artifact under
`protocol_A002/` is read-only here; results land in a new `protocol_A002_regrade_r2/`
directory plus versioned `*_r2` reports, so the r1 evidence stays byte-identical and
the two can be diffed.

Provenance recorded per condition: the source predictions hash as published in
VERIFIED_BASELINES_A002.json, the dev input hashes as frozen in
EVALUATION_INPUT_MANIFEST_A002.json, the new grader hash, and this regrader's hash.

SQL conditions are regraded through the UNCHANGED grade_v3, and the run asserts
their verdicts are identical to r1 -- a control showing the delta is confined to
the natural-language answer path.
"""
import hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'finetune'))
import eval_records_v3 as R          # noqa: E402
import eval_verify_v3 as V           # noqa: E402
import grade_v3 as G                 # noqa: E402
from answer_parser_v3 import grade_answer,VERSION as PARSER_VERSION  # noqa: E402

RUN_ID='protocol_A002_regrade_r2'
SOURCE_RUN='protocol_A002'
CONDITIONS=('base','base_ctx_oracle','base_sql','base_sql_5shot')
DB=ROOT/'datasets_v3/gnem_v3.sqlite'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs(names):
    manifest=json.loads((ROOT/'datasets_v3/EVALUATION_INPUT_MANIFEST_A002.json').read_text())
    items={}
    for name in names:
        path=ROOT/'datasets_v3'/name
        if sha(path)!=manifest['sha256'][name]:
            raise SystemExit(f'dev input drifted from the frozen manifest: {name}')
        if manifest['classification'][name]!='dev':
            raise SystemExit(f'refusing to regrade a non-dev input: {name}')
        for line in path.read_text().splitlines():
            row=json.loads(line);items[row['example_id']]=row
    return items


def regrade_condition(condition,regrader_sha):
    source=ROOT/'results_v3/dev'/condition/SOURCE_RUN
    published=json.loads((ROOT/'results_v3/dev/VERIFIED_BASELINES_A002.json').read_text())
    metadata=json.loads((source/'manifest.json').read_text())
    predpath=source/'predictions.jsonl'
    source_sha=sha(predpath)
    if source_sha!=published[condition]['predictions_sha256']:
        raise SystemExit(f'{condition}: retained predictions differ from the published r1 hash')
    items=load_inputs(metadata['input_hashes'])
    raw=[json.loads(line) for line in predpath.read_text().splitlines()]
    if len(raw)!=metadata['expected_count']:
        raise SystemExit(f'{condition}: prediction count differs from the recorded expectation')
    sql_condition='sql' in condition
    core=[];telemetry=[];changes=[]
    for row in raw:
        item=items[row['example_id']]
        if row['question']!=item['question'] or row['gold']!=item['gold_value']:
            raise SystemExit(f"{condition}/{row['example_id']}: retained record does not match its dev input")
        text=row['raw_output']                      # raw prediction preserved verbatim
        truncated=bool(row.get('stopped_at_max_new_tokens'))
        if sql_condition:
            result=G.grade_structured(item,text,item['gold_sql'],'train_dev_kb',
                                      db_path=DB,stopped_at_max_new_tokens=truncated)
            parsed=text;grader=G.GRADER_VERSION;graderpath=ROOT/'finetune/grade_v3.py'
        else:
            result,parsed=grade_answer(text,item,truncated)
            grader=PARSER_VERSION;graderpath=ROOT/'finetune/answer_parser_v3.py'
        if result.status!=row['status']:
            changes.append({'example_id':row['example_id'],
                            'attribute':item.get('attribute'),
                            'from':row['status'],'to':result.status,
                            'raw_output':text,'gold':row['gold'],
                            'format_repairs':result.metrics.get('format_repairs',[]),
                            'output_contract_compliant':result.metrics.get('output_contract_compliant')})
        record=R.EvalRecord(
            example_id=row['example_id'],family=row['family'],condition=condition,
            question=row['question'],raw_output=text,
            parsed_output=json.dumps(parsed,ensure_ascii=False) if parsed is not None else None,
            generated_sql=row['generated_sql'],execution_result=row['execution_result'],
            gold=row['gold'],answer_type=row['answer_type'],target_columns=row['target_columns'],
            task_result_correctness=result.task_result_correctness,
            strict_result_schema_accuracy=result.strict_result_schema_accuracy,
            status=result.status,
            error_type=None if result.status=='correct' else result.status,
            error_detail=result.detail,prompt_hash=row['prompt_hash'],
            adapter_hash=row['adapter_hash'],seed=row['seed'],
            grader_version=grader,grader_sha256=sha(graderpath),
            parts=row.get('parts'),regrade_outcome='recomputed',regrader_sha256=regrader_sha)
        core.append(record)
        telemetry.append({'example_id':row['example_id'],'metrics':result.metrics,
                          'r1_status':row['status'],'r1_grader_sha256':row['grader_sha256'],
                          **{k:v for k,v in row.items()
                             if k not in R.ALL_FIELDS and k not in ('metrics',)}})
    if not sql_condition and any(c['from']=='correct' and c['to']!='correct' for c in changes):
        raise SystemExit('Regrade rejected a previously correct answer')
    if sql_condition and changes:
        raise SystemExit(f'{condition}: grade_v3 is unchanged but SQL verdicts moved -- investigate')
    verification=V.verify(core,expected_count=len(items),grader_sha256=sha(graderpath),
                          expected_families={r['family'] for r in items.values()})
    out=ROOT/'results_v3/dev'/condition/RUN_ID;out.mkdir(parents=True,exist_ok=True)
    (out/'predictions.jsonl').write_text(
        ''.join(json.dumps(r.to_dict(),ensure_ascii=False)+'\n' for r in core))
    (out/'runtime_telemetry.jsonl').write_text(
        ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in telemetry))
    (out/'manifest.json').write_text(json.dumps({
        'condition':condition,'regrade_of':f'results_v3/dev/{condition}/{SOURCE_RUN}',
        'source_predictions_sha256':source_sha,'development_only':True,'micro_only':False,
        'model_inference_repeated':False,'expected_count':metadata['expected_count'],
        'input_hashes':metadata['input_hashes'],'prompt_sha256':metadata['prompt_sha256'],
        'model_revision':metadata['model_revision'],
        'grader_version':G.GRADER_VERSION if sql_condition else PARSER_VERSION,
        'grader_sha256':sha(ROOT/('finetune/grade_v3.py' if sql_condition else 'finetune/answer_parser_v3.py')),
        'regrader_sha256':regrader_sha,'status_changes':len(changes),
        'note':'Raw predictions preserved verbatim; only the verdict was recomputed.',
    },indent=2)+'\n')
    rows=[r.to_dict() for r in core]
    metrics_by_id={t['example_id']:t['metrics'] for t in telemetry}

    def stats(subset):
        n=len(subset)
        compliant=sum(bool(metrics_by_id[r['example_id']].get('output_contract_compliant')) for r in subset)
        return {'n':n,'correct':sum(r['status']=='correct' for r in subset),
                'statuses':dict(Counter(r['status'] for r in subset)),
                'semantic_exact_score':sum(r['task_result_correctness'] for r in subset)/n,
                'strict_contract_correct':sum(r['strict_result_schema_accuracy'] for r in subset)/n,
                'output_contract_compliance_rate':None if sql_condition else compliant/n}

    byfamily=defaultdict(list);byattribute=defaultdict(list)
    for r in rows:
        byfamily[r['family']].append(r)
        attribute=items[r['example_id']].get('attribute')
        if attribute:byattribute[attribute].append(r)
    return {'verification':verification,'overall':stats(rows),
            'by_family':{k:stats(v) for k,v in byfamily.items()},
            'by_attribute':{k:stats(v) for k,v in byattribute.items()},
            'status_changes':changes,
            'source_predictions_sha256':source_sha,
            'grader_sha256':sha(graderpath),
            'r1_overall':json.loads((ROOT/'results_v3/dev/VERIFIED_BASELINES_A002.json').read_text())[condition]['overall'],
            'predictions_sha256':sha(out/'predictions.jsonl'),
            'telemetry_sha256':sha(out/'runtime_telemetry.jsonl')}


def main():
    regrader_sha=sha(__file__)
    report={c:regrade_condition(c,regrader_sha) for c in CONDITIONS}
    dest=ROOT/'results_v3/dev'
    payload={'regrade_id':'r2','parser_version':PARSER_VERSION,
             'parser_sha256':sha(ROOT/'finetune/answer_parser_v3.py'),
             'sql_grader_version':G.GRADER_VERSION,
             'sql_grader_sha256':sha(ROOT/'finetune/grade_v3.py'),
             'regrader_sha256':regrader_sha,
             'supersedes':'results_v3/dev/VERIFIED_BASELINES_A002.json',
             'model_inference_repeated':False,
             'q42_approval':'pending_by_user','final_training_runs_completed':0,
             'conditions':report}
    (dest/'VERIFIED_BASELINES_A002_r2.json').write_text(json.dumps(payload,indent=2)+'\n')

    lines=['# V3 development baselines, revision r2 — not final test results','',
      'Regrade of the **retained r1 raw predictions** under `answer_parser_A002.2`. No model '
      'inference was repeated; only the verdict computed from the preserved text changed. '
      'The r1 report and its artifacts remain unmodified at '
      '[REPORT_A002.md](REPORT_A002.md) and `*/protocol_A002/`.','',
      'There are no completed final fine-tuning runs (0 of 18). Q42 approval remains pending '
      'at the user\'s direction. No protected test evaluation has run.','',
      '## Two independently computed axes','',
      '`semantic` asks whether the answer carried the recorded value, after a bounded, '
      'documented output-format repair. `format` asks whether the original response obeyed '
      'the frozen JSON output contract for its answer type, judged from the response text '
      'alone and never from agreement with gold. A well-formed wrong answer scores format '
      'but not semantic; a correct answer in prose scores semantic but not format. '
      '`strict` is the conjunction: contract-compliant AND matching gold with no repair.','',
      '| Condition | Family | Semantic correct / total | Semantic | Format-compliant | Strict |',
      '|---|---|---:|---:|---:|---:|']
    for condition,data in report.items():
        for family,s in data['by_family'].items():
            lines.append(f"| {condition} | {family} | {s['correct']} / {s['n']} | "
                         f"{s['semantic_exact_score']:.1%} | "
                         + ('N/A (SQL)' if s['output_contract_compliance_rate'] is None else f"{s['output_contract_compliance_rate']:.1%}") + ' | '
                         +
                         f"{s['strict_contract_correct']:.1%} |")
    lines+=['','## What moved between r1 and r2','',
      '| Condition | r1 correct | r2 correct | Reclassified |','|---|---:|---:|---:|']
    for condition,data in report.items():
        lines.append(f"| {condition} | {data['r1_overall']['correct']} / {data['r1_overall']['n']} | "
                     f"{data['overall']['correct']} / {data['overall']['n']} | {len(data['status_changes'])} |")
    repairs=Counter()
    for data in report.values():
        for change in data['status_changes']:
            for repair in change['format_repairs']:repairs[repair]+=1
    lines+=['','Reclassification causes: '+(', '.join(f'{k} x{v}' for k,v in sorted(repairs.items())) or 'none')+'.','',
      'Every reclassification is incorrect -> correct: the bounded repair is strictly widening and '
      'is regression-tested never to reject a strictly correct answer. SQL conditions are regraded '
      'through the unchanged `grade_v3` as a control and must not move; the run aborts if they do.','',
      '## Limits that r2 does not change','',
      '- The oracle-context condition is provided the correct record by construction, and the SQL '
      'conditions execute against `train_dev_kb` with identical full-source vocabulary catalogues. '
      'These information-access conditions must not be compared as pure weight memorization.',
      '- All 51 structured development questions quote their own gold answer inside the question '
      '(*"Which recorded company is named X and has &lt;field&gt; recorded as V?"* with gold `[[X]]`). '
      'A 100% score on them is a ceiling artifact, not evidence of analytical capability, and they '
      'remain unfit for checkpoint selection. Tracked in '
      '[PRE_TRAINING_GATES_A002.md](../../validation_v3/PRE_TRAINING_GATES_A002.md).',
      '- Boolean surface forms (`true`/`False`) against recorded `Yes`/`No` remain incorrect by '
      'decision; the contract asks for the recorded value.',
      '- No failed prediction was removed from a denominator. Earlier `initial`/`json_contract` runs '
      'remain pilots and are excluded.']
    (dest/'REPORT_A002_r2.md').write_text('\n'.join(lines)+'\n')
    total=sum(len(d['status_changes']) for d in report.values())
    print(f'PASS: four conditions regraded from retained raw predictions; {total} reclassified; '
          f'SQL control unchanged. r1 artifacts untouched.')


if __name__=='__main__':main()
