# Changelog

All notable changes to AgentMeasure (standard, SDK, and reference product) are
documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

- **Harness-native direction**: harness profiles for [Codex](profiles/codex.md), [Claude Code](profiles/claude-code.md) and [DeepSeek Harness](profiles/deepseek-harness.md) (what each runtime can/cannot observe, mapped to AgentMeasure semantics); [Experiment D — cross-harness compatibility](experiments/EXPERIMENT-D-cross-harness-compatibility.md) (one fail→retry→fallback→success task across three harnesses); [Proposal: Delegation](proposals/2026-08-21-delegation-graph.md) (fourth semantic object for agent-to-agent delegation); whitepaper §1.5 "Harness-native Software and the Measurement Problem" (EN + zh-CN)
- **Product Gate A in progress**: first external Provider onboarding ([#2](https://github.com/roy-tong/AgentMeasure/issues/2)), first benchmark design discussion ([#3](https://github.com/roy-tong/AgentMeasure/discussions/3))
- README: added status badge row (CI / spec draft / release / license / discussions, EN + zh-CN); status section now shows Draft 0.4.4

## [v0.1.1] - 2026-08-17 — External-Ready convergence

The review round that makes the SDK safe to hand to the first external provider.
The demo is now a reproducible experiment, the SDK is non-blocking with real buffer
accounting, caller identity is per-request, and the benchmark uses the standard's
own Evidence Profile instead of a parallel ladder.

### Fixed

- **Demo reproducibility**: `examples/demo-e2e.sh` now runs in an isolated
  `mktemp -d` workspace and never touches `~/.agentmeasure`; the fixture is labeled
  `usage_context=synthetic` at the source; same fixture + same policy = same result
  (42 calls → 84 observations, every run)
- **Removed invented `result_consumed`** from the provider example: a provider-side
  MCP server cannot observe whether the agent consumed the result —
  UNOBSERVABLE is not fabricated as TRUE (42 calls → 84 observations, not 126)
- **SDK is non-blocking**: `emit()` only enqueues; a background flusher batches
  writes to rotating spool files (default 5 MiB, keep 7); `BUFFER_LIMIT` (10,000)
  is now enforced with explicit loss accounting (`bufferHealth`: queueDepth,
  droppedTotal, droppedSinceLastFlush, flushFailures, spoolBytes, rotatedFiles);
  loss numbers are stamped into each persisted batch's `collection_health`
- **Caller per-request**: `wrapTool(..., { getCaller })` resolves the CallerClaim
  from the request context (v2 `_meta.clientInfo` / v1 `_meta.sessionId` echo);
  the server-level caller is a fallback for fixtures only
- **Lineage snake_case**: `operation_id` / `task_id` / `retry_of` per payload
  schemas; camelCase aliases map (deprecated); previously a runtime-provided
  camelCase field would produce a schema-invalid observation
- **Local analytics**: `--days` is honored (was hardcoded 365); latency histogram
  (p50/p95/buckets from non-sensitive `duration_ms`); caller attribution by runtime
  and identity strength (was "needs histogram" / observer-count placeholder)
- **CI**: `sdk/**` `examples/**` `benchmark/**` `reports/**` added to triggers;
  new `sdk-gate` job (npm ci → build → 21 unit tests → canonical-boundary pipeline
  gate); core tests rewritten to feed **canonical JSONL only** (no more
  `store_observation` + legacy `lifecycle_stage` bypass)
- **MCP SDK v2 support**: `@modelcontextprotocol/server` (stable 2026-07-28 line)
  is the primary adapter path (`mcp-integration-v2.js`); v1 remains as a
  compatibility path; the SDK itself is MCP-version-agnostic (peer dep)
- **Benchmark methodology**: E0–E5 single ladder and A/B/C/D composite scores
  removed — claims are profiled with the multi-axis Evidence Profile
  (`standard/TRUST.md` §3); "Context" renamed to Observation Surface / Provenance
  (CORE `usage_context` keeps its own meaning); output is a Measurement Claim
  Label; machine-readable `benchmark/claims/*.json` with snapshot discipline;
  AgentMeasure's own numbers moved out of the ranking (reference fixture only);
  overclaims in Run #001 corrected ("every number is self-reported" →
  "the dominant pattern is self-reporting"; "Independence beats volume" →
  "Independence strengthens corroboration; it does not substitute for coverage")
- **License unified**: SDK package is MIT (was Apache-2.0) with its own LICENSE,
  matching the repo and the release
- **Release copy correction**: "no self-reported numbers" overstated — callee-side
  measurement means *provider-observed rather than caller-self-reported*; stronger
  claims still require independent corroboration or attestation (TRUST §3)

### Added

- `schemas/validate_jsonl.py` — single-source canonical JSONL validator (SDK tests
  and CI share it)
- `scripts/verify_sdk_pipeline.py` — External-Ready pipeline gate
  (SDK fixture → JSONL → validate → ingest → metrics → expected output)
- `scripts/canonical_core_gate.py` — core invariants through canonical ingestion only
- `sdk/test/` — 21 tests: schema / fail-open / privacy / lineage / caller /
  concurrency / buffer / mcp-integration (v1 + v2)
- `benchmark/claims/*.json` — machine-readable claim records for Run #001

### Changed

- `reports/measurement-report-001.md` → `reports/pipeline-validation-001.md`
  (42/84 honest baseline; **Measurement Report #001 is reserved for the first
  external provider**)
- `@agentmeasure/mcp` v0.1.1 — package.json: MIT, devDeps vs peerDeps, `files`
  includes LICENSE

### v0.1.1 RC → External Alpha（本版追加）

- **Vocabulary single source of truth**: `registry/vocabularies.yaml` →
  `scripts/gen_vocab.py` regenerates the observation schema enums and the
  vocabulary table, and CI-checks TS unions + Python tuples (`--check`).
  `usage_context` now includes `demo`; `validity_source` now includes
  `provider_configuration` — the CORE/schema/TS/Python drift is closed
- **Validity loophole closed**: providers can only claim validity values they
  can know (`health_check` / `load_test` / `suspected_invalid` / `duplicate`);
  `normal` is collector-derived. `validity_source=provider_configuration` is
  never strong qualification (collector core-5 gate)
- **Benchmark Draft 0.3**: Authentication strictly per TRUST (A0/A1/A2 —
  "attributable" is no longer A1); new orthogonal Source Attribution axis;
  Benchmark `Qualification` renamed **Claim Completeness** (Qualification is
  returned to Measurement Core); primary-source rule added and demonstrated —
  claim #003 corrected: primary source is **Ahrefs** (server-log/web-analytics
  telemetry over 137,210 domains, May 2026), not originality.ai / independent
  crawl; claims regenerated with real excerpt+sha256 snapshots
