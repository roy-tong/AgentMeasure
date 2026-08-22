"""Deterministic synthetic harness ("mock") — the controlled agent model.

Purpose: make the whole pipeline (preregistration -> assignment -> funnel
capture -> honest statistics -> report) runnable offline, and give tests a
planted ground truth: factor effects below are simulation parameters, the
engine's job is to *recover or honestly fail to recover* them.

This is a simulation of agent choice behavior, NOT a claim about real
agents. Real harness adapters (claude-code, codex, ...) replace it via the
plugin interface; the funnel, statistics and report layers do not change.

Behavior model (all parameters overridable via manifest harness config):
- Selection: softmax over candidate attraction. Subject attraction shifts
  by the sum of factor effects on "attraction" for the variant's levels.
- Execution: attempts retry per attempt.retry_prob up to max_attempts;
  first-attempt success shifts by "attempt_success_add" effects and the
  task tier; one Operation succeeds iff any attempt succeeds.
- Consumption: Bernoulli shifted by "consumption_add" effects and tier;
  steps (and cost) shift by "steps_add" effects — the guardrail channel
  (echoing the literature: clearer descriptions can raise selection while
  inflating steps and hurting consumption).
- Factors absent from factor_effects have exactly zero effect: the honest
  null path.
"""

import math
from typing import Any, Dict, List

from . import funnel
from .harness import HarnessRunner


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


DEFAULT_CONFIG: Dict[str, Any] = {
    "candidates": [
        {"id": "your-search-api", "base_attraction": 0.100, "role": "subject"},
        {"id": "web-search-pro", "base_attraction": 0.120},
        {"id": "docs-search", "base_attraction": 0.100},
        {"id": "site-crawler", "base_attraction": 0.060},
    ],
    "softmax_temperature": 0.05,
    # channel -> factor -> level -> delta
    # Default amplitudes are deliberately REALISTIC (single-digit pp on
    # selection, echoing Hasan et al.'s +5.85pp-class effects), not
    # attention-grabbing: demos must not flatter the engine.
    "factor_effects": {
        "attraction": {
            "description_clarity": {"control": 0.0, "clear": 0.012},
            "output_verbosity": {"baseline": 0.0, "verbose": 0.002},
            "version_label": {"a": 0.0, "b": 0.0},
        },
        "attempt_success_add": {
            "output_verbosity": {"baseline": 0.0, "verbose": -0.02},
        },
        "consumption_add": {
            "output_verbosity": {"baseline": 0.0, "verbose": -0.06},
        },
        "steps_add": {
            "output_verbosity": {"baseline": 0.0, "verbose": 5},
        },
    },
    "attempt": {
        "success_base": 0.80,
        "tier_add": {"easy": 0.04, "medium": -0.04, "hard": -0.10},
        "retry_prob": 0.30,
        "max_attempts": 3,
    },
    "steps": {"base": 8, "tier_add": {"easy": 0, "medium": 3, "hard": 6}, "jitter": 3},
    "consumption": {"base": 0.62, "tier_add": {"easy": 0.03, "medium": -0.04, "hard": -0.10}},
}


def _channel_delta(config: Dict[str, Any], channel: str, variant_levels: Dict[str, str]) -> float:
    table = config["factor_effects"].get(channel, {})
    total = 0.0
    for factor, level in variant_levels.items():
        total += float(table.get(factor, {}).get(level, 0.0))
    return total


def _clamp01(p: float) -> float:
    return min(1.0, max(0.0, p))


