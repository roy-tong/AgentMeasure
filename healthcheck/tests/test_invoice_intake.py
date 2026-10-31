"""Local invoice extraction: never assume the parsed fields are booked costs."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from verovo_healthcheck.invoice_intake import InvoiceIntakeError, extract_invoice


class InvoiceIntakeTests(unittest.TestCase):
    def test_extract_keeps_unverified_provenance(self):
        fake = types.ModuleType("invoice2data")
        fake.extract_data = lambda path: {
            "issuer": "Example Provider", "invoice_number": "INV-001",
            "date": "2026-10-31", "currency": "usd",
            "amount": 43.50, "template_name": "example.yml",
        }
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "example.pdf"
            src.write_bytes(b"invoice test fixture")
            with patch.dict(sys.modules, {"invoice2data": fake}):
                record = extract_invoice(src)
            self.assertEqual(record["currency"], "USD")
            self.assertEqual(record["gross_amount"], "43.5")
            self.assertEqual(record["review_status"], "unreviewed")
            self.assertEqual(record["cost_ledger_status"], "not_imported")
            self.assertIsNone(record["task_allocation"])
            self.assertEqual(len(record["source_sha256"]), 64)
            self.assertNotIn("source_path", record)

    def test_invalid_and_missing_source(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(InvoiceIntakeError):
                extract_invoice(Path(d) / "missing.pdf")
            bad = Path(d) / "invoice.exe"
            bad.write_bytes(b"bad")
            with self.assertRaises(InvoiceIntakeError):
                extract_invoice(bad)

    def test_rejects_missing_invoice_fields(self):
        fake = types.ModuleType("invoice2data")
        fake.extract_data = lambda path: {"amount": 12}
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "invoice.pdf"
            src.write_bytes(b"fixture")
            with patch.dict(sys.modules, {"invoice2data": fake}):
                with self.assertRaisesRegex(InvoiceIntakeError, "issuer"):
                    extract_invoice(src)


if __name__ == "__main__":
    unittest.main()
