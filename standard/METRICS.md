# AgentMeasure Metrics — Metric Registry（Draft 0.3）

> **本文件是 AgentMeasure 变更最频繁的文档。** 每个正式指标必须携带完整合同（Metric
> Contract），使任何独立实现输入相同数据算出相同数字。
> 指标变更走 AUP（`aup/`）。

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

### M2.2 — Selection Rate

- **Purpose**：Agent 有机会选择 Tool 时选择该 Tool 的概率
- **Object**：Selection / Presentation；**Grain**：Decision Opportunity
- **Numerator**：Tool 被 Selected 的 eligible Decision Opportunities
- **Denominator**：Tool 被 Presented 的 eligible Decision Opportunities
- **公式**：`Selection Rate = Selected Opportunities ÷ Presented Opportunities`
- **Eligibility**：双侧可观察（presented + selected）；Strict Qualified
- **Exclusions**：available-not-presented；presentation UNOBSERVABLE；不同 Choice Mode 混合比较
- **Unknown**：presented 不可观察的 runtime 不进入分母
- **Counterexample**：Agent 一天看到 Exa 10 次选 1 次 → 10% 而非 100%

### M2.3 — Presentation Share

- **Purpose**：谁进入 Agent 决策上下文最多（类别内）
- **公式**：`Tool Presentations ÷ Category Presentations`
- **Grain**：Decision Opportunity；**Category**：`category_id + category_version`
- **Eligibility**：category 归属可判定

### M2.4 — Selection Share

- **Purpose**：实际发生的选择中谁占最多（类别内）
- **公式**：`Tool Selections ÷ Category Selections`
- **Grain**：Decision Opportunity

### M2.5 — Conditional Choice Share

- **Purpose**：A 与 B 实际同台竞争时的选择偏好（最表达 Agent Preference）
- **公式**：`A selected ÷ (A+B selected)`，仅限 A、B 同时出现在同一 Candidate Set 的 decision
- **Eligibility**：同 candidate_set_id、同 category、同 Choice Mode、同窗口
- **Counterexample**：全局 SoC 高不意味直接竞争中胜出（Exa vs Tavily 同台 10,000 次选 6,400 → 64%）

## 2. Execution Family（M3，Grain = Invocation）

### M3.1 — Logical Invocations

- **Purpose**：实际执行的调用数（重试/重复归一后）
- **Grain**：Invocation；**公式**：`COUNT(DISTINCT invocation_id)`
- **Eligibility**：Strict Qualified；**Dedup**：tool_call_id 唯一；重试链折叠

### M3.2 — Completion Rate

- **公式**：`Completed Invocations ÷ Invoked Invocations`
- **Observability**：UNOBSERVABLE 的完成状态不计入分母（不视为未完成）

### M3.3 — Success Rate

- **公式**：`Successful Completed Invocations ÷ Completed Invocations`
- **注意**：outcome=inconsistent（双侧冲突）不计入 success，单列披露
- **Unknown**：outcome=unknown 不计入分母，披露 Unknown Outcome Share

## 3. Utility Family（M4，Grain = Result / Invocation）

### M4.1 — Result Consumed Rate

- **Purpose**：返回的结果有没有被 Agent 实际消费
- **公式**：`Consumed Results ÷ Consumption-observable eligible invocations`
- **Eligibility**：仅 consumption 可观察的 runtime/调用进入分母
- **Observability**：Codex 等不可观察面 → UNOBSERVABLE，**绝不记为未消费**
- **Counterexample**：99% success + 32% consumed vs 94% success + 81% consumed——后者更有用

## 4. Distribution Family（M1，Grain = Client / Client-Day）

### M1.1 — Active Clients

- **Purpose**：采用广度
- **公式**：`COUNT(DISTINCT client_key)`（窗口内 ≥1 次 Strict Qualified eligible invocation）
- **Grain**：Client；**Eligibility**：Strict Qualified
- **Unknown**：client 不可解析/无标识的调用不计入，披露 Identity Coverage

## 5. 指标之间的纪律

1. 不同 Grain 的指标不可互换（不变量 16）
2. 每指标必须披露：Numerator / Denominator / Observable population / Qualified population / Runtime coverage / Choice mode（Measurement Label）
3. Strict Qualified Usage（production+normal）是公共口径默认；Extended（+unknown）仅研究用
4. 最小样本量门槛内不发布比率（privacy_threshold）
5. Category 绑定 `category_id + category_version`，SoC 类指标必须声明

## 6. 待 AUP 的指标（Draft 0.3 不正式化）

- First-choice Rate、Substitution/Switch Rate、Dependency、Substitutability
- Task Success Association、Incremental Lift（实验设计见 AgentMeasure 0.5）
