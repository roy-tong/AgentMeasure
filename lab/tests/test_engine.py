"""End-to-end engine tests: M1 gate — synthetic preregistered experiment
including the honest null path (PRD §9), plus determinism, budget breaker,
schema conformance and the anti-fake-growth path."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.prereg import load_schema
from agentmeasure_lab.schemas import validate
from tests._support import LabWorkspace, base_manifest, load_json

NULL = {"id": "label-b", "baseline": False,
        "levels": {"description_clarity": "control", "version_label": "b"}}


class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = LabWorkspace()
        # Uplift: planted +attraction for description_clarity=clear.
        cls.uplift, cls.uplift_dir, cls.uplift_prereg = cls.ws.run(
            base_manifest(experiment_id="e2e-uplift", seed=20260822, replicates=40)
        )
        # Null: version_label=b has exactly zero planted effect.
        cls.null, cls.null_dir, _ = cls.ws.run(
            base_manifest(
                experiment_id="e2e-null",
                variants=[
                    {"id": "control", "baseline": True,
                     "levels": {"description_clarity": "control", "version_label": "a"}},
                    NULL,
                ],
                seed=20260822,
                replicates=40,
            )
        )

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def _variant(self, report, vid):
        return next(v for v in report["variants"] if v["variant_id"] == vid)

    def test_uplift_detected(self):
        v = self._variant(self.uplift, "clear")
        self.assertEqual(v["primary_comparison"]["verdict"], "significant")
        self.assertEqual(v["primary_comparison"]["direction"], "improvement")
        self.assertGreater(v["primary_comparison"]["difference"], 0.03)
        self.assertIn(v["verdict"], ("adopt_candidate", "effective_not_qualified"))

    def test_null_is_honest(self):
        v = self._variant(self.null, "label-b")
        self.assertIn(v["verdict"], ("null_result", "undetermined"))
        if v["primary_comparison"]["verdict"] == "null_result":
            self.assertIn("honest null", v["primary_comparison"]["reason"])

    def test_determinism_same_fingerprint(self):
        rep2, _, _ = self.ws.run(base_manifest(experiment_id="e2e-uplift", seed=20260822, replicates=40))
        self.assertEqual(self.uplift["run"]["run_fingerprint"], rep2["run"]["run_fingerprint"])

    def test_different_seed_different_fingerprint(self):
        rep3, _, _ = self.ws.run(base_manifest(experiment_id="e2e-uplift-b", seed=999, replicates=40))
        self.assertNotEqual(self.uplift["run"]["run_fingerprint"], rep3["run"]["run_fingerprint"])

    def test_assignment_balance_verifiable_from_events(self):
        events = [json.loads(line) for line in open(os.path.join(self.uplift_dir, "events.jsonl"), encoding="utf-8")]
        reach = {}
        for ev in events:
            if ev["event"] == "reach":
                reach[ev["variant_id"]] = reach.get(ev["variant_id"], 0) + 1
        counts = list(reach.values())
        self.assertLessEqual(max(counts) - min(counts), 1)

    def test_all_events_conform_to_fmt002(self):
        schema = load_schema("funnel-event.schema.json")
        events = [json.loads(line) for line in open(os.path.join(self.uplift_dir, "events.jsonl"), encoding="utf-8")]
        self.assertGreater(len(events), 1000)
        for ev in events:
            validate(ev, schema)  # raises on violation

    def test_report_conforms_to_fmt003(self):
        schema = load_schema("report.schema.json")
        validate(self.uplift, schema)
        validate(self.null, schema)

    def test_labels_on_every_rate(self):
        for v in self.uplift["variants"]:
            for name in ("selection_rate", "operation_success_rate", "consumption_rate"):
                m = v["metrics"][name]
                self.assertIn("measurement_label", m)
                self.assertIn("numerator", m)
                self.assertIn("denominator", m)
                label = m["measurement_label"]
                self.assertTrue(label["grain"] and label["rules_version"] and label["definition"])

    def test_per_condition_reported(self):
        v = self._variant(self.uplift, "clear")
        self.assertEqual(len(v["per_condition"]), 1)
        self.assertEqual(v["per_condition"][0]["condition"], "mock-v1")
        self.assertIn("comparison", v["per_condition"][0])

    def test_value_formula_computable_with_params(self):
        v = self._variant(self.uplift, "clear")
        self.assertTrue(v["value"]["computable"])
        self.assertIn("incremental_margin_per_month", v["value"])

    def test_report_renders_offline_html(self):
        path = os.path.join(self.uplift_dir, "report.html")
        html = open(path, encoding="utf-8").read()
        self.assertIn("<!doctype html>", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))
        self.assertIn("selection", html)


class TestBudgetBreaker(unittest.TestCase):
    def test_budget_safe_stop_keeps_data(self):
        ws = LabWorkspace()
        try:
            manifest = base_manifest(
                experiment_id="e2e-budget",
                seed=1,
                replicates=12,
                budget={"max_operations": 40, "max_cost_units": 10_000_000, "max_wall_clock_seconds": 300},
            )
            report, out_dir, _ = ws.run(manifest)
            run = report["run"]
            self.assertEqual(run["status"], "incomplete")
            self.assertEqual(run["stopped_reason"], "budget:max_operations")
            self.assertEqual(run["assignments_executed"], 40)
            events_path = os.path.join(out_dir, "events.jsonl")
            self.assertTrue(os.path.exists(events_path))
            v = next(v for v in report["variants"] if not v.get("baseline"))
            # Below preregistered minimum: verdict must be undetermined, never a guess.
            self.assertEqual(v["verdict"], "undetermined")
            self.assertEqual(report["decision"]["run_incomplete"], True)
        finally:
            ws.close()


class TestGuardrailPath(unittest.TestCase):
    def test_verbose_variant_flags_guardrail_or_fake_growth(self):
        ws = LabWorkspace()
        try:
            manifest = base_manifest(
                experiment_id="e2e-guardrail",
                seed=20260822,
                replicates=40,
                variants=[
                    {"id": "control", "baseline": True,
                     "levels": {"description_clarity": "control", "output_verbosity": "baseline"}},
                    {"id": "clear-verbose", "baseline": False,
                     "levels": {"description_clarity": "clear", "output_verbosity": "verbose"}},
                ],
            )
            # factor list must match variant levels
            manifest["factors"] = [
                {"name": "description_clarity", "levels": ["control", "clear"]},
                {"name": "output_verbosity", "levels": ["baseline", "verbose"]},
            ]
            report, _, _ = ws.run(manifest)
            v = next(v for v in report["variants"] if not v.get("baseline"))
            breaches = [g for g in v["guardrails"] if g["status"] == "breach"]
            self.assertTrue(
                breaches or (v.get("fake_growth") or {}).get("flagged"),
                "verbose variant must trip a guardrail or the fake-growth check",
            )
            if breaches:
                self.assertIn(v["verdict"], ("effective_not_qualified", "unverified_growth"))
        finally:
            ws.close()


if __name__ == "__main__":
    unittest.main()
