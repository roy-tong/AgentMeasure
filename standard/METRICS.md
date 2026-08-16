# AgentMeasure Metrics — Metric Registry（Draft 0.4）

> **本文件是 AgentMeasure 变更最频繁的文档。** 每个正式指标必须携带完整合同（Metric
> Contract），使任何独立实现输入相同数据算出相同数字。
> 指标变更走 AUP（`proposals/`）。
>
> **Draft 0.4 变更**：M2.2 更名为 *Observed Selection Rate*（observed ≠ preference）；
> 比较类指标新增 Decision Authority / Selection Constraint 披露轴；
> M3 家族明确 Attempt（= Invocation）粒度与 Operation 计数对象。

## 0. Metric Contract 模板

```text
Metric ID            AgentMeasure-M<family>.<n>
Name
Purpose
Measurement Object
Measurement Grain
Numerator
Denominator
Formula
Eligibility（进入分母的资格）
Exclusions（明确排除）
Observable States（哪些状态可进入）
Unknown Handling
Required Dimensions
Optional Dimensions
Aggregation Rules
Dedup Rules
Coverage Requirements
Evidence Requirements
Reporting Window
Minimum Sample Size
Measurement Label Requirements
Examples
Counterexamples
```

## 1. Choice Family（M2，Grain = Decision Opportunity）

### M2.1 — Presented Opportunities

- **Purpose**：Reach 的选择面——Tool 有多少次进入决策上下文
- **Object**：Tool Presentation；**Grain**：Decision Opportunity
- **Numerator**：该 Tool 的 eligible Tool Presentations
- **Denominator**：无（计数指标）
- **Eligibility**：presentation 可观察且 Context ∈ {production}、Validity ∈ {normal}、Choice Mode 已声明
- **Exclusions**：available 但未 presented；UNOBSERVABLE runtime；synthetic/benchmark/test
- **Unknown**：context/validity 为 unknown 时不计入 Strict，单列披露
- **Dedup**：同 decision 同 tool 只计 1（presentation_id 唯一）
- **Label 要求**：grain、choice mode 分布、unknown shares

### M2.2 — Observed Selection Rate

- **Purpose**：Agent 有机会选择 Tool 时，**观察到**选择该 Tool 的比率
- **Object**：Selection / Presentation；**Grain**：Decision Opportunity
- **Numerator**：Tool 被 Selected 的 eligible Decision Opportunities
- **Denominator**：Tool 被 Presented 的 eligible Decision Opportunities
- **公式**：`Observed Selection Rate = Observed Selected Opportunities ÷ Presented Opportunities`
- **Eligibility**：双侧可观察（presented + selected）；Strict Qualified
- **Exclusions**：available-not-presented；presentation UNOBSERVABLE；不同 Choice Mode 混合比较
- **Unknown**：presented 不可观察的 runtime 不进入分母
- **Required Dimensions**：choice_mode；**decision_authority**；**selection_constraint**（三轴见 Core §6）
- **注意（Observed ≠ Preference）**：required/forced 的"选择"不是偏好。跨
  authority/constraint 比较 MUST 声明标准化方法，或按轴分层报告
- **Counterexample**：Agent 一天看到 Exa 10 次选 1 次 → 10% 而非 100%；
  policy 强制选 Exa 的 100% 与 model 自主选 Exa 的 100% 含义不同

### M2.3 — Presentation Share

- **Purpose**：谁进入 Agent 决策上下文最多（类别内）
- **公式**：`Tool Presentations ÷ Category Presentations`
- **Grain**：Decision Opportunity；**Category**：`category_id + category_version`
- **Eligibility**：category 归属可判定

### M2.4 — Selection Share

- **Purpose**：实际发生的选择中谁占最多（类别内）
- **公式**：`Tool Selections ÷ Category Selections`
- **Grain**：Decision Opportunity
- **Required Dimensions**：decision_authority / selection_constraint（同 M2.2）

### M2.5 — Conditional Choice Share

