"""Development-only real-model micro battery across SQL result shapes."""
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'finetune'))
import grade_v3 as G
import sqlexec_v3 as X

def main():
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    out=ROOT/'results_v3/micro/runtime_battery_A002';out.mkdir(parents=True,exist_ok=True)
    if (out/'predictions.jsonl').exists():raise RuntimeError('Do not overwrite predictions')
    cases=[
      {'example_id':'MICRO_COUNT','question':'How many distinct companies are recorded?',
       'gold_sql':'SELECT COUNT(DISTINCT company) AS n FROM companies','answer_type':'scalar','target_columns':['n']},
      {'example_id':'MICRO_TOPK','question':'Return the three company names that come first alphabetically, using distinct company names.',
       'gold_sql':'SELECT DISTINCT company FROM companies ORDER BY company LIMIT 3','answer_type':'top_k','target_columns':['company']},
      {'example_id':'MICRO_EMPTY','question':'List companies whose name is exactly GNEM nonexistent runtime fixture.',
       'gold_sql':"SELECT company FROM companies WHERE company='GNEM nonexistent runtime fixture'",'answer_type':'set','target_columns':['company']},
      {'example_id':'MICRO_COMPOSITION','question':'List companies with a recorded CNC Machining process and a recorded ISO 9001 certification, allowing observations across records of the same company.',
       'gold_sql':"SELECT DISTINCT c.company FROM companies c JOIN processes p ON p.company=c.company JOIN certifications s ON s.company=c.company WHERE p.process='CNC Machining' AND s.standard_family='ISO 9001' ORDER BY c.company",'answer_type':'set','target_columns':['company']},
      {'example_id':'MICRO_GROUP','question':'For each recorded category, return category and the number of distinct companies as n. Sort by category.',
       'gold_sql':'SELECT category, COUNT(DISTINCT company) AS n FROM companies GROUP BY category ORDER BY category','answer_type':'set','target_columns':['category','n']},
      {'example_id':'MICRO_MULTI','question':'First count distinct companies as n. Then list distinct category values. Return one SQL statement for each part, in that order.',
       'gold_sql':{'count':'SELECT COUNT(DISTINCT company) AS n FROM companies','categories':'SELECT DISTINCT category FROM companies ORDER BY category'},
       'answer_type':'multi_part','target_columns':['n','category'],
       'parts':[{'part_id':'count','answer_type':'scalar','target_columns':['n']},{'part_id':'categories','answer_type':'set','target_columns':['category']}]}
    ]
    p=json.loads((ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    tok=AutoTokenizer.from_pretrained(p['model_id'],revision=p['model_revision'],local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(p['model_id'],revision=p['model_revision'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
    model.generation_config.do_sample=False
    report=[]
    with (out/'predictions.jsonl').open('x') as f:
        for item in cases:
            gold={}
            for key,sql in (item['gold_sql'].items() if isinstance(item['gold_sql'],dict) else [('answer',item['gold_sql'])]):
                r=X.run_sql(sql,'train_dev_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite')
                gold[key]={'columns':r.columns,'rows':r.rows}
            # Gold self-score verifies the complete executor/grader branch first.
            gold_text='; '.join(item['gold_sql'].values()) if isinstance(item['gold_sql'],dict) else item['gold_sql']
            assert G.grade_structured(item,gold_text,item['gold_sql'],'train_dev_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite').status=='correct'
            system=p['sql_system']
            if item['answer_type']=='multi_part':system=system.replace('a single read-only SQL SELECT query','read-only SQL SELECT queries').replace('exactly one SQL SELECT statement','one SQL SELECT statement per requested part, in order')
            messages=[{'role':'system','content':system},{'role':'user','content':item['question']}]
            text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            encoded=tok(text,return_tensors='pt',add_special_tokens=False).to(model.device)
            with torch.inference_mode():generated=model.generate(**encoded,max_new_tokens=1024,do_sample=False,pad_token_id=tok.eos_token_id)
            ids=generated[0,encoded.input_ids.shape[1]:];raw=tok.decode(ids,skip_special_tokens=True)
            truncated=len(ids)>=1024 and int(ids[-1])!=tok.eos_token_id
            result=G.grade_structured(item,raw,item['gold_sql'],'train_dev_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite',stopped_at_max_new_tokens=truncated)
            row={'item':item,'raw_output':raw,'gold_results':gold,'status':result.status,'task_result_correctness':result.task_result_correctness,
                'strict_result_schema_accuracy':result.strict_result_schema_accuracy,'detail':result.detail,'metrics':result.metrics,
                'prompt':messages,'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'output_tokens':len(ids),'truncated':truncated,'scope':'train_dev_kb'}
            f.write(json.dumps(row)+'\n');f.flush();report.append(row);print(item['example_id'],result.status,flush=True)
    (out/'SUMMARY.json').write_text(json.dumps({'count':len(report),'statuses':{r['item']['example_id']:r['status'] for r in report},
        'gold_self_checks_passed':len(report),'development_micro_only':True,'model_revision':p['model_revision'],'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
