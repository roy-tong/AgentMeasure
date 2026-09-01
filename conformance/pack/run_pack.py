#!/usr/bin/env python3
"""AgentMeasure Conformance Pack — check a caller-provided telemetry fixture
against measurement invariants. PASS / FAIL / UNPROVABLE, never silent zeros.

Subcommands:
  conformance --fixture events.jsonl [--metadata m.json] [--claims c.json]
              [--json out.json] [--require id,id] [--strict]
  selftest    run the pack against the repository's own external fixtures
              (independent of caller input, per contract C1)

Exit codes: 0 = no FAIL (UNPROVABLE allowed unless --require'd); 1 = FAIL
present, or a required invariant not PROVEN; 2 = usage / input error.

First-principle: AgentMeasure does not tell you whether your agent system is
good. It tells you whether your metrics mean what you think they mean.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from agentmeasure_lab.analysis import aggregate  # noqa: E402
from agentmeasure_lab.schemas import SchemaError, validate  # noqa: E402

PACK = Path(__file__).resolve().parent
REGISTRY = json.loads((PACK / "invariants.json").read_text(encoding="utf-8"))
SCHEMA_FILE = ROOT / "lab" / "schemas" / "funnel-event.schema.json"

PASS, FAIL, UNPROVABLE = "PASS", "FAIL", "UNPROVABLE"


def check_schema_events(raw_lines):
    events, errors = [], []
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    for i, line in enumerate(raw_lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: invalid JSON ({e})")
            continue
        try:
            validate(ev, schema)
        except SchemaError as e:
            errors.append(f"line {i}: FMT-002 schema violation ({e})")
            continue
        events.append(ev)
    return events, errors


def load_metadata(path):
    if not path:
        return None, []
    md = json.loads(Path(path).read_text(encoding="utf-8"))
    required = ["source", "time_window", "observation_surface", "data_class"]
    missing = [k for k in required if not md.get(k)]
    if md.get("data_class") not in (None, "production", "synthetic"):
        return md, [f"metadata.data_class must be production or synthetic, got {md.get('data_class')!r}"]
    return md, [f"metadata missing field: {k}" for k in missing]


def load_claims(path):
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate(events, claims):
    """Map aggregate() output to invariant verdicts. Data-only mode checks
    internal consistency and computes reference values; claims mode additionally
    compares observed claims against computation and FAILs on mismatch."""
    cells = aggregate(events)
    # single-cell packs: FMT-002 fixtures are per experiment variant; if the
    # fixture spans multiple variant cells, evaluate each and report combined.
    results = []

    def fail_reasons(recs):
        out = []
        for r in recs:
            for why in r.get("reasons", []):
                out.append(why)
        return out

    for key, c in cells.items():
        declared = c["operation_reconciliation"]["declared_summaries"]
        recon_failed = c["operation_reconciliation"]["failed"]
        recon_status = c["operation_reconciliation"]["status"]
        aps = c["attempts_per_operation"]
        # aggregate() attributes attempts to operations at declaration time;
        # the pack counts raw attempt rows itself so that missing declarations
        # are reported as missing evidence, not as absent attempts.
        attempt_rows = sum(1 for ev in events if ev.get("event") == "attempt")
        med = c["median_steps_per_operation"]
        cup = c["cost_units_per_operation"]
        # attempt groups by (assignment_id, operation_index), straight from rows
        declared_keys = set()
        for ev in events:
            if ev.get("event") == "operation_result":
                declared_keys.add((ev["assignment_id"], ev.get("operation_index")))
        attempt_groups = {}
        for ev in events:
            if ev.get("event") == "attempt":
                k = (ev["assignment_id"], ev.get("operation_index"))
                attempt_groups[k] = attempt_groups.get(k, 0) + 1
        undeclared_attempt_groups = sum(1 for k in attempt_groups if k not in declared_keys)

        r = {"cell": list(key)}

        # I-1 execution-grain
        if declared == 0 and attempt_rows > 0:
            r["execution-grain"] = {
                "verdict": UNPROVABLE,
                "reason": f"{attempt_rows} attempt row(s) observed; no declared or safely "
                          "correlated operation boundary exists; unsafe inference refused",
                "reference": {"attempts": attempt_rows, "operations": None},
            }
        elif declared == 0 and attempt_rows == 0:
            r["execution-grain"] = {"verdict": UNPROVABLE,
                                    "reason": "no attempt rows and no operation declarations"}
        else:
            r["execution-grain"] = {
                "verdict": PASS if recon_status == "passed" else FAIL,
                "reference": {"operations": c["operations"], "attempts": aps["numerator"],
                              "attempts_per_operation": aps["value"]},
            }
            if recon_status != "passed":
                r["execution-grain"]["reason"] = "; ".join(fail_reasons(c["operation_reconciliation"]["failures"]))

        # I-2 retry-reconciliation
        if declared == 0:
            r["retry-reconciliation"] = {
                "verdict": UNPROVABLE, "reason": "no operation_result declarations to reconcile"}
        else:
            r["retry-reconciliation"] = {
                "verdict": PASS if recon_status == "passed" else FAIL,
                "reference": {"declared": declared, "reconciled": declared - recon_failed,
                              "failed": recon_failed},
            }
            if recon_status != "passed":
                r["retry-reconciliation"]["reason"] = "; ".join(
                    fail_reasons(c["operation_reconciliation"]["failures"]))

        # I-3 cost-preservation
        if cup["numerator"] in (0, 0.0, None):
            r["cost-preservation"] = {"verdict": UNPROVABLE,
                                      "reason": "fixture carries no attempt cost fields"}
        else:
            conserved = abs(round(cup["numerator"], 6) - round(
                sum(ev.get("cost_units", 0) for ev in events if ev.get("event") == "attempt"), 6)) < 1e-9
            r["cost-preservation"] = {
                "verdict": PASS if conserved else FAIL,
                "reference": {"total_attempt_cost": cup["numerator"],
                              "per_operation": cup["value"],
                              "note": "arithmetic conservation of the fixture's own cost "
                                      "units; not a statement about real billing"},
            }
            if not conserved:
                r["cost-preservation"]["reason"] = "grouped cost differs from sum of attempt costs"

        # I-4 operation-grain (assignment-grain aggregation is the AM-U-007 class)
        if med["value"] is None or med["denominator"] == 0:
            r["operation-grain"] = {"verdict": UNPROVABLE,
                                    "reason": "no resolved operation carries steps"}
        else:
            entry = {"verdict": PASS,
                     "reference": {"median_steps_per_operation": med["value"],
                                   "denominator_operations": med["denominator"],
                                   "grain": "operation"}}
            if claims is not None:
                claimed = claims.get("median_steps_per_operation")
                if isinstance(claimed, dict):
                    claimed = claimed.get("value")
                if claimed is not None:
                    entry["claimed"] = claimed
                    if abs(float(claimed) - float(med["value"])) > 1e-9:
                        entry["verdict"] = FAIL
                        entry["reason"] = (f"claimed {claimed} at the metric's declared "
                                           f"operation grain; computation at that grain "
                                           f"gives {med['value']} over {med['denominator']}")
            r["operation-grain"] = entry

        # I-5 evidence-boundary (disclosure through-line)
        total_groups = len(attempt_groups)
        covered = declared - recon_failed
        r["evidence-boundary"] = {
            "verdict": PASS,  # disclosure itself succeeds; content is what matters
            "reference": {
                "declared_operations": declared,
                "reconciled": covered,
                "attempt_groups_without_operation_evidence": undeclared_attempt_groups,
                "decidability_coverage": (round(covered / declared, 4) if declared else None),
            },
            "note": "attempt groups without operation evidence are disclosed, "
                    "not folded into counts",
        }
        results.append(r)
    return results


def human_report(results, metadata_warnings, claims_mode, registry):
    lines = ["AgentMeasure Conformance Pack v" + registry["pack_version"]]
    counts = {PASS: 0, FAIL: 0, UNPROVABLE: 0}
    for r in results:
        lines.append("")
        lines.append(f"cell {r['cell']}")
        for inv in registry["invariants"]:
            if inv["status"] != "supported":
                lines.append(f"  –  {inv['id']:<22} NOT-SUPPORTED ({inv['reason'][:60]}…)")
                continue
            v = r.get(inv["id"])
            if not v:
                continue
            counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
            mark = {PASS: "✓ PASS ", FAIL: "✗ FAIL ", UNPROVABLE: "? UNPROVABLE"}[v["verdict"]]
            lines.append(f"  {mark} {inv['id']}")
            if v.get("reason"):
                lines.append(f"        reason: {v['reason']}")
            if v.get("reference"):
                lines.append(f"        reference: {json.dumps(v['reference'], ensure_ascii=False)}")
    n = sum(counts.values())
    lines.append("")
    if n and counts[PASS] == n and counts[UNPROVABLE] == 0:
        lines.append(f"{n} invariants checked: all PASS.")
    elif counts[FAIL] == 0 and counts[UNPROVABLE] > 0:
        lines.append(f"{n} invariants checked: {counts[PASS]} PASS, {counts[UNPROVABLE]} UNPROVABLE, "
                     "0 FAIL. UNPROVABLE means the evidence to decide is absent — this is a "
                     "finding, not a pass; use --require to make specific rules blocking.")
    else:
        lines.append(f"{n} invariants checked: {counts[PASS]} PASS, {counts[FAIL]} FAIL, "
                     f"{counts[UNPROVABLE]} UNPROVABLE.")
    if not claims_mode:
        lines.append("claims: none supplied — data-consistency and reference computation only; "
                     "no statement is made about any implementation's reported metrics.")
    if metadata_warnings:
        lines.append("metadata warnings: " + "; ".join(metadata_warnings))
    return "\n".join(lines), counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="agentmeasure", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("conformance")
    c.add_argument("--fixture", required=True, help="FMT-002 funnel-event JSONL (caller's file)")
    c.add_argument("--metadata", default=None, help="optional sidecar metadata JSON")
    c.add_argument("--claims", default=None, help="optional observed-claims JSON")
    c.add_argument("--json", dest="json_out", default=None, help="also write machine-readable JSON here")
    c.add_argument("--require", default="", help="comma-separated invariant ids that must be PROVEN")

    sub.add_parser("selftest")

    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return selftest()

    try:
        raw = Path(args.fixture).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2
    events, errors = check_schema_events(raw)
    if errors:
        print("fixture failed FMT-002 validation:", file=sys.stderr)
        for e in errors[:10]:
            print("  " + e, file=sys.stderr)
        return 2
    if not events:
        print("fixture contains no valid events", file=sys.stderr)
        return 2
    try:
        metadata, md_warn = load_metadata(args.metadata)
        claims = load_claims(args.claims)
    except (OSError, json.JSONDecodeError) as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2

    results = evaluate(events, claims)
    text, counts = human_report(results, md_warn, claims is not None, REGISTRY)
    print(text)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "pack": REGISTRY["pack_version"], "fixture": args.fixture,
            "counts": counts, "results": results,
            "claims_mode": claims is not None,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    required = [x.strip() for x in args.require.split(",") if x.strip()]
    unproven_required = []
    for inv in required:
        for r in results:
            v = r.get(inv, {})
            if v.get("verdict") != PASS:
                unproven_required.append(f"{inv}={v.get('verdict', 'missing')}")
    if counts.get(FAIL, 0) > 0:
        return 1
    if unproven_required:
        print("required invariants not proven: " + ", ".join(unproven_required), file=sys.stderr)
        return 1
    return 0


def selftest() -> int:
    """Contract C1: selftest uses the repository's own fixtures and never
    caller input. Three acceptance cases from the AM-16 contract."""
    vec = ROOT / "conformance" / "vectors" / "external" / "urusilla-002"
    events = [json.loads(l) for l in
              (vec / "agentmeasure_urusilla_fixture_002.events.jsonl").read_text().splitlines() if l.strip()]
    ok = True

    def expect(name, cond, detail=""):
        nonlocal ok
        print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if not cond and detail else ""))
        ok = ok and cond

    # case 1: correct claims → operation-grain PASS
    r = evaluate(events, {"median_steps_per_operation": 2.5})[0]
    expect("correct claims (2.5/2) → PASS", r["operation-grain"]["verdict"] == PASS)

    # case 2: wrong claims (the pre-fix AgentMeasure number) → FAIL
    r = evaluate(events, {"median_steps_per_operation": 5.0})[0]
    expect("wrong claims (5.0 assignment grain) → FAIL", r["operation-grain"]["verdict"] == FAIL)

    # case 3: strip operation declarations → UNPROVABLE, refused inference
    no_decl = [e for e in events if e.get("event") != "operation_result"]
    r = evaluate(no_decl, None)[0]
    expect("missing operation evidence → UNPROVABLE",
           r["execution-grain"]["verdict"] == UNPROVABLE and r["retry-reconciliation"]["verdict"] == UNPROVABLE)

    # case 4: reconciliation tamper → FAIL with reasons
    import copy
    tampered = copy.deepcopy(events)
    for e in tampered:
        if e.get("event") == "operation_result":
            e["attempts"] = 9
            break
    r = evaluate(tampered, None)[0]
    expect("contradictory declaration → FAIL", r["retry-reconciliation"]["verdict"] == FAIL)

    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
