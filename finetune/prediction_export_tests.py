import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prediction_export_v3 as E
import final_eval_v3 as F

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'datasets_v3').mkdir()
        (self.root/'finetune').mkdir()
        (self.root/'datasets_v3/PROMPT_TEMPLATES_A002.json').write_text('{"model_revision":"fixture"}')
        (self.root/'finetune/structured_prompt_v3.py').write_text('fixture')
        self.row = dict(example_id='x', question='Example?', condition='base', seed=None,
                        rendered_prompt='Actual prompt', raw_output='', stopped_at_max_new_tokens=False)
    def export(self, rows=None, **kwargs):
        return E.export_predictions(self.root, self.root/'out', rows or [self.row],
                    expected_ids=['x'], model_revision='fixture', **kwargs)
    def test_base_roundtrip_and_no_overwrite(self):
        reg = self.export(model_kind='base')
        p = self.root/'out/predictions.jsonl'
        with patch.object(F, 'ROOT', self.root):
            F.validate_prediction_identities(reg, p, F.load(p))
        self.assertIs(reg['approved'], False)
        with self.assertRaises(FileExistsError): self.export(model_kind='base')
    def test_adapter_roundtrip_and_drift(self):
        (self.root/'adapter.safetensors').write_bytes(b'fixture')
        reg = self.export(model_kind='adapter', adapter_path='adapter.safetensors')
        p = self.root/'out/predictions.jsonl'
        with patch.object(F, 'ROOT', self.root):
            F.validate_prediction_identities(reg, p, F.load(p))
            (self.root/'adapter.safetensors').write_bytes(b'drift')
            with self.assertRaises(RuntimeError): F.validate_prediction_identities(reg,p,F.load(p))
    def test_bad_prompt_and_duplicate_ids_leave_no_export(self):
        for rows in ([{**self.row,'prompt_hash':'a'*64}], [self.row,self.row]):
            with self.assertRaises(ValueError): self.export(rows, model_kind='base')
            self.assertFalse((self.root/'out').exists())
    def test_bad_identity_rejected(self):
        with self.assertRaises(ValueError): self.export(model_kind='base', adapter_path='anything')
        with self.assertRaises(ValueError): self.export(model_kind='adapter', adapter_path='../outside')

if __name__ == '__main__': unittest.main(verbosity=2)
