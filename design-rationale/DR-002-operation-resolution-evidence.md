# DR-002 — Operation Resolution Evidence

- Status: Adopted (Draft 0.4.4)
- Date: 2026-08-18
- External evidence: Arthi A (second reply); Alexey Vasilev (@Alvasilevv, sequence framing)

## Problem

When a runtime does not emit an operation_id, a measurement layer may infer one. Boundary
inference fails silently: merging two intents or splitting one produces a plausible operation
count with nothing raising. This is the same defect class as the wrong-numbers corpus.

## Decision

1. Declared operations when available; evidence-graded reconstruction only when defensible.
2. The evidence grade lives on the operation record itself, not in documentation.
3. The rule that produced the grouping is stored with the grouping (rule_id / rule_version),
   so a wrong boundary can be audited back to the heuristic.
4. Any operation-level metric reports its inferred fraction beside it.
5. When evidence is ambiguous, refuse to group: `unresolved` is first-class.
6. Over-splitting is safer than over-merging: an inflated operation count is visible, while
   merging contaminates every operation-level metric (success rate, value per op, cost per op).

## Implication

- Alexey's heuristic (same tool + same args + error window → retry; unc consumed output → probe)
  becomes an *experimental structural inference rule*, never truth, and stays off by default.

## Rejected alternatives

- Treating the structural heuristic as truth — rejected: it must stay an inference with
  explicit evidence grading.
