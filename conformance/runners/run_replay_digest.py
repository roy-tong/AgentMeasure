#!/usr/bin/env python3
"""Evidence-case conformance: replay-digest parity (cost preservation as bytes).

Origin: the replay vector proposed by Metrecept (iwasinnam2 / Ivan
Karpusheff), six-questions answer 2026-10-12 — the fill and the replay of
the same request, from two planes, with equal request and response digests,
and a changed payload alongside with its own digests. Fixture and wording:
Verovo (synthetic). Production cut reserved as external/iwasinnam-005.

Companion to run_aggregate_join.py: that guards the aggregate edge of
counting integrity; this guards the crossing edge.

Guards:
  1. parity       — fill and replay of the same request carry equal request
                    and response digests under canonicalization;
  2. assembly     — different chunkings of the same stream assemble to the
                    same body digest under the published rule;
  3. distinctness — the changed payload yields different request AND
                    response digests;
  4. no-shortcut  — raw wire bytes of fill and replay differ, so a naive
                    raw-byte comparison fails to certify the replay
                    (canonicalization is load-bearing);
  5. no-merge     — replay is its own metered crossing (distinct
                    meter_event_id from the fill; no N-to-one collapse).

Claim boundary: synthetic conformance fixture — not an endorsement, not an
external reproduction, not a production artifact.

Exit 0 = all guards pass.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "conformance" / "evidence" / "replay-digest-parity" / "fixture.json"

fails: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def canon(o) -> str:
    """The published canonical-JSON rule: sorted keys, no whitespace, UTF-8."""
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_digest(crossing: dict) -> str:
    return "sha256:" + hashlib.sha256(canon(crossing["request_content"]).encode("utf-8")).hexdigest()


def response_digest(crossing: dict) -> str:
    """The published stream-assembly rule: concatenate text deltas in order."""
    body = "".join(crossing["response_chunks"])
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def main() -> int:
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    by_role = {c["role"]: c for c in fx["crossings"]}
    fill, replay, changed = by_role["fill"], by_role["replay"], by_role["changed-payload"]

    print("replay-digest guard 1: parity (same request, two planes, equal digests)")
    check(f"request digest equal: {request_digest(fill)[:23]}…",
          request_digest(fill) == request_digest(replay),
          f"{request_digest(fill)[:16]} vs {request_digest(replay)[:16]}")
    check("response digest equal", response_digest(fill) == response_digest(replay))

    print("replay-digest guard 2: assembly rule (different chunkings, same body)")
    check("fill chunks differ from replay chunks (order/shape)",
          fill["response_chunks"] != replay["response_chunks"])
    assembled_fill = "".join(fill["response_chunks"])
    assembled_replay = "".join(replay["response_chunks"])
    check(f"assembled bodies identical ({assembled_fill!r})",
          assembled_fill == assembled_replay and hashlib.sha256(assembled_fill.encode()).hexdigest()
          == hashlib.sha256(assembled_replay.encode()).hexdigest())

    print("replay-digest guard 3: distinctness (changed payload differs both ways)")
    check("request digest differs", request_digest(fill) != request_digest(changed))
    check("response digest differs", response_digest(fill) != response_digest(changed))

    print("replay-digest guard 4: no raw-bytes shortcut (canonicalization is load-bearing)")
    wire_fill = fill["request_wire"]
    wire_replay = replay["request_wire"]
    # both wires parse to the same logical request, but the bytes differ
    same_logical = json.loads(wire_fill) == json.loads(wire_replay)
    check("raw wire bytes differ between planes", wire_fill != wire_replay)
    check("both wires parse to the same logical request", same_logical)
    check("canonical digests still match despite differing wires",
          request_digest(fill) == request_digest(replay))

    print("replay-digest guard 5: no merge (replay is its own crossing)")
    ids = [c["meter_event_id"] for c in fx["crossings"]]
    check("fill and replay have distinct meter_event_ids",
          fill["meter_event_id"] != replay["meter_event_id"])
    check("all meter_event_ids unique in the ledger", len(set(ids)) == len(ids))

    if fails:
        print(f"\nREPLAY-DIGEST CONFORMANCE FAIL: {len(fails)} guard(s): {', '.join(fails)}")
        return 1
    print("\nREPLAY-DIGEST CONFORMANCE PASS: parity + assembly + distinctness + no-shortcut + no-merge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
