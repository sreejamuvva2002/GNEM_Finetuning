"""Regression guards for V2's zero-label/truncation failure."""
import unittest
from phase10_build_a_cpt import load_real_tokenizer
from training_tokens_v3 import encode_chat,supervised_tokens
class LabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tok,_=load_real_tokenizer()
    def chat(self,user='What is recorded?',answer='ISO 9001; ISO 14001'):
        return [{'role':'system','content':'Answer from the dataset.'},{'role':'user','content':user},{'role':'assistant','content':answer}]
    def test_entire_answer_and_eot_supervised(self):
        messages=self.chat();row=encode_chat(self.tok,messages)
        supervised=[v for v in row['labels'] if v!=-100]
        self.assertEqual(self.tok.decode(supervised),'\n'+messages[-1]['content']+'<|im_end|>')
        self.assertEqual(supervised_tokens(row),len(supervised))
    def test_long_prompt_fails_instead_of_dropping_answer(self):
        with self.assertRaises(ValueError):encode_chat(self.tok,self.chat(user='company '*2000))
    def test_long_answer_fails_instead_of_truncating_list(self):
        with self.assertRaises(ValueError):encode_chat(self.tok,self.chat(answer='ISO 9001; '*2000))
    def test_empty_assistant_refused(self):
        with self.assertRaises(ValueError):encode_chat(self.tok,self.chat(answer=''))
    def test_extra_turn_refused_until_explicit_support(self):
        with self.assertRaises(ValueError):encode_chat(self.tok,self.chat()+[{'role':'user','content':'Next'}])
if __name__=='__main__':unittest.main(verbosity=2)
