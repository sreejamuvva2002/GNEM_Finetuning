import unittest,json
from structured_answer_v3 import grade_structured_answer
class StructuredAnswers(unittest.TestCase):
    def test_topk_order_width_and_extras(self):
        item={'answer_type':'top_k','gold_value':{'columns':['company','n'],'rows':[['A',3],['B',2]]}}
        for rows,ok in [([['A',3],['B',2]],1),([['B',2],['A',3]],0),([['A',3]],0),([['A',3],['B',2],['C',1]],0),(['A','B'],0)]:
            g,_=grade_structured_answer(json.dumps(rows),item);self.assertEqual(g.task_result_correctness,ok)
    def test_multicolumn_set_ignores_order_not_extra_rows(self):
        item={'answer_type':'set','gold_value':{'columns':['a','b'],'rows':[['X',1],['Y',2]]}}
        g,_=grade_structured_answer('[["Y",2],["X",1]]',item);self.assertEqual(g.task_result_correctness,1)
        g,_=grade_structured_answer('[["Y",2],["X",1],["Z",3]]',item);self.assertEqual(g.task_result_correctness,0)
    def test_multipart_requires_all_and_only_requested_parts(self):
        item={'answer_type':'multi_part','gold_value':{'count':{'columns':['n'],'rows':[[2]]},'names':{'columns':['company'],'rows':[['A'],['B']]}},'parts':[{'part_id':'count','answer_type':'scalar'},{'part_id':'names','answer_type':'set'}]}
        for obj,ok in [({'count':2,'names':['A','B']},1),({'count':3,'names':['A','B']},0),({'count':2},0),({'count':2,'names':['A','B'],'extra':1},0)]:
            g,_=grade_structured_answer(json.dumps(obj),item);self.assertEqual(g.task_result_correctness,ok)
    def test_public_dispatch_and_prompt_shape(self):
        from answer_parser_v3 import grade_answer
        from structured_prompt_v3 import output_instruction
        item={'answer_type':'multi_part','gold_value':{'count':{'columns':['n'],'rows':[[2]]}},'parts':[{'part_id':'count','answer_type':'scalar','target_columns':['n']}]}
        self.assertIn('count',output_instruction(item))
        g,_=grade_answer('{"count":2}',item)
        self.assertEqual(g.task_result_correctness,1)
        self.assertEqual(g.strict_result_schema_accuracy,1)

    def test_nonstandard_and_truncated_rejected(self):
        item={'answer_type':'top_k','gold_value':{'columns':['n'],'rows':[[1]]}}
        for text in ('[[NaN]]','prose [[1]]'):
            g,_=grade_structured_answer(text,item);self.assertEqual(g.task_result_correctness,0)
        g,_=grade_structured_answer('[[1]]',item,True);self.assertEqual(g.task_result_correctness,0)
if __name__=='__main__':unittest.main(verbosity=2)
