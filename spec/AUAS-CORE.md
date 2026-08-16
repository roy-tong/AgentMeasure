# AUAS-CORE — Agent Usage Measurement Standard（Draft 0.3）

> **Draft 0.3：Metric Semantics & Denominator Discipline。** 目标：每个指标都能被
> 独立实现且算出同一个数字。本版本解决"怎么算"——Decision Opportunity、
> Measurement Grain、Observability、Metric Eligibility、Denominator 纪律。
>
> agent-used 是参考实现。**AUAS 不定义谁是真相来源，而定义什么证据、按照什么
> 规则，可以支持什么结论。**

## 0. 版本与治理

- 版本路线：Draft 0.2（框架）→ **0.3（语义）** → 0.4（测量质量）→ 0.5（价值测量）→ 1.0
- 指标变更走 **AUP**（`aup/`）；**AUAS-METRICS 是变更最频繁的文档**，whitepaper 保持稳定
- 毕业标准（不变）：2 独立实现 + 3 profiles + 2 tool-side + conformance + vectors + 5-10 项目 + discrepancy report + 双 review

## 1. 核心命题（不变）

Reach → Choice → Use → Utility → Value。五问不变。

## 2. Measurement Objects（Draft 0.3 重构）

### 2.1 行为对象

| 对象 | 定义 | 关键标识 |
| --- | --- | --- |
| **Decision Opportunity** | Agent/runtime 发生**一次**工具选择决策 | `decision_id` |
| **Candidate Set** | 该次决策中真正可供选择的 Tool 集合 | `candidate_set_id` |
| **Tool Presentation** | 某 Tool 出现在该 Candidate Set 中 | `presentation_id` |
| **Selection** | Agent 在该次决策中选择某 Tool | `selection_id` |
| **Invocation** | Tool 实际执行 | `tool_call_id` |
| **Task** | Invocation 服务的任务单位 | `task_id` |

**Opportunity 拆分为四对象**（Draft 0.2 的 Opportunity 把"决策机会"与"某 Tool 被
呈现"混为一谈）：

```text
Decision Opportunity
        │
        ▼
Candidate Set
 ┌──────┼──────┐
Tool A Tool B Tool C
  │
  ▼
Tool Presentation
        │
        ▼
Selection
```

计数纪律：Agent 一天看到 Exa 10 次、选择 1 次 = **10 Presentations / 1 Selection
= 10%**，不是 1/1=100%。

### 2.2 Market 对象

Client / Project / Category（不变）。Category 是**版本化的 measurement construct**
（`category_id + category_version`），不是永久真理（见 AUAS-TAXONOMY，Draft 0.4）。

## 3. Measurement Grain（统计粒度）

| Family | Grain |
| --- | --- |
| Distribution | Client / Client-Day |
| **Choice** | **Decision Opportunity** |
| Execution | Invocation |
| Utility | Result / Invocation |
| Outcome | Task / Experiment Unit |
| Relationship | Client × Project × Window |

**不变量：不同 Grain 的指标不可互换。** 10 invocations ≠ 10 users ≠ 10 decision
opportunities ≠ 10 tasks。任何指标必须声明 Grain。

## 4. Observability States（可观测四态）

观测结果不是二值。正式定义：

| 状态 | 含义 |
| --- | --- |
| **TRUE** | 确认发生 |
| **FALSE** | 有能力判断，并确认未发生 |
| **UNKNOWN** | 应该可以判断，但数据缺失/冲突 |
| **UNOBSERVABLE** | 当前 observation surface 根本无法观察 |

**不变量：An unobservable outcome MUST NOT be interpreted as a negative
outcome.**

示例：Codex 的 Consumed 不可观察 → 记为 UNOBSERVABLE，不记 FALSE：

```text
Consumption Rate = Consumed ÷ Consumption-observable eligible invocations
```

## 5. Metric Eligibility（指标资格）

**Qualified Usage ≠ Metric Eligible Sample。**

