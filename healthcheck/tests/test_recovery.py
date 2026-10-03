"""Recovery-ledger tests: realized value is counted separately from a claim.

BP r28 p8 row four: 实际退款/抵扣 gets its own table — linked to the original
disputed line, with the confirmation date and the evidence reference. The
ledger refuses to flatter: over-claimed concessions are input errors, rows the
pack does not contain are listed as unmatched, and only credited/paid cash
counts as realized.
"""
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck import dispute as dispute_mod
from am_healthcheck import recovery as recovery_mod
from am_healthcheck.recovery import RecoveryError, load_confirmations

EXPORT = fixture("vendor-export-intercom.csv")


def write_csv(text):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                      encoding="utf-8", newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


def build_pack(tmpdir):
    pack = dispute_mod.build_pack(
        export_path=EXPORT, vendor_id="intercom", buyer_label="Test Buyer")
    pack_path = os.path.join(tmpdir, "dispute-pack.json")
    dispute_mod.write_pack(pack, tmpdir)
    return pack_path, pack


class TestConfirmations(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _load(self, text):
        path = write_csv(text)
        self.paths.append(path)
        return load_confirmations(path)

    def test_known_statuses_load(self):
        rows = self._load("conversation_id,status,confirmed_date,amount,evidence_ref\n"
                          "C-1001,credited,2026-09-10,2.97,credit-note-7\n")
        self.assertEqual(rows[0]["status"], "credited")
        self.assertEqual(rows[0]["amount"], 2.97)

    def test_unknown_status_refused(self):
        with self.assertRaises(RecoveryError):
            self._load("conversation_id,status\nC-1001,refunded\n")

    def test_bad_amount_refused(self):
        with self.assertRaises(RecoveryError):
            self._load("conversation_id,status,amount\nC-1001,paid,lots\n")

    def test_negative_amount_refused(self):
        with self.assertRaises(RecoveryError):
            self._load("conversation_id,status,amount\nC-1001,paid,-5\n")

    def test_missing_status_column_refused(self):
        with self.assertRaises(RecoveryError):
            self._load("conversation_id,amount\nC-1001,5\n")


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.paths = []
        self.tmpdir = tempfile.mkdtemp()
        self.pack_path, self.pack = build_pack(self.tmpdir)

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)
        for name in os.listdir(self.tmpdir):
            os.unlink(os.path.join(self.tmpdir, name))
        os.rmdir(self.tmpdir)

    def _confirm(self, text):
        path = write_csv(text)
        self.paths.append(path)
        return path

    def test_disputed_lines_come_from_the_pack(self):
        ledger = recovery_mod.build_ledger(
            self.pack_path,
            self._confirm("conversation_id,status\n"))
        self.assertGreater(ledger["totals"]["disputed_lines"], 0)
        # every row is a line the pack found billed-but-not-billable
        for row in ledger["rows"]:
            self.assertEqual(row["original_finding"], "billed_but_not_billable")

    def test_realized_counts_only_cash_statuses(self):
        # Two concessions on the same line: an acceptance on paper, then cash.
        path = self._confirm(
            "conversation_id,status,confirmed_date,amount,evidence_ref\n"
            "C-1003,accepted,2026-09-01,,ticket-1\n"
            "C-1003,credited,2026-09-10,0.99,credit-note-7\n")
        ledger = recovery_mod.build_ledger(self.pack_path, path)
        row = ledger["rows"][0]
        self.assertEqual(row["status"], "credited")
        self.assertEqual(row["realized_amount"], 0.99)
        self.assertEqual(ledger["totals"]["realized"], 0.99)

    def test_over_realization_is_refused_not_absorbed(self):
        # Intercom fixture price is $0.99; claiming 99.00 on one line is an
        # input error. A ledger that absorbs it would flatter the buyer.
        path = self._confirm(
            "conversation_id,status,amount\nC-1003,paid,99.00\n")
        with self.assertRaises(RecoveryError):
            recovery_mod.build_ledger(self.pack_path, path)

    def test_unmatched_rows_listed_never_counted(self):
        path = self._confirm(
            "conversation_id,status,amount\n"
            "C-1003,credited,0.99\n"
            "C-9999,credited,42.00\n")
        ledger = recovery_mod.build_ledger(self.pack_path, path)
        self.assertEqual(len(ledger["unmatched"]), 1)
        self.assertEqual(ledger["unmatched"][0]["conversation_id"], "C-9999")
        self.assertEqual(ledger["totals"]["realized"], 0.99)

    def test_rejected_and_pending_do_not_count_as_realized(self):
        path = self._confirm(
            "conversation_id,status,amount\n"
            "C-1003,rejected,0.99\n"
            "C-1004,pending,0.99\n")
        ledger = recovery_mod.build_ledger(self.pack_path, path)
        self.assertEqual(ledger["totals"]["realized"], 0.0)
        self.assertEqual(ledger["totals"]["rejected_lines"], 1)
        # 4 disputed lines: 1 rejected, the rest still awaiting a concession
        self.assertEqual(ledger["totals"]["pending_lines"], 3)

    def test_outstanding_is_claimed_minus_realized(self):
        path = self._confirm(
            "conversation_id,status,amount\nC-1003,credited,0.99\n")
        ledger = recovery_mod.build_ledger(self.pack_path, path)
        t = ledger["totals"]
        self.assertEqual(t["outstanding"], round(t["claimed"] - t["realized"], 2))

    def test_non_pack_input_refused(self):
        other = os.path.join(self.tmpdir, "not-a-pack.json")
        with open(other, "w", encoding="utf-8") as fh:
            fh.write('{"schema": "something/else"}')
        with self.assertRaises(RecoveryError):
            recovery_mod.build_ledger(
                other, self._confirm("conversation_id,status\nC-1001,paid\n"))

    def test_markdown_and_csv_render(self):
        path = self._confirm(
            "conversation_id,status,confirmed_date,amount,evidence_ref\n"
            "C-1003,credited,2026-09-10,0.99,credit-note-7\n")
        ledger = recovery_mod.build_ledger(self.pack_path, path)
        paths = recovery_mod.write_ledger(ledger, self.tmpdir)
        with open(paths["markdown"], encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("Recovery ledger", md)
        self.assertIn("realized (credited + paid)", md)
        self.assertIn("Unmatched confirmation rows"
                      if ledger["unmatched"] else "never added to these numbers",
                      md)
        self.assertIn("Renewal savings", md)
        with open(paths["csv"], encoding="utf-8") as fh:
            header = fh.readline().strip()
        self.assertEqual(
            header,
            "conversation_id,export_line,original_finding,claimed_amount,"
            "status,confirmed_date,realized_amount,evidence_ref,note")

    def test_no_concession_default(self):
        ledger = recovery_mod.build_ledger(
            self.pack_path, self._confirm("conversation_id,status\n"))
        row = ledger["rows"][0]
        self.assertEqual(row["status"], "no_concession")
        self.assertEqual(row["realized_amount"], 0.0)


if __name__ == "__main__":
    unittest.main()
