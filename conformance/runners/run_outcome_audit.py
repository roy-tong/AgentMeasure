#!/usr/bin/env python3
"""AgentMeasure Outcome Audit conformance runner (OUT-001..004).
Draft 0.4.4 — runs the nested OUT family vectors and asserts expected verdicts.

Usage: python3 conformance/runners/run_outcome_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS_DIR = ROOT / "conformance" / "vectors"

PASS, FAIL, UNPROVABLE = "PASS", "FAIL", "UNPROVABLE"


def _check_out_001(vector: dict) -> bool:
    """Outcome Determinability: billing claims must map to a registered class.

    Three sub-vectors:
      out-001a: registered class + matching claim → PASS
      out-001b: unregistered class → FAIL
      out-001c: assumed_resolved claimed as resolved → FAIL
    """
    cid = vector["id"]
    obs = vector["input"]["observation"]
    claim = vector["input"]["billing_claim"]
    exp = vector["expect"]
    outcome_class = obs.get("outcome_class", "")
    claimed_class = claim.get("outcome_class_claimed", "")

    if cid == "out-001a-registered":
        # Known registered classes: resolved, assumed_resolved, escalated, abandoned, reopened, not_outcome
        registered = {"resolved", "assumed_resolved", "escalated", "abandoned", "reopened", "not_outcome"}
        return (
            outcome_class in registered
            and outcome_class == claimed_class
            and exp["verdict"] == PASS
        )
    elif cid == "out-001b-unregistered":
        return (
            not exp.get("class_in_registry", True)
            and exp["verdict"] == FAIL
        )
    elif cid == "out-001c-assumed-vs-resolved":
        return (
            outcome_class == "assumed_resolved"
            and claimed_class == "resolved"
            and exp["verdict"] == FAIL
        )
    return False


def _check_out_002(vector: dict) -> bool:
    """Effect Confirmation Traceability: billing lines must reference effect_confirmed records."""
    cid = vector["id"]
    exp = vector["expect"]

    if cid == "out-002a-traceable":
        ref = vector["input"]["billing_line"].get("effect_confirmation_ref")
        confirmation = vector["input"].get("effect_confirmation", {})
        return bool(ref) and bool(confirmation.get("observer_grade")) and exp["verdict"] == PASS
    elif cid == "out-002b-no-trace":
        ref = vector["input"]["billing_line"].get("effect_confirmation_ref")
        return ref is None and exp["verdict"] == FAIL
    elif cid == "out-002c-unstable":
        settlement_as_of = vector["input"].get("settlement_as_of", "")
        deadline = vector["input"].get("effect_confirmation", {}).get("stability_deadline", "")
        within_window = settlement_as_of < deadline if settlement_as_of and deadline else True
        return within_window and not exp["settlement_grade"] and "PASS" in exp["verdict"]
    return False


def _check_out_003(vector: dict) -> bool:
    """Reopen/Repeat Dedup: same task must not produce two billable outcome units."""
    cid = vector["id"]
    exp = vector["expect"]

    if cid == "out-003a-no-dual-bill":
        n_lines = len(vector["input"].get("billing_lines", []))
        return n_lines == 1 and exp["verdict"] == PASS and exp["total_billable_outcome_units"] == 1
    elif cid == "out-003b-reopen-links":
        effects = vector["input"].get("effects", [])
        reversals = [e for e in effects if e.get("reversal_of")]
        return len(reversals) == 1 and exp["reversal_chain_verified"] and exp["verdict"] == PASS
    elif cid == "out-003c-silent-reversal":
        return exp.get("possible_silent_reversal") and not exp["reversal_chain_verified"] and exp["verdict"] == FAIL
    return False


def _check_out_004(vector: dict) -> bool:
    """Claim-Evidence Match: billing_basis=outcome must carry incrementality_evidence."""
    cid = vector["id"]
    bl = vector["input"]["billing_line"]
    exp = vector["expect"]

    if cid == "out-004a-evidence-matches":
        return bl.get("incrementality_evidence") == "v4_holdout" and exp["verdict"] == PASS
    elif cid == "out-004b-evidence-none":
        return bl.get("incrementality_evidence") == "none" and exp.get("effective_billing_basis") == "operation" and "PASS" in exp["verdict"]
    elif cid == "out-004c-assumed-as-resolved":
        actual = vector["input"].get("actual_outcome", {})
        return actual.get("outcome_class") == "assumed_resolved" and actual.get("observer_grade") == "self_attested" and exp["verdict"] == FAIL
    return False


def _check_out_005(vector: dict) -> bool:
    """Symmetric Disclosure: a bundle must report findings both ways and net them.

    COMMERCIAL 5.1 D-2. A statement that only ever finds against the audited
    party is an advocacy document; the audited party can dismiss it with one
    counter-example in their favour.
    """
    cid = vector["id"]
    b = vector["input"]["bundle"]
    exp = vector["expect"]

    disputed = b.get("disputed_lines", 0)
    underbilled = b.get("underbilled_lines", 0)
    searched = b.get("search_for_favourable_findings") != "not_performed"
    both_directions = bool(underbilled) or searched

    if cid == "out-005a-symmetric":
        netted = abs(b.get("claimed_amount", -1) - (b.get("disputed_amount", 0) - b.get("underbilled_amount", 0))) < 1e-9
        return (disputed > 0 and underbilled > 0 and both_directions
                and netted and exp["verdict"] == PASS)

    if cid == "out-005b-one-directional":
        # No favourable search performed at all -> advocacy, not audit.
        return (not searched and underbilled == 0
                and exp["verdict"] == FAIL)

    if cid == "out-005c-claimed-without-netting":
        net = b.get("disputed_amount", 0) - b.get("underbilled_amount", 0)
        claimed_gross = abs(b.get("claimed_amount", -1) - b.get("disputed_amount", 0)) < 1e-9
        return (both_directions and claimed_gross
                and abs(b.get("claimed_amount", -1) - net) > 1e-9
                and exp["verdict"] == FAIL)

    return False


# Map OUT check IDs to their runner functions
FAMILY_RUNNERS = {
    "OUT-001": _check_out_001,
    "OUT-002": _check_out_002,
    "OUT-003": _check_out_003,
    "OUT-004": _check_out_004,
    "OUT-005": _check_out_005,
}


def main() -> int:
    vec_file = VECTORS_DIR / "out-001-004.json"
    if not vec_file.exists():
        print(f"  ! file not found: {vec_file}")
        return 1

    data = json.loads(vec_file.read_text(encoding="utf-8"))
    family_runner_map = {}
    for group in data["vectors"]:
        gid = group["id"]
        runner = FAMILY_RUNNERS.get(gid)
        if runner is None:
            print(f"  ! no runner for {gid}")
            continue
        family_runner_map[gid] = (runner, group.get("vectors", []))

    failed = 0
    total = 0
    for gid, (runner, subvecs) in sorted(family_runner_map.items()):
        for v in subvecs:
            total += 1
            try:
                ok = runner(v)
            except Exception as exc:
                ok = False
                print(f"    error: {exc}")
            if ok:
                print(f"  ✓ [{gid}] {v['id']}")
            else:
                print(f"  ✗ [{gid}] {v['id']}")
                failed += 1

    print(f"\n{total - failed}/{total} OUT vectors PASS" + ("" if failed == 0 else f" ({failed} FAILED)"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())