import unittest
from answer_parser_v3 import (grade_answer, output_contract_compliant,
                              unquote_bounded, MAX_QUOTE_LAYERS)


def scalar(gold, **extra):
    item = {'answer_type': 'scalar', 'gold_value': gold}
    item.update(extra)
    return item


class ParserTests(unittest.TestCase):
    """Original A002.1 coverage -- unchanged, must keep passing."""

    def test_extra_certification_rejected(self):
        item={'answer_type':'set','gold_value':['ISO 9001'],'company':'Example'}
        g,_=grade_answer('ISO 9001; ISO 14001',item)
        self.assertEqual(g.task_result_correctness,0)
        self.assertEqual(g.metrics['precision'],.5)
    def test_valid_set(self):
        item={'answer_type':'set','gold_value':['ISO 9001','ISO 14001'],'company':'Example'}
        for answer in ('ISO 14001; ISO 9001','["ISO 9001", "ISO 14001"]'):
            self.assertEqual(grade_answer(answer,item)[0].status,'correct')
    def test_empty_or_noise_not_valid_abstention(self):
        item={'answer_type':'set','gold_value':[]}
        for answer in ('','I cannot answer.','!!!'):
            self.assertNotEqual(grade_answer(answer,item)[0].status,'correct')
        self.assertEqual(grade_answer('No companies match.',item)[0].status,'correct')
    def test_scalar_no_substring_credit(self):
        item={'answer_type':'scalar','gold_value':'180'}
        self.assertEqual(grade_answer('The answer is 180.',item)[0].status,'correct')
        self.assertNotEqual(grade_answer('180 or 200',item)[0].status,'correct')
    def test_truncation_not_correct(self):
        self.assertEqual(grade_answer('180',{'answer_type':'scalar','gold_value':'180'},True)[0].status,'truncated_output')


class ContractComplianceIndependenceTests(unittest.TestCase):
    """Output-format compliance must be a function of the RESPONSE ALONE."""

    def test_compliance_never_consults_gold(self):
        # Identical response text, four different golds -> identical compliance.
        for gold in ('Tier 1', 'Tier 2', 'anything', ''):
            self.assertTrue(grade_answer('"Tier 1"', scalar(gold))[0]
                            .metrics['output_contract_compliant'])

    def test_compliance_helper_is_pure_text_and_type(self):
        self.assertTrue(output_contract_compliant('"Tier 1"', 'scalar'))
        self.assertTrue(output_contract_compliant('  180  ', 'scalar'))
        self.assertTrue(output_contract_compliant('["a"]', 'set'))
        self.assertTrue(output_contract_compliant('[["a", 1]]', 'top_k'))
        # Not "a string or number", not a bare value, not a lone array.
        self.assertFalse(output_contract_compliant('true', 'scalar'))
        self.assertFalse(output_contract_compliant('null', 'scalar'))
        self.assertFalse(output_contract_compliant('{"a": 1}', 'scalar'))
        self.assertFalse(output_contract_compliant('["a"]', 'scalar'))
        self.assertFalse(output_contract_compliant('"a"', 'set'))
        self.assertFalse(output_contract_compliant('Tier 1', 'scalar'))
        self.assertFalse(output_contract_compliant('```json\n"Tier 1"\n```', 'scalar'))
        self.assertFalse(output_contract_compliant('The value is "Tier 1".', 'scalar'))

    def test_all_four_correctness_format_combinations_are_reachable(self):
        cases = {
            # (semantically_correct, output_contract_compliant): response
            (True,  True):  '"Tier 1"',
            (True,  False): 'Tier 1',
            (False, True):  '"Tier 2"',
            (False, False): 'Tier 2',
        }
        for (want_correct, want_compliant), text in cases.items():
            g, _ = grade_answer(text, scalar('Tier 1'))
            self.assertEqual(g.metrics['semantically_correct'], want_correct, text)
            self.assertEqual(g.metrics['output_contract_compliant'], want_compliant, text)

    def test_correct_plain_text_semantic_pass_format_fail(self):
        g, _ = grade_answer('Tier 1', scalar('Tier 1'))
        self.assertEqual(g.status, 'correct')
        self.assertEqual(g.task_result_correctness, 1.0)
        self.assertFalse(g.metrics['output_contract_compliant'])
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)
        self.assertEqual(g.metrics['format_repairs'], [])

    def test_correct_json_scalar_both_pass(self):
        g, _ = grade_answer('"Tier 1"', scalar('Tier 1'))
        self.assertEqual(g.status, 'correct')
        self.assertTrue(g.metrics['output_contract_compliant'])
        self.assertTrue(g.metrics['matched_without_repair'])
        self.assertEqual(g.strict_result_schema_accuracy, 1.0)
        self.assertEqual(g.metrics['format_repairs'], [])

    def test_wrong_json_scalar_format_passes_semantics_fails(self):
        g, _ = grade_answer('"Tier 2"', scalar('Tier 1'))
        self.assertEqual(g.status, 'incorrect')
        self.assertEqual(g.task_result_correctness, 0.0)
        self.assertTrue(g.metrics['output_contract_compliant'])   # well-formed, wrong
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)


