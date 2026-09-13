import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import final_generate_v3 as G

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        names=list(G.DEPENDENCIES)+['validation_v3/Q42_HUMAN_APPROVAL_A002.json',
            'datasets_v3/probe_42_v3.jsonl','fixture.jsonl','runtime.json']
        for name in names:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
        self.run={'run_id':'fixture','inputs':'fixture.jsonl','runtime_spec':'runtime.json',
                  'out':'results_v3/sealed_generation/fixture','mode':'memory',
                  'condition':'base','seed':None,'model_kind':'base'}
        self.release={'approved':True,'purpose':'protected_generation','runs':[self.run],
                      'classification':{'fixture.jsonl':'sealed_inputs'}}
        self.approval=self.root/'validation_v3/Q42_HUMAN_APPROVAL_A002.json'
        self.approval.write_text(json.dumps({'approved':True,'benchmark_sha256':G.sha(self.root/'datasets_v3/probe_42_v3.jsonl')}))
        self.names=names;self.pin()
    def pin(self): self.release['sha256']={n:G.sha(self.root/n) for n in self.names}
    def check(self): return G.authorize_generation(self.root,self.release,'fixture')
    def test_valid_fixture(self): self.assertEqual(self.check()[0],self.run)
    def test_approval_refused_before_backend(self):
        self.approval.write_text('{"approved":false}');self.pin()
        factory=Mock(side_effect=AssertionError('Must not load model'))
        with self.assertRaises(RuntimeError):G.execute(self.root,self.release,'fixture',factory)
        factory.assert_not_called()
    def test_unpinned_and_changed_code(self):
        del self.release['sha256'][G.DEPENDENCIES[0]]
        with self.assertRaises(RuntimeError):self.check()
        self.pin();(self.root/G.DEPENDENCIES[0]).write_text('changed')
        with self.assertRaises(RuntimeError):self.check()
    def test_run_and_path_constraints(self):
        for key,value in [('mode','sql'),('seed',True),('out','../external'),('adapter_path','fake')]:
            old=dict(self.run);self.run[key]=value
            with self.assertRaises(RuntimeError):self.check()
            self.run.clear();self.run.update(old)
    def test_stale_approval(self):
        (self.root/'datasets_v3/probe_42_v3.jsonl').write_text('changed');self.pin()
        with self.assertRaises(RuntimeError):self.check()
    def test_runtime_exact_match(self):
        G.verify_runtime({'tokenizer':'a'}, {'backend_runtime':{'tokenizer':'a'}})
        for spec in ({},{'backend_runtime':{}},{'backend_runtime':{'tokenizer':'b'}}):
            with self.assertRaises(RuntimeError):G.verify_runtime({'tokenizer':'a'},spec)
    def test_complete_synthetic_generation(self):
        config={'model_revision':'fixture','closed_book_system':'Fixture',
                'decoding':{'do_sample':False,'max_new_tokens':2},'max_context':20}
        (self.root/'datasets_v3/PROMPT_TEMPLATES_A002.json').write_text(json.dumps(config))
        (self.root/'runtime.json').write_text(json.dumps({'prompt_config':config,'backend_runtime':{'fixture':True}}))
        (self.root/'fixture.jsonl').write_text(json.dumps({'example_id':'x','question':'Return 7','answer_type':'scalar'})+'\n')
        self.pin()
        class Backend:
            runtime={'fixture':True}
            eos_token_ids={9}
            def render(self,messages):return str(messages)
            def encode(self,text):return [1]
            def generate(self,ids,limit):return [7,9]
            def decode(self,ids):return '7'
        reg=G.execute(self.root,self.release,'fixture',lambda *a,**k:Backend())
        out=self.root/self.run['out']
        self.assertTrue((out/'generation_release.json').is_file())
        self.assertIs(reg['approved'],False)
        self.assertEqual(json.loads((out/'predictions.jsonl').read_text())['raw_output'],'7')
    def test_no_real_approval_created(self):
        self.assertFalse((G.ROOT/G.RELEASE_NAME).exists())

if __name__=='__main__':unittest.main(verbosity=2)
