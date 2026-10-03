"""Native-export preparation tests: a skeleton, never a verdict.

`prepare` exists so a first-look engagement can start from the buyer's real
Intercom/Zendesk export (F1.1). Its contract with the concierge: columns the
export really carries pass through with provenance, judgement columns stay
empty for a human, native signal columns travel as hints, and nothing that
could be mistaken for a finding is produced.
"""
import os
import tempfile
import unittest

from _support import fixture

from am_healthcheck import prepare as prepare_mod
from am_healthcheck.vendors import load_export

# A native-style Zendesk ticket export: documentation-confirmed headers, no
# judgement columns at all — exactly what F1.1 says arrives from a buyer.
ZENDESK_NATIVE = (
    "Ticket ID,Created at,Solved at,Assignee,Reopened,Reopened at,Subject\n"
    "77102,2026-08-01T09:00:00Z,2026-08-01T09:30:00Z,jane@buyer.com,yes,2026-08-02T09:00:00Z,refund not received\n"
    "77103,2026-08-01T10:00:00Z,2026-08-01T10:20:00Z,,no,,login broken\n"
)

# An Intercom-style dataset export (F1.1 memo: official attribute names).
INTERCOM_NATIVE = (
    "Conversation ID,Conversation created at,First contacted by,Has user reply,Closing note\n"
    "C-9001,2026-08-01T09:00:00Z,Fin AI Agent,No,done\n"
    "C-9002,2026-08-01T10:00:00Z,Teammate,Yes,done\n"
)


def write_csv(text):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                      encoding="utf-8", newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


