"""Local basic regression screen; never a broad competence/forgetting claim."""
import json,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from answer_parser_v3 import normalize
    source=ROOT/'datasets_v3/general_capability_sanity_v3.jsonl'
    rows=list(map(json.loads,source.read_text().splitlines()))
    out=ROOT/'results_v3/dev/general_sanity_base_r3';out.mkdir(parents=True,exist_ok=False)
    p=json.loads((ROOT/'datasets_v3/PROMPT_TEMPLATES_A002.json').read_text())
    tok=AutoTokenizer.from_pretrained(p['model_id'],revision=p['model_revision'],local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(p['model_id'],revision=p['model_revision'],local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
    model.generation_config.do_sample=False;result=[]
    for r in rows:
        messages=[{'role':'user','content':r['question']}];text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        enc=tok(text,return_tensors='pt',add_special_tokens=False).to(model.device)
        with torch.inference_mode():ids=model.generate(**enc,max_new_tokens=128,do_sample=False,pad_token_id=tok.eos_token_id)[0,enc.input_ids.shape[1]:]
        raw=tok.decode(ids,skip_special_tokens=True);truncated=len(ids)>=128 and int(ids[-1])!=tok.eos_token_id
        result.append({**r,'raw_output':raw,'correct':not truncated and normalize(raw)==normalize(r['gold_value']),'truncated':truncated,'messages':messages})
    (out/'predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in result))
    report={'model_revision':p['model_revision'],'input_sha256':sha(source),'runner_sha256':sha(__file__),'predictions_sha256':sha(out/'predictions.jsonl'),'n':len(result),'correct':sum(r['correct'] for r in result),'limitation':'Basic floor screen only; requires matched post-training evaluation and broader tasks to assess forgetting.'}
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
