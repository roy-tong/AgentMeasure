# Agent Usage Measurement Spec v0.1（草案）

> agent-used 的核心规范。回答一个问题：**对 AI Agent 使用的软件，什么才算一次"真实使用"？**
> 原则：不重复定义 OTel/MCP 已有字段；只定义它们不覆盖的语义层。
> 状态：草案，随白皮书 v1 与外部讨论演进。

## 1. 定位

**OpenTelemetry tells us how telemetry travels. agent-used defines what counts as usage.**

本规范定义 Agent 生态中"使用归因"（Usage Attribution）的语义模型：

- 什么算一次使用（Selection → Execution → Success → Consumption → Contribution）
- 使用属于谁（Identity）
- 使用有多可信（Evidence Level）
- 不同 Agent / Tool 之间如何可比（Normalization + Metrics）
- 如何公开统计而不泄露用户信息（Privacy）

agent-used 是 OTel 之上的语义层，不是替代品。

## 2. 使用漏斗（The Usage Funnel）

**Install ≠ Usage。** 任何一层都不能替代下一层：

| 阶段 | 定义 | 谁可观察 | MVP 范围 |
| --- | --- | --- | --- |
| **S0 Selected** | Agent 选择了该工具（如 tools/list 命中、skill 加载） | Agent runtime | ✅ |
| **S1 Executed** | Runtime 实际执行了该工具（tools/call 发起） | Agent runtime + Tool runtime | ✅ |
| **S2 Execution Success** | 工具成功返回（无 error） | 双侧 | ✅ |
| **S3 Result Consumed** | Agent 实际使用了返回结果（后续上下文引用/继续任务） | Agent runtime（部分） | 🔶 部分 |
| **S4 Task Contribution** | 工具结果对下游任务完成有贡献 | 研究方向 | 🔬 研究 |

**度量纪律**：
- 一次任务内的 6 次重复调用 ≠ 6 倍使用（见 metrics.md 的 Engagement 层）
- 失败重试链 `call → fail → retry → success` ≠ 3 次使用（按 session 归一）
- 公开指标默认以 **Active Agent Sessions** 为首要口径，raw call count 只是 supporting metric

## 3. 证据等级（Evidence Level）

**签名 ≠ 真实。** HMAC 只证明"数据来自持 key 主体且未被篡改"，不证明"真的有 Agent 调用"。因此用证据等级取代"调用是真的"这种二元判断：

| 等级 | 名称 | 来源 | 能证明什么 | 公共统计可信度 |
| --- | --- | --- | --- | --- |
| **E0 Observed** | 单边本地日志 | 某一方声称发生调用 | 低 |
| **E1 Source-authenticated** | 签名事件（Tool 或 Agent 侧） | 数据来源与完整性 | 中低 |
| **E2 Correlated** | Agent-side + Tool-side 双边匹配（同一 trace_id / tool_use_id） | 双边独立观察到同一次真实调用 | 高 |
| **E3 Platform-attested** | Agent 平台 / trusted runtime 直接证明 | 平台确认调用发生 | 很高 |

**corroborated usage（E2+）是本项目的核心可信度指标。** MCP 2026-07-28 RC 将 OTel trace context（traceparent/tracestate/baggage）纳入 `_meta` 传递，使 client/server 双边关联首次成为协议级现实——这是 E2 的技术基础。

```
Tool Server                 MCP                    Agent Host
  span A                  trace_id=abc              span B
  trace_id=abc                                      tool_use_id=X
```

当 agent-used 同时获得 `{codex: tool_use_id=X, trace_id=abc, tool=foo.search}` 与 `{mcp server: trace_id=abc, tool=foo.search, success}`，即构成 **corroborated usage**。

## 4. 统一使用模型（Unified Usage Model）

所有 adapter 输出统一映射到以下模型（跨 Agent 归一化的目标）：

| 字段 | 说明 | 来源示例 |
| --- | --- | --- |
| `project` | 归一的项目身份（见 identity.md） | github.com/foo/bar |
| `agent.host` | 宿主标识 | codex / claude-code / deepseek-harness |
| `session` | 伪匿名会话标识（旋转） | pid-xxxxx |
| `tool` | 工具名（跨实现归一） | foo.search |
| `stage` | S0-S4 漏斗阶段 | S1 / S2 |
| `evidence` | E0-E3 | E2 |
| `outcome` | success / failure / retry / denied | success |
| `duration` | 粗粒度耗时 | 10s-60s |
| `trace_id` | OTel trace 关联 | abc |
| `observer.side` | client / server / platform | client |

## 5. 规范范围与边界

**本规范定义**：语义、证据、身份、指标、隐私、威胁模型。

**不定义**（复用已有标准）：
- 传输格式与 trace 传播：OpenTelemetry / MCP `_meta` trace context
- 工具调用协议：MCP tools/call
- 基础指标字段：`gen_ai.tool.name`、`mcp.method.name`、`error.type`、`service.name`、`trace_id`、`span_id`（见 otel-mapping.md）

**明确不做**：任何形式的自动 star/follow、内容采集、排名激励（防拆 API 刷榜，见 metrics.md）。

## 6. 配套文档

- `otel-mapping.md` — agent-used 在 OTel 之上的最小扩展字段
- `evidence-model.md` — E0-E3 详细定义与判定规则
- `metrics.md` — 四层指标（Execution / Adoption / Engagement / Contribution）
- `privacy.md` — Raw stays local, aggregates by default
- `identity.md` — Canonical Identity Graph
- `threat-model.md` — 攻击面与缓解
