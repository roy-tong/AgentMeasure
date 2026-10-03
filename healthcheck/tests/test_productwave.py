"""Product-wave tests: outcome engine, CRM join, period compare, certify,
incrementality, templates, and the schema v0.2 widening.

The through-line under test: engines fail closed (inconsistent units are
invalid, not smoothed), the CRM join fills empties and names conflicts but
never overwrites, the digest is stable across runs, certification promotes
only on evidence in the document, and statistics never masquerade as a
billing verdict.
"""
import json
import os
import tempfile
import unittest

from _support import REPO_ROOT, fixture

from am_healthcheck import outcomes as om
from am_healthcheck import crm as crm_mod
from am_healthcheck import periods as periods_mod
from am_healthcheck import certify as cert_mod
from am_healthcheck import incrementality as inc_mod
from am_healthcheck import templates as tpl_mod
from am_healthcheck import ledger as ledger_mod

SCHEMA = os.path.join(REPO_ROOT, "schemas", "outcome-unit.schema.json")
EXPORT = fixture("vendor-export-intercom.csv")


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


def unit(**overrides):
    base = {
        "schema_version": "agentmeasure-outcome-0.1",
        "unit_id": "u-1",
        "unit_type": "qualified_lead",
        "contract_ref": "MSA §5.1",
        "occurred_at": "2026-09-12T14:30:00Z",
        "declared_by": "vendor",
        "observer_grade": "affected_party",
        "qualification": {"criteria_met": ["budget evidenced"]},
        "status": "counted",
        "value": {"currency": "USD", "amount": 150},
    }
    base.update(overrides)
    return base


