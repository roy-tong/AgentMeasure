import copy
import json
import os
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

from buyer_ledger import browser, ingest, parsing
from buyer_ledger.llm import LLMClient, extract_json
from buyer_ledger.model import ChargeLine, LedgerError, PricingPolicy, SourceDocument, UsageEvent
from buyer_ledger.reconcile import (
    CLS_ESTIMATE_INCOMPLETE, CLS_MATCHED, CLS_REVIEW_REQUIRED, CLS_UNPRICED_USAGE,
    apply_pricing, reconcile,
)
from buyer_ledger.store import LedgerStore


class LedgerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LedgerStore(os.path.join(self.tmp.name, "ledger.db"))
        self.fixture_seq = 0

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def doc(self, h, tier="bill_fact", provider="p", account="", period="2026-10"):
        doc = SourceDocument(content_hash=h * 64, provider=provider, tier=tier,
                             account_ref=account, period=period,
                             doc_type="usage_export" if tier == "platform_usage" else "bill")
        self.store.put_document(doc)
        return doc

    def bill(self, doc, amount="100", currency="USD", status="verified", **kw):
        line = ChargeLine(document_id=doc.id, provider=doc.provider, currency=currency,
                          amount=amount, period=kw.pop("period", "2026-10"),
                          review_status=status, **kw)
        self.store.put_charge_line(line)
        return line

    def usage(self, doc, quantity="100", unit="operation", charge=None,
              currency="USD", status="verified", **kw):
        period = kw.pop("period", "2026-10")
        initial_currency = kw.pop("currency", "") if charge is None else ""
        if charge is not None:
            self.fixture_seq += 1
            kw["capability"] = "fixture-%d" % self.fixture_seq
        event = UsageEvent(document_id=doc.id, provider=doc.provider,
                           billable_unit=unit, quantity=quantity, period=period,
                           currency=initial_currency, review_status=status, **kw)
        self.store.put_usage_event(event)
        if charge is not None:
            rate = Decimal(charge) / Decimal(quantity)
            self.store.put_policy(PricingPolicy(
                policy_id=event.capability, version="1", provider=doc.provider,
                model="per_unit", unit_price=str(rate), capability=event.capability,
                currency=currency))
            apply_pricing(self.store, doc.provider, period)
        return event


class ReconciliationSafetyTest(LedgerCase):
    def test_currencies_never_sum_or_false_match(self):
        usd = self.doc("a")
        eur = self.doc("b")
        usage_doc = self.doc("u", "platform_usage")
        self.bill(usd, "100", "USD")
        self.bill(eur, "100", "EUR")
        self.usage(usage_doc, "1", charge="100", currency="USD")
        results = reconcile(self.store, "2026-10")
        self.assertEqual(len(results), 2)
        by_currency = {r["currency"]: r for r in results}
        self.assertEqual(by_currency["USD"]["bill_total"], "100")
        self.assertEqual(by_currency["USD"]["variance_class"], CLS_MATCHED)
        self.assertEqual(by_currency["EUR"]["bill_total"], "100")
        self.assertIsNone(by_currency["EUR"]["variance"])

    def test_accounts_are_independent(self):
        for account, h, amount in (("A", "a", "100"), ("B", "b", "50")):
            bill_doc = self.doc(h, account=account)
            usage_doc = self.doc("u" if account == "A" else "v", "platform_usage", account=account)
            self.bill(bill_doc, amount)
            self.usage(usage_doc, "1", charge=amount)
        results = reconcile(self.store, "2026-10")
        self.assertEqual({r["account_ref"] for r in results}, {"A", "B"})
        self.assertEqual({r["bill_total"] for r in results}, {"100", "50"})

    def test_partial_recount_has_subtotal_but_no_variance(self):
        self.bill(self.doc("a"), "100")
        usage_doc = self.doc("u", "platform_usage")
        self.usage(usage_doc, "1", charge="100")
        self.usage(usage_doc, "999", unit="token", currency="")
        result = reconcile(self.store, "2026-10")[0]
        self.assertEqual(result["variance_class"], CLS_ESTIMATE_INCOMPLETE)
        self.assertEqual(result["recount_total"], "100")
        self.assertIsNone(result["variance"])
        self.assertFalse(result["recount_complete"])

    def test_pending_records_block_economic_verdict(self):
        self.bill(self.doc("a"), "999", status="pending")
        self.usage(self.doc("u", "platform_usage"), "1", charge="999")
        result = reconcile(self.store, "2026-10")[0]
        self.assertEqual(result["variance_class"], CLS_REVIEW_REQUIRED)
        self.assertIsNone(result["variance"])

    def test_unparsed_document_blocks_stale_matched_result(self):
        self.bill(self.doc("a"), "100")
        self.usage(self.doc("u", "platform_usage"), "1", charge="100")
        path = os.path.join(self.tmp.name, "new-bill.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Service,Amount,Currency\nNew charge,999,USD\n")
        imported = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10")
        self.assertEqual(imported["charge_lines"], 0)
        result = reconcile(self.store, "2026-10")[0]
        self.assertEqual(result["variance_class"], CLS_REVIEW_REQUIRED)
        self.assertIsNone(result["variance"])
        self.assertEqual(result["detail"]["unparsed_documents"][0]["id"],
                         imported["document_id"])

    def test_unpriced_quantities_stay_separate_by_unit(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "2", unit="operation", currency="")
        self.usage(doc, "1000", unit="token", currency="")
        result = reconcile(self.store, "2026-10")[0]
        self.assertEqual(result["variance_class"], CLS_UNPRICED_USAGE)
        self.assertIsNone(result["detail"]["unpriced_usage_qty"])
        self.assertEqual(result["detail"]["unpriced_usage_by_unit"],
                         {"operation": "2", "token": "1000"})

    def test_empty_period_is_rejected(self):
        with self.assertRaises(LedgerError):
            reconcile(self.store, "")

    def test_rerun_replaces_stale_period_snapshot(self):
        old_doc = self.doc("a")
        original = self.bill(old_doc, "100")
        reconcile(self.store, "2026-10")
        new_doc = self.doc("b", period="2026-11")
        self.bill(new_doc, "110", period="2026-11", revision=2,
                  supersedes=original.id)
        self.assertEqual(reconcile(self.store, "2026-10"), [])
        self.assertEqual(self.store.list_reconciliations("2026-10"), [])


