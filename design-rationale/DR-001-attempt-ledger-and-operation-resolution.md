# DR-001 — Attempt Ledger and Operation Resolution

- Status: Adopted (Draft 0.4.4)
- Date: 2026-08-18
- External evidence: Arthi A (wrong-numbers / cachecheck), two technical replies

## Problem

AgentMeasure must answer "what is one agent operation". Early models treated operation as the
primary record and retry as an outcome value. External review showed: **consumption is an
attempt-level fact, intent is an operation-level semantics**; mixing the two units causes
double counting, cache mispricing and operation inflation, and becomes unauditable.

## Decision

1. Attempts are append-only, immutable factual records. Reconciliation never rewrites or merges them.
2. Operations are semantic views over attempts, never mutations.
3. Operation resolution carries provenance: status (resolved / unresolved / ambiguous) × method
   (explicit_operation_id / idempotency_key / cross_side_correlation / structural_inference / none),
   plus rule_id / rule_version / source_attempt_ids.
4. An inferred operation MUST NOT be observationally equivalent to a declared operation.
5. Ungrouped / unresolved attempts are first-class. When evidence is insufficient, preserve the
   attempts and refuse to manufacture the operation.

## Rejected alternatives

- Operation-as-single-grain (one unit for money and intent) — rejected: the two questions
  need different grains.
- Reconciliation that merges attempts into one operation record — rejected: loses auditability
  of per-attempt cost.

## Implications

- SDK schema: attempt gains `retry_of` relationship (replaces `outcome: retry`).
- Aggregator: reports resolution coverage and inferred share (METRICS M3.1).
- Vocabulary: `operation_resolution` status/method terms.

> Motivated in part by failure patterns documented in Arthi A's wrong-numbers corpus.
