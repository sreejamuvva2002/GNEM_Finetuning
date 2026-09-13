"""Build a versioned diagnostic multipart dev set from frozen dev components."""
import json
import hashlib
from pathlib import Path
import sqlexec_v3 as X
ROOT=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(source):
    counts=sorted((x for x in source if x['answer_type']=='scalar'),key=lambda x:x['example_id'])
    lists=sorted((x for x in source if x['answer_type']=='set'),key=lambda x:x['example_id'])
    # Exclude certifications here to avoid the held-out certifications+processes composition.
    counts=[x for x in counts if 'certifications' not in x['fields_used']]
    lists=[x for x in lists if 'certifications' not in x['fields_used']]
    if len(counts)<12 or len(lists)<12:raise ValueError('Insufficient permitted components')
    result=[]
    for i in range(12):
        components=[counts[i],lists[(i+3)%len(lists)]]
        if i>=6:components.append(counts[(i+7)%len(counts)])
        parts=[];golds={};sql={};questions=[]
        for j,component in enumerate(components):
            key=f'part_{j+1}'
            parts.append({'part_id':key,'answer_type':component['answer_type'],
                          'target_columns':component['target_columns']})
            golds[key]=component['gold_value'];sql[key]=component['gold_sql']
            questions.append(key+': '+component['question'])
        result.append({'example_id':f'DEV_MULTI_R1_{i+1:02d}','family':'dev_multipart_r1',
            'question':'Answer every part independently.\n'+'\n'.join(questions),
            'answer_type':'multi_part','parts':parts,'gold_value':golds,'gold_sql':sql,
            'scope':'train_dev_kb','task_split':'dev',
            'component_ids':[x['example_id'] for x in components],
            'component_dev_anchor_row_ids':{p['part_id']:c['dev_anchor_row_ids'] for p,c in zip(parts,components)},
            'fields_used':sorted({f for c in components for f in c['fields_used']}),'operation_family':'filter',
            'note':'Recombination of existing dev components; not an independent unseen-fact benchmark. Not used for checkpoint selection.'})
    return result

def main():
    source=ROOT/'datasets_v3/dev_structured_r2_v3.jsonl'
    out=ROOT/'datasets_v3/dev_multipart_r1_v3.jsonl'
    manifest=ROOT/'validation_v3/DEV_MULTIPART_R1_MANIFEST.json'
    if out.exists() or manifest.exists():raise RuntimeError('Versioned artifacts already exist')
    rows=build([json.loads(l) for l in source.read_text().splitlines()])
    for row in rows:
        for key,sql in row['gold_sql'].items():
            r=X.run_sql(sql,row['scope'],db_path=ROOT/'datasets_v3/gnem_v3.sqlite')
            assert {'columns':list(r.columns),'rows':[list(v) for v in r.rows]}==row['gold_value'][key]
    out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    manifest.write_text(json.dumps({'version':'dev_multipart_r1','items':12,'parts':30,
        'classification':'dev','source_sha256':sha(source),'dataset_sha256':sha(out),
        'builder_sha256':sha(Path(__file__)),'database_sha256':sha(ROOT/'datasets_v3/gnem_v3.sqlite'),
        'sql_parts_verified':30,'selection':'Sorted non-certification dev components, fixed offsets; six two-part and six three-part tasks.',
        'limitations':['All components reused from dev r2; scores are correlated with it.',
                      'Allowed filters/counts only; not broad multipart domain analysis.',
                      'No automatic adoption for training or checkpoint selection.']},indent=2)+'\n')
    print('Built 12 multipart dev questions; verified 30 scoped SQL parts.')
if __name__=='__main__':main()
