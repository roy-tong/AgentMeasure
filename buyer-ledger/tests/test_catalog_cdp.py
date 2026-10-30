import copy
import json
import os
import tempfile
import unittest
from unittest import mock

from buyer_ledger import browser, catalog
from buyer_ledger.report import render_report


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog.load_catalog()

    def test_catalog_has_both_regions_and_roles(self):
        self.assertGreaterEqual(len(self.catalog["providers"]), 20)
        providers = self.catalog["providers"]
        self.assertEqual({p["region"] for p in providers}, {"cn", "global"})
        self.assertTrue(all(set(p["roles"]) == {"buyer", "seller"} for p in providers))

    def test_every_provider_has_bill_and_audit_dimensions(self):
        for provider in self.catalog["providers"]:
            for field in ("billing_models", "metering_units", "bill_sources",
                          "audit_capabilities"):
                self.assertTrue(provider[field], "%s missing %s" % (provider["id"], field))
            self.assertEqual(provider["live_bill_status"], "not_validated")

    def test_coverage_recognizes_aliases_and_unknowns(self):
        result = catalog.coverage(["Claude API", "扣子", "unmapped.vendor"])
        self.assertEqual(result["known_count"], 2)
        self.assertEqual(result["unknown"], ["unmapped.vendor"])
        self.assertEqual({r["id"] for r in result["known"]}, {"anthropic", "coze"})

    def test_summary_does_not_claim_live_validation(self):
        summary = catalog.support_summary(self.catalog)
        self.assertEqual(summary["live_bill_validated"], 0)
        self.assertEqual(summary["by_role"]["buyer"], summary["total"])
        self.assertEqual(summary["by_role"]["seller"], summary["total"])

    def test_duplicate_alias_is_rejected(self):
        broken = copy.deepcopy(self.catalog)
        broken["providers"][0]["aliases"].append(broken["providers"][1]["name"])
        errors = catalog.validate_catalog(broken)
        self.assertTrue(any("maps to both" in e for e in errors))


class _FakePage:
    def __init__(self):
        self.url = "https://portal.example.saas/billing/usage"
        self.closed = False

    def goto(self, url, **kwargs):
        self.url = url

    def content(self):
        return ""

    def wait_for_selector(self, selector, **kwargs):
        pass

    def click(self, selector, **kwargs):
        pass

    def close(self):
        self.closed = True


class _FakeContext:
    def __init__(self, page):
        self.pages = []
        self._page = page
        self.routed = False

    def route(self, pattern, handler):
        self.routed = True

    def new_page(self):
        self.pages.append(self._page)
        return self._page


class _FakeBrowser:
    def __init__(self, context):
        self.contexts = [context]


class CdpTransportTest(unittest.TestCase):
    def setUp(self):
        root = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "recipes", "examples", "example.saas.usage-csv.json")
        self.recipe = browser.load_recipe(root)
        self.recipe["steps"] = [{"action": "wait_for", "selector": "table.usage-table"}]

    def _manager(self, page, calls):
        class Chromium:
            def connect_over_cdp(self, endpoint):
                calls.append(endpoint)
                return _FakeBrowser(_FakeContext(page))
        class Playwright:
            chromium = Chromium()
        class Manager:
            def __enter__(self):
                return Playwright()
            def __exit__(self, *args):
                return False
        return Manager

    def test_attaches_to_loopback_cdp_and_uses_audit_transport(self):
        page = _FakePage()
        calls = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(browser, "_require_playwright",
                                  return_value=self._manager(page, calls)), \
                mock.patch.object(browser, "DEFAULT_CDP_ROOT", tmp), \
                mock.patch.object(browser, "DEFAULT_AUDIT_ROOT", tmp):
            result = browser.run_recipe(
                self.recipe, period="2026-10", cdp_endpoint="http://127.0.0.1:9222")
        self.assertEqual(calls, ["http://127.0.0.1:9222"])
        self.assertEqual(result["transport"], "cdp")
        self.assertEqual(result["downloads"], [])

    def test_remote_cdp_and_non_http_are_rejected(self):
        for endpoint in ("https://evil.example:9222", "file:///tmp/chrome",
                         "http://127.0.0.1:9222?token=secret"):
            if "token" in endpoint:
                with self.assertRaises(browser.RecipeError):
                    browser._validate_cdp_endpoint(endpoint)
                continue
            with self.assertRaises(browser.RecipeError):
                browser._validate_cdp_endpoint(endpoint)


class PerspectiveReportTest(unittest.TestCase):
    def test_seller_view_and_tool_coverage_are_explicit(self):
        detail = {
            "bill_fact_lines": 1, "usage_events": 2, "priced_usage_events": 1,
            "unpriced_usage_qty": "100", "unpriced_usage_by_unit": {"token": "100"},
            "recount_complete": False, "review_pending_lines": 0,
            "undeterminable_lines": 0, "review_pending_usage": 0,
            "unlinked_charge_lines": [],
            "unlinked_usage_events": [{"id": "ue-1", "tool": "search",
                                       "quantity": "100", "unit": "token"}],
        }
        result = {
            "period": "2026-10", "provider": "coze", "account_ref": "A",
            "currency": "CNY", "bill_total": "10.00", "recount_total": "5.00",
            "variance": None, "variance_class": "estimate_incomplete",
            "recount_complete": False, "detail": detail,
        }
        coverage = catalog.coverage(["coze", "new.vendor"])
        markdown = render_report("2026-10", [result], documents_count=1,
                                 catalog_coverage=coverage, perspective="seller")
        self.assertIn("卖方计量完整性审查", markdown)
        self.assertIn("扣子 Coze", markdown)
        self.assertIn("new.vendor", markdown)
        self.assertIn("不得直接宣称为漏收收入", markdown)


if __name__ == "__main__":
    unittest.main()
