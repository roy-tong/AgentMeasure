"""Drill-down and decision-journal tests (BP r32 p09 promise ② and the
third value book).

The drill-down must agree with the recount verdict for verdict, not just
vibe: every row of the fixture replayed through explain_one has to land on
the same verdict the engine produced. The decision journal keeps its books
separate — enum-validated types, context amounts never summed with recovery.
"""
import json
import os
import tempfile
import unittest

from _support import fixture

from verovo_healthcheck import drilldown as dd
from verovo_healthcheck import decisions as dec
from verovo_healthcheck.vendors import (AGREES, BILLABLE_BUT_NOT_BILLED,
                                    BILLED_BUT_NOT_BILLABLE, CANNOT_SETTLE,
                                    load_export, recount, get_vendor)

EXPORT = fixture("vendor-export-intercom.csv")


def tmpfile(suffix, text, mode="w"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding="utf-8", newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


class TestExplainOne(unittest.TestCase):
    def test_every_row_agrees_with_the_recount(self):
        export = load_export(EXPORT)
        engine = recount(export, "intercom")
        for i, rec in enumerate(export["records"]):
            explained = dd.explain_one(rec, get_vendor("intercom"))
            self.assertEqual(explained["verdict"],
                             engine["verdicts"][i]["verdict"],
                             "row %d diverges" % i)
            self.assertEqual(explained["verdict_3state"],
                             engine["verdicts"][i]["verdict_3state"])

    def test_reopen_row_names_the_documented_deduction(self):
        export = load_export(EXPORT)
        result = dd.drilldown(export, "intercom", conversation="C-1003")
        self.assertEqual(result["verdict"], BILLED_BUT_NOT_BILLABLE)
        blob = "\n".join(result["steps"])
        self.assertIn("came back inside the window", blob)
        self.assertIn("reopen deduction", blob)
        self.assertEqual(result["amount_at_issue"], 0.99)

    def test_zendesk_silence_is_unprovable_not_a_pass(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n"
                "Z-1,no,yes,no,yes\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = dd.drilldown(load_export(path), "zendesk",
                              conversation="Z-1")
        self.assertEqual(result["verdict"], CANNOT_SETTLE)
        self.assertIn("adjudication", "\n".join(result["steps"]))

    def test_human_finish_explains_the_rule(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n"
                "H-1,yes,yes,no,yes\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = dd.drilldown(load_export(path), "intercom",
                              conversation="H-1")
        self.assertEqual(result["verdict"], BILLED_BUT_NOT_BILLABLE)
        self.assertIn("human finished the conversation",
                      "\n".join(result["steps"]))

    def test_missing_field_says_so(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n"
                "M-1,,yes,no,yes\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = dd.drilldown(load_export(path), "intercom",
                              conversation="M-1")
        self.assertEqual(result["verdict"], CANNOT_SETTLE)
        self.assertIn("Evidence is incomplete", result["steps"][1])

    def test_underbilling_also_replays(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n"
                "U-1,no,yes,no,no\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = dd.drilldown(load_export(path), "intercom",
                              conversation="U-1")
        self.assertEqual(result["verdict"], BILLABLE_BUT_NOT_BILLED)
        self.assertIn("their favour", "\n".join(result["steps"]))


class TestDrilldownRender(unittest.TestCase):
    def test_text_and_markdown_carry_the_repro_command(self):
        export = load_export(EXPORT)
        result = dd.drilldown(export, "intercom", line=4)  # C-1003
        text = dd.drilldown_text(result, "filled.csv")
        md = dd.drilldown_markdown(result, "filled.csv")
        for doc in (text, md):
            self.assertIn("verovo recount --export filled.csv", doc)
            self.assertIn("C-1003", doc)
            self.assertIn("billed_but_not_billable", doc)
        self.assertIn("| field | value |", md)

    def test_line_lookup(self):
        result = dd.drilldown(load_export(EXPORT), "intercom", line=2)
        self.assertEqual(result["conversation_id"], "C-1001")
        self.assertEqual(result["verdict"], AGREES)

    def test_unknown_conversation_refused(self):
        with self.assertRaises(ValueError):
            dd.drilldown(load_export(EXPORT), "intercom",
                         conversation="NOPE")


class TestDrilldownCli(unittest.TestCase):
    def _run(self, *argv):
        import contextlib
        import io
        from verovo_healthcheck.cli import main
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(list(argv))
        return rc, out.getvalue()

    def test_cli_prints_replay(self):
        rc, out = self._run("drilldown", "--export", EXPORT,
                            "--vendor", "intercom",
                            "--conversation", "C-1003")
        self.assertEqual(rc, 0)
        self.assertIn("One finding, fully replayed", out)
        self.assertIn("reopen deduction", out)

    def test_cli_writes_markdown(self):
        md = tmpfile(".md", "")
        self.addCleanup(lambda: os.path.exists(md) and os.unlink(md))
        rc, out = self._run("drilldown", "--export", EXPORT,
                            "--vendor", "intercom", "--conversation",
                            "C-1003", "--md", md)
        self.assertEqual(rc, 0)
        with open(md, encoding="utf-8") as fh:
            self.assertIn("step by step", fh.read())


class TestDecisions(unittest.TestCase):
    def test_log_and_report(self):
        path = tmpfile(".jsonl", "")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        dec.log_entry(path, "ACME", "intercom", "renewal_signed",
                      linked="C-1003", outcome="resolved",
                      note="same terms, after review")
        dec.log_entry(path, "ACME", "intercom", "payment_held",
                      amount=120.0)
        entries = dec.load_entries(path)
        self.assertEqual(len(entries), 2)
        rep = dec.report(entries)
        self.assertEqual(rep["by_type"]["renewal_signed"], 1)
        self.assertEqual(rep["pending"], 1)
        text = dec.report_text(rep)
        self.assertIn("third value book", text)
        self.assertIn("renewal_signed", text)
        self.assertIn("never added to recovered cash", text)

    def test_enum_and_amount_guards(self):
        path = tmpfile(".jsonl", "")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(dec.DecisionError):
            dec.log_entry(path, "A", "v", "vibes")
        with self.assertRaises(dec.DecisionError):
            dec.log_entry(path, "A", "v", "payment_held", outcome="done")
        with self.assertRaises(dec.DecisionError):
            dec.log_entry(path, "A", "v", "payment_held", amount=-5)

    def test_whole_review_link_default(self):
        path = tmpfile(".jsonl", "")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        entry = dec.log_entry(path, "ACME", "zendesk", "vendor_review")
        self.assertEqual(entry["linked"], "(whole review)")
        self.assertIsNone(entry["amount"])

    def test_cli_log_and_read(self):
        import contextlib
        import io
        from verovo_healthcheck.cli import main
        path = tmpfile(".jsonl", "")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["decisions", "--log", path, "--log-event",
                       "--engagement", "ACME", "--vendor", "intercom",
                       "--type", "discount_requested", "--linked", "C-1004"])
        self.assertEqual(rc, 0)
        out2 = io.StringIO()
        with contextlib.redirect_stdout(out2):
            rc = main(["decisions", "--log", path])
        self.assertEqual(rc, 0)
        self.assertIn("discount_requested", out2.getvalue())

    def test_cli_bad_type_exits_two(self):
        # argparse rejects the non-enum choice with usage error (exit 2)
        import contextlib
        import io
        from verovo_healthcheck.cli import main
        err = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stderr(err):
            main(["decisions", "--log", "/tmp/x.jsonl", "--log-event",
                  "--engagement", "A", "--vendor", "v", "--type", "vibes"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()


class TestAdapterCanary(unittest.TestCase):
    """H1: the canary must go RED when an adapter stops parsing its pinned
    generation — that red names the adapter, before users see zero-session
    reports."""

    def _import_canary(self):
        import importlib.util
        from _support import REPO_ROOT
        from pathlib import Path as _P
        spec = importlib.util.spec_from_file_location(
            "adapter_canary", _P(REPO_ROOT) / "scripts" / "adapter_canary.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _manifest(self, sample_name):
        return {"canaries": {"codex": {
            "sample": sample_name,
            "captured_cli_version": "0.153.0",
            "captured_on": "2026-09-01",
            "max_corrupt": 0,
            "format_markers": ["0.153.0"]}}}

    def test_pinned_generation_parses_green(self):
        mod = self._import_canary()
        results = mod.run_canaries()
        self.assertTrue(results, "no canaries ran")
        for r in results:
            self.assertTrue(r["ok"], r)

    def test_tampered_sample_goes_red_and_names_the_problem(self):
        import shutil
        import tempfile
        from pathlib import Path
        mod = self._import_canary()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        # corrupt: strip the session_meta line so the adapter parses nothing
        from _support import REPO_ROOT as _R
        src = (Path(_R) / "healthcheck" / "fixtures" / "canary" /
               "codex.jsonl").read_text(encoding="utf-8").splitlines()
        tampered = "\n".join(l for l in src if '"session_meta"' not in l) + "\n"
        (tmp / "codex.jsonl").write_text(tampered, encoding="utf-8")
        results = mod.run_canaries(self._manifest("codex.jsonl"), canary_dir=tmp)
        self.assertFalse(results[0]["ok"])
        self.assertTrue(results[0]["problems"])
