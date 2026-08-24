#!/usr/bin/env python3
"""External fixture conformance: Urusilla-001 (#8 / #9 regression guard).

Source: first external conformance pass by @jaden3824 (Urusilla), pinned
AgentMeasure v0.2.1 @ 20807ad — langfuse/langfuse#16383.
Accepted upstream per the commitment in issues #8 and #9.

Guards:
  1. schema   — every fixture event validates under FMT-002
                (lab/schemas/funnel-event.schema.json);
  2. #8       — mutations that strip a root-required field (sibling of the
                root oneOf) must be REJECTED by the validator;
  3. metrics  — aggregate() reproduces expected.json exactly;
  4. #9       — tampered operation_result declarations (wrong attempt count,
                wrong outcome, missing attempt rows) must surface as
                reconciliation: failed, never silent trust.

Claim boundary (from the source project): this fixture is project-authored
synthetic evidence — not an AgentMeasure endorsement, a Langfuse adoption,
an external reproduction, or a real provider-cost observation.

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

VEC = ROOT / "conformance" / "vectors" / "external" / "urusilla-001"
EVENTS_FILE = VEC / "agentmeasure_urusilla_fixture_001.events.jsonl"
EXPECTED_FILE = VEC / "agentmeasure_urusilla_fixture_001.expected.json"
SCHEMA_FILE = ROOT / "lab" / "schemas" / "funnel-event.schema.json"

fails: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def main() -> int:
    events = [json.loads(l) for l in EVENTS_FILE.read_text().splitlines() if l.strip()]
    expected = json.loads(EXPECTED_FILE.read_text())["expected_metrics"]
    schema = json.loads(SCHEMA_FILE.read_text())

    print("urusilla-001 guard 1: schema validation (FMT-002)")
    for i, ev in enumerate(events, 1):
        try:
            validate(ev, schema)
        except SchemaError as e:
            check(f"event {i} valid", False, str(e))
    check(f"{len(events)} events valid under FMT-002", True)

    print("urusilla-001 guard 2: #8 root-sibling enforcement")
    root_required = [k for k in schema.get("required", [])]
    victim = dict(events[2])  # an attempt event
    for field in root_required:
        mutated = {k: v for k, v in victim.items() if k != field}
        try:
            validate(mutated, schema)
            check(f"missing {field} rejected", False, "validator accepted a oneOf-matching record without root sibling")
        except SchemaError:
            check(f"missing {field} rejected", True)

    print("urusilla-001 guard 3: metrics reproduce expected.json")
    cell = aggregate(events)[("urusilla-projection",)]
    for k in ("reach", "selected", "operations"):
        check(f"{k} == {expected[k]}", cell[k] == expected[k], f"got {cell[k]}")
    for k in ("selection_rate", "operation_success_rate", "consumption_rate",
              "attempts_per_operation", "cost_units_per_operation"):
        check(f"{k}.value == {expected[k]['value']}",
              cell[k]["value"] == expected[k]["value"], f"got {cell[k]['value']}")
    check("median_steps == 5.0",
          cell["median_steps_per_operation"]["value"] == expected["median_steps_per_operation"]["value"])
    check("reconciliation: passed", cell["operation_reconciliation"]["status"] == "passed",
          cell["operation_reconciliation"]["status"])

    print("urusilla-001 guard 4: #9 declared-summary reconciliation")

    def tampered(mutator) -> dict:
        evs = [json.loads(json.dumps(e)) for e in events]
        mutator(evs)
        return aggregate(evs)[("urusilla-projection",)]

    def _decl(evs):
        return next(e for e in evs if e["event"] == "operation_result")

    # a) declared attempt count contradicts rows
    c = tampered(lambda evs: _decl(evs).update(attempts=9))
    rec = c["operation_reconciliation"]
    check("declared attempts=9 -> failed", rec["status"] == "failed", rec["status"])
    check("attempts stay measured (4)", c["attempts_per_operation"]["numerator"] == 4,
          f"got {c['attempts_per_operation']['numerator']}")

    # b) declared outcome contradicts attempt rows
    c = tampered(lambda evs: _decl(evs).update(outcome="failure"))
    rec = c["operation_reconciliation"]
    check("declared failure vs derived success -> failed", rec["status"] == "failed", rec["status"])
    check("operation still counted from rows", c["operation_success_rate"]["numerator"] == 1)

    # c) no attempt rows at all under the declaration
    c = tampered(lambda evs: [evs.remove(e) for e in list(evs) if e["event"] == "attempt"])
    rec = c["operation_reconciliation"]
    check("zero attempt rows -> failed", rec["status"] == "failed", rec["status"])
    check("attempts do not fall back to declaration",
          c["attempts_per_operation"]["numerator"] == 0,
          f"got {c['attempts_per_operation']['numerator']}")

    if fails:
        print(f"\nURUSILLA-001 CONFORMANCE FAIL: {len(fails)} guard(s)")
        return 1
    print("\nURUSILLA-001 CONFORMANCE PASS: schema + #8 + metrics + #9 all guarded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
