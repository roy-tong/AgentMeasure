# AUAS-CORE — Agent Usage Measurement Standard（Draft 0.2）

> **agent-used 是 AUAS 的参考实现。** AUAS 是 Agent 软件生态的共同数据语言：
> 定义 Agent 如何发现、选择、使用、依赖软件，以及什么样的数据能支持什么样的结论。
>
> **AUAS 不定义谁是真相来源，而定义什么证据、按照什么规则，可以支持什么结论。**
>
> 本文件是语义核心（measurement semantics）。技术采集（signature、transport、
> collection）只是 supporting layer——见 AUAS-DATA/TRUST/BIND。

## 0. 版本与状态

- 版本：**Draft 0.2**（Measurement Framework 重构版）
- 毕业到 AUAS 1.0：2 个独立实现 + 3 个 runtime profiles + 2 个 tool-side 实现 +
  公开 conformance + canonical test vectors + 5-10 个真实项目 + discrepancy report +
  security/privacy review
- 变更机制：AUP（Agent Usage Proposal）

## 1. 核心命题

**Agent 正在成为软件的新消费者，但行业没有统一的方法衡量 Agent 如何发现、选择、
使用和依赖软件。**

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
```

AUAS 回答五个递进问题（Reach → Choice → Use → Utility → Value）：

1. **Reach** — 我的 Tool 有没有进入 Agent 的选择范围？
2. **Choice** — Agent 有机会时会不会选我？
3. **Use** — 选了以后有没有真正使用？
4. **Utility** — 使用以后有没有产生有效结果？
5. **Value** — 如果没有我，Agent 的结果会不会更差？

## 2. Measurement Objects（测量对象）

**Observation 是证据单位，不是业务测量单位。** 业务测量单位是：

| 对象 | 定义 | 层 |
| --- | --- | --- |
| **Opportunity** | Agent 有机会选择 Tool（进入 decision context / candidate set） | Behavior |
| **Invocation** | Tool 实际执行了一次调用 | Behavior |
| **Task** | Invocation 所服务的任务单位 | Behavior |
| **Client** | 独立 Agent runtime / installation | Market |
| **Project** | 多个 package / MCP / skill 归属的软件项目 | Market |
| **Category** | 可比较的能力类别（如 search、coding） | Market |
| **Observation** | 对上述行为的一次证据性观察（Receipt） | **Evidence** |

```text
Evidence Layer:   Observation
                      ↓ reconstruct
Behavior Layer:   Opportunity · Invocation · Task
                      ↓ aggregate
