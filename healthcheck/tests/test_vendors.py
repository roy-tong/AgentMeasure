"""Vendor-rule recount tests: Tier 1 applies the vendor's own published rules."""
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck.vendors import (AGREES, BILLABLE_BUT_NOT_BILLED,
                                    BILLED_BUT_NOT_BILLABLE, CANNOT_SETTLE,
                                    get_vendor, list_vendors, load_export,
                                    recount, recount_report)

HEADER = ("conversation_id,human_agent_participated,issue_addressed,"
          "customer_recontacted_within_window,vendor_billed\n")


def write_export(rows):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                      encoding="utf-8", newline="")
    tmp.write(HEADER)
    for r in rows:
        tmp.write(",".join(r) + "\n")
    tmp.close()
    return tmp.name


class TestRegistry(unittest.TestCase):
    def test_known_vendors(self):
        for vid in ("intercom", "zendesk", "hubspot", "ada", "salesforce", "generic"):
            self.assertIn(vid, [v["id"] for v in list_vendors()])

    def test_unknown_vendor_raises(self):
        with self.assertRaises(ValueError):
            get_vendor("nope")

    def test_every_vendor_cites_a_source(self):
        # Tier 1 is only unarguable if the rule is attributable.
        for v in list_vendors():
            self.assertTrue(v["source"], "%s has no source" % v["id"])
            self.assertIn(v["confidence"], ("P", "S", "U"))

    def test_zendesk_silence_does_not_bill(self):
        # The corrected rule: Zendesk is the most conservative, not the most
        # aggressive. Silence alone is free; only an LLM verdict bills.
        zd = get_vendor("zendesk")
        self.assertFalse(zd["silence_bills"])
        self.assertEqual(zd["billing_trigger"], "llm_verified_only")

    def test_intercom_silence_bills(self):
        ic = get_vendor("intercom")
        self.assertTrue(ic["silence_bills"])
        self.assertEqual(ic["reopen_deduction"], "documented_including_cross_period")


