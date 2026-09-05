"""Adapter tests: correct read, empty file, corrupt lines, missing fields,
duplicate records — the R1 acceptance failure modes."""
import unittest

from _support import fixture

from am_healthcheck.codex import parse_session


class TestOkSession(unittest.TestCase):
    def setUp(self):
        self.rec = parse_session(fixture("codex-ok.jsonl"))

    def test_metadata(self):
        self.assertEqual(self.rec.cli_version, "0.153.0")
        self.assertEqual(self.rec.originator, "Codex Desktop")
        self.assertIn("demo-model-a", self.rec.models)
        self.assertTrue(self.rec.started_at)

    def test_counts(self):
        self.assertEqual(self.rec.line_stats.total, 13)
        self.assertEqual(self.rec.line_stats.corrupt, 0)
        self.assertEqual(len(self.rec.execs), 3)      # 2 CommandExecution + 1 Mcp
        self.assertEqual(len(self.rec.calls), 2)      # function + custom
        self.assertEqual(len(self.rec.tokens), 1)
        self.assertEqual(self.rec.turns, 1)
        self.assertEqual(self.rec.file_changes, 1)

    def test_exec_statuses(self):
        statuses = [e.status for e in self.rec.execs]
        self.assertEqual(statuses, ["ok", "ok", "ok"])
        self.assertEqual(self.rec.execs[0].kind, "git")
        self.assertEqual(self.rec.execs[2].kind, "mcp:demo-server/deploy-prod")

    def test_call_output_linking(self):
        call = [c for c in self.rec.calls if c.call_id == "call_demo_1"][0]
        self.assertTrue(call.has_output)
        self.assertIsNotNone(call.output_line)

    def test_token_subsets_stored_not_summed(self):
        snap = self.rec.tokens[0]
        self.assertEqual(snap.input_tokens, 1000)
        self.assertEqual(snap.cached_input, 300)
        self.assertEqual(snap.total_tokens, 1200)  # as reported, not recomputed


class TestEmptyFile(unittest.TestCase):
    def test_empty(self):
        rec = parse_session(fixture("codex-empty.jsonl"))
        self.assertEqual(rec.line_stats.total, 0)
        self.assertEqual(rec.execs, [])
        self.assertEqual(rec.calls, [])
        self.assertTrue(any("no session_meta" in a for a in rec.anomalies))


class TestCorruptFile(unittest.TestCase):
    def setUp(self):
        self.rec = parse_session(fixture("codex-corrupt.jsonl"))

    def test_corrupt_accounting(self):
        # broken JSON, JSON array, missing type, truncated object
        self.assertEqual(self.rec.line_stats.corrupt, 4)
        self.assertEqual(self.rec.line_stats.total, 10)

    def test_good_lines_still_parsed(self):
        self.assertEqual(len(self.rec.execs), 1)
        self.assertEqual(len(self.rec.tokens), 1)

    def test_unknown_types_accounted(self):
        self.assertIn("totally_unknown_type", self.rec.unknown_types)

    def test_missing_payload_becomes_empty(self):
        # payload-as-string line must not crash; parsed count reflects it
        self.assertEqual(self.rec.line_stats.parsed, 6)


class TestDuplicates(unittest.TestCase):
    def setUp(self):
        self.rec = parse_session(fixture("codex-duplicates.jsonl"))

    def test_identical_lines(self):
        # line 4 repeats line 3, line 9 repeats line 8 (byte-identical);
        # line 5 reuses the call_id with different content — counted under
        # dup_call_ids, not dup_lines.
        self.assertEqual(len(self.rec.dup_lines), 2)

    def test_duplicate_call_ids(self):
        self.assertEqual(self.rec.dup_call_ids.get("call_dup_1"), 3)


class TestRetriesFixture(unittest.TestCase):
    def setUp(self):
        self.rec = parse_session(fixture("codex-retries.jsonl"))

    def test_exec_outcomes(self):
        outcomes = [e.status for e in self.rec.execs]
        self.assertEqual(len(outcomes), 10)
        self.assertEqual(outcomes.count("failed"), 8)
        self.assertEqual(outcomes.count("ok"), 2)


if __name__ == "__main__":
    unittest.main()
