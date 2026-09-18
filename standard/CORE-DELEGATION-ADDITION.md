# Delegation — CORE.md Draft 0.4.5 规范补充
# 以下为应插入 CORE.md 各处的完整文本，按插入点分块。

---

## 块 A：更新文档版本号

**位置**：第 1 行

**替换**：
```
# AgentMeasure Core Specification — Open Measurement Standard for AI-Agent Software Usage（Standard Compatibility agentmeasure-0.4 · Document revision 0.4.5）
```

---

## 块 B：在 §2.4 行为对象表中新增 Delegation 行

**位置**：在第 81 行（Operation 行）之后、第 82 行（Attempt 行）之前插入

**文本**：
```
| **Delegation** | Agent 将子目标连同执行权交给另一 Agent 的**边界事件**（Agent → Agent 调用）；与 Operation 同层，作为 Task 的直接子节点 | `delegation_id` |
```

**完整效果**（第 81–84 行变为）：
```
| **Operation** | 对某 Capability 的一次**逻辑使用**（为某 task 而用） | `operation_id` |
| **Delegation** | Agent 将子目标连同执行权交给另一 Agent 的**边界事件**（Agent → Agent 调用）；与 Operation 同层，作为 Task 的直接子节点 | `delegation_id` |
| **Attempt** | **标准执行对象**：一次实际执行（API request / MCP call / CLI execution / Agent-to-Agent call 统一映射为 Attempt）。**不可变事实对象**（Draft 0.4.4） | `attempt_id`（agentmeasure 自有 identity；外部 id 见 `external_ids`） |
```

---

## 块 C：更新谱系图（含 Delegation 分支）

**位置**：替换第 86–98 行（"完整谱系（一条链路）：" 及其后的代码块）

**替换文本**：
```
完整谱系（同 harness 内一条链路；Delegation 跨越 harness 时产生新的子链路）：

```text
Task ──▶ Decision Opportunity ──▶ Selection
                                       │
                                       ▼
                                   Operation ──▶ Attempt 1 ──▶ Result / Effect
                                       │             │  (retry)
                                       │             ▼
                                       │          Attempt 2 ──▶ Result / Effect
                                       │
                                  Delegation ──▶ [Sub-agent scope:
                                       │            Operation → Attempt …]
                                       ▼
                                   Outcome
```
```

---

## 块 D：新增 Delegation 定义子节（§2.4 内，在 Operation/Attempt 拆分之后）

**位置**：在第 123 行（"AgentMeasure Correlation 的确定性规则（不变量 23：无证据不归并）"）之后、第 125 行（"### 2.5 Decision Authority（决策主体）"）之前插入

