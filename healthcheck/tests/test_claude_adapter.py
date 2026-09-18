"""Claude Code session adapter tests (fixtures + fail-closed guarantees)."""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from am_healthcheck import claude as claude_adapter
from am_healthcheck import checks as checks_mod

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "am_healthcheck", "fixtures")


def fixture(name):
    return os.path.join(FIXTURES, name)


class TestClaudeAdapter(unittest.TestCase):
    def test_ok_session_maps_tools_turns_and_models(self):
        rec = claude_adapter.parse_session(fixture("claude-ok.jsonl"))
        self.assertEqual(rec.session_id, "sess-ok-1")
        self.assertEqual(rec.project, "shop")
        self.assertEqual(rec.turns, 2)
        self.assertEqual(rec.models, ["claude-sonnet-4-5"])
        # three tool executions: Bash exec, MCP call, Edit tool
        self.assertEqual(len(rec.execs), 3)
        self.assertEqual(len(rec.calls), 3)
        sources = sorted(e.source for e in rec.execs)
        self.assertEqual(sources, ["exec", "mcp", "tool"])
        self.assertEqual(rec.execs[0].kind, "pytest")
        self.assertTrue(rec.execs[0].kind and rec.execs[1].kind.startswith("mcp:github/"))
        self.assertEqual(rec.file_changes, 1)  # the Edit
        # every tool_result arrived: all outcomes decided
        self.assertEqual({e.status for e in rec.execs}, {"ok"})
        self.assertTrue(all(c.has_output for c in rec.calls))
        self.assertEqual(rec.line_stats.corrupt, 0)
        self.assertEqual(rec.dup_lines, [])

    def test_retry_session_builds_failure_then_success_chain(self):
        rec = claude_adapter.parse_session(fixture("claude-retries.jsonl"))
        self.assertEqual(len(rec.execs), 4)
        statuses = [e.status for e in rec.execs]
        self.assertEqual(statuses, ["failed", "failed", "failed", "ok"])
        # same command → same hash → one retry chain
        self.assertEqual(len({e.cmd_hash for e in rec.execs}), 1)

    def test_duplicate_lines_are_dropped_not_counted(self):
        rec = claude_adapter.parse_session(fixture("claude-duplicates.jsonl"))
        # byte-identical re-emission recorded as dup, not a second execution
        self.assertEqual(len(rec.dup_lines), 1)
        self.assertEqual(len(rec.execs), 1)
        self.assertEqual(len(rec.calls), 1)

    def test_empty_file_produces_nothing(self):
        rec = claude_adapter.parse_session(fixture("claude-empty.jsonl"))
        self.assertEqual(rec.line_stats.total, 0)
        self.assertEqual(rec.execs, [])
        self.assertEqual(rec.calls, [])

    def test_missing_tool_result_stays_unknown(self):
        import json, tempfile, os
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({
                "type": "assistant", "cwd": "/x", "sessionId": "s1",
                "timestamp": "2026-09-10T10:00:00.000Z",
                "message": {"model": "m", "content": [
                    {"type": "tool_use", "id": "toolu_z", "name": "Bash",
                     "input": {"command": "make build"}}], "usage": {}}}) + "\n")
            path = f.name
        try:
            rec = claude_adapter.parse_session(path)
            self.assertEqual(rec.execs[0].status, "unknown")
            self.assertFalse(rec.calls[0].has_output)
        finally:
            os.unlink(path)

    def test_per_request_usage_disclosed_not_invented_as_cumulative(self):
        rec = claude_adapter.parse_session(fixture("claude-ok.jsonl"))
        # no cumulative counter exists in Claude transcripts → no snapshots
        self.assertEqual(rec.tokens, [])
        self.assertEqual(rec.thread_tokens, [])
        self.assertFalse(rec.token_invalid)  # not malformed — honestly absent
        self.assertTrue(any("UNPROVABLE by surface" in a for a in rec.anomalies))


class TestClaudeChecks(unittest.TestCase):
    def test_ok_session_all_checks_ok(self):
        rec = claude_adapter.parse_session(fixture("claude-ok.jsonl"))
        ov, results, _cov, _top = checks_mod.run_checks([rec], "test")
        verdicts = {c.check_id: c.status for c in results}
        # HC-01 is "info": the dual-stream note (model-side calls + command events)
        # is informative, not a defect — and warns against summing both streams
        self.assertEqual(verdicts.get("HC-01"), "info")
        self.assertEqual(verdicts.get("HC-02"), "ok")
        self.assertEqual(verdicts.get("HC-03"), "ok")
        # token accounting: per-request only → UNPROVABLE, never zeroed as fact
        self.assertEqual(ov.token_provable, False)
        self.assertEqual(ov.token_missing_sessions, 1)

    def test_retry_session_flags_hc02_and_hc03(self):
        rec = claude_adapter.parse_session(fixture("claude-retries.jsonl"))
        ov, results, _cov, _top = checks_mod.run_checks([rec], "test")
        verdicts = {c.check_id: c.status for c in results}
        self.assertEqual(verdicts.get("HC-02"), "finding")
        self.assertEqual(verdicts.get("HC-03"), "finding")
        self.assertEqual(ov.exec_total, 4)
        self.assertEqual(ov.exec_failed, 3)
        self.assertEqual(ov.exec_ok, 1)

    def test_duplicate_session_flags_hc01(self):
        rec = claude_adapter.parse_session(fixture("claude-duplicates.jsonl"))
        ov, results, _cov, _top = checks_mod.run_checks([rec], "test")
        verdicts = {c.check_id: c.status for c in results}
        self.assertEqual(verdicts.get("HC-01"), "finding")
        self.assertEqual(ov.exec_total, 1)  # dup dropped, count stays honest


if __name__ == "__main__":
    unittest.main()
