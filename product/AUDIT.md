# AgentMeasure Audit — a 7-day capability performance audit

> **In one line: find out what your agent traffic actually is — hidden retries, wasted spend, polluted "production" numbers — in one week, without your data leaving your machine.**

You know how many MCP / API calls you receive. You probably don't know:

- how many **logical operations** those calls represent after retries and fallbacks;
- how much of your "production" traffic is actually **CI, health checks, or synthetic monitors**;
- what your **cost per successful operation** is — as opposed to cost per raw call;
- which callers are genuinely **agents** (correlated evidence) vs self-declared vs unknown.

The AgentMeasure Audit answers these with an evidence-graded measurement, not another dashboard.

**Start here: [Issue #2 — First external Provider onboarding](https://github.com/roy-tong/AgentMeasure/issues/2)** · [How the standard works](../README.md)

---

## What you get

A Measurement Report plus a 45-minute review call. Findings are stated as business conclusions with their evidence class attached — never as a wall of traces. Typical finding types (all provable from the provider side alone):

| # | Finding | Example shape |
| --- | --- | --- |
| 1 | **Attempt inflation** | call count overstates logical usage; retry-chain evidence where strict correlation exists, honest coverage disclosure where it doesn't |
| 2 | **Execution economics** | cost per successful attempt / resolved operation, per capability and per caller class |
| 3 | **Caller attribution structure** | correlated vs declared vs unknown share — how much of your traffic is *provable* agent usage |
| 4 | **Qualified-traffic pollution** | CI / healthcheck / synthetic traffic sitting inside your production numbers |
| 5 | **Anomalous patterns** | schema / timeout shapes that cluster with retry storms |

Every number carries a **Measurement Label** (coverage / sampling / policy / method) — the same discipline we applied when auditing six public ecosystem claims in [Benchmark Run #001](../reports/benchmark-run-001.md).

**What this is not:** not a trace viewer, not an observability platform, not a marketplace score. Client↔server evidence pairing and cross-harness comparisons are later, paid tiers — we don't promise them in the free audit.

---

## How integration works (≤30 minutes)

1. Install the SDK from the [v0.1.1 release](https://github.com/roy-tong/AgentMeasure/releases/tag/v0.1.1):
   ```bash
   npm install https://github.com/roy-tong/AgentMeasure/releases/download/v0.1.1/agentmeasure-mcp-0.1.1.tgz
   ```
2. Wrap your tool handlers — [v2 example](../sdk/examples/mcp-integration-v2.js) (MCP SDK v2) or [v1 example](../sdk/examples/mcp-integration.js):
   ```js
   server.tool = (name, schema, handler) => mw.wrapTool(name, handler)
   ```
3. After 7 days, generate the report locally:
   ```bash
   python3 product/local-analytics.py ~/.agentmeasure/events/ --project github.com/you/your-server
   ```

Properties that matter to you:

- **Data stays local by default.** Observations are JSONL on your machine; the report is generated locally. Hosted ingestion is explicit opt-in, later.
- **Not on the critical path.** The SDK is non-blocking with a durable spool and loss accounting; if the SDK fails, your server doesn't.
- **No agent-side install, no open-source requirement, MCP not required** (it's simply the first reference surface).

---

## The schedule

```text
Day 1     integrate (≤30 min)
Day 2–7   measure — real production traffic, one capability
Day 4     first findings preview
Day 7     report + 45-min review
Day 8+    you pick an action; optional re-measure proves the before/after
```

---

## Pricing

- **Design Partner (free, 3–5 slots).** In exchange: at least 7 days of real production traffic, one findings review, and — only if we find something you act on — a discussion about follow-up and an (opt-in, anonymizable) case study.
- **Founding Audit (from $1,500).** Adds client↔server evidence pairing, cross-harness analysis, and an optimization review. Slots open after the design-partner round.

---

## FAQ

**We already have analytics.** Most provider dashboards count *calls*. The Audit measures *operations vs attempts, caller evidence classes, and qualified usage* — a semantic layer your dashboards can keep building on. The [2-minute demo](../examples/README.md) shows the difference concretely.

**Is this open source?** The standard, SDK, collector, and conformance vectors are (MIT). The Audit is a service on top of them; using the standard never requires it.

**Why free?** We're calibrating the measurement against real provider traffic. Your cost is 30 minutes and one review call; ours is the analysis. Both sides can walk away after Day 7.

**What if you find nothing we didn't know?** Then the method needs work, and we'll say so. That outcome is public information about us, not about you.

---

**→ Apply: [Provider Trial form](https://github.com/roy-tong/AgentMeasure/issues/new?template=5-provider-trial.yml)** (five fields, ~2 minutes) · [Program details → Issue #2](https://github.com/roy-tong/AgentMeasure/issues/2) · [Website](https://roy-tong.github.io/AgentMeasure/)
