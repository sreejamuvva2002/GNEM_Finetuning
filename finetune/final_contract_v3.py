"""New final-only unique-set contract; historical graders remain unchanged."""
import json
from dataclasses import replace
from answer_parser_v3 import grade_answer,normalize
VERSION='final_unique_sets_A002.2'
def grade_final_answer(text,item,truncated=False):
    g,pred=grade_answer(text,item,truncated)
    if truncated or g.status not in ('correct','incorrect'):return g,pred
    if item['answer_type']=='multi_part' and isinstance(pred,dict):
        expected={part['part_id'] for part in item['parts']}
        if set(pred)!=expected:return g,pred
        parts={}
        for part in item['parts']:
            key=part['part_id']
            if key not in pred:return g,pred
            sub={**part,'gold_value':item['gold_value'][key]}
            parts[key]=grade_final_answer(json.dumps(pred[key]),sub)[0]
        compliant=all(x.metrics.get('output_contract_compliant',False) for x in parts.values())
        metrics={**g.metrics,'output_contract_compliant':compliant,'part_metrics':{k:x.metrics for k,x in parts.items()}}
        return replace(g,strict_result_schema_accuracy=float(all(x.strict_result_schema_accuracy==1 for x in parts.values())),metrics=metrics),pred
    if item['answer_type']!='set' or not isinstance(pred,list):return g,pred
    gold=item['gold_value']
    multi=isinstance(gold,dict) and len(gold.get('columns',[]))>1
    # Match structured_answer_v3's distinction between null and a literal string.
    key=lambda v:tuple(('null',) if x is None else ('value',normalize(x)) for x in v) if multi else normalize(v)
    if multi and any(not isinstance(r,list) for r in pred):return g,pred
    keys=[key(v) for v in pred];duplicates=len(keys)-len(set(keys))
    compliant=bool(g.metrics.get('output_contract_compliant',False)) and duplicates==0
    metrics={**g.metrics,'duplicate_rows':duplicates,'output_contract_compliant':compliant,'contract_version':VERSION}
    return replace(g,strict_result_schema_accuracy=float(g.strict_result_schema_accuracy==1 and compliant),metrics=metrics),pred
