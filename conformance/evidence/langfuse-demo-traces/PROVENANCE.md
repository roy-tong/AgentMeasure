# Provenance & claim boundary

## Source

- Repository: `langfuse/langfuse` (public)
- Path: `packages/shared/scripts/seeder/utils/framework-traces/`
- Files analyzed (all three, no selection beyond "the framework traces
  present in that directory at pin time"):
  - `langgraph-2025-08-22.json`
  - `openai-agents-2025-09-30.json`
  - `pydantic-ai-tools-2025-12-04.json`
- Pinned commit: `ea3c905cd535` (langfuse `main`, fetched 2026-08-24/25).
  `fetch_source.py` downloads exactly this commit's copies.
- What they are: real framework-instrumented traces captured via Langfuse SDK
  integrations, used by Langfuse as demo-environment seed data.

## Redistribution

The langfuse repository ships a multi-part license
(Copyright 2023-2026 ClickHouse, Inc. — see their `LICENSE`). We
therefore **do not redistribute the source files** in this repository.
`fetch_source.py` pulls them from the pinned commit; the pinned raw URLs are
immutable, and the analysis is of the fetched bytes.

## Claim boundary (hard constraints on quoting this case)

- Evidence Case Taxonomy: **External Fixture**. Third-party public artifact,
  reproducible by anyone via the commands above.
- NOT a Production Case. NOT Langfuse endorsing, adopting, or reproducing
  AgentMeasure. NOT a statement about any Langfuse product beyond the
  contents of these three files.
- All numbers (12 attempts, 0% grouping evidence, 0/26 usage, 4 patterns)
  describe these three traces only. No extrapolation to Langfuse demo data
  generally, to other traces, or to any production deployment is implied or
  permitted.
- The adapter and runner here are one-off concierge code, frozen for
  reproducibility. They are not a supported product surface and make no
  claim to handle arbitrary Langfuse exports (mapping decisions and their
  limitations are documented in the adapter docstring).

## Adapter mapping decisions (disclosed)

| Langfuse export | Canonical handling |
|---|---|
| `TOOL "running tool: X"` | attempt_started + attempt_completed; surface = X |
| `GENERATION` (model M) | attempt_started + attempt_completed; surface = `model:<M>` |
| `SPAN` / `AGENT` | not an invocation — grouping context, analyzed structurally by `run_case.py` |
| observation id | `tool_call_id` (pairs start/completed) |
| `traceId` | `trace_id` and `task_id` (trace = task boundary; correlation-grade, no operation declaration) |
| `startTime`/`endTime` | `started_at` / `duration_ms` |
| `level` | outcome: `ERROR` → failure, else success (completion assumed; Langfuse levels mark errors only) |
| `usage` fields | absent in export → no usage observations emitted |
| `operation_id` / `retry_of` | absent in export → not emitted (the finding itself) |
| context labels | `usage_context: demo`, `provenance: wrapper`, observer side `client` |
