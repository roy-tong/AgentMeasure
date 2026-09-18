"""Preregistration names for the vendored lab scope.

Minimal vendored surface: the healthcheck conformance pack needs only the
guardrail metric name list from the canonical prereg module. Keep this list
byte-identical to lab/agentmeasure_lab/prereg.py:guardrail_metric_names()
(the conformance pack selftest exercises guardrail aggregation, so a drift
here fails loudly instead of silently disagreeing with the main lab).
"""
from typing import List


def guardrail_metric_names() -> List[str]:
    return [
        "attempts_per_operation",
        "consumption_rate",
        "median_steps_per_operation",
        "cost_units_per_operation",
        "outcome_rate",
        "effect_confirmation_rate",
    ]
