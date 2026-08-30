#!/usr/bin/env python3
"""External fixture conformance: Urusilla-002 (AM-U-007 / #12 regression guard).

Source: second external conformance vector by @jaden3824 (Urusilla), pinned
urusilla @ cfb4ef3 — langfuse/langfuse#16383. Different boundary from 001:
two operations in one assignment (cache-write failure -> cache-read retry;
local schema rejection -> explicit JSON fallback).

Guards:
  1. schema   — every fixture event validates under FMT-002
                (lab/schemas/funnel-event.schema.json);
  2. metrics  — aggregate() reproduces expected.json; multi-operation
                metrics (attempts_per_operation, cost_units_per_operation)
                match the externally pinned values;
  3. AM-U-007 (#12) — median_steps_per_operation is operation-grain:
                per-operation step totals reproduce [3, 2], the median is
                2.5 with denominator 2 (not 5.0 / 1 at assignment grain);
  4. fail-closed — an operation whose declaration fails reconciliation
                contributes nothing to the median.

Claim boundary (from the source project, stated verbatim in intent): this
fixture is project-authored synthetic offline evidence only — no AgentMeasure
endorsement, upstream acceptance, external reproduction, Urusilla adoption,
live model run, or real provider-cost observation is implied.

Exit 0 = all guards pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from agentmeasure_lab.analysis import aggregate  # noqa: E402
from agentmeasure_lab.schemas import SchemaError, validate  # noqa: E402

VEC = ROOT / "conformance" / "vectors" / "external" / "urusilla-002"
EVENTS_FILE = VEC / "agentmeasure_urusilla_fixture_002.events.jsonl"
EXPECTED_FILE = VEC / "agentmeasure_urusilla_fixture_002.expected.json"
SCHEMA_FILE = ROOT / "lab" / "schemas" / "funnel-event.schema.json"

fails: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def main() -> int:
    events = [json.loads(l) for l in EVENTS_FILE.read_text().splitlines() if l.strip()]
    doc = json.loads(EXPECTED_FILE.read_text())
    expected = doc["expected_current_agentmeasure_metrics"]
    cross = doc["multi_operation_grain_cross_check"]
    schema = json.loads(SCHEMA_FILE.read_text())

    print("urusilla-002 guard 1: schema validation (FMT-002)")
    for i, ev in enumerate(events, 1):
        try:
            validate(ev, schema)
        except SchemaError as e:
            check(f"event {i} valid", False, str(e))
    check(f"{len(events)} events valid under FMT-002", len(events) == 10)

    print("urusilla-002 guard 2: metrics reproduce expected.json")
    cell = aggregate(events)[("urusilla-projection",)]
    for k in ("reach", "selected", "operations"):
        check(f"{k} == {expected[k]}", cell[k] == expected[k], f"got {cell[k]}")
    for k in ("selection_rate", "operation_success_rate", "consumption_rate",
              "attempts_per_operation", "cost_units_per_operation"):
        check(f"{k}.value == {expected[k]['value']}",
              cell[k]["value"] == expected[k]["value"], f"got {cell[k]['value']}")
    check("attempts preserved (4)",
          cell["attempts_per_operation"]["numerator"] == expected["attempts_per_operation"]["numerator"])
    check("cost units preserved (13.0)",
          cell["cost_units_per_operation"]["numerator"] == expected["cost_units_per_operation"]["numerator"])
    check("reconciliation: passed",
          cell["operation_reconciliation"]["status"] == expected["operation_reconciliation"]["status"],
          cell["operation_reconciliation"]["status"])

    print("urusilla-002 guard 3: AM-U-007 (#12) operation-grain median")
    per_op = {}
    for ev in events:
        if ev["event"] == "attempt":
            k = (ev["assignment_id"], ev.get("operation_index"))
            per_op[k] = per_op.get(k, 0) + ev["steps"]
    totals = sorted(per_op.values())
    check(f"per-operation step totals == {cross['operation_step_totals']}",
          totals == sorted(cross["operation_step_totals"]), f"got {totals}")
    med = cell["median_steps_per_operation"]
    check(f"median == {cross['semantic_median_steps_per_operation']} (semantic, post-fix)",
          med["value"] == cross["semantic_median_steps_per_operation"], f"got {med['value']}")
    check(f"denominator == {cross['semantic_denominator']} (resolved operations)",
          med["denominator"] == cross["semantic_denominator"], f"got {med['denominator']}")

    print("urusilla-002 guard 4: fail-closed on failed reconciliation")
    evs = [json.loads(json.dumps(e)) for e in events]
    decl = next(e for e in evs if e["event"] == "operation_result")
    decl["attempts"] = 9  # contradicts its measured rows -> reconciliation fails
    c2 = aggregate(evs)[("urusilla-projection",)]
    check("tampered declaration -> reconciliation failed",
          c2["operation_reconciliation"]["status"] == "failed",
          c2["operation_reconciliation"]["status"])
    m2 = c2["median_steps_per_operation"]
    remaining = sorted(t for t in per_op.values())
    expected_med = sorted(
        v for k, v in per_op.items()
        if k != (decl["assignment_id"], decl.get("operation_index"))
    )
    check(f"failed operation's steps excluded (median {sorted(expected_med)[0] if len(expected_med)==1 else '...'}, denominator {len(expected_med)})",
          m2["denominator"] == len(expected_med) and m2["value"] == (
              expected_med[0] if len(expected_med) == 1 else m2["value"]),
          f"got value={m2['value']} denominator={m2['denominator']}")

    if fails:
        print(f"\nURUSILLA-002 CONFORMANCE FAIL: {len(fails)} guard(s)")
        return 1
    print("\nURUSILLA-002 CONFORMANCE PASS: schema + metrics + AM-U-007 grain + fail-closed all guarded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