class PricingSafetyTest(LedgerCase):
    def test_only_valid_policy_applies(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "100", occurred_at="2026-10-15")
        self.store.put_policy(PricingPolicy(
            policy_id="current", version="1", provider="p", model="per_unit",
            unit_price="0.05", valid_from="2026-01-01", valid_until="2026-12-31"))
        self.store.put_policy(PricingPolicy(
            policy_id="future", version="1", provider="p", model="per_unit",
            unit_price="0.50", valid_from="2027-01-01"))
        apply_pricing(self.store, "p", "2026-10")
        event = self.store.effective_usage_events(period="2026-10")[0]
        self.assertEqual(event["computed_charge"], "5.00")
        self.assertEqual(event["pricing_policy_id"], "current@1")

    def test_stale_estimate_is_withdrawn_when_policy_becomes_ambiguous(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "100")
        self.store.put_policy(PricingPolicy(
            policy_id="one", version="1", provider="p", model="per_unit",
            unit_price="0.05"))
        apply_pricing(self.store, "p", "2026-10")
        self.store.put_policy(PricingPolicy(
            policy_id="two", version="1", provider="p", model="per_unit",
            unit_price="0.50"))
        summary = apply_pricing(self.store, "p", "2026-10")
        event = self.store.effective_usage_events(period="2026-10")[0]
        self.assertEqual(summary["withdrawn_stale_estimates"], 1)
        self.assertIsNone(event["computed_charge"])
        self.assertEqual(event["pricing_policy_id"], "")

    def test_free_quota_is_shared_across_period_events(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "800", occurred_at="2026-10-01")
        self.usage(doc, "800", occurred_at="2026-10-02")
        self.store.put_policy(PricingPolicy(
            policy_id="quota", version="1", provider="p", model="free_quota",
            free_quota="1000", unit_price="0.02"))
        apply_pricing(self.store, "p", "2026-10")
        events = self.store.effective_usage_events(period="2026-10")
        self.assertEqual(sum(Decimal(e["computed_charge"]) for e in events), Decimal("12.00"))

    def test_volume_tier_uses_period_total(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "6000", occurred_at="2026-10-01")
        self.usage(doc, "6000", occurred_at="2026-10-02")
        self.store.put_policy(PricingPolicy(
            policy_id="tier", version="1", provider="p", model="volume_tiered",
            tiers=[{"unit_from": 0, "unit_price": "0.05"},
                   {"unit_from": 10000, "unit_price": "0.03"}]))
        apply_pricing(self.store, "p", "2026-10")
        events = self.store.effective_usage_events(period="2026-10")
        self.assertEqual(sum(Decimal(e["computed_charge"]) for e in events), Decimal("360.00"))

    def test_flat_price_without_scope_does_not_duplicate_fixed_fee(self):
        doc = self.doc("u", "platform_usage")
        self.usage(doc, "1", occurred_at="2026-10-01")
        self.usage(doc, "1", occurred_at="2026-10-02")
        self.store.put_policy(PricingPolicy(
            policy_id="flat", version="1", provider="p", model="flat", unit_price="100"))
        summary = apply_pricing(self.store, "p", "2026-10")
        self.assertEqual(summary["updated"], 0)
        self.assertTrue(all(e["computed_charge"] is None
                            for e in self.store.effective_usage_events()))

    def test_policy_identity_is_provider_scoped_and_immutable(self):
        for provider in ("p", "other"):
            self.store.put_policy(PricingPolicy(
                policy_id="shared", version="1", provider=provider,
                model="per_unit", unit_price="0.05"))
        self.assertIsNotNone(self.store.find_policy("p"))
        self.assertIsNotNone(self.store.find_policy("other"))
        with self.assertRaises(LedgerError):
            self.store.put_policy(PricingPolicy(
                policy_id="shared", version="1", provider="p",
                model="per_unit", unit_price="0.10"))