class MockHarnessRunner(HarnessRunner):
    runner_id = "mock"

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.subject_id: str = ""
        self.candidates: List[Dict[str, Any]] = []

    def setup(self, config: Dict[str, Any]) -> None:
        self.config = _deep_merge(DEFAULT_CONFIG, config)
        self.candidates = self.config["candidates"]
        subjects = [c["id"] for c in self.candidates if c.get("role") == "subject"]
        if len(subjects) != 1:
            raise ValueError("mock harness config needs exactly one candidate with role=subject")
        self.subject_id = subjects[0]

    def describe(self) -> Dict[str, Any]:
        return {
            "runner_id": self.runner_id,
            "kind": "synthetic",
            "disclosure": (
                "Simulated agent choice/execution model. Factor effects are planted "
                "ground truth for engine validation, not claims about real agents. "
                "Replace with a real harness adapter (claude-code/codex plugin) for "
                "controlled-environment experiments on real harnesses."
            ),
            "observability": {
                "reach": "full candidate set observable (controlled environment)",
                "choice": "selection event observable",
                "success": "attempts and outcomes observable",
                "consumption": "result consumption observable",
            },
            "softmax_temperature": self.config["softmax_temperature"],
            "candidates": [c["id"] for c in self.candidates],
            "config": self.config,
        }

    def run_episode(
        self,
        task: Dict[str, Any],
        variant_levels: Dict[str, str],
        assignment: Dict[str, Any],
        rng,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        assignment = dict(assignment, subject_id=self.subject_id)
        tier = task.get("tier", "medium")

        # 1. Reach: the candidate set actually presented for this decision.
        candidate_ids = [c["id"] for c in self.candidates]
        events.append(funnel.reach_event(assignment, candidate_ids))

        # 2. Choice: softmax over attraction, subject shifted by variant factors.
        temperature = float(self.config["softmax_temperature"])
        attraction_delta = _channel_delta(self.config, "attraction", variant_levels)
        utilities = []
        for c in self.candidates:
            u = float(c["base_attraction"])
            if c["id"] == self.subject_id:
                u += attraction_delta
            utilities.append(u)
        weights = [math.exp(u / temperature) for u in utilities]
        total = sum(weights)
        pick = rng.random() * total
        selected = candidate_ids[-1]
        acc = 0.0
        for cid, w in zip(candidate_ids, weights):
            acc += w
            if pick < acc:
                selected = cid
                break
        events.append(funnel.choice_event(assignment, selected))

        if selected != self.subject_id:
            return events  # competitor chosen: subject has no execution this episode

        # 3. Execution: attempts with retries; one logical operation.
        attempt_cfg = self.config["attempt"]
        success_p = _clamp01(
            float(attempt_cfg["success_base"])
            + float(attempt_cfg["tier_add"].get(tier, 0.0))
            + _channel_delta(self.config, "attempt_success_add", variant_levels)
        )
        retry_prob = float(attempt_cfg["retry_prob"])
        max_attempts = int(attempt_cfg["max_attempts"])

        steps_cfg = self.config["steps"]
        steps_base = int(steps_cfg["base"]) + int(steps_cfg["tier_add"].get(tier, 0))
        steps_delta = int(_channel_delta(self.config, "steps_add", variant_levels))

        attempts = 0
        succeeded = False
        for attempt_index in range(1, max_attempts + 1):
            attempts = attempt_index
            ok = rng.bernoulli(success_p)
            steps = max(1, steps_base + steps_delta + rng.below(int(steps_cfg["jitter"])))
            latency_ms = steps * 45 + rng.below(200)
            cost_units = round(steps * 2.5, 2)
            events.append(
                funnel.attempt_event(
                    assignment, 1, attempt_index,
                    "success" if ok else "failure", steps, latency_ms, cost_units,
                )
            )
            if ok:
                succeeded = True
                break
            if attempt_index < max_attempts and not rng.bernoulli(retry_prob):
                break  # agent gave up

        outcome = "success" if succeeded else "failure"
        events.append(funnel.operation_result_event(assignment, 1, outcome, attempts))

        # 4. Consumption: did the agent actually use the delivered result?
        if succeeded:
            cons_p = _clamp01(
                float(self.config["consumption"]["base"])
                + float(self.config["consumption"]["tier_add"].get(tier, 0.0))
                + _channel_delta(self.config, "consumption_add", variant_levels)
            )
            consumed = rng.bernoulli(cons_p)
            events.append(
                funnel.consumption_event(assignment, 1, consumed, "task_continuation" if consumed else "none")
            )
        else:
            events.append(funnel.consumption_event(assignment, 1, False, "operation_failed"))
        return events
