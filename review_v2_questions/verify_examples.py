from pathlib import Path
import ast,collections,csv,hashlib,json,sqlite3,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
facts=collections.defaultdict(lambda:[0,0]);certs=[];selected=[]
keys={('B_facts','probe_recall',1),('B_facts','probe_recall_paraphrase',1),('B_facts','probe_recall',11),('BC_facts_answers','probe_recall',11),('D_sql','probe_recall',11),('B_facts','probe_cert_recall',2),('B_facts','probe_recall',12),('C_answers','probe_42',8),('BD_facts_sql','probe_42',8),('D_sql','probe_42',8),('D_sql','probe_42',16),('BD_facts_sql','probe_42',12),('BD_facts_sql','probe_42',23),('B_facts','probe_42',12)}
for line in (OUT/'all_predictions.jsonl').open():
 r=json.loads(line);a=r['analysis']
 if a['seed']!='original':continue
 if (a['condition'],a['probe'],a['source_line']) in keys:selected.append(r)
 if a['condition']=='B_facts' and a['probe']=='probe_recall':
  k=(a['attribute'],a['entity_split']);facts[k][0]+=a['stored_correct'];facts[k][1]+=1
 if a['condition']=='B_facts' and a['probe']=='probe_cert_recall':
  prefix=a['company']+' holds:';pred=str(a['answer']);gold=a['gold']
  parsed=pred.startswith(prefix)
  if parsed:
   values={x.strip().rstrip('.').casefold() for x in pred[len(prefix):].split(';') if x.strip()}
   expected={x.strip().rstrip('.').casefold() for x in gold.split(';') if x.strip()}
   certs.append({'question':a['question'],'source_line':a['source_line'],'stored_correct':a['stored_correct'],'answer':pred,'gold':gold,'predicted_set':sorted(values),'gold_set':sorted(expected),'unsupported_entries':sorted(values-expected),'missing_entries':sorted(expected-values),'literal_set_correct':values==expected})
checks={}
with sqlite3.connect('file:'+str(OUT/'historical_gnem.sqlite')+'?mode=ro',uri=True) as con:
 for name,q in {
  'ACM_category':"SELECT category FROM companies WHERE company='ACM Georgia LLC'",
  'Adient_employment':"SELECT employment FROM companies WHERE company='Adient'",
  'Ajin_location':"SELECT city,county FROM companies WHERE company='Ajin Georgia'",
  'ADVICS_certifications':"SELECT standard_family FROM certifications k JOIN companies c ON c.row_id=k.row_id WHERE c.company='ADVICS Manufacturing Georgia LLC' ORDER BY standard_family",
  'Tier1_highest_county':"SELECT county,SUM(employment) FROM companies WHERE category='Tier 1' GROUP BY county ORDER BY SUM(employment) DESC LIMIT 1",
  'Copper_foil_candidates':"SELECT company,product_service FROM companies WHERE lower(product_service) LIKE '%copper foil%'",
 }.items():
  try:checks[name]={'sql':q,'rows':con.execute(q).fetchall()}
  except Exception as e:checks[name]={'sql':q,'error':str(e)}
 for r in selected:
  a=r['analysis']
  if a['condition'] not in ['D_sql','BD_facts_sql']:continue
  try:result={'rows':con.execute(a['completion']).fetchall()}
  except Exception as e:result={'error':str(e)}
  a['independent_archived_db_execution']=result
source=subprocess.check_output(['git','show','v2-frozen-reference:finetune/taxonomy.py'],cwd=ROOT,text=True)
module=ast.parse(source);tax={}
for n in module.body:
 if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id in ['REQUIRED_PHRASES','REQUIRED_NUMBERS']:
  tax[n.target.id]=ast.literal_eval(n.value)
checks['Q8_grader_requires']={k:v.get(8) for k,v in tax.items()}
(OUT/'verified_examples.json').write_text(json.dumps({'checks':checks,'selected_predictions':selected},indent=2,ensure_ascii=False)+'\n')
(OUT/'certification_literal_set_audit.json').write_text(json.dumps({'scope':'Original B_facts only; parses exact company-holds template; case/whitespace normalized, no semantic synonym resolution','total_probe_records':118,'parsed':len(certs),'stored_correct_with_extra_entries':sum(x['stored_correct']==1 and bool(x['unsupported_entries']) for x in certs),'items':certs},indent=2)+'\n')
print(json.dumps(checks,indent=2));print('Certs parsed',len(certs),'stored passes with extras',sum(x['stored_correct']==1 and bool(x['unsupported_entries']) for x in certs))
print('facts',dict(facts))
