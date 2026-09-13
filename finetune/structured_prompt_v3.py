"""Explicit result-shape contracts for final structured evaluation integration.

Existing baseline prompt artifacts remain unchanged. Consumers must record this
module's hash when adopting these instructions for a separately versioned run.
"""
import json
VERSION='structured_prompt_A002.2_unique_sets'
def output_instruction(item):
    kind=item['answer_type']
    if kind=='multi_part':
        parts=item.get('parts',[]);ids=[p['part_id'] for p in parts]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Unique multipart IDs required')
        descriptions={p['part_id']:output_instruction(p) for p in parts}
        return 'Return only one JSON object with exactly these part IDs and contracts: '+json.dumps(descriptions,ensure_ascii=False)
    if kind=='scalar':return 'Return only one JSON string or number containing the recorded value.'
    if kind=='top_k':return 'Return only a JSON array of rows in the requested order, with columns ordered as '+json.dumps(item.get('target_columns',[]))+'.'
    if kind=='set':
        if len(item.get('target_columns',[]))>1:
            return 'Return only a JSON array of unique rows (no duplicate rows), with columns ordered as '+json.dumps(item['target_columns'])+'. Return [] if no record matches.'
        return 'Return only a JSON array of every requested value exactly once (no duplicates). Return [] if no record matches.'
    raise ValueError('Unsupported answer type: '+str(kind))
