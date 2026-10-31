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
        self.assertEqual("1.2989", result["totals"]["roi"])
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
                text=True, capture_output=True)
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
                text=True, capture_output=True)
            self.assertEqual(2, cp.returncode)
            self.assertIn("overwrite", cp.stderr)


if __name__ == "__main__":
    unittest.main()
