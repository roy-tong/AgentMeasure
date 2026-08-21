# AgentMeasure Harness Profile — Codex（OpenAI Codex CLI / App Server）

> Draft 0.4.4。回答一份固定问卷：这个 harness 能可靠观察到什么、什么观察不到、
> 如何映射到 AgentMeasure 语义对象。协议侧摘要见 standard/PROFILES.md P1；
> 本文是完整 Profile。来源：Codex CLI 公开文档与 `codex proto` / App Server JSON-RPC
> 接口（截至 2026-08，开发者预览，字段可能变化）。

## 1. Observable objects

| Codex 对象 | 说明 | 观察渠道 |
|---|---|---|
| Thread / Session | 一次会话（rollout 持久化） | rollout 文件 / App Server `thread/*` |
| Turn | 一轮用户输入驱动的 loop | session 事件流 |
| Tool Call（`tool_use`） | 一次工具调用意图 | PostToolUse hook / 事件流 |
| Tool Result | 工具返回 | 事件流 |
| Model request / usage | tokens、模型名 | 事件流（usage 归 request） |
| Approval 事件 | 命令批准/拒绝 | 事件流 |

## 2. 语义映射

| Codex | AgentMeasure | 说明 |
|---|---|---|
| Thread 内一个用户目标 | Task 候选 | Codex 无显式 task 对象；线程级目标需调用方声明 |
| Turn | Execution Context（粒度披露） | turn ≠ operation，不得混用 |
| `tool_use`（PostToolUse） | Attempt started/completed | 一个 tool_use = 一个 attempt 候选 |
| 同名工具、同意图的重发 | `retry_of` 关系 | Codex 不自带 retry 标记，需 adapter 用 (name, args-hash, turn) 推断 → `inferred` |
| 无 | Delegation | Codex 无内置 subagent 概念；被 DSH 作为 provider 调用时，**在 DSH 侧**记为 Delegation |
| Model usage | attempt_usage（model 层） | 与 tool 层 attempt 分开记 |
| Rollout / 事件流本身 | external_ids（correlation 证据） | 非 measurement unit |

## 3. 可靠性矩阵

- **可靠**：`tool_name`、`tool_use_id`、session（伪匿名后）、model、turn 边界。
- **不可靠（官方 PostToolUse schema 无）**：trace_id、精确时间戳、成败判定、duration。
- **不可观察**：Consumption（结果是否进入下游推理不可见 → UNOBSERVABLE，
  绝不记为未消费）；Selection 过程（候选集如何被呈现/筛选发生在模型内部）。

## 4. Adapter 规则

1. `observer_side=client, provenance=hook|platform`。
2. outcome 默认 `unknown`；只有从 result payload 推断时标 `inferred`。
3. 关联能力：Exact（tool_use_id）；无 trace → Structural/Commitment 依赖工具侧。
4. App Server 双向 JSON-RPC 是更完整的观察面（含事件流与 usage），adapter 应优先
   走 App Server 而非仅 hook，并在 `provenance` 中区分 `hook` 与 `platform`。

## 5. 与 Delegation Graph 的关系

Codex 作为 **被委托方**：当 DSH 通过 `dsh-subagent-codex` 调起 Codex 时，
Delegation 事件由 **DSH 侧**（委托方 harness）记录；Codex 内部的 tool calls
由 Codex 侧记录为普通 attempts。两侧用 parent lineage（DSH 传入的 cwd/session
标识）做跨 harness correlation —— 证据等级至多 `correlated`，不得声称为同一
观察的重复确认。

## 状态

Draft。等 Codex App Server 接口稳定后升级；差异反馈走 Discussions。
