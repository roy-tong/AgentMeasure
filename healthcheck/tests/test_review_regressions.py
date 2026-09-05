"""Regression cases found during the pre-publication review.

All payloads are synthetic. No real logs or home-directory overrides are used.
"""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from _support import HEALTHCHECK_DIR
from am_healthcheck import cli, codex, history
from am_healthcheck.checks import (build_overview, coverage_findings, run_checks,
                                   retry_chains_for_session)
from am_healthcheck.model import Overview
from am_healthcheck.report_html import _overview_grid
from am_healthcheck.share import build_share_summary, share_json, share_markdown


def event(item, ts="2026-09-05T12:01:00Z"):
    return {"timestamp": ts, "type": "event_msg",
            "payload": {"type": "item_completed", "item": item}}


def command(eid, code=0, cmd=None, cwd="/synthetic/a"):
    return {"type": "CommandExecution", "id": eid, "command": cmd or ["git", "status"],
            "cwd": cwd, "exit_code": code, "status": "completed" if code == 0 else "failed"}


def usage(n):
    return {"input_tokens": n, "output_tokens": 10, "total_tokens": n + 10,
            "cached_input_tokens": 0, "reasoning_output_tokens": 0}


class ReviewCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_log(self, rows, name="a.jsonl", meta=True, session_id="synthetic-review-session"):
        if meta:
            rows = [{"timestamp": "2026-09-05T12:00:00Z", "type": "session_meta",
                     "payload": {"id": session_id, "cli_version": "0.153.0",
                                 "cwd": "/synthetic/a"}}] + rows
        path = self.root / name
        path.write_text("\n".join(json.dumps(r) if not isinstance(r, str) else r
                                  for r in rows) + "\n")
        return path

    def invoke(self, args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return cli.main(args)

    def test_share_drops_explicit_path_and_arbitrary_version_metadata(self):
        ov = Overview(cli_versions=["0.153.0", "/private/SECRET-REPO", "1.2.3-SECRET-REPO"])
        summary = build_share_summary(ov, [], "own-data", "explicit directory: /private/SECRET-REPO")
        for blob in (share_json(summary), share_markdown(summary)):
            self.assertNotIn("SECRET-REPO", blob)
            self.assertNotIn("/private", blob)
        self.assertEqual(summary["runtime_versions"], ["0.153.0", "1.2.3"])

    def test_html_escapes_all_runtime_metadata(self):
        payload = '<span><img src="https://example.invalid/pixel" onerror="alert(1)">'
        html = _overview_grid(Overview(cli_versions=[payload]))
        self.assertNotIn('<img src=', html)
        self.assertIn('&lt;img', html)

    def test_malformed_nested_info_does_not_crash(self):
        p = self.write_log([{"type": "event_msg", "payload": {"type": "token_count", "info": [1]}}])
        s = codex.parse_session(str(p))
        self.assertTrue(s.anomalies or s.line_stats.corrupt)
        self.assertFalse(build_overview([s], "test").token_provable)

    def test_invalid_utf8_line_is_disclosed_as_corrupt(self):
        p = self.write_log([event(command("one"))])
        with open(p, "ab") as fh:
            fh.write(b"\xff\n")
        session = codex.parse_session(str(p))
        self.assertEqual(session.line_stats.corrupt, 1)
        self.assertEqual(session.corrupt_lines, [3])

    def test_non_finite_duration_is_unknown(self):
        item = command("one")
        item["duration"] = float("nan")
        session = codex.parse_session(str(self.write_log([event(item)])))
        self.assertIsNone(session.execs[0].duration)

    def test_lone_unicode_surrogate_does_not_break_exports(self):
        p = self.write_log([{"type": "turn_context", "payload": {"model": "bad\ud800"}},
                            event(command("one"))], session_id="bad\ud800")
        html = self.root / "surrogate.html"
        jsn = self.root / "surrogate.json"
        self.assertEqual(self.invoke(["check", "--dir", str(self.root),
                                      "--html", str(html), "--json", str(jsn),
                                      "--no-history"]), 0)
        self.assertIn("bad", html.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(jsn.read_text(encoding="utf-8"))["overview"]["sessions"], 1)

    def test_missing_token_counters_are_unknown(self):
        p = self.write_log([{"type": "event_msg", "payload": {"type": "token_count",
                         "info": {"total_token_usage": {"cached_input_tokens": 10}}}}])
        self.assertFalse(build_overview([codex.parse_session(str(p))], "test").token_provable)

    def test_invalid_token_snapshot_overrides_later_valid_snapshot(self):
        rows = [
            {"type": "event_msg", "payload": {"type": "token_count",
             "info": {"total_token_usage": usage(100)}}},
            {"type": "event_msg", "payload": {"type": "token_count",
             "info": {"total_token_usage": {"input_tokens": 200,
                                                "output_tokens": 10}}}},
        ]
        session = codex.parse_session(str(self.write_log(rows)))
        ov = build_overview([session], "test")
        self.assertFalse(ov.token_provable)
        self.assertEqual(ov.token_invalid_sessions, 1)
        self.assertTrue(any("invalid or incomplete" in f.title
                            for f in coverage_findings(ov)))

    def test_negative_token_subset_is_invalid(self):
        bad = usage(100)
        bad["cached_input_tokens"] = -1
        p = self.write_log([{"type": "token_usage_record", "payload": {
            "thread_token_usage": bad}}])
        session = codex.parse_session(str(p))
        self.assertTrue(session.token_invalid)
        self.assertFalse(build_overview([session], "test").token_provable)

    def test_invalid_thread_usage_does_not_fallback_to_turn_usage(self):
        bad = usage(100)
        bad.pop("total_tokens")
        p = self.write_log([{"type": "token_usage_record", "payload": {
            "thread_token_usage": bad, "usage": usage(20)}}])
        session = codex.parse_session(str(p))
        self.assertTrue(session.token_invalid)
        self.assertFalse(build_overview([session], "test").token_provable)

    def test_partial_token_coverage_is_unprovable(self):
        valid = self.write_log([{"type": "token_usage_record", "payload": {
            "thread_token_usage": usage(100)}}], "valid.jsonl", session_id="valid")
        missing = self.write_log([event(command("one"))], "missing.jsonl",
                                 session_id="missing")
        ov = build_overview(codex.parse_files([str(valid), str(missing)]), "test")
        self.assertFalse(ov.token_provable)
        self.assertEqual(ov.token_missing_sessions, 1)

    def test_thread_usage_uses_cumulative_not_single_response(self):
        p = self.write_log([{"type": "token_usage_record", "payload": {
            "usage": usage(20), "thread_token_usage": usage(1000)}}])
        ov = build_overview([codex.parse_session(str(p))], "test")
        self.assertEqual(ov.token_total_input, 1000)

    def test_latest_snapshot_and_same_session_not_summed_twice(self):
        a = self.write_log([{"timestamp": "2026-09-05T12:01:00Z", "type": "event_msg", "payload": {
            "type": "token_count", "info": {"total_token_usage": usage(100)}}}], "a.jsonl")
        b = self.write_log([{"timestamp": "2026-09-05T12:02:00Z", "type": "token_usage_record", "payload": {
            "usage": usage(20), "thread_token_usage": usage(200)}}], "b.jsonl")
        ov = build_overview(codex.parse_files([str(a), str(b)]), "test")
        self.assertEqual(ov.sessions, 1)
        self.assertEqual(ov.token_total_input, 200)

    def test_duplicate_exec_ids_and_copied_file_do_not_inflate_counts(self):
        rows = [event(command("one", 1)), event(command("one", 1), "2026-09-05T12:02:00Z")]
        a = self.write_log(rows, "a.jsonl")
        b = self.write_log(rows, "b.jsonl")
        sessions = codex.parse_files([str(a), str(b)])
        ov, results, _, _ = run_checks(sessions, "test")
        self.assertEqual(ov.exec_total, 1)
        self.assertEqual(ov.retry_chains, 0)
        self.assertEqual(results[0].status, "finding")

    def test_conflicting_exec_id_is_unknown(self):
        p = self.write_log([event(command("one", 1)), event(command("one", 0))])
        s = codex.parse_session(str(p))
        self.assertEqual(len(s.execs), 1)
        self.assertEqual(s.execs[0].status, "unknown")

    def test_success_closes_candidate_retry_sequence(self):
        p = self.write_log([event(command(str(i), code)) for i, code in enumerate([1, 0, 0])])
        chains = retry_chains_for_session(codex.parse_session(str(p)))
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].attempts, 2)

    def test_different_working_directories_are_not_same_operation(self):
        p = self.write_log([event(command("1", 1)), event(command("2", 0, cwd="/synthetic/b"))])
        self.assertEqual(retry_chains_for_session(codex.parse_session(str(p))), [])

    def test_turn_boundary_breaks_candidate_chain(self):
        p = self.write_log([event(command("1", 1)), {"type": "event_msg", "payload": {
            "type": "task_started", "turn_id": "next"}}, event(command("2", 0))])
        self.assertEqual(retry_chains_for_session(codex.parse_session(str(p))), [])

    def test_corrupt_gap_breaks_chain_and_is_disclosed(self):
        p = self.write_log([event(command("1", 1)), "{broken", event(command("2", 0))])
        s = codex.parse_session(str(p))
        self.assertEqual(retry_chains_for_session(s), [])
        _, checks, _, _ = run_checks([s], "test")
        self.assertTrue(checks[1].unprovable_reason)

    def test_mcp_different_arguments_are_not_same_operation(self):
        items = [{"type": "McpToolCall", "id": str(i), "server": "demo", "tool": "lookup",
                  "arguments": {"query": q}, "status": st}
                 for i, (q, st) in enumerate([("alpha", "failed"), ("beta", "completed")])]
        p = self.write_log([event(item) for item in items])
        self.assertEqual(retry_chains_for_session(codex.parse_session(str(p))), [])

    def test_mcp_argument_key_order_does_not_break_retry_detection(self):
        items = [
            {"type": "McpToolCall", "id": "m1", "server": "demo", "tool": "lookup",
             "arguments": {"a": 1, "b": 2}, "status": "failed"},
            {"type": "McpToolCall", "id": "m2", "server": "demo", "tool": "lookup",
             "arguments": {"b": 2, "a": 1}, "status": "completed"},
        ]
        p = self.write_log([event(item) for item in items])
        chains = retry_chains_for_session(codex.parse_session(str(p)))
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].attempts, 2)

    def test_mcp_error_result_overrides_completed_envelope(self):
        item = {"type": "McpToolCall", "id": "m1", "server": "demo", "tool": "lookup",
                "status": "completed", "result": {"isError": True, "content": []}}
        p = self.write_log([event(item)])
        self.assertEqual(codex.parse_session(str(p)).execs[0].status, "failed")

    def test_many_calls_without_outcomes_count_one_session(self):
        rows = [{"type": "response_item", "payload": {"type": "function_call",
                 "call_id": str(i), "name": "tool"}} for i in range(4)]
        p = self.write_log(rows)
        ov = build_overview([codex.parse_session(str(p))], "test")
        self.assertEqual(ov.sessions_without_exec_events, 1)

    def test_metadata_only_session_is_unprovable_for_outcome_checks(self):
        p = self.write_log([], meta=True)
        session = codex.parse_session(str(p))
        ov, results, _, _ = run_checks([session], "test")
        self.assertEqual(ov.sessions_without_exec_events, 1)
        self.assertEqual({c.check_id: c.status for c in results}["HC-02"],
                         "unprovable")
        self.assertEqual({c.check_id: c.status for c in results}["HC-03"],
                         "unprovable")

    def test_missing_exit_code_is_not_success(self):
        item = command("one"); item.pop("exit_code")
        p = self.write_log([event(item)])
        s = codex.parse_session(str(p))
        self.assertEqual(s.execs[0].status, "unknown")
        _, checks, _, _ = run_checks([s], "test")
        self.assertEqual(checks[2].status, "unprovable")

    def test_read_cap_is_reported(self):
        p = self.write_log([event(command("one"))])
        with patch.object(codex, "PER_FILE_LIMIT_BYTES", 220):
            s = codex.parse_session(str(p))
        self.assertTrue(s.anomalies)

    def test_only_unrelated_json_is_an_input_error(self):
        d = self.root / "input"; d.mkdir(); (d / "x.jsonl").write_text('{"hello":"world"}\n')
        self.assertEqual(self.invoke(["check", "--dir", str(d), "--no-history",
                                      "--html", str(self.root / "out.html")]), 2)

    def test_output_cannot_overwrite_source_log(self):
        p = self.write_log([event(command("one"))]); before = p.read_bytes()
        code = self.invoke(["check", "--dir", str(self.root), "--html", str(p), "--no-history"])
        self.assertEqual(code, 2)
        self.assertEqual(p.read_bytes(), before)

    def test_output_hardlink_cannot_overwrite_source_log(self):
        p = self.write_log([event(command("one"))])
        linked = self.root / "linked.html"
        os.link(str(p), str(linked))
        before = p.read_bytes()
        code = self.invoke(["check", "--dir", str(self.root), "--html", str(linked),
                            "--no-history"])
        self.assertEqual(code, 2)
        self.assertEqual(p.read_bytes(), before)

    def test_same_personal_and_share_output_path_rejected(self):
        dest = str(self.root / "collision.md")
        self.assertEqual(self.invoke(["demo", "--html", dest, "--share", dest, "--no-history"]), 2)

    def test_unwritable_report_is_nonzero_without_traceback(self):
        self.assertEqual(self.invoke(["demo", "--html", str(self.root / "absent" / "out.html"),
                                      "--no-history"]), 2)

    def test_non_object_history_rows_are_ignored(self):
        p = self.root / "history.jsonl"; p.write_text('[1,2]\nnull\n{"mode":"own-data"}\n')
        with patch.object(history, "history_path", return_value=str(p)):
            self.assertEqual(history.run_number("own-data"), 2)


if __name__ == "__main__":
    unittest.main()
