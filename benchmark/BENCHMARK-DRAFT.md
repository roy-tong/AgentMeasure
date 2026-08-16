# AgentMeasure Benchmark — Draft 0.1

**Benchmarking "agent usage" claims across the ecosystem: an evidence-graded audit.**

> Status: **Draft 0.1** — open for community input. This is not a product benchmark of
> agents. It is a benchmark of *claims*: how well does the ecosystem measure and
> evidence agent usage of software capabilities?
>
> 中文摘要：本基准不测试 Agent 本身，而是审计生态中"被 Agent 使用"的声称——
> skill 目录、MCP registry、Agent 框架与 README 徽章。目标是把"使用量"从营销
> 数字变成可反驳的事实：每条声称按证据强度 E0–E5 分级，按观测上下文与执行
> 有效性（Context × Validity）限定口径，再输出可验证性评分。

---

## 1. Why this benchmark exists

In 2026, "agent usage" is becoming social proof and the basis for metering and payment,
yet almost every publicly visible usage signal is self-reported:

- skills.sh install counts are CLI self-reported telemetry — gameable, with no public
  stats API (GitHub issue #190).
- The official MCP registry explicitly does not provide adoption/usage data.
- A third-party audit found ~39,000 llms.txt files, of which 97% had received zero AI
  requests — *declared ≠ used*.
- README badges (install counts, AI-attribution, token consumption) are self-reported
  with no verification layer.

The window for defining verifiable "agent usage" semantics is open (2026: AAIF exists,
OpenTelemetry GenAI conventions still in development). Whoever ships the verifiable
definition first owns the next npm download count. This benchmark accelerates that
definition by making claims auditable and comparable.

## 2. Method

Each claim passes through four stages:

```text
Claim collection → Evidence grading (E0–E5) → Qualification (Context × Validity) → Scorecard
```

### 2.1 Evidence grading E0–E5

| Level | Definition | Example |
|---|---|---|
| E0 | No evidence; claim only | "Most-used skill" with no data at all |
| E1 | Self-reported aggregate, no method | CLI telemetry count on a leaderboard |
| E2 | Self-reported with disclosed method & raw event schema | Open event log, documented counters |
| E3 | Third-party verification of aggregation | Independent replay of events against a public schema |
| E4 | Independent observation (auditor role) | Events observed by a gateway/registry not controlled by the claimant |
| E5 | Cross-checked independent observation | Two independent observers agree; discrepancy reports published |

### 2.2 Qualification: Context × Validity

Every claim must state, per the AgentMeasure Core spec (Qualification section):

- **Context (观测上下文):** where was the event observed — agent runtime, gateway,
  provider-side, or self-report?
- **Validity (执行有效性):** did the attempt actually deliver — selected → invoked →
  delivered → consumed, with attempt-level resolution?

Claims that omit either dimension are downgraded one evidence level and flagged
`unqualified`.

### 2.3 Scorecard dimensions

| Dimension | Question | Weight |
|---|---|---|
| Coverage | What fraction of the claimed population is actually measured? | 25% |
| Verifiability | Can a third party independently re-verify the aggregate? | 35% |
| Stability | Does the count move for non-usage reasons (resets, renames, gaming)? | 20% |
| Semantics disclosure | Are grain, choice mode, decision authority, and constraints disclosed? | 20% |

Overall grade: **A** (E4+ and verifiable), **B** (E3), **C** (E1–E2), **D** (E0/unqualified).

## 3. Cohort v0.1

| Cohort | Targets | Claims audited |
|---|---|---|
| Skill catalogs | skills.sh (Vercel), Skillselion, gh skill ecosystem | install counts, rankings, adoption claims |
| MCP registries | official registry.modelcontextprotocol.io, Glama, Smithery, mcp.so | server counts, adoption/usage claims, quality scores |
| Agent frameworks & runtimes | Claude Code, Cursor, Codex, Gemini CLI, DeepSeek Harness | tool-use telemetry, "X calls" claims |
| README claims & badges | agent-badge, mcp-badge-creator, skills install lines, shields endpoints | token consumption, install counts, AI-attribution |
| Declared indexes | llms.txt / llms-full.txt adopters | "read by AI" claims vs actual request logs |
| Observation standards | OpenTelemetry GenAI semantic conventions, AAIF outputs | span coverage, tool-call semantics maturity |

## 4. Report format

Each benchmark cycle publishes:

1. **Per-claim scorecards** (machine-readable JSON + human-readable markdown),
2. **An ecosystem heatmap** — who measures what, at what evidence level,
3. **Discrepancy reports** — where claims and verified counts diverge,
4. **Recommendations** — the minimum semantics every provider should publish.

Format follows the AgentMeasure reports convention (`reports/`), with a
machine-readable registry under `registry/`.

## 5. Relationship to the standard

This benchmark is a consumer of the standard, not part of it:

- Claims are graded against the **Core spec** qualification and measurement-label rules;
- `conformance/` vectors keep the standard implementable; this benchmark keeps it *credible*;
- 1.0 graduation criteria include "a published discrepancy report" and "5–10 real
  projects" — benchmark cycles are one path to both.

## 6. Cadence and next steps

- **Draft 0.1 → 0.2:** community review of the rubric (open an issue or discussion).
- **Cohort nominations:** add targets with real public claims for the first full audit.
- **Cycle 1 (target):** skills.sh + official MCP registry + llms.txt audit,
  published as Measurement/Benchmark Report, aligned with the agent-usage
  social-proof research baseline (2026 mid-year snapshot).

## 7. Open questions

1. Should the benchmark also cover *agent-side* claims (what agents say they used)?
2. Is a public "verifiability badge" (E-level shown in README) in scope, and who issues it?
3. How should privacy-sensitive telemetry (per-user agent logs) be redacted while
   remaining auditable?
4. Should scores be time-windowed (e.g., trailing 30 days) to resist gaming?

---

*Related:* [Core Specification](../standard/CORE.md) · [Measurement Report #001](../reports/measurement-report-001.md) · [Whitepaper](../whitepaper/measuring-software-used-by-ai-agents.md)
