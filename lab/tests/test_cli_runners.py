"""Integration tests for the real-harness runners (LAB-004).

Strategy: scripted fake CLIs emit the documented headless transcript shapes,
so the adapters' full path (candidate injection config → subprocess →
transcript parse → funnel events → engine run) is tested without the real
CLIs. Live-CLI validation remains a separate, pending step (disclosed in
every report the adapters produce).
"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.harness import get_runner
from agentmeasure_lab.rng import DetRng
from tests._support import TASK_SET_NAME, LabWorkspace, base_manifest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FAKE_CLAUDE = os.path.join(TESTS_DIR, "fake_claude.py")
FAKE_CODEX = os.path.join(TESTS_DIR, "fake_codex.py")

TASK = {"id": "search-e1", "instruction": "Find the homepage title of Northwind Robotics.",
        "category": "search", "tier": "easy"}

ASSIGNMENT = {
    "experiment_id": "runner-test",
    "assignment_id": "runner-test/h/task/r0001/variant",
    "harness_id": "h",
    "task_id": "task",
    "variant_id": "variant",
    "replicate": 1,
}


def _make_executable(path):
    os.chmod(path, 0o755)


def _run_episode(runner_id, cli_path, mode, levels=None):
    _make_executable(cli_path)
    os.environ["AM_FAKE_MODE"] = mode
    try:
        runner = get_runner(runner_id)
        runner.setup({"cli_path": cli_path, "timeout_seconds": 5, "max_turns": 6})
        return runner.run_episode(TASK, levels or {}, ASSIGNMENT, DetRng(1, "ep"))
    finally:
        os.environ.pop("AM_FAKE_MODE", None)


def _events_by_type(events):
    return {e["event"]: e for e in events}


class TestClaudeCodeRunner(unittest.TestCase):
    def test_registered(self):
        runner = get_runner("claude-code")
        self.assertEqual(runner.runner_id, "claude-code")

    def test_subject_selected_success_consumed(self):
        events = _run_episode("claude-code", FAKE_CLAUDE, "subject",
                              levels={"description_clarity": "clear"})
        by_type = _events_by_type(events)
        self.assertEqual(by_type["reach"]["candidate_ids"][0], "your-search-api")
        self.assertTrue(by_type["choice"]["selected_subject"])
        self.assertEqual(by_type["attempt"]["outcome"], "success")
        self.assertEqual(by_type["operation_result"]["outcome"], "success")
        self.assertTrue(by_type["consumption"]["consumed"])
        self.assertEqual(by_type["consumption"]["signal"], "task_continuation")

    def test_competitor_selected_no_subject_ops(self):
        events = _run_episode("claude-code", FAKE_CLAUDE, "competitor")
        by_type = _events_by_type(events)
        self.assertEqual(by_type["choice"]["selected_id"], "web-search-pro")
        self.assertFalse(by_type["choice"]["selected_subject"])
        self.assertNotIn("attempt", by_type)
        self.assertNotIn("operation_result", by_type)

    def test_retry_then_success_is_one_operation(self):
        events = _run_episode("claude-code", FAKE_CLAUDE, "error")
        by_type = _events_by_type(events)
        self.assertEqual(by_type["operation_result"]["outcome"], "success")
        self.assertEqual(by_type["operation_result"]["attempts"], 2)

    def test_timeout_produces_honest_events(self):
        events = _run_episode("claude-code", FAKE_CLAUDE, "timeout")
        by_type = _events_by_type(events)
        self.assertEqual(by_type["choice"]["selected_id"], "none-of-the-candidates")
        self.assertNotIn("operation_result", by_type)

    def test_describe_discloses_status(self):
        runner = get_runner("claude-code")
        runner.setup({"cli_path": FAKE_CLAUDE})
        d = runner.describe()
        self.assertIn("live-CLI validation pending", d["disclosure"])
        self.assertIn("continuation proxy", json.dumps(d["observability"]))

    def test_missing_cli_is_clean_error(self):
        from agentmeasure_lab.rng import DetRng as R

        runner = get_runner("claude-code")
        runner.setup({"cli_path": "/nonexistent/claude", "timeout_seconds": 2})
        with self.assertRaises(ValueError) as ctx:
            runner.run_episode(TASK, {}, ASSIGNMENT, R(1))
        self.assertIn("CLI not found", str(ctx.exception))


class TestCodexRunner(unittest.TestCase):
    def test_subject_selected(self):
        events = _run_episode("codex", FAKE_CODEX, "subject")
        by_type = _events_by_type(events)
        self.assertTrue(by_type["choice"]["selected_subject"])
        self.assertEqual(by_type["operation_result"]["outcome"], "success")
        self.assertTrue(by_type["consumption"]["consumed"])

    def test_competitor_selected(self):
        events = _run_episode("codex", FAKE_CODEX, "competitor")
        by_type = _events_by_type(events)
        self.assertEqual(by_type["choice"]["selected_id"], "web-search-pro")

    def test_experimental_flag(self):
        runner = get_runner("codex")
        runner.setup({"cli_path": FAKE_CODEX})
        self.assertIn("EXPERIMENTAL", runner.describe()["disclosure"])


class TestRunnerThroughEngine(unittest.TestCase):
    """Full pipeline: engine run on the claude-code adapter with the fake CLI."""

    def test_engine_run_with_claude_adapter(self):
        ws = LabWorkspace()
        os.environ["AM_FAKE_MODE"] = "subject"
        try:
            manifest = base_manifest(experiment_id="e2e-claude", seed=1, replicates=2)
            manifest["analysis"]["min_sample_per_arm"] = 2
            manifest["harnesses"] = [{
                "id": "claude-code-fake",
                "runner": "claude-code",
                "config": {"cli_path": FAKE_CLAUDE, "timeout_seconds": 5, "max_turns": 6},
            }]
            report, run_dir, _ = ws.run(manifest)
            self.assertEqual(report["run"]["status"], "complete")
            # deterministic fake: both arms select subject 100% -> honest null
            v = next(v for v in report["variants"] if not v.get("baseline"))
            self.assertIn(v["verdict"], ("null_result", "undetermined"))
            events = [json.loads(l) for l in
                      open(os.path.join(run_dir, "events.jsonl"), encoding="utf-8").read().splitlines() if l.strip()]
            self.assertTrue(any(e["event"] == "choice" and e["selected_subject"] for e in events))
            # events conform to FMT-002
            from agentmeasure_lab.prereg import load_schema
            from agentmeasure_lab.schemas import validate

            schema = load_schema("funnel-event.schema.json")
            for ev in events:
                validate(ev, schema)
            # disclosure reaches the report
            self.assertIn("claude-code", json.dumps(report["run"]["harnesses"]))
        finally:
            os.environ.pop("AM_FAKE_MODE", None)
            ws.close()


if __name__ == "__main__":
    unittest.main()
