#!/usr/bin/env python3
"""Run the langfuse-demo-traces evidence case end to end.

  1. adapter: source/*.json -> canonical/*.canonical.jsonl
  2. schema validation of every canonical line (fail loudly)
  3. canonical pipeline, run twice:
       A) fail-closed  (derive_operations default — explicit-only)
       B) structural-experimental (derive_operations enable_structural=True;
          disclosed as experimental, never headline)
  4. sibling-pattern scan on the raw exports (retry vs loop indistinguishable)
  5. write results.json and print the coverage-first summary

Reproduces every number quoted in README.md.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent.parent  # conformance/evidence/<case> -> repo root
sys.path.insert(0, str(REPO / "reference"))

from collector.aggregator.aggregator import compute  # noqa: E402
from collector.correlator.correlator import (  # noqa: E402
    connect,
    derive_operations,
    match_invocations,
)
from collector.ingest import ingest_canonical_jsonl  # noqa: E402

PROJECT = "langfuse/demo-seed-traces"
SINCE_DAYS = 420  # pinned traces span 2025-08..2025-12; window must include them


def run_pipeline(structural: bool) -> dict:
    db = HERE / ("case_%s.db" % ("structural" if structural else "failclosed"))
    if db.exists():
        db.unlink()
    conn = connect(db)
    accepted = 0
    for f in sorted((HERE / "canonical").glob("*.canonical.jsonl")):
        r = ingest_canonical_jsonl(conn, f, source="evidence-case",
                                   project_id=PROJECT, principal="concierge")
        accepted += r["accepted"]
        if r["rejected"]:
            raise SystemExit(f"ingest rejected rows in {f.name}: {r['reject_reasons']}")
    match_invocations(conn)
    derivation = derive_operations(conn, enable_structural=structural)
    metrics = compute(conn, PROJECT, days=SINCE_DAYS)
    conn.close()
    return {"accepted": accepted, "derivation": derivation, "metrics": metrics}


def sibling_patterns() -> list:
    facts = []
    for f in sorted((HERE / "source").glob("*.json")):
        obs = json.loads(f.read_text()).get("observations", [])
        by_parent: dict = {}
        for o in obs:
            by_parent.setdefault((o.get("parentObservationId"), o["name"]), []).append(o)
        count = 0
        for (parent, name), group in by_parent.items():
            if len(group) > 1:
                count += 1
                facts.append({
                    "trace": f.stem,
                    "pattern": f"{len(group)}x '{name}' under same parent",
                    "verdict": "retry OR loop step — indistinguishable without declared boundary",
                })
        has_usage = sum(1 for o in obs if o.get("usage"))
        facts.append({
            "trace": f.stem,
            "pattern": "token usage in export",
            "verdict": f"PRESENT ({has_usage}/{len(obs)})" if has_usage else f"ABSENT (0/{len(obs)})",
        })
    return facts


def main() -> int:
    src = HERE / "source"
    if not src.exists() or not list(src.glob("*.json")):
        raise SystemExit("source/ is empty — run: python3 fetch_source.py")
    import adapter_langfuse_export as ad  # noqa: E402  (adapter as library)
    ad.main(src)

    # schema validation (fail loudly)
    for f in sorted((HERE / "canonical").glob("*.canonical.jsonl")):
        r = subprocess.run(
            [sys.executable, str(REPO / "schemas" / "validate_jsonl.py"), str(f)],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"schema validation failed for {f.name}:\n{r.stdout}{r.stderr}")
        print(f"schema OK: {f.name}")

    a = run_pipeline(structural=False)
    b = run_pipeline(structural=True)
    out = {
        "artifact": "langfuse demo-seed framework traces (3 files, pinned)",
        "fail_closed": a,
        "structural_experimental": b,
        "raw_patterns": sibling_patterns(),
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=2))

    m = a["metrics"]
    print("\n=== coverage-first summary (fail-closed) ===")
    print(f"attempts: {m['attempts']}  resolved operations: {m['resolved_operations']}")
    print(f"operation resolution coverage: {m['operation_resolution_coverage']}")
    print(f"attempt-as-operation count: {m['legacy_attempt_equivalent']}")
    print("\n=== sibling patterns ===")
    for f_ in out["raw_patterns"]:
        print(f"  {f_['trace']:28s} {f_['pattern']:42s} {f_['verdict']}")
    print("\nwrote results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
