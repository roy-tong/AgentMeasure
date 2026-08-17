# AgentMeasure Benchmark — Draft 0.2

**Benchmarking "agent usage" claims across the ecosystem: an evidence-profile audit.**

> Status: **Draft 0.2** — open for community input. This is not a product benchmark of
> agents. It is a benchmark of *claims*: how well does the ecosystem measure and
> evidence agent usage of software capabilities?
>
> 中文摘要：本基准不测试 Agent 本身，而是审计生态中"被 Agent 使用"的声称——
> skill 目录、MCP registry、Agent 框架与 README 徽章。目标是把"使用量"从营销
> 数字变成可反驳的事实。每条声称输出一张 **Measurement Claim Label**（单位、
> 粒度、观测面、覆盖基础、方法披露、独立佐证、可复现性），不做单一字母评分。
>
> **Draft 0.2 变更（v0.1.1 External-Ready 收敛）**：废弃单轴 E0–E5 阶梯
> （与标准 `standard/TRUST.md` §3 的 Evidence Profile 多轴模型冲突）；"Context"
> 更名为 **Observation Surface / Provenance**（CORE 的 `usage_context` 是另一概念，
> 保留其原始语义）；取消 A/B/C/D 综合评分；AgentMeasure 自身不再参与排名，
> 仅作为参考 fixture 单列。
>
> **Draft 0.3 变更（v0.1.1 RC → External Alpha）**：`Authentication` 严格遵守
> TRUST（A0 none / A1 signed / A2 identity-verified），新增正交的
> **Source Attribution** 轴（unknown / named / verified_organization）；
> Benchmark 的 `Qualification` 更名为 **Claim Completeness**（`Qualification`
> 一词归还给 Measurement Core：Usage Context × Attempt Validity）；
> 新增 **primary-source 追溯规则**（secondary source MUST resolve primary
> measurement source if available）。Benchmark 是 Standard 的消费者，
> 不得重新解释 Standard。

---

## 1. Why this benchmark exists

In 2026, "agent usage" is becoming social proof and the basis for metering and payment.
The dominant pattern in public usage signals is self-reporting:

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
definition by making claims auditable and comparable — using the standard's own
evidence model, not a parallel one.

## 2. Method

Each claim passes through four stages:

```text
Claim collection → Evidence Profile (multi-axis) → Provenance & completeness → Measurement Claim Label
```

### 2.1 Claim collection（机器可读，可复现）

Every claim is captured as `benchmark/claims/claim-<NNN>.json` with:

```jsonc
{
  "claim_id": "sha256(claim text + source url)[:12]",
  "claim": "exact quoted text",
  "metric_unit": "payment | merchant | AI request | call | …",   // null if undefined
  "grain": "count | rate | share | …",
  "source": {"url": "...", "type": "x-post | audit | report | readme | …"},
  "primary_source": {"url": "...", "name": "...", "resolved": true},
  "retrieved_at": "2026-08-16T…Z",
  "snapshot": {"status": "excerpt-hash | retrieval-pending",
               "excerpt": "normalized excerpt proving the claim (minimal, no full-page mirror)",
               "excerpt_sha256": "…", "retrieved_at": "…"},
  "reviewer": "github handle",
  "evidence_profile": {…},         // §2.2
  "source_attribution": "…",       // §2.2.1
  "provenance": {…},               // §2.3
  "completeness": {…}              // §2.4
}
```

**Primary-source rule**: if the claim was encountered through a secondary source,
it MUST resolve to the primary measurement source when available and record
`primary_source.resolved: true`. Attribution errors (secondary retold as primary,
or the wrong surface) are themselves benchmark findings — this benchmark exists
to catch exactly that.

### 2.2 Evidence Profile（多轴，与 standard/TRUST.md §3 一致）

**不采用单一字母阶梯**。每条声称按 TRUST 的五轴独立评级，
`Authentication` 的定义与 TRUST 逐字一致（**不得改写**）：

| 轴 | 取值 | 回答 |
| --- | --- | --- |
| Authentication | A0 none / A1 signed / A2 identity-verified | 我知道是谁说的（**签名/身份验证**，不是"可归因"） |
| Corroboration | C0 single / C1 multiple | 有几方这么说 |
| Independence | I0 unknown / I1 distinct runtime / I2 distinct trust domain | 是否同一主体控制 |
| Attestation | T0 none / T1 platform-attested | 是否有受信任平台背书 |
| Match | none / heuristic / exact-call-id / trace-verified | 数字与观测的关联强度 |

#### 2.2.1 Source Attribution（正交轴，与 Authentication 分离）

"这篇文章明确是 Ahrefs 发的"是 **attributable provenance**，不是
**cryptographically signed observation**。两者分开记录：

| 取值 | 含义 |
| --- | --- |
| unknown | 无法确认来源身份 |
| named | 可指认到具体账号/作者（未经组织验证） |
| verified_organization | 可验证到组织身份（官网/组织仓库/公开身份） |

一条声称可以同时是 `Authentication A0 + Source Attribution verified_organization`
——被确认真实身份的发言者**没有签名**，Authentication 仍为 A0。

五轴 + Source Attribution 均正交，不合并为一个分数（见 §2.5）。

### 2.3 Observation Surface / Provenance（不是 "Context"）

