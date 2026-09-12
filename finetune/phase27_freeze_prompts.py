"""Freeze prompts and a small general-capability regression screen before inference."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import kb_v3 as K
import holdout_v3 as H
from phase11_build_b_facts import CLOSED_BOOK_SYSTEM
from phase14_build_d_sql import SQL_SYSTEM
from context_renderer_v3 import SYSTEM_PROMPT as CONTEXT_SYSTEM
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'datasets_v3'

def main():
    manifest=json.loads((OUT/'EVALUATION_INPUT_MANIFEST_A002.json').read_text())
    for name,sha in manifest['sha256'].items():assert H.sha256_file(OUT/name)==sha
    few=json.loads((OUT/'FEWSHOT_CANDIDATES_A002.json').read_text())
    reg=H.load_registry()
    assert len(few)==5 and all(t['split']=='train' for t in few)
    for t in few:
        assert not H.operation_families_present(t['gold_sql'])
        H.assert_composition_scan_verified(H.scan_compositions([t['fields_used']],reg))
    # Shared runtime catalogue contains vocabulary only, no company-to-fact mapping.
    catalogue_fields=('category','industry_group','primary_facility_type','ev_supply_chain_role',
                      'supplier_or_affiliation_type','ev_battery_relevant','classification_method',
                      'city','county','processes','services','certifications')
    catalogue={}
    for field in catalogue_fields:
        values=set()
        for row in K.load_kb('full_kb'):
            value=getattr(row,field)
            if field in H.MULTIVALUED:values.update(H.terms(value,field))
            elif value is not None:values.add(str(value))
        catalogue[field]=sorted(values)
    (OUT/'RUNTIME_VALUE_CATALOGUE_A002.json').write_text(json.dumps(catalogue,indent=2,ensure_ascii=False)+'\n')
    templates={'model_revision' :'cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8',
        'model_id':'Qwen/Qwen2.5-14B-Instruct','closed_book_system':CLOSED_BOOK_SYSTEM,
        'sql_system':SQL_SYSTEM,'context_system':CONTEXT_SYSTEM,
        'decoding':{'do_sample':False,'max_new_tokens':1024},
        'max_context':32768,'training_max_sequence_length':1024,
        'output_instructions':{'scalar':'Return only one JSON string or number containing the recorded value. For missing evidence, return its recorded sentinel. Do not include explanatory prose.',
          'set':'Return only a JSON array containing every requested value. Use an empty array if no record matches. Do not include explanatory prose.',
          'top_k':'Return only a JSON array of rows in the requested order. Do not include explanatory prose.'},
        'runtime_catalogue_sha256':H.sha256_file(OUT/'RUNTIME_VALUE_CATALOGUE_A002.json'),
        'runtime_catalogue_scope':'Full source vocabulary; SQL conditions only; no company-to-value associations',
        'training_template_sha256':H.sha256_file(ROOT/'finetune/templates/qwen_a002.jinja'),
        'note':'Information access differs explicitly: model-only, oracle record context, or SQL execution. No outcomes used.'}
    sanity=[]
    for i in range(10):
        a,b=i+2,i+7
        sanity.append({'example_id':f'SANITY_ADD_{i}','question':f'What is {a} + {b}? Answer with the number only.','gold_value':str(a+b),'family':'general_sanity'})
    for i,word in enumerate(('battery','supplier','Georgia','process','service','company','record','factory','material','quality')):
        sanity.append({'example_id':f'SANITY_COPY_{i}','question':f'Repeat this word exactly: {word}','gold_value':word,'family':'general_sanity'})
    for i,(a,b) in enumerate(((2,3),(9,4),(1,8),(7,6),(11,2),(5,12),(20,3),(8,13),(15,4),(6,14))):
        sanity.append({'example_id':f'SANITY_MAX_{i}','question':f'Which number is larger, {a} or {b}? Answer with that number only.','gold_value':str(max(a,b)),'family':'general_sanity'})
    assert len(sanity)==30
    (OUT/'general_capability_sanity_v3.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sanity))
    (OUT/'PROMPT_TEMPLATES_A002.json').write_text(json.dumps(templates,indent=2,sort_keys=True)+'\n')
    fm={'source':'STRUCTURED_TASK_POOL_v3.jsonl','source_sha256':H.sha256_file(OUT/'STRUCTURED_TASK_POOL_v3.jsonl'),
        'examples':few,'task_ids':[r['task_id'] for r in few],
        'prompt_sha256':H.sha256_file(OUT/'PROMPT_TEMPLATES_A002.json'),
        'sanity_sha256':H.sha256_file(OUT/'general_capability_sanity_v3.jsonl'),
        'sanity_limit':'A basic 30-item regression screen, not a broad general-capability benchmark'}
    (OUT/'FEWSHOT_MANIFEST_v3.json').write_text(json.dumps(fm,indent=2,sort_keys=True)+'\n')
    print('PASS: frozen prompts, five reserved training few-shots and 30-item sanity screen.')
if __name__=='__main__':main()
