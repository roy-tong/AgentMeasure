import os
import tempfile
import unittest
from decimal import Decimal

from buyer_ledger.model import ChargeLine, PricingPolicy, SourceDocument, UsageEvent
from buyer_ledger.reconcile import apply_pricing, reconcile
from buyer_ledger.report import render_report
from buyer_ledger.store import LedgerStore


def make_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return LedgerStore(path), path


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.store, self.path = make_store()
        bill_doc = SourceDocument(
            content_hash="b" * 64, provider="example", tier="bill_fact", period="2026-10")
        usage_doc = SourceDocument(
            content_hash="u" * 64, provider="example", tier="platform_usage",
            period="2026-10", doc_type="usage_export")
        self.store.put_document(bill_doc)
        self.store.put_document(usage_doc)
        self.store.put_charge_line(ChargeLine(
            document_id=bill_doc.id, provider="example", currency="USD",
            amount="90.00", period="2026-10", tool="search", line_no=1,
            review_status="verified"))
        self.store.put_usage_event(UsageEvent(
            document_id=usage_doc.id, provider="example",
            billable_unit="operation", quantity="1200", period="2026-10",
            tool="search", capability="search", review_status="verified"))
        self.store.put_policy(PricingPolicy(
            policy_id="fixture", version="1", provider="example", model="per_unit",
            capability="search", unit_price="0.05"))
        apply_pricing(self.store, "example", "2026-10")
        self.results = reconcile(self.store, "2026-10")

    def tearDown(self):
        self.store.close()
        os.unlink(self.path)

    def _render(self):
        rows = []
        for r in self.results:
            rows.append(r)
        return render_report("2026-10", rows, documents_count=2,
                             ledger_path="test.db")

    def test_three_tiers_separated(self):
        md = self._render()
        self.assertIn("一、账单事实", md)
        self.assertIn("二、复算估算", md)
        self.assertIn("三、差异与结论", md)

    def test_bill_and_recount_not_merged(self):
        md = self._render()
        self.assertIn("90.00", md)      # 实收
        self.assertIn("60.00", md)     # 复算
        self.assertIn("多收嫌疑", md)   # 分类措辞：嫌疑待证据
        self.assertNotIn("实收 150", md)

    def test_estimate_disclaimer_present(self):
        md = self._render()
        self.assertIn("估算不冒充", md)
        self.assertIn("缺失不补零", md)

    def test_drilldown_note(self):
        md = self._render()
        self.assertIn("SourceDocument", md)
        self.assertIn("审计链", md)

    def test_unlinked_section_renders(self):
        md = self._render()
        self.assertIn("四、无法关联项", md)


if __name__ == "__main__":
    unittest.main()
