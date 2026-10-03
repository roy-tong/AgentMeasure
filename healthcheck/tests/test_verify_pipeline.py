"""Pipeline tests: crosscheck, verified ledger, rules-diff, narrative,
delivery metrics, dashboard.

These are the six lanes BP r28 promises that this round completed. The common
thread under test: lanes stay separate (claim / leverage / realized), numbers
are never invented by the narrative layer, and every artifact renders from
the data alone.
"""
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
from am_healthcheck.vendors import load_export

EXPORT = fixture("vendor-export-intercom.csv")


def tmpfile(suffix, text, mode="w"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding="utf-8", newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


class TestCrosscheck(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _ledger(self, text):
        path = tmpfile(".csv", text)
        self.paths.append(path)
        return cc.load_ledger(path)

    def test_all_matched_is_quiet(self):
        # Every line the export bills (C-1001..C-1006, C-1009, C-1010) is
        # confirmed by the ledger at the published price.
        ids = ["C-1001", "C-1002", "C-1003", "C-1004", "C-1005", "C-1006",
               "C-1009", "C-1010"]
        rows = self._ledger(
            "conversation_id,amount\n" + "".join("%s,0.99\n" % i for i in ids))
        result = cc.crosscheck(load_export(EXPORT), rows, "intercom")
        self.assertEqual(result["flag_without_charge"], [])
        self.assertEqual(result["charge_without_export_flag"], [])
        self.assertEqual(result["not_in_export"], [])
        self.assertEqual(result["matched_billed"], 8)

    def test_export_billed_but_ledger_silent(self):
        # C-1003 is billed per export; the ledger has nothing — the claim
        # stands on the export, and the missing billing evidence is named.
        rows = self._ledger("conversation_id,amount\nC-1001,0.99\n")
        result = cc.crosscheck(load_export(EXPORT), rows, "intercom")
        flagged = {r["conversation_id"] for r in result["flag_without_charge"]}
        self.assertIn("C-1003", flagged)
        self.assertIn("C-1005", flagged)

    def test_ledger_charge_on_unbilled_export_line(self):
        # C-1007 is billable-but-not-billed per export; a ledger charge here
        # is money moving where the export says none did.
        rows = self._ledger("conversation_id,amount\nC-1007,0.99\n")
        result = cc.crosscheck(load_export(EXPORT), rows, "intercom")
        self.assertEqual(len(result["charge_without_export_flag"]), 1)
        self.assertEqual(result["charge_without_export_flag"][0]["conversation_id"],
                         "C-1007")

    def test_charge_absent_from_export_entirely(self):
        rows = self._ledger("conversation_id,amount\nC-9999,0.99\n")
        result = cc.crosscheck(load_export(EXPORT), rows, "intercom")
        self.assertEqual(result["not_in_export"][0]["conversation_id"], "C-9999")

    def test_amount_deviation_from_published_price(self):
        rows = self._ledger("conversation_id,amount\nC-1001,1.49\n")
        result = cc.crosscheck(load_export(EXPORT), rows, "intercom")
        self.assertEqual(result["amount_deviation"][0]["expected"], 0.99)
        self.assertEqual(result["amount_deviation"][0]["charged"], 1.49)

    def test_ledger_without_conversation_id_refused(self):
        path = tmpfile(".csv", "id,amount\nC-1,1.00\n")
        self.paths.append(path)
        with self.assertRaises(cc.LedgerError):
            cc.load_ledger(path)


class TestVerifiedLedger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)
        for name in os.listdir(self.tmpdir):
            os.unlink(os.path.join(self.tmpdir, name))
        os.rmdir(self.tmpdir)

    def test_minimal_ledger_is_tier1_only(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        self.assertEqual(doc["tier1"]["counts"]["billed_but_not_billable"], 4)
        self.assertIsNone(doc["outcome_lane"])
        self.assertIsNone(doc["billing_crosscheck"])
        md = ledger_mod.ledger_markdown(doc)
        self.assertIn("Verified Ledger", md)
        self.assertIn("UNPROVABLE", md)
        self.assertNotIn("Outcome-standard lane", md)

    def test_full_ledger_joins_every_lane(self):
        contract = tmpfile(".json", json.dumps(
            {"label": "MSA §4.2", "reopen_window_hours": 72}))
        self.paths.append(contract)
        billing = tmpfile(".csv", "conversation_id,amount\nC-1001,0.99\nC-7777,0.99\n")
        self.paths.append(billing)
        confirmations = tmpfile(".csv", "conversation_id,status,amount\n"
                                        "C-1003,credited,0.99\n")
        self.paths.append(confirmations)
        doc = ledger_mod.build_ledger_document(
            EXPORT, "intercom", contract_path=contract,
            ledger_path=billing, confirmations_path=confirmations)
        self.assertEqual(doc["outcome_lane"]["label"], "MSA §4.2")
        self.assertEqual(len(doc["billing_crosscheck"]["not_in_export"]), 1)
        self.assertEqual(doc["recovery"]["totals"]["realized"], 0.99)
        md = ledger_mod.ledger_markdown(doc)
        self.assertIn("Outcome-standard lane", md)
        self.assertIn("Billing-ledger cross-check", md)
        self.assertIn("Recovery", md)
        self.assertIn("sha256", md)

    def test_write_and_reload_round_trips(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        paths = ledger_mod.write_ledger_document(doc, self.tmpdir)
        with open(paths["json"], encoding="utf-8") as fh:
            reloaded = json.load(fh)
        self.assertEqual(reloaded["schema"],
                         "agentmeasure.commercial/verified-ledger")


class TestRulesDiff(unittest.TestCase):
    def _docs(self, old_vendors, new_vendors, old_v="0.1", new_v="0.2"):
        return ({"version": old_v, "vendors": old_vendors},
                {"version": new_v, "vendors": new_vendors})

    def test_material_change_is_named(self):
        old = {"intercom": {"billing_trigger": "confirmed_or_assumed",
                            "unit_price": 0.99}}
        new = {"intercom": {"billing_trigger": "llm_verified_only",
                            "unit_price": 0.99}}
        result = rd.diff_rules(*self._docs(old, new))
        self.assertTrue(result["material"])
        self.assertEqual(result["vendors_changed"][0]["changes"][0]["field"],
                         "billing_trigger")

    def test_informational_change_is_not_material(self):
        old = {"intercom": {"billing_trigger": "confirmed_or_assumed",
                            "source": "old-url"}}
        new = {"intercom": {"billing_trigger": "confirmed_or_assumed",
                            "source": "new-url"}}
        result = rd.diff_rules(*self._docs(old, new))
        self.assertFalse(result["material"])
        self.assertIn("source", result["vendors_changed"][0]["informational"])

    def test_price_move_is_material(self):
        old = {"intercom": {"unit_price": 0.99}}
        new = {"intercom": {"unit_price": 1.19}}
        result = rd.diff_rules(*self._docs(old, new))
        self.assertTrue(result["material"])

    def test_new_vendor_is_material(self):
        result = rd.diff_rules(*self._docs({}, {"ada": {"unit_price": None}}))
        self.assertTrue(result["material"])

    def test_report_says_reverify_when_material(self):
        old = {"intercom": {"unit_price": 0.99}}
        new = {"intercom": {"unit_price": 1.19}}
        report = rd.rules_diff_report(rd.diff_rules(*self._docs(old, new)))
        self.assertIn("Re-verify", report)

    def test_no_changes_report(self):
        v = {"intercom": {"unit_price": 0.99, "billing_trigger": "x"}}
        report = rd.rules_diff_report(rd.diff_rules(*self._docs(v, v)))
        self.assertIn("No rule changes", report)


class TestNarrative(unittest.TestCase):
    def setUp(self):
        self.pack = {
            "schema": "agentmeasure.commercial/dispute-pack",
            "vendor": {"name": "Intercom Fin", "id": "intercom",
                       "rule_source": "https://example.com/fin-rules"},
            "currency": "USD",
            "buyer_label": "ACME",
            "period": {"start": None, "end": None},
            "tier1": {"counts": {"billed_but_not_billable": 4,
                                 "billable_but_not_billed": 2,
                                 "cannot_settle": 2, "agrees": 2},
                      "net_findings": 2},
            "claim": {"billed_but_not_billable": 4, "billable_but_not_billed": 2,
                      "cannot_settle": 2,
                      "dollars": {"overcharge": 3.96, "undercharge": 1.98,
                                  "net_variance": 1.98}},
            "outcome_lane": {"label": "MSA §4.2", "at_risk_amount": 3.96,
                             "counts": {"fails_buyer_standard": 2,
                                        "meets_buyer_standard": 1,
                                        "unprovable": 1, "not_reviewed": 0}},
        }

    def test_finance_note_template_carries_the_numbers(self):
        text = narr.render_finance_note(self.pack)
        self.assertIn("4", text)
        self.assertIn("1.98", text)
        self.assertIn("renewal leverage", text)
        self.assertIn("until the vendor confirms", text)

    def test_obedient_llm_draft_ships(self):
        draft = ("Dear Intercom Fin team: 4 conversations were billed but are "
                 "not billable under your own rule; the net variance is USD "
                 "1.98. — ACME")
        text, source, violations = narr.render_or_draft(
            self.pack, draft, "vendor")
        self.assertEqual(source, "llm")
        self.assertIsNone(violations)
        self.assertEqual(text, draft)

    def test_invented_number_is_refused_and_template_ships(self):
        draft = ("4 conversations billed wrongly, net USD 1.98, and 999 "
                 "conversations total.")
        text, source, violations = narr.render_or_draft(
            self.pack, draft, "vendor")
        self.assertEqual(source, "template")
        self.assertIn("999", violations)
        self.assertNotIn("999", text)

    def test_rounded_number_is_refused_too(self):
        # 3.96 rounded to 3.9 — a number the pack does not contain.
        draft = "the overcharge identified is USD 3.9 in total."
        text, source, violations = narr.render_or_draft(
            self.pack, draft, "finance")
        self.assertEqual(source, "template")
        self.assertIn("3.9", violations)

    def test_no_model_means_template(self):
        text, source, violations = narr.render_or_draft(
            self.pack, None, "finance")
        self.assertEqual(source, "template")
        self.assertIsNone(violations)

    def test_prompt_forbids_new_numbers(self):
        prompt = narr.build_prompt(self.pack, "vendor")
        self.assertIn("MUST NOT introduce, round, or alter any number", prompt)
        self.assertIn("1.98", prompt)  # the facts travel inside the prompt


class TestDelivery(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _log(self, events):
        lines = "".join(json.dumps(e) + "\n" for e in events)
        path = tmpfile(".jsonl", lines)
        self.paths.append(path)
        return path

    def test_first_look_and_third_period_bars(self):
        path = self._log([
            {"engagement": "A", "vendor": "intercom", "period_index": 1,
             "phase": "mapping", "minutes": 300},
            {"engagement": "A", "vendor": "intercom", "period_index": 1,
             "phase": "judgment", "minutes": 60},
            {"engagement": "A", "vendor": "intercom", "period_index": 3,
             "phase": "recount", "minutes": 40},
        ])
        rep = del_mod.report(del_mod.load_events(path))
        self.assertEqual(rep["first_look"][0]["hours"], 6.0)
        self.assertTrue(rep["first_look"][0]["within_10h_bar"])
        self.assertEqual(rep["third_period"][0]["minutes"], 40)
        self.assertTrue(rep["third_period"][0]["within_1h_bar"])
        self.assertEqual(rep["reuse"]["engagements_with_repeat"], 1)

    def test_shared_fingerprint_is_mapping_reuse(self):
        path = self._log([
            {"engagement": "A", "vendor": "intercom", "period_index": 1,
             "phase": "mapping", "minutes": 100, "fingerprint": "fp1"},
            {"engagement": "B", "vendor": "intercom", "period_index": 1,
             "phase": "mapping", "minutes": 30, "fingerprint": "fp1"},
        ])
        rep = del_mod.report(del_mod.load_events(path))
        self.assertEqual(rep["reuse"]["shared_mapping_fingerprints"]["fp1"],
                         ["A", "B"])

    def test_over_bar_is_flagged_not_hidden(self):
        path = self._log([
            {"engagement": "A", "vendor": "zendesk", "period_index": 1,
             "phase": "mapping", "minutes": 700},
        ])
        rep = del_mod.report(del_mod.load_events(path))
        self.assertFalse(rep["first_look"][0]["within_10h_bar"])

    def test_log_event_validates(self):
        path = self._log([])
        with self.assertRaises(del_mod.DeliveryError):
            del_mod.log_event(path, "", "intercom", 1, "mapping", 10)
        with self.assertRaises(del_mod.DeliveryError):
            del_mod.log_event(path, "A", "intercom", 0, "mapping", 10)
        with self.assertRaises(del_mod.DeliveryError):
            del_mod.log_event(path, "A", "intercom", 1, "meditation", 10)
        with self.assertRaises(del_mod.DeliveryError):
            del_mod.log_event(path, "A", "intercom", 1, "mapping", -5)

    def test_prepare_fingerprint_is_stable_and_value_free(self):
        from am_healthcheck import prepare as prepare_mod
        native = ("Ticket ID,Created at,Solved at\n"
                  "77102,2026-08-01T09:00:00Z,2026-08-01T09:30:00Z\n")
        p1 = tmpfile(".csv", native)
        p2 = tmpfile(".csv", native)
        self.paths += [p1, p2]
        a = prepare_mod.prepare(p1, "zendesk")
        b = prepare_mod.prepare(p2, "zendesk")
        self.assertEqual(a["mapping_fingerprint"], b["mapping_fingerprint"])
        # The fingerprint must never carry row values.
        self.assertNotIn("77102", a["mapping_fingerprint"])


class TestDashboard(unittest.TestCase):
    def test_renders_from_verified_ledger(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        html_text = dash.render_dashboard(doc)
        self.assertIn("Verified Ledger", html_text)
        self.assertIn("PASS", html_text)
        self.assertIn("no data left this machine", html_text)

    def test_renders_every_lane_it_is_given(self):
        contract = tmpfile(".json", json.dumps({"reopen_window_hours": 72}))
        self.paths = [contract]
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom",
                                               contract_path=contract)
        html_text = dash.render_dashboard(doc)
        self.assertIn("Outcome-standard lane", html_text)
        self.assertIn("leverage", html_text)
        self.assertIn("Never netted into the claim", html_text)

    def test_escapes_hostile_labels(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        doc["buyer_label"] = "<script>alert(1)</script>"
        html_text = dash.render_dashboard(doc)
        self.assertNotIn("<script>", html_text)
        self.assertIn("&lt;script&gt;", html_text)

    def test_foreign_document_refused(self):
        with self.assertRaises(ValueError):
            dash.render_dashboard({"schema": "something/else"})


if __name__ == "__main__":
    unittest.main()
