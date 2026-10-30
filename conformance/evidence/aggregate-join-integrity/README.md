# Aggregate-Join Integrity (counting's second edge)

> Origin: the enforcement case reported by Metrecept (iwasinnam2 / Ivan
> Karpusheff) on 2026-10-09 — an edge cache HIT served without the caller's
> session tag, so the **signed** session aggregate said `cache_hits: 0`. The
> join semantics and the proposed vector are his (six-questions answer,
> 2026-10-12): N crossing receipts and the one aggregate they belong to;
> conformance is `event_count == N` and `amount == sum`. The framing sentence
> "a signature made the absence look like proof" is **Verovo's**
> (preamble, applied to his case); his words are the confirmation that it is
> the right one — attribution kept separate per his stated conditions. This
> fixture and its wording are ours; his production cut is offered for the
> external set (companion slot `external/iwasinnam-004`, in flight).
>
> This fixture is **synthetic, offline conformance evidence**. It asserts
> join relations between declared quantities only. It is not an endorsement,
> not a Metrecept production artifact, and not a statement about any specific
> implementation's current behavior.

## The invariant

Counting integrity has **two edges**:

1. count one event once (the classic dedup family);
2. count it **inside the right aggregate** — and a signed aggregate that
   passes signature verification is exactly where the second edge hides,
   because the signature is honest about the wrong total.

The checkable invariant:

> **An aggregate is evidence only if it reconciles to its member records by
> count and by sum. An aggregate that verifies on its own is a verified claim
> about the events the aggregator happened to see.**

## The fixture

Four metered crossings; three carry the session tag, one (a bypass, the
2026-10-09 shape) is metered but untagged. Two aggregates: the session cover
(3 events, 5000 micro-USD) and the ledger total (4 events, 5500 micro-USD).

## Guards (run_aggregate_join.py)

1. **shape** — every member has the money identity (unique `meter_event_id`,
   kind, request/response digests, integer amount);
2. **session-join** — session aggregate == exactly the tagged members, by
   count and by sum;
3. **absence fails** — remove one tagged member (the event the aggregator
   never received): reconciliation MUST fail; the vector exists to make that
   failure loud, not silent;
4. **untagged is not invented** — pushing the untagged bypass into the
   session aggregate fails the join (nothing is invented), while the ledger
   aggregate reconciles over all four;
5. **duplication fails** — a duplicated member must not reconcile (a naive
   dedup that erases genuine members is the mirror failure, see the
   maintainer-side counterexample in `registry/provider-mapping.md`);
6. **sum drift fails** — tampering one member's amount fails;
7. **signature is not the join** — the session aggregate carries a valid
   signature and self-consistent counters, yet every member-level mutation
   above still fails reconciliation: signature verification does not
   discharge the join obligation (VSS-1 S-9).
