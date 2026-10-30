# Independent recomputation receipt — iwasinnam-004 (join) / iwasinnam-005 (replay)

Date: 2026-10-16. Recomputed by Verovo (Roy Tong), returned in the
originating mail thread as promised on 2026-10-15. Free conformance
collaboration — no charge, per the standing agreement. The claim boundary for
each fixture is the contributor's `CLAIM_BOUNDARY.md`, carried verbatim next to
the data; this receipt states what WE recomputed and what we did not.

## Method (independence statement)

- Every verdict is recomputed from the raw fixture bytes and the key directory.
  The fixtures' embedded `guards` blocks were NOT read for any verdict — those
  are the contributor's own claims.
- Signatures: Ed25519 (EdDSA) over the JWS signing input, public key fetched
  live from `api.metrecept.co.uk/.well-known/http-message-signatures-directory`
  on 2026-10-16 (live fetch matched the pinned copy byte-for-byte); `kid`
  checked against a locally recomputed RFC 7638 thumbprint.
- Money: `Decimal` arithmetic; no float accumulation.
- Canonical JSON (`response_sha256` rule, from the -005 field semantics):
  sorted keys, no whitespace, UTF-8, non-ASCII unescaped.
- Stream assembly implemented independently from the raw SSE lines (content
  deltas concatenated; role/finish from the deltas; usage from the last
  usage-bearing chunk), not by running the contributor's script.

## Results — 21/21 checks pass, 0 hard failures

Runner: `conformance/runners/run_external_fixture_004_005.py` (exit 0).

### iwasinnam-004 — join vector

| id | check | result |
|---|---|---|
| A1 | all 5 JWS verify vs the live key directory; kid = recomputed RFC 7638 thumbprint | PASS |
| A2 | `event_count` (3) == number of tagged member receipts | PASS |
| A3 | session `pipe_usd` (0.009) == Decimal sum of tagged members (0.0015+0.006+0.0015) | PASS |
| A4 | per-kind counts match members (hits 1, misses 2, bypasses/api/fetches 0) | PASS |
| A5 | untagged bypass: metered with own `meter_event_id`, correctly ABSENT from the aggregate (sum with it would be 0.0105) | PASS |
| A6 | 4 crossings, 4 distinct `meter_event_id`s — cover, not collapse | PASS |
| A7 | `session_sha256` == sha256("iwasinnam-004-join-20261013b") | PASS |
| A8 | raw session id appears in no signed payload | PASS |
| M1 | drop a member → join fails while the session signature still verifies | PASS |
| M2 | reprice a member → join fails, signature still verifies | PASS |
| M3 | insert the bypass into the member set → join fails | PASS |

### iwasinnam-005 — replay vector

| id | check | result |
|---|---|---|
| B1 | all 5 JWS verify vs the live key directory | PASS |
| B2 | JSON fill and replay share request and response digests | PASS |
| B3 | changed payload carries different request AND response digests | PASS |
| B4 | two different planes signed fill (python) and replay (rust-edge) | PASS |
| B5 | response_sha256 recomputed from `served_body` under the canonical rule — matches all 3 JSON receipts | PASS |
| B6 | streamed fill (15 chunks) and replay (5 chunks) share both digests | PASS |
| B7 | our independent SSE assembly reproduces BOTH streamed receipts' `response_sha256` (80f1bfd2…) | PASS |
| B8 | 5 crossings, 5 distinct `meter_event_id`s — a replay is summed, never merged | PASS |
| BNDRY | JSON digest ≠ streamed digest of the same body — EXPECTED per the claim boundary (a stream drops provider extras); recorded, not failed | recorded |
| M4 | one mutated served byte → recomputed digest leaves the receipt | PASS |

### Public clock (read 2026-10-16)

- Session receipt signature leaf answers at slot `20261013T22Z`, index 14 —
  matches the fixture's clock block.
- The two fixture files answer as external leaves at index 20 and 21 of the
  same slot — as stated in the contributor's cover note.
- Boundary: we record the clock's ANSWERS (slot/index/leaf match). We did not
  re-derive the Merkle root from the returned proof chains; that is not
  claimed here.

## What this receipt does not claim

- No endorsement of Metrecept, no certification of the live service, and
  nothing about crossings outside this run.
- The cross-carriage difference (JSON vs streamed digest) is a stated boundary
  of the fixture, not a finding against it.
- Per the 2026-10-15 correction: this collaboration is free; nothing here is a
  paid engagement or a purchase.

## Reproduce

```bash
python3 conformance/runners/run_external_fixture_004_005.py --live
```
