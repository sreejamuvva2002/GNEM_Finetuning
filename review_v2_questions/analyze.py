"""Read-only census of archived V2 answers; scores retained, not blindly relabelled as truth."""
from pathlib import Path
import collections,csv,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(__file__).resolve().parent
REF='v2-frozen-reference'
def git(path):return subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT)
def rows(b):return [json.loads(l) for l in b.splitlines() if l.strip()]
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',REF],cwd=ROOT,text=True).splitlines()
predpaths=[p for p in paths if p.startswith('finetune/results_v2/') and p.endswith('.jsonl')]
trains={}; trainmanifest={}
for arm in ['A_cpt','B_facts','C_answers','D_sql','BC_facts_answers','BD_facts_sql','D_sql_k0','D_sql_k5','D_sql_k25']:
 p='finetune/datasets/train_'+arm+'.jsonl'
 b=(ROOT/'review_training_2026-09-11/recovered_train_B_facts.jsonl').read_bytes() if arm=='B_facts' else git(p)
 trains[arm]=rows(b);trainmanifest[arm]={'source':p,'sha256':hashlib.sha256(b).hexdigest(),'rows':len(trains[arm]),'B_recovered_from_matching_BC_BD_prefix':arm=='B_facts'}
question_index={}; fact_index={}
for arm,rr in trains.items():
 qi=collections.defaultdict(list);fi=collections.defaultdict(list)
 for n,r in enumerate(rr,1):
  ms=r.get('messages',[]);us=[m['content'] for m in ms if m['role']=='user'];aa=[m['content'] for m in ms if m['role']=='assistant']
  if us:qi[us[-1]].append({'line':n,'target':aa[-1] if aa else None})
  if r.get('company') and r.get('attr'):fi[(r['company'],r['attr'])].append({'line':n,'gold_value':r.get('gold_value'),'target':aa[-1] if aa else None})
 question_index[arm]=qi;fact_index[arm]=fi
aggregates=collections.defaultdict(lambda: {'n':0,'correct_sum':0.0,'scored_n':0,'sql_errors':0,'exact_question_seen':0,'fact_pair_seen':0,'f1_sum':0.0,'f1_n':0})
mainrecords={};manifest=[]; allcount=0; triage=collections.Counter(); badparse=[]
fields=['condition','seed','probe','source_path','source_line','question','company','attribute','entity_split','family','stored_correct','stored_f1','sql_error','completion','answer','gold','gold_sql','exact_training_question','training_targets','factual_pair_in_training','factual_training_targets','triage']
factrows=collections.defaultdict(dict)
with (OUT/'all_questions.csv').open('w',newline='') as cf,(OUT/'all_predictions.jsonl').open('w') as jf:
 w=csv.DictWriter(cf,fieldnames=fields);w.writeheader()
 for pi,p in enumerate(predpaths):
  b=git(p);rr=rows(b);bits=p.split('/');seed=bits[2] if bits[2].startswith('seed') else 'original';arm=bits[-2];probe=Path(p).stem
  manifest.append({'path':p,'sha256':hashlib.sha256(b).hexdigest(),'records':len(rr)})
  for line,r in enumerate(rr,1):
   it=r['item'];q=it.get('question','');scores=r.get('scores',{});co=it.get('company','');attr=it.get('attr',''); gold=it.get('gold_value',it.get('gold_answer','')); correct=scores.get('correct');f1=scores.get('f1');sq=r.get('sql_error')
   tq=question_index.get(arm,{}).get(q,[]);tf=fact_index.get(arm,{}).get((co,attr),[]) if co and attr else []
   tags=[]
   if sq:tags.append('recorded_sql_execution_error')
   if correct is not None and correct<1:
    if tq:tags.append('stored_failure_despite_exact_training_question')
    if tf:tags.append('stored_failure_with_explicit_factual_supervision')
    if it.get('entity_split')=='heldout':tags.append('heldout_company_fact_not_memorization_test')
    if not tq and not tf:tags.append('no_exact_supervision_match_in_this_recipe')
   if arm in ['D_sql','BD_facts_sql','D_sql_k0','D_sql_k5','D_sql_k25','base_sql','base_sql_5shot','router','router_ft']:tags.append('SQL_or_routed_answer_not_closed_book_recall')
   if probe=='probe_42':tags.append('business_answer_requires_manual_completeness_check')
   for t in tags:triage[t]+=1
   result={'condition':arm,'seed':seed,'probe':probe,'source_path':p,'source_line':line,'question':q,'company':co,'attribute':attr,'entity_split':it.get('entity_split',''),'family':it.get('family',it.get('skill','')),'stored_correct':correct,'stored_f1':f1,'sql_error':sq,'completion':r.get('completion'),'answer':r.get('answer'),'gold':gold,'gold_sql':it.get('gold_sql'),'exact_training_question':bool(tq),'training_targets':tq,'factual_pair_in_training':bool(tf),'factual_training_targets':tf,'triage':tags}
   w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in result.items()})
   jf.write(json.dumps({'analysis':result,'original_record':r},ensure_ascii=False)+'\n');allcount+=1
   for dimension,value in [('probe',probe),('attribute',attr)] if attr else [('probe',probe)]:
    key=(seed,arm,dimension,value,it.get('entity_split','all'))
    a=aggregates[key];a['n']+=1;a['sql_errors']+=bool(sq);a['exact_question_seen']+=bool(tq);a['fact_pair_seen']+=bool(tf)
    if correct is not None:a['correct_sum']+=correct;a['scored_n']+=1
    if f1 is not None:a['f1_sum']+=f1;a['f1_n']+=1
   if seed=='original':
    mainrecords[(arm,probe,line)]=result
   if probe in ['probe_recall','probe_recall_paraphrase'] and co and attr:
    factrows[(seed,arm,co,attr)][probe]=result
  if pi%80==0:print(pi,len(predpaths),allcount,flush=True)
