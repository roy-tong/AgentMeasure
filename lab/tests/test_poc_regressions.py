"""POC-driven regression tests (business acceptance, not just mechanics).

These encode the boss-level acceptance criteria from the business POC:
- fake growth must block the ship recommendation at the decision exit (P3);
- a within-noise consumption dip must NOT trigger the warning (credibility);
- a null must carry next-round sizing guidance (a boss must not read
  "null" as "no effect" and kill a valuable direction);
- a strictly dominated candidate must be called out;
- CLI failures speak one clean line, not a traceback;
- hand-written manifests resolve the shipped task set by filename fallback.
"""

import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests._support import LAB_DIR, LabWorkspace, base_manifest, load_json
from agentmeasure_lab.cli import main as cli_main


def _deep_merge_effects(base: dict, override: dict) -> None:
    """Deep-merge factor-effect tables (a shallow update would drop the
    description_clarity table the base config carries)."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge_effects(base[k], v)
        else:
            base[k] = v


def _manifest_with_variants(experiment_id, variants, harness_effects=None, guardrails=None, replicates=40, seed=20260822):
    m = base_manifest(experiment_id=experiment_id, variants=variants, seed=seed, replicates=replicates)
    m["factors"] = [
        {"name": "description_clarity", "levels": ["control", "clear"]},
        {"name": "output_verbosity", "levels": ["baseline", "verbose"]},
    ]
    _deep_merge_effects(m["harnesses"][0]["config"]["factor_effects"], harness_effects or {})
    m["guardrails"] = guardrails or [{"metric": "attempts_per_operation", "max": 2.0}]
    return m


class TestFakeGrowthBlocksShip(unittest.TestCase):
    def test_p3_fake_growth_rejects_ship(self):
        """The POC's central failure case: selection up, consumption down —
        the decision exit must say DO NOT SHIP, not adopt."""
        ws = LabWorkspace()
        try:
            manifest = _manifest_with_variants(
                "p3-fakegrowth",
                variants=[
                    {"id": "control", "baseline": True,
                     "levels": {"description_clarity": "control", "output_verbosity": "baseline"}},
                    {"id": "clear-verbose", "baseline": False,
                     "levels": {"description_clarity": "clear", "output_verbosity": "verbose"}},
                ],
                harness_effects={
                    "consumption_add": {"output_verbosity": {"baseline": 0.0, "verbose": -0.12}},
                },
                # loose guardrails on purpose: only the fake-growth check can catch this
                guardrails=[{"metric": "attempts_per_operation", "max": 2.0}],
            )
            report, run_dir, _ = ws.run(manifest)
            v = next(v for v in report["variants"] if v["variant_id"] == "clear-verbose")
            self.assertEqual(v["verdict"], "unverified_growth")
            self.assertTrue((v.get("fake_growth") or {}).get("flagged"))
            self.assertTrue(v["value"]["fake_growth_adjusted"])
            rec = next(d for d in report["decision"]["recommendations"] if d["variant_id"] == "clear-verbose")
            self.assertIn("do not ship", rec["recommended_action"])
            html = open(os.path.join(run_dir, "report.html"), encoding="utf-8").read()
            self.assertIn("For the decision maker", html)
            self.assertIn("假增长", html)
        finally:
            ws.close()

    def test_noise_dip_does_not_flag(self):
        """POC credibility finding: a -2pp within-noise consumption dip must
        not fire the warning."""
        ws = LabWorkspace()
        try:
            report, _, _ = ws.run(base_manifest(experiment_id="noise-check", seed=20260822))
            v = next(v for v in report["variants"] if v["variant_id"] == "clear")
            fg = v.get("fake_growth") or {}
            self.assertFalse(fg.get("flagged", False), f"noise dip must not flag: {fg}")
            self.assertEqual(v["verdict"], "adopt_candidate")
        finally:
            ws.close()


class TestNullPowerNoteAndDominance(unittest.TestCase):
    def test_null_carries_power_note(self):
        ws = LabWorkspace()
        try:
            manifest = base_manifest(
                experiment_id="null-power",
                seed=20260822,
                replicates=8,
                variants=[
                    {"id": "control", "baseline": True,
                     "levels": {"description_clarity": "control", "version_label": "a"}},
                    {"id": "label-b", "baseline": False,
                     "levels": {"description_clarity": "control", "version_label": "b"}},
                ],
            )
            manifest["analysis"]["min_sample_per_arm"] = 2  # null (not undetermined) at small n
            report, _, _ = ws.run(manifest)
            v = next(v for v in report["variants"] if v["variant_id"] == "label-b")
            cmp = v["primary_comparison"]
            self.assertEqual(cmp["verdict"], "null_result")
            self.assertIn("power_note", cmp)
            rec = next(d for d in report["decision"]["recommendations"] if d["variant_id"] == "label-b")
            self.assertIn("honest null", rec["recommended_action"])
        finally:
            ws.close()

    def test_dominance_rule(self):
        """Unit test of the dominance rule with deterministic report data.

        Conservative by design: fires only when B makes no more money
        (within 2%) at >2% higher cost with no better consumption; must NOT
        fire when B is genuinely more profitable.
        """
        from agentmeasure_lab.analysis import _annotate_dominance

        def variant(vid, diff, margin, cost, cons, sig="significant"):
            return {
                "variant_id": vid,
                "baseline": False,
                "verdict": "adopt_candidate" if sig == "significant" else sig,
                "primary_comparison": {"verdict": sig, "direction": "improvement", "difference": diff},
                "value": {"incremental_margin_per_month": margin},
                "metrics": {
                    "cost_units_per_operation": {"value": cost},
                    "consumption_rate": {"value": cons},
                },
            }

        # B: same money (within 2%), higher cost, lower consumption -> dominated
        vs = [variant("a", 0.05, 10000.0, 30.0, 0.60), variant("b", 0.05, 9900.0, 46.0, 0.48)]
        _annotate_dominance(vs)
        self.assertEqual(vs[1].get("dominated_by"), "a")

        # B genuinely more profitable -> NOT dominated
        vs = [variant("a", 0.05, 10000.0, 30.0, 0.60), variant("b", 0.06, 12000.0, 46.0, 0.55)]
        _annotate_dominance(vs)
        self.assertIsNone(vs[1].get("dominated_by"))

        # B cheaper -> not dominated
        vs = [variant("a", 0.05, 10000.0, 30.0, 0.60), variant("b", 0.05, 9900.0, 29.0, 0.48)]
        _annotate_dominance(vs)
        self.assertIsNone(vs[1].get("dominated_by"))

        # non-significant candidates are never in scope
        vs = [variant("a", 0.05, 10000.0, 30.0, 0.60),
              variant("b", 0.05, 9900.0, 46.0, 0.48, sig="null_result")]
        _annotate_dominance(vs)
        self.assertIsNone(vs[1].get("dominated_by"))


class TestCliFriendliness(unittest.TestCase):
    def _run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli_main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_missing_manifest_is_one_clean_line(self):
        code, _, err = self._run_cli("lab", "preregister", "does-not-exist.json")
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertIn("error:", err)
        self.assertIn("AM_LAB_DEBUG", err)

    def test_task_path_fallback_to_shipped_corpus(self):
        """A hand-written manifest whose task path only names the shipped
        corpus must still run (POC UX finding)."""
        import tempfile

        ws = LabWorkspace()
        try:
            with tempfile.TemporaryDirectory() as td:
                m = base_manifest(experiment_id="fallback-test")
                m["task_set"]["path"] = "tasks/search-retrieval-scrape.v1.json"  # does not exist relative to td
                mpath = os.path.join(td, "fallback.json")
                with open(mpath, "w", encoding="utf-8") as fh:
                    json.dump(m, fh)
                code, out, _ = self._run_cli("lab", "preregister", mpath)
                self.assertEqual(code, 0)
                self.assertIn("plan:", out)  # preview worked via fallback
                self.assertIn("power planning aid", out)
                code, out, _, = self._run_cli("lab", "run", os.path.splitext(mpath)[0] + ".prereg.json")
                self.assertEqual(code, 0)
        finally:
            ws.close()

    def test_preregister_preview_shows_scale_power_budget(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            m = base_manifest(experiment_id="preview-test")
            m["task_set"]["path"] = os.path.join(LAB_DIR, "tasks", "search-retrieval-scrape.v1.json")
            mpath = os.path.join(td, "preview.json")
            with open(mpath, "w", encoding="utf-8") as fh:
                json.dump(m, fh)
            code, out, _ = self._run_cli("lab", "preregister", mpath)
            self.assertEqual(code, 0)
            self.assertIn("per-arm n=", out)
            self.assertIn("+3pp", out)
            self.assertIn("budget caps", out)


if __name__ == "__main__":
    unittest.main()
