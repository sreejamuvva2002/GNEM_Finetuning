"""CPU-only reconstruction of documented TRL 1.9.2 assistant labels; no model execution."""
import hashlib,json,subprocess
from pathlib import Path
from transformers import AutoTokenizer
OUT=Path(__file__).resolve().parent
tok=AutoTokenizer.from_pretrained('Qwen/Qwen2.5-14B-Instruct',revision='cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8',local_files_only=True)
assert tok.chat_template==(OUT/'library_sources/qwen2_5.jinja').read_text()
template=(OUT/'library_sources/qwen2_5_training.jinja').read_text();results=[]
for name in ['B_facts','C_answers','D_sql','BC_facts_answers','BD_facts_sql','D_sql_k0','D_sql_k5','D_sql_k25']:
 raw=(OUT/'recovered_train_B_facts.jsonl').read_bytes()if name=='B_facts'else subprocess.check_output(['git','show',f'v2-frozen-reference:finetune/datasets/train_{name}.jsonl'])
 rows=[json.loads(l)for l in raw.splitlines()];retained=[];zero=[];details=[];before=after=content_before=content_after=0;changed_render=0
 for i,r in enumerate(rows):
  ms=r['messages'];o=tok.apply_chat_template(ms,chat_template=template,tokenize=True,return_dict=True,return_assistant_tokens_mask=True)
  ids=o['input_ids'];mask=o['assistant_masks'];labels=[t if m else -100 for t,m in zip(ids,mask)]
  plain=tok.apply_chat_template(ms,tokenize=True,return_dict=False)
  changed_render+=ids!=plain
  n=sum(v!=-100 for v in labels[1:]);cl=labels[:1024];a=sum(v!=-100 for v in cl[1:]);before+=n;after+=a
  spans=[j for j,m in enumerate(mask)if m]; details.append({'row_index':i,'full_tokens':len(ids),'first_supervised_index':spans[0]if spans else None,'supervised_before':n,'supervised_after':a,'dropped':not any(v!=-100 for v in cl)})
  if not any(v!=-100 for v in cl):zero.append(i)
  else:retained.append({'input_ids':ids[:1024],'labels':cl})
 s={'variant':name,'source_sha256':hashlib.sha256(raw).hexdigest(),'input_rows':len(rows),'retained_rows':len(retained),'dropped_rows':len(zero),'dropped_row_indices':zero,'supervised_tokens_before':before,'supervised_tokens_after':after,'training_template_changes_token_sequence':changed_render,'retained_input_tokens':sum(len(r['input_ids'])for r in retained),'retained_input_labels_sha256':hashlib.sha256(json.dumps(retained,separators=(',',':')).encode()).hexdigest(),'expected_optimizer_steps_batch1_accum8_epochs3':((len(retained)+7)//8)*3}
 results.append(s);(OUT/f'mask_details_{name}.json').write_text(json.dumps(details,indent=2)+'\n');print(s,flush=True)
(OUT/'mask_reconstruction_summary.json').write_text(json.dumps(results,indent=2)+'\n')
