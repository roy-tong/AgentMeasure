# Replay-Digest Parity (cost preservation stated as bytes)

> Origin: the replay vector proposed by Metrecept (iwasinnam2 / Ivan
> Karpusheff) in his six-questions answer (2026-10-12): the fill and the
> replay of the same request, from two planes, with equal request and
> response digests, and a changed payload alongside with its own digests —
> *cost-preservation stated as bytes: a replay is the same answer, and the
> record proves it rather than asserts it.* Fixture and wording: Verovo
> (synthetic). His production cut is reserved as `external/iwasinnam-005`,
> in flight.
>
> Synthetic, offline conformance evidence. Asserts digest relations between
> declared quantities only. Not an endorsement, not a production artifact.

## The invariant

> **A cache replay may only claim the original answer's cost basis if the
> per-crossing records prove byte-equality: same request digest (canonical
> form) and same response digest (assembled by the published stream rule).
> Different payload ⇒ different digests — no exceptions, no defaulting.**

This is the member-level twin of
[aggregate-join-integrity](../aggregate-join-integrity/README.md): the join
guards the aggregate edge, this guards the crossing edge.

## The fixture

Three crossings: `rp-001` fill (control plane), `rp-002` replay (edge plane)
of the same request — the two carry the same logical content in **different
raw wire serializations**, and their streamed responses arrive in **different
chunkings** of the same body. `rp-003` is a one-character-changed payload with
its own digests.

## Guards (run_replay_digest.py)

1. **parity** — fill and replay of the same request carry equal request and
   response digests (canonicalization makes wire-format differences
   irrelevant);
2. **assembly rule** — different chunkings of the same stream assemble to
   the same body digest under the published rule;
3. **distinctness** — the changed payload produces different request AND
   response digests (a digest scheme that collides here is worthless);
4. **no raw-bytes shortcut** — the raw wire bytes of fill and replay differ
   (so a naive raw-byte comparison would have failed to certify the replay:
   canonicalization is load-bearing, same lesson as the re-serialization
   guard in chenhz01-001);
5. **no merge** — the replay is its own metered crossing: distinct
   `meter_event_id` from the fill, both present in the ledger (no N-to-one
   collapse; VSS-1 L5 discipline).
