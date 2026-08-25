# Community Outreach Templates（3 类目标人群）

> 纪律：邀请"指出定义哪里不成立"，不是要 star。每条私信/issue 都应当给出
> 一个具体可反驳的 claim。

## 1. Agent runtime / harness 开发者

```
Hi <name> — I've been reading <their project> and I have a question your
observability work is uniquely positioned to answer:

When a tool call happens inside <runtime>, how much can the runtime itself
honestly observe? (presentation? choice? consumption?)

We're building an open measurement standard (AgentMeasure) where every
observation surface declares its capability boundary instead of guessing.
Your runtime's boundary is the one we understand least.

If you have 10 minutes: https://github.com/roy-tong/AgentMeasure/issues
— specifically issue "Runtime Observation Gap" template. We'd rather learn
where our model breaks than collect stars.
```

## 2. MCP / API capability 开发者

```
Hi <name> — you build <server>. Two numbers you probably can't get today:

1. How many of your MCP calls come from agents vs CI/curl/tests?
2. How many of those are retries of the same logical operation?

We built an open SDK that answers #1 and #2 from the provider side without
touching your code paths or content:

  npm install @agentmeasure/mcp
  server.tool = (name, schema, mw.wrapTool(name, handler))

It emits canonical observations (default: unknown — nothing is claimed
without evidence). 10-minute install, local-only, no cloud.

> **Install note (until npm publish lands):** not on the public registry yet;
> install from the release tarball attached to
> [v0.2.2](https://github.com/roy-tong/AgentMeasure/releases/tag/v0.2.2)
> (`agentmeasure-mcp-0.1.1.tgz`), or `npm pack` inside `sdk/`.

If the numbers come out wrong or the definitions feel broken, that's the
most useful feedback we can get: https://github.com/roy-tong/AgentMeasure/issues
```

## 3. Observability / measurement 背景的人

```
Hi <name> — your work on <denominator/coverage/sampling> is exactly the
kind of rigor that's missing in agent analytics.

We're trying to define, as an open standard: what counts as an agent
"selection", "operation", "attempt", "consumed result" — and which
denominators are legal. Current draft: AgentMeasure Draft 0.4.3
(standard/QUALITY.md has a coverage_basis rule: participating networks
may only claim "observed", never market share).

You'd be the person most likely to find the hole in it. If you're willing:
https://github.com/roy-tong/AgentMeasure/issues — Measurement Semantics
or Discrepancy templates. A counterexample beats a star.
```

## 4. 邀请模板（可在 GitHub Issues 直接开）

```markdown
---
name: Review invitation
title: "[Review] <具体 claim> 是否成立？"
---

**Claim**: （粘贴标准里的一句定义/公式/不变量）
**Counterexample**: （如果你能找到反例，这比任何贡献都有价值）
**Where it breaks**: （哪个 denominator / eligibility / 不变量）
```

> 用法：每周挑 1-2 个具体 claim（如"Strict Qualified 默认 production+normal"、
> "M3.5 Operation Resolution Coverage 的 fail-closed"），开成 issue 邀请外部
> 反驳；反驳被采纳即进入 proposals/（AUP）并署名。
