"""Buyer review regression: billing truth cannot substitute for delivery truth."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from _support import DEMO_DIR
from verovo_healthcheck import review, cli


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = json.loads((Path(DEMO_DIR) / "buyer-review.json").read_text())
        self.facts = json.loads((Path(DEMO_DIR) / "buyer-observations.json").read_text())

    def run_review(self):
        (self.root / "task.json").write_text(json.dumps(self.task))
        (self.root / "buyer-observations.json").write_text(json.dumps(self.facts))
        return review.evaluate(self.root / "task.json")

    def command(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = cli.main(args)
        return status, out.getvalue(), err.getvalue()

    def test_correct_charge_does_not_mask_failed_delivery_or_missing_evidence(self):
        result = self.run_review()
        self.assertEqual(result['lanes']['charges']['verdict'], 'PASS')
        self.assertEqual(result['lanes']['delivery']['verdict'], 'FAIL')
        self.assertEqual(result['lanes']['delivery']['counts']['UNPROVABLE'], 1)
        self.assertEqual(len(result['criteria'][0]['source_sha256']), 64)
        self.assertIn('not proof of incorrect billing', result['boundary'])

    def test_delivery_only_needs_no_billing_discrepancy(self):
        self.task['workflow'] = 'delivery'
        self.task['criteria'] = self.task['criteria'][1:2]
        self.facts['delivery']['manual_rescue_tasks'] = 2
        result = self.run_review()
        self.assertEqual(result['lanes']['charges']['verdict'], 'NOT_REVIEWED')
        self.assertEqual(result['lanes']['delivery']['verdict'], 'PASS')

    def test_missing_lane_criteria_not_a_pass(self):
        self.task['criteria'] = self.task['criteria'][:1]
        self.assertEqual(self.run_review()['lanes']['delivery']['verdict'], 'UNPROVABLE')

    def test_null_missing_bad_type_and_nonfinite_are_not_false(self):
        for value in (None, True, '5', {}, float('inf')):
            with self.subTest(value=value):
                self.facts['delivery']['manual_rescue_tasks'] = value
                self.assertEqual(self.run_review()['criteria'][1]['verdict'], 'UNPROVABLE')
        self.facts['delivery'].pop('manual_rescue_tasks')
        self.assertEqual(self.run_review()['criteria'][1]['verdict'], 'UNPROVABLE')

    def test_boolean_is_not_numeric_one(self):
        self.task['criteria'][2]['expected'] = True
        self.facts['delivery']['external_completion'] = 1
        self.assertEqual(self.run_review()['criteria'][2]['verdict'], 'UNPROVABLE')

    def test_bad_contract_and_duplicate_ids_rejected(self):
        original = copy.deepcopy(self.task)
        for change in ('id', 'basis', 'operator', 'expected'):
            self.task = copy.deepcopy(original)
            if change == 'id':
                self.task['criteria'][1]['id'] = self.task['criteria'][0]['id']
            elif change == 'basis':
                self.task['criteria'][1]['basis']['kind'] = 'billing_rule'
            elif change == 'operator':
                self.task['criteria'][0]['operator'] = 'execute'
            else:
                self.task['criteria'][1]['expected'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_review()

    def test_missing_evidence_file_is_unprovable(self):
        self.task['criteria'][0]['source']['path'] = 'missing.json'
        self.assertEqual(self.run_review()['criteria'][0]['verdict'], 'UNPROVABLE')

    def test_evidence_path_cannot_escape(self):
        self.task['criteria'][0]['source']['path'] = '../outside.json'
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.run_review()

    def test_pointer_escaped_keys_and_array(self):
        self.assertEqual(review._pointer({'a/b': [{'~x': 3}]}, '/a~1b/0/~0x'), 3)
        for pointer in ('/a~2b', '/a~'):
            with self.assertRaises(ValueError):
                review._pointer({}, pointer)

    def test_duplicate_json_keys_rejected(self):
        path = self.root/'duplicate.json'
        path.write_text('{"value": 1, "value": 2}')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            review._read(path)

    def test_html_escapes_buyer_supplied_text(self):
        self.task['scope']['buyer'] = '<script>alert(1)</script>'
        rendered = review.report_html(self.run_review())
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_cli_sample_and_output_paths(self):
        report, data = self.root/'review.html', self.root/'review.json'
        code, out, err = self.command(['review', '--sample', '--html', str(report), '--json', str(data)])
        self.assertEqual(code, 0, err)
        self.assertIn('SYNTHETIC DEMO', out)
        self.assertTrue(json.loads(data.read_text())['synthetic'])
        self.assertIn('UNPROVABLE', report.read_text())

    def test_cli_preserves_input_and_template(self):
        self.run_review()
        task = self.root/'task.json'
        original = task.read_bytes()
        self.assertEqual(self.command(['review', '--task', str(task), '--json', str(task)])[0], 2)
        self.assertEqual(task.read_bytes(), original)
        evidence = self.root/'buyer-observations.json'
        before = evidence.read_bytes()
        self.assertEqual(self.command(['review', '--task', str(task), '--html', str(evidence)])[0], 2)
        self.assertEqual(evidence.read_bytes(), before)
        self.assertEqual(self.command(['review', '--init', str(task)])[0], 2)
        new_task = self.root/'new.json'
        self.assertEqual(self.command(['review', '--init', str(new_task)])[0], 0)
        self.assertEqual(self.command(['review', '--task', str(new_task)])[0], 2)


if __name__ == '__main__':
    unittest.main()
