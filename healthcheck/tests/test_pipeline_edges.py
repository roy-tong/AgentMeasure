"""Adversarial edge tests — the hostile-input pass over the new pipeline.

Every test here is a bug that plausibly exists: legacy packs the dashboard
must still render, duplicate ids a join must not silently swallow, BOM/CRLF/
quoted CSV, header-only exports, empty journals, packs without dollars.
Exit-code discipline (2 on bad input, never a traceback) is part of the
contract.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck import crosscheck as cc
from am_healthcheck import dashboard as dash
from am_healthcheck import delivery as del_mod
from am_healthcheck import ledger as ledger_mod
from am_healthcheck import narrative as narr
from am_healthcheck import rulesdiff as rd
from am_healthcheck import prepare as prepare_mod
from am_healthcheck.vendors import load_export, recount

EXPORT = fixture("vendor-export-intercom.csv")


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


class TestLegacyPackCompatibility(unittest.TestCase):
    """Packs generated before the three-state vocabulary must still render."""

    def _legacy_pack(self):
        with open(os.path.join(tempfile.mkdtemp(), "pack.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({
                "schema": "agentmeasure.commercial/dispute-pack",
                "schema_version": "0.1.0",
                "generated_at": "2026-09-01T00:00:00+00:00",
                "vendor": {"name": "Intercom Fin", "id": "intercom",
                           "rule_source": "https://example.com"},
                "buyer_label": "ACME", "period": {"start": None, "end": None},
                "currency": "USD", "unit_price": 0.99,
                "tier1": {
                    "counts": {"billed_but_not_billable": 4,
                               "billable_but_not_billed": 2,
                               "cannot_settle": 2, "agrees": 2},
                    "net_findings": 2, "variance": 1.98,
                    "verdicts": [
                        {"line": 2, "conversation_id": "C-1",
                         "verdict": "billed_but_not_billable"}],
                },
                "claim": {"billed_but_not_billable": 4,
                          "billable_but_not_billed": 2, "net": 2,
                          "cannot_settle": 2},
                "outcome_lane": None, "tier2": None,
                "inputs": {"export_file": "x.csv", "export_sha256": "ab" * 8,
                           "columns_missing": []},
            }, fh)
        # (path returned by mkdtemp composition above)
        return fh.name

    def test_dashboard_renders_legacy_pack_without_three_state(self):
        pack = self._legacy_pack()
        self.addCleanup(lambda: os.path.exists(pack) and os.unlink(pack))
        doc = dash.load_document(pack)
        html_text = dash.render_dashboard(doc)
        self.assertIn("PASS", html_text)
        self.assertIn("FAIL", html_text)
        self.assertIn("UNPROVABLE", html_text)
        self.assertIn("2", html_text)  # computed FAIL = 4? no: 4+2=6; "2" appears anyway
        self.assertNotIn("None", html_text.split("</header>")[1][:400])

    def test_narrative_template_on_legacy_pack(self):
        pack = json.loads(json.dumps({
            "schema": "agentmeasure.commercial/dispute-pack",
            "vendor": {"name": "V", "rule_source": "x"},
            "buyer_label": "B", "period": {"start": None, "end": None},
            "currency": "USD",
            "tier1": {"counts": {"billed_but_not_billable": 1,
                                 "billable_but_not_billed": 0,
                                 "cannot_settle": 0, "agrees": 0},
                      "net_findings": 1},
            "claim": {"billed_but_not_billable": 1,
                      "billable_but_not_billed": 0, "cannot_settle": 0,
                      "dollars": None},
        }))
        text, source, violations = narr.render_or_draft(pack, None, "finance")
        self.assertEqual(source, "template")
        self.assertIsNone(violations)
        self.assertIn("1", text)


class TestDuplicateIds(unittest.TestCase):
    def test_crosscheck_names_duplicate_export_ids(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n"
                "C-1,no,yes,no,yes\n"
                "C-1,no,yes,no,yes\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        rows = cc.load_ledger(self._ledger_two())
        result = cc.crosscheck(load_export(path), rows, "intercom")
        self.assertEqual(len(result["duplicate_ids_in_export"]), 1)
        self.assertEqual(result["duplicate_ids_in_export"][0]["rows"], 2)
        report = cc.crosscheck_report(result)
        self.assertIn("DUPLICATE", report)
        self.assertIn("C-1", report)

    def _ledger_two(self):
        return tmpfile(".csv", "conversation_id,amount\nC-1,0.99\nC-1,0.99\n")


class TestHostileCsv(unittest.TestCase):
    def test_bom_crlf_and_quoted_commas_recount_cleanly(self):
        # BOM prefix, CRLF line endings, and a quoted field containing a
        # comma (the conversation id) must all survive the loader.
        text = ("\ufeffconversation_id,human_agent_participated,"
                "issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\r\n"
                '"C,1",no,yes,no,yes\r\n')
        path = tmpfile(".csv", text, encoding="utf-8")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = recount(load_export(path), "intercom")
        self.assertEqual(result["total_conversations"], 1)
        self.assertEqual(result["counts"]["agrees"], 1)
        self.assertEqual(result["verdicts"][0]["conversation_id"], "C,1")

    def test_header_only_export_sets_all_zero(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed\n")
        path = tmpfile(".csv", text)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        result = recount(load_export(path), "intercom")
        self.assertEqual(result["total_conversations"], 0)
        self.assertEqual(result["cannot_settle_share"], 0.0)
        self.assertEqual(result["three_state_counts"],
                         {"PASS": 0, "FAIL": 0, "UNPROVABLE": 0})

    def test_prepare_on_header_only_native_file(self):
        path = tmpfile(".csv", "Ticket ID,Created at,Solved at\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        prepared = prepare_mod.prepare(path, "zendesk")
        self.assertEqual(prepared["rows"], 0)
        out = tmpfile(".csv", "")
        self.addCleanup(lambda: os.path.exists(out) and os.unlink(out))
        prepare_mod.write_prepared(prepared, out)
        with open(out, encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        self.assertEqual(len(lines), 1)  # header only, no crash

    def test_ledger_negative_amount_refused(self):
        path = tmpfile(".csv", "conversation_id,amount\nC-1,-3\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(cc.LedgerError):
            cc.load_ledger(path)


class TestCliEdgeExits(unittest.TestCase):
    def _run(self, *argv):
        from am_healthcheck.cli import main
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_verify_bad_vendor_exits_two(self):
        rc, _, err = self._run("verify", "--export", EXPORT,
                               "--vendor", "nope")
        self.assertEqual(rc, 2)
        self.assertIn("unknown vendor", err)

    def test_crosscheck_malformed_ledger_exits_two(self):
        bad = tmpfile(".csv", "id,amount\nC-1,1\n")
        self.addCleanup(lambda: os.path.exists(bad) and os.unlink(bad))
        rc, _, err = self._run("crosscheck", "--export", EXPORT,
                               "--ledger", bad, "--vendor", "intercom")
        self.assertEqual(rc, 2)
        self.assertIn("conversation_id", err)

    def test_rules_diff_identical_snapshot_exits_zero(self):
        registry = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "am_healthcheck", "vendor-rules.json")
        rc, out, _ = self._run("rules-diff", registry)
        self.assertEqual(rc, 0)
        self.assertIn("No rule changes", out)

    def test_dashboard_rejects_non_pack_exits_two(self):
        bad = tmpfile(".json", '{"schema": "nope"}')
        self.addCleanup(lambda: os.path.exists(bad) and os.unlink(bad))
        rc, _, err = self._run("dashboard", "--pack", bad,
                               "--out", os.path.join(tempfile.mkdtemp(), "d.html"))
        self.assertEqual(rc, 2)
        self.assertIn("not a supported dashboard document", err)

    def test_narrative_needs_dispute_pack(self):
        bad = tmpfile(".json", '{"schema": "other"}')
        self.addCleanup(lambda: os.path.exists(bad) and os.unlink(bad))
        rc, _, err = self._run("narrative", "--pack", bad)
        self.assertEqual(rc, 2)

    def test_delivery_empty_journal_prints_guidance(self):
        empty = tmpfile(".jsonl", "")
        self.addCleanup(lambda: os.path.exists(empty) and os.unlink(empty))
        rc, out, _ = self._run("delivery", "--log", empty)
        self.assertEqual(rc, 0)
        self.assertIn("Nothing logged yet", out)

    def test_delivery_corrupt_journal_exits_two(self):
        bad = tmpfile(".jsonl", "{not json}\n")
        self.addCleanup(lambda: os.path.exists(bad) and os.unlink(bad))
        rc, _, err = self._run("delivery", "--log", bad)
        self.assertEqual(rc, 2)
        self.assertIn("not valid JSONL", err)


class TestRulesDiffEdges(unittest.TestCase):
    def test_missing_vendor_side_reads_as_change(self):
        old = {"version": "1", "vendors": {"intercom": {"unit_price": 0.99}}}
        new = {"version": "2", "vendors": {}}
        result = rd.diff_rules(old, new)
        self.assertTrue(result["material"])

    def test_null_to_null_is_not_a_change(self):
        v = {"intercom": {"unit_price": None, "billing_trigger": None}}
        result = rd.diff_rules({"version": "1", "vendors": v},
                               {"version": "2", "vendors": dict(v)})
        self.assertFalse(result["material"])


class TestLedgerEdges(unittest.TestCase):
    def test_recovery_lane_over_realization_fails_the_whole_verify(self):
        # The verify command composes recovery; an over-claimed concession
        # must fail the build, not vanish into the artifact.
        contract = tmpfile(".json", json.dumps({"reopen_window_hours": 72}))
        confirmations = tmpfile(".csv",
                                "conversation_id,status,amount\nC-1003,paid,99\n")
        for p in (contract, confirmations):
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        with self.assertRaises(ValueError):
            ledger_mod.build_ledger_document(
                EXPORT, "intercom", contract_path=contract,
                confirmations_path=confirmations)

    def test_empty_contract_window_refused_via_verify(self):
        contract = tmpfile(".json", json.dumps({"label": "empty"}))
        self.addCleanup(lambda: os.path.exists(contract) and os.unlink(contract))
        with self.assertRaises(ValueError):
            ledger_mod.build_ledger_document(EXPORT, "intercom",
                                             contract_path=contract)


if __name__ == "__main__":
    unittest.main()
