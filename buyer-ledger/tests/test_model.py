import unittest

from buyer_ledger.model import (
    ChargeLine,
    EvidenceRef,
    LedgerError,
    PricingPolicy,
    SourceDocument,
    UsageEvent,
    dec,
)


def doc(tier="bill_fact", provider="example"):
    return SourceDocument(content_hash="a" * 64, provider=provider, tier=tier,
                          period="2026-10")


class DecimalDisciplineTest(unittest.TestCase):
    def test_refuses_float(self):
        with self.assertRaises(LedgerError):
            ChargeLine(document_id="doc-x", provider="p", currency="USD", amount=1.5)

    def test_decimal_string_ok(self):
        cl = ChargeLine(document_id="doc-x", provider="p", currency="USD", amount="1.50")
        self.assertEqual(str(cl.amount_dec()), "1.50")

    def test_bad_decimal_rejected(self):
        with self.assertRaises(LedgerError):
            ChargeLine(document_id="doc-x", provider="p", currency="USD", amount="abc")


class ChargeLineTest(unittest.TestCase):
    def test_reversal_must_be_negative(self):
        with self.assertRaises(LedgerError):
            ChargeLine(document_id="doc-x", provider="p", currency="USD",
                       amount="10.00", reversal_of="cl-old")
        cl = ChargeLine(document_id="doc-x", provider="p", currency="USD",
                        amount="-10.00", reversal_of="cl-old")
        self.assertTrue(cl.id.startswith("cl-"))

    def test_fingerprint_stable(self):
        a = ChargeLine(document_id="d", provider="p", currency="USD",
                       amount="3.00", description="api calls")
        b = ChargeLine(document_id="d", provider="p", currency="USD",
                       amount="3.00", description="api calls")
        self.assertEqual(a.fingerprint, b.fingerprint)


class UsageEventTest(unittest.TestCase):
    def test_no_price_without_computed_charge(self):
        # 手工塞单价而未经价格政策计算 → 拒绝（估算只能来自政策）
        with self.assertRaises(LedgerError):
            UsageEvent(document_id="d", provider="p", billable_unit="operation",
                       quantity="10", unit_price_applied="0.05")

    def test_computed_charge_optional(self):
        ue = UsageEvent(document_id="d", provider="p", billable_unit="operation",
                        quantity="10")
        self.assertIsNone(ue.computed_charge)


class EvidenceTest(unittest.TestCase):
    def test_evidence_roundtrip(self):
        e = EvidenceRef(document_id="doc-abc", locator="row 3", quote="api calls 12.00")
        cl = ChargeLine(document_id="doc-abc", provider="p", currency="USD",
                        amount="12.00", evidence=[e])
        self.assertEqual(cl.evidence[0].locator, "row 3")


class PricingPolicyTest(unittest.TestCase):
    def test_per_unit(self):
        p = PricingPolicy(policy_id="p:1", version="1", provider="p",
                          model="per_unit", unit_price="0.05")
        charge, note = p.charge_for(dec("1000"))
        self.assertEqual(str(charge), "50.00")

    def test_volume_tiered(self):
        p = PricingPolicy(policy_id="p:2", version="1", provider="p",
                          model="volume_tiered",
                          tiers=[{"unit_from": 0, "unit_price": "0.05"},
                                 {"unit_from": 10000, "unit_price": "0.03"}])
        self.assertEqual(str(p.charge_for(dec("10000"))[0]), "300.00")
        self.assertEqual(str(p.charge_for(dec("9999"))[0]), "499.95")

    def test_free_quota_overage(self):
        p = PricingPolicy(policy_id="p:3", version="1", provider="p",
                          model="free_quota", free_quota="1000", unit_price="0.02")
        self.assertEqual(str(p.charge_for(dec("800"))[0]), "0")
        self.assertEqual(str(p.charge_for(dec("1500"))[0]), "10.00")

    def test_subscription_needs_manual_rule(self):
        p = PricingPolicy(policy_id="p:4", version="1", provider="p",
                          model="subscription")
        charge, note = p.charge_for(dec("999"))
        self.assertIsNone(charge)  # 缺失不补零（INV-3/INV-4）
        self.assertIn("allocation", note)

    def test_tier_model_requires_tiers(self):
        with self.assertRaises(LedgerError):
            PricingPolicy(policy_id="p:5", version="1", provider="p",
                          model="volume_tiered")


if __name__ == "__main__":
    unittest.main()
