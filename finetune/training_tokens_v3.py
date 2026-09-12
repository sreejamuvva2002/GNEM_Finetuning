"""Shared trainer/budget preprocessing: no truncation; explicit assistant masks."""
from pathlib import Path
TEMPLATE=(Path(__file__).resolve().parent/'templates/qwen_a002.jinja').read_text()
MAX_SEQUENCE_LENGTH=1024

def encode_chat(tok, messages, max_length=MAX_SEQUENCE_LENGTH):
    if [m['role'] for m in messages] != ['system','user','assistant']:
        raise ValueError('Training contract requires system/user/assistant turns')
    if any(not isinstance(m['content'],str) or not m['content'] for m in messages):
        raise ValueError('Empty or invalid training message')
    original=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=False)
    rendered=tok.apply_chat_template(messages,chat_template=TEMPLATE,tokenize=False,add_generation_prompt=False)
    if original != rendered:
        raise ValueError('Training template changed the pinned model-visible text')
    encoded=tok.apply_chat_template(messages,chat_template=TEMPLATE,tokenize=True,
                                   add_generation_prompt=False,return_dict=True,
                                   return_assistant_tokens_mask=True)
    ids=list(encoded['input_ids']); mask=list(encoded['assistant_masks'])
    if len(ids)!=len(mask) or len(ids)>max_length:
        raise ValueError(f'Invalid mask or sequence exceeds {max_length}: {len(ids)}')
    labels=[t if m else -100 for t,m in zip(ids,mask)]
    if not any(m for m in mask[1:]): raise ValueError('Zero assistant supervision')
    return {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':labels}

def supervised_tokens(encoded):
    return sum(t != -100 for t in encoded['labels'][1:])
