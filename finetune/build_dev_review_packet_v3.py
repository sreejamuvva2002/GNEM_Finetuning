"""Render draft development items for human review; never fill review decisions."""
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'validation_v3/dev_review_packet_2026-09-15'
SOURCES=[ROOT/'datasets_v3/dev_ambiguity_r1_draft_v3.jsonl',
         ROOT/'datasets_v3/dev_supplier_evidence_r1_draft_v3.jsonl']
RUBRICS=[ROOT/'docs/DEV_AMBIGUITY_R1_DRAFT.md',ROOT/'docs/DEV_SUPPLIER_EVIDENCE_R1_DRAFT.md']


def main():
    if OUT.exists():raise RuntimeError('Preserve prior packet')
    items=[]
    for source in SOURCES:
        for line in source.read_text().splitlines():
            item=json.loads(line)
            assert item['status']=='draft_requires_human_rubric_review'
            items.append(item)
    assert len(items)==32 and len({i['example_id'] for i in items})==32
    lines=['# Development question review packet',
        'Status: draft. No model responses or completed reviewer decisions are included.',
        'Review source fidelity, question intent, acceptable answers and scoring anchors. '
        'Use accept, revise or reject in the separate CSV, with reviewer identity/date and reasons. '
        'An item decision is not a training or protected-evaluation release. '
        'Leave decisions blank until a human actually reviews the item.',
        'All source observations are supplied in context. These diagnostics do not test closed-book recall.',
        '## Scoring anchors']
    for rubric in RUBRICS:
        lines.extend([f'### Source: {rubric.relative_to(ROOT)}',rubric.read_text()])
    for i,item in enumerate(items,1):
        lines.extend([f'## {i}. {item["example_id"]}',
            f'Kind: {item["kind"]}; context SHA-256: `{item["context_sha256"]}`',
            '### Model-visible evidence',item['context'],
            '### Question',item['question'],
            '### Reviewer-only fact sheet — never include in the model prompt',
            '```json',json.dumps(item['fact_sheet'],ensure_ascii=False,indent=2),'```',
            '### Proposed scoring metadata','```json',json.dumps(item['scoring'],indent=2),'```'])
    OUT.mkdir()
    (OUT/'REVIEW_PACKET.md').write_text('\n\n'.join(lines)+'\n')
    fields=['example_id','reviewer','review_date','decision','source_fidelity','question_intent',
            'acceptable_answer_coverage','rubric_fairness','requested_revision','notes']
    with (OUT/'REVIEW_DECISIONS.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for item in items:writer.writerow({'example_id':item['example_id']})
    pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in SOURCES+RUBRICS+[Path(__file__),OUT/'REVIEW_PACKET.md',OUT/'REVIEW_DECISIONS.csv']}
    (OUT/'manifest.json').write_text(json.dumps({'status':'draft_no_human_decisions',
        'items':32,'sha256':pins,'note':'Decision-sheet hash identifies the blank template; completed reviews must be separately retained with their reviewer provenance.'},indent=2)+'\n')
    # Verify the rendered artifact contains every exact question and context once.
    text=(OUT/'REVIEW_PACKET.md').read_text()
    for item in items:
        assert item['question'] in text and item['context'] in text
    with (OUT/'REVIEW_DECISIONS.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==32 and all(not v for row in rows for k,v in row.items() if k!='example_id')
    print('Rendered 32 items with source contexts and reviewer-only fact sheets; all decisions blank.')


if __name__=='__main__':main()
