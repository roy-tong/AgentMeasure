"""Schema validation, the validate subcommand, and the external example."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _support import fixture, HEALTHCHECK_DIR, FIXTURES_DIR

from am_healthcheck import cli
from am_healthcheck import schema as schema_mod
from am_healthcheck import share as share_mod
from am_healthcheck import snapshot as snapshot_mod
from am_healthcheck.checks import run_checks, session_summaries
from am_healthcheck.codex import parse_session


def _build_snapshot(path=None):
    s = parse_session(fixture("codex-ok.jsonl"))
    ov, checks, _cov, _top = run_checks([s], "unit")
    snap = snapshot_mod.build_snapshot(ov, checks, session_summaries([s]),
                                       "synthetic-demo", "unit", "unit")
    if path:
        snapshot_mod.save_snapshot(snap, path)
    return snap


class TestSchemaValidator(unittest.TestCase):
    def test_valid_snapshot_passes(self):
        self.assertEqual(schema_mod.validate_snapshot(_build_snapshot()), [])

    def test_missing_required_field_fails(self):
        snap = _build_snapshot()
        del snap["overview"]["exec_total"]
        errors = schema_mod.validate_snapshot(snap)
        self.assertTrue(any("exec_total" in e for e in errors))

    def test_wrong_type_fails(self):
        snap = _build_snapshot()
        snap["overview"]["sessions"] = "thirteen"
        errors = schema_mod.validate_snapshot(snap)
        self.assertTrue(any("sessions" in e for e in errors))

    def test_future_schema_version_is_refused(self):
        snap = _build_snapshot()
        snap["schema"] = 99
        self.assertTrue(schema_mod.validate_snapshot(snap))

    def test_detect_kind(self):
        snap = _build_snapshot()
        self.assertEqual(schema_mod.detect_kind(snap), "snapshot")
        self.assertEqual(schema_mod.detect_kind({"hello": 1}), None)

    def test_report_requires_share_summary_shape(self):
        errors = schema_mod.validate_report({"schema": 1, "tool": "other"})
        self.assertTrue(errors)


class TestValidateCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _run(self, argv, expect):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(io.StringIO()):
            code = cli.main(argv)
        self.assertEqual(code, expect)
        return buf_out.getvalue()

    def test_valid_files_pass(self):
        snap = os.path.join(self.tmp.name, "s.json")
        _build_snapshot(snap)
        out = self._run(["validate", snap], expect=0)
        self.assertIn("valid snapshot", out)
        self.assertIn("PASS", out)

    def test_broken_file_fails_with_reason(self):
        snap = os.path.join(self.tmp.name, "broken.json")
        data = _build_snapshot()
        data["schema"] = 99
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        out = self._run(["validate", snap], expect=2)
        self.assertIn("INVALID", out)
        self.assertIn("schema", out)

    def test_not_json_fails(self):
        path = os.path.join(self.tmp.name, "x.json")
        with open(path, "w") as fh:
            fh.write("not json")
        self._run(["validate", path], expect=2)

    def test_unknown_document_fails(self):
        path = os.path.join(self.tmp.name, "y.json")
        with open(path, "w") as fh:
            json.dump({"hello": 1}, fh)
        out = self._run(["validate", path], expect=2)
        self.assertIn("not an AgentMeasure export", out)


class TestExternalExample(unittest.TestCase):
    """The R8 story: an outside consumer reads snapshots via schema only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _example(self, *paths):
        script = os.path.join(HEALTHCHECK_DIR, "examples", "track-weekly.py")
        proc = subprocess.run([sys.executable, script] + list(paths),
                              capture_output=True, text=True)
        return proc

    def test_reads_two_snapshots(self):
        a = os.path.join(self.tmp.name, "a.json")
        b = os.path.join(self.tmp.name, "b.json")
        _build_snapshot(a)
        _build_snapshot(b)
        proc = self._example(a, b)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("snapshot", proc.stdout)
        self.assertIn("verdicts", proc.stdout)

    def test_refuses_future_schema(self):
        path = os.path.join(self.tmp.name, "future.json")
        snap = _build_snapshot()
        snap["schema"] = 2
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snap, fh)
        proc = self._example(path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("schema", proc.stderr)


class TestShareCommand(unittest.TestCase):
    """R4: preview-then-export — nothing leaves the machine before review."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        old = os.environ.get("HOME")
        os.environ["HOME"] = os.path.join(self.tmp.name, "home")
        os.makedirs(os.environ["HOME"], exist_ok=True)
        self.addCleanup(lambda: os.environ.__setitem__("HOME", old) if old
                        else os.environ.pop("HOME", None))

    def _run(self, argv, expect=0):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(io.StringIO()):
            code = cli.main(argv)
        self.assertEqual(code, expect,
                         "stdout:\n%s\nstderr:\n%s" % (buf_out.getvalue(),
                                                       buf_err.getvalue()))
        return buf_out.getvalue()

    def _report(self):
        report = os.path.join(self.tmp.name, "run.json")
        self._run(["check", "--dir", FIXTURES_DIR,
                   "--html", os.path.join(self.tmp.name, "r.html"),
                   "--json", report, "--no-history"])
        return report

    def test_preview_writes_nothing_by_default(self):
        report = self._report()
        out = self._run(["share", report])
        self.assertIn("preview", out)
        self.assertIn("nothing was written", out)
        self.assertFalse([f for f in os.listdir(self.tmp.name)
                          if f.startswith("summary")])

    def test_preview_is_sanitized(self):
        out = self._run(["share", self._report()])
        for planted in ("secret-project", "Users/tongxiarui", "call_demo_1",
                        "SESSIONUUID", "deploy-prod"):
            self.assertNotIn(planted, out)

    def test_export_only_with_out(self):
        report = self._report()
        dest = os.path.join(self.tmp.name, "summary.md")
        out = self._run(["share", report, "--out", dest])
        self.assertIn("reviewed the preview", out)
        self.assertTrue(os.path.isfile(dest))

    def test_json_variant(self):
        report = self._report()
        dest = os.path.join(self.tmp.name, "summary.json")
        self._run(["share", report, "--out", dest])
        with open(dest) as fh:
            payload = json.load(fh)
        self.assertEqual(payload["tool"], "AgentMeasure Healthcheck")

    def test_snapshot_file_rejected(self):
        snap = os.path.join(self.tmp.name, "s.json")
        self._run(["check", "--dir", FIXTURES_DIR,
                   "--html", os.path.join(self.tmp.name, "r.html"),
                   "--save-snapshot", snap, "--no-history"])
        out = self._run(["share", snap], expect=2)

    def test_tampered_summary_refused(self):
        report = self._report()
        with open(report, encoding="utf-8") as fh:
            data = json.load(fh)
        data["share_summary"]["my_prompts"] = ["hello"]
        with open(report, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        self._run(["share", report], expect=2)


class TestSummaryWhitelist(unittest.TestCase):
    def test_extra_key_is_a_problem(self):
        problems = share_mod.summary_problems({"tool": "x", "extra": 1})
        self.assertTrue(any("extra" in p for p in problems))

    def test_good_summary_has_no_problems(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        ov, checks, _cov, _top = run_checks([s], "unit")
        summary = share_mod.build_share_summary(ov, checks, "synthetic-demo", "u")
        self.assertEqual(share_mod.summary_problems(summary), [])


if __name__ == "__main__":
    unittest.main()
