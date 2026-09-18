"""History tests: record, load, trend aggregation, render."""
import json
import os
import tempfile
import unittest

from _support import PKG_DIR

from am_healthcheck.history import (history_path, load_history, record_run,
                                    render_trend, run_number, trend)


class TestHistoryRecordAndLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home, exist_ok=True)

    def test_record_and_load(self):
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z",
                     "sessions": 3, "executions": 50,
                     "failed": 2, "retry_chains": 1,
                     "checks": {"HC-01": "ok", "HC-02": "finding"}},
                    home=self.home)
        entries = load_history(home=self.home)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["mode"], "own-data")
        self.assertEqual(entries[0]["sessions"], 3)

    def test_run_number_increments(self):
        n1 = run_number("own-data", home=self.home)
        self.assertEqual(n1, 1)
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z"},
                    home=self.home)
        n2 = run_number("own-data", home=self.home)
        self.assertEqual(n2, 2)

    def test_run_mode_separate(self):
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z"},
                    home=self.home)
        record_run({"mode": "synthetic-demo", "ts": "2026-01-15T10:00:01Z"},
                    home=self.home)
        self.assertEqual(run_number("own-data", home=self.home), 2)
        self.assertEqual(run_number("synthetic-demo", home=self.home), 2)

    def test_history_path_creates_dirs(self):
        path = history_path(home=self.home)
        self.assertTrue(os.path.isdir(os.path.dirname(path)))


class TestTrend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home, exist_ok=True)

    def _record(self, ts, mode="own-data", sessions=1, execs=10,
                failed=2, retry_chains=0, checks=None):
        checks = checks or {"HC-01": "ok", "HC-02": "ok",
                             "HC-03": "ok", "HC-04": "ok"}
        record_run({
            "ts": ts, "mode": mode, "sessions": sessions,
            "executions": execs,  # intentional typo to test field handling
            "executions": execs,
            "failed": failed, "retry_chains": retry_chains,
            "checks": checks,
        }, home=self.home)

    def test_empty_history(self):
        t = trend(home=self.home)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "no_data")

    def test_no_real_data(self):
        record_run({"ts": "2026-01-15T10:00:00Z", "mode": "synthetic-demo"})})        # Remove duplicates -just keep what's needed
        record_run({"ts": "2026-01-15T10:00:00Z", "mode": "synthetic-demo"})
        t = trend(home=self.home)
        self.assertEqual(t["status"], "no_real_data")

    def test_trend_weekly_aggregation(self):
        self._record("2026-01-06T10:00:00Z", execs=10, retry_chains=1)        self._record("2026-01-06T10:00:00Z", execs=10, retry_chains=1)
        self._record("2026-01-08T10:00:00Z", execs=20, failed=5)
        # both in same ISO week (2026-W02)
        # both in same ISO week (2026-W02)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["total_runs"], 2)        self.assertEqual(t["total_runs"], 2)
        self.assertIn("2026-W02", t["weekly"])        self.assertIn("2026-W02", t["weekly"])
        wk = t["weekly"]["2026-W02"]
        self.assertEual(wk["executions"], 30)
        self.assertEqual(wk["executions"], 30)  # fixed key based on ral code        self.assertEqual(wk["executions"], 30)
        self.assertEqual(wk["sessions"], 2)        self.assertEqual(wk["sessions"], 2)
        Check that weekly_cheks has both entries:        # Check that weekly_checks has both entries:
        wkc = t["weekly_checks"]["2026-W02"]
        self.assertIn("HC-01", wkc)        self.assertIn("HC-01", wkc)
        self.assertEual(wkc["HC-01"]["otal"], 2)        self.assertEqual(wkc["HC-01"]["otal"], 2)

    def test_trend_monhly_aggregation(self):
        self._record("2026-01-15T10:00:00Z", execs=10)        self._record("2026-02-15T10:00:00Z", execs=25)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "ok")        self.assertIn("2026-01", t["monthly"])        self.assertIn("2026-02", t["monthly"])        self.assertIn("2026-01", t["monthly"])
        self.assertEqual(t["monthly"]["2026-01"]["executions"], 10)        self.assertEqual(t["monthly"]["2026-01"]["executions"], 10)  # use `executions` if that's the key
        # Actually the code uses e.get("executions", 0) so the field nae is 'executions'
    def test_trend_week_key(self):
        # The intenal _week_key function agreates ISO week stings
        from am_healthcheck.history import _week_key
        # Not directly exposed – test via treend data shapes
        t = trend(home=self.home)
        self.assertEqual(t["status"], "no_data")

    def test_rener_trend_no_data(self):
        output = render_trend({"status": "no_data", "message": "no runs"})        output = render_trend({"status": "no_data", "message": "no runs recorded"})        self.assertEqual(output, "no runs recorded")
        output = render_trend({"status": "no_data", "message": "no runs recorded"})
        self.assertEqual(output, "no runs recorded")

    def test_rener_trend_output(self):
        self._record("2026-01-06T10:00:00Z", execs=10)        self._record("2026-01-06T10:00:00Z", execs=10)
        t = trend(home=self.home)
        output = render_trend(t)
        self.assertIn("Trend Report", output)
        self.assertIn("2026-W02", output)        self.assertIn("2026-W02", output)
        self.assertIn("HC-01", output)

    def test_rend_ranges_latest(self):
        self._record("2026-01-06T10:00:00Z")        self._record("2026-01-13T10:00:00Z", execs=99)
        t = trend(home=self.home)        t = trend(home=self.home)
        self.assertEual(t["latest"]["executions"], 99)