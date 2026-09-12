"""Synthetic end-to-end evaluation checks; no protected model output opened."""
import json,unittest
from pathlib import Path
import final_eval_v3 as F
class FinalDriver(unittest.TestCase):
    def fixture(self):
        return [
          {'example_id':'count','family':'synthetic','question':'Count fixture entries.','answer_type':'scalar','gold_value':2,'target_columns':['n']},
          {'example_id':'empty','family':'synthetic','question':'List absent fixtures.','answer_type':'set','gold_value':[],'target_columns':['company']},
          {'example_id':'rank','family':'synthetic','question':'Rank the two fixtures.','answer_type':'top_k','gold_value':{'columns':['company'],'rows':[['A'],['B']]},'target_columns':['company']},
          {'example_id':'parts','family':'synthetic','question':'Count and list fixtures.','answer_type':'multi_part','gold_value':{'n':2,'names':['A','B']},'parts':[{'part_id':'n','answer_type':'scalar','target_columns':['n']},{'part_id':'names','answer_type':'set','target_columns':['company']}]}]
    def preds(self,items):
        values=['2','[]','[["A"],["B"]]','{"n":2,"names":["A","B"]}']
        return [{'example_id':i['example_id'],'condition':'fixture','seed':61,'question':i['question'],'prompt_hash':'a'*64,'adapter_hash':'b'*64,'raw_output':v} for i,v in zip(items,values)]
    def run_fixture(self,items,preds,mode='memory'):
        return F.grade_run(items,preds,condition='fixture',seed=61,mode=mode,scope='train_dev_kb',db=F.ROOT/'datasets_v3/gnem_v3.sqlite')
    def test_shapes_serialization_and_denominators(self):
        items=self.fixture();records,telemetry,summary=self.run_fixture(items,self.preds(items))
        self.assertEqual(summary['correct'],4);self.assertEqual(summary['n'],4)
        self.assertEqual(summary['valid_no_match_n'],1)
        for r in records:self.assertEqual(F.R.from_dict(json.loads(json.dumps(r.to_dict()))),r)
    def test_missing_and_duplicate_ids_rejected(self):
        items=self.fixture();preds=self.preds(items)
        for bad in (preds[:-1],preds+[preds[0]]):
            with self.assertRaises(ValueError):self.run_fixture(items,bad)
    def test_failures_not_removed(self):
        items=self.fixture();preds=self.preds(items);preds[0]['raw_output']='3';preds[1]['raw_output']=''
        records,telemetry,s=self.run_fixture(items,preds)
        self.assertEqual(s['n'],4);self.assertEqual(s['correct'],2);self.assertEqual(s['valid_no_match_n'],0)
    def test_truncation_rejects_correct_prefix(self):
        items=self.fixture();preds=self.preds(items);preds[0]['stopped_at_max_new_tokens']=True
        records,_,s=self.run_fixture(items,preds);self.assertEqual(records[0].status,'truncated_output')
    def test_sql_execution_evidence_retained(self):
        items=[{'example_id':'count','family':'synthetic','question':'Return two.','answer_type':'scalar','gold_value':{'columns':['n'],'rows':[[2]]},'gold_sql':'SELECT 2 AS n','target_columns':['n']}]
        preds=self.preds(items);preds[0]['raw_output']='SELECT 2 AS n'
        records,_,s=self.run_fixture(items,preds,'sql');self.assertEqual(s['correct'],1)
        self.assertEqual(records[0].execution_result,[{'columns':['n'],'rows':[[2]]}])
    def test_declared_probe_scope_used_for_sql(self):
        from unittest.mock import patch
        items=[{'example_id':'count','family':'synthetic','question':'Return two.','scope':'train_kb','answer_type':'scalar','gold_value':{'columns':['n'],'rows':[[2]]},'gold_sql':'SELECT 2 AS n','target_columns':['n']}]
        preds=self.preds(items);preds[0]['raw_output']='SELECT 2 AS n'
        with patch.object(F.G,'grade_structured',wraps=F.G.grade_structured) as spy:
            _,telemetry,_=self.run_fixture(items,preds,'sql')
            self.assertEqual(spy.call_args.args[3],'train_kb')
            self.assertEqual(telemetry[0]['scope'],'train_kb')
    def test_authorization_fails_before_missing_files_read(self):
        with self.assertRaisesRegex(RuntimeError,'approved Phase 40'):
            F.authorize({},Path('/nonexistent'),Path('/nonexistent'),Path('/nonexistent'))
    def test_independent_seed_summary_and_duplicates(self):
        from dataclasses import replace
        items=self.fixture();records,_,_=self.run_fixture(items,self.preds(items))
        other=[replace(r,seed=62) for r in records]
        result=F.summarize_independent_runs([records,other])
        self.assertEqual(result['summary']['mean'],1)
        self.assertEqual(result['summary']['sd'],0)
        with self.assertRaises(ValueError):F.summarize_independent_runs([records,records])
        with self.assertRaises(ValueError):F.summarize_independent_runs([records,other[:-1]])
    def test_no_real_release_exists(self):self.assertFalse(F.RELEASE.exists())
if __name__=='__main__':unittest.main(verbosity=2)
