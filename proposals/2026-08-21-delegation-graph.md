# Proposal 0007 — Delegation：Agent 调 Agent 时的第四种语义对象

- 状态：Draft
- 作者：Roy Tong
- 日期：2026-08-21
- 相关：Core Draft 0.4（§对象模型）/ DATA.md / PROFILES.md / profiles/deepseek-harness.md

## 问题

Harness 之间的委托已经成为现实：DSH 的 subagent seam 可以把 Codex、Claude Code、
DSH SDK 注册为 provider（`dsh-subagent-codex` 等），带 parent lineage 与
delegation depth。但当前对象模型只有三层：

```text
Task → Operation → Attempt
```

当一个 Agent 把子目标交给另一个 Agent/Harness 时，这个事件**不是**：

- **Tool call**：委托的对象是 agent，不是 capability；
- **Operation**：没有逻辑 capability intent 被表达；
- **Attempt**：没有任何执行发生（执行发生在子 harness 里）；
- **Task**：它是父 task 内部的一个步骤，不是新的用户级目标。

不预先定义，"Codex 被 DSH 当 subagent 调一次"到底是 tool call、capability use、
delegation 还是 task，每个 adapter 会给出不同答案 —— 这是标准的漏洞，不是实现细节。

## 提案

### 1. 新增第四种语义对象：Delegation

```text
Task
├── Operation A
│    ├── Attempt 1
│    └── Attempt 2
└── Delegation ──▶ Subagent（另一 Harness）
                      └── Operation B
                           └── Attempt 3
```

**定义**：Delegation 是一个 agent 把子目标连同执行权交给另一个 agent（通常在
另一个 harness/runtime 中）的**决策与边界事件**。它记录"谁、为何、向谁、多深"，
不记录子侧执行细节。

### 2. 字段（Delegation 事件 payload）

| 字段 | 必填 | 说明 |
|---|---|---|
| `delegation_id` | ✅ | 本侧唯一 |
| `parent_task_id` | ✅ | 委托发生时的 task |
| `provider` | ✅ | 被委托 harness/agent 标识（如 `dsh-subagent-codex`） |
| `depth` | ✅ | 委托深度（顶层=0） |
| `lineage` | ◻ | 祖先链（DSH 可提供） |
| `subgoal` | ◻ | 委托意图（prompt 摘要或 hash） |
| `child_ref` | ◻ | 子侧可关联标识（session/cwd）；跨侧 correlation 证据 |

### 3. 规则

1. **Delegation 由委托方 harness 记录**（只有委托方看得到决策）；被委托方按普通
   Task/Operation/Attempt 记录自己的内部。
2. 跨侧关联至多 `correlated`（两个独立观察），**永不**声称为 corroborated
   （同一事件的重复确认）。
3. **计数纪律**：Delegation 计数不进入 Operation Count 或 Attempt Count；
   新增独立指标 `Delegations per Task`、`Delegation Depth`。计量图必须是 DAG。
4. **计费归属**：子 harness 内 attempts 的 cost 归属该 attempt 本身（sum(attempts)
   = money 不变）；父侧只聚合，不重复计。
5. Delegation 的 outcome（子任务是否达成）是**子侧 Task Outcome 的引用**，
   证据等级 `correlated`；父侧不得自行推断子任务成败。

### 4. 指标影响（METRICS 增补）

- `Delegation Rate` = delegations / tasks
- `Delegation Depth Distribution`
- `Cross-harness Share` = 涉及 ≥2 harness 的 task 占比
- 声明 Grain 时必须披露：delegation 是否可观察（profile 矩阵新增一行）

## 影响

- standard/CORE.md：对象模型新增 Delegation；计数纪律
- standard/DATA.md：observation_type 增 `delegation_started` / `delegation_completed`
- standard/PROFILES.md：能力矩阵加 Delegation 行（DSH ✅ / Claude Code ⚠️ / Codex ❌）
- schemas/observation.schema.json：payload 变体
- reference adapter：DSH session log → delegation 事件（首个实现源）

## 备选方案

1. **把 Delegation 当作特殊 Operation**（capability=agent）：否。会让
   Operation Count 语义污染（agent 不是 capability），计费与选择率全部失真。
2. **只在 correlation 层（CORR）表达**：否。委托是经济事件（谁替谁干活），
   必须是一等对象，否则 attribution 无法展开。
3. **等 ACP/MCP 标准化再定**：部分采纳 —— 字段命名对齐 ACP 术语，但对象语义
   现在就定，否则 cross-harness 实验数据无法比较。

## 开放问题

1. Continuable subagent（DSH 的多次 send_message 续话）算一次还是多次 Delegation？
   倾向：一次 Delegation + N 次 continuation 事件。
2. 委托失败（子 harness 启动即败）如何记？倾向：delegation_completed +
   outcome=failure，不产生子侧 attempts。