class TestRecount(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _recount(self, rows, vendor="intercom"):
        p = write_export(rows)
        self.paths.append(p)
        return recount(load_export(p), vendor)

    def test_agrees_when_vendor_follows_its_own_rule(self):
        r = self._recount([("C1", "no", "yes", "no", "yes")])
        self.assertEqual(r["counts"][AGREES], 1)
        self.assertEqual(r["net_findings"], 0)

    def test_reopen_is_billed_but_not_billable(self):
        # Intercom documents a reopen deduction, so a billed reopen is an overcharge.
        r = self._recount([("C1", "no", "yes", "yes", "yes")])
        self.assertEqual(r["counts"][BILLED_BUT_NOT_BILLABLE], 1)

    def test_human_finish_is_not_an_ai_resolution(self):
        r = self._recount([("C1", "yes", "yes", "no", "yes")])
        self.assertEqual(r["counts"][BILLED_BUT_NOT_BILLABLE], 1)

    def test_unaddressed_is_not_billable(self):
        r = self._recount([("C1", "no", "no", "no", "yes")])
        self.assertEqual(r["counts"][BILLED_BUT_NOT_BILLABLE], 1)

    def test_underbilling_is_reported_too(self):
        r = self._recount([("C1", "no", "yes", "no", "no")])
        self.assertEqual(r["counts"][BILLABLE_BUT_NOT_BILLED], 1)

    def test_missing_field_lowers_verdict_not_guesses(self):
        r = self._recount([("C1", "", "yes", "no", "yes")])
        self.assertEqual(r["counts"][CANNOT_SETTLE], 1)
        self.assertEqual(r["counts"][BILLED_BUT_NOT_BILLABLE], 0)

    def test_zendesk_verified_cannot_be_decided_from_counts(self):
        # The adjudication is the vendor's own model output, which a counts-only
        # export does not carry. We do not invent it in either direction.
        r = self._recount([("C1", "no", "yes", "no", "yes")], vendor="zendesk")
        self.assertEqual(r["counts"][CANNOT_SETTLE], 1)

    def test_net_is_over_minus_under(self):
        r = self._recount([
            ("C1", "no", "yes", "yes", "yes"),   # over
            ("C2", "no", "yes", "yes", "yes"),   # over
            ("C3", "no", "yes", "no", "no"),     # under
        ])
        self.assertEqual(r["net_findings"], 1)

    def test_variance_is_net_times_price(self):
        r = self._recount([
            ("C1", "no", "yes", "yes", "yes"),
            ("C2", "no", "yes", "no", "no"),
        ])
        self.assertAlmostEqual(r["variance"], 0.0)   # 1 over - 1 under = 0
        self.assertAlmostEqual(r["overcharge_amount"], 0.99)
        self.assertAlmostEqual(r["undercharge_amount"], 0.99)

    def test_missing_required_column_marks_all_rows(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8", newline="")
        # human_agent_participated column absent entirely
        tmp.write("conversation_id,issue_addressed,"
                  "customer_recontacted_within_window,vendor_billed\n")
        tmp.write("C1,yes,no,yes\n")
        tmp.close()
        self.paths.append(tmp.name)
        export = load_export(tmp.name)
        self.assertIn("human_agent_participated", export["columns_missing"])
        r = recount(export, "intercom")
        self.assertEqual(r["counts"][CANNOT_SETTLE], 1)


class TestRealFixture(unittest.TestCase):
    def test_shipped_fixture_recounts(self):
        r = recount(load_export(fixture("vendor-export-intercom.csv")), "intercom")
        self.assertEqual(r["total_conversations"], 10)
        self.assertEqual(r["billed_by_vendor"], 8)
        self.assertEqual(r["counts"][BILLED_BUT_NOT_BILLABLE], 4)
        self.assertEqual(r["counts"][BILLABLE_BUT_NOT_BILLED], 2)
        self.assertEqual(r["counts"][CANNOT_SETTLE], 2)
        self.assertEqual(r["counts"][AGREES], 2)
        self.assertEqual(r["net_findings"], 2)

    def test_report_states_both_directions(self):
        r = recount(load_export(fixture("vendor-export-intercom.csv")), "intercom")
        text = recount_report(r)
        self.assertIn("billed but not billable", text)
        self.assertIn("billable but not billed", text)
        self.assertIn("netted before any dollar", text)
        self.assertIn("removed from the claim, not zeroed", text)


class TestRecountCli(unittest.TestCase):
    """The recount subcommand: parse, list, and produce a report."""

    def test_parser_has_recount(self):
        from am_healthcheck.cli import build_parser
        args = build_parser().parse_args(
            ["recount", "--export", "x.csv", "--vendor", "intercom"])
        self.assertEqual(args.cmd, "recount")
        self.assertEqual(args.vendor, "intercom")

    def test_list_vendors_exits_zero(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["recount", "--list-vendors"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("intercom", out)
        self.assertIn("source:", out)

    def test_missing_args_is_usage_error(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["recount", "--vendor", "intercom"])
        self.assertEqual(rc, 2)

    def test_unknown_vendor_is_usage_error(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["recount", "--export", fixture("vendor-export-intercom.csv"),
                       "--vendor", "nope"])
        self.assertEqual(rc, 2)

    def test_recount_writes_json(self):
        import contextlib
        import io
        import json as _json
        from am_healthcheck.cli import main
        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
        self.addCleanup(lambda: os.path.exists(out) and os.unlink(out))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["recount", "--export", fixture("vendor-export-intercom.csv"),
                       "--vendor", "intercom", "--json", out])
        self.assertEqual(rc, 0)
        payload = _json.load(open(out, encoding="utf-8"))
        self.assertEqual(payload["vendor_id"], "intercom")
        self.assertEqual(payload["net_findings"], 2)


if __name__ == "__main__":
    unittest.main()

class TestNativeHeaderAliases(unittest.TestCase):
    """F1.1a: real vendor export headers use display forms with spaces
    ("Ticket ID", "Solved at"). After lower() they keep the space, so the
    alias table must carry the space forms or native exports silently fail
    to map."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _export(self, header):
        path = os.path.join(self.tmp.name, "export.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(",".join(header) + "\n")
        return path

    def test_zendesk_style_headers_map(self):
        from am_healthcheck.vendors import load_export
        path = self._export([
            "Ticket ID", "Created at", "Solved at",
            "human_agent_participated", "issue_addressed",
            "customer_recontacted_within_window", "vendor_billed"])
        export = load_export(path)
        self.assertIn("conversation_id", export["columns_found"])
        self.assertIn("opened_at", export["columns_found"])
        self.assertIn("closed_at", export["columns_found"])
        self.assertEqual(export["columns_missing"], [])

    def test_intercom_label_headers_map(self):
        from am_healthcheck.vendors import load_export
        path = self._export([
            "Conversation ID", "Conversation created at",
            "human_agent_participated", "issue_addressed",
            "customer_recontacted_within_window", "vendor_billed"])
        export = load_export(path)
        self.assertIn("conversation_id", export["columns_found"])
        self.assertIn("opened_at", export["columns_found"])
