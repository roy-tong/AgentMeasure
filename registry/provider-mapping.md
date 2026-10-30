# Provider Mapping Guide (native events → canonical observations)

> How an MCP/API provider maps what they already log onto the canonical
> observation contract. Goal of a mapping: the reader (you or us) can
> reconstruct, from your mapped rows alone, what happened at attempt grain —
> and can see precisely what your surface could not observe.

## The five questions a mapping must answer

Write these down before touching the schema — they are the mapping:

1. **What is one attempt on your surface?** (one tool call? one HTTP request?
   one billed unit?) — this becomes `attempt_started`/`attempt_completed`.
2. **What groups attempts into one operation?** (same `operation_id`? a
   retry-of chain? nothing observable?) — if nothing observable groups them,
   do not invent grouping; leave `operation_id` off and the report marks
   grouping UNPROVABLE.
3. **Where do retries hide on your surface?** (client library? gateway?
   invisible entirely?) — if invisible, say so in the mapping; that is a
   finding, not a failure.
4. **Can you see outcomes?** (resolved / escalated / abandoned …) — only map
   `effect_confirmed` if your surface genuinely observes the outcome, not
   infers it.
5. **What do you bill on?** (per call / per token / per resolution / per
   execution) — record it even if you send no billing rows; it frames every
   inflation finding against your actual billable unit.

## Mapping table (typical provider log row → canonical)

| Your native field | Canonical field | Notes |
|---|---|---|
| request id / call id | `payload.tool_call_id` | The identity retries must not collapse |
| session / conversation id | `deployment_context.project_id` (pseudonymous ok) | Hash it if it is customer-identifying |
| tool / capability name | `surface.surface_id` | Namespace it: `mcp_tool:<name>` |
| start timestamp | `observed_at` on `attempt_started` | RFC 3339 |
| status / error code | `payload.outcome` | Map to the enum; `unknown` if unmappable |
| latency | `payload.duration_ms` | Optional |
| retry linkage (if any) | `payload.retry_of` | **Only if genuinely observable** |
| tokens / usage (if any) | keep in your export; usage sits on the member rows, never invented | See `observation.usage_context` |
| outcome event (if any) | `effect_confirmed` payload | `outcome_class` from the registry vocabulary |

## Rules

- **Never fabricate identity.** If your log lacks a stable per-attempt id,
  emit `attempt_completed` without `tool_call_id` and mark it — a missing
  identity must stay unknown; deduplication must not erase genuine executed
  attempts (this principle arrived the hard way, from a maintainer-side
  counterexample: source-JSONL duplicate-attempt detection failing while the
  OTLP export of the same run passed).
- **One row, one observation.** Do not pre-aggregate; aggregates are produced
  by the measurement layer, and an aggregate is evidence only if it can be
  joined back to its members by count and by sum.
- **Pseudonymize by default.** Hash customer identifiers; drop payloads you
  cannot share; keep the shape.

## Submission convention (external fixture, three pieces)

When you want your run preserved as a reusable conformance fixture:

```
conformance/vectors/external/<your-handle>-<seq>/
  ├── <name>.events.jsonl      # the canonical rows
  ├── <name>.expected.json     # expected verdicts/counts (we help write this)
  └── VEROVO_<NAME>_MAPPING_<date>.md   # the five answers + claim boundary
```

Claim boundary is yours to state (synthetic vs production-derived, anonymized
how), Verovo reviews it. Precedents: `external/urusilla-001`
(project-authored synthetic), `external/iwasinnam-001..003` (production
signing path, decoded-payload level).

## What you get back

A measurement check on your sample: what safely counts as attempts vs
operations in your data, where retries may inflate usage against your billable
unit, and what your telemetry cannot prove. See
[docs/provider-onboarding.md](../docs/provider-onboarding.md) for the run
definition and success criteria.
