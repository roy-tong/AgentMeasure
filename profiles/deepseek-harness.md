# AgentMeasure Harness Profile — DeepSeek Harness（DSH）

> Draft 0.4.4。来源：deepseek-harness 仓库 `docs/subsystems/`（session.md /
> subagent.md，master@2026-08）。DSH 处于开发者预览，事件词汇表可能随插件演化。

## 1. Observable objects

DSH 的核心事实：**Session 是 append-only 的 `SessionEvent` 日志**，消息历史由日志
派生。这意味着 DSH 是目前 harness 侧观察保真度最高的平台之一。

| DSH 事件 | 说明 | AgentMeasure 映射 |
|---|---|---|
| `user/message` | 用户输入 / 注入上下文 / steering | Task 候选边界（intent 证据） |
| `assistant/message` | 模型输出，**携带 usage（token）**，`interrupted` 标记 | attempt_usage（model 层） |
| `tool/call` | `{turn, step, callId, name, arguments}` | Attempt started |
| `tool/result` | 与 callId 配对 | Attempt completed |
| `todo/write` | 整表快照 | Execution Context（非计量单位） |
| subagent 工具调用 | `ctx.subagents`（spawn-in-process / fork / acp / codex / claude-code / dsh-sdk） | **Delegation** |
| `hook/invoked` / `hook/result` | hook 桥的 log-only 记录 | provenance=hook 的旁证 |

## 2. 关键映射规则

1. **配对**：`tool/call` ↔ `tool/result` 通过 `callId` 原生配对（Exact 关联）。
   注意：harness 内配对只证明**生命周期完成**（completed lifecycle observation），
   不构成独立 outcome 佐证。
2. **Retry**：DSH 不产 retry 标记；同 (name, arguments-hash) 的重复 `tool/call`
   在统计层建 `retry_of` —— 证据等级 `inferred`（DR-001：retry 是关系不是 outcome）。
3. **Subagent = Delegation，不是 Operation**。`SubagentStartRequest` 携带
   `parent`（lineage + delegation depth）。映射：
   - Delegation 事件在**委托方（DSH）**记录，payload 携带 provider 名
     （codex / claude-code / dsh-sdk…）与 depth；
   - 子 agent 内部的 attempts 由子 harness 侧观察；
   - 跨侧只做 correlation（`correlated`），不产生 corroborated。
4. **Usage**：`assistant/message.usage` 归属该 step 的 model attempt；
   sum(attempts) = money，合并为 operation 时不得去重。
5. **Task**：DSH 无显式 task 对象；`user/message` 到下一条非 steering 的
   `user/message` 之间的区间是 Task 候选 → `declared`，除非有外部 task id。

## 3. 可靠性矩阵

- **可靠**：callId 配对、turn/step 结构、usage（adapter 上报时）、subagent
  lineage/depth、append-only 重放。
- **不可靠**：Selection 过程（哪些 capability 被呈现给模型 — 发生在上下文构造
  内部）；Consumption（结果是否被后续推理使用）。
- **插件扩展事件**（compaction、hook bridge 等）不是 SurfaceEventType，adapter
  不得当作计量事件。

## 4. 为什么 DSH 对 AgentMeasure 特别重要

DSH 把"Agent 调 Agent"做成了显式的、带 lineage 和 depth 的对象。这是
Delegation Graph（见 proposals/2026-08-21-delegation-graph.md）第一个
真实存在的数据源：一次任务里 3 个 Agent、2 个 Harness、N 个 capability
的链路，在 DSH 的事件日志里是可重建的。

## 状态

Draft。随 DSH 预览版演化维护；字段变更走 profile issue。
