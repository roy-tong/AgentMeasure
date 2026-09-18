"""History tests: record, load, trend aggregation, render."""
import os
import tempfile
import unittest

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
        self.assertEqual(run_number("own-data", home=self.home), 1)
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z"},
                   home=self.home)
        self.assertEqual(run_number("own-data", home=self.home), 2)

    def test_run_number_separate_modes(self):
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z"},
                   home=self.home)
        record_run({"mode": "synthetic-demo", "ts": "2026-01-15T10:00:01Z"},
                   home=self.home)
        self.assertEqual(run_number("own-data", home=self.home), 2)
        self.assertEqual(run_number("synthetic-demo", home=self.home), 2)

    def test_record_run_creates_history_dir(self):
        # history_path() only computes the path; record_run() is what creates
        # the ~/.agentmeasure directory tree.
        path = history_path(home=self.home)
        self.assertFalse(os.path.exists(os.path.dirname(path)))
        record_run({"mode": "own-data", "ts": "2026-01-15T10:00:00Z"},
                   home=self.home)
        self.assertTrue(os.path.isdir(os.path.dirname(path)))
        self.assertTrue(os.path.isfile(path))

    def test_load_history_missing_file_is_empty(self):
        self.assertEqual(load_history(home=self.home), [])


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
            "executions": execs,
            "failed": failed, "retry_chains": retry_chains,
            "checks": checks,
        }, home=self.home)

    def test_empty_history(self):
        t = trend(home=self.home)
        self.assertEqual(t["status"], "no_data")

    def test_no_real_data(self):
        record_run({"ts": "2026-01-15T10:00:00Z", "mode": "synthetic-demo"},
                   home=self.home)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "no_real_data")

    def test_trend_weekly_aggregation(self):
        self._record("2026-01-06T10:00:00Z", execs=10, retry_chains=1)
        self._record("2026-01-08T10:00:00Z", execs=20, failed=5)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "ok")
        self.assertEqual(t["total_runs"], 2)
        # both dates fall in ISO week 2026-W02
        self.assertIn("2026-W02", t["weekly"])
        wk = t["weekly"]["2026-W02"]
        self.assertEqual(wk["executions"], 30)
        self.assertEqual(wk["sessions"], 2)
        self.assertEqual(wk["failed"], 7)

    def test_trend_weekly_checks_aggregate(self):
        self._record("2026-01-06T10:00:00Z",
                     checks={"HC-01": "ok", "HC-02": "finding"})
        self._record("2026-01-08T10:00:00Z",
                     checks={"HC-01": "finding", "HC-02": "finding"})
        t = trend(home=self.home)
        wkc = t["weekly_checks"]["2026-W02"]
        self.assertEqual(wkc["HC-01"]["total"], 2)
        self.assertEqual(wkc["HC-01"]["ok"], 1)
        self.assertEqual(wkc["HC-01"]["finding"], 1)
        self.assertEqual(wkc["HC-02"]["finding"], 2)

    def test_trend_monthly_aggregation(self):
        self._record("2026-01-15T10:00:00Z", execs=10)
        self._record("2026-02-15T10:00:00Z", execs=25)
        t = trend(home=self.home)
        self.assertEqual(t["status"], "ok")
        self.assertIn("2026-01", t["monthly"])
        self.assertIn("2026-02", t["monthly"])
        self.assertEqual(t["monthly"]["2026-01"]["executions"], 10)
        self.assertEqual(t["monthly"]["2026-02"]["executions"], 25)

    def test_trend_latest_is_last_run(self):
        self._record("2026-01-06T10:00:00Z")
        self._record("2026-01-13T10:00:00Z", execs=99)
        t = trend(home=self.home)
        self.assertEqual(t["latest"]["executions"], 99)

    def test_trend_ignores_demo_runs(self):
        self._record("2026-01-06T10:00:00Z", mode="synthetic-demo", execs=999)
        self._record("2026-01-06T10:00:00Z", mode="own-data", execs=10)
        t = trend(home=self.home)
        self.assertEqual(t["total_runs"], 1)
        self.assertEqual(t["monthly"]["2026-01"]["executions"], 10)


class TestRenderTrend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home, exist_ok=True)

    def test_render_no_data(self):
        output = render_trend({"status": "no_data", "message": "no runs recorded"})
        self.assertEqual(output, "no runs recorded")

    def test_render_output_has_sections(self):
        record_run({"ts": "2026-01-06T10:00:00Z", "mode": "own-data",
                    "sessions": 1, "executions": 10, "failed": 1,
                    "retry_chains": 0, "checks": {"HC-01": "ok"}},
                   home=self.home)
        output = render_trend(trend(home=self.home))
        self.assertIn("Trend Report", output)
        self.assertIn("2026-W02", output)
        self.assertIn("HC-01", output)

    def test_render_no_real_data_message(self):
        t = {"status": "no_real_data", "message": "no own-data runs recorded yet"}
        self.assertEqual(render_trend(t), "no own-data runs recorded yet")


if __name__ == "__main__":
    unittest.main()
