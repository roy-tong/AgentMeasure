import os
import tempfile
import unittest
from decimal import Decimal

from buyer_ledger.model import ChargeLine, SourceDocument, UsageEvent
from buyer_ledger.store import LedgerStore


def make_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return LedgerStore(path), path


def doc(provider="example", period="2026-10", tier="bill_fact", h="a"):
    return SourceDocument(content_hash=(h * 64), provider=provider, tier=tier,
                          period=period)


class IdempotencyTest(unittest.TestCase):
    """INV-1：同哈希文档、同指纹行重复导入不产生新事实。"""

    def setUp(self):
        self.store, self.path = make_store()

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_document_dedup(self):
        d = doc(h="a")
        _, created1 = self.store.put_document(d)
        _, created2 = self.store.put_document(d)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(len(self.store.list_documents()), 1)

    def test_charge_line_dedup_and_totals(self):
        self.store.put_document(doc(h="a"))
        cl = ChargeLine(document_id=doc(h="a").id, provider="example",
                        currency="USD", amount="10.00", period="2026-10")
        _, c1 = self.store.put_charge_line(cl)
        _, c2 = self.store.put_charge_line(cl)
        self.assertTrue(c1)
        self.assertFalse(c2)
        lines = self.store.effective_charge_lines(period="2026-10")
        total = sum((Decimal(l["amount"]) for l in lines), Decimal("0"))
        self.assertEqual(total, Decimal("10.00"))  # 重放 100 次不涨 100 倍


class RevisionTest(unittest.TestCase):
    """INV-2：修订走 supersedes，冲销走负额行，汇总只计有效行。"""

    def setUp(self):
        self.store, self.path = make_store()
        self.store.put_document(doc(h="a"))

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def _line(self, amount, line_no=1, **kw):
        return ChargeLine(document_id=doc(h="a").id, provider="example",
                          currency="USD", amount=amount, period="2026-10",
                          line_no=line_no, **kw)

    def test_supersede_replaces_total(self):
        original = self._line("10.00")
        self.store.put_charge_line(original)
        corrected = self._line("12.00", supersedes=original.id, revision=2,
                               note="vendor reissued")
        # 修正行指纹不同（金额不同）→ 新行；旧行被指向后从有效集中排除
        self.store.put_charge_line(corrected)
        lines = self.store.effective_charge_lines(period="2026-10")
        self.assertEqual(len(lines), 1)
        self.assertEqual(Decimal(lines[0]["amount"]), Decimal("12.00"))

    def test_reversal_nets_to_zero(self):
        original = self._line("25.00")
        self.store.put_charge_line(original)
        reversal = self._line("-25.00", reversal_of=original.id)
        self.store.put_charge_line(reversal)
        total = sum((Decimal(l["amount"]) for l in
                     self.store.effective_charge_lines(period="2026-10")),
                    Decimal("0"))
        self.assertEqual(total, Decimal("0"))

    def test_usage_revision(self):
        self.store.put_document(doc(h="b", tier="platform_usage"))
        ue = UsageEvent(document_id=doc(h="b", tier="platform_usage").id, provider="example",
                        billable_unit="operation", quantity="10",
                        period="2026-10")
        self.store.put_usage_event(ue)
        fixed = UsageEvent(document_id=doc(h="b", tier="platform_usage").id, provider="example",
                           billable_unit="operation", quantity="8",
                           period="2026-10", supersedes=ue.id, revision=2)
        self.store.put_usage_event(fixed)
        events = self.store.effective_usage_events(period="2026-10")
        self.assertEqual(len(events), 1)
        self.assertEqual(Decimal(events[0]["quantity"]), Decimal("8"))


class PolicyStoreTest(unittest.TestCase):
    def setUp(self):
        self.store, self.path = make_store()

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def test_capability_policy_preferred_over_default(self):
        from buyer_ledger.model import PricingPolicy
        self.store.put_policy(PricingPolicy(
            policy_id="ex:default", version="1", provider="example",
            model="per_unit", unit_price="0.05"))
        self.store.put_policy(PricingPolicy(
            policy_id="ex:search", version="1", provider="example",
            model="per_unit", unit_price="0.10", capability="search"))
        self.assertEqual(self.store.find_policy("example", "search").unit_price, "0.10")
        self.assertEqual(self.store.find_policy("example", "").unit_price, "0.05")
        self.assertIsNone(self.store.find_policy("other", ""))


if __name__ == "__main__":
    unittest.main()
