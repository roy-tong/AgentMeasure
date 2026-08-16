# agent-used

**An open usage attribution standard for software used by AI agents.**

> OpenTelemetry tells us how telemetry travels.
> **agent-used defines what counts as usage.**

agent-used 是一套面向 AI Agent 软件生态的开放 **Usage Attribution 标准与基础设施**。它从 Agent 侧与 Tool 侧采集调用证据，在 Codex、Claude Code、DeepSeek Harness、MCP 等不同运行环境之间统一数据口径，对双边事件进行关联与去重，并以明确的证据等级发布隐私保护后的使用统计。

**这不是又一个 Agent observability 工具。** Langfuse / Grafana 回答"我的 Agent 运行得怎么样"；agent-used 回答"整个生态里，哪些第三方工具真的被 Agent 使用"。

[《如何测量 Agent Tool Economy》（白皮书）](whitepaper/) · [Measurement Spec](spec/measurement-spec.md) · [English](README.en.md)

## 核心概念

### 使用漏斗：Install ≠ Usage

| 阶段 | 定义 | MVP |
| --- | --- | --- |
| S0 Selected | Agent 选择了该工具 | ✅ |
| S1 Executed | Runtime 实际执行了调用 | ✅ |
| S2 Execution Success | 工具成功返回 | ✅ |
| S3 Result Consumed | Agent 实际使用了返回结果 | 🔶 部分 |
| S4 Task Contribution | 结果对下游任务有贡献 | 🔬 研究 |

### 证据等级：签名 ≠ 真实

| 等级 | 名称 | 能证明什么 |
| --- | --- | --- |
| E0 Observed | 单边日志 | 某一方声称 |
| E1 Source-authenticated | 签名事件 | 来源与完整性 |
| **E2 Correlated** | 双边 trace 匹配（同一 trace_id） | **同一次真实调用（核心）** |
| E3 Platform-attested | 平台直接证明 | 平台确认 |

HMAC 只证明"数据来自持 key 主体且未被篡改"，不证明"真的有 Agent 调用"——所以证据是分级的，`corroborated usage`（E2）才是可信度核心。MCP 2026-07-28 RC 将 OTel trace context 纳入 `_meta`，使双边关联成为协议级现实。

### 指标：Raw Calls 不是北极星

- **Adoption**（首要）：Active Agent Sessions
- **Engagement**：Repeat Usage、7d/30d 回访率
- **Quality**：Execution Success / Result Consumption
- **Trust**：Corroborated Usage Share

排名按 sessions 而非 calls——防拆 API 刷榜。一次任务 6 次调用 ≠ 6 倍使用。

## 架构

```text
Public Usage Layer（Dashboard / API / Badge / Rankings / Trends）
        ▲   aggregated only
agent-used Attribution Layer
  Identity Resolution · Dedup · Cross-side Correlation
  Evidence Grading · Privacy Aggregation · Metric Normalization
        ▲               ▲
 Agent Adapters        Tool Adapters
  codex / claude / dsh   mcp / http / cli
        ▲               ▲
   OTel / MCP existing standards
```

agent-used **站在 OTel 之上**：复用 `gen_ai.tool.name`、`mcp.method.name`、trace 字段；只增加 6 个 `agentused.*` 扩展字段（[otel-mapping](spec/otel-mapping.md)）。

## 目录

```text
agent-used/
├── spec/          # 标准（测量/证据/指标/隐私/身份/威胁模型/OTel 映射）
├── adapters/
│   ├── codex/           # PostToolUse hooks → 本地事件
│   ├── claude-code/     # OTLP → agent-used Collector（设计）
│   ├── deepseek-harness/# DSH plugin（tools/pre-execute → post-execute，设计）
│   └── mcp/             # legacy zero-config wrapper（wrapper.py）
├── collector/
│   ├── normalizer/      # 跨 Agent 统一口径（待实现）
│   ├── correlator/      # 双边 trace 匹配 → E2（待实现）
│   ├── redactor/        # 默认 DROP 敏感字段（待实现）
│   └── aggregator/      # 本地统计 + 徽章 SVG（已有 aggregator.py）
├── registry/
│   └── project-identity/ # 项目身份映射（待填充）
├── examples/
└── whitepaper/          # 《如何测量 Agent Tool Economy》
```

## 隐私

**Raw telemetry stays local. Public infrastructure receives aggregates by default.**

prompt / tool_input / tool_output / path / raw session id——代码级默认 DROP（adapter 含泄漏测试）。伪匿名 installation id（本地 secret + 按月轮换）支持 unique installations 与 repeat usage，云端无法反推身份。`DO_NOT_TRACK=1` 全程生效。

## 路线图

| Stage | 目标 | 关键产物 |
| --- | --- | --- |
| M0 Definition | 讲清"什么算 Agent Usage" | ✅ Whitepaper + Measurement Spec + Threat Model |
| M1 Cross-Agent Proof | 证明跨 Agent 可统一 | Codex + Claude + DSH adapter |
| M2 OTel Native | 标准采集链 | Collector + OTel mapping + MCP adapter |
| M3 Attribution | 项目核心 | Identity Graph + Correlation + Evidence |
| M4 Public Network | 公开数据 | API + Dashboard + Badge |
| M5 External Validation | 指标是否真被需要 | 外部项目接入 + discrepancy report |
| M6 Ecosystem | 公共基础设施 | MCP / OTel / Agent Platform / Registry 合作 |

**不做的事**：不替代 OTel；不做自动 star/follow；不采集内容；不按 raw calls 排名；不在 M3 之前做聚合云。

## License

MIT
