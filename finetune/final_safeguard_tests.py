import unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
import final_eval_v3 as F
from final_contract_v3 import grade_final_answer
class Safeguards(unittest.TestCase):
    def test_duplicate_membership_format_separated(self):
        for item,text in [({'answer_type':'set','gold_value':['A','B']},'["A","A","B"]'),({'answer_type':'set','gold_value':{'columns':['x','n'],'rows':[['A',1],['B',2]]}},'[["A",1],["A",1],["B",2]]')]:
            g,_=grade_final_answer(text,item)
            self.assertEqual(g.task_result_correctness,1);self.assertEqual(g.strict_result_schema_accuracy,0)
            self.assertFalse(g.metrics['output_contract_compliant']);self.assertEqual(g.metrics['duplicate_rows'],1)
    def test_extra_multipart_key_cannot_regain_format_credit(self):
        item={'answer_type':'multi_part','parts':[{'part_id':'a','answer_type':'scalar'}],'gold_value':{'a':1}}
        g,_=grade_final_answer('{"a":1,"extra":2}',item)
        self.assertEqual(g.task_result_correctness,0)
        self.assertEqual(g.strict_result_schema_accuracy,0)
        self.assertFalse(g.metrics['output_contract_compliant'])
    def test_null_and_literal_none_are_distinct_rows(self):
        item={'answer_type':'set','gold_value':{'columns':['x','y'],'rows':[[None,1],['None',1]]}}
        g,_=grade_final_answer('[[null,1],["None",1]]',item)
        self.assertEqual(g.task_result_correctness,1)
        self.assertEqual(g.strict_result_schema_accuracy,1)
        self.assertTrue(g.metrics['output_contract_compliant'])
        self.assertEqual(g.metrics['duplicate_rows'],0)
    def test_wrong_members_and_rank_duplicates_fail(self):
        for item,text in [({'answer_type':'set','gold_value':['A']},'["A","B"]'),({'answer_type':'top_k','gold_value':{'columns':['x'],'rows':[['A'],['B']]}},'[["A"],["A"],["B"]]')]:
            g,_=grade_final_answer(text,item);self.assertEqual(g.task_result_correctness,0)
    def test_extra_sql_rejected_before_execution(self):
        item={'example_id':'x','family':'synthetic','question':'Return two parts','answer_type':'multi_part','parts':[{'part_id':'a','answer_type':'scalar','target_columns':['n']},{'part_id':'b','answer_type':'scalar','target_columns':['n']}],'gold_sql':{'a':'SELECT 1 AS n','b':'SELECT 2 AS n'},'gold_value':{'a':1,'b':2}}
        pred={'example_id':'x','question':item['question'],'condition':'fixture','seed':61,'raw_output':'SELECT 1; SELECT 2; SELECT 3','prompt_hash':'a'*64}
        with patch.object(F.G,'grade_structured',side_effect=AssertionError('Must not execute')):
            records,_,_=F.grade_run([item],[pred],condition='fixture',seed=61,mode='sql',db=None,scope='train_kb')
        self.assertEqual(records[0].status,'invalid_output')
    def test_identity_manifest_rejects_substitution(self):
        with tempfile.TemporaryDirectory() as d,patch.object(F,'ROOT',Path(d)):
            root=Path(d);(root/'datasets_v3').mkdir();(root/'finetune').mkdir()
            prompt=root/'datasets_v3/PROMPT_TEMPLATES_A002.json';prompt.write_text('{"model_revision":"fixed"}')
            contract=root/'finetune/structured_prompt_v3.py';contract.write_text('fixture')
            predpath=root/'predictions.jsonl';predpath.write_text('fixture output')
            manifest=root/'identity.json';adapter=root/'adapter.safetensors';adapter.write_bytes(b'fixture weights')
            r={'example_id':'x','prompt_hash':'a'*64,'adapter_hash':F.sha(adapter)}
            m={'predictions_sha256':F.sha(predpath),'model_revision':'fixed','prompt_artifact_sha256':F.sha(prompt),'structured_prompt_sha256':F.sha(contract),'model_kind':'adapter','adapter_path':adapter.name,'prompt_hashes':{'x':'a'*64}}
            manifest.write_text(json.dumps(m))
            release={'sha256':{'identity.json':F.sha(manifest),adapter.name:F.sha(adapter)},'prediction_identity_manifests':{'predictions.jsonl':'identity.json'}}
            F.validate_prediction_identities(release,predpath,[r])
            for field,value in [('adapter_hash','fabricated'),('prompt_hash','b'*64)]:
                bad={**r,field:value}
                with self.assertRaises(RuntimeError):F.validate_prediction_identities(release,predpath,[bad])
            adapter.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):F.validate_prediction_identities(release,predpath,[r])
    def test_missing_identity_refused(self):
        with self.assertRaises(RuntimeError):F.validate_prediction_identities({},F.ROOT/'missing',[])
if __name__=='__main__':unittest.main(verbosity=2)
