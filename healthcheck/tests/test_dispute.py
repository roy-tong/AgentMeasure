"""Dispute & Recovery Pack tests: the negotiable deliverable."""
import json
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck.dispute import (build_pack, render_cover_letter,
                                    render_pack_markdown, write_pack)

EXPORT = fixture("vendor-export-intercom.csv")


class TestBuildPack(unittest.TestCase):
    def test_pack_has_both_tiers(self):
        p = build_pack(EXPORT, "intercom",
                       effects_path=os.path.join(
                           os.path.dirname(os.path.dirname(os.path.dirname(
                               os.path.abspath(__file__)))),
                           "conformance", "evidence", "assumed-resolution",
                           "fixture.jsonl"),
                       price=0.99)
        self.assertEqual(p["schema"], "agentmeasure.commercial/dispute-pack")
        self.assertIsNotNone(p["tier1"])
        self.assertIsNotNone(p["tier2"])
        self.assertEqual(p["tier1"]["counts"]["billed_but_not_billable"], 4)

    def test_pack_without_effects_still_works(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        self.assertIsNone(p["tier2"])
        self.assertEqual(p["claim"]["net"], 2)

    def test_claim_nets_before_claiming(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        d = p["claim"]["dollars"]
        self.assertAlmostEqual(d["overcharge"], 3.96)
        self.assertAlmostEqual(d["undercharge"], 1.98)
        self.assertAlmostEqual(d["net_variance"], 1.98)
        self.assertIn("netted", p["claim"]["netting_rule"])

    def test_cannot_settle_is_removed_not_zeroed(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        self.assertEqual(p["claim"]["cannot_settle"], 2)
        self.assertAlmostEqual(p["claim"]["dollars"]["cannot_settle_removed"], 1.98)
        self.assertIn("not zeroed", p["claim"]["cannot_settle_rule"])

    def test_payback_only_when_cost_and_variance_given(self):
        p = build_pack(EXPORT, "intercom", price=0.99, audit_cost=2500)
        self.assertIn("payback", p["claim"])
        self.assertGreater(p["claim"]["payback"]["months_to_payback"], 0)
        p2 = build_pack(EXPORT, "intercom", price=0.99)
        self.assertNotIn("payback", p2["claim"])

    def test_provenance_hashes_inputs(self):
        p = build_pack(EXPORT, "intercom")
        self.assertEqual(len(p["inputs"]["export_sha256"]), 64)

    def test_unknown_vendor_raises(self):
        with self.assertRaises(ValueError):
            build_pack(EXPORT, "not-a-vendor")


class TestCoverLetter(unittest.TestCase):
    def test_letter_cites_the_vendor_rule_not_ours(self):
        p = build_pack(EXPORT, "intercom", price=0.99, buyer_label="Acme")
        letter = render_cover_letter(p)
        self.assertIn("your published rules", letter)
        self.assertIn("Acme", letter)
        self.assertIn("fin.ai", letter)          # the cited source
        self.assertIn("We would welcome a correction", letter)

    def test_letter_reports_the_favourable_direction(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        letter = render_cover_letter(p)
        self.assertIn("not billed", letter)
        self.assertIn("would not be a statement", letter)

    def test_letter_states_cannot_settle_handling(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        self.assertIn("removed them from this claim", render_cover_letter(p))


class TestMarkdownPack(unittest.TestCase):
    def test_appendix_lists_disputed_with_line_numbers(self):
        md = render_pack_markdown(build_pack(EXPORT, "intercom", price=0.99))
        self.assertIn("Disputed conversations", md)
        self.assertIn("`C-1003`", md)
        self.assertIn("export line", md)

    def test_appendix_separates_cannot_settle(self):
        md = render_pack_markdown(build_pack(EXPORT, "intercom"))
        self.assertIn("Cannot settle (removed from the claim)", md)
        self.assertIn("`C-1009`", md)

    def test_pack_states_no_message_text_read(self):
        md = render_pack_markdown(build_pack(EXPORT, "intercom"))
        self.assertIn("No message text", md)

    def test_write_pack_produces_both_files(self):
        p = build_pack(EXPORT, "intercom", price=0.99)
        with tempfile.TemporaryDirectory() as d:
            paths = write_pack(p, d)
            self.assertTrue(os.path.isfile(paths["json"]))
            self.assertTrue(os.path.isfile(paths["markdown"]))
            payload = json.load(open(paths["json"], encoding="utf-8"))
            self.assertEqual(payload["claim"]["net"], 2)


class TestDisputeCli(unittest.TestCase):
    def test_parser_has_dispute(self):
        from am_healthcheck.cli import build_parser
        args = build_parser().parse_args(
            ["dispute", "--export", "x.csv", "--vendor", "intercom"])
        self.assertEqual(args.cmd, "dispute")

    def test_dispute_end_to_end(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["dispute", "--export", EXPORT, "--vendor", "intercom",
                           "--price", "0.99", "--out", d, "--buyer", "Acme"])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join(d, "dispute-pack.md")))
            self.assertTrue(os.path.isfile(os.path.join(d, "dispute-pack.json")))

    def test_inspect_produces_no_numbers(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["recount", "--export", EXPORT, "--vendor", "intercom",
                       "--inspect"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Column alignment", out)
        self.assertIn("no numbers produced", out)
        self.assertNotIn("billed but not billable", out)


if __name__ == "__main__":
    unittest.main()
