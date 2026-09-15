"""Reconcile retained development multipart outputs; never run inference."""
import collections
import json
from pathlib import Path
from final_contract_v3 import grade_final_answer
from prediction_export_v3 import sha

ROOT = Path(__file__).resolve().parent.parent


def main():
    source = ROOT / 'datasets_v3/dev_multipart_r1_v3.jsonl'
    base = ROOT / 'results_v3/dev/base_multipart_r1'
    out = ROOT / 'results_v3/dev/base_multipart_r1_audit_2026-09-15'
    if out.exists():
        raise RuntimeError('Preserve existing audit')
    def load(p):
        return [json.loads(s) for s in p.read_text().splitlines()]
    tasks = load(source)
    predictions = load(base / 'predictions.jsonl')
    scores = load(base / 'scores.jsonl')
    summary = json.loads((base / 'summary.json').read_text())
    runtime = json.loads((base / 'runtime.json').read_text())
    assert sha(source) == summary['input_sha256']
    assert sha(base / 'predictions.jsonl') == summary['predictions_sha256']
    for name, digest in runtime['grader_sha256'].items():
        assert sha(ROOT / 'finetune' / name) == digest, 'Historical grader drift: ' + name
    ids = [t['example_id'] for t in tasks]
    assert len(ids) == len(set(ids))
    assert ids == [p['example_id'] for p in predictions] == [s['example_id'] for s in scores]
    counts = collections.Counter()
    rows = []
    for task, pred, saved in zip(tasks, predictions, scores):
        assert pred['question'] == task['question']
        grade, _ = grade_final_answer(pred['raw_output'], task, pred['stopped_at_max_new_tokens'])
        actual = {'example_id': task['example_id'], 'status': grade.status,
                  'correct': grade.task_result_correctness,
                  'strict': grade.strict_result_schema_accuracy, 'metrics': grade.metrics}
        assert actual == saved, 'Historical score differs: ' + task['example_id']
        counts['questions'] += 1
        counts['all_parts_correct'] += saved['correct']
        counts['strict_questions_correct'] += saved['strict']
        counts['question_format_compliant'] += bool(saved['metrics']['output_contract_compliant'])
        counts['truncated_questions'] += pred['stopped_at_max_new_tokens']
        value = json.loads(pred['raw_output'])
        for part in task['parts']:
            key = part['part_id']; kind = part['answer_type']
            result = saved['metrics']['parts'][key]
            gold = task['gold_value'][key]
            counts['expected_parts'] += 1
            counts['correct_parts'] += result['correct']
            counts[kind + '_parts'] += 1
            counts[kind + '_correct'] += result['correct']
            counts['part_format_compliant'] += bool(saved['metrics']['part_metrics'][key]['output_contract_compliant'])
            if kind == 'set':
                counts['set_empty_outputs'] += value[key] == []
                counts['set_nonempty_golds'] += bool(gold['rows'])
            rows.append({'example_id': task['example_id'], 'part_id': key,
                         'component_id': task['component_ids'][len([r for r in rows if r['example_id']==task['example_id']])],
                         'answer_type': kind, 'correct': result['correct'],
                         'output': value[key], 'gold': gold})
    assert counts['all_parts_correct'] == summary['correct']
    assert counts['expected_parts'] == summary['expected_parts']
    report = {'counts': dict(counts), 'all_saved_scores_reproduced': True,
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                  [source, base/'predictions.jsonl', base/'scores.jsonl', base/'summary.json', Path(__file__)]},
              'limitations': ['Reused development components; not independent unseen-fact evidence.',
                             'Questions and parts are correlated, not independent model runs.',
                             'Audit of existing outputs only; no inference or training change.']}
    out.mkdir()
    (out/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'parts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(json.dumps(report['counts'], indent=2))


if __name__ == '__main__':
    main()
