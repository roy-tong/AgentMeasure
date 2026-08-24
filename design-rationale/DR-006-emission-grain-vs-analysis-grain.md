# DR-006 — Emission Grain ≠ Analysis Grain

- Status: Adopted as design rationale (Draft 0.4.4)
- Date: 2026-08-25
- External evidence: Avi Seth (direct reply 2026-08-24: operation is an additive grouping,
  "a stable id to group by," not "the unit you emit"); Arthi (attempts = append-only facts,
  operation = view); converging with Eren / Darien retry-identity threads

## Problem

Two questions were routinely conflated: (a) is an operation a useful grouping for analysis,
and (b) should the operation replace the attempt as the primary emitted telemetry unit.
Answering yes to (a) does not license yes to (b). If the emission layer collapses attempts
into operations at collection time, the debugging facts — 429 vs timeout vs slow-but-successful —
die before analysis and cannot be reconstructed.

## Decision

**Attempt is the emission/observation grain. Operation is the analysis grain.**

| Grain | Unit of | Used for |
|---|---|---|
| Attempt | emission (append-only execution fact) | debugging, raw usage, failure analysis, cost evidence |
| Operation | analysis (stable grouping key) | logical success, retry inflation, accounting grouping |
| Task | end-to-end outcome | outcome attribution |

1. Emitted telemetry MUST NOT collapse attempts into operations. `operation_id` is additive:
   a stable key to group by, never the unit you emit.
2. Operation-level metrics are **views** computed over attempt facts, never replacements.
3. The OTel / Logfire shape maps naturally: parent span = logical operation,
   child spans = retry attempts. The standard aligns with it rather than inventing
   a competing emission shape.

```text
operation-A (analysis grain)
│
├── attempt-1 → 429        (emission grain, append-only)
├── attempt-2 → timeout    (emission grain, append-only)
└── attempt-3 → success    (emission grain, append-only)
```

## Implications

- Builds on DR-001 (attempt ledger; operation resolution as a derived view).
- Conformance case backlog: the 3-attempt fixture above — `attempt_count = 3`,
  `attempt_success_rate = 33.3%`, `operation_count = 1`, `operation_success_rate = 100%`,
  attempt facts intact, operation groups but does not replace.
- Retry inflation and logical success are computed claims and MUST be labeled as views,
  not observed facts (see DR-002 evidence discipline).

## Rejected alternatives

- Operation as the primary emitted unit — rejected: irreversibly discards retry
  distinctions at collection time.
- Attempts only, no operation linkage — rejected: loses accounting grouping and invites
  retry-inflated billing and success-rate confusion.
