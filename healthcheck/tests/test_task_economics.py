#!/usr/bin/env python3
"""Task economics: three-ledger connection, dedup, allocation and verified success."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verovo_healthcheck import task_economics as econ


def base_case():
    return {
        "schema_version": "1.0", "case_id": "case-1", "currency": "USD",
        "period": {"start": "2026-10-01", "end": "2026-10-31"},
        "allocation_rules": [
            {"id": "equal", "version": "1", "method": "equal"},
        ],
        "tasks": [
            {"task_id": "t1", "type": "support"},
            {"task_id": "t2", "type": "support"},
        ],
        "runs": [
            {"run_id": "r1", "task_id": "t1"},
            {"run_id": "r2", "task_id": "t2"},
            {"run_id": "rx"},  # unallocated
        ],
        "usage": [
            {"usage_id": "u1", "run_id": "r1", "cost": "1.50",
             "financialized": True, "source_ref": "trace:r1"},
            {"usage_id": "u2", "run_id": "r2", "cost": "2.00",
             "financialized": True, "source_ref": "trace:r2"},
            {"usage_id": "u3", "run_id": "rx", "cost": "9.00",
             "financialized": True, "source_ref": "trace:rx"},
            {"usage_id": "u4", "run_id": "r1", "cost": "99.00",
             "financialized": False, "source_ref": "trace:u4"},
        ],
        "documents": [
            {"document_id": "inv1", "type": "invoice", "total": "43.50",
             "source_ref": "invoice:1"},
        ],
        "cost_items": [
            {"cost_id": "c1", "task_id": "t1", "amount": "10.00",
             "source_ref": "invoice:1", "vendor": "v"},
            {"cost_id": "c2", "task_id": "t1", "amount": "10.00",
             "source_ref": "invoice:1", "vendor": "v"},
            {"cost_id": "c3", "amount": "30.00", "source_ref": "invoice:shared",
             "vendor": "v", "allocation_rule": "equal"},
        ],
        "outcomes": [
            {"task_id": "t1", "status": "success", "verified": True,
             "source_ref": "crm:1", "value": "100.00", "value_verified": True},
            {"task_id": "t2", "status": "pending", "verified": False},
        ],
        "loss_events": [
            {"loss_id": "l1", "task_id": "t1", "amount": "5.00",
             "status": "confirmed", "source_ref": "claim:1"},
        ],
    }


class TestTaskEconomics(unittest.TestCase):
    def test_full_case_cost_and_roi(self):
        result = econ.evaluate(base_case())
        self.assertEqual("43.50", result["totals"]["fully_loaded_cost"])
        self.assertEqual(1, result["totals"]["verified_success_tasks"])
        self.assertEqual("43.50", result["totals"]["cost_per_verified_success"])
        self.assertIsNone(result["totals"]["roi"])
        self.assertIn("incomplete", result["totals"]["roi_reason"])
        self.assertEqual("5.00", result["totals"]["loss_events"])
        self.assertTrue(any(f["code"] == "duplicate_cost_item"
                            for f in result["findings"]))
        self.assertTrue(any(f["code"] == "unverified_outcome"
                            for f in result["findings"]))
        self.assertEqual(1, len(result["unallocated"]))
        self.assertEqual("u3", result["unallocated"][0]["id"])
        # Unfinancialized usage is neither cost nor an unallocated finding.
        self.assertNotIn("u4", [x["id"] for x in result["unallocated"]])

    def test_cross_currency_is_rejected(self):
        case = base_case()
        case["cost_items"][2]["currency"] = "EUR"
        with self.assertRaisesRegex(econ.EconomicsError, "cross-currency"):
            econ.evaluate(case)

    def test_no_verified_value_makes_roi_null(self):
        case = base_case()
        case["outcomes"] = [{"task_id": "t1", "status": "success",
                             "verified": True, "source_ref": "crm:1"}]
        case["usage"] = [u for u in case["usage"] if u["usage_id"] != "u3"]
        result = econ.evaluate(case)
        self.assertIsNone(result["totals"]["roi"])
        self.assertIn("no verified business value", result["totals"]["roi_reason"])

    def test_shared_cost_without_rule_is_unallocated_not_spread(self):
        case = base_case()
        for item in case["cost_items"]:
            item.pop("allocation_rule", None)
        result = econ.evaluate(case)
        self.assertEqual("13.50", result["totals"]["fully_loaded_cost"])
        self.assertTrue(any("allocation_rule" in row["reason"]
                            for row in result["unallocated"]))

    def test_decimal_arithmetic_is_exact(self):
        case = base_case()
        case["tasks"] = [{"task_id": "t1", "type": "x"}]
        case["runs"] = [{"run_id": "r1", "task_id": "t1"}]
        case["usage"] = []
        case["cost_items"] = [
            {"cost_id": "a", "task_id": "t1", "amount": "0.10",
             "source_ref": "a"},
            {"cost_id": "b", "task_id": "t1", "amount": "0.20",
             "source_ref": "b"},
        ]
        case["outcomes"] = []
        result = econ.evaluate(case)
        self.assertEqual("0.30", result["totals"]["fully_loaded_cost"])

    def test_cli_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_path = root / "case.json"
            case_path.write_text(json.dumps(base_case()), encoding="utf-8")
            json_path = root / "out.json"
            md_path = root / "out.md"
            cp = subprocess.run(
                [sys.executable, "-m", "verovo_healthcheck.cli", "economics",
                 "--case", str(case_path), "--json", str(json_path),
                 "--markdown", str(md_path)],
                text=True, capture_output=True,
                cwd=str(Path(__file__).resolve().parents[1]))
            self.assertEqual(0, cp.returncode, cp.stdout + cp.stderr)
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())
            self.assertIn("Task economics", md_path.read_text(encoding="utf-8"))

    def test_cli_refuses_output_over_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(base_case()), encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-m", "verovo_healthcheck.cli", "economics",
                 "--case", str(path), "--json", str(path)],
                text=True, capture_output=True,
                cwd=str(Path(__file__).resolve().parents[1]))
            self.assertEqual(2, cp.returncode)
            self.assertIn("overwrite", cp.stderr)


    def test_rounding_never_charges_zero_weight_or_negative_share(self):
        from decimal import Decimal
        shares = econ._allocate(Decimal("0.03"), ["a", "b", "c"],
                                {"method": "headcount", "basis": {"weights": {"a": 1, "b": 1, "c": 0}}})
        self.assertEqual(Decimal("0.03"), sum(shares.values()))
        self.assertEqual(0, shares["c"])
        self.assertTrue(all(v >= 0 for v in shares.values()))

    def test_duplicate_outcome_does_not_double_revenue(self):
        case = base_case()
        case["outcomes"].append(dict(case["outcomes"][0]))
        self.assertEqual("100.00", econ.evaluate(case)["totals"]["verified_business_value"])

    def test_reverted_outcome_removes_success_and_value(self):
        case = base_case()
        case["outcomes"].append({"task_id": "t1", "status": "reverted", "verified": True, "source_ref": "crm:reversal"})
        totals = econ.evaluate(case)["totals"]
        self.assertEqual(0, totals["verified_success_tasks"])
        self.assertIsNone(totals["roi"])

    def test_value_needs_source_and_real_boolean(self):
        for field, value in [("source_ref", ""), ("verified", "false"), ("value_verified", "false")]:
            case = base_case()
            case["outcomes"][0][field] = value
            self.assertIsNone(econ.evaluate(case)["totals"]["roi"])

    def test_usage_and_bill_can_share_charge_identity(self):
        case = base_case()
        case["usage"][0]["charge_id"] = "vendor:line-1"
        case["cost_items"] = [{"cost_id": "invoice-line", "task_id": "t1", "amount": "1.50", "source_ref": "invoice:line1", "charge_id": "vendor:line-1"}]
        result = econ.evaluate(case)
        self.assertEqual("3.50", result["totals"]["fully_loaded_cost"])
        self.assertTrue(any(x["code"] == "duplicate_charge" for x in result["findings"]))

    def test_zero_verified_value_is_negative_one_roi(self):
        case = base_case()
        case["usage"] = [u for u in case["usage"] if u["usage_id"] != "u3"]
        case["outcomes"][0]["value"] = "0"
        self.assertEqual("-1.0000", econ.evaluate(case)["totals"]["roi"])

    def test_unconfirmed_and_duplicate_losses_are_excluded(self):
        case = base_case()
        case["loss_events"] += [dict(case["loss_events"][0]), {"loss_id": "l2", "task_id": "t1", "amount": "500", "status": "estimated", "source_ref": "estimate"}]
        self.assertEqual("5.00", econ.evaluate(case)["totals"]["loss_events"])


if __name__ == "__main__":
    unittest.main()
