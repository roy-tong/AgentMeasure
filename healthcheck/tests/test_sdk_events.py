"""Cross-side SDK event pairing tests."""
import json
import os
import tempfile
import unittest

from am_healthcheck.model import ExecRecord, SessionRecord
from am_healthcheck.sdk_events import build_cross_side_report, load_sdk_events


def session_with_calls(call_ids):
    """Build a session whose ExecRecords carry the given exec_ids.

    ExecRecord is the client-side record the pairing walks; it exposes
    ``exec_id`` (CallRecord is the one that carries ``call_id``).
    """
    s = SessionRecord(path="mem://x", session_id="sess-x")
    for i, cid in enumerate(call_ids):
        s.execs.append(ExecRecord(
            session_id="sess-x", file="mem://x", line=i + 1, source="exec",
            kind="mcp", status="ok", exec_id=cid,
            cmd_hash="h%d" % i))
    return s


class TestLoadSdkEvents(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, text):
        path = os.path.join(self.tmp.name, "sdk.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_load_valid_events(self):
        path = self._write(
            json.dumps({"tool_call_id": "c1", "type": "attempt_started"}) + "\n"
            + json.dumps({"tool_call_id": "c1", "type": "attempt_completed"}) + "\n")
        events = load_sdk_events(path)
        self.assertEqual(len(events), 2)

    def test_load_skips_blank_lines(self):
        path = self._write("\n\n" + json.dumps({"tool_call_id": "c1"}) + "\n\n")
        self.assertEqual(len(load_sdk_events(path)), 1)

    def test_load_empty_file(self):
        path = self._write("")
        self.assertEqual(load_sdk_events(path), [])

    def test_load_invalid_json_raises(self):
        path = self._write("{not json}\n")
        with self.assertRaises(ValueError):
            load_sdk_events(path)

    def test_load_missing_file_raises(self):
        with self.assertRaises(OSError):
            load_sdk_events(os.path.join(self.tmp.name, "nope.jsonl"))


class TestBuildCrossSideReport(unittest.TestCase):
    def test_all_paired(self):
        sessions = [session_with_calls(["c1", "c2"])]
        events = [{"tool_call_id": "c1"}, {"tool_call_id": "c2"}]
        report = build_cross_side_report(sessions, events)
        self.assertEqual(report["total_client_operations"], 2)
        self.assertEqual(report["total_sdk_attempts"], 2)
        self.assertEqual(report["paired_count"], 2)
        self.assertEqual(report["sdk_only_count"], 0)
        self.assertEqual(report["client_only_count"], 0)

    def test_sdk_only_events(self):
        sessions = [session_with_calls(["c1"])]
        events = [{"tool_call_id": "c1"}, {"tool_call_id": "unmatched"}]
        report = build_cross_side_report(sessions, events)
        self.assertEqual(report["paired_count"], 1)
        self.assertEqual(report["sdk_only_count"], 1)

    def test_client_only_operations(self):
        sessions = [session_with_calls(["c1", "c2", "c3"])]
        events = [{"tool_call_id": "c1"}]
        report = build_cross_side_report(sessions, events)
        self.assertEqual(report["paired_count"], 1)
        self.assertEqual(report["client_only_count"], 2)

    def test_no_events(self):
        sessions = [session_with_calls(["c1"])]
        report = build_cross_side_report(sessions, [])
        self.assertEqual(report["total_sdk_attempts"], 0)
        self.assertEqual(report["paired_count"], 0)
        self.assertEqual(report["client_only_count"], 1)

    def test_no_sessions(self):
        report = build_cross_side_report([], [{"tool_call_id": "c1"}])
        self.assertEqual(report["total_client_operations"], 0)
        self.assertEqual(report["sdk_only_count"], 1)

    def test_report_disclaims_billable_audit(self):
        report = build_cross_side_report([], [])
        # Pairing alone is cross-side attribution, not billable_audit.
        self.assertIn("cross-side_attribution", report["note"])
        self.assertIn("billable_audit", report["note"])


if __name__ == "__main__":
    unittest.main()
