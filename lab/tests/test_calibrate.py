"""Calibration tests (CAL-002/003): production re-test, per-condition transfer,
not_comparable degradation."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.calibrate import calibrate, write_calibration_report
from agentmeasure_lab.prereg import load_schema
from agentmeasure_lab.schemas import validate
from tests._support import (
    TASK_SET_NAME,
    LabWorkspace,
    base_manifest,
    generate_production_events,
    load_json,
)


class TestCalibrate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = LabWorkspace()
        # Offline experiment with a planted ~+8pp selection effect.
        cls.report, cls.run_dir, cls.prereg_path = cls.ws.run(
            base_manifest(experiment_id="cal-offline", seed=20260822, replicates=40)
        )
        cls.tasks = load_json(os.path.join(cls.ws.tmp, TASK_SET_NAME))["tasks"]
        cls.task_ids = [t["id"] for t in cls.tasks]

        # Production rollout with a SMALLER planted effect (+4pp): the
        # calibration analysis must recover both numbers and the gap.
        cls.prod_path = os.path.join(cls.ws.tmp, "production-events.jsonl")
        generate_production_events(
            cls.prod_path,
            experiment_id="cal-offline",
            seed=424242,
            arm_selection_probs={"control": 0.36, "clear": 0.40},
            n_per_arm=2500,
            task_ids=cls.task_ids,
        )

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def test_production_confirmed_with_transfer(self):
        cal = calibrate(self.run_dir, self.prereg_path, self.prod_path)
        v = next(v for v in cal["variants"] if v["variant_id"] == "clear")
        self.assertEqual(v["calibration"]["calibration"], "production_confirmed")
        prod = v["production_comparison"]["difference"]
        self.assertGreater(prod, 0.015, "planted +4pp production effect should be positive")
        self.assertLess(prod, 0.065, "production effect should be smaller than offline")
        off = v["offline_comparison"]["difference"]
        self.assertGreater(off, prod, "offline effect larger than production by design")
        tr = v["transfer_overall"]
        self.assertIsNotNone(tr)
        self.assertGreater(tr["offline_minus_production"], 0.0)

    def test_per_condition_rows_exist(self):
        cal = calibrate(self.run_dir, self.prereg_path, self.prod_path)
        v = next(v for v in cal["variants"] if v["variant_id"] == "clear")
        conditions = [r["condition"] for r in v["per_condition"]]
        self.assertTrue(any(c.startswith("harness:") for c in conditions))
        self.assertTrue(any(c.startswith("stratum:") for c in conditions))
        for row in v["per_condition"]:
            if row.get("status") == "not_comparable":
                self.assertIn("gap", row)
            else:
                self.assertIn("comparison", row)
                self.assertIn("offline", row)

    def test_not_comparable_when_arm_missing(self):
        bad_path = os.path.join(self.ws.tmp, "prod-missing-arm.jsonl")
        generate_production_events(
            bad_path,
            experiment_id="cal-offline",
            seed=1,
            arm_selection_probs={"control": 0.36},  # treatment arm never shipped
            n_per_arm=500,
            task_ids=self.task_ids,
        )
        cal = calibrate(self.run_dir, self.prereg_path, bad_path)
        v = next(v for v in cal["variants"] if v["variant_id"] == "clear")
        self.assertEqual(v["calibration"]["calibration"], "not_comparable")

    def test_direction_mismatch_detected(self):
        flip_path = os.path.join(self.ws.tmp, "prod-flipped.jsonl")
        generate_production_events(
            flip_path,
            experiment_id="cal-offline",
            seed=2,
            arm_selection_probs={"control": 0.45, "clear": 0.38},  # production REGRESSES
            n_per_arm=2500,
            task_ids=self.task_ids,
        )
        cal = calibrate(self.run_dir, self.prereg_path, flip_path)
        v = next(v for v in cal["variants"] if v["variant_id"] == "clear")
        self.assertEqual(v["calibration"]["calibration"], "direction_mismatch")

    def test_report_schema_and_html(self):
        cal = calibrate(self.run_dir, self.prereg_path, self.prod_path)
        validate(cal, load_schema("calibration-report.schema.json"))
        json_path = write_calibration_report(cal, self.run_dir)
        self.assertTrue(os.path.exists(json_path))
        html = open(os.path.join(self.run_dir, "calibration-report.html"), encoding="utf-8").read()
        self.assertIn("Calibration Report", html)
        self.assertIn("transfer", html.lower())

    def test_reweighting_suggestions_flow_back(self):
        cal = calibrate(self.run_dir, self.prereg_path, self.prod_path)
        v = next(v for v in cal["variants"] if v["variant_id"] == "clear")
        self.assertIsInstance(v["reweighting_suggestions"], list)


if __name__ == "__main__":
    unittest.main()
