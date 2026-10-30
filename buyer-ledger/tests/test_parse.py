import os
import tempfile
import unittest

from buyer_ledger import parsing
from buyer_ledger.llm import LLMClient
from buyer_ledger.model import SourceDocument


BILL_CSV = """Invoice Date,Service,Tool,Quantity,Rate,Amount,Currency
2026-10-03,API calls,search,1200,$0.05,"$60.00",USD
2026-10-05,API calls,lookup,300,$0.02,"$6.00",USD
2026-10-28,Subscription fee,,,,"$99.00",USD
Total,,,,,"$165.00",
"""

BILL_SPEC = {
    "tier": "bill_fact",
    "delimiter": ",",
    "header_row": 0,
    "skip_rows_containing": ["Total"],
    "columns": {
        "charged_at": {"col": "Invoice Date"},
        "description": {"col": "Service"},
        "tool": {"col": "Tool"},
        "quantity": {"col": "Quantity"},
        "unit_price": {"col": "Rate"},
        "amount": {"col": "Amount"},
        "currency": {"col": "Currency"},
    },
}

USAGE_CSV = """date,tool,capability,unit,qty
2026-10-03,search,search,operation,1000
2026-10-05,lookup,lookup,operation,300
"""

USAGE_SPEC = {
    "tier": "platform_usage",
    "delimiter": ",",
    "header_row": 0,
    "skip_rows_containing": [],
    "columns": {
        "occurred_at": {"col": "date"},
        "tool": {"col": "tool"},
        "capability": {"col": "capability"},
        "unit": {"col": "unit"},
        "quantity": {"col": "qty"},
        "currency": {"const": "USD"},
    },
}


def doc(tier="bill_fact"):
    return SourceDocument(content_hash="f" * 64, provider="example", tier=tier,
                          period="2026-10")


class FingerprintTest(unittest.TestCase):
    def test_same_header_same_fingerprint(self):
        a = parsing.format_fingerprint("a.csv", BILL_CSV)
        b = parsing.format_fingerprint("b-different-name.csv", BILL_CSV)
        self.assertEqual(a, b)

    def test_different_header_different_fingerprint(self):
        a = parsing.format_fingerprint("a.csv", BILL_CSV)
        b = parsing.format_fingerprint("a.csv", BILL_CSV.replace("Rate", "Price"))
        self.assertNotEqual(a, b)


class ApplySpecTest(unittest.TestCase):
    def test_bill_parse_with_symbol_cleanup(self):
        result = parsing.apply_spec("bill.csv", BILL_CSV, BILL_SPEC, doc(),
                                    provider="example", period="2026-10")
        self.assertEqual(len(result["charge_lines"]), 3)
        amounts = [l.amount for l in result["charge_lines"]]
        self.assertEqual(amounts, ["60.00", "6.00", "99.00"])
        self.assertEqual(result["charge_lines"][0].currency, "USD")
        self.assertEqual(result["charge_lines"][0].tool, "search")

    def test_stated_total_constraint_pass(self):
        result = parsing.apply_spec("bill.csv", BILL_CSV, BILL_SPEC, doc(),
                                    provider="example", period="2026-10")
        self.assertIsNotNone(result["constraint"])
        self.assertTrue(result["constraint"]["match"])

    def test_stated_total_constraint_fail_marks_pending(self):
        bad = BILL_CSV.replace('"$165.00"', '"$999.00"')
        result = parsing.apply_spec("bill.csv", bad, BILL_SPEC, doc(),
                                    provider="example", period="2026-10")
        self.assertFalse(result["constraint"]["match"])
        self.assertTrue(all(l.review_status == "pending"
                            for l in result["charge_lines"]))
        self.assertTrue(any("CONSTRAINT FAILED" in n for n in result["notes"]))

    def test_usage_parse(self):
        result = parsing.apply_spec("usage.csv", USAGE_CSV, USAGE_SPEC,
                                    doc(tier="platform_usage"), provider="example",
                                    period="2026-10")
        self.assertEqual(len(result["usage_events"]), 2)
        self.assertEqual(result["usage_events"][0].quantity, "1000")
        self.assertIsNone(result["usage_events"][0].computed_charge)

    def test_evidence_attached(self):
        result = parsing.apply_spec("bill.csv", BILL_CSV, BILL_SPEC, doc(),
                                    provider="example", period="2026-10")
        ev = result["charge_lines"][0].evidence[0]
        self.assertTrue(ev.document_id.startswith("doc-"))
        self.assertIn("row 1", ev.locator)


class SpecValidationTest(unittest.TestCase):
    def test_valid_spec_passes(self):
        self.assertEqual(parsing.validate_spec(BILL_SPEC), [])

    def test_unknown_field_rejected(self):
        bad = dict(BILL_SPEC)
        bad["columns"] = dict(BILL_SPEC["columns"], bogus={"col": "x"})
        self.assertTrue(any("unknown field" in e for e in parsing.validate_spec(bad)))

    def test_bad_tier_rejected(self):
        bad = dict(BILL_SPEC, tier="reference")
        self.assertTrue(any("tier" in e for e in parsing.validate_spec(bad)))


class FakeLLM(LLMClient):
    """注入式假 LLM：回放固定 spec，测试 agent 生成路径（不发网络请求）。"""

    def __init__(self, spec):
        super().__init__(base_url="http://fake", api_key="k", model="fake")
        self.spec = spec
        self.calls = 0

    def chat(self, system, user, temperature=0.0, timeout=60):
        self.calls += 1
        import json
        return "```json\n" + json.dumps(self.spec) + "\n```"


class AgentSpecTest(unittest.TestCase):
    def test_agent_generates_and_validates(self):
        fake = FakeLLM(BILL_SPEC)
        spec, golden = parsing.agent_generate_spec(
            "bill.csv", BILL_CSV, "example", "bill", fake)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(parsing.validate_spec(spec), [])
        self.assertEqual(len(golden), 0)  # 默认不外发/保存原始数据行

    def test_invalid_agent_spec_raises(self):
        bad_spec = dict(BILL_SPEC, tier="bogus")
        fake = FakeLLM(bad_spec)
        from buyer_ledger.model import LedgerError
        with self.assertRaises(LedgerError):
            parsing.agent_generate_spec("bill.csv", BILL_CSV, "example", "bill", fake)

    def test_golden_replay_produces_rows(self):
        _, golden = parsing.agent_generate_spec(
            "bill.csv", BILL_CSV, "example", "bill", FakeLLM(BILL_SPEC), sample_rows=2)
        probe = parsing.replay_golden(BILL_CSV, BILL_SPEC, golden)
        result = parsing.apply_spec("probe.csv", probe, BILL_SPEC, doc(),
                                    provider="example", period="2026-10")
        self.assertEqual(len(result["charge_lines"]), len(golden))


if __name__ == "__main__":
    unittest.main()