class RevisionSafetyTest(LedgerCase):
    def test_revision_branch_is_refused(self):
        original = self.bill(self.doc("a"), "10", line_no=1)
        self.bill(self.doc("b"), "12", line_no=1, revision=2, supersedes=original.id)
        with self.assertRaises(LedgerError):
            self.bill(self.doc("c"), "13", line_no=1, revision=2,
                      supersedes=original.id)

    def test_cross_provider_revision_is_refused(self):
        original = self.bill(self.doc("a", provider="p"), "10")
        other = self.doc("b", provider="other")
        with self.assertRaises(LedgerError):
            self.store.put_charge_line(ChargeLine(
                document_id=other.id, provider="other", currency="USD", amount="12",
                period="2026-10", revision=2, supersedes=original.id))

    def test_reversal_cannot_exceed_target(self):
        original = self.bill(self.doc("a"), "10")
        with self.assertRaises(LedgerError):
            self.bill(self.doc("b"), "-11", reversal_of=original.id)

    def test_superseded_charge_cannot_be_reversed(self):
        original = self.bill(self.doc("a"), "100")
        self.bill(self.doc("b"), "120", revision=2, supersedes=original.id)
        with self.assertRaises(LedgerError):
            self.bill(self.doc("c"), "-100", reversal_of=original.id)

    def test_computed_usage_must_come_from_pricing_pipeline(self):
        doc = self.doc("u", "platform_usage")
        event = UsageEvent(document_id=doc.id, provider="p", billable_unit="operation",
                           quantity="1", period="2026-10", computed_charge="5",
                           currency="USD", pricing_policy_id="unregistered@1")
        with self.assertRaises(LedgerError):
            self.store.put_usage_event(event)

    def test_duplicate_usage_reversal_is_refused(self):
        doc = self.doc("u", "platform_usage")
        original = self.usage(doc, "10", charge="5")
        stored = next(e for e in self.store.effective_usage_events() if e["id"] == original.id)
        for occurred_at in ("2026-10-02", "2026-10-03"):
            reversal = UsageEvent(
                document_id=doc.id, provider="p", billable_unit="operation",
                quantity="-10", period="2026-10", occurred_at=occurred_at,
                computed_charge="-5", currency="USD",
                pricing_policy_id=stored["pricing_policy_id"], reversal_of=original.id)
            if occurred_at.endswith("02"):
                self.store.put_usage_event(reversal)
            else:
                with self.assertRaises(LedgerError):
                    self.store.put_usage_event(reversal)
        events = self.store.effective_usage_events()
        self.assertEqual(sum(Decimal(e["quantity"]) for e in events), Decimal("0"))
        self.assertEqual(sum(Decimal(e["computed_charge"]) for e in events), Decimal("0"))

    def test_cross_account_usage_reversal_is_refused(self):
        doc_a = self.doc("u", "platform_usage", account="A")
        doc_b = self.doc("v", "platform_usage", account="B")
        original = self.usage(doc_a, "10", charge="5")
        stored = next(e for e in self.store.effective_usage_events() if e["id"] == original.id)
        reversal = UsageEvent(
            document_id=doc_b.id, provider="p", billable_unit="operation",
            quantity="-10", period="2026-10", computed_charge="-5", currency="USD",
            pricing_policy_id=stored["pricing_policy_id"], reversal_of=original.id)
        with self.assertRaises(LedgerError):
            self.store.put_usage_event(reversal)

    def test_usage_identity_includes_account_and_agent(self):
        doc = self.doc("u", "platform_usage")
        first = self.usage(doc, "10", account_ref="A", agent="one")
        second = self.usage(doc, "10", account_ref="B", agent="two")
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(self.store.effective_usage_events()), 2)


