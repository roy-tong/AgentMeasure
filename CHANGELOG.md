# Changelog

All notable changes to AgentMeasure (standard, SDK, and reference product) are
documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- **First public evidence case — [langfuse-demo-traces](conformance/evidence/langfuse-demo-traces/)**: three real framework-instrumented traces published by Langfuse as demo seed data (commit-pinned, source not redistributed), run through the canonical pipeline via a disclosed one-off adapter. Result: 12 attempts, operation grouping evidence 100% ungrouped, **safe operation coverage 0%** in both fail-closed and structural-experimental modes; 4 sibling patterns where retry and loop step are observationally indistinguishable; token usage absent from the export (0/26). Fully reproducible (`fetch_source.py` + `run_case.py`, stdlib only). Claim boundary: External Fixture — numbers describe these three traces only.

## [v0.2.2] - 2026-08-24 — conformance hardening (#8 / #9 + first external vector)

- **Fix #8 — validator: root sibling constraints after oneOf** (found in the first external conformance pass, [langfuse#16383](https://github.com/langfuse/langfuse/discussions/16383)): the bundled validator returned after evaluating `oneOf`, so records matching one branch but missing root-level required fields (siblings of the root `oneOf` in FMT-002) validated successfully. `oneOf`/`anyOf` are now compositional — sibling keywords are always evaluated after a branch matches; zero-match errors carry the first branch error for diagnosis. The registry validator additionally fails closed on unsupported composition keywords instead of silently ignoring them.
- **Fix #9 — aggregator: reconcile declared operation summaries against attempt rows**: the lab aggregator trusted `operation_result` declarations (`attempts`, `outcome`) without checking the underlying `attempt` rows. Every declaration is now reconciled — declared count vs actual rows, declared outcome vs the rows' derived outcome (rule op-success-any/1, last-attempt outcome disclosed) — and mismatches surface as an explicit `operation_reconciliation: failed` block. Counts and outcomes use **measured rows, never declarations**. The canonical collector gained the same discipline: `task_outcome` payloads now persist `task_success`/`attempt_count` and `compute()` emits `operation_summary_reconciliation`.
- **First external conformance vector accepted upstream** — [Urusilla-001](conformance/vectors/external/urusilla-001/) (project-authored synthetic fixture by @jaden3824, per the #8/#9 commitment): schema validity, #8 root-sibling mutation guard, exact metric reproduction, and #9 tamper guards via `conformance/runners/run_external_fixture.py`. Claim boundary preserved: synthetic evidence, not an endorsement or external reproduction. The external-fixture runner and the full lab test suite run in CI (`lab/**` now triggers workflows; guards execute on every conformance run).

## [v0.2.1] - 2026-08-22 — codex adapter live-validated

- **Live validation on a real harness** (codex-cli 0.149.0-alpha, gpt-5.6-sol): first preregistered controlled A/B on a real agent — 4 tasks × 2 variants (description clarity), full funnel (reach/choice/success/consumption), **real token metering** (188K–215K tokens/op measured), steps proxy, honest null with next-round sizing (+25pp observed, n=4/arm, p=0.29 → "plan ≈31/arm"); report verified (`am lab verify` PASS), bilingual one-pager + live disclosure in place.
- Adapter fixes found by the live run (why live validation matters): MCP tools arrive as `mcp_tool_call` items with `server`/`tool` fields (not `function_call`); MCP calls need `--approve-for-me` in exec mode (otherwise "approval policy is never" denies them); stdin must be DEVNULL; **toolserver contract bug** — the runner's spec carried `id` where the server requires `name`, crashing `tools/list` so agents saw "server failed to start" (now covered by a contract regression test); candidate-set steering in the episode prompt (a real harness otherwise reasonably prefers its built-in search).
- codex runner: token usage metered as cost units (1 unit = 1 token, amortized per attempt); `codex_config` / `extra_args` passthrough; `--ephemeral` by default (no session pollution); `claude-code` benefits from the shared fixes (DEVNULL, steering, contract) and remains scripted-transcript-tested pending its own live run. 78 tests (+4).

## [v0.2.0] - 2026-08-22 — Whitepaper v0.3 + AgentMeasure Lab v0.4 (open experiment engine)

- **Lab v0.4 — real harness runners (LAB-004) + experiment history (G6 local)**: `claude-code` adapter — runs the real harness headless (`claude -p --output-format stream-json --mcp-config`) against a **controlled candidate set** injected through a per-episode local MCP tool server ([`toolserver.py`](lab/agentmeasure_lab/toolserver.py), pure stdlib; presentation varies per variant); `codex` adapter (experimental, `codex exec --json`, App Server surface future work); transcript→funnel parsing with honest limits (choice from transcript, success from tool_result, consumption = continuation proxy, latency/cost placeholders — disclosed in every report); integration-tested end-to-end against scripted CLI transcripts (tests/fake_claude.py / fake_codex.py) — **live-CLI validation pending, first live runs are validation runs**; `am lab history` — local experiment/hypothesis library (every run with date, verdicts, prereg hash, fingerprint); `run.json` now records `created_at`; baseline funnel section in [product/local-analytics.py](product/local-analytics.py) (BASE0-002: attempts → resolved operations → success, with explicit "not observable provider-side" boundaries); 74 tests (14 new).
- **Lab v0.3 — business-POC-driven release hardening**: fake growth now blocks the decision exit — a significant selection uplift whose consumption drop is significant or material (>5pp) is verdicted `unverified_growth` with a "do not ship: fix consumption first" recommendation (previously the warning existed but the verdict still said adopt); the check is significance-aware, so within-noise consumption dips no longer false-flag; **dominated candidates are called out** (no more money at higher cost → "pick the other one"); **null results carry next-round sizing guidance** (≈n per arm to resolve the observed effect — a boss must not read "null" as "no effect"); reports open with a **bilingual decision-maker one-pager** (conclusion / uplift / monthly margin / certainty / recommended action, no statistics vocabulary); `preregister` prints a **scale / power / budget preview** (per-arm n vs minimum, n needed for +2/+3/+5/+8pp at an assumed baseline, budget caps + worst-case spend — LAB-002 acceptance and NFR-COST-001 now met); CLI errors print **one clean line** instead of tracebacks (`AM_LAB_DEBUG=1` restores them); task-set paths fall back to the shipped corpus; run output defaults to a predictable cwd-relative `runs/`; mock harness default effect amplitudes cut to **realistic literature scale** (single-digit pp, echoing Hasan et al.) so demos cannot flatter the engine; MCP advice now carries plain-language verdicts, verified monthly margin, dominance and power notes; 60 tests (7 new POC regression tests encoding boss-level acceptance criteria).
- **Lab v0.2 — calibration loop + MCP interface**: production re-test analysis ([`am lab calibrate`](lab/README.md), CAL-002/003) — offline vs production uplift under the same preregistered plan, per-condition (harness × task stratum) transfer effects with intervals (never a single global coefficient), verdicts `production_confirmed` / `direction_mismatch` / `transfer_not_established` / `not_comparable` (gap named, never assumed), matrix-reweighting suggestions (CAL-004 minimal); connector data plane (`am connector`, CAL-001) — local-first aggregation, three-tier per-class authorization (`off`/`local`/`export`), immediate revocation, HMAC-signed aggregate-only exports (schema-level: no per-assignment rows, no content); read-only MCP query interface (`am mcp serve`, LAB-009) — `get_run_summary` / `get_presentation_advice` (evidence grades, guardrails, production-verification status) / `get_funnel_metrics`, no rankings, no competitor data; calibration-report schema; [FMT-004 mapping doc](lab/docs/CORE-MAPPING.md) (Core 0.4.4 ↔ experiment formats + 2 reference scenarios); synthetic production-event generator for demos; 53 tests. Real production ingestion still gated on G0 data rights — validated on synthetic rollouts with planted transfer, disclosed as such.
- **Lab v0.1 — open experiment engine** ([lab/](lab/README.md)): end-to-end preregistered experiments (M1 synthetic-harness scope) — CLI (`am lab init/preregister/run/report/verify/selftest`), enforced preregistration lock (hash), balanced blocked assignment, seed determinism (same seed → same run fingerprint), budget circuit breaker (safe stop, data kept, honest "incomplete" analysis), Reach→Choice→Success→Consumption funnel capture with Operation/Attempt semantics, honest statistics (Wilson/Newcombe intervals, two-proportion tests, honest nulls, "undetermined" with required n), guardrails (`effective_not_qualified` verdict), fake-growth warning, value-formula bridge, offline HTML/JSON reports with Measurement Labels; open formats FMT-001/002/003 ([lab/schemas/](lab/schemas/)); synthetic vertical task corpus v1 (36 tasks, 3 tiers); 30 tests + built-in selftest; synthetic mock harness with planted ground truth (disclosed in every report) — real harness runners (claude-code/codex) are plugin-interface pending
- **Whitepaper v0.3** (EN + zh-CN): experimentation & calibration as first-class measurement semantics (§8 — preregistered loop, guardrails, per-condition effect sizes, offline→production transfer); anti-fake-growth elevated to a core thesis with the x402 wash-trading evidence (§2); data-rights claim tiers in the observation-surfaces chapter (§10); value formula bridging measurement to margin (§7.5); new evidence (Hasan et al. arXiv 2602.14878, BiasBusters ICLR 2026, Arcade ToolBench, AAIF/A2A/AgentCore/AP2 infrastructure); zh-CN now structurally in sync with EN (missing §0.2/§0.5 added); references updated; version pinned to Standard Draft 0.4.4
- **Harness-native direction**: harness profiles for [Codex](profiles/codex.md), [Claude Code](profiles/claude-code.md) and [DeepSeek Harness](profiles/deepseek-harness.md) (what each runtime can/cannot observe, mapped to AgentMeasure semantics); [Experiment D — cross-harness compatibility](experiments/EXPERIMENT-D-cross-harness-compatibility.md) (one fail→retry→fallback→success task across three harnesses); [Proposal: Delegation](proposals/2026-08-21-delegation-graph.md) (fourth semantic object for agent-to-agent delegation); whitepaper §1.5 "Harness-native Software and the Measurement Problem" (EN + zh-CN)
- **Product**: [product/AUDIT.md](product/AUDIT.md) — the 7-day capability performance audit, productized (design-partner offer, founding-audit tier, FAQ); README (EN/zh-CN) now links it as the front-door offer
- **Roadmap**: standard track under a change timebox until 2026-09-04 (non-blocking AUPs queued); product track (Product Gate A) is the critical path
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