class TestPrepare(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _prepare(self, text, vendor):
        path = write_csv(text)
        self.paths.append(path)
        return prepare_mod.prepare(path, vendor)

    def test_zendesk_headers_map_to_canonical(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        prov = prepared["provenance"]
        self.assertEqual(prov["conversation_id"], "exported:Ticket ID")
        self.assertEqual(prov["opened_at"], "exported:Created at")
        self.assertEqual(prov["closed_at"], "exported:Solved at")

    def test_intercom_created_at_alias_maps(self):
        prepared = self._prepare(INTERCOM_NATIVE, "intercom")
        self.assertEqual(prepared["provenance"]["opened_at"],
                         "exported:Conversation created at")
        self.assertEqual(prepared["provenance"]["conversation_id"],
                         "exported:Conversation ID")

    def test_judgement_columns_stay_empty(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        # Native "Reopened"/"Reopened at" map directly (registry aliases);
        # the columns that need a human stay empty.
        for col in ("human_agent_participated", "issue_addressed",
                    "vendor_billed"):
            self.assertIsNone(prepared["records"][0][col], col)
            self.assertEqual(prepared["provenance"][col], "needs_human")
        self.assertEqual(prepared["provenance"]["customer_recontacted_within_window"],
                         "exported:Reopened")
        self.assertEqual(prepared["provenance"]["customer_recontacted_at"],
                         "exported:Reopened at")

    def test_hints_carry_native_signals(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        row = prepared["records"][0]
        self.assertIn("assignee=jane@buyer.com",
                      row["hint_human_agent_participated"])
        # Reopened/Reopened at map directly, so they are columns, not hints.
        self.assertNotIn("hint_customer_recontacted_within_window", row)
        self.assertNotIn("hint_customer_recontacted_at", row)

    def test_hint_is_not_written_when_export_has_the_real_column(self):
        text = ("Ticket ID,human_agent_participated,Assignee\n"
                "77102,yes,jane@buyer.com\n")
        prepared = self._prepare(text, "zendesk")
        self.assertNotIn("hint_human_agent_participated", prepared["records"][0])
        self.assertEqual(prepared["records"][0]["human_agent_participated"], "yes")

    def test_no_hint_leak_for_unknown_vendor_columns(self):
        prepared = self._prepare("Ticket ID,Weather\n77102,sunny\n", "zendesk")
        self.assertIn("Weather", prepared["unmapped_native_columns"])
        for rec in prepared["records"]:
            for key in rec:
                self.assertFalse(key.startswith("hint_"))

    def test_needs_fill_counts_rows(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        self.assertEqual(prepared["needs_fill"]["vendor_billed"], 2)
        self.assertEqual(prepared["needs_fill"]["issue_addressed"], 2)
        self.assertNotIn("customer_recontacted_within_window", prepared["needs_fill"])

    def test_columns_missing_lists_required_only(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        self.assertEqual(sorted(prepared["columns_missing"]),
                         ["human_agent_participated",
                          "issue_addressed",
                          "vendor_billed"])

    def test_write_then_load_round_trips(self):
        # The prepared file must be readable by the recount loader: every
        # required column present (values possibly empty -> cannot_settle,
        # never a mapping failure).
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        out = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8", newline="")
        out.close()
        self.paths.append(out.name)
        prepare_mod.write_prepared(prepared, out.name)
        export = load_export(out.name)
        self.assertEqual(export["columns_missing"], [])
        self.assertEqual(len(export["records"]), 2)
        first = export["records"][0]
        self.assertEqual(first["conversation_id"], "77102")
        # vendor_billed had no source column: written empty, read as absent,
        # so a recount of the untouched skeleton cannot settle — by design.
        self.assertFalse(first["vendor_billed"])

    def test_report_prints_next_steps_and_vendor_note(self):
        prepared = self._prepare(ZENDESK_NATIVE, "zendesk")
        report = prepare_mod.prepare_report(prepared)
        self.assertIn("no verdicts produced", report)
        self.assertIn("NEEDS HUMAN", report)
        self.assertIn("--inspect", report)
        self.assertIn("Explore datasets", report)  # registry note travels


class TestPrepareCLI(unittest.TestCase):
    def setUp(self):
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def _run(self, *argv):
        import contextlib
        import io
        from am_healthcheck.cli import main
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_inspect_writes_nothing(self):
        src = write_csv(ZENDESK_NATIVE)
        self.paths.append(src)
        out = os.path.join(tempfile.mkdtemp(), "prepared.csv")
        self.addCleanup(
            lambda: os.path.exists(out) and os.unlink(out))
        rc, stdout, _ = self._run("prepare", "--export", src,
                                  "--vendor", "zendesk",
                                  "--out", out, "--inspect")
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(out))
        self.assertIn("no verdicts produced", stdout)

    def test_prepare_writes_skeleton_and_exits_zero(self):
        src = write_csv(INTERCOM_NATIVE)
        self.paths.append(src)
        out = os.path.join(tempfile.mkdtemp(), "prepared.csv")
        self.addCleanup(
            lambda: os.path.exists(out) and os.unlink(out))
        rc, stdout, _ = self._run("prepare", "--export", src,
                                  "--vendor", "intercom", "--out", out)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(out))
        with open(out, encoding="utf-8") as fh:
            header = fh.readline().strip()
        self.assertTrue(header.startswith(
            "conversation_id,opened_at,closed_at,human_agent_participated,"
            "issue_addressed,customer_recontacted_within_window,vendor_billed"))
        self.assertIn("prov_", header)

    def test_unknown_vendor_is_usage_error(self):
        src = write_csv(ZENDESK_NATIVE)
        self.paths.append(src)
        rc, _, stderr = self._run("prepare", "--export", src,
                                  "--vendor", "nope")
        self.assertEqual(rc, 2)
        self.assertIn("unknown vendor", stderr)


class TestOptionalColumn(unittest.TestCase):
    def test_recontact_timestamp_maps_when_present(self):
        text = ("conversation_id,human_agent_participated,issue_addressed,"
                "customer_recontacted_within_window,vendor_billed,"
                "customer_recontacted_at\n"
                "C1,no,yes,no,yes,2026-08-02T09:00:00Z\n")
        path = write_csv(text)
        self.paths = [path]
        export = load_export(path)
        self.assertEqual(export["columns_missing"], [])
        self.assertEqual(export["records"][0]["customer_recontacted_at"],
                         "2026-08-02T09:00:00Z")

    def test_recontact_timestamp_absent_is_fine(self):
        path = fixture("vendor-export-intercom.csv")
        export = load_export(path)
        self.assertEqual(export["columns_missing"], [])
        self.assertNotIn("customer_recontacted_at", export["records"][0])


if __name__ == "__main__":
    unittest.main()
