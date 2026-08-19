# AgentMeasure Interoperability Profile — Pydantic AI

> Draft 0.4.4 / 0.5 方向。Pydantic AI / Logfire 已覆盖大部分 agent 生命周期 observation；
> 本 profile 定义其执行层对象 → AgentMeasure 语义对象。

## 映射表

| Pydantic AI | AgentMeasure | 说明 |
|---|---|---|
| `AgentRun` | Task / Operation 候选 | 一次 run 是一个 operation 候选；内嵌多次 model/tool 执行 |
| `ModelRequest` | Attempt（model 层）| 一次 provider 请求 = 一个 attempt |
| `FunctionToolCallEvent` | Attempt（tool 层）| 一次 tool 执行 = 一个 attempt |
| `ModelRetry` | `retry_of` relationship | retry 是关系不是 outcome（DR-001）|
| `RunUsage`（requests/tokens/tool_calls） | attempt_usage（消费归 attempt）| `RunUsage.tool_calls` **NOT automatically Operation Count** |
| `RunResult` | candidate Result / Outcome evidence | 是否被下游消费 → Use vs probe |
| `AgentRunResult` / span 结构 | external_ids（correlation 证据）| Logfire span 是 observation evidence，非 measurement unit |

## 关键规则
1. Pydantic 的 `RunUsage` 是 attempt 层聚合：同一 run 内多次 request 各自有 usage；合并为
   operation 时**不得把 attempt 级 consumption 去重**（sum(attempts) = money）。
2. 序列化 roundtrip 丢失 usage（pydantic-ai issue #5744）→ 正是 attempt ledger 不可变的理由：
   事实对象 identity 与外部协议 id 分离后，roundtrip 不丢 facts。
3. `ModelRetry` → `attempt_2.retry_of = attempt_1`；operation 计数 = 1（intent 未变），
   attempts 计数 = 2（DR-002 共识：Arthi/Suraj/김지훈）。

## 状态
Draft。目标：Pydantic 团队确认 mapping 后升级为合作 profile（Interop Collaboration）。
