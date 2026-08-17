# Outreach Strategy（公开版）

> 本文档只描述**策略**。目标名单、邮箱、发送/回复记录等运营数据属于
> 私有运营资产（local ops / publish_agent/outreach/），不在此仓库维护。

## 1. 目标

**External Provider #001 → Real Traffic → Measurement Report #001 → 一个真实
Actionability Case。**

成功定义：第一个外部 Provider 接入后，AgentMeasure 告诉了他一件他原来不知道的
事实（以及一件"以当前 lineage 无法知道"的事实），并且他因此改了产品。

## 2. 分池（2026-08 修订：MCP 项目 ≠ Measurement Alpha 项目）

| Pool | 目标 | 说明 |
|---|---|---|
| **A — Measurement Alpha** | 有真实远程/长期 server 流量 | **唯一能产出 Report #001 的池**：Remote MCP / Hosted MCP / SaaS-backed MCP / 长期 self-hosted MCP，**合作方自己控制运行中的 server process** |
| **B — SDK Implementer** | 本地 MCP 项目 | 验证 SDK 兼容性与标准语义；观察发生在最终用户电脑上，维护者看不到调用边界 |
| **C — Runtime Partner** | Codex / Claude / 1MCP / Harness | 补 Reach / Choice / Operation lineage（Provider-side SDK 看不到的层） |
| **D — Standard / Trust Partner** | observability / receipt / evaluation / payment | Agent Receipts（Obsigna）、Horizon3/NodeZero 等 evidence/trust 项目——interop 合作而非竞品 |
| **E — Strategic Logo** | Neon / Sentry / Cloudflare / GitHub / Apify | 先有 Pool A 真实案例，再谈 logo |

**Partner Strategy 定位（2026-08 升级）**：从"找 MCP developer"正式升级为

> **找拥有 Agent Capability Runtime Boundary 的人。**

目标池是：Hosted SaaS MCP · Remote MCP · Agent-facing API · MCP Gateway/Runtime ·
Agent Observability Platform · Agent Commerce Infrastructure。候选池从"海量但
质量差"缩到 100–300 个真正关键的 Provider——早期用**高密度 BD**，不广撒网。

纪律：第一批发出的 13 封多数属于 Pool B（本地/stdio MCP）。它们是有效的
SDK/标准验证对象，但第一份真实 Measurement Report 必须来自 Pool A。缺口在 A。

## 2.1 Opportunity Score（候选排序）

\[
Opportunity = 0.30\,B + 0.25\,D + 0.20\,M + 0.15\,T + 0.10\,L
\]

- **B — Boundary Control**：是否控制真实线上 Provider boundary
- **D — Decision Accessibility**：维护者是否容易直接决定
- **M — Measurement Fit**：数据是否能产生有意义指标
- **T — Traffic Probability**：真实 Agent 流量概率
- **L — Logo / Leverage**：品牌与传播价值

现阶段小团队（B/D 高）可以比大品牌（L 高）更值得联系：现在需要的是
YES → integration → traffic → report，而不是 great brand → forwarded →
meeting → security → legal → three months。当前各目标评分见私有运营区。

## 3. 核心话术（2026-08 修订）

不主打"我们能告诉你多少调用来自 Agent、多少是重试"（很多情况下做不到）。

统一卖点：

> **AgentMeasure tells you what can actually be known about your agent traffic —
> and what is still unknowable.**

下面接：

> Which calls carry attributable agent identity?
> Which remain unknown?
> How reliable are the executions?
> How much of the traffic can actually be resolved into logical operations?

对 Pool C/D 的邮件不用"装 SDK"框架，改用：

> 我们的 measurement model 和你们的 runtime/evidence model 有一块天然可以
> 互补，想一起定义 interoperability。

## 3.1 三种邮件原型（不再所有人同一版）

**A — 小型 Provider / Founder**（Sugra、Senado、独立 hosted MCP）
核心是 "I can do the integration work for you"，不是 "Please install our SDK"：
10–15 min · private alpha · 不要求公开原始数据 · 我可以帮你做/提交 patch ·
你拿到第一份私有 measurement report。

**B — 已有 telemetry 的 Provider**（Postman / Apify / Grafana / Rootly）
绝不说 "We built an analytics SDK"。说：

> You already collect most of the raw facts. AgentMeasure is an attempt to make
> those facts portable and comparable across agent-facing software.

合作形态可以是 `现有 telemetry → AgentMeasure adapter → Canonical Observation
Envelope`，根本不一定装 SDK。

**C — 大型官方 Hosted MCP**（Figma / Vercel / Slack / GitLab / Google / Cloudflare / Atlassian）
目标不是 alpha user，而是**标准共建者**：

> We're working on an open measurement vocabulary for agent-facing capabilities,
> and your hosted MCP is one of the clearest examples of the problem we're trying
> to standardize.

邀请：review semantics · identify missing fields · explore adapter/telemetry mapping。

## 4. 节奏（控制式 cadence）

1. 每批只补发 5–8 个最高匹配对象（不连续轰炸）；
2. 发出后 24–72h 观察回复模式：没兴趣 / 看不懂 / 安装麻烦 / 不拥有
   server-side traffic；
3. 有人表示兴趣 → 立即从 outbound 切成 **concierge onboarding**（可以直接
   替他做 PR，不要求他自己安装）；
4. 第一个 Alpha 默认 **Private**（报告只发给 Provider；公开需显式 opt-in）；
5. 第 5–7 天只 follow-up 一次，无回复即结束（每目标最多 2 次触达）。

## 5. 落地工具

- 发送：`publish_agent/send_email.py`（CDP 驱动 Gmail，限速 60–150s，断点续发）
- 队列/记录：`publish_agent/outreach/`（queue.json / log.jsonl / TARGETS.md）——
  **私有运营资产，不在本仓库**
- 合作方 landing：Issue #2（内容由 `docs/ISSUE-2.md` 驱动，push 时自动同步）
- 报告模板：`reports/pipeline-validation-001.md` 之后的第一份真实报告编号为
  **Measurement Report #001**（预留给外部 Provider）

## 6. 当前状态

- 2026-08-17：第一批 13 封（多为 Pool B）已发；第二批 5–8 封（Pool A 优先）
  准备中；funnel 记录在私有运营区。
