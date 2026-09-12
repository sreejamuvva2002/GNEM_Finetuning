"""Loss-bearing CPT boundaries must preserve source tokens exactly."""
import unittest
from training_tokens_v3 import pack_cpt_stream,supervised_tokens
class CPTPacking(unittest.TestCase):
    def test_all_boundaries_preserve_tokens(self):
        for n in (2,3,7,8,9,15,16,17,1025,2049):
            stream=list(range(n)); rows=pack_cpt_stream(stream,8)
            self.assertEqual([t for r in rows for t in r['input_ids']],stream)
            self.assertTrue(all(2<=len(r['input_ids'])<=8 for r in rows))
            self.assertEqual(sum(supervised_tokens(r) for r in rows),n-len(rows))
    def test_ordinary_boundaries_unchanged(self):
        rows=pack_cpt_stream(list(range(18)),8)
        self.assertEqual([len(r['input_ids']) for r in rows],[8,8,2])
    def test_unsupervisable_stream_rejected(self):
        for s in ([],[1]):
            with self.assertRaises(ValueError):pack_cpt_stream(s)
if __name__=='__main__':unittest.main(verbosity=2)
