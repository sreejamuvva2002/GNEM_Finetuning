import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import final_eval_v3 as F
from generation_core_v3 import generate_and_export
from generation_core_v3 import generate_records

class Backend:
    eos_token_ids = {9, 10}
    def render(self, messages): return str(messages)
    def encode(self, text): return [1, 2]
    def generate(self, ids, limit): return self.outputs
    def decode(self, ids): return str(ids)

class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.backend.outputs = [3, 9]
        self.item = {'example_id':'x','question':'Which company?', 'answer_type':'scalar',
                     'gold_value':'SECRET_GOLD', 'gold_sql':'SECRET_SQL'}
        self.config = {'decoding':{'do_sample':False,'max_new_tokens':2},
                       'max_context':10,'closed_book_system':'Answer from memory.'}
    def run_records(self, items=None):
        return generate_records(items or [self.item], self.backend, prompt_config=self.config,
                                condition='base',seed=None)
    def test_prompt_excludes_gold_and_retains_tokens(self):
        row = self.run_records()[0]
        self.assertNotIn('SECRET',row['rendered_prompt'])
        self.assertEqual(row['input_token_ids'],[1,2])
        self.assertEqual(row['output_token_ids'],[3,9])
        self.assertFalse(row['stopped_at_max_new_tokens'])
    def test_truncation_and_alternative_eos(self):
        for tokens, truncated in [([3,4],True),([3,10],False),([],False)]:
            self.backend.outputs = tokens
            self.assertEqual(self.run_records()[0]['stopped_at_max_new_tokens'],truncated)
    def test_context_and_duplicate_refusal(self):
        with self.assertRaises(ValueError): self.run_records([self.item,self.item])
        self.config['max_context']=3
        with self.assertRaises(ValueError): self.run_records()
    def test_generation_export_evaluator_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'datasets_v3').mkdir();(root/'finetune').mkdir()
            self.config['model_revision']='fixture'
            (root/'datasets_v3/PROMPT_TEMPLATES_A002.json').write_text(json.dumps(self.config))
            (root/'finetune/structured_prompt_v3.py').write_text('fixture')
            self.backend.runtime={'fixture':True}
            reg=generate_and_export(root,root/'out',[self.item],self.backend,
                prompt_config=self.config,condition='base',seed=None,model_kind='base')
            with patch.object(F,'ROOT',root):
                p=root/'out/predictions.jsonl'
                F.validate_prediction_identities(reg,p,F.load(p))
            self.assertIn('out/runtime.json',reg['sha256'])
    def test_backend_budget_violation(self):
        self.backend.outputs=[1,2,3]
        with self.assertRaises(ValueError): self.run_records()

if __name__=='__main__': unittest.main(verbosity=2)
