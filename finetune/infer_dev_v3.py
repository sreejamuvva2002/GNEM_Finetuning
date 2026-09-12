"""Real development-only inference. No option accepts protected test input paths."""
import argparse,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
ROOT=Path(__file__).resolve().parent.parent
import grade_v3 as G
import sqlexec_v3 as X
from answer_parser_v3 import grade_answer,VERSION
from eval_records_v3 import EvalRecord
from context_renderer_v3 import build_ctx_oracle_prompt

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--condition',choices=['base','base_ctx_oracle','base_sql','base_sql_5shot'],required=True)
    parser.add_argument('--micro',action='store_true');parser.add_argument('--run-id',default='initial');args=parser.parse_args()
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    out=ROOT/'results_v3'/('micro' if args.micro else 'dev')/args.condition/args.run_id
    out.mkdir(parents=True,exist_ok=True)
    resultpath=out/'predictions.jsonl'
    if resultpath.exists():raise RuntimeError('Refusing to overwrite predictions')
    prompts=json.loads((ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    inputs=json.loads((ROOT/'datasets_v3/EVALUATION_INPUT_MANIFEST_A002.json').read_text())
    files=['dev_fact_v3.jsonl'] if args.condition=='base_ctx_oracle' else (['dev_structured_v3.jsonl'] if 'sql' in args.condition else ['dev_fact_v3.jsonl','dev_structured_v3.jsonl'])
    rows=[]
    for name in files:
        path=ROOT/'datasets_v3'/name
        assert inputs['classification'][name]=='dev' and sha(path)==inputs['sha256'][name]
        part=[json.loads(l) for l in path.read_text().splitlines()]
        # Micro needs varied attributes, not just the first record's category.
        rows.extend(part[:15] if args.micro else part)
    few=json.loads((ROOT/'datasets_v3/FEWSHOT_MANIFEST_v3.json').read_text())['examples']
    catalogue_path=ROOT/'datasets_v3/RUNTIME_VALUE_CATALOGUE_A002.json'
    assert sha(catalogue_path)==prompts['runtime_catalogue_sha256']
    catalogue=catalogue_path.read_text()
    tok=AutoTokenizer.from_pretrained(prompts['model_id'],revision=prompts['model_revision'],local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(prompts['model_id'],revision=prompts['model_revision'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
    model.generation_config.do_sample=False
    metadata={'condition':args.condition,'development_only':True,'micro_only':args.micro,'expected_count':len(rows),
              'input_hashes':{name:inputs['sha256'][name] for name in files},'prompt_sha256':sha(ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json'),
              'model_revision':prompts['model_revision'],'runner_sha256':sha(__file__),
              'parser_sha256':sha(ROOT/'finetune/answer_parser_v3.py'),'note':'Conservative parser scores; semantic equivalents may require separately reported adjudication.'}
    (out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    summaries=[]
    with resultpath.open('x') as f:
        for item in rows:
            if args.condition=='base_ctx_oracle':messages=build_ctx_oracle_prompt('train_dev_kb',item['row_id'],item['question'])
            else:
                sqlmode='sql' in args.condition
                messages=[{'role':'system','content':prompts['sql_system' if sqlmode else 'closed_book_system'] + ('\nRecorded vocabulary (not supplier relationships):\n'+catalogue if sqlmode else '')}]
                if args.condition=='base_sql_5shot':
                    for t in few:messages.extend([{'role':'user','content':t['question']},{'role':'assistant','content':t['gold_sql']}])
                messages.append({'role':'user','content':item['question']})
            if 'sql' not in args.condition:
                messages[-1]['content'] += '\n'+prompts['output_instructions'][item['answer_type']]
            text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            encoded=tok(text,return_tensors='pt',add_special_tokens=False).to(model.device)
            if encoded.input_ids.shape[1]+1024>prompts['max_context']:raise RuntimeError('Prompt exceeds context budget')
            started=time.monotonic()
            with torch.inference_mode():generated=model.generate(**encoded,max_new_tokens=1024,do_sample=False,pad_token_id=tok.eos_token_id)
            ids=generated[0,encoded.input_ids.shape[1]:];raw=tok.decode(ids,skip_special_tokens=True)
            truncated=len(ids)>=1024 and int(ids[-1])!=tok.eos_token_id
            execution=None
            if 'sql' in args.condition:
                result=G.grade_structured(item,raw,item['gold_sql'],'train_dev_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite',stopped_at_max_new_tokens=truncated)
                parsed=raw
                if result.status in {'correct','incorrect'}:
                    q=X.run_sql(raw,'train_dev_kb',db_path=ROOT/'datasets_v3/gnem_v3.sqlite');execution=[list(r) for r in q.rows]
                grader=G.GRADER_VERSION;graderpath=ROOT/'finetune/grade_v3.py'
            else:
                result,parsed=grade_answer(raw,item,truncated);grader=VERSION;graderpath=ROOT/'finetune/answer_parser_v3.py'
            record=EvalRecord(example_id=item['example_id'],family=item['family'],condition=args.condition,question=item['question'],
                raw_output=raw,parsed_output=json.dumps(parsed,ensure_ascii=False) if parsed is not None else None,
                generated_sql=raw if 'sql' in args.condition else None,execution_result=execution,gold=item['gold_value'],
                answer_type=item['answer_type'],target_columns=item.get('target_columns'),
                task_result_correctness=result.task_result_correctness,strict_result_schema_accuracy=result.strict_result_schema_accuracy,
                status=result.status,error_type=None if result.status=='correct' else result.status,error_detail=result.detail,
                prompt_hash=hashlib.sha256(text.encode()).hexdigest(),adapter_hash=None,seed=None,grader_version=grader,grader_sha256=sha(graderpath))
            value=record.to_dict();value.update(elapsed_seconds=time.monotonic()-started,input_tokens=encoded.input_ids.shape[1],output_tokens=len(ids),
                stopped_at_max_new_tokens=truncated,metrics=result.metrics,messages=messages)
            f.write(json.dumps(value,ensure_ascii=False)+'\n');f.flush();summaries.append(value)
            print(item['example_id'],result.status,flush=True)
    assert len(summaries)==len(rows)
    summary={'count':len(rows),'correct':sum(r['status']=='correct' for r in summaries),'status_counts':{s:sum(r['status']==s for r in summaries) for s in G.STATUSES},'prediction_sha256':sha(resultpath)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
