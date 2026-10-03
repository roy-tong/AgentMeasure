"""Console tests — the user-facing integrated page.

The console is the product surface a normal person opens. The tests pin
three things: the flow renders from real verification documents in business
order; draft/developer markers stay banned from visible copy (the guard
actually fires); and it renders without recomputing while escaping hostile
values.
"""
import json
import os
import unittest

from _support import FIXTURES_DIR, REPO_ROOT

from am_healthcheck import console as console_mod
from am_healthcheck import ledger as ledger_mod
from am_healthcheck import commerce as cm
from am_healthcheck import pnl as pnl_mod
from am_healthcheck import audit as audit_mod
from am_healthcheck import policy as policy_mod

EXPORT = os.path.join(FIXTURES_DIR, "vendor-export-intercom.csv")
CFIX = os.path.join(FIXTURES_DIR, "commerce")


def build_ledger():
    contract = tmpfile(".json", json.dumps({"reopen_window_hours": 72}))
    billing = tmpfile(".csv", "conversation_id,amount\nC-1001,0.99\n")
    confirmations = tmpfile(".csv", "conversation_id,status,amount\n"
                                    "C-1003,credited,0.99\n")
    paths = [contract, billing, confirmations]
    doc = ledger_mod.build_ledger_document(
        EXPORT, "intercom", contract_path=contract, ledger_path=billing,
        confirmations_path=confirmations)
    return doc, paths


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = __import__("tempfile").NamedTemporaryFile(
        mode, suffix=suffix, delete=False, encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


class TestBillingFlow(unittest.TestCase):
    def setUp(self):
        self.doc, self.paths = build_ledger()
        for p in self.paths:
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))

    def _page(self, **kwargs):
        return console_mod.build_console(
            meta={"title": "Bill verification", "vendor": "Intercom Fin",
                  "period": "August 2026", "buyer": "ACME CX"},
            ledger=self.doc, **kwargs)

    def test_all_six_steps_render_in_order(self):
        page = self._page()
        for anchor in ("your-data", "recount", "your-standard", "money",
                       "evidence-pack", "recovery"):
            self.assertIn('id="%s"' % anchor, page)
        self.assertLess(page.index("The recount"), page.index("Your own "
                                                              "service standard"))
        self.assertLess(page.index("Your own service standard"),
                        page.index("Does the money match?"))

    def test_copy_is_user_language(self):
        page = self._page()
        self.assertIn("Charged, but their own rules say they", page)
        self.assertIn("Continue:", page)
        self.assertIn("computed locally, nothing uploaded", page)

    def test_numbers_come_from_the_document(self):
        page = self._page()
        over = self.doc["tier1"]["counts"]["billed_but_not_billable"]
        self.assertIn(">%d<" % over, page)
        self.assertIn("%.2f" % self.doc["tier1"]["variance"], page)

    def test_optional_steps_only_when_documents_exist(self):
        ledger_only = self._page()
        # without commerce docs there is no channel part
        self.assertNotIn("Offer guardrails", ledger_only)
        self.assertNotIn("Your agent channel", ledger_only)
        # the money step exists because the ledger carries a crosscheck
        self.assertIn('id="money"', ledger_only)

    def test_draft_markers_banned(self):
        page = self._page()
        for marker in console_mod.BANNED_MARKERS:
            self.assertNotIn(marker, page)

    def test_marker_guard_actually_fires(self):
        # A hostile "vendor name" carrying a draft marker must fail the
        # build, not ship to a user.
        doc = json.loads(json.dumps(self.doc))
        doc["vendor"]["name"] = "Intercom Tier 1"
        with self.assertRaises(ValueError):
            console_mod.build_console(meta={"title": "x"}, ledger=doc)

    def test_hostile_buyer_escaped(self):
        doc = json.loads(json.dumps(self.doc))
        page = console_mod.build_console(
            meta={"title": "Bill verification",
                  "buyer": "<script>alert(1)</script>"},
            ledger=doc)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)


class TestChannelFlow(unittest.TestCase):
    def setUp(self):
        schema = json.loads(open(os.path.join(
            REPO_ROOT, "schemas", "commerce-profile.schema.json"),
            encoding="utf-8").read())
        events = cm.load_events(os.path.join(CFIX, "agent-events.jsonl"),
                                schema)
        orders = cm.load_orders(os.path.join(CFIX, "merchant-orders.csv"))
        payments = cm.load_payments(os.path.join(CFIX, "merchant-payments.csv"))
        self.receipt = cm.reconcile(events, orders, payments, "1.0.0")
        self.margin = pnl_mod.contribution_margin([
            {"order_id": "V-1", "amount": 100.0, "status": "confirmed",
             "channel": "organic", "campaign_id": "", "line": 2}], [
            {"category": "coupon", "amount": 10.0, "order_id": "", "line": 2}],
            "2026-09")
        self.audit = audit_mod.audit_channel(
            {"agent_traffic": 5000, "brand_category_intent_share": 0.08,
             "paid_inventory_depth": 80, "commercial_task_frequency": 400,
             "conversion_rate": 0.01, "contribution_margin_pct": 0.02},
            {m: {"threshold": t} for m, t in [
                ("agent_traffic", 1000), ("conversion_rate", 0.03)]})
        self.policy_path = tmpfile(".json", json.dumps({
            "schema": "agentmeasure.commerce/decision-policy",
            "policy_version": "2026.10",
            "risk_policy_ref": "agentic-ops/action-risk-policy#v3",
            "rules": [{"rule_id": "R-1", "action_type": "coupon",
                       "tier": "auto", "max_value": 10.0}]}))
        self.addCleanup(lambda: os.path.exists(self.policy_path)
                        and os.unlink(self.policy_path))
        self.policy = policy_mod.load_policy(self.policy_path)

    def test_channel_part_renders_all_steps(self):
        page = console_mod.build_console(
            meta={"title": "Operations review"},
            receipt=self.receipt, margin=self.margin,
            channel_audit=self.audit,
            decisions=policy_mod.audit_executions(self.policy, [
                {"execution_id": "E-1", "action_type": "coupon", "value": 5.0}]))
        for anchor in ("receipt", "margin", "readiness", "guardrails"):
            self.assertIn('id="%s"' % anchor, page)
        self.assertIn("Part two", page)
        # plain-language materiality line from the receipt
        self.assertIn("The verified number is", page)

    def test_channel_without_decisions_hides_guardrails(self):
        page = console_mod.build_console(
            meta={"title": "Operations review"},
            receipt=self.receipt)
        self.assertNotIn("Offer guardrails", page)


class TestWriteConsole(unittest.TestCase):
    def test_write_round_trips(self):
        doc, paths = build_ledger()
        for p in paths:
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        page = console_mod.build_console(meta={"title": "t"}, ledger=doc)
        out = tmpfile(".html", "")
        self.addCleanup(lambda: os.path.exists(out) and os.unlink(out))
        written = console_mod.write_console(page, out)
        with open(written, encoding="utf-8") as fh:
            self.assertIn("AgentMeasure", fh.read())


if __name__ == "__main__":
    unittest.main()
