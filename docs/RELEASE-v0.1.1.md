# Release v0.1.1 — External Ready

> 本文件是 GitHub Release v0.1.1 的正文（粘贴即用）。
> v0.1.0 Release 顶部请加一行：
>
> > **Superseded by v0.1.1.** The original release contained several
> > measurement-model issues (reported 42/126 observations, an unverifiable
> > "no self-reported numbers" claim, and a non-reproducible demo); all are
> > documented and fixed in the changelog. History is kept, not deleted.

---

## What's in this release

The measurement layer for the Agent Capability Economy — a review-driven
convergence that makes the SDK safe to hand to the first external provider.

**Standard (Draft 0.4.3)**

- Canonical Observation Envelope + 6 payload types; qualification resolution
  (Context × Validity); observe-first with `unknown` defaults
- **Vocabulary single source of truth**: `registry/vocabularies.yaml` drives the
  schema enums, TypeScript unions and Python tuples (CI-checked)
- **Validity discipline**: providers may only claim validity values they can
  know; `normal` is collector-derived; `provider_configuration` validity is
  never strong qualification

**SDK `@agentmeasure/mcp` v0.1.1**

- Non-blocking: `emit()` only enqueues; background flusher batches to rotating
  spool files (dir 0700 / files 0600); loss accounting in `bufferHealth` and in
  every persisted batch's `collection_health`
- Per-request caller resolution (v2 `_meta.clientInfo` / v1 `_meta.sessionId`
  echo); server-level claim is fixture fallback only
- MCP SDK v2 (`@modelcontextprotocol/server`) as the primary path, v1 compatible;
  the SDK itself is MCP-version-agnostic (no MCP dependency)
- Lineage snake_case (`operation_id` / `task_id` / `retry_of`)
- 21 tests (schema / fail-open / privacy / lineage / caller / concurrency /
  buffer / mcp-integration v1+v2); deterministic demo fixture — same fixture +
  same policy = bitwise-identical semantic output (42 calls → 84 observations,
  6 failures, fixed latency sequence)

**Product**

- Local analytics: `--days`, latency histogram (p50/p95), caller attribution
- Pipeline Validation #001 (deterministic baseline); **Measurement Report #001
  is reserved for the first external provider**

**Benchmark (Draft 0.3)**

- Multi-axis Evidence Profile per TRUST (Authentication strictly A0/A1/A2) +
  Source Attribution axis; no composite scores
- Claim Completeness (Qualification is a Core term); primary-source rule —
  demonstrated by correcting claim #003 to its primary source (Ahrefs
  server-log/web-analytics study of 137,210 domains, May 2026)
- Machine-readable `benchmark/claims/*.json` with excerpt+hash snapshots

**Correction to v0.1.0 messaging**

v0.1.0 said "No self-reported numbers. Measurement happens at the callee
boundary." That overstated the guarantee. The accurate statement:

> **Provider-observed rather than caller-self-reported**; stronger claims still
> require independent corroboration or attestation (TRUST §3).

---

## Install

```bash
npm install @agentmeasure/mcp   # publish in progress — see CHANGELOG
# or: git clone https://github.com/roy-tong/AgentMeasure && cd sdk && npm install
```

## Demo

```bash
./examples/demo-e2e.sh   # isolated workspace, deterministic, 2 minutes
```