- **Demo fully deterministic**: fixed failure pattern (callIndex%8==0 → 6/42)
  and fixed latency sequence (20+(i*37)%280) via wrapTool `durationMs` override
  (fixture-only; production records measured wall time). Two runs are now
  bitwise-identical in semantic output; pipeline gate asserts success 0.857 and
  the exact duration set
- **Packaging**: `peerDependencies` removed — the SDK is MCP-version-agnostic
  (examples/tests depend on v1/v2 packages themselves); `spoolFileName` option
  with multi-process guidance; spool dir 0700 / files 0600; optional
  `handleSignals` (SIGTERM/SIGINT drain) with documented crash boundary
  ("up to one flush interval may be lost on abrupt termination");
  `npm pack` + clean-install verified in a fresh project
- **Outreach v2**: Pool A/B/C/D segmentation (first 10 = Pool A only);
  email copy rewritten from "we answer both" to
  "we show you what can be known — and what cannot"; Private Alpha default /
  Public Alpha opt-in modes for first-wave providers; no `npm install`
  instruction until the package is actually published

## [v0.1.0] - 2026-08-16

First public release: the measurement layer for the Agent Capability Economy.

### Added

- **Standard (Draft 0.4.3)**: canonical observation schema + 6 payload types, qualification resolution, metrics registry (14 metrics, single source of truth), observe-first policy with `unknown` defaults
- **SDK**: `@agentmeasure/mcp` v0.1.0 — TypeScript wrapper for official MCP SDK servers (fail-open, zero-content, registration-time wrapping)
- **Product**: canonical end-to-end pipeline (adapters → observations → collector → metrics); `local-analytics.py` with six classes of metrics
- **Pipeline Validation #001**: honest baseline (42 synthetic calls → 84 canonical observations, 0 rejected, 0 qualified usage by design; the Measurement Report #001 number is reserved for the first external provider)
- **Docs**: whitepaper (EN/ZH), core spec, quality dimensions, commercial semantics, roadmap, governance
- **Community**: Discussions with 5 categories; issue templates (Metric Semantics / Observation Gap / Discrepancy / Proposal)

### Notes

- `0 stars at launch` is a feature of the honesty-first posture, not a bug.
- Synthetic traffic only so far; every limitation is stated in the report.
- 2026-08-17: v0.1.1 tag pushed; CI workflow fixed (quoted step name)
- 2026-08-17: release automation live — GitHub Release v0.1.1 created and
  v0.1.0 marked superseded by `.github/workflows/release.yml` (GITHUB_TOKEN);
  `agentmeasure-mcp-0.1.1.tgz` attached as a release asset (providers can
  install without npm: `npm install <release-download-url>`); npm publish is
  automated and activates automatically once an `NPM_TOKEN` secret is added
  to the repository (job runs build + tests before publish; `--access public`).
  No npm credentials exist on the dev machine (npm whoami: ENEEDAUTH).
