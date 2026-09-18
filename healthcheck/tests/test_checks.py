"""Check tests: verdicts, evidence, and UNPROVABLE discipline."""
import unittest
from collections import defaultdict

from _support import fixture

from am_healthcheck.checks import (build_overview, check_duplicate_records,
                                   check_retry_amplification, check_tool_error_runs,
                                   check_operation_resolution_coverage,
                                   check_cache_accounting_cross_check,
                                   check_token_accounting_stability,
                                   run_checks, retry_chains_for_session)
from am_healthcheck.codex import parse_session
from am_healthcheck.model import (CallRecord, ExecRecord, SessionRecord,
                                  TokenSnapshot)


def session_with_execs(statuses, hashes=None, kinds=None):
    """Build a minimal in-memory session for chain/run logic tests."""
    s = SessionRecord(path="mem://s1", session_id="sess1")
    hashes = hashes or (["cmd%s" % ((i // 2) % 3) for i in range(len(statuses))])
    kinds = kinds or (["git"] * len(statuses))
    for i, st in enumerate(statuses):
        s.execs.append(ExecRecord(
            session_id="sess1", file="mem://s1", line=i + 1, source="exec",
            kind=kinds[i], status=st,
            exit_code=0 if st == "ok" else (1 if st == "failed" else None),
            cmd_hash=hashes[i]))
    return s


class TestRetryChains(unittest.TestCase):
    def test_fail_fail_ok_is_one_chain(self):
        s = session_with_execs(["failed", "failed", "ok"],
                               hashes=["npm", "npm", "npm"])
        chains = retry_chains_for_session(s)
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0].attempts, 3)
        self.assertTrue(chains[0].resolved)

    def test_ok_then_repeats_is_not_chain(self):
        s = session_with_execs(["ok", "ok", "ok"], hashes=["ls", "ls", "ls"])
        self.assertEqual(retry_chains_for_session(s), [])

    def test_unresolved_chain(self):
        s = session_with_execs(["failed", "failed"], hashes=["cargo", "cargo"])
        chains = retry_chains_for_session(s)
        self.assertEqual(len(chains), 1)
        self.assertFalse(chains[0].resolved)

    def test_unknown_interrupts_block(self):
        s = session_with_execs(["failed", "unknown", "failed"],
                               hashes=["a", "a", "a"])
        self.assertEqual(retry_chains_for_session(s), [])

    def test_alternating_commands_not_one_chain(self):
        s = session_with_execs(["failed", "failed", "failed", "failed"],
                               hashes=["x", "y", "x", "y"])
        self.assertEqual(retry_chains_for_session(s), [])


class TestErrorRuns(unittest.TestCase):
    def test_run_of_three_same_kind(self):
        s = session_with_execs(["failed", "failed", "failed"],
                               hashes=["p1", "p2", "p1"], kinds=["python"] * 3)
        res = check_tool_error_runs([s])
        self.assertEqual(res.status, "finding")
        self.assertIn("1 run(s)", res.findings[0].title)

    def test_two_failures_not_a_run(self):
        s = session_with_execs(["failed", "failed"], hashes=["a", "a"])
        res = check_tool_error_runs([s])
        self.assertEqual(res.status, "ok")

    def test_success_breaks_run(self):
        s = session_with_execs(["failed", "failed", "ok", "failed"],
                               hashes=["a", "a", "a", "a"])
        self.assertEqual(check_tool_error_runs([s]).status, "ok")


class TestUnprovable(unittest.TestCase):
    def test_calls_without_exec_events(self):
        s = SessionRecord(path="mem://cli", session_id="cli1")
        s.calls.append(CallRecord(session_id="cli1", file="mem://cli", line=1,
                                  call_id="c1", name="shell", kind="function"))
        self.assertEqual(check_retry_amplification([s]).status, "unprovable")
        self.assertEqual(check_tool_error_runs([s]).status, "unprovable")
        ov = build_overview([s], "w")
        self.assertEqual(ov.sessions_without_exec_events, 1)


class TestVerdictsOnFixtures(unittest.TestCase):
    def test_ok_fixture_clean(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        _ov, results, _cov, top3 = run_checks([s], "test")
        verdicts = {c.check_id: c.status for c in results}
        self.assertEqual(verdicts["HC-02"], "ok")
        self.assertEqual(verdicts["HC-03"], "ok")
        self.assertEqual(verdicts["HC-01"], "info")  # dual-stream disclosure only

    def test_retries_fixture_finds_both(self):
        s = parse_session(fixture("codex-retries.jsonl"))
        _ov, results, coverage, top3 = run_checks([s], "test")
        verdicts = {c.check_id: c.status for c in results}
        self.assertEqual(verdicts["HC-02"], "finding")
        self.assertEqual(verdicts["HC-03"], "finding")
        chains = retry_chains_for_session(s)
        self.assertEqual(len(chains), 2)          # npm(3, resolved) + cargo(2, unresolved)
        self.assertTrue(top3)

    def test_duplicates_fixture(self):
        s = parse_session(fixture("codex-duplicates.jsonl"))
        res = check_duplicate_records([s])
        self.assertEqual(res.status, "finding")
        finding_titles = [f.title for f in res.findings]
        self.assertTrue(any("duplicate line" in t for t in finding_titles))
        self.assertTrue(any("call_id" in t for t in finding_titles))
        call_finding = next(f for f in res.findings if "call_id" in f.title)
        self.assertTrue(call_finding.evidence[0].line > 0)

    def test_evidence_carries_location(self):
        s = parse_session(fixture("codex-retries.jsonl"))
        res = check_retry_amplification([s])
        ev = res.findings[0].evidence[0]
        self.assertEqual(ev.session, "99999999")
        self.assertTrue(ev.line >= 1)
        self.assertIn("attempts", ev.detail)


class TestHc04ResolutionCoverage(unittest.TestCase):
    def test_hc04_no_execs_unprovable(self):
        s = SessionRecord(path="mem://noexec", session_id="noexec")
        res = check_operation_resolution_coverage([s])
        self.assertEqual(res.status, "unprovable")
        self.assertIn("No execution events", res.unprovable_reason)

    def test_hc04_resolution_coverage_ok(self):
        """>80% resolved — ok"""
        s = SessionRecord(path="mem://ok", session_id="ok_sess")
        for i in range(10):
            s.execs.append(ExecRecord(
                session_id="ok_sess", file="mem://ok", line=i + 1, source="exec",
                kind="bash", status="ok", exec_id="op-%d" % i,
                cmd_hash="h%d" % i))
        res = check_operation_resolution_coverage([s])
        self.assertEqual(res.status, "ok")
        self.assertIn("resolution rate", res.summary)

    def test_hc04_resolution_coverage_finding(self):
        """<50% resolved — finding"""
        s = SessionRecord(path="mem://low", session_id="low_sess")
        for i in range(10):
            s.execs.append(ExecRecord(
                session_id="low_sess", file="mem://low", line=i + 1, source="exec",
                kind="bash",
                status="ok" if i < 3 else "failed",
                exec_id="op-%d" % i if i < 5 else "",
                cmd_hash="h%d" % i))
        res = check_operation_resolution_coverage([s])
        self.assertEqual(res.status, "finding")
        self.assertTrue(any("Low" in f.title for f in res.findings))
        self.assertTrue(any("50%" in f.title for f in res.findings))

    def test_hc04_resolution_coverage_info(self):
        """50-80% resolved — info (borderline)"""
        s = SessionRecord(path="mem://mid", session_id="mid_sess")
        for i in range(10):
            s.execs.append(ExecRecord(
                session_id="mid_sess", file="mem://mid", line=i + 1, source="exec",
                kind="bash",
                status="ok" if i < 6 else "failed",
                exec_id="op-%d" % i,
                cmd_hash="h%d" % i))
        res = check_operation_resolution_coverage([s])
        self.assertEqual(res.status, "info")
        self.assertTrue(any("Moderate" in f.title for f in res.findings))


class TestHc05CacheAccounting(unittest.TestCase):
    def test_hc05_cache_accounting_ok(self):
        """No suspicious patterns → ok"""
        s = SessionRecord(path="mem://cok", session_id="cok")
        s.tokens.append(TokenSnapshot(
            file="mem://cok", line=1,
            input_tokens=100, cached_input=30, cache_write_input=20,
            output_tokens=50, total_tokens=150))
        res = check_cache_accounting_cross_check([s])
        self.assertEqual(res.status, "ok")

    def test_hc05_cach_accounting_finding(self):
        """total > input + output → double-counting finding"""
        s = SessionRecord(path="mem://csus", session_id="csus")
        s.tokens.append(TokenSnapshot(
            file="mem://csus", line=1,
            input_tokens=100, cached_input=30, cache_write_input=20,
            output_tokens=50, total_tokens=200))  # 200 > 150
        res = check_cache_accounting_cross_check([s])
        self.assertEqual(res.status, "finding")
        self.assertIn("likely double-counted", res.findings[0].explanation)

    def test_hc05_cache_accounting_no_tokens(self):
        """No token snapshots → unprovable"""
        s = SessionRecord(path="mem://ct", session_id="ct")
        res = check_cache_accounting_cross_check([s])
        self.assertEqual(res.status, "unprovable")


class TestHc06TokenStability(unittest.TestCase):
    def test_hc06_no_tokens_unprovable(self):
        """No token data → unprovable"""
        s = SessionRecord(path="mem://nou", session_id="nt")
        res = check_token_accounting_stability([s])
        self.assertEqual(res.status, "unprovable")
        self.assertIn("No token snapshots", res.unprovable_reason)

    def test_hc06_no_execs_unprovable(self):
        """Token data but no execs → unprovable"""
        s = SessionRecord(path="mem://n", session_id="ne")
        s.tokens.append(TokenSnapshot(
            file="mem://ne", line=1,
            input_tokens=50, output_tokens=50, total_tokens=100))
        res = check_token_accounting_stability([s])
        self.assertEqual(res.status, "unprovable")
        self.assertIn("No executions", res.unprovable_reason)

    def test_hc06_token_stability_finding(self):
        """Two sessions with very different token/exec ratios → finding"""
        s1 = SessionRecord(path="mem://h", session_id="h", project="p1")
        for i in range(10):
            s1.execs.append(ExecRecord(
                session_id="h", file="mem://h", line=i + 1, source="exec",
                kind="bash", status="ok", cmd_hash="h%d" % i))
        s1.tokens.append(TokenSnapshot(
            file="mem://h", line=1,
            input_tokens=1000, output_tokens=1000, total_tokens=2000))

        s2 = SessionRecord(path="mem://l", session_id="l", project="p1")
        for i in range(10):
            s2.execs.append(ExecRecord(
                session_id="l", file="mem://l", line=i + 1, source="exec",
                kind="bash", status="ok", cmd_hash="h%d" % i))
        s2.tokens.append(TokenSnapshot(
            file="mem://l", line=1,
            input_tokens=10, output_tokens=10, total_tokens=20))

        res = check_token_accounting_stability([s1, s2])
        self.assertEqual(res.status, "finding")

    def test_hc06_token_stability_ok(self):
        """Similar ratios across sessions → ok"""
        s1 = SessionRecord(path="mem://a", session_id="a", project="stable")
        for i in range(5):
            s1.execs.append(ExecRecord(
                session_id="a", file="mem://a", line=i + 1, source="exec",
                kind="bash", status="ok", cmd_hash="h%d" % i))
        s1.tokens.append(TokenSnapshot(
            file="mem://a", line=1,
            input_tokens=100, output_tokens=100, total_tokens=200))

        s2 = SessionRecord(path="mem://b", session_id="b", project="stable")
        for i in range(5):
            s2.execs.append(ExecRecord(
                session_id="b", file="mem://b", line=i + 1, source="exec",
                kind="bash", status="ok", cmd_hash="h%d" % i))
        s2.tokens.append(TokenSnapshot(
            file="mem://b", line=1,
            input_tokens=105, output_tokens=95, total_tokens=200))

        res = check_token_accounting_stability([s1, s2])
        self.assertEqual(res.status, "ok")


class TestAuditMode(unittest.TestCase):
    def test_run_checks_with_audit_mode(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        _ov, results, _cov, _top = run_checks([s], "test", audit_mode=True)
        check_ids = {c.check_id for c in results}
        self.assertIn("HC-04", check_ids)
        self.assertIn("HC-05", check_ids)
        self.assertIn("HC-06", check_ids)

    def test_run_checks_without_audit_mode(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        _ov, results, _cov, _top = run_checks([s], "test", audit_mode=False)
        check_ids = {c.check_id for c in results}
        self.assertIn("HC-04", check_ids)   # HC-04 is always included
        self.assertNotIn("HC-05", check_ids)
        self.assertNotIn("HC-06", check_ids)