CORE 的 `usage_context`（production / development / test / benchmark / evaluation /
synthetic / ci / demo / unknown）描述**数据本身**的环境语义，本基准不重定义它。
声称级的"数字从哪里观测到"使用独立概念：

- **Surface:** provider-side ledger · provider-side telemetry · gateway · registry ·
  independent crawl · server-log / web-analytics telemetry · self-report · unknown
- **Coverage basis / population:** what fraction of the claimed population the number
  actually covers（如 "137,210 Ahrefs Web Analytics 域" vs "39k 域 of an unknown universe"）
- **Observed period:** 数字覆盖的时间窗（如 May 2026）

### 2.4 Claim Completeness（执行有效性；不用 `Qualification`）

`Qualification` 是 Measurement Core 的术语（Usage Context × Attempt Validity），
Benchmark 不再占用。声称级完整性使用独立概念：

| 维度 | 取值 |
| --- | --- |
| definition_status | defined / partial / undefined（metric unit 是否有定义） |
| method_disclosure | yes / partial / no（计数方法是否披露） |
| source_traceability | primary / secondary-resolved / unresolved（能否追溯到 primary source） |
| coverage_disclosure | yes / partial / no（population 与覆盖是否披露） |

### 2.5 Measurement Claim Label（输出；不做综合评分）

每条声称输出一张标签，**不压成 A/B/C/D**：

```text
Claim            : "x402 settled its 162-millionth payment"
Metric unit      : "payment" (undefined)
Grain            : count
Surface          : provider-side ledger (claimed)
Coverage basis   : unknown
Method disclosed : no
Authentication   : A0 (not signed)   Source Attribution: named
Corroboration    : C0 · Independence I0 · Attestation T0
Match            : none
Completeness     : definition undefined · method no · traceability unresolved
Replayability    : no (no public ledger, no raw data)
```

为什么不做综合分：维度正交且用途相关。平台遥测可能 Coverage 强但 Independence
低；独立爬虫可能 Independence 强但 Coverage 弱——谁"更好"取决于用途。综合分
会隐藏这两者的差异，这正是 AgentMeasure 自己的质量模型反对的。

## 3. Cohort v0.1

| Cohort | Targets | Claims audited |
|---|---|---|
| Skill catalogs | skills.sh (Vercel), Skillselion, gh skill ecosystem | install counts, rankings, adoption claims |
| MCP registries | official registry.modelcontextprotocol.io, Glama, Smithery, mcp.so | server counts, adoption/usage claims, quality scores |
| Agent frameworks & runtimes | Claude Code, Cursor, Codex, Gemini CLI, DeepSeek Harness | tool-use telemetry, "X calls" claims |
| README claims & badges | agent-badge, mcp-badge-creator, skills install lines, shields endpoints | token consumption, install counts, AI-attribution |
| Declared indexes | llms.txt / llms-full.txt adopters | "read by AI" claims vs actual request logs |
| Observation standards | OpenTelemetry GenAI semantic conventions, AAIF outputs | span coverage, tool-call semantics maturity |

**外部 cohort 只审外部声称。** AgentMeasure 自己的数字（Pipeline Validation #001）
作为 **Reference Fixture** 单列于报告附录，不进排名——避免"自己建评分体系给
自己评级"。

## 4. Report format

Each benchmark cycle publishes:

1. **Per-claim Measurement Claim Labels**（machine-readable `benchmark/claims/*.json`
   + human-readable markdown），无综合评分；
2. **An ecosystem heatmap** — who measures what, on which surface, at what
   authentication/independence/corroboration level;
3. **Discrepancy reports** — where claims and verified counts diverge;
4. **Recommendations** — the minimum semantics every provider should publish.

## 5. Relationship to the standard

This benchmark is a consumer of the standard, not part of it:

- Claims are profiled with the **Evidence Profile** from `standard/TRUST.md` (§3) and
  the qualification rules from the Core spec — the benchmark uses the standard's own
  vocabulary, never a parallel ladder;
- `conformance/` vectors keep the standard implementable; this benchmark keeps it *credible*;
- 1.0 graduation criteria include "a published discrepancy report" and "5–10 real
  projects" — benchmark cycles are one path to both.

## 6. Cadence and next steps

- **Draft 0.2 → 0.3:** community review of the label schema (open a discussion).
- **Cohort nominations:** add targets with real public claims for the first full audit.
- **Cycle 1 (target):** skills.sh + official MCP registry + llms.txt audit, published
  as a Benchmark Report, aligned with the agent-usage social-proof research baseline
  (2026 mid-year snapshot).

## 7. Open questions

1. Should the benchmark also cover *agent-side* claims (what agents say they used)?
2. Should "replayability" become a publishable badge (per-claim, not a score)? Who issues it?
3. How should privacy-sensitive telemetry (per-user agent logs) be redacted while
   remaining auditable?
4. Should claim windows be time-stamped (e.g., trailing 30 days) to resist gaming?

---

*Related:* [Evidence Profile — standard/TRUST.md](../standard/TRUST.md) · [Core Specification](../standard/CORE.md) · [Pipeline Validation #001](../reports/pipeline-validation-001.md) · [Benchmark Run #001](../reports/benchmark-run-001.md) · [Whitepaper](../whitepaper/measuring-software-used-by-ai-agents.md)