- **Purpose**：A 与 B 实际同台竞争时的选择偏好（最表达 Agent Preference）
- **公式**：`A selected ÷ (A+B selected)`，仅限 A、B 同时出现在同一 Candidate Set 的 decision
- **Eligibility**：同 candidate_set_id、同 category、同 Choice Mode、同窗口
- **Required Dimensions**：decision_authority / selection_constraint——同轴竞争默认；
  混轴时 MUST 披露（如 64% 是 model 自主竞争下的偏好，policy 强制场景另计）
- **Counterexample**：全局 SoC 高不意味直接竞争中胜出（Exa vs Tavily 同台 10,000 次选 6,400 → 64%）

## 2. Execution Family（M3，Grain = Attempt，对象 = Operation / Attempt）

> Draft 0.4：**重试 = 同一 Operation 的多个 Attempt**（Core §2.4）。
> Operation 是逻辑调用计数对象；Attempt 是执行计数对象。

### M3.1 — Logical Invocations

- **Purpose**：实际执行的逻辑调用数（重试/重复归一后）
- **Object**：Operation；**Grain**：Operation
- **公式**：`COUNT(DISTINCT operation_id)`；无 operation_id 的旧数据回退
  `COUNT(DISTINCT invocation_id)`（0.3 兼容，Label 披露 `operation_resolution`）
- **Eligibility**：Strict Qualified；**Dedup**：结构性——同 operation 多 attempt 只计 1
- **Label 要求**：`attempts_per_operation`（均值/分布，公开披露）

### M3.2 — Completion Rate

- **公式**：`Completed Attempts ÷ Invoked Attempts`
- **Grain**：Attempt；Operation 级完成率可由 attempt 聚合（须声明口径）
- **Observability**：UNOBSERVABLE 的完成状态不计入分母（不视为未完成）

### M3.3 — Success Rate

- **公式**：`Successful Completed Attempts ÷ Completed Attempts`
- **注意**：outcome=inconsistent（双侧冲突）不计入 success，单列披露
- **Unknown**：outcome=unknown 不计入分母，披露 Unknown Outcome Share
- **重试**：同一 operation 的失败 attempt 与成功 attempt 分别计数；
  operation 级成功率（至少一次成功）另列披露

## 3. Utility Family（M4，Grain = Result / Invocation）

### M4.1 — Result Consumed Rate

- **Purpose**：返回的结果有没有被 Agent 实际消费
- **公式**：`Consumed Results ÷ Consumption-observable eligible invocations`
- **Eligibility**：仅 consumption 可观察的 runtime/调用进入分母
- **Observability**：Codex 等不可观察面 → UNOBSERVABLE，**绝不记为未消费**
- **Counterexample**：99% success + 32% consumed vs 94% success + 81% consumed——后者更有用
- **Draft 0.4**：本指标度量 **Result**（返回值被消费）；Effect（世界改变）属于
  0.5 的验证型 Utility 指标（Core §2.7 不变量 22）

## 4. Distribution Family（M1，Grain = Client / Client-Day）

### M1.1 — Active Clients

- **Purpose**：采用广度
- **公式**：`COUNT(DISTINCT client_key)`（窗口内 ≥1 次 Strict Qualified eligible invocation）
- **Grain**：Client；**Eligibility**：Strict Qualified
- **Unknown**：client 不可解析/无标识的调用不计入，披露 Identity Coverage

## 5. 指标之间的纪律

1. 不同 Grain 的指标不可互换（不变量 16）
2. 每指标必须披露：Numerator / Denominator / Observable population / Qualified population / Runtime coverage / Choice mode / **Decision authority / Selection constraint**（Measurement Label）
3. Strict Qualified Usage（production+normal）是公共口径默认；Extended（+unknown）仅研究用
4. 最小样本量门槛内不发布比率（privacy_threshold）
5. Category 绑定 `category_id + category_version`，SoC 类指标必须声明
6. 比较类指标三轴声明：Choice Mode × Decision Authority × Selection Constraint（不变量 24）

## 6. 待 AUP 的指标（Draft 0.4 不正式化）

- First-choice Rate、Substitution/Switch Rate、Dependency、Substitutability
- Task Success Association、Incremental Lift（实验设计见 AgentMeasure 0.5）
- Effect 类 Utility（世界状态改变验证，见 Core §2.7）
