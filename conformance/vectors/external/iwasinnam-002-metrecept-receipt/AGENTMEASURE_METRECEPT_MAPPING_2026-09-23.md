# AgentMeasure ↔ Metrecept signed receipt mapping

Date: 2026-09-23

Status: external production artifact contributed in BerriAI/litellm#39057 by
iwasinnam2 (Ivan): a real minted Ed25519 JWS receipt (demo key) from the
Metrecept signing path, with decoded payload, field semantics, five explicit
limits, and a stranger-verification path. Project-authored projection into the
conformance vector format at the contributor's request ("please encode these
explicitly in the fixture").

## Independent convergence with AMS-1

Metrecept's receipt semantics converge with the AMS-1 posture without contact:

| Metrecept concept | AMS-1 counterpart |
|---|---|
| receipt signs pipe rent only (L1) | two-rail separation: billed rail vs provider-side columns |
| hit-only counterfactual in a separate unsigned surface (L2) | evidence posture axis: signed/settlement-grade vs estimate-only labelled |
| per-crossing meter_event_id, no N-to-one collapse | counting integrity: one billable event per crossing |
| request_sha256 exact-match identity | replay identity; semantic variants are misses |
| iat is a claim, not a when-proof (L4) | provenance fields are claims; when-proofs need their own mechanism |

## Fixture boundary

- The decoded payload is the fixture level. Signature verification is a
  production-path property, not a fixture one; the stranger-verifier
  (public JWKS, triple-implemented) is documented for completeness.
- Companion vector: external/iwasinnam-001 (hop-replay ledger, request-1/2).
  Ivan offered a follow-up with the session-kind aggregate shape (one signed
  receipt over N crossings) — slot reserved as iwasinnam-003 if delivered.
