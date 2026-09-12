"""Construct dev and protected probe inputs, never model predictions or scores."""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kb_v3 as K
import holdout_v3 as H
import phase11_build_b_facts as B
import phase12_task_pool as P
import sqlexec_v3 as X
import leak_audit_v3 as L
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'datasets_v3'

def read(name):return [json.loads(s) for s in (OUT/name).read_text().splitlines()]
def save(name,rows):
    assert rows and len({r['example_id'] for r in rows})==len(rows),name
    (OUT/name).write_text(''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows))

def factual(rec,field,split,paraphrase=False):
    item=B.render_item(rec.company,field,getattr(rec,field))
    # Row scoping prevents fabricated reconciliation of duplicate names.
    question=(f"In source record {rec.row_id} for {rec.company}, what does the dataset record for "
              f"{field.replace('_',' ')}?")
    if paraphrase:
        question=(f"Give the recorded {field.replace('_',' ')} for {rec.company}, using source "
                  f"record {rec.row_id}. If evidence is missing, state that limitation.")
    item.update(example_id=f"{'FP' if paraphrase else 'FR'}_{rec.row_id}_{field}",question=question,
        row_id=rec.row_id,entity_split=split,scope='train_dev_kb' if split=='dev' else 'full_kb',
        family='factual_paraphrase' if paraphrase else 'factual_recall',
        knowledge_exposure=['trained_fact'] if split=='train' else ['heldout_entity'])
    item['messages'][1]['content']=question
    item['source_row_ids']=[rec.row_id]
    item['gold_sql']=f'SELECT {field} AS value FROM companies WHERE row_id = {rec.row_id}' if field not in H.MULTIVALUED else None
    return item

def task(identifier,question,sql,fields,values,scope='full_kb',family='structured',answer_type='set',columns=None):
    cols=columns or ['company']
    item=P.make_task(identifier,question,sql,answer_type=answer_type,target_columns=cols,
                     fields_used=fields,values_used=values,logical_components={'op':'query','field':'sql','value':sql},
                     join_arity=len(__import__('re').findall(r'\bJOIN\b',H._strip_sql_noise(sql),__import__('re').I)))
    result=X.run_sql(sql,scope,db_path=OUT/'gnem_v3.sqlite')
    item.update(example_id=identifier,family=family,scope=scope,
                gold_value={'columns':list(result.columns),'rows':[list(r) for r in result.rows]},
                entity_dependent=True)
    item['logical_fingerprint']=H.logical_fingerprint(item)
    return item

