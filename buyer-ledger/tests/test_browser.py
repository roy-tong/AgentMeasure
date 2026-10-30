import json
import os
import tempfile
import unittest

from buyer_ledger import browser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(REPO, "recipes", "examples", "example.saas.usage-csv.json")


class RecipeValidationTest(unittest.TestCase):
    """INV-6：配方白名单不含任何文本输入动作；只读声明强制。"""

    def test_example_recipe_valid(self):
        recipe = browser.load_recipe(EXAMPLE)
        self.assertEqual(browser.validate_recipe(recipe), [])

    def test_fill_action_structurally_impossible(self):
        self.assertNotIn("fill", browser.ALLOWED_ACTIONS)
        self.assertNotIn("type", browser.ALLOWED_ACTIONS)
        recipe = browser.load_recipe(EXAMPLE)
        recipe["steps"].append({"action": "fill", "selector": "#password",
                                "value": "x"})
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("not in whitelist" in e for e in errors))

    def test_readonly_enforced(self):
        recipe = browser.load_recipe(EXAMPLE)
        recipe["readonly"] = False
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("readonly" in e for e in errors))

    def test_missing_logged_in_indicator_rejected(self):
        recipe = browser.load_recipe(EXAMPLE)
        del recipe["logged_in_indicator"]
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("logged_in_indicator" in e for e in errors))

    def test_non_https_rejected(self):
        recipe = browser.load_recipe(EXAMPLE)
        recipe["start_url"] = "http://portal.example.saas/billing"
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("HTTPS" in e for e in errors))

    def test_download_needs_save_as(self):
        recipe = browser.load_recipe(EXAMPLE)
        recipe["steps"][-1].pop("save_as")
        errors = browser.validate_recipe(recipe)
        self.assertTrue(any("save_as" in e for e in errors))


class DryRunTest(unittest.TestCase):
    def test_dry_run_plans_without_browser(self):
        recipe = browser.load_recipe(EXAMPLE)
        plan = browser.dry_run(recipe)
        self.assertEqual(plan["recipe_id"], recipe["recipe_id"])
        self.assertEqual(len(plan["steps"]), len(recipe["steps"]))
        self.assertEqual(plan["expected_downloads"], ["usage-{period}.csv"])
        self.assertIn("no browser was launched", plan["note"])


class AuditChainTest(unittest.TestCase):
    def test_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            trail = browser.AuditTrail("ex/test", "20261029T120000", root=tmp)
            trail.add(action="run_start", provider="example")
            trail.add(action="navigate", url="https://x.example/")
            trail.add(action="download", path="/tmp/a.csv", sha256="0" * 64)
            trail.add(action="run_end", final=True)
            ok, reason = browser.verify_chain(trail.entries())
            self.assertTrue(ok, reason)
            self.assertTrue(trail.final_hash)

    def test_tampered_chain_breaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            trail = browser.AuditTrail("ex/test", "20261029T120000", root=tmp)
            trail.add(action="navigate", url="https://x.example/")
            trail.add(action="download", path="/tmp/a.csv", sha256="0" * 64)
            entries = trail.entries()
            entries[1]["record"]["path"] = "/tmp/TAMPERED.csv"
            ok, reason = browser.verify_chain(entries)
            self.assertFalse(ok)
            self.assertIn("hash mismatch", reason)

    def test_genesis_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            trail = browser.AuditTrail("ex/test", "20261029T120000", root=tmp)
            trail.add(action="run_start", provider="example")
            entries = trail.entries()
            entries[0]["prev_hash"] = "FAKE"
            ok, reason = browser.verify_chain(entries)
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
