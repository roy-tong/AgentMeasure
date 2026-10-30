import os
import tempfile
import unittest
from decimal import Decimal

from buyer_ledger.model import ChargeLine, PricingPolicy, SourceDocument, UsageEvent
from buyer_ledger.reconcile import (
    CLS_ESTIMATE_ONLY,
    CLS_INSUFFICIENT_EVIDENCE,
    CLS_MATCHED,
    CLS_OVERCHARGE_SUSPECTED,
    CLS_UNDERCHARGE,
    CLS_UNPRICED_USAGE,
    apply_pricing,
    reconcile,
)
from buyer_ledger.store import LedgerStore


def make_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return LedgerStore(path), path


def ensure_doc(store, tier):
    doc = SourceDocument(
        content_hash=("b" if tier == "bill_fact" else "u") * 64,
        provider="example", tier=tier, period="2026-10",
        doc_type="bill" if tier == "bill_fact" else "usage_export")
    if not store.get_document(doc.id):
        store.put_document(doc)
    return doc


def bill(store, amount, tool="", line_no=1):
    doc = ensure_doc(store, "bill_fact")
    store.put_charge_line(ChargeLine(
        document_id=doc.id, provider="example", currency="USD",
        amount=amount, period="2026-10", line_no=line_no, tool=tool,
        review_status="verified"))


def usage(store, qty, tool="", computed=None, line_no=1):
    doc = ensure_doc(store, "platform_usage")
    event = UsageEvent(
        document_id=doc.id, provider="example", billable_unit="operation",
        quantity=qty, period="2026-10", tool=tool, capability=tool,
        review_status="verified")
    store.put_usage_event(event)
    if computed is not None:
        rate = Decimal(computed) / Decimal(qty)
        store.put_policy(PricingPolicy(
            policy_id="fixture:" + (tool or "default"), version="1", provider="example",
            model="per_unit", unit_price=str(rate), capability=tool))
        apply_pricing(store, "example", "2026-10")


class ClassifyTest(unittest.TestCase):
    def test_matched_within_tolerance(self):
        cls, v = reconcile_cls("100.00", "100.05")
        self.assertEqual(cls, CLS_MATCHED)

    def test_overcharge_suspected(self):
        cls, v = reconcile_cls("120.00", "100.00")
        self.assertEqual(cls, CLS_OVERCHARGE_SUSPECTED)
        self.assertEqual(v, Decimal("20.00"))

    def test_undercharge(self):
        cls, v = reconcile_cls("80.00", "100.00")
        self.assertEqual(cls, CLS_UNDERCHARGE)


def reconcile_cls(bill, recount):
    from buyer_ledger.reconcile import classify
    return classify(Decimal(bill), Decimal(recount) if recount else None,
                    Decimal("0.01"), Decimal("0.005"))


class ReconcileTest(unittest.TestCase):
    def setUp(self):
        self.store, self.path = make_store()

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_matched_provider(self):
        bill(self.store, "60.00", tool="search")
        usage(self.store, "1200", tool="search", computed="60.00")
        results = reconcile(self.store, "2026-10")
        self.assertEqual(results[0]["variance_class"], CLS_MATCHED)
        self.assertEqual(results[0]["bill_total"], "60.00")
        self.assertEqual(results[0]["recount_total"], "60.00")

    def test_overcharge_flagged_with_disclosure(self):
        bill(self.store, "90.00", tool="search")
        usage(self.store, "1200", tool="search", computed="60.00")
        results = reconcile(self.store, "2026-10")
        r = results[0]
        self.assertEqual(r["variance_class"], CLS_OVERCHARGE_SUSPECTED)
        self.assertEqual(r["variance"], "30.00")
        self.assertTrue(r["detail"]["tiers_present"]["bill_fact"])

    def test_estimate_only_never_mixed_into_bill(self):
        # 只有用量与复算，无账单 → estimate_only，且不把估算写成实收
        usage(self.store, "1200", tool="search", computed="60.00")
        results = reconcile(self.store, "2026-10")
        r = results[0]
        self.assertEqual(r["variance_class"], CLS_ESTIMATE_ONLY)
        self.assertIsNone(r["bill_total"])
        self.assertEqual(r["recount_total"], "60.00")

    def test_missing_usage_is_not_zero(self):
        # 只有账单，无用量 → 证据不足；差异不得报成"实收-0"
        bill(self.store, "99.00")
        results = reconcile(self.store, "2026-10")
        r = results[0]
        self.assertEqual(r["variance_class"], CLS_INSUFFICIENT_EVIDENCE)
        self.assertIsNone(r["variance"])

    def test_unpriced_usage_class(self):
        bill(self.store, "99.00")
        usage(self.store, "500", tool="search")  # 无政策 → 未计价
        results = reconcile(self.store, "2026-10")
        self.assertEqual(results[0]["variance_class"], CLS_UNPRICED_USAGE)
        self.assertEqual(results[0]["detail"]["unpriced_usage_qty"], "500")

    def test_unlinked_items_disclosed(self):
        bill(self.store, "99.00")                     # 无 tool 标签
        usage(self.store, "100", tool="search", computed="5.00")
        results = reconcile(self.store, "2026-10")
        d = results[0]["detail"]
        self.assertEqual(len(d["unlinked_charge_lines"]), 1)
        self.assertGreaterEqual(len(d["unlinked_usage_events"]), 1)


class ApplyPricingTest(unittest.TestCase):
    def setUp(self):
        self.store, self.path = make_store()

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_pricing_applies_per_unit(self):
        self.store.put_policy(PricingPolicy(
            policy_id="ex:search", version="2026.1", provider="example",
            model="per_unit", unit_price="0.05", capability="search"))
        usage(self.store, "1200", tool="search")
        summary = apply_pricing(self.store, "example", "2026-10")
        self.assertEqual(summary["updated"], 1)
        events = self.store.effective_usage_events(period="2026-10")
        self.assertEqual(events[0]["computed_charge"], "60.00")
        self.assertEqual(events[0]["pricing_policy_id"], "ex:search@2026.1")

    def test_no_policy_leaves_none(self):
        usage(self.store, "1200", tool="search")
        summary = apply_pricing(self.store, "example", "2026-10")
        self.assertEqual(summary["skipped_no_policy_or_rule"], 1)
        events = self.store.effective_usage_events(period="2026-10")
        self.assertIsNone(events[0]["computed_charge"])   # 不补零


if __name__ == "__main__":
    unittest.main()
