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
| **D — Standard / Trust Partner** | observability / receipt / evaluation / payment | Agent Receipts（Obsigna）等 evidence/receipt/trust 项目——interop 合作而非竞品 |
| **E — Strategic Logo** | Neon / Sentry / Cloudflare / GitHub / Apify | 先有 Pool A 真实案例，再谈 logo |

纪律：**第一批发出的 13 封多数属于 Pool B**（本地/stdio MCP）。它们是有效的
SDK/标准验证对象，但第一份真实 Measurement Report 必须来自 Pool A。缺口在 A。

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
