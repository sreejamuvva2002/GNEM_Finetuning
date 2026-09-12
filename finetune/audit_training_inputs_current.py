"""Actual post-preprocessing label budgets for every current training recipe."""
import json,hashlib
from pathlib import Path
from phase10_build_a_cpt import load_real_tokenizer
from train_v3 import FILES
from training_tokens_v3 import encode_chat,pack_cpt_stream,supervised_tokens
ROOT=Path(__file__).resolve().parent.parent
def main():
    tok,_=load_real_tokenizer();report={}
    for variant,name in FILES.items():
        p=ROOT/'datasets_v3'/name;rows=list(map(json.loads,p.read_text().splitlines()))
        if variant=='A_cpt':
            stream=[]
            for r in rows:stream+=tok(r['text'],add_special_tokens=False)['input_ids']+[tok.eos_token_id]
            encoded=pack_cpt_stream(stream)
        else:encoded=[encode_chat(tok,r['messages']) for r in rows]
        report[variant]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_rows':len(rows),'training_sequences':len(encoded),'shifted_supervised_tokens':sum(supervised_tokens(r) for r in encoded),'max_sequence_length':max(len(r['input_ids']) for r in encoded),'configured_single_device_steps':(4 if variant=='A_cpt' else 3)*((len(encoded)+7)//8)}
    path=ROOT/'validation_v3/resumption/TRAINING_LABEL_AUDIT_CURRENT.json'
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
