import unittest,json,collections
from pathlib import Path
from phase16_build_bd import repeat_to_budget
class Repetition(unittest.TestCase):
    def test_partial_cycle_distributed_and_full_source_retained(self):
        rows=[{'example_id':f'{a}-{i}','join_arity':a,'_completion_tokens':10} for a,n in [(0,60),(1,20),(2,20)] for i in range(n)]
        out=repeat_to_budget(rows,1200)
        counts=collections.Counter(r['join_arity'] for r in out[100:])
        self.assertEqual(counts,{0:12,1:4,2:4})
        self.assertEqual({r['source_example_id'] for r in out},{r['example_id'] for r in rows})
        self.assertEqual(len({r['example_id'] for r in out}),len(out))
    def test_real_extra_cycles_cover_every_arity(self):
        root=Path(__file__).resolve().parent.parent/'datasets_v3'
        for name in ('train_BD_controlled_v3.jsonl','train_D_repeat_budgetmatched_v3.jsonl'):
            rows=[json.loads(l) for l in (root/name).read_text().splitlines()]
            d=[r for r in rows if 'join_arity' in r];counts=collections.Counter(r.get('source_example_id',r['example_id']) for r in d)
            minimum=min(counts.values())
            repeated={r['join_arity'] for r in d if counts[r.get('source_example_id',r['example_id'])]>minimum}
            self.assertEqual(repeated,{0,1,2})
if __name__=='__main__':unittest.main(verbosity=2)
