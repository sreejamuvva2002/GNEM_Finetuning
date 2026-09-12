"""Read-only historical Git audit; writes derived evidence into this directory."""
import ast,csv,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
REF='v2-frozen-reference'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(path):return git('show',f'{REF}:{path}')
files=git('ls-tree','-r','--name-only',REF).decode().splitlines()
summary=[];curves=[]
for path in files:
 if not path.endswith('.train.log'):continue
 raw=blob(path);s=raw.decode(errors='replace');events=[]
 for m in re.finditer(r"\{[^{}\n\r]*\}",s):
  try:r=ast.literal_eval(m.group())
  except (ValueError,SyntaxError):continue
  if isinstance(r,dict)and ('loss'in r or 'train_loss'in r):
   r={k:float(v) if isinstance(v,(str,int,float)) and re.fullmatch(r'[-+\d.eE]+',str(v))else v for k,v in r.items()};events.append(r)
 meta={}
 for m in re.finditer(r'\{\s*"variant"\s*:',s):
  try:meta=json.JSONDecoder().raw_decode(s[m.start():])[0]
  except json.JSONDecodeError:pass
 history=[e for e in events if 'loss'in e];final=next((e for e in reversed(events)if 'train_loss'in e),{})
 step_pairs=[(int(a),int(b))for a,b in re.findall(r'(\d+)/(\d+)\s*\[',s)]
 # Progress bars for dataset processing may also occur; step total nearest the last training bar is used.
 steps=step_pairs[-1]if step_pairs else (None,None)
 row={'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'v2_run':'/run_v2_'in path,'smoke':'smoke'in path,'variant':meta.get('variant',Path(path).name.split('.')[0]),'seed_label':(re.search(r'\.seed(\d+)\.',path).group(1)if re.search(r'\.seed(\d+)\.',path)else 'unsuffixed'), 'completed':bool(final and meta),'has_train_summary':bool(final),'has_metadata':bool(meta),'logging_points':len(history),'first_loss':history[0]['loss']if history else None,'last_logged_loss':history[-1]['loss']if history else None,'last_logged_epoch':history[-1].get('epoch')if history else None,'last_grad_norm':history[-1].get('grad_norm')if history else None,'last_entropy':final.get('entropy',history[-1].get('entropy')if history else None),'last_token_accuracy':final.get('mean_token_accuracy',history[-1].get('mean_token_accuracy')if history else None),'train_loss':final.get('train_loss'),'train_runtime':final.get('train_runtime'),'final_epoch':final.get('epoch'),'last_progress_step':steps[0],'progress_total':steps[1],'eval_loss_present':'eval_loss'in s,'traceback':'Traceback (most recent call last)'in s,**{k:meta.get(k)for k in ['n_examples','epochs','lr','lora_r','max_length','peak_vram_gb','trained_at','git_commit','git_dirty','base_model_revision','dataset_sha256']}}
 ds=meta.get('dataset')
 if ds and 'finetune/datasets/'+ds in files:row['dataset_matches_frozen_reference']=hashlib.sha256(blob('finetune/datasets/'+ds)).hexdigest()==meta.get('dataset_sha256')
 row['error_tail']=s[-1000:]if not row['completed']else ''
 summary.append(row)
 for j,e in enumerate(history):curves.append({'path':path,'variant':row['variant'],'seed_label':row['seed_label'],'log_index':j+1,**e})
 if row['v2_run']:
  dst=OUT/'raw_logs'/Path(path).parent.name/Path(path).name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
for name,rs in [('runs',summary),('loss_history',curves)]:
 (OUT/f'{name}.json').write_text(json.dumps(rs,indent=2)+'\n')
 fields=list(dict.fromkeys(k for r in rs for k in r if k!='error_tail'))
 with (OUT/f'{name}.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rs)
for p in ['finetune/train_lora.py','finetune/variants.py','finetune/requirements.lock','finetune/validate/freeze_v2/training_config_v2.json']:
 dst=OUT/'historical_sources'/Path(p).name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(blob(p))
print('Logs',len(summary),'completed',sum(r['completed']for r in summary),'v2 completed',sum(r['completed']and r['v2_run']for r in summary))
for r in summary:
 if r['v2_run']:print(r['path'].split('/')[-2:], 'complete',r['completed'],'loss',r['first_loss'],r['last_logged_loss'],r['train_loss'],'accuracy',r['last_token_accuracy'],'steps',r['last_progress_step'],r['progress_total'],'data_match',r.get('dataset_matches_frozen_reference'))
