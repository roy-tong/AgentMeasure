#!/usr/bin/env python3
"""Run the assumed-resolution evidence case end to end.

Reproduces every number quoted in README.md from fixture.jsonl:

  1. validate + load the 10 effect-confirmed records
  2. compute the provider's headline claim (resolved + assumed_resolved)
  3. compute the audited rate (resolved only, affected_party attested)
  4. show the gap and the settlement-bundle disclosure
  5. write results.json

The point of the case is one sentence: a "resolution" that the provider's own
system inferred from 3 days of silence is NOT the same billable unit as a
resolution the customer confirmed. Aggregating them is what produced the
70%-vs-40% dispute.

Usage: python3 conformance/evidence/assumed-resolution/run_case.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent.parent  # conformance/evidence/<case> -> repo root
sys.path.insert(0, str(REPO / "healthcheck"))

from am_healthcheck.settle import generate_bundle  # noqa: E402

FIXTURE = HERE / "fixture.jsonl"
RESULTS = HERE / "results.json"


def load_records() -> list:
    records = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def main() -> int:
    records = load_records()
    total = len(records)

    # --- The provider's headline number ---------------------------------
    # "Resolution" as the dashboard counts it: confirmed + assumed.
    provider_resolved = sum(
        1 for r in records if r["outcome_class"] in ("resolved", "assumed_resolved"))
    provider_rate = provider_resolved / total if total else 0.0

    # --- The audited number ---------------------------------------------
    # Only outcomes the affected party actually confirmed, and only when the
    # record is settlement-grade (outside its stability window is a separate
    # check the bundle performs; here we count class + grade).
    audited_resolved = sum(
        1 for r in records
        if r["outcome_class"] == "resolved"
        and r["observer_grade"] == "affected_party")
    audited_rate = audited_resolved / total if total else 0.0

    # --- Outcome-class breakdown ----------------------------------------
    by_class: dict = {}
    for r in records:
        by_class[r["outcome_class"]] = by_class.get(r["outcome_class"], 0) + 1

    by_grade: dict = {}
    for r in records:
        by_grade[r["observer_grade"]] = by_grade.get(r["observer_grade"], 0) + 1

    # --- Produce the real settlement bundle through the shipped command --
    bundle = generate_bundle(
        effects_path=str(FIXTURE),
        output_path=str(HERE / "settlement-bundle.json"),
        metadata={
            "provider": "Intercom (Fin)",
            "offering": "per-resolution",
            "period_start": "2025-03-01T00:00:00Z",
            "period_end": "2025-03-31T23:59:59Z",
            "evidence_level": "none",
        },
    )

    results = {
        "case": "assumed-resolution",
        "fixture_records": total,
        "provider_claim": {
            "definition": "resolved + assumed_resolved",
            "count": provider_resolved,
            "rate": round(provider_rate, 4),
        },
        "audited": {
            "definition": "resolved, affected_party attested only",
            "count": audited_resolved,
            "rate": round(audited_rate, 4),
        },
        "gap_percentage_points": round((provider_rate - audited_rate) * 100, 1),
        "by_outcome_class": by_class,
        "by_observer_grade": by_grade,
        "unprovable_count": bundle["metering_summary"]["unprovable_count"],
        "claim_boundary": (
            "Synthetic fixture modelling the publicly reported Intercom Fin "
            "dispute shape. Not Intercom data, not an endorsement, not an "
            "accusation — the case demonstrates what a settlement evidence "
            "bundle would have disclosed."
        ),
    }

    RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    # --- Print the coverage-first summary -------------------------------
    print("Assumed-Resolution Evidence Case")
    print("=" * 52)
    print(f"Fixture records: {total}")
    print()
    print("Provider headline (resolved + assumed_resolved):")
    print(f"  {provider_resolved}/{total} = {provider_rate * 100:.0f}%")
    print()
    print("Audited (resolved, affected_party attested only):")
    print(f"  {audited_resolved}/{total} = {audited_rate * 100:.0f}%")
    print()
    print(f"Gap: {(provider_rate - audited_rate) * 100:.0f} percentage points")
    print()
    print("By outcome class:")
    for cls in ("resolved", "assumed_resolved", "escalated", "abandoned"):
        print(f"  {cls:<18} {by_class.get(cls, 0)}")
    print()
    print("By observer grade:")
    for grade in ("affected_party", "self_attested", "third_party_corroborated"):
        if by_grade.get(grade):
            print(f"  {grade:<26} {by_grade[grade]}")
    print()
    print("UNPROVABLE disclosure:")
    print(f"  {results['unprovable_count']}/{total} records carry no "
          "incrementality evidence")
    print("  → billed at operation basis per COMMERCIAL §5, never zeroed")
    print()
    print(f"Wrote {RESULTS.name} and settlement-bundle.json")

    # The case is a demonstration, not a pass/fail check: exit 0 once the
    # numbers reproduce.
    ok = (provider_resolved == 7 and audited_resolved == 4 and total == 10)
    print()
    print("REPRODUCED" if ok else "MISMATCH — README numbers no longer match fixture")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
