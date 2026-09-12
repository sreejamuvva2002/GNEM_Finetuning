import subprocess,json,hashlib
from pathlib import Path
from transformers import AutoTokenizer
OUT=Path(__file__).resolve().parent
REF='v2-frozen-reference'
tok=AutoTokenizer.from_pretrained('Qwen/Qwen2.5-14B-Instruct',revision='cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8',local_files_only=True)
summary=[]
for name in ['B_facts','D_sql','D_sql_k0','D_sql_k5','D_sql_k25','BD_facts_sql','C_answers','BC_facts_answers','A_cpt']:
 raw=subprocess.check_output(['git','show',f'{REF}:finetune/datasets/train_{name}.jsonl']);rows=[];errors=[]
 for no,line in enumerate(raw.splitlines(),1):
  try:rows.append(json.loads(line))
  except json.JSONDecodeError as e:errors.append({'line':no,'error':str(e)})
 stats=[]
 for r in rows:
  if 'messages'in r:
   ms=r['messages'];pre=tok.apply_chat_template(ms[:-1],tokenize=True,add_generation_prompt=True,return_dict=False);full=tok.apply_chat_template(ms,tokenize=True,add_generation_prompt=False,return_dict=False)
  else:pre=[];full=tok(r['text'],add_special_tokens=False)['input_ids']
  stats.append({'prompt':len(pre),'full':len(full),'retained_answer_right':max(0,min(1024,len(full))-len(pre)),'answer_tokens':len(full)-len(pre),'prefix_matches':full[:len(pre)]==pre})
 s={'variant':name,'parsed_rows':len(rows),'parse_errors':errors,'dataset_sha256':hashlib.sha256(raw).hexdigest(),'prompt_min':min(x['prompt']for x in stats),'prompt_max':max(x['prompt']for x in stats),'full_min':min(x['full']for x in stats),'full_max':max(x['full']for x in stats),'over_1024':sum(x['full']>1024 for x in stats),'zero_answer_after_right_cut':sum(x['retained_answer_right']==0 for x in stats),'raw_answer_tokens':sum(x['answer_tokens']for x in stats),'retained_answer_tokens':sum(x['retained_answer_right']for x in stats),'nonprefix':sum(not x['prefix_matches']for x in stats)}
 summary.append(s);(OUT/f'token_lengths_{name}.json').write_text(json.dumps(stats,indent=2)+'\n');print(s,flush=True)
(OUT/'token_length_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
