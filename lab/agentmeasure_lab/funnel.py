"""Funnel events and judgment rules (LAB-006, LAB-007).

Funnel: Reach -> Choice -> Success -> Consumption, evaluated inside the
controlled experiment environment where the full candidate set is observable.

Anti-fake-growth semantics (Core 0.4.4) are enforced here:
- retries are additional Attempts of one Operation, never additional
  logical uses (an operation succeeds if any attempt succeeds);
- events carry no timestamps so runs are byte-replayable; wall-clock lives
  in run metadata only;
- every derived rate states its numerator and denominator (Measurement
  Label); missing signals are recorded as "unknown", never guessed.
"""

from typing import Any, Dict, List

from . import FUNNEL_RULES_VERSION

EVENT_SCHEMA = "agentmeasure.lab/funnel-event"
EVENT_SCHEMA_VERSION = "1.0.0"


def _base(event: str, assignment: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": EVENT_SCHEMA,
        "schema_version": EVENT_SCHEMA_VERSION,
        "event": event,
        "experiment_id": assignment["experiment_id"],
        "assignment_id": assignment["assignment_id"],
        "harness_id": assignment["harness_id"],
        "task_id": assignment["task_id"],
        "variant_id": assignment["variant_id"],
        "replicate": assignment["replicate"],
        "subject_id": assignment["subject_id"],
        "rules_version": FUNNEL_RULES_VERSION,
    }


def reach_event(assignment: Dict[str, Any], candidate_ids: List[str]) -> Dict[str, Any]:
    e = _base("reach", assignment)
    e["candidate_ids"] = list(candidate_ids)
    return e


def choice_event(assignment: Dict[str, Any], selected_id: str) -> Dict[str, Any]:
    e = _base("choice", assignment)
    e["selected_id"] = selected_id
    e["selected_subject"] = selected_id == assignment["subject_id"]
    return e


def attempt_event(
    assignment: Dict[str, Any],
    operation_index: int,
    attempt_index: int,
    outcome: str,
    steps: int,
    latency_ms: int,
    cost_units: float,
) -> Dict[str, Any]:
    e = _base("attempt", assignment)
    e.update(
        {
            "operation_index": operation_index,
            "attempt_index": attempt_index,
            "outcome": outcome,  # "success" | "failure"
            "steps": steps,
            "latency_ms": latency_ms,
            "cost_units": cost_units,
        }
    )
    return e


def operation_result_event(
    assignment: Dict[str, Any], operation_index: int, outcome: str, attempts: int
) -> Dict[str, Any]:
    """Operation outcome derived from attempts by versioned rule:

    rule op-success-any/1: an operation succeeds iff any attempt succeeded;
    an operation with only failed attempts is a failure; an operation with
    no attempt outcome is "unresolved", never silently dropped or guessed.
    """
    e = _base("operation_result", assignment)
    e.update({"operation_index": operation_index, "outcome": outcome, "attempts": attempts})
    return e


def consumption_event(
    assignment: Dict[str, Any], operation_index: int, consumed: bool, signal: str
) -> Dict[str, Any]:
    """Consumption of the subject capability's result by the agent.

    signal: "task_continuation" (agent used the result in the task),
    "operation_failed" (nothing delivered to consume),
    "none" (delivered but no consumption observed).
    """
    e = _base("consumption", assignment)
    e.update({"operation_index": operation_index, "consumed": consumed, "signal": signal})
    return e
