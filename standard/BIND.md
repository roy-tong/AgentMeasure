# AgentMeasure Bindings — Transport & Telemetry Bindings（Draft 0.1）

> **Core protocol 是 vendor-neutral、transport-neutral 的。** 以下是承载 AgentMeasure 的
> 现成传输/遥测绑定——它们是可行性证明，不是协议成立的前提。

## B1. MCP Binding（Transport）

| MCP 要素 | AgentMeasure 使用 |
| --- | --- |
| `tools/call`（协议调用） | S1/S2 生命周期事件的传输载体 |
| `_meta` trace context（2026-07-28 正式规范） | trace_id 传播 → Structural match（AgentMeasure Correlation） |
| `clientInfo {name, version}` | observer 身份线索（L1 识别，尽力而为） |
| MCP Registry | project/server 身份声明来源（非唯一） |

## B2. OTel Binding（Telemetry）

| OTel 要素 | AgentMeasure 使用 |
| --- | --- |
| `gen_ai.tool.name` / `gen_ai.tool.call.id` | tool / tool_call_id 语义字段 |
| Execute tool span | S1/S2 观察载体 |
| `trace_id` / `span_id` / parent-child | Structural match |
| OTLP Collector | 数据分流载体（参考实现消费侧脱敏） |

**参考实现只增加 6 个 `agentused.*` 扩展字段**（属性前缀沿用早期实现名，是技术标识）；evidence 是派生属性，
只出现在 Invocation/Attribution Record，不出现在 instrumentation span。

## B3. 绑定原则

1. 绑定可替换：未来新传输（如自定义协议）只需实现"承载 Receipt + commitment"
2. 绑定的能力边界决定 Profile 的能力矩阵（见 AgentMeasure-PROFILE-*）
3. 没有 trace 传播的传输仍可工作（Exact match + Commitment match 兜底）
