"""Check tests: verdicts, evidence, and UNPROVABLE discipline."""
import unittest

from _support import fixture

from am_healthcheck.checks import (build_overview, check_duplicate_records,
                                   check_retry_amplification, check_tool_error_runs,
                                   run_checks, retry_chains_for_session)
from am_healthcheck.codex import parse_session
from am_healthcheck.model import CallRecord, ExecRecord, SessionRecord


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


if __name__ == "__main__":
    unittest.main()
