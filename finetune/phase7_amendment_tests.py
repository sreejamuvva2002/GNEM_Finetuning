"""A-002 regressions: semantic aliases, bounded SQL, and scope isolation."""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sqlexec_v3 as X
import grade_v3 as G
DB = Path(__file__).resolve().parent.parent / 'datasets_v3/gnem_v3.sqlite'

class AmendmentTests(unittest.TestCase):
    def test_scalar_alias_semantics_and_strict_schema(self):
        item = {'answer_type': 'scalar', 'target_columns': ['n']}
        r = G.grade_structured(item, 'SELECT COUNT(*) AS company_count FROM companies',
                               'SELECT COUNT(*) AS n FROM companies', 'train_kb', db_path=DB)
        self.assertEqual((r.status, r.task_result_correctness, r.strict_result_schema_accuracy),
                         ('correct', 1.0, 0.0))
        for sql in ('SELECT 999 AS other', 'SELECT 148 AS other, 148 AS ambiguous',
                    'SELECT 148 AS other UNION ALL SELECT 148',
                    'SELECT company AS other FROM companies WHERE 0'):
            r = G.grade_structured(item, sql, 'SELECT 148 AS n', 'train_kb', db_path=DB)
            self.assertEqual(r.task_result_correctness, 0.0, sql)

    def test_actual_expensive_query_is_interrupted(self):
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            X.run_sql('SELECT COUNT(*) FROM companies a CROSS JOIN companies b '
                      'CROSS JOIN companies c CROSS JOIN companies d', 'train_kb',
                      db_path=DB, timeout_seconds=0.02)
        self.assertLess(time.monotonic() - start, 2.0)
        self.assertEqual(X.run_sql('SELECT COUNT(*) FROM companies', 'train_kb',
                                   db_path=DB).rows, ((148,),))

    def test_sql_looking_literal_is_data(self):
        value = "Product; drop -- coating /* machining */"
        result = X.run_sql("SELECT 'Product; drop -- coating /* machining */' AS value",
                           'train_kb', db_path=DB)
        self.assertEqual(result.rows, ((value,),))
        with self.assertRaises(X.SQLPolicyError):
            X.run_sql("SELECT 1; DELETE FROM companies", 'train_kb', db_path=DB)

    def test_timeout_configuration(self):
        for value in (0, -1, float('nan'), float('inf'), True, '5', None):
            with self.assertRaises(X.ConfigError):
                X.run_sql('SELECT 1', 'train_kb', db_path=DB, timeout_seconds=value)

    def test_timeout_status(self):
        with patch.object(X, 'execute_pair', side_effect=TimeoutError('fixture')):
            r = G.grade_structured({'answer_type':'scalar','target_columns':['n']},
                                   'SELECT 1 AS n', 'SELECT 1 AS n', 'train_kb', db_path=DB)
        self.assertEqual(r.status, 'timeout')

    def test_deadline_preserves_scope_guard(self):
        with self.assertRaises(X.SQLPolicyError):
            X.run_sql('SELECT * FROM main.companies', 'train_kb', db_path=DB)

if __name__ == '__main__':
    unittest.main(verbosity=2)