BILL_CSV = """Service,Amount,Currency\nA,10,USD\nB,20,USD\nTotal,30,\n"""
BILL_SPEC = {
    "tier": "bill_fact", "delimiter": ",", "header_row": 0,
    "skip_rows_containing": ["Total"],
    "columns": {"description": {"col": "Service"}, "amount": {"col": "Amount"},
                "currency": {"col": "Currency"}},
}


class FakeLLM(LLMClient):
    def __init__(self, spec):
        super().__init__(base_url="https://llm.example", api_key="k", model="m")
        self.spec = spec
        self.prompt = ""

    def chat(self, system, user, temperature=0.0, timeout=60):
        self.prompt = user
        return json.dumps(self.spec)


class ParsingSafetyTest(LedgerCase):
    def write_bill(self, text=BILL_CSV):
        path = os.path.join(self.tmp.name, "bill.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_parseable_import_requires_explicit_period(self):
        path = self.write_bill()
        with self.assertRaises(LedgerError):
            ingest.import_file(self.store, path, "p", "bill_fact")
        self.assertEqual(self.store.list_documents(), [])

    def test_same_content_can_be_imported_for_two_accounts(self):
        path = self.write_bill()
        fingerprint = parsing.format_fingerprint("bill.csv", BILL_CSV)
        self.store.put_parse_rule(fingerprint, BILL_SPEC, provider="p", doc_type="bill",
                                  tier="bill_fact", created_via="manual")
        first = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10",
                                   account_ref="A")
        second = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10",
                                    account_ref="B")
        self.assertNotEqual(first["document_id"], second["document_id"])
        self.assertEqual(len(self.store.list_documents()), 2)
        self.assertEqual(len(self.store.effective_charge_lines()), 4)

    def test_financial_constants_are_refused(self):
        spec = copy.deepcopy(BILL_SPEC)
        spec["columns"]["amount"] = {"const": "999"}
        self.assertTrue(any("source column" in e for e in parsing.validate_spec(spec)))

    def test_agent_rule_needs_explicit_approval_and_sends_no_rows(self):
        path = self.write_bill()
        llm = FakeLLM(BILL_SPEC)
        result = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10",
                                    use_agent_if_new=True, llm_client=llm)
        self.assertTrue(result["review_required"])
        self.assertEqual(result["charge_lines"], 0)
        self.assertNotIn("A,10,USD", llm.prompt)
        fingerprint = result["fingerprint"]
        self.store.approve_parse_rule(fingerprint, provider="p", doc_type="bill",
                                      tier="bill_fact")
        imported = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10")
        self.assertEqual(imported["charge_lines"], 2)
        self.assertTrue(all(r["review_status"] == "verified"
                            for r in self.store.effective_charge_lines()))

    def test_import_rolls_back_all_rows_on_failure(self):
        path = self.write_bill()
        fingerprint = parsing.format_fingerprint("bill.csv", BILL_CSV)
        self.store.put_parse_rule(fingerprint, BILL_SPEC, provider="p", doc_type="bill",
                                  tier="bill_fact", created_via="manual")
        original = self.store.put_charge_line
        calls = {"n": 0}

        def fail_second(row, commit=True):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected failure")
            return original(row, commit=commit)

        self.store.put_charge_line = fail_second
        with self.assertRaises(RuntimeError):
            ingest.import_file(self.store, path, "p", "bill_fact", "2026-10")
        documents = self.store.list_documents()
        self.assertEqual(len(documents), 1)
        self.assertEqual(self.store.count_rows_for_document(documents[0]["id"]), 0)
        self.store.put_charge_line = original
        result = ingest.import_file(self.store, path, "p", "bill_fact", "2026-10")
        self.assertEqual(result["charge_lines"], 2)

    def test_integer_total_mismatch_is_not_ignored(self):
        doc = SourceDocument(content_hash="f" * 64, provider="p", tier="bill_fact",
                             period="2026-10")
        result = parsing.apply_spec("bill.csv", BILL_CSV.replace("Total,30", "Total,999"),
                                    BILL_SPEC, doc, "p", "2026-10", review_status="verified")
        self.assertFalse(result["constraint"]["match"])
        self.assertTrue(all(line.review_status == "pending" for line in result["charge_lines"]))

    def test_billable_unit_column_is_not_discarded(self):
        text = "Qty,Unit\n5,token\n"
        spec = {"tier": "platform_usage", "columns": {
            "quantity": {"col": "Qty"}, "billable_unit": {"col": "Unit"}}}
        doc = SourceDocument(content_hash="u" * 64, provider="p", tier="platform_usage",
                             period="2026-10")
        result = parsing.apply_spec("u.csv", text, spec, doc, "p", "2026-10")
        self.assertEqual(result["usage_events"][0].billable_unit, "token")

    def test_ambiguous_single_comma_number_is_refused(self):
        with self.assertRaises(LedgerError):
            parsing.clean_amount("1,234")
        self.assertEqual(parsing.clean_amount("1,234.56"), "1234.56")
        self.assertEqual(parsing.clean_amount("1.234,56"), "1234.56")

    def test_json_decoder_allows_braces_inside_strings(self):
        self.assertEqual(extract_json('{"columns":{"x":{"const":"}"}}}')["columns"]["x"]["const"], "}")


