# AgentMeasure Metrics — Metric Registry（Document revision 0.4.3）

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

### M2.5 — Observed Head-to-Head Choice Share

- **Purpose**：A 与 B 实际同台竞争时的**观测到的正面竞争选择份额**（claim discipline：
  不默认称为 preference）
- **公式**：`A selected ÷ (A+B selected)`，仅限 A、B 同时出现在同一 Candidate Set 的 decision
- **Eligibility**：同 candidate_set_id、同 category、同 Choice Mode、同窗口
- **Required Dimensions**：decision_authority / selection_constraint——同轴竞争默认；
  混轴时 MUST 披露
- **Preference 声称条件**：仅当 `decision_authority=model` 且
  `selection_constraint=autonomous` 且 candidate placement 受控、task/model/runtime
  可比时，才可以说 "preference evidence / preference signal"（否则只能报告
  observed share）
- **Counterexample**：全局 SoC 高不意味直接竞争中胜出（Exa vs Tavily 同台 10,000 次选 6,400 → 64%）

## 2. Execution Family（M3，对象 = Operation 与 Attempt；Grain 按指标声明）

> Draft 0.4.1：**重试 = 同一 Operation 的多个 Attempt**（Core §2.4）。
> 本家族不声明统一 Grain——M3.1 以 Operation 计数，M3.2/M3.3 以 Attempt 计数。

### M3.1 — Operation Count

- **Purpose**：实际执行的逻辑使用数（重试/重复归一后）
- **Object**：Operation；**Grain**：Operation
- **公式**：`COUNT(DISTINCT operation_id)` —— **只计已解析的 operation，无回退**
  （Draft 0.4.3，不变量 25）
- **Eligibility**：Strict Qualified；**Dedup**：结构性——同 operation 多 attempt 只计 1
- **Label 要求**：`attempts_per_operation`（均值/分布，公开披露）；
  `operation_resolution` 分布；无解析证据时本指标为 0 / N/A——**绝不把 Attempt
  数伪装成 Operation 数**。旧 0.3 数据如需兼容，提供
  `Legacy Attempt-equivalent Count`（独立字段，不得命名为 Operation Count）
- **Draft 0.4.4 — Inferred Operation Share**：任何 Operation Count 必须伴随
  resolution 构成，不得让总数看起来都是同等确定的事实：
  ```text
  Operation Count                 12,483
    Explicit / correlated         68%
    Inferred                      21%
    Unresolved attempts           11%
  ```
  指标：`Resolved Operation Share`（resolved ÷ resolved+unresolved+ambiguous）
  · `Inferred Operation Share`（inferred ÷ resolved）
- 历史名：Logical Invocations

### M3.2 — Attempt Completion Rate

- **公式**：`Completed Attempts ÷ Invoked Attempts`
- **Grain**：Attempt
- **Observability**：UNOBSERVABLE 的完成状态不计入分母（不视为未完成）

### M3.3 — Attempt Success Rate

- **公式**：`Successful Completed Attempts ÷ Completed Attempts`
- **注意**：outcome=inconsistent（双侧冲突）不计入 success，单列披露
- **Unknown**：outcome=unknown 不计入分母，披露 Unknown Outcome Share
- **重试**：同一 operation 的失败 attempt 与成功 attempt 分别计数

### 不变量：Reliability claims MUST declare their grain（Draft 0.4.4）

```text
Attempt Success Rate   ≠   Operation Success Rate
```

1 user intent → 2 provider attempts → 1 final success：
- 按 attempt 计：2 attempts，50% success
- 按 operation 计：1 operation，100% success（intent 最终成功）
- attempts_per_operation = 2（retry overhead）

**Attempt reliability 不得被报告为 operation reliability，反之亦然。**
任何 `Reliability = X%` 的声明必须伴随 grain（Provider Attempt Reliability /
Capability Operation Reliability / Mean Attempts per Successful Operation）。

### M3.4 — Operation Success Rate

- **公式**：`Operations with ≥1 successful attempt ÷ Completed Operations`
- **Grain**：Operation
- **Purpose**：逻辑使用层面的成败（对 Metering 的 `operation_succeeded` 事件
  最有意义：3 attempts 中 1 次成功 = 1 个成功 operation）

### M3.5 — Operation Resolution Coverage

- **公式**：`Attempts with resolved operation_id ÷ All attempts`
- **Grain**：Attempt
- **Purpose**：Provider-only 拓扑下 Operation 是否可证的透明度指标——覆盖率低时
  M3.1/M3.4 不得突出显示（fail-closed，不把 unresolved attempts 伪装成 operations）
- **Resolution**：explicit（observation 自带 operation_id）· structural（重试链证据）·
  unknown（无证据，不归并）
- **Label 要求**：resolution 分布（explicit/structural/unknown）随 M3.1 一起披露

## 3. Utility Family（M4，Grain = Result / Invocation）

### M4.1 — Result Consumed Rate

- **Purpose**：返回的结果有没有被 Agent 实际消费
- **公式**：`Consumed Results ÷ Consumption-observable eligible invocations`
- **Eligibility**：仅 consumption 可观察的 runtime/调用进入分母
- **Observability**：Codex 等不可观察面 → UNOBSERVABLE，**绝不记为未消费**
- **Counterexample**：99% success + 32% consumed vs 94% success + 81% consumed——后者更有用
- **Draft 0.4**：本指标度量 **Result**（返回值被消费）；Effect（世界改变）属于
  0.5 的验证型 Utility 指标（Core §2.7 不变量 22）

## 4. Adoption & Relationship Family（M1，Grain = Client / Client-Day）

> Active Clients 是**采用 / 关系**指标（使用已发生），不是 Reach。
> Reach / Distribution 指标（Eligible Opportunities、Presentation Rate、
> Distribution Coverage）挂靠 M2（Presented）与 Taxonomy，不另设家族。

### M1.1 — Active Clients

- **Purpose**：采用广度
- **公式**：`COUNT(DISTINCT client_instance_id)`（窗口内 ≥1 次 Strict Qualified eligible attempt）
- **Grain**：Client Instance（身份 Grain 明确：session ≠ runtime_instance ≠
  client_instance ≠ deployment ≠ consumer_account）
- **Eligibility**：Strict Qualified
- **Unknown**：client 不可解析/无标识的调用不计入，披露 Identity Coverage
- **Pseudonym epoch**：伪匿名密钥按月轮换，跨月窗口 MUST 披露 epoch（否则同一
  client 跨月会被双计）；session_key 不得直接用作 client 计数（session ≠ client）

### M1.2 — Repeat Clients（定义，待向量）

- **公式**：跨 ≥2 个窗口有 eligible usage 的 clients
- **Grain**：Client × Window

### M1.3 — Active Client-Days（= ACD，定义，待向量）

- **公式**：`COUNT(DISTINCT client × UTC-day)`（窗口内 ≥1 次 eligible invocation）
- **Grain**：Client-Day；跨 Codex/Claude/DSH 可比

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
