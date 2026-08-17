# First external Provider onboarding

> 本文件是 Issue #2 的正文源（`docs/ISSUE-2.md`）。push 时由
> `.github/workflows/issue-sync.yml` 自动同步到
> https://github.com/roy-tong/AgentMeasure/issues/2 —— 不要手改 Issue。

## Goal

Onboard the first **external capability provider** onto AgentMeasure — a
remote/hosted/self-hosted MCP server or API that starts emitting canonical
observations instead of opaque call logs.

**First deliverable:** one fact about your server's usage you didn't know —
plus an honest statement of what **cannot** be known with today's lineage.

## Why this matters

Today every agent-facing tool keeps its own logs in its own shape, so nothing
is comparable. AgentMeasure's own baseline is
[Pipeline Validation #001](https://github.com/roy-tong/AgentMeasure/blob/main/reports/pipeline-validation-001.md)
(42 synthetic calls → 84 canonical observations, deterministic fixture,
deliberately 0 qualified usage). **Measurement Report #001 is reserved for the
first external provider** — your real traffic, your numbers, your story.

We are especially looking for providers who **control the running server
process**: remote MCP, hosted MCP, SaaS-backed MCP, or long-running
self-hosted deployments. (Local/stdio-only projects are welcome as SDK
implementers, but they don't see the call boundary.)

## What onboarding looks like (~10-15 min)

1. Pick a capability you expose (MCP server, API endpoint, CLI).
2. Wrap it with `@agentmeasure/mcp` (SDK **v0.1.1**, MIT) — install from the
   release tarball:
   `npm install https://github.com/roy-tong/AgentMeasure/releases/download/v0.1.1/agentmeasure-mcp-0.1.1.tgz`
   (npm registry publish pending scope/token), or clone and `cd sdk && npm install`.
   See `sdk/examples/mcp-integration-v2.js` (MCP SDK v2, primary) and
   `mcp-integration.js` (v1).
3. Emit canonical observations — `unknown` defaults are fine; honesty first,
   we never fabricate what can't be observed.
4. Done. The report is generated locally; nothing leaves your machine.

## Two onboarding modes

- **Private Alpha (default):** instrument with the SDK, run 3–7 days on real
  traffic, and the report is shared only with you. Nothing leaves your machine.
- **Public Alpha (opt-in):** after seeing your private report, you may opt in
  to publishing your numbers as a Measurement Claim Label (multi-axis Evidence
  Profile — no ranking, no composite scores).

## What you get

- One fact about your server's usage you didn't know — plus what remains
  unknowable and why.
- A say in where the standard's definitions break — your edge case becomes a
  spec change.
- Listed as an early implementer in the README (public only if you opt in).

## Who this is for

Anyone who runs a remote/hosted/self-hosted MCP server or publishes an API for
agents, and wants real numbers about usage. If the SDK doesn't fit your stack
yet (Python? Go?), say so — that's exactly the feedback we need.

> Reply here, or email the maintainer directly (see the private ops outreach
> list). If you'd rather not install anything yourself, we can prepare the
> integration PR for you — concierge onboarding is available.
