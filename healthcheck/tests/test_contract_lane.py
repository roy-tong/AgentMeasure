"""Outcome-standard lane tests: the buyer's contract overlay is a second lane.

The lane exists because BP r28 p2/p5/p8 separates two kinds of difference:
a contract billing variance is money (Tier 1 claim), an outcome-standard
difference is renewal leverage (this lane). The tests pin the separation:
nothing in the lane may change the Tier 1 verdicts, and an unevaluable
criterion is UNPROVABLE, never guessed.
"""
import json
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck import vendors
from am_healthcheck.vendors import (load_contract, load_export, outcome_lane,
                                    recount)


def write_json(doc):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                      encoding="utf-8")
    json.dump(doc, tmp)
    tmp.close()
    return tmp.name


CONTRACT_72H = {"label": "MSA 2026 §4.2", "reopen_window_hours": 72,
                "human_takeover_disqualifies": True}


class TestLoadContract(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _load(self, doc):
        path = write_json(doc)
        self.paths.append(path)
        return load_contract(path)

    def test_valid_contract_round_trips(self):
        contract = self._load(CONTRACT_72H)
        self.assertEqual(contract["reopen_window_hours"], 72)
        self.assertEqual(contract["label"], "MSA 2026 §4.2")
        self.assertTrue(contract["human_takeover_disqualifies"])
        self.assertFalse(contract["require_issue_addressed"])

    def test_empty_contract_is_refused(self):
        with self.assertRaises(ValueError):
            self._load({"label": "nothing in here"})

    def test_unknown_key_is_refused(self):
        with self.assertRaises(ValueError):
            self._load({"reopen_window_hours": 72, "penalty_rate": 0.1})

    def test_non_positive_window_is_refused(self):
        for bad in (0, -1, 1.5, "72", True):
            with self.assertRaises(ValueError):
                self._load({"reopen_window_hours": bad})

    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            load_contract("/nonexistent/contract.json")


class TestOutcomeLane(unittest.TestCase):
    def setUp(self):
        self.paths = []
        path = write_json(CONTRACT_72H)
        self.paths.append(path)
        self.contract = load_contract(path)

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _lane(self, rows):
        """rows: dicts over the canonical columns (+ optional)."""
        header = ("conversation_id,human_agent_participated,issue_addressed,"
                  "customer_recontacted_within_window,vendor_billed,"
                  "closed_at,customer_recontacted_at\n")
        lines = [header]
        for r in rows:
            lines.append(",".join(r) + "\n")
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8", newline="")
        tmp.write("".join(lines))
        tmp.close()
        self.paths.append(tmp.name)
        return outcome_lane(load_export(tmp.name), "intercom", self.contract)

    def test_billed_and_reopened_inside_contract_window_fails(self):
        # Vendor-billed, no recontact inside ITS window, but the customer came
        # back 48h after close — inside the contractual 72h window. Tier 1 has
        # no finding here; the outcome lane does. That is the separation.
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "2026-08-03T10:00:00Z")])
        self.assertEqual(lane["counts"]["fails_buyer_standard"], 1)
        self.assertIn("inside the", lane["lines"][0]["reasons"][0])

    def test_reopen_outside_window_meets_standard(self):
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "2026-08-09T10:00:00Z")])
        self.assertEqual(lane["counts"]["meets_buyer_standard"], 1)

    def test_boolean_alone_cannot_judge_a_contract_window(self):
        # The exported boolean is judged against the vendor's window, not ours.
        # Using it would be a guess in either direction: UNPROVABLE instead.
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "")])
        self.assertEqual(lane["counts"]["unprovable"], 1)
        self.assertIn("customer_recontacted_at",
                      lane["lines"][0]["missing_evidence"])

    def test_human_takeover_fails_when_contract_disqualifies(self):
        lane = self._lane([("C-1", "yes", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "")])
        self.assertEqual(lane["counts"]["fails_buyer_standard"], 1)
        self.assertIn("human", lane["lines"][0]["reasons"][0])

    def test_unbilled_line_is_not_reviewed(self):
        lane = self._lane([("C-1", "no", "yes", "yes", "no",
                            "2026-08-01T10:00:00Z", "2026-08-02T10:00:00Z")])
        self.assertEqual(lane["counts"]["not_reviewed"], 1)
        self.assertEqual(lane["lines"][0]["outcome_verdict"], "not_reviewed")

    def test_missing_billed_flag_is_unprovable_not_assumed(self):
        lane = self._lane([("C-1", "no", "yes", "no", "",
                            "2026-08-01T10:00:00Z", "")])
        self.assertEqual(lane["counts"]["unprovable"], 1)
        self.assertIn("vendor_billed", lane["lines"][0]["missing_evidence"])

    def test_at_risk_amount_is_priced_and_labelled(self):
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "2026-08-02T10:00:00Z"),
                           ("C-2", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00Z", "2026-08-09T10:00:00Z")])
        self.assertEqual(lane["at_risk_amount"], 0.99)
        self.assertEqual(lane["at_risk_note"], "not part of the claim")
        self.assertIn("not", lane["claim_rule"])

    def test_naive_timestamps_are_read_as_utc(self):
        # Naive local-looking timestamps parse; nine days later is outside
        # the 72h window, so the line meets the standard.
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "2026-08-01T10:00:00", "2026-08-10T10:00:00")])
        self.assertEqual(lane["counts"]["meets_buyer_standard"], 1)

    def test_unparseable_timestamp_is_unprovable(self):
        lane = self._lane([("C-1", "no", "yes", "no", "yes",
                            "not-a-date", "also-not-a-date")])
        self.assertEqual(lane["counts"]["unprovable"], 1)


class TestLaneSeparation(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def test_lane_never_changes_tier1(self):
        # The same export under the contract overlay must recount identically.
        export_path = fixture("vendor-export-intercom.csv")
        path = write_json(CONTRACT_72H)
        self.paths.append(path)
        contract = load_contract(path)
        plain = recount(load_export(export_path), "intercom")
        lane = outcome_lane(load_export(export_path), "intercom", contract)
        self.assertEqual(plain["counts"]["billed_but_not_billable"], 4)
        # The lane may find outcome-standard failures on lines Tier 1 passes;
        # that is the point. But it reports them out of band:
        self.assertIn("not", lane["claim_rule"])
        self.assertNotIn("variance", lane)

    def test_lane_report_names_it_leverage(self):
        export_path = fixture("vendor-export-intercom.csv")
        path = write_json(CONTRACT_72H)
        self.paths.append(path)
        lane = outcome_lane(load_export(export_path), "intercom",
                            load_contract(path))
        report = vendors.outcome_lane_report(lane)
        self.assertIn("Outcome-standard lane", report)
        self.assertIn("renewal leverage", report)
        self.assertIn("never netted", report)


if __name__ == "__main__":
    unittest.main()
