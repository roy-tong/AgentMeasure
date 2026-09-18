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


FAMILY_RUNNERS = {
    "DELEGATION-001": _check_delegation_001,
    "DELEGATION-002": _check_delegation_002,
    "DELEGATION-003": _check_delegation_003,
}


def main() -> int:
    vec_file = VECTORS_DIR / "delegation-001-003.json"
    if not vec_file.exists():
        print(f"  ! file not found: {vec_file}")
        return 1

    data = json.loads(vec_file.read_text(encoding="utf-8"))
    failed = 0
    total = 0
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