**文本**：
```

**Delegation（Agent → Agent 调用，Draft 0.4.5）**：

**定义**：Delegation 是第四种语义对象，与 Operation 同层、作为 Task 的直接子节点：
一个 Agent（`delegating_caller`）把子目标连同执行权交给另一个 Agent（`called_agent`）的
**边界事件**。它记录"谁、为何、向谁、多深"，不记录子侧执行细节。

Delegation **不是**：
- **Operation**：没有对子侧 Capability 的直接逻辑 intent 表达；
- **Attempt**：执行发生在子 harness，不在父侧；
- **Task**：它是父 Task 内部的一个步骤，不是新的用户级目标。

### 标识与字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `delegation_id` | ✅ | 委托方侧唯一标识（`am-delegation-*`） |
| `delegating_caller` | ✅ | 发起委托的 Agent entity_id |
| `called_agent` | ✅ | 被委托的 Agent entity_id |
| `called_capability` | ✅ | 被调用的被委托方 Capability（如 `agent:accept_subtask`） |
| `parent_task_id` | ✅ | 委托发生时的 task_id |
| `depth` | ✅ | 委托深度（顶层 = 0；子侧 depth = 父 depth + 1） |
| `lineage` | ◻ | 祖先链（`delegation_id` 序列） |
| `subgoal` | ◻ | 委托意图（prompt 摘要或 hash） |
| `child_ref` | ◻ | 子侧可关联标识（session_id / task_id）；跨侧 correlation 证据 |

### 计数纪律（Counting Discipline）

1. **Delegation 不进入 Operation Count 或 Attempt Count**。Delegation 是独立计数对象，
   新增指标 `Delegations per Task`、`Delegation Depth Distribution`。
2. **一个 Delegation ≠ 一个 Operation**。一个 Delegation 可能对应子侧的 0..N 个
   Operation（子 harness 自行解析其 Operation 与 Attempt）；父侧不预测也不取代子侧计数。
3. **计量图必须是 DAG**。Delegation depth 有实现定义的上限（default MAX_DELEGATION_DEPTH）；
   环状委托（A → B → A）MUST 被检测并拒绝。
4. **计费归属**：子侧 Attempt 的 cost 归属该 Attempt 本身（sum(attempts) = money 不变）；
   父侧只聚合 cost，不重复计；aggregation MUST 标注为 `aggregated`。

### 跨侧跟踪（Cross-side Tracking）

- Delegation 由**委托方 harness** 记录（只有委托方看得到决策上下文）；
  被委托方按普通 Task / Operation / Attempt 记录自己的内部。
- 跨侧关联至多 `correlated`（两个独立观察），**永不**声称为 `corroborated`
  （同一事件的重复确认）。
- Delegation 的 outcome 是**子侧 Task Outcome 的引用**，证据等级 `correlated`；
  父侧不得自行推断子任务成败。
- 跨侧 cost attribution 由 lineage 追溯实现：父侧可聚合 `sum(depth=N attempts.cost)`，
  但 attribution 声明 MUST 标注为 `aggregated`（非直接观测）。

### 与现有对象的关系

| 关系 | 说明 |
|---|---|
| Task → Delegation | Task 可包含 0..N 个 Delegation（以及 0..N 个 Operation） |
| Delegation → Operation（子侧） | 子侧 Operation 由子侧 harness 独立记录，通过 `child_ref` 跨侧关联 |
| Delegation → Attempt（子侧） | 同上，跨侧关联 |
| Delegation → Outcome | Delegation Outcome 是子侧 Task Outcome 的 `correlated` 引用 |
```

---

## 块 E：在 §3 Measurement Grain 表中新增 Delegation 行

**位置**：在第 181 行（Execution 行）之后、第 182 行（Utility 行）之前插入

**文本**：
```
| **Delegation** | **Delegation** |
```

**完整效果**（第 179–184 行变为）：
```
| Distribution | Client / Client-Day |
| **Choice** | **Decision Opportunity** |
| Execution | Attempt（标准执行对象） |
| **Delegation** | **Delegation** |
| Utility | Result / Attempt |
| Outcome | Task / Operation |
```

---

## 块 F：更新不变量文本（第 186 行）

**位置**：第 186 行

**替换**：
```
**不变量：不同 Grain 的指标不可互换。** 10 attempts ≠ 10 operations ≠ 10 delegations ≠ 10 decision
opportunities ≠ 10 tasks。任何指标必须声明 Grain。
```

---

## 块 G：在 §9 标准不变量中新增 Delegation 专属不变量

**位置**：在第 303 行（不变量 24）之后、第 305 行（"## 10. 分层"）之前插入

**文本**：
```
27. **Delegation MUST NOT 被压平为调用方的 Operation。** Delegation 是独立的语义对象，
    不得计入 Operation Count 或 Attempt Count（不变量 25 的补充）。
28. **Delegation 计数必须在 delegating_caller 与 called_agent 两侧均可追溯。**
    跨侧关联至多 `correlated`，不得声称 `corroborated`。
29. **Delegation Outcome 是子侧 Task Outcome 的 `correlated` 引用。**
    父侧 MUST NOT 自行推断子任务成败。
30. **计量图 MUST 是 DAG。** 环状委托 MUST 被检测并拒绝；delegation depth
    有实现定义的上限（default MAX_DELEGATION_DEPTH）。
31. **子侧 Attempt 的 cost 归属该 Attempt 本身。** 父侧聚合 MUST 标注为 `aggregated`。
```

---

## 块 H：在 §11 文档结构中新增 Delegation 相关提案引用

**位置**：在第 331 行（proposals/ 行）之后、第 332 行（文件尾）之前插入

**文本**：
| proposals/2026-08-21-delegation-graph.md | Delegation 对象提案与设计决策记录 |
```