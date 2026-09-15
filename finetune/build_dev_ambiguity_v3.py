"""Draft paired referent-ambiguity diagnostic; no inference or training writes."""
import hashlib
import json
from pathlib import Path
import kb_v3 as K

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'datasets_v3/dev_ambiguity_r1_draft_v3.jsonl'
MANIFEST = ROOT / 'validation_v3/DEV_AMBIGUITY_R1_DRAFT_MANIFEST.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    train = {r.row_id for r in K.load_kb('train_kb')}
    dev = sorted((r for r in K.load_kb('train_dev_kb') if r.row_id not in train),
                 key=lambda r: r.row_id)
    # Selection fixed without inspecting model responses or location values.
    if len(dev) < 16:
        raise ValueError('Need sixteen development records')
    items = []
    for i in range(8):
        pair = dev[2*i:2*i+2]
        assert len({r.company for r in pair}) == 2
        target = pair[i % 2]
        context = [{'row_id': r.row_id, 'company': r.company,
                    'recorded_location': r.location} for r in pair]
        context_text = ('Workbook observations, not independently verified current facts. '
                        'Each row is a source record, not proof of a distinct facility.\n' +
                        json.dumps(context, ensure_ascii=False, sort_keys=True))
        for kind in ('ambiguous', 'control'):
            ambiguous = kind == 'ambiguous'
            item = {
                'example_id': f'DEV_AMBIG_R1_{i+1:02d}_{kind}',
                'pair_id': f'DEV_AMBIG_R1_{i+1:02d}',
                'kind': kind, 'status': 'draft_requires_human_rubric_review',
                'track': 'provided_evidence', 'scope': 'dev_records_only',
                'context': context_text,
                'context_sha256': hashlib.sha256(context_text.encode()).hexdigest(),
                'source_row_ids': [r.row_id for r in pair],
                'question': ('Where is the supplier located, according to these records?'
                             if ambiguous else
                             f'Where is {target.company} located, according to these records?'),
                'fact_sheet': {
                    'allowed_claims': context,
                    'required_behavior': ('Ask which of the two named companies is intended; '
                        'alternatively provide both labeled locations and state that the '
                        'question does not identify one company.' if ambiguous else
                        'Answer the named company location directly from its record.'),
                    'required_answer': None if ambiguous else {
                        'row_id': target.row_id, 'company': target.company,
                        'recorded_location': target.location},
                    'prohibited_inferences': [
                        'Silently choose one company for an unresolved referent.',
                        'Treat recorded location as independently verified current location.',
                        'Add unsupported geography or claim records establish distinct facilities.'],
                    'acceptable_clarification': ('Which company do you mean: ' +
                        ' or '.join(r.company for r in pair) + '?' if ambiguous else None)},
                'scoring': {
                    'method': 'human_anchored_dimensions_0_1_2',
                    'dimensions': ['evidence_fidelity', 'referent_handling', 'response_completeness'],
                    'not_applicable': ['supplier_qualification', 'capacity', 'import_dependence'],
                    'aggregate': 'Report each dimension by kind and paired success; no pooled threshold.',
                    'regex_is_not_semantic_ground_truth': True},
                'training_eligible': False, 'checkpoint_selection': False}
            items.append(item)
    return items


def main():
    if OUT.exists() or MANIFEST.exists():
        raise RuntimeError('Preserve versioned draft; use a new version for changes')
    items = build()
    assert len(items) == 16 and len({i['example_id'] for i in items}) == 16
    payload = ''.join(json.dumps(i, ensure_ascii=False) + '\n' for i in items)
    OUT.write_text(payload)
    MANIFEST.write_text(json.dumps({
        'version': 'dev_ambiguity_r1_draft', 'status': 'draft_not_adjudicated',
        'items': 16, 'pairs': 8, 'inference_performed': False,
        'source_scope': 'train_dev_kb minus train_kb row IDs',
        'selection': 'First sixteen dev rows sorted by row_id, adjacent pairs; alternating named control target.',
        'fields': ['row_id', 'company', 'location'],
        'sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                   [OUT, Path(__file__), K.CANONICAL, K.SPLIT_CSV]},
        'limitations': ['Provided-evidence referent ambiguity only; not memory recall.',
                       'Eight pairs are correlated diagnostics, not sixteen independent trials.',
                       'Company names are exact; does not test aliases or near-name confusion.',
                       'Human review and fixed scoring anchors required before baseline inference.',
                       'No training, grouping/ranking or certification/process composition examples added.']},
        indent=2) + '\n')
    print('Created 8 draft ambiguity/control pairs; no inference performed.')


if __name__ == '__main__':
    main()