class BoundedRepairTests(unittest.TestCase):

    def test_double_encoded_scalar_contract_treatment(self):
        """Valid JSON string whose CONTENT is quoted.

        Contract treatment, stated explicitly: the response IS one JSON string, so
        `output_contract_compliant` is True. It did not deliver the recorded value
        without repair, so `matched_without_repair` is False and
        `strict_result_schema_accuracy` is 0.0, while semantics pass.
        """
        g, _ = grade_answer('"\\"Tier 1\\""', scalar('Tier 1'))
        self.assertEqual(g.status, 'correct')
        self.assertEqual(g.task_result_correctness, 1.0)
        self.assertTrue(g.metrics['output_contract_compliant'])
        self.assertFalse(g.metrics['matched_without_repair'])
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)
        self.assertIn('surplus_quote_strip', g.metrics['format_repairs'])

    def test_double_quoted_non_json_scalar_is_not_contract_compliant(self):
        """The same defect expressed as INVALID JSON: semantics pass, format fails."""
        g, _ = grade_answer('""Tier 1""', scalar('Tier 1'))
        self.assertEqual(g.status, 'correct')
        self.assertFalse(g.metrics['output_contract_compliant'])
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)
        self.assertIn('surplus_quote_strip', g.metrics['format_repairs'])

    def test_budget_scalar_vs_array_members(self):
        # Scalar: json.loads spends 1, R1 spends 1 -> exactly at the cap.
        self.assertEqual(unquote_bounded('"Tier 1"', 1), ('Tier 1', True))
        # No decode spent: R1 may spend both layers.
        self.assertEqual(unquote_bounded('""Tier 1""', 0), ('Tier 1', True))
        # Budget exhausted: one layer survives.
        self.assertEqual(unquote_bounded('""Tier 1""', 1), ('"Tier 1"', True))
        self.assertEqual(MAX_QUOTE_LAYERS, 2)

    def test_array_members_each_get_their_own_budget(self):
        item = {'answer_type': 'set', 'gold_value': ['ISO 9001', 'ISO 14001']}
        g, _ = grade_answer('["\\"ISO 9001\\"", "\\"ISO 14001\\""]', item)
        self.assertEqual(g.status, 'correct')
        self.assertTrue(g.metrics['output_contract_compliant'])   # it is a JSON array
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)    # but needed repair
        self.assertIn('surplus_quote_strip', g.metrics['format_repairs'])

    def test_mismatched_quotes_are_never_stripped(self):
        import json as _json
        for bad in ('“Tier 1"', '"Tier 1”', '”Tier 1“'):
            self.assertEqual(unquote_bounded(bad, 0), (bad, False), bad)
            g, _ = grade_answer(_json.dumps(bad), scalar('Tier 1'))
            self.assertEqual(g.status, 'incorrect', bad)

    def test_matched_typographic_pair_is_stripped(self):
        self.assertEqual(unquote_bounded('“Tier 1”', 1), ('Tier 1', True))

    def test_excessive_quoting_layers_are_not_repaired(self):
        import json as _json
        # Three layers via JSON: 1 decode + 1 R1 = cap, one layer survives.
        g, _ = grade_answer(_json.dumps('""Tier 1""'), scalar('Tier 1'))
        self.assertEqual(g.status, 'incorrect')
        # Three literal layers, no decode: 2 x R1 = cap, one layer survives.
        g, _ = grade_answer('"""Tier 1"""', scalar('Tier 1'))
        self.assertEqual(g.status, 'incorrect')

    def test_requested_key_object_unwrapped(self):
        g, _ = grade_answer('{"location": "Rome, Floyd County"}',
                            scalar('Rome, Floyd County', attribute='location'))
        self.assertEqual(g.status, 'correct')
        self.assertFalse(g.metrics['output_contract_compliant'])  # object, not scalar
        self.assertEqual(g.strict_result_schema_accuracy, 0.0)
        self.assertIn('named_object_unwrap', g.metrics['format_repairs'])

    def test_target_column_key_object_unwrapped(self):
        g, _ = grade_answer('{"n": 5}', scalar('5', target_columns=['n']))
        self.assertEqual(g.status, 'correct')
        self.assertIn('named_object_unwrap', g.metrics['format_repairs'])

    def test_unrelated_key_object_rejected(self):
        for text in ('{"answer": "Rome, Floyd County"}',
                     '{"value": "Rome, Floyd County"}',
                     '{"location": "Rome", "county": "Floyd County"}'):
            g, _ = grade_answer(text, scalar('Rome, Floyd County', attribute='location'))
            self.assertEqual(g.status, 'incorrect', text)

    def test_object_with_requested_key_but_wrong_value_rejected(self):
        g, _ = grade_answer('{"location": "Atlanta"}',
                            scalar('Rome, Floyd County', attribute='location'))
        self.assertEqual(g.status, 'incorrect')

    def test_repair_never_rescues_a_wrong_value(self):
        for text in ('"\\"Tier 2\\""', '""Tier 2""', '{"category": "Tier 2"}'):
            g, _ = grade_answer(text, scalar('Tier 1', attribute='category'))
            self.assertEqual(g.status, 'incorrect', text)

    def test_repair_never_breaks_a_strictly_correct_answer(self):
        corpus = [('"Tier 1"', scalar('Tier 1')),
                  ('Tier 1', scalar('Tier 1')),
                  ('180', scalar('180')),
                  ('The answer is 180.', scalar('180')),
                  ('["ISO 9001", "ISO 14001"]',
                   {'answer_type': 'set', 'gold_value': ['ISO 9001', 'ISO 14001']}),
                  ('ISO 14001; ISO 9001',
                   {'answer_type': 'set', 'gold_value': ['ISO 9001', 'ISO 14001']})]
        for text, item in corpus:
            g, _ = grade_answer(text, item)
            self.assertEqual(g.task_result_correctness, 1.0, text)


