# AgentMeasure ↔ Metrecept signed session-aggregate receipt mapping

Date: 2026-10-05

Status: external production artifact delivered in BerriAI/litellm#39057 by
iwasinnam2 (Ivan) on 2026-10-04, fulfilling the slot reserved in the
[-002 mapping](../iwasinnam-002-metrecept-receipt/AGENTMEASURE_METRECEPT_MAPPING_2026-09-23.md).
One Ed25519 JWS session-kind aggregate (demo key) minted read-time by the
Metrecept signing path (`src/at_utility/receipts.py::mint_session_receipt`)
over three already-ledgered crossings: one MISS, two HITs on a byte-identical
prompt. The decoded payload is the fixture level; the JWS verifies against the
gateway's public JWKS via `scripts/verify_receipt.py --base <gateway>`.

Credit: this fixture and the receipt semantics it encodes are **Metrecept's**
work (iwasinnam2 / Ivan), contributed for conformance use. The mapping below is
our projection, at the contributor's request.

## Independent convergence with AMS-1 at aggregate grain

| Metrecept limit (fixture `limits`) | AMS-1 counterpart |
|---|---|
| L1 pipe rent, not provider cost — `pipe_usd` signs only what the pipe billed | two-rail separation: billed rail vs provider-side columns |
| L2 counterfactual not in aggregate — `estimated_provider_avoided_usd` excluded from the signed surface, enforced at type level in `mint_ledger_statement_receipt()` | evidence posture axis: signed/settlement-grade vs estimate-only, boundary by construction not caller discipline |
| L3 aggregate is lossy by design — per-crossing model and cache-discount shape stay on per-crossing receipts | counting integrity vs judgment split: the cover asserts the sum, not the composition |
| L4 `iat` / `first_ts` / `last_ts` are claims, not when-proofs | provenance fields are claims; when-proofs need their own mechanism (Merkle clock leaf) |
| L5 cover, not collapse — N crossings keep distinct `meter_event_id`s; repeat hits are distinct metered crossings | one billable event per crossing; no N-to-one merge of retries/hits |
| L6 session id never raw — `session_sha256` only; membership checkable by rehash | provenance: identifiers appear as verifiable digests, not raw claims |

## Fixture boundary

- Decoded payload is the fixture level; signature verification is a
  production-path property (public JWKS, stranger-verifier documented in the
  fixture's `external_source`).
- Session-kind adds nothing contradictory to -002's stance: the aggregate is a
  signed cover over money identities (per-crossing receipts), and the estimate
  surface stays unsigned (`grade: estimate_only`, `signed: false`).
- Companion vectors: external/iwasinnam-001 (hop-replay ledger),
  external/iwasinnam-002-metrecept-receipt (per-request receipt).
