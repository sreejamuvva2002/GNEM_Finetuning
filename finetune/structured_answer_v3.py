"""Exact JSON result-shape grading for ordered rows and multipart answers.

No free-text extraction or substring matching. Nested parts use the existing
scalar/set grader. This is an engineering extension, not Q42 approval.
"""
import json
from grade_v3 import GradeResult

def _reject_constant(value):
    raise ValueError('Nonstandard JSON constant: '+value)

def grade_structured_answer(text,item,truncated=False):
    from answer_parser_v3 import normalize,grade_answer
    if truncated:return GradeResult('truncated_output',0.,0.,'Incomplete structured answer'),None
    try:pred=json.loads(text,parse_constant=_reject_constant)
    except (ValueError,TypeError):
        return GradeResult('parse_failure',0.,0.,'Expected one JSON result',
                           {'output_contract_compliant':False,'semantically_correct':False}),None
    kind=item['answer_type']; gold=item['gold_value']
    if kind=='multi_part':
        parts=item.get('parts',[]); ids=[p['part_id'] for p in parts]
        if not ids or len(ids)!=len(set(ids)) or not isinstance(gold,dict) or set(gold)!=set(ids):
            raise ValueError('Multipart gold and part IDs must agree exactly')
        shape=isinstance(pred,dict) and set(pred)==set(ids)
        if not shape:
            return GradeResult('incorrect',0.,0.,'Multipart answer must contain exactly the requested part IDs',
                               {'output_contract_compliant':False,'semantically_correct':False}),pred
        results={}
        for part in parts:
            key=part['part_id'];sub={**part,'gold_value':gold[key]}
            g,_=grade_answer(json.dumps(pred[key],ensure_ascii=False),sub)
            results[key]=g
        ok=all(g.task_result_correctness==1 for g in results.values())
        compliant=all(g.metrics.get('output_contract_compliant',False) for g in results.values())
        strict=all(g.strict_result_schema_accuracy==1 for g in results.values())
        return GradeResult('correct' if ok else 'incorrect',float(ok),float(strict),
                           'Multipart exact result; every part required',
                           {'output_contract_compliant':compliant,'semantically_correct':ok,
                            'part_accuracy':sum(g.task_result_correctness for g in results.values())/len(parts),
                            'parts':{k:{'status':g.status,'correct':g.task_result_correctness} for k,g in results.items()}}),pred
    if not isinstance(gold,dict) or 'rows' not in gold or 'columns' not in gold:
        raise ValueError('Structured gold requires columns and rows')
    columns=gold['columns'];width=len(columns)
    shape=(isinstance(pred,list) and all(isinstance(r,list) and len(r)==width
           and all(not isinstance(v,(dict,list)) for v in r) for r in pred))
    if not shape:
        return GradeResult('incorrect',0.,0.,'Expected array of rows with requested column count',
                           {'output_contract_compliant':False,'semantically_correct':False}),pred
    def rowkey(row):return tuple(('null',) if v is None else ('value',normalize(v)) for v in row)
    expected=[rowkey(r) for r in gold['rows']];actual=[rowkey(r) for r in pred]
    ok=(actual==expected) if kind=='top_k' else (set(actual)==set(expected))
    return GradeResult('correct' if ok else 'incorrect',float(ok),float(ok),
                       'Ordered row equality' if kind=='top_k' else 'Exact unordered row-set equality',
                       {'output_contract_compliant':True,'semantically_correct':ok}),pred
