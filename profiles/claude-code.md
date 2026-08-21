# AgentMeasure Harness Profile — Claude Code

> Draft 0.4.4。来源：Claude Code 公开文档（hooks、OTel telemetry、MCP 集成），
> 截至 2026-08。协议侧摘要见 standard/PROFILES.md P2。

## 1. Observable objects

| Claude Code 对象 | 说明 | 观察渠道 |
|---|---|---|
| Session | 会话（伪匿名后） | hooks / telemetry |
| Tool result（PostToolUse） | `tool_name / tool_use_id / success / duration_ms / error_type` | hook / OTLP |
| API request telemetry | **携带 `mcp_server.name` / `mcp_tool.name`** | OTLP |
| Trace | 请求链 | OTLP |
| Subagent（Task tool） | 内置子 agent 委托 | 工具调用形态 |

## 2. 语义映射

| Claude Code | AgentMeasure | 说明 |
|---|---|---|
| Session 内用户目标 | Task 候选（`declared`） | 无显式 task 对象 |
| Tool result（success/duration/error_type） | Attempt completed（**自带成败判定**） | 三个 harness 中唯一 |
| `mcp_tool.name` 出现在后续 request | **Consumption 信号** | tool_result(X) → 后续 request 引用 = 消费链 |
| Task tool 调用 | Delegation（`inferred`） | 无 lineage/depth 元数据，弱于 DSH |
| usage（tokens） | attempt_usage（model 层） | 归 request |

## 3. 关键规则

1. `observer_side=client, provenance=otel|hook`。
2. **Consumption 的第一个实证平台**：Invoked → Completed → Delivered → Consumed
   链条可闭合（reference/collector/consumption.py 已实现）。Consumption Rate 的
   分母纪律：consumption-observable eligible invocations。
3. Retry 无原生标记 → (name, args-hash) 推断，`inferred`。
4. Selection（候选呈现）不可观察。

## 4. 与 Delegation Graph 的关系

Claude Code 的 Task tool 产生子 agent，但缺少 DSH 那样的 parent lineage 与
depth 对象；子 agent 的工具调用若走独立 session，跨 session correlation 只能到
`structural`。这本身就是一个测量兼容性发现（见 experiments/EXPERIMENT-D）。

## 状态

Draft。Consumption 链已实证；Delegation 侧等待上游暴露 lineage 元数据。