- **Qualified Usage**：这条数据是否值得统计的真实生产使用（Context × Validity × Policy）
- **Metric Eligibility**：这条数据是否有资格进入**这个具体指标**的分母
  （如：Presented 不可观察的 runtime 不进入 Selection Rate 分母；
  Consumption 不可观察的不进入 Consumption Rate 分母）

## 6. Choice Mode（选择模式）

| Mode | 定义 |
| --- | --- |
| exclusive | 从候选集中选一个 |
| multi_select | 选择多个 |
| parallel | 同时调用多个 |
| sequential | 先 A，失败后 B |
| ordered_fallback | 按序回退 |
| router_preselected | runtime 先过滤，模型再从子集选 |
| unknown | 无法判定 |

**不变量：不同 Choice Mode 默认不得直接比较 Selection Rate / Share of Choice**
（或必须声明标准化方法）。

## 7. Qualification：Context × Validity

### Usage Context（数据来源环境）

```text
production · development · test · benchmark · evaluation · synthetic · ci · demo · unknown
```

### Invocation Validity（调用有效性）

```text
normal · retry · duplicate · replay · agent_loop · health_check · load_test · suspected_invalid · unknown
```

retry/duplicate/replay/loop/health check 不是 context——是 validity。

### 口径定义

| 口径 | 组成 | 用途 |
| --- | --- | --- |
| **Strict Qualified Usage** | `production` + `validity=normal` | 公共 leaderboard / market metric 默认 |
| **Extended Observed Usage** | `production + unknown` | 研究与内部诊断 |

同时公开：`Unknown Context Share`、`Unknown Validity Share`。
**Unknown 默认不得进入 Strict 口径**（避免"不知道是什么流量→报 unknown→进排行榜"
的激励漏洞）。

## 8. Measurement Label（Draft 0.3 补 denominator 披露）

见 AUAS-QUALITY。每个指标除 label 外必须披露：Numerator / Denominator /
Observable population / Qualified population / Runtime coverage / Choice mode。

## 9. 标准不变量（Draft 0.3 完整版）

1. Same input + same policy = same result
2. One invocation counted at most once
3. Duplicate observations never increase counts
4. Evidence never self-declared
5. Unsigned fields never affect authenticated claims
6. Ambiguous observations never promoted to corroborated
7. `unknown` never inferred as `success`
8. Metrics always declare scope + policy + window + **grain** + label
9. Public receipts never contain user content
10. Corroboration never assumes different strings = independent control
11. Platform attestation UNSUPPORTED until verified
12. Outcome conflicts preserved (inconsistent)
13. Qualified usage never mixes with benchmark/test/synthetic/CI
14. Attribution claims never stated as causation
15. Selection Rate denominator = Presented, not Available
16. **Different grains are not interchangeable**
17. **Unobservable MUST NOT be interpreted as negative**
18. **Presentations count per Decision Opportunity（presentation ≠ decision）**
19. **Different Choice Modes are not directly comparable**
20. **Strict Qualified Usage excludes unknown context/validity**

## 10. 参与者与信任（不变）

## 11. 文档结构（Draft 0.3）

| 文档 | 负责 |
| --- | --- |
| AUAS-CORE（本文） | Objects、Grain、Observability、Eligibility、Qualification、不变式 |
| AUAS-DATA | Observation Envelope（六类型）schema |
| AUAS-METRICS | Metric Registry + 指标合同（变更最频繁） |
| AUAS-TRUST | Principal、Signature、Trust Domain、Evidence |
| AUAS-CORR | Observation → Invocation 确定性规则 |
| AUAS-QUALITY | Context/Validity/Coverage/Observability/Label |
| AUAS-PRIVACY / SECURITY / BIND / PROFILES | 不变 |
| AUAS-TAXONOMY | Category/Capability 分类（Draft 0.4 立项） |
| aup/ | 指标与规范变更提案 |
