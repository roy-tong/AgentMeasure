"""End-to-end CLI tests: demo run, exit codes, outputs, history behavior."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _support import HEALTHCHECK_DIR

from am_healthcheck import cli
from am_healthcheck import history as history_mod

sys.path.insert(0, os.path.join(HEALTHCHECK_DIR))


class CliHarness(unittest.TestCase):
    def run_cli(self, argv, expect_code=0):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            code = cli.main(argv)
        self.assertEqual(code, expect_code,
                         "stdout:\n%s\nstderr:\n%s" % (buf_out.getvalue(),
                                                       buf_err.getvalue()))
        return buf_out.getvalue(), buf_err.getvalue()


class TestDemoRun(CliHarness):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.home, exist_ok=True)
        self.addCleanup(self.tmp.cleanup)
        self._old_home = os.environ.get("HOME")

    def tearDown(self):
        if self._old_home is not None:
            os.environ["HOME"] = self._old_home

    def test_demo_produces_report_and_summary(self):
        html = os.path.join(self.tmp.name, "demo.html")
        jsn = os.path.join(self.tmp.name, "demo.json")
        share = os.path.join(self.tmp.name, "share.md")
        out, _err = self.run_cli([
            "demo", "--html", html, "--json", jsn, "--share", share,
            "--no-history"])
        self.assertIn("run #", out)
        self.assertTrue(os.path.isfile(html))
        with open(html, encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("SYNTHETIC DEMO", body)
        self.assertIn("AgentMeasure Healthcheck", body)
        self.assertIn("demo --html", body)
        with open(share, encoding="utf-8") as fh:
            self.assertNotIn("secret-project", fh.read())
        with open(jsn, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["mode"], "synthetic-demo")
        self.assertIn("checks", payload)
        self.assertIn("share_summary", payload)

    def test_demo_history_distinguishes_runs(self):
        home2 = os.path.join(self.tmp.name, "home2")
        os.makedirs(home2, exist_ok=True)
        html = os.path.join(self.tmp.name, "d1.html")
        old = os.environ.get("HOME")
        os.environ["HOME"] = home2
        try:
            self.run_cli(["demo", "--html", html])
            self.run_cli(["demo", "--html", html])
        finally:
            if old is not None:
                os.environ["HOME"] = old
        entries = history_mod.load_history(home2)
        self.assertEqual(len(entries), 2)
        self.assertEqual(history_mod.run_number("synthetic-demo", home2), 3)

    def test_check_missing_dir_errors(self):
        self.run_cli(["check", "--dir", os.path.join(self.tmp.name, "nope")],
                     expect_code=2)

    def test_check_empty_dir_errors(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        self.run_cli(["check", "--dir", empty], expect_code=2)

    def test_check_explicit_fixture_dir(self):
        # fixtures dir contains no rollout-* names but check --dir accepts .jsonl
        out, _err = self.run_cli([
            "check", "--dir", os.path.join(HEALTHCHECK_DIR, "fixtures"),
            "--html", os.path.join(self.tmp.name, "fx.html"), "--no-history"])
        self.assertIn("reading", out)
        self.assertIn("HC-01", out)


class TestExitCodes(unittest.TestCase):
    def test_selftest_passes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["selftest"])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("selftest: PASS", buf.getvalue())

    def test_version_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("agentmeasure-healthcheck", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