summary=[dict(zip(['seed','condition','dimension','value','entity_split'],k),**v) for k,v in aggregates.items()]
paraphrases=[]
for (seed,arm,co,attr),pair in factrows.items():
 if len(pair)!=2:continue
 x=pair['probe_recall'];y=pair['probe_recall_paraphrase']
 if x['gold']!=y['gold']:continue
 if x['stored_correct']!=y['stored_correct']:
  paraphrases.append({'seed':seed,'condition':arm,'company':co,'attribute':attr,'original':x,'paraphrase':y})
# Aligned six-arm answers for every original-run evaluation question.
mainarms=['A_cpt','B_facts','C_answers','D_sql','BC_facts_answers','BD_facts_sql']
comparison={}
for (arm,probe,line),r in mainrecords.items():
 if arm not in mainarms:continue
 k=(probe,r['question']);comparison.setdefault(k,{})[arm]=r
with (OUT/'six_variant_comparison.csv').open('w',newline='') as f:
 cols=['probe','question','gold','entity_split']+[a+'_'+v for a in mainarms for v in ['answer','completion','stored_correct','training_targets']]
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
 for (probe,q),arms in comparison.items():
  first=next(iter(arms.values()));o={'probe':probe,'question':q,'gold':first['gold'],'entity_split':first['entity_split']}
  for a,r in arms.items():
   for v in ['answer','completion','stored_correct','training_targets']:o[a+'_'+v]=json.dumps(r[v],ensure_ascii=False) if isinstance(r[v],list) else r[v]
  w.writerow(o)
(OUT/'summary.json').write_text(json.dumps({'prediction_files':len(manifest),'prediction_records':allcount,'aligned_original_questions':len(comparison),'triage':dict(triage),'aggregates':summary},indent=2)+'\n')
(OUT/'paraphrase_disagreements.json').write_text(json.dumps(paraphrases,indent=2,ensure_ascii=False)+'\n')
(OUT/'original_examples.json').write_text(json.dumps([r for r in mainrecords.values() if r['condition'] in mainarms and (r['probe']=='probe_42' or r['company'] in ['ACM Georgia LLC','Adient','ADVICS Manufacturing Georgia LLC'])],indent=2,ensure_ascii=False)+'\n')
(OUT/'INPUT_MANIFEST.json').write_text(json.dumps({'reference':subprocess.check_output(['git','rev-parse',REF],cwd=ROOT,text=True).strip(),'training':trainmanifest,'predictions':manifest,'interpretation':'Stored scores retained, not all independently regraded; exposure matches not causal diagnoses. Original and seed13 results are not assumed independent.'},indent=2)+'\n')
print('DONE',allcount,'records;',len(comparison),'aligned original questions;',len(paraphrases),'score disagreements',flush=True)
