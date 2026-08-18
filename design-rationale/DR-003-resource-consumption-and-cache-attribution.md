# DR-003 — Resource Consumption and Cache Attribution

- Status: Adopted (Draft 0.4.4)
- Date: 2026-08-18
- External evidence: Vidit Ostwal (crewAI, cache tokens); OpenLIT PR discussion (reasoning tokens)

## Problem

Provider-reported usage spans multiple resource shapes (tokens with cache breakdown, compute,
reasoning subsets). Questions: which run owns cache read vs creation cost? Is reasoning output
a third token type?

## Decision

**Consumption Attribution Principle:** every measurable consumption event is attributed to the
execution attempt in which the consumption occurred, even when the consumed resource was
created by an earlier attempt.

```text
Run 1 → cache creation tokens → Run 1
Run 2 → cache read tokens    → Run 2
```

Cache is a **resource lineage** (create/consume) between attempts, not an operation attribute.

Provider capability differences degrade into unknown, never fabricated normalization:

```text
provider exposes cache breakdown → normalized breakdown
provider does not → total input known, cache allocation unknown
```

Subset quantities are not additive: `output_tokens = 1000`, `reasoning_output_tokens = 700`
(⊆ output), never 1700. Resource model must support total / subset / component relations.

## Implications

- New concept (Draft 0.5): Resource Consumption Fact — consumption belongs to the attempt that
  consumed it (token / compute / records / storage / network).
- Canonical schema: attempt_usage carries uncached / cache_read / cache_creation breakdowns when
  evidence exists.

## Rejected alternatives

- Cache state at operation level — rejected: misprices every retry in one direction or the other.
- reasoning as a third token_type in the metric — rejected: subset of output, not additive.
