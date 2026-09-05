"""v0.2.0 features: snapshots, compare, project breakdown, date filters."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

from _support import fixture, HEALTHCHECK_DIR

from am_healthcheck import cli
from am_healthcheck.checks import build_overview, run_checks, session_summaries
from am_healthcheck.codex import parse_session
from am_healthcheck.discover import filter_by_date, parse_date
from am_healthcheck.share import build_share_summary, share_json
from am_healthcheck import snapshot as snapshot_mod


class CliHarness(unittest.TestCase):
    def run_cli(self, argv, expect_code=0):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            code = cli.main(argv)
        self.assertEqual(code, expect_code,
                         "stdout:\n%s\nstderr:\n%s" % (buf_out.getvalue(),
                                                       buf_err.getvalue()))
        return buf_out.getvalue(), buf_err.getvalue()


class TestProjectDimension(unittest.TestCase):
    def test_project_extracted_from_cwd(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        self.assertEqual(s.project, "secret-project")

    def test_overview_projects_aggregate(self):
        s = parse_session(fixture("codex-retries.jsonl"))
        ov = build_overview([s], "test")
        self.assertEqual(len(ov.projects), 1)
        self.assertEqual(ov.projects[0]["project"], "project")
        self.assertEqual(ov.projects[0]["exec_total"], 10)
        self.assertEqual(ov.projects[0]["exec_failed"], 8)

    def test_project_name_stays_out_of_share(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        ov, checks, _cov, _top = run_checks([s], "test")
        summary = build_share_summary(ov, checks, "own-data", "test")
        self.assertNotIn("secret-project", share_json(summary))
        self.assertNotIn("projects", share_json(summary))

    def test_session_summaries_canonical(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        rows = session_summaries([s])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["exec_total"], 3)
        self.assertEqual(rows[0]["retry_chains"], 0)
        self.assertEqual(rows[0]["project"], "secret-project")


class TestDateFilters(unittest.TestCase):
    def test_parse_date_valid_and_invalid(self):
        self.assertEqual(parse_date("2026-09-01"),
                         datetime(2026, 9, 1, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            parse_date("09/01/2026")
        with self.assertRaises(ValueError):
            parse_date("2026-13-40")

    def test_filter_by_date_keeps_undated(self):
        with tempfile.TemporaryDirectory() as tmp:
            dated = os.path.join(tmp, "rollout-2026-08-01T10-00-00-abc.jsonl")
            newer = os.path.join(tmp, "rollout-2026-09-04T10-00-00-abc.jsonl")
            undated = os.path.join(tmp, "codex-ok.jsonl")
            for path in (dated, newer, undated):
                open(path, "w").close()
            kept, skipped, undated_count = filter_by_date(
                [dated, newer, undated], parse_date("2026-09-01"), None)
            self.assertEqual(kept, [newer, undated])
            self.assertEqual(skipped, 1)
            self.assertEqual(undated_count, 1)

    def test_cli_rejects_bad_since(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            code = cli.main(["check", "--since", "not-a-date"])
        self.assertEqual(code, 2)

    def test_cli_rejects_inverted_range(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            code = cli.main(["check", "--since", "2026-09-05",
                             "--until", "2026-09-01"])
        self.assertEqual(code, 2)


class TestSnapshotFlow(CliHarness):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = os.path.join(self.tmp.name, "home")
        os.makedirs(os.environ["HOME"], exist_ok=True)

    def tearDown(self):
        if self.old_home is not None:
            os.environ["HOME"] = self.old_home

    def test_check_saves_snapshot(self):
        snap = os.path.join(self.tmp.name, "snap.json")
        out, _err = self.run_cli([
            "check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
            "--html", os.path.join(self.tmp.name, "r.html"),
            "--save-snapshot", snap, "--no-history"])
        self.assertIn("Snapshot", out)
        data = snapshot_mod.load_snapshot(snap)
        self.assertEqual(data["schema"], 1)
        self.assertTrue(data["overview"]["exec_total"] >= 1)
        self.assertTrue(data["sessions"])

    def test_snapshot_flag_without_value_uses_default_name(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            out, _err = self.run_cli([
                "check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
                "--save-snapshot", "--no-history"])
            self.assertIn("agentmeasure-snapshot-", out)
            files = [f for f in os.listdir(self.tmp.name)
                     if f.startswith("agentmeasure-snapshot-")]
            self.assertEqual(len(files), 1)
        finally:
            os.chdir(cwd)

    def test_compare_two_snapshots(self):
        snap_a = os.path.join(self.tmp.name, "a.json")
        snap_b = os.path.join(self.tmp.name, "b.json")
        self.run_cli(["check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
                      "--html", os.path.join(self.tmp.name, "ra.html"),
                      "--save-snapshot", snap_a, "--no-history"])
        self.run_cli(["check", "--dir", os.path.join(HEALTHCHECK_DIR, "demo"),
                      "--html", os.path.join(self.tmp.name, "rb.html"),
                      "--save-snapshot", snap_b, "--no-history"])
        out, _err = self.run_cli(["compare", snap_a, snap_b])
        self.assertIn("HC-02", out)
        self.assertIn("changed", out)
        # windows differ → caveat disclosed
        self.assertIn("Caveats", out)

    def test_compare_one_snapshot_against_fresh_run(self):
        snap_a = os.path.join(self.tmp.name, "a.json")
        self.run_cli(["check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
                      "--html", os.path.join(self.tmp.name, "ra.html"),
                      "--save-snapshot", snap_a, "--no-history"])
        out, _err = self.run_cli([
            "compare", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"), snap_a,
            "--json", os.path.join(self.tmp.name, "cmp.json")])
        self.assertIn("fresh run", out)
        with open(os.path.join(self.tmp.name, "cmp.json")) as fh:
            payload = json.load(fh)
        self.assertEqual(payload["schema"], 1)
        self.assertIn("rows", payload)

    def test_compare_rejects_three_snapshots(self):
        self.run_cli(["compare", "a.json", "b.json", "c.json"], expect_code=2)

    def test_compare_rejects_foreign_file(self):
        path = os.path.join(self.tmp.name, "not-a-snapshot.json")
        with open(path, "w") as fh:
            json.dump({"hello": 1}, fh)
        self.run_cli(["compare", path], expect_code=2)

    def test_project_filter_and_known_projects_error(self):
        out, err = self.run_cli([
            "check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
            "--html", os.path.join(self.tmp.name, "rp.html"),
            "--project", "never-matches", "--no-history"], expect_code=2)
        self.assertIn("known projects", out + err)
        # --project match keeps only matching sessions
        out2, _err2 = self.run_cli([
            "check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
            "--html", os.path.join(self.tmp.name, "rp2.html"),
            "--project", "project", "--no-history"])
        self.assertIn("project ~project", out2)


class TestCompareContracts(unittest.TestCase):
    def setUp(self):
        from am_healthcheck.codex import parse_files
        self.a = snapshot_mod.build_snapshot(
            *self._run(fixture("codex-ok.jsonl"), "wa"),
            mode="synthetic-demo", window_label="wa", command="x")

    @staticmethod
    def _run(path, window):
        s = parse_session(path)
        ov, checks, _cov, _top = run_checks([s], window)
        return ov, checks, session_summaries([s])

    def test_version_mismatch_warns(self):
        b = snapshot_mod.build_snapshot(
            *self._run(fixture("codex-retries.jsonl"), "wa"),
            mode="synthetic-demo", window_label="wa", command="x")
        b["tool_version"] = "0.0.9"
        cmp = snapshot_mod.compare_snapshots(self.a, b)
        self.assertTrue(any("versions" in w for w in cmp["warnings"]))

    def test_mode_mismatch_warns(self):
        b = snapshot_mod.build_snapshot(
            *self._run(fixture("codex-retries.jsonl"), "wa"),
            mode="own-data", window_label="wa", command="x")
        cmp = snapshot_mod.compare_snapshots(self.a, b)
        self.assertTrue(any("modes differ" in w for w in cmp["warnings"]))

    def test_delta_formatting(self):
        cmp = snapshot_mod.compare_snapshots(self.a, self.a)
        for row in cmp["rows"]:
            self.assertEqual(row["delta"], "±0")
        text = snapshot_mod.render_compare_text(cmp)
        self.assertIn("Metric", text)


if __name__ == "__main__":
    unittest.main()
