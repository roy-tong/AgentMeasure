#!/usr/bin/env python3
"""External fixture conformance: chenhz01-001 — availability certification (#11).

Source: AgentMeasure issue #11 (Clarify Result Consumption). The two-state
ontology (availability vs influence) and the compaction boundary are
@gunjanjaswal's; the trace-side hash certification is @chenhz01's; the
canonicalized-content + field-path + four-value axis is @roy-tong's. This
fixture is the first availability vector: one synthetic trace whose four tool
results each meet a different certification outcome, so a compaction-aware
implementation can be tested against all four at once.

Certification axis (per result, orthogonal to the State-B influence axis):
  verbatim      the result's canonicalized content is embedded in the next
                model request -> State A certified (observability: TRUE);
  summary-embed only a lossy projection reached the request -> weak influence
                evidence, NOT availability, its own bucket (FALSE for A);
  absent        a request left, the result is nowhere in it (FALSE);
  unreachable   no request left the framework -> UNOBSERVABLE, excluded from
                the denominator, never counted FALSE (invariant 17).

Guards:
  1. schema   — every event validates under FMT-002;
  2. core     — aggregate() reproduces the naive boolean consumption_rate
                (1/4): the collapse the four-value axis corrects;
  3. cert     — certification recomputed from the raw trace_context (canonical
                field-walk) reproduces every event's x_availability and the
                expected four-bucket breakdown;
  4. reserial — a raw byte/substring certifier MISSES op1 (re-serialized JSON
                string) where the canonical field-walk certifies it verbatim;
  5. boundary — the forbid list holds: summary-embed is not State A and not
                absent; unreachable is excluded, never collapsed to FALSE;
  6. collapse — mislabeling unreachable as absent (UNOBSERVABLE -> FALSE)
                changes the denominator; the vector must make that detectable.

Claim boundary: synthetic conformance fixture authored for #11 — not an
endorsement, an external reproduction, or a real runtime observation.

Exit 0 = all guards pass.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab"))
from agentmeasure_lab.analysis import aggregate  # noqa: E402
from agentmeasure_lab.schemas import SchemaError, validate  # noqa: E402

VEC = ROOT / "conformance" / "vectors" / "external" / "chenhz01-001"
EVENTS_FILE = VEC / "agentmeasure_chenhz01_fixture_001.events.jsonl"
EXPECTED_FILE = VEC / "agentmeasure_chenhz01_fixture_001.expected.json"
CONTEXT_FILE = VEC / "agentmeasure_chenhz01_fixture_001.trace_context.json"
SCHEMA_FILE = ROOT / "lab" / "schemas" / "funnel-event.schema.json"

fails: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hcontent(o) -> str:
    return "sha256:" + hashlib.sha256(canon(o).encode("utf-8")).hexdigest()


def certify_canonical(op: str, ctx: dict):
    """Recompute certification from raw inputs: canonicalize each field value,
    compare content hashes, record the field path. Independent of x_availability."""
    results = ctx["results"]
    req = ctx["next_request"][op]
    if not req["emitted"]:
        return "unreachable", None
    target = hcontent(results[op]["content"])
    for i, m in enumerate(req["messages"] or []):
        val = m.get("content")
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
            except Exception:
                parsed = None
            if parsed is not None and hcontent(parsed) == target:
                return "verbatim", f"messages[{i}].content"
    if ctx["embed_form"][op] == "summary":
        return "summary-embed", ctx["embedded_at"][op]
    return "absent", None


def certify_raw_substring(op: str, ctx: dict) -> str:
    """Naive certifier: substring of the canonical result in the re-serialized
    request blob. Breaks on re-serialization — present only to be caught."""
    results = ctx["results"]
    req = ctx["next_request"][op]
    if not req["emitted"]:
        return "unreachable"
    blob = canon(req)
    if canon(results[op]["content"]) in blob:
        return "verbatim"
    return "summary-embed" if ctx["embed_form"][op] == "summary" else "absent"


def main() -> int:
    events = [json.loads(l) for l in EVENTS_FILE.read_text().splitlines() if l.strip()]
    expected = json.loads(EXPECTED_FILE.read_text())
    ctx = json.loads(CONTEXT_FILE.read_text())
    schema = json.loads(SCHEMA_FILE.read_text())

    print("chenhz01-001 guard 1: schema validation (FMT-002)")
    for i, ev in enumerate(events, 1):
        try:
            validate(ev, schema)
        except SchemaError as e:
            check(f"event {i} valid", False, str(e))
    check(f"{len(events)} events valid under FMT-002", True)

    print("chenhz01-001 guard 2: core boolean consumption_rate (the collapse)")
    cell = aggregate(events)[("availability-cert",)]
    ce = expected["core_expected_metrics"]
    check(f"operations == {ce['operations']}", cell["operations"] == ce["operations"], str(cell["operations"]))
    cr = cell["consumption_rate"]
    check(f"consumption_rate == {ce['consumption_rate']['value']} (= {ce['consumption_rate']['numerator']}/{ce['consumption_rate']['denominator']})",
          cr["value"] == ce["consumption_rate"]["value"]
          and cr["numerator"] == ce["consumption_rate"]["numerator"]
          and cr["denominator"] == ce["consumption_rate"]["denominator"],
          f"got {cr['numerator']}/{cr['denominator']}={cr['value']}")
    check("operation reconciliation passed", cell["operation_reconciliation"]["status"] == "passed",
          cell["operation_reconciliation"]["status"])

    print("chenhz01-001 guard 3: certification recomputed from raw trace_context")
    consumptions = {e["operation_index"]: e for e in events if e["event"] == "consumption"}
    buckets = {"verbatim": 0, "summary-embed": 0, "absent": 0, "unreachable": 0}
    for op_str in ("1", "2", "3", "4"):
        op = int(op_str)
        cert, path = certify_canonical(op_str, ctx)
        buckets[cert] += 1
        xa = consumptions[op]["x_availability"]
        check(f"op{op} certification == x_availability ({cert})", xa["certification"] == cert, xa["certification"])
        check(f"op{op} field_path == {path}", xa["embedded_field_path"] == path, str(xa["embedded_field_path"]))
        check(f"op{op} content hash matches", xa["result_content_hash"] == hcontent(ctx["results"][op_str]["content"]))
        check(f"op{op} consumed boolean == state_a", consumptions[op]["consumed"] == (cert == "verbatim"))
    exp_bd = expected["availability_certification"]["breakdown"]
    for k, v in buckets.items():
        check(f"breakdown[{k}] == {v}", exp_bd[k.replace('-', '_')] == v, str(exp_bd[k.replace('-', '_')]))

    print("chenhz01-001 guard 4: re-serialization false negative on op1")
    raw1 = certify_raw_substring("1", ctx)
    good1, _ = certify_canonical("1", ctx)
    check("raw substring misses op1 (absent)", raw1 == "absent", raw1)
    check("canonical field-walk certifies op1 (verbatim)", good1 == "verbatim", good1)

    print("chenhz01-001 guard 5: bucket boundary (forbid list)")
    sa = expected["availability_certification"]["state_a_rate"]
    judgeable = buckets["verbatim"] + buckets["summary-embed"] + buckets["absent"]
    check("State-A denominator excludes unreachable", sa["denominator"] == judgeable and sa["denominator"] == 3,
          str(sa["denominator"]))
    check("State-A numerator counts verbatim only", sa["numerator"] == buckets["verbatim"] == 1)
    check("summary-embed is not State A", consumptions[2]["x_availability"]["state_a_certified"] is False
          and consumptions[2]["consumed"] is False)
    check("summary-embed is its own bucket, not absent",
          consumptions[2]["x_availability"]["certification"] == "summary-embed")
    check("unreachable maps to UNOBSERVABLE, not FALSE",
          consumptions[4]["x_availability"]["observability_state"] == "UNOBSERVABLE")

    print("chenhz01-001 guard 6: collapse is detectable (UNOBSERVABLE -> FALSE)")
    # Mislabel the unreachable result as absent: invariant 17 violation. The
    # judgeable denominator would wrongly grow from 3 to 4 — the vector must
    # make that change observable rather than silent.
    collapsed = dict(buckets)
    collapsed["unreachable"] -= 1
    collapsed["absent"] += 1
    collapsed_den = collapsed["verbatim"] + collapsed["summary-embed"] + collapsed["absent"]
    check("collapsing unreachable->absent changes the denominator (3 -> 4)",
          collapsed_den == 4 and collapsed_den != judgeable, str(collapsed_den))

    if fails:
        print(f"\nCHENHZ01-001 CONFORMANCE FAIL: {len(fails)} guard(s): {', '.join(fails)}")
        return 1
    print("\nCHENHZ01-001 CONFORMANCE PASS: schema + core collapse + cert + re-serial + boundary + collapse-detectable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
