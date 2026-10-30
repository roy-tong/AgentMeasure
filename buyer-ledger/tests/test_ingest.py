import os
import tempfile
import unittest
from decimal import Decimal

from buyer_ledger import ingest
from buyer_ledger.store import LedgerStore

BILL_CSV = """Invoice Date,Service,Tool,Quantity,Rate,Amount,Currency
2026-10-03,API calls,search,1200,$0.05,"$60.00",USD
2026-10-05,API calls,lookup,300,$0.02,"$6.00",USD
Total,,,,,"$66.00",
"""

SPEC = {
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


def write_tmp(content, suffix=".csv"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class ImportFlowTest(unittest.TestCase):
    def setUp(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = db_path
        self.store = LedgerStore(db_path)
        self.bill_path = write_tmp(BILL_CSV)

    def tearDown(self):
        self.store.close()
        os.unlink(self.db_path)
        os.unlink(self.bill_path)

    def test_import_with_rule_then_idempotent_reimport(self):
        from buyer_ledger import parsing
        fingerprint = parsing.format_fingerprint("bill.csv", BILL_CSV)
        self.store.put_parse_rule(fingerprint, SPEC, provider="example",
                                  doc_type="bill", tier="bill_fact",
                                  created_via="manual", golden=[])
        r1 = ingest.import_file(self.store, self.bill_path, provider="example",
                                tier="bill_fact", period="2026-10")
        self.assertFalse(r1["duplicate"])
        self.assertEqual(r1["charge_lines"], 2)
        self.assertEqual(r1["spec_source"], "replay")

        # M1 验收：同批数据重复导入不重复计费
        r2 = ingest.import_file(self.store, self.bill_path, provider="example",
                                tier="bill_fact", period="2026-10")
        self.assertTrue(r2["duplicate"])
        total = sum((Decimal(l["amount"]) for l in
                     self.store.effective_charge_lines(period="2026-10")),
                    Decimal("0"))
        self.assertEqual(total, Decimal("66.00"))

    def test_import_without_rule_returns_hint(self):
        r = ingest.import_file(self.store, self.bill_path, provider="example",
                               tier="bill_fact", period="2026-10")
        self.assertEqual(r["charge_lines"], 0)
        self.assertTrue(any("parse --agent" in n for n in r["notes"]))

    def test_unparsed_document_can_be_reparsed_after_rule_arrives(self):
        # 首次导入无规则（只登记文档）；规则就位后再次导入同文件 → 解析照常发生
        from buyer_ledger import parsing
        ingest.import_file(self.store, self.bill_path, provider="example",
                           tier="bill_fact", period="2026-10")
        fingerprint = parsing.format_fingerprint("bill.csv", BILL_CSV)
        self.store.put_parse_rule(fingerprint, SPEC, provider="example",
                                  doc_type="bill", tier="bill_fact",
                                  created_via="manual", golden=[])
        r2 = ingest.import_file(self.store, self.bill_path, provider="example",
                                tier="bill_fact", period="2026-10")
        self.assertFalse(r2["duplicate"])
        self.assertEqual(r2["charge_lines"], 2)
        # 第三次：已解析过 → 幂等 no-op
        r3 = ingest.import_file(self.store, self.bill_path, provider="example",
                                tier="bill_fact", period="2026-10")
        self.assertTrue(r3["duplicate"])
        self.assertEqual(r3["charge_lines"], 0)

    def test_reference_tier_stored_not_parsed(self):
        path = write_tmp("contract text", suffix=".txt")
        r = ingest.import_file(self.store, path, provider="example",
                               tier="reference", period="2026-10")
        self.assertEqual(r["charge_lines"], 0)
        self.assertTrue(any("reference only" in n for n in r["notes"]))
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