Market Layer:     Client · Project · Category
```

## 3. Agent Tool Interaction Lifecycle（交互生命周期）

所有状态必须明确：definition、numerator、denominator、observable/inferred、minimum evidence。

| 阶段 | 定义 | 事实/推断 | 可观察者 |
| --- | --- | --- | --- |
| **Presented** | Tool 进入 Agent 的 decision context（candidate set） | 事实 | Agent runtime（routing 层） |
| **Selected** | Agent/runtime 决定调用该 Tool | 事实 | Agent runtime |
| **Invoked** | runtime 开始执行 | 事实 | 双侧 |
| **Completed** | 返回 success/failure/denied | 事实 | 双侧 |
| **Consumed** | 结果被后续模型请求实际使用 | 事实（部分平台） | Agent runtime（部分） |
| **Contributed** | 结果影响最终任务结果 | **推断** | 研究 |

**关键变化：Discovered → Presented。** `tools/list`、registry discovery、skill
search 都只是 discovered；真正的分母是"Tool 是否进入了 Agent 的 decision context"
（如 runtime routing 后实际提供给模型的 tool schema）。三个商业意义不同的状态：

```text
Installed ✓ Available ✓ Presented ✓ Selected ✓   ← 被选
Installed ✓ Available ✓ Presented ✓ Selected ✗   ← 有机会但没被选（Selection Rate 分母）
Installed ✓ Available ✓ Presented ✗              ← 根本没机会（Distribution 缺口）
```

## 4. Measurement Framework（五大指标家族）

**标准定义 Metric Families，不定义全局北极星。** 工具类型（search/coding/payment/
browser/database/enterprise）价值结构不同，一个 KPI 无法通用。

### M1 Distribution（分发）— Reach
我的 Tool 有没有进入 Agent 的世界？
`Available Clients · Presented Opportunities · Presentation Rate · Agent Host
Coverage · Model/Runtime Coverage`

### M2 Choice（选择）— 最 Agent-native
Agent 有机会选我时，会不会选我？
`Selections · Selection Rate (Selected/Presented) · Share of Choice ·
First-choice Rate · Substitution Rate · Switch Rate`

### M3 Execution（执行）— Use
选了以后好不好用？
`Logical Invocations · Completion Rate · Success Rate · Error/Retry Rate ·
Latency · Cost`

### M4 Utility（有效使用）— Utility
返回的东西 Agent 到底有没有用？
`Result Delivered Rate · Result Consumed Rate · Continuation Rate ·
Correction Rate · Fallback Rate`

### M5 Outcome（价值）— Value
它最终是否改善任务？
`Task Success Association · Contribution · Incremental Lift · Time Saved ·
Cost Saved · Human Intervention Reduced`

## 5. Relationship Model（Agent–Tool 关系）

跨时间的关系，Agent-native 行为定义（非消费者忠诚度照搬）：

| 关系 | 定义（Agent-native） |
| --- | --- |
| Trial | 首次使用 |
| Active | 周期内有 eligible usage |
| Repeated | 多个窗口重复使用 |
| Preferred | 同等 candidate set 中持续优先选择（SoC 高） |
| Dependent | 移除 Tool 后任务表现显著下降（Incrementality 高） |

## 6. Attribution vs Incrementality（归因与增量，分离）

> **Tool 参与了成功 ≠ Tool 导致了成功。**

- **Attribution Measurement**（observational）：哪些 Tool 参与了任务链——
  `associated with successful task` / `contributed to execution chain`
- **Incrementality Measurement**（counterfactual）：Tool 的存在带来多少额外价值——
  随机对照（Treatment=可用 / Control=不可见），比较 task success、time、token
  cost、tool calls、human intervention、quality：

```text
Incremental Task Success = P(Success|Tool) − P(Success|No Tool)
Time Lift   = Time(control) − Time(tool)
Cost Lift   = Cost(control) − Cost(tool)
```

这是最 AI-native 的一层：广告行业从 last-click attribution 走向 holdout/
incrementality，Agent 工具同样需要。

## 7. Measurement Quality（测量质量，四块独立）

**Evidence ≠ Coverage ≠ Qualification ≠ Methodology。** 一个 E3 事件集合
（100% 真实）如果只覆盖 2% 的 Agent，也不能代表市场。

```text
Measurement Quality
├── Evidence quality    事件真实吗（AUAS-TRUST）
├── Coverage quality    我看到多少世界（AUAS-COVERAGE）
├── Traffic qualification   算不算真实生产使用（Usage Context）
├── Sampling            采样与不确定性（AUAS-COVERAGE）
├── Identity resolution 身份归一质量
└── Method/version      统计方法与版本
```

### Usage Context（无效使用分离）—— 比 E0-E3 更直接决定排名可信度

```text
production · development · test · benchmark · evaluation · synthetic · ci · unknown
```

- **Raw Invocation** ≠ **Qualified Usage**
- 公开 adoption 默认：`production` + `unknown`（单独披露）
- `benchmark/eval/test/CI/synthetic` **绝不**与真实使用混在一起
- 未来大量调用来自：自测、CI、benchmark、eval、synthetic agent、health check、
  retry storm、agent loop、replay、load test、demo——必须可区分

## 8. Standard Reporting（标准报告）

### Measurement Label（"营养成分表"）

每个公开 Metric 必须携带：

```text
Agent Usage Measurement Label
Standard version:   0.2
Window:             30 days
Usage context:      production
Agent hosts:        Claude Code, Codex
Coverage:           partial
Collection:         client + server
Corroborated:       68%
Sampling:           none
Unknown context:    12%
Synthetic excluded: yes
Identity coverage:  91%
```

不给 Tool 打万能质量分——披露数字怎么来的，让使用者自行判断适用性。

### Measurement Profiles（测量画像，按场景选择）

| Profile | North Star | Guardrail | Diagnostic |
| --- | --- | --- | --- |
| Adoption | Active Clients | Qualified Usage Rate, Coverage | Presented, Selection Rate, Repeat |
| Reliability | Successful Completed Invocations | p95 latency, cost, retry | error type, host, version |
| Utility | Consumed Results | Correction Rate, Fallback Rate | completion→consumption 转化 |
| Value | Incremental Task Success | Cost, Latency, Safety | task type, model, alternatives |

## 9. 标准不变量（Invariants，更新）

1. Same input + same policy = same result
2. One invocation counted at most once
3. Duplicate observations never increase counts
4. Evidence never self-declared
5. Unsigned fields never affect authenticated claims
6. Ambiguous observations never promoted to corroborated
7. `unknown` never inferred as `success`
8. Metrics always declare scope + policy + window + **measurement label**
9. Public receipts never contain user content
10. Corroboration never assumes different strings = independent control
11. Platform attestation UNSUPPORTED until verified
12. Outcome conflicts preserved (inconsistent)
13. **Qualified usage never mixes with benchmark/test/synthetic/CI**
14. **Attribution claims never stated as causation**
15. **Selection Rate denominator = Presented, not Available**

## 10. 参与者与信任（同 Draft 0.1）

Agent Runtime / Tool Runtime / Observer / Verifier / Correlator / Attestor /
Aggregator / Registry——信任最小化不变：任何单一主体不能伪造"被独立佐证的使用"。

## 11. AUAS 文档结构

| 文档 | 负责 |
| --- | --- |
| AUAS-CORE（本文） | Objects、Lifecycle、Families、Relationship、Quality、Reporting |
| AUAS-DATA | Receipt / Manifest / Aggregate schemas |
| AUAS-TRUST | Principal、Signature、Trust Domain、Evidence Profile |
| AUAS-CORR | Observation → Invocation 确定性规则 |
| AUAS-METRICS | 五大家族指标定义（numerator/denominator/evidence 门槛） |
| AUAS-COVERAGE | Scope、sampling、coverage、uncertainty |
| AUAS-PRIVACY | Identifier、retention、aggregation、redaction |
| AUAS-SECURITY | Sybil、collusion、replay、forgery、aggregator |
| AUAS-BIND/PROFILE | MCP/OTel 承载、Codex/Claude/DSH 实现（supporting layer） |
| Verification | Conformance + Test Vectors |