class DeliberatelyNotNormalisedTests(unittest.TestCase):

    def test_boolean_substitution_rejected(self):
        for text, gold in (('"False"', 'No'), ('"false"', 'No'),
                           ('"true"', 'Yes'), ('"True"', 'Yes'),
                           ('false', 'No'), ('true', 'Yes')):
            g, _ = grade_answer(text, scalar(gold, attribute='ev_battery_relevant'))
            self.assertEqual(g.status, 'incorrect', (text, gold))

    def test_missing_set_member_rejected(self):
        item = {'answer_type': 'set', 'gold_value': ['ISO 9001', 'ISO 14001']}
        g, _ = grade_answer('["ISO 9001"]', item)
        self.assertEqual(g.status, 'incorrect')
        self.assertEqual(g.metrics['missing_values'], ['iso 14001'])
        self.assertEqual(g.metrics['extra_values'], [])

    def test_extra_set_member_rejected(self):
        item = {'answer_type': 'set', 'gold_value': ['ISO 9001', 'ISO 14001']}
        g, _ = grade_answer('["ISO 9001", "ISO 14001", "AS9100"]', item)
        self.assertEqual(g.status, 'incorrect')
        self.assertEqual(g.metrics['extra_values'], ['as9100'])
        self.assertEqual(g.metrics['missing_values'], [])

    def test_repaired_set_still_rejects_extra_member(self):
        item = {'answer_type': 'set', 'gold_value': ['ISO 9001']}
        g, _ = grade_answer('["\\"ISO 9001\\"", "\\"AS9100\\""]', item)
        self.assertEqual(g.status, 'incorrect')
        self.assertEqual(g.metrics['extra_values'], ['as9100'])


class StrictJSONConstantsTests(unittest.TestCase):
    def test_nonstandard_constants_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            for text, kind in ((value, 'scalar'), ('['+value+']', 'set')):
                self.assertFalse(output_contract_compliant(text, kind), text)

    def test_standard_values_remain_compliant(self):
        for text in ('0', '-12', '3.5', '1e3', '"NaN"'):
            self.assertTrue(output_contract_compliant(text, 'scalar'), text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
