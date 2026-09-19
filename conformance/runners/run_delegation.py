#!/usr/bin/env python3
"""AgentMeasure Delegation conformance runner (DELEGATION-001..003).
Draft 0.4.5 — runs the nested delegation-family vectors and asserts verdicts.

These checks pin the CORE §9 invariants that CORE 0.4.5 introduced with the
Delegation object: 27 (no flattening into Operation), 28 (both-side
traceability), 29 (correlated-only outcome reference), 30 (DAG enforcement),
31 (child-side cost ownership).

Usage: python3 conformance/runners/run_delegation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS_DIR = ROOT / "conformance" / "vectors"

PASS, FAIL = "PASS", "FAIL"

# Top-level delegation depth is 0; the profile default ceiling is 2 hops
# (CORE §9 invariant 30 leaves the exact bound to the profile).
MAX_DELEGATION_DEPTH = 2


def _check_delegation_001(vector: dict) -> bool:
    """Delegation MUST NOT be flattened into Operation (invariant 27)."""
    inp = vector["input"]
    exp = vector["expect"]
    delegations = inp.get("delegations", [])
    operations = inp.get("operations", [])

    delegation_count = len(delegations)
    operation_count = len(operations)

    if exp.get("verdict") == PASS:
        # Counts are reported separately and match the raw input sizes.
        return (delegation_count == exp["delegation_count"]
                and operation_count == exp["operation_count"]
                and not exp.get("delegation_inflated_operation_count", False))

    # FAIL case: the provider's claimed operation count includes delegations.
    claimed = inp.get("claimed_operation_count")
    inflated = claimed is not None and claimed != operation_count
    return (not exp.get("claimed_operation_count_matches", True)
            and inflated
            and exp.get("verdict") == FAIL)


def _has_cycle(edges) -> bool:
    """DFS cycle detection over delegating_caller → called_agent edges."""
    graph = {}
    for e in edges:
        graph.setdefault(e["delegating_caller"], []).append(e["called_agent"])

    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    for n in list(graph):
        for m in graph[n]:
            color.setdefault(m, WHITE)

    def visit(node):
        color[node] = GREY
        for nxt in graph.get(node, []):
            if color.get(nxt) == GREY:
                return True
            if color.get(nxt) == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in list(color))


def _check_delegation_002(vector: dict) -> bool:
    """Delegation graph MUST be a DAG with a bounded depth (invariant 30)."""
    inp = vector["input"]
    exp = vector["expect"]
    edges = inp.get("delegations", [])

    cycle = _has_cycle(edges)
    max_depth = max((e.get("depth", 0) for e in edges), default=0)

    if exp.get("cycle_detected"):
        # A→B→A MUST be detected and rejected.
        return cycle and exp.get("dag_integrity") is False

    if exp.get("depth_limit_enforced") is False:
        # The chain reaches the declared ceiling → the limit was not enforced,
        # which is the violation this vector demonstrates.
        limit = inp.get("max_delegation_depth")
        return limit is not None and max_depth >= limit

    if exp.get("verdict") == PASS:
        return (not cycle
                and max_depth == exp.get("max_depth_observed", max_depth)
                and exp.get("dag_integrity") is True)

    return False


def _check_delegation_003(vector: dict) -> bool:
    """Child-side cost belongs to the child; parent aggregation is labelled.

    Invariants 28/31: cross-side attribution is at most `correlated`, and the
    parent's aggregate MUST be marked `aggregated` (never presented as a
    directly observed figure).
    """
    inp = vector["input"]
    exp = vector["expect"]

    # FAIL case: the same child spend is claimed by both parent and child.
    if exp.get("double_count_detected"):
        parent = inp.get("parent_harness", {})
        child = inp.get("child_harness", {})
        combined = parent.get("claimed_cost", 0.0) + child.get("claimed_cost", 0.0)
        return (combined > exp.get("unique_total_cost", 0.0)
                and exp.get("verdict") == FAIL)

    if exp.get("verdict") != PASS:
        return False

    # Case: parent reports own + aggregated child cost, labelled.
    report = inp.get("parent_cost_report")
    if report is not None:
        expected = (report.get("own_attempts_cost", 0.0)
                    + report.get("aggregated_child_cost", 0.0))
        accounted = abs(report.get("total_cost", 0.0) - expected) < 1e-9
        labelled = report.get("aggregation_label") == "aggregated"
        return accounted and labelled

    # Case: lineage trace with per-attempt child costs.
    attempts = inp.get("child_session_attempts", [])
    agg = inp.get("aggregation_report", {})
    child_total = sum(a.get("cost", 0.0) for a in attempts)
    traceable = abs(agg.get("total_child_cost", -1.0) - child_total) < 1e-9
    lineage_preserved = bool(inp.get("lineage"))
    labelled = bool(agg.get("lineage_trace"))
    return traceable and lineage_preserved and labelled


def _check_delegation_004(vector: dict) -> bool:
    """Under-count: child spend never rolls up (invariant 31 / D-2)."""
    inp = vector["input"]
    exp = vector["expect"]
    rep = inp["parent_report"]
    child_total = round(sum(a.get("cost", 0.0) for a in inp.get("child_attempts", [])), 6)
    cid = vector["id"]

    if round(child_total, 6) != round(exp["child_cost_total"], 6):
        return False

    if cid == "del-004a-silent-under-count":
        reported = rep["reported_total"]
        claims_to_include = rep.get("includes_child_cost", False)
        declared = rep.get("exclusion_declared", False)
        under = round(exp["expected_parent_total"] - reported, 6)
        # Silent: claims to include child cost, does not, and declares no exclusion.
        return (claims_to_include and not declared
                and abs(under - round(exp["under_counted_by"], 6)) < 1e-9
                and exp["verdict"] == FAIL)

    if cid == "del-004b-rolls-up-labelled":
        expected = round(rep["own_cost"] + child_total, 6)
        return (abs(rep["reported_total"] - expected) < 1e-9
                and rep.get("aggregation_label") == "aggregated"
                and exp["verdict"] == PASS)

    if cid == "del-004c-disclosed-exclusion":
        # Own cost only, but the exclusion is stated: auditable, so it passes.
        return (not rep["includes_child_cost"] and rep.get("exclusion_declared")
                and exp["verdict"] == PASS)

    return False


def _check_delegation_005(vector: dict) -> bool:
    """Over-count: an inherited cumulative counter bills the parent twice."""
    inp = vector["input"]
    exp = vector["expect"]
    cid = vector["id"]

    if cid == "del-005a-inherited-counter":
        parent_final = inp["parent"]["final_cumulative_tokens"]
        child_first = inp["child"]["first_snapshot_cumulative_tokens"]
        inherited = child_first == parent_final
        return (inherited
                and exp["inheritance_detected"] is True
                and inp["billed_total_tokens"] >= parent_final + inp["child"]["own_usage_tokens"]
                and exp["verdict"] == FAIL)

    if cid == "del-005b-own-counter":
        child = inp["child"]
        inherited = child["first_snapshot_cumulative_tokens"] == inp["parent"]["final_cumulative_tokens"]
        return (not inherited and exp["inheritance_detected"] is False
                and exp["verdict"] == PASS)

    if cid == "del-005c-shared-instance":
        n = inp["agents_sharing"]
        measured = inp["measured_usage_tokens"]
        reported = inp["reported_usage_tokens"]
        factor = reported / measured if measured else 0
        return (inp.get("shared_llm_instance") and n > 1
                and abs(factor - n) < 1e-9
                and abs(factor - exp["multiplication_factor"]) < 1e-9
                and exp["verdict"] == FAIL)

    return False


def _check_delegation_006(vector: dict) -> bool:
    """Mis-attribution: the billing record must name the serving agent/model."""
    inp = vector["input"]
    exp = vector["expect"]
    cid = vector["id"]

    if cid == "del-006a-handoff-misattribution":
        served = inp["serving_record"]
        billed = inp["billing_record"]
        mutated_early = not inp["handoff"].get("handoff_after_turn_closed", False)
        mismatch = (served["agent"] != billed["agent"]
                    or served["model"] != billed["model"])
        return (mismatch and mutated_early
                and exp["attribution_matches"] is False
                and exp["verdict"] == FAIL)

    if cid == "del-006b-correct-attribution":
        served = inp["serving_record"]
        billed = inp["billing_record"]
        closed_first = inp["handoff"].get("handoff_after_turn_closed", False)
        return (served == billed and closed_first
                and exp["attribution_matches"] is True
                and exp["verdict"] == PASS)

    if cid == "del-006c-flattened-to-root":
        flattened = sum(1 for s in inp["spans"]
                        if s.get("expected_parent") and not s.get("parent_span_id"))
        return (flattened == exp["flattened_spans"] and flattened > 0
                and exp["verdict"] == FAIL)

    return False


def _check_delegation_007(vector: dict) -> bool:
    """Non-propagation: a declared budget must reach the child to be enforceable."""
    inp = vector["input"]
    exp = vector["expect"]
    d = inp["delegation"]
    cid = vector["id"]
    budget = d.get("budget_declared")

    if cid == "del-007a-declared-not-propagated":
        propagated = d.get("budget_propagated_to_child", False)
        overspend = round(inp["child_spend"] - budget, 6) if budget else None
        return (budget is not None and not propagated
                and abs(overspend - round(exp["overspend"], 6)) < 1e-9
                and exp["budget_enforceable_at_child"] is False
                and exp["verdict"] == FAIL)

    if cid == "del-007b-propagated":
        propagated = d.get("budget_propagated_to_child", False)
        within = budget is not None and inp["child_spend"] <= budget
        return (propagated and within
                and exp["budget_enforceable_at_child"] is True
                and exp["verdict"] == PASS)

    if cid == "del-007c-no-budget":
        # Nothing was declared, so nothing failed. The absence is disclosed,
        # not treated as an enforcement gap.
        return (budget is None
                and exp["budget_enforceable_at_child"] is None
                and exp["verdict"] == PASS)

    return False


FAMILY_RUNNERS = {
    "DELEGATION-001": _check_delegation_001,
    "DELEGATION-002": _check_delegation_002,
    "DELEGATION-003": _check_delegation_003,
    "DELEGATION-004": _check_delegation_004,
    "DELEGATION-005": _check_delegation_005,
    "DELEGATION-006": _check_delegation_006,
    "DELEGATION-007": _check_delegation_007,
}


def main() -> int:
    vec_files = sorted(VECTORS_DIR.glob("delegation-*.json"))
    if not vec_files:
        print(f"  ! no delegation vector files under {VECTORS_DIR}")
        return 1

    failed = 0
    total = 0
    for vec_file in vec_files:
        data = json.loads(vec_file.read_text(encoding="utf-8"))
        for group in data["vectors"]:
            gid = group["id"]
            runner = FAMILY_RUNNERS.get(gid)
            if runner is None:
                print(f"  ! no runner for {gid}")
                continue
            for v in group.get("vectors", []):
                total += 1
                try:
                    ok = runner(v)
                except Exception as exc:  # noqa: BLE001
                    ok = False
                    print(f"    error: {exc}")
                if ok:
                    print(f"  ✓ [{gid}] {v['id']}")
                else:
                    print(f"  ✗ [{gid}] {v['id']}")
                    failed += 1

    print(f"\n{total - failed}/{total} delegation vectors PASS"
          + ("" if failed == 0 else f" ({failed} FAILED)"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
