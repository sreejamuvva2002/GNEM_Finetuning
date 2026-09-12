"""Independent source-observation and mixture audit, run after builders."""
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kb_v3 as K
import holdout_v3 as H
import phase11_build_b_facts as B
ROOT=Path(__file__).resolve().parent.parent

def load(name):
    return [json.loads(x) for x in (ROOT/'datasets_v3'/name).read_text().splitlines()]

def main():
    records=K.load_kb('train_kb'); by_id={r.row_id:r for r in records}
    a=load('train_A_cpt_v3.jsonl'); b=load('train_B_facts_v3.jsonl')
    assert {x['row_id'] for x in a}==set(by_id)
    for x in a:
        r=by_id[x['row_id']]
        assert f'Source record {r.row_id}' in x['text']
        for field in ('company',)+B.ALL_FIELDS:
            assert f'Recorded {field.replace("_"," ")}: {getattr(r,field)}.' in x['text'], (r.row_id,field)
    observed=set()
    for x in b:
        for rid in x['source_row_ids']:
            assert rid in by_id
            r=by_id[rid]; f=x['attribute']; v=getattr(r,f)
            expected=sorted(set(H.terms(v,f))) if x['answer_type']=='set' else str(v)
            assert x['gold_value']==expected,(rid,f,x['gold_value'],expected)
            observed.add((rid,f))
        if x['conflicting_observations']:
            assert len(x['source_row_ids'])==1
            assert str(x['source_row_ids'][0]) in x['question']
            assert 'disagree' in x['messages'][-1]['content']
    required={(r.row_id,f) for r in records for f in B.ALL_FIELDS}
    assert observed==required, ('Unexplained omissions',sorted(required-observed))
    d=load('train_D_sql_v3.jsonl'); c=load('train_C_answers_v3.jsonl')
    assert {x['task_id']:x['question'] for x in c}=={x['task_id']:x['question'] for x in d}
    sources={x['example_id']:x for x in b+c+d}
    files=['train_A_cpt_v3.jsonl','train_B_facts_v3.jsonl','train_C_answers_v3.jsonl','train_D_sql_v3.jsonl',
           'train_BC_facts_answers_v3.jsonl','train_BD_facts_sql_v3.jsonl','train_BD_controlled_v3.jsonl','train_D_repeat_budgetmatched_v3.jsonl']
    manifests={}
    for name in files:
        rows=load(name);ids=[x['example_id'] for x in rows]; assert len(ids)==len(set(ids))
        manifests[name]={'sha256':H.sha256_file(ROOT/'datasets_v3'/name),'example_ids':ids,
                         'source_ids':[x.get('source_example_id',x['example_id']) for x in rows]}
        if name in files[4:]:
            for x in rows:
                src=x.get('source_example_id',x['example_id'])
                assert src in sources and x['messages']==sources[src]['messages'], (name,src)
    for name,expected in [('train_BC_facts_answers_v3.jsonl',b+c),('train_BD_facts_sql_v3.jsonl',b+d),('train_BD_controlled_v3.jsonl',b+d)]:
        assert set(manifests[name]['source_ids'])=={x['example_id'] for x in expected}
    report={'training_records':len(records),'required_factual_observations':len(required),
        'covered_factual_observations':len(observed),'unexplained_omissions':[],
        'identity_fields':'company in each question/answer; source row IDs in provenance and record-scoped tasks',
        'exception':'Certification Count preserved internally; no model-facing target',
        'company_holdout_records':57,'paired_structured_items':len(c),'artifacts':manifests}
    (ROOT/'validation_v3/resumption/FULL_FIELD_COVERAGE_A002.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: {len(required)} / {len(required)} factual observations, complete A records, exact paired C/D, and full factual coverage in mixtures.')
if __name__=='__main__':main()