class BrowserSafetyTest(unittest.TestCase):
    def setUp(self):
        root = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "recipes", "examples", "example.saas.usage-csv.json")
        self.recipe = browser.load_recipe(root)

    def test_navigation_and_paths_are_constrained(self):
        recipe = copy.deepcopy(self.recipe)
        recipe["steps"].append({"action": "navigate",
                                "url": "http://169.254.169.254/latest/meta-data"})
        recipe["steps"].append({"action": "download", "link_selector": "a",
                                "save_as": "../../outside.csv"})
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("HTTPS" in e or "allowed_hosts" in e for e in errors))
        self.assertTrue(any("safe basename" in e for e in errors))

    def test_empty_chain_is_not_verified(self):
        self.assertFalse(browser.verify_chain([])[0])

    def test_query_string_cannot_fake_login(self):
        class Page:
            url = "https://evil.example/?next=portal.example.saas/billing"
        self.assertFalse(browser._logged_in(Page(), self.recipe["logged_in_indicator"]))

    def _run_with_fake_page(self, recipe, page):
        class Context:
            def __init__(self):
                self.pages = [page]
            def route(self, pattern, handler):
                self.guard = handler
            def close(self):
                pass
        context = Context()
        class Chromium:
            def launch_persistent_context(self, *args, **kwargs):
                return context
        class Playwright:
            chromium = Chromium()
        class Manager:
            def __enter__(self):
                return Playwright()
            def __exit__(self, *args):
                return False
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(browser, "_require_playwright", return_value=Manager), \
                mock.patch.object(browser, "DEFAULT_PROFILE_ROOT", tmp), \
                mock.patch.object(browser, "DEFAULT_AUDIT_ROOT", tmp):
            return browser.run_recipe(recipe, period="2026-10")

    def test_redirect_is_checked_before_click(self):
        recipe = copy.deepcopy(self.recipe)
        recipe["steps"] = [{"action": "wait_for", "selector": "table"},
                           {"action": "click", "selector": "#delete-account"}]
        class Page:
            def __init__(self):
                self.url = recipe["start_url"]
                self.clicks = []
            def goto(self, url, **kwargs):
                self.url = url
            def content(self):
                return ""
            def wait_for_selector(self, selector, **kwargs):
                self.url = "https://evil.example/phish"
            def click(self, selector, **kwargs):
                self.clicks.append((self.url, selector))
        page = Page()
        with self.assertRaises(browser.Handoff):
            self._run_with_fake_page(recipe, page)
        self.assertEqual(page.clicks, [])

    def test_cross_origin_download_is_refused_before_save_or_ingest(self):
        recipe = copy.deepcopy(self.recipe)
        recipe["steps"] = [{"action": "download", "link_selector": "a",
                            "save_as": "usage.csv"}]
        class Download:
            url = "https://evil.example/usage.csv"
            saved = False
            def save_as(self, path):
                self.saved = True
        download = Download()
        class DownloadContext:
            value = download
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        class Page:
            def __init__(self):
                self.url = recipe["start_url"]
            def goto(self, url, **kwargs):
                self.url = url
            def content(self):
                return ""
            def click(self, selector, **kwargs):
                pass
            def expect_download(self, **kwargs):
                return DownloadContext()
        with self.assertRaises(browser.Handoff):
            self._run_with_fake_page(recipe, Page())
        self.assertFalse(download.saved)


if __name__ == "__main__":
    unittest.main()