def main():
    proof=json.loads((ROOT/'validation_v3/resumption/FULL_FIELD_COVERAGE_A002.json').read_text())
    assert all(H.sha256_file(OUT/name)==v['sha256'] for name,v in proof['artifacts'].items()), 'Training audit is stale'
    reg=H.load_registry(); records=K.load_kb('full_kb'); splits=L.row_splits()
    train=K.load_kb('train_kb'); dev=[r for r in records if splits[r.row_id]=='dev']
    facts=[factual(r,f,splits[r.row_id]) for r in records if splits[r.row_id]!='dev' for f in B.ALL_FIELDS]
    paraphrases=[factual(r,f,splits[r.row_id],True) for r in records if splits[r.row_id]!='dev' for f in B.ALL_FIELDS]
    devfacts=[factual(r,f,'dev') for r in dev for f in B.ALL_FIELDS]
    devstructured=[]
    for r in dev:
        for f in ('category','industry_group','primary_facility_type'):
            sql=f'SELECT DISTINCT company FROM companies WHERE company = {P.sql_lit(r.company)} AND {f} = {P.sql_lit(getattr(r,f))} ORDER BY company'
            devstructured.append(task(f'DEV_S_{r.row_id}_{f}',f'Which recorded company is named {r.company} and has {f.replace("_"," ")} recorded as {getattr(r,f)}?',sql,['company',f],[r.company,getattr(r,f)],scope='train_dev_kb',family='dev_structured'))
    pool=read('STRUCTURED_TASK_POOL_v3.jsonl'); d=read('train_D_sql_v3.jsonl'); d_ids={r['task_id'] for r in d}
    eligible=[t for t in pool if t['task_id'] in d_ids]
    # Reserve five source tasks before constructing probes, preventing fewshot/probe collision.
    few=eligible[:5]; reserved={r['logical_fingerprint'] for r in few}
    (OUT/'FEWSHOT_CANDIDATES_A002.json').write_text(json.dumps(few,indent=2)+'\n')
    heldin=[]
    for t in eligible[5:]:
        x=copy.deepcopy(t);x.update(example_id='ST_'+t['task_id'],family='structured_train',scope='train_kb',gold_value=t['train_kb_gold'],diagnostic_only=True)
        heldin.append(x)
    operations=[]
    for t in pool:
        if H.operation_families_present(t['gold_sql']):
            x=copy.deepcopy(t);x.update(example_id='OP_'+t['task_id'],family='operation_heldout',scope='full_kb',gold_value=t['full_kb_gold'])
            operations.append(x)
    compositions=[]
    f1,f2=reg['composition_holdouts']['held_out_sets'][0]
    for i,((v1,v2),_) in enumerate(sorted(P.composition_candidates(train,f1,f2).items())):
        sql=P.sql_composition(f1,v1,f2,v2)
        compositions.append(task(f'COMP_{i}',f'List companies with both recorded {f1}: {v1} and recorded {f2}: {v2}.',sql,[f1,f2],[v1,v2],family='composition_heldout'))
    values=[]
    # Natural exposure strata, with no false claim that literals were withheld.
    for f in H.MULTIVALUED:
        train_values={v for r in train for v in H.terms(getattr(r,f),f)}
        all_values={v for r in records for v in H.terms(getattr(r,f),f)}
        for i,v in enumerate(sorted(all_values)):
            x=task(f'VALUE_{f}_{i}',f'Which companies have {f.replace("_"," ")} recorded as {v}?',P.sql_child_filter(f,v),[f],[v],family='value_exposure')
            x['value_exposure']='observed_in_training_records' if v in train_values else 'naturally_unexposed_company_holdout_value'
            values.append(x)
    structured_para=[]
    for t in heldin:
        x=copy.deepcopy(t);x['example_id']='SP_'+t['task_id'];x['family']='structured_paraphrase'
        # Predicate-specific wording, not a punctuation-only edit.
        if len(t['fields_used'])==1:
            f=t['fields_used'][0];v='; '.join(t['values_used'])
            x['question']=f'Return the {"number of distinct matching companies" if t["answer_type"]=="scalar" else "complete list of matching company names"} for this recorded criterion: {f.replace("_"," ")} = {v}.'
            # Numeric thresholds need the original comparator, never convert >= to equality.
            if '>' in t['gold_sql'] or '<' in t['gold_sql']: continue
        else:
            x['question']='Identify all companies satisfying both recorded criteria: '+ ' and '.join(o['field'].replace('_',' ') + ': ' + str(o['value']) for o in t['logical_components']['operands'])
        structured_para.append(x)
    nomatch=[]
    for i in range(20):
        name=f'GNEM nonexistent fixture company {i:03d}'
        x=task(f'NM_{i}',f'List recorded companies whose name is exactly {name}.',f'SELECT company FROM companies WHERE company = {P.sql_lit(name)}',['company'],[name],family='no_match')
        assert not x['gold_value']['rows'];x['knowledge_exposure']=['no_match'];nomatch.append(x)
    outputs={'dev_fact_v3.jsonl':devfacts,'dev_structured_v3.jsonl':devstructured,
        'probe_fact_recall_v3.jsonl':facts,'probe_fact_paraphrase_v3.jsonl':paraphrases,
        'probe_structured_train_v3.jsonl':heldin,'probe_value_exposure_v3.jsonl':values,
        'probe_operation_heldout_v3.jsonl':operations,'probe_composition_heldout_v3.jsonl':compositions,
        'probe_structured_paraphrase_v3.jsonl':structured_para,'probe_no_match_v3.jsonl':nomatch}
    trainquestions={r['question'] for r in read('train_B_facts_v3.jsonl')+read('train_C_answers_v3.jsonl')}
    assert not {r['question'] for r in devfacts+devstructured+paraphrases+structured_para}&trainquestions
    assert not {r['question'] for r in facts}&{r['question'] for r in paraphrases}
    assert not {r['company'] for r in devfacts}&{r['company'] for r in facts}
    assert all(not H.operation_families_present(t['gold_sql']) for t in compositions)
    assert all(t['join_arity']==2 for t in compositions)
    assert any(t['join_arity']==2 for t in eligible)
    # Fingerprint convention differs for newly constructed tasks; also compare
    # canonical SQL directly so that metadata wording cannot hide a collision.
    few_sql={t['gold_sql'] for t in few}
    for name,rows in outputs.items():
        if name.startswith('probe_'):
            rows[:]=[r for r in rows if r.get('logical_fingerprint') not in reserved and r.get('gold_sql') not in few_sql]
        save(name,rows)
    manifest={'classification':{n:'dev' if n.startswith('dev_') else 'sealed_inputs' for n in outputs},
        'counts':{n:len(r) for n,r in outputs.items()},'sha256':{n:H.sha256_file(OUT/n) for n in outputs},
        'registry_sha256':reg.sha256(),'model_inference_performed':False,
        'limitations':['Phase 27 prompts/sanity and Phase 28 business benchmark still required',
            'Exposure strata describe source records, not equal per-arm supervision',
            'Multipart business evaluation remains in Phase 28; this builder handles single-query probes']}
    (OUT/'EVALUATION_INPUT_MANIFEST_A002.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['counts'],indent=2))
if __name__=='__main__':main()
