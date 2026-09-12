"""Reload every smoke adapter and verify finite, nonzero updates and stable logits."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'finetune'))
from train_v3 import MODEL,REVISION,FILES

def main():
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import PeftModel
    from safetensors.torch import load_file
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,local_files_only=True)
    base=AutoModelForCausalLM.from_pretrained(MODEL,revision=REVISION,local_files_only=True,
        torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa').eval()
    encoded=tok('The dataset records employment of',return_tensors='pt').to(base.device)
    with torch.inference_mode():reference=base(**encoded).logits[:,-1].float().cpu()
    report={}
    for variant in ('D_sql',):
        directory=ROOT/'validation_v3/rehearsal_models'/f'{variant}.seed61'
        metric=json.loads((directory/'METRICS.json').read_text());assert metric['global_step']==6
        state=json.loads((directory/'trainer_state.json').read_text())
        losses=[x['eval_loss'] for x in state['log_history'] if 'eval_loss' in x]
        assert len(losses)>=3 and metric['eval']['eval_loss']==min(losses)
        chosen=Path(metric['best_model_checkpoint'])/'adapter_model.safetensors'
        selected=directory/'selected_adapter/adapter_model.safetensors'
        chosen_tensors=load_file(chosen); selected_tensors=load_file(selected)
        assert chosen_tensors.keys()==selected_tensors.keys()
        assert all(torch.equal(chosen_tensors[k],selected_tensors[k]) for k in chosen_tensors)
        adapter=directory/'selected_adapter';path=adapter/'adapter_model.safetensors'
        tensors=load_file(path);b=[v for k,v in tensors.items() if 'lora_B' in k]
        assert b and all(torch.isfinite(v).all() for v in tensors.values())
        assert all(torch.count_nonzero(v)>0 for v in b),'Unchanged zero-initialized LoRA B'
        model=PeftModel.from_pretrained(base,adapter,is_trainable=False).eval()
        with torch.inference_mode():first=model(**encoded).logits[:,-1].float().cpu()
        difference=(first-reference).abs().max().item()
        assert difference>0 and torch.isfinite(first).all()
        base=model.unload().eval()
        model=PeftModel.from_pretrained(base,adapter,is_trainable=False).eval()
        with torch.inference_mode():second=model(**encoded).logits[:,-1].float().cpu()
        assert torch.equal(first,second),'Checkpoint reload changed deterministic logits'
        base=model.unload().eval()
        report[variant]={'adapter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'all_tensors_finite':True,'all_lora_B_updated':True,'max_logit_difference_from_base':difference,
            'reload_logits_identical':True,'optimizer_steps':6,'selected_matches_best_checkpoint':True,'epoch_evaluation_losses':losses}
        print(variant,'PASS',difference,flush=True)
    (ROOT/'validation_v3/resumption/REHEARSAL_RELOAD_A002.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