class TestOutcomeEngine(unittest.TestCase):
    def setUp(self):
        self.schema = om.load_schema(SCHEMA)
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _run(self, units):
        path = tmpfile(".jsonl", "".join(json.dumps(u) + "\n" for u in units))
        self.paths.append(path)
        return om.verify_units(om.load_units(path), self.schema)

    def test_counted_unit_enters_claim(self):
        result = self._run([unit()])
        self.assertEqual(result["counts"]["counted"], 1)
        self.assertEqual(result["claim_value"], 150.0)
        self.assertEqual(result["claim_currency"], "USD")

    def test_unproven_criteria_cannot_be_counted(self):
        # The engine's core invariant: counted + criteria_unproven is an
        # inconsistency, failed closed — never silently accepted.
        bad = unit(qualification={"criteria_met": ["a"],
                                  "criteria_unproven": ["authority"]},
                   status="counted")
        result = self._run([bad])
        self.assertEqual(result["counts"]["counted"], 0)
        self.assertEqual(result["counts"]["invalid"], 1)
        self.assertIn("unproven", result["lines"][0]["reasons"][0])

    def test_explicit_unproven_status_is_respected(self):
        ok = unit(qualification={"criteria_met": ["a"],
                                 "criteria_unproven": ["authority"]},
                  status="unproven")
        result = self._run([ok])
        self.assertEqual(result["counts"]["unproven"], 1)
        self.assertIsNone(result["claim_value"])

    def test_schema_invalid_unit_counts_as_invalid_only(self):
        bad = unit(unit_type="vibe")  # not in enum
        result = self._run([bad])
        self.assertEqual(result["counts"]["invalid"], 1)
        self.assertTrue(any("enum" in r for r in result["lines"][0]["reasons"]))

    def test_duplicate_ids_named(self):
        result = self._run([unit(), unit()])
        self.assertEqual(result["duplicate_unit_ids"], ["u-1"])
        # duplicates still count as units — they are named, not resolved
        self.assertEqual(result["counts"]["counted"], 2)

    def test_reopen_inside_window_is_named_not_judged(self):
        r = unit(window={"stability_hours": 336,
                         "reopened_at": ["2026-09-20T09:00:00Z"]})
        result = self._run([r])
        self.assertIn("u-1", result["reopened_in_window"])
        self.assertEqual(result["counts"]["counted"], 1)

    def test_multi_currency_refuses_to_sum(self):
        rows = [unit(value={"currency": "USD", "amount": 100}),
                unit(unit_id="u-2", value={"currency": "EUR", "amount": 100})]
        result = self._run(rows)
        self.assertIsNone(result["claim_currency"])
        self.assertIn("not summed", result["currency_note"])

    def test_v02_action_unit_with_allowance(self):
        a = unit(unit_id="a-1", unit_type="action",
                 billing_context={"plan_allowance_included": 300,
                                  "consumed_in_period": 300,
                                  "overage_billed": True})
        result = self._run([a])
        self.assertEqual(result["counts"]["counted"], 1)
        self.assertEqual(result["by_unit_type"]["action"], 1)

    def test_v01_examples_still_validate(self):
        # schema widening is additive: the shipped v0.1 examples must pass v0.2
        examples = os.path.join(REPO_ROOT, "schemas", "examples",
                                "outcome-units")
        for name in ("qualified-lead.json", "completed-case.json"):
            with open(os.path.join(examples, name), encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(om.validate_schema(doc, self.schema), [], name)


class TestCrmJoin(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _canonical_with_empty_ts(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed,"
                "customer_recontacted_at\n"
                "C-1,no,yes,no,yes,\n"
                "C-2,yes,yes,no,yes,2026-08-02T00:00:00Z\n")
        path = tmpfile(".csv", text)
        self.paths.append(path)
        return path

    def test_fills_empty_and_never_overwrites(self):
        crm = tmpfile(".csv", "conversation_id,reopened_at,human_handover_at\n"
                              "C-1,2026-08-03T09:00:00Z,\n"
                              "C-2,2026-08-09T00:00:00Z,\n")
        self.paths.append(crm)
        out = tmpfile(".csv", "")
        self.paths.append(out)
        rows = crm_mod.load_crm(crm)
        result = crm_mod.crm_join(self._canonical_with_empty_ts(), rows, out)
        self.assertEqual(result["rows_filled"], 1)  # C-1 only; C-2 kept its own
        with open(out, encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        self.assertIn("2026-08-03T09:00:00Z", lines[1])
        self.assertIn("2026-08-02T00:00:00Z", lines[2])  # export value intact
        self.assertIn("prov_customer_recontacted_at", lines[0])

    def test_conflict_named_not_resolved(self):
        crm = tmpfile(".csv", "conversation_id,reopened_at,human_handover_at\n"
                              "C-1,,2026-08-01T10:00:00Z\n")
        self.paths.append(crm)
        out = tmpfile(".csv", "")
        self.paths.append(out)
        result = crm_mod.crm_join(self._canonical_with_empty_ts(),
                                  crm_mod.load_crm(crm), out)
        self.assertEqual(len(result["conflicts"]), 1)
        self.assertEqual(result["conflicts"][0]["export_says"], "no")

    def test_missing_conversation_id_refused(self):
        bad = tmpfile(".csv", "id,reopened_at\nC-1,2026-08-01\n")
        self.paths.append(bad)
        with self.assertRaises(crm_mod.CrmError):
            crm_mod.load_crm(bad)


class TestPeriodCompare(unittest.TestCase):
    def _ledger_file(self, name, counts_over=4, counts_under=2, variance=1.98,
                     verdicts=None):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        t1 = doc["tier1"]
        t1["counts"]["billed_but_not_billable"] = counts_over
        t1["counts"]["billable_but_not_billed"] = counts_under
        t1["three_state_counts"] = {
            "PASS": t1["counts"]["agrees"], "FAIL": counts_over + counts_under,
            "UNPROVABLE": t1["counts"]["cannot_settle"]}
        t1["variance"] = variance
        t1["net_findings"] = counts_over - counts_under
        if verdicts is not None:
            t1["verdicts"] = verdicts
        doc["generated_at"] = "2026-09-01T00:00:00+00:00"
        path = tmpfile(".json", json.dumps(doc))
        self.paths.append(path)
        return path

    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def test_delta_and_new_fail_lines(self):
        prev = self._ledger_file("p", counts_over=4, counts_under=2,
                                 variance=1.98,
                                 verdicts=[
                                     {"line": 2, "conversation_id": "C-3",
                                      "verdict": "billed_but_not_billable",
                                      "verdict_3state": "FAIL"}])
        curr = self._ledger_file("c", counts_over=5, counts_under=2,
                                 variance=2.97,
                                 verdicts=[
                                     {"line": 2, "conversation_id": "C-3",
                                      "verdict": "billed_but_not_billable",
                                      "verdict_3state": "FAIL"},
                                     {"line": 3, "conversation_id": "C-6",
                                      "verdict": "billed_but_not_billable",
                                      "verdict_3state": "FAIL"}])
        result = periods_mod.compare_periods(prev, curr)
        self.assertEqual(result["three_state_delta"]["FAIL"], 1)
        self.assertEqual(result["variance_delta"], 0.99)
        self.assertIn("C-6", result["new_fail_lines"])
        self.assertFalse(result["rules_version_changed"])

    def test_rules_version_change_is_flagged(self):
        prev = self._ledger_file("p")
        curr = self._ledger_file("c")
        with open(curr, encoding="utf-8") as fh:
            doc = json.load(fh)
        doc["vendor"]["rules_version"] = "9.9.9-different"
        with open(curr, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        result = periods_mod.compare_periods(prev, curr)
        self.assertTrue(result["rules_version_changed"])
        md = periods_mod.compare_markdown(result)
        self.assertIn("rules version changed", md)


class TestCertify(unittest.TestCase):
    def test_stage1_for_recomputable_ledger(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        result = cert_mod.certify(doc)
        self.assertEqual(result["stage"], "stage-1")
        self.assertTrue(result["requirements"]["inputs_hashed"])
        self.assertIn("stage-2", result["next_requirements"])

    def test_stage2_on_matching_reproduction(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        digest = cert_mod.deterministic_digest(doc)
        doc["reproductions"] = [{"by": "damian", "digest": digest,
                                 "date": "2026-10-04"}]
        result = cert_mod.certify(doc)
        self.assertEqual(result["stage"], "stage-2")

    def test_stage3_on_acceptance(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        digest = cert_mod.deterministic_digest(doc)
        doc["reproductions"] = [{"by": "damian", "digest": digest}]
        doc["acceptances"] = [{"by": "Intercom Fin team", "role": "vendor",
                               "date": "2026-10-10", "ref": "credit-note-77"}]
        result = cert_mod.certify(doc)
        self.assertEqual(result["stage"], "stage-3")

    def test_non_matching_reproduction_does_not_promote(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        doc["reproductions"] = [{"by": "someone", "digest": "deadbeef"}]
        result = cert_mod.certify(doc)
        self.assertEqual(result["stage"], "stage-1")

    def test_digest_is_stable_and_ignores_timestamp(self):
        doc = ledger_mod.build_ledger_document(EXPORT, "intercom")
        d1 = cert_mod.deterministic_digest(doc)
        doc["generated_at"] = "2099-01-01T00:00:00+00:00"
        d2 = cert_mod.deterministic_digest(doc)
        self.assertEqual(d1, d2)
        doc["tier1"]["counts"]["billed_but_not_billable"] = 5
        self.assertNotEqual(d1, cert_mod.deterministic_digest(doc))


class TestIncrementality(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _events(self, t_conv, t_n, h_conv, h_n):
        rows = ["group,converted"]
        rows += ["treatment,1"] * t_conv + ["treatment,0"] * (t_n - t_conv)
        rows += ["holdout,1"] * h_conv + ["holdout,0"] * (h_n - h_conv)
        path = tmpfile(".csv", "\n".join(rows) + "\n")
        self.paths.append(path)
        return path

    def test_positive_difference_detected(self):
        groups = inc_mod.load_groups(self._events(20, 100, 8, 100))
        result = inc_mod.analyze(groups)
        self.assertEqual(result["verdict_band"], "positive_difference")
        lo, hi = result["difference"]["ci95_newcombe"]
        self.assertGreater(lo, 0)
        self.assertLessEqual(hi, 1.0)

    def test_small_samples_do_not_earn_confidence(self):
        groups = inc_mod.load_groups(self._events(3, 10, 1, 10))
        result = inc_mod.analyze(groups)
        self.assertEqual(result["verdict_band"], "insufficient_evidence")
        self.assertIn("CI95", inc_mod.report_text(result))  # interval still shown

    def test_interval_covering_zero_is_said_plainly(self):
        groups = inc_mod.load_groups(self._events(50, 1000, 50, 1000))
        result = inc_mod.analyze(groups)
        self.assertEqual(result["verdict_band"], "no_detectable_difference")
        self.assertIn("covers zero", result["note"])

    def test_never_produces_pass_fail(self):
        groups = inc_mod.load_groups(self._events(20, 100, 8, 100))
        result = inc_mod.analyze(groups)
        blob = json.dumps(result)
        self.assertNotIn("PASS", blob)
        self.assertNotIn("FAIL", blob)
        self.assertIn("never a billing verdict", result["claim_boundary"])

    def test_unknown_group_refused(self):
        bad = tmpfile(".csv", "group,converted\ncontrol,1\n")
        self.paths.append(bad)
        with self.assertRaises(inc_mod.IncrementalityError):
            inc_mod.load_groups(bad)


class TestTemplates(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.paths = []

    def tearDown(self):
        for name in os.listdir(self.dir):
            os.unlink(os.path.join(self.dir, name))
        os.rmdir(self.dir)
        for p in self.paths:
            os.unlink(p)

    def test_save_list_replay(self):
        contract = {"reopen_window_hours": 72}
        cases = [{
            "name": "reopen inside vendor window only",
            "columns": {"conversation_id": "SYN-1",
                        "human_agent_participated": "no",
                        "issue_addressed": "yes",
                        "customer_recontacted_within_window": "yes",
                        "vendor_billed": "yes"},
            "expected_3state": "FAIL",
        }]
        doc = tpl_mod.export_template("intercom", "fp123", contract=contract,
                                      boundary_cases=cases)
        path = tpl_mod.save_template(doc, self.dir)
        loaded = tpl_mod.load_template(path)
        self.assertEqual(loaded["mapping_fingerprint"], "fp123")
        listing = tpl_mod.list_templates(self.dir)
        self.assertEqual(listing[0]["boundary_cases"], 1)

        # replay through the real recount: the boundary must hold
        from am_healthcheck.vendors import load_export, recount
        header = ("conversation_id,human_agent_participated,issue_addressed,"
                  "customer_recontacted_within_window,vendor_billed\n")
        def recount_fn(rows):
            text = header + "".join(
                ",".join(str(rows[0][k]) for k in
                         ("conversation_id", "human_agent_participated",
                          "issue_addressed",
                          "customer_recontacted_within_window", "vendor_billed"))
                + "\n")
            p = tmpfile(".csv", text)
            self.paths.append(p)
            return recount(load_export(p), "intercom")["verdicts"]
        replay = tpl_mod.replay_boundary_cases(loaded, recount_fn)
        self.assertTrue(all(r["holds"] for r in replay), replay)

    def test_rules_change_that_moves_a_boundary_is_caught(self):
        cases = [{
            "name": "human takeover",
            "columns": {"conversation_id": "SYN-2",
                        "human_agent_participated": "yes",
                        "issue_addressed": "yes",
                        "customer_recontacted_within_window": "no",
                        "vendor_billed": "yes"},
            "expected_3state": "PASS",  # deliberately wrong: replay must fail
        }]
        doc = tpl_mod.export_template("intercom", "fp", boundary_cases=cases)
        from am_healthcheck.vendors import load_export, recount
        header = ("conversation_id,human_agent_participated,issue_addressed,"
                  "customer_recontacted_within_window,vendor_billed\n")
        text = header + "SYN-2,yes,yes,no,yes\n"
        p = tmpfile(".csv", text)
        self.paths.append(p)
        verdicts = recount(load_export(p), "intercom")["verdicts"]
        replay = tpl_mod.replay_boundary_cases(doc, lambda rows: verdicts)
        self.assertFalse(replay[0]["holds"])

    def test_bad_3state_refused(self):
        with self.assertRaises(tpl_mod.TemplateError):
            tpl_mod.export_template("intercom", "fp",
                                    boundary_cases=[{"expected_3state": "ok"}])


if __name__ == "__main__":
    unittest.main()
