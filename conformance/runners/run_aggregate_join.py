#!/usr/bin/env python3
"""Evidence-case conformance: aggregate-join integrity (counting's second edge).

Origin: Metrecept (iwasinnam2 / Ivan Karpusheff) — the 2026-10-09 incident
(edge cache HIT served without the session tag; the SIGNED session aggregate
said cache_hits=0) and the six-questions answer of 2026-10-12 proposing the
join vector: N crossing receipts and the one aggregate they belong to;
conformance is event_count == N and amount == sum. The framing "a signature
made the absence look like proof" is Verovo's sentence; his words are
the confirmation that it is the right one (attribution kept separate per his
conditions). Fixture and wording: Verovo (synthetic). His production
cut is reserved as external/iwasinnam-004.

This pins VSS-1 clause S-9 (aggregate reconciliation): an aggregate is
evidence only if it reconciles to its members by count and by sum.

Guards:
  1. shape     — every member carries the money identity (unique
                 meter_event_id, kind, digests, integer micro-USD amount);
  2. join      — session aggregate == exactly the tagged members by count
                 and sum; ledger aggregate == all members;
  3. absence   — removing one tagged member MUST fail reconciliation (the
                 event the aggregator never received — the vector exists to
                 make that failure loud);
  4. untagged  — pushing the untagged bypass into the session aggregate
                 fails (nothing is invented);
  5. duplicate — a duplicated member fails (dedup must not erase genuine
                 members either — mirror failure);
  6. drift     — tampering one member's amount fails;
  7. signature — the aggregate's signature is valid and its counters are
                 self-consistent, yet every mutation above still fails the
                 join: signature verification does not discharge the join
                 obligation.

Claim boundary: synthetic conformance fixture — not an endorsement, not an
external reproduction, not a production artifact.

Exit 0 = all guards pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "conformance" / "evidence" / "aggregate-join-integrity" / "fixture.json"

fails: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'✓' if cond else '✗'} {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def reconcile(aggregate: dict, members: list) -> dict:
    """The join: an aggregate is evidence only if event_count == len(members)
    and amount == sum(members). Returns a verdict object, never raises."""
    count_ok = aggregate["event_count"] == len(members)
    sum_ok = aggregate["amount_usd_micro"] == sum(m["amount_usd_micro"] for m in members)
    return {"status": "passed" if (count_ok and sum_ok) else "failed",
            "count_ok": count_ok, "sum_ok": sum_ok}


def main() -> int:
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    members = fx["members"]
    session_agg = fx["session_aggregate"]
    ledger_agg = fx["ledger_aggregate"]
    tagged = [m for m in members if m["session_tag"] == "present"]

    print("aggregate-join guard 1: shape (money identity on every member)")
    check("fixture has members", len(members) > 0, str(len(members)))
    ids = [m["meter_event_id"] for m in members]
    check("meter_event_id unique", len(set(ids)) == len(ids))
    for m in members:
        ok = all(m.get(k) for k in ("meter_event_id", "kind", "request_sha256", "response_sha256")) \
            and isinstance(m.get("amount_usd_micro"), int) \
            and m.get("session_tag") in ("present", "absent")
        check(f"{m['meter_event_id']} identity complete", ok, json.dumps(m)[:120])

    print("aggregate-join guard 2: join (aggregate == its members, count and sum)")
    sj = reconcile(session_agg, tagged)
    check(f"session aggregate reconciles over tagged members "
          f"({session_agg['event_count']} events, {session_agg['amount_usd_micro']} micro-USD)",
          sj["status"] == "passed", str(sj))
    lj = reconcile(ledger_agg, members)
    check(f"ledger aggregate reconciles over ALL members ({ledger_agg['event_count']} events)",
          lj["status"] == "passed", str(lj))
    check("untagged member exists in fixture (the 2026-10-09 shape)",
          any(m["session_tag"] == "absent" for m in members))

    print("aggregate-join guard 3: absence fails (member the aggregator never received)")
    dropped = [m for m in tagged if m["meter_event_id"] != "me-002"]
    r = reconcile(session_agg, dropped)
    check("dropping a tagged member fails the join", r["status"] == "failed", str(r))
    # The failure mode the vector exists for: the aggregate is unchanged,
    # well-formed, self-consistent — only the member set knows it is wrong.
    check("the unchanged aggregate looks self-consistent on its own "
          "(signature valid, counters consistent)",
          session_agg["signature"] == "valid-demo"
          and session_agg["cache_hits"] + session_agg["cache_misses"] == session_agg["event_count"])

    print("aggregate-join guard 4: untagged is not invented into the session")
    r = reconcile(session_agg, members)  # naive join: all members into session
    check("joining ALL members into the session aggregate fails", r["status"] == "failed", str(r))

    print("aggregate-join guard 5: duplication fails")
    dup = tagged + [dict(tagged[1])]
    r = reconcile(session_agg, dup)
    check("a duplicated member fails the join", r["status"] == "failed", str(r))

    print("aggregate-join guard 6: sum drift fails")
    tampered = [dict(m) for m in tagged]
    tampered[0]["amount_usd_micro"] += 1
    r = reconcile(session_agg, tampered)
    check("tampering one member's amount fails", r["status"] == "failed", str(r))

    print("aggregate-join guard 7: signature is not the join")
    # A "signature-verifying implementation" accepts the aggregate as-is:
    # counters self-consistent, signature valid. The join must still be
    # demanded — run the three mutations against it and require failure.
    sig_only_passes = (session_agg["signature"] == "valid-demo")
    mutations_fail = all(
        reconcile(session_agg, m)["status"] == "failed"
        for m in (dropped, members, dup, tampered)
    )
    check("aggregate passes signature checks yet fails every member-level mutation",
          sig_only_passes and mutations_fail)

    if fails:
        print(f"\nAGGREGATE-JOIN CONFORMANCE FAIL: {len(fails)} guard(s): {', '.join(fails)}")
        return 1
    print("\nAGGREGATE-JOIN CONFORMANCE PASS: shape + join + absence-fails + untagged + duplicate + drift + signature-is-not-the-join")
    return 0


if __name__ == "__main__":
    sys.exit(main())
