# AgentMeasure Quality — Measurement Quality Model（Document revision 0.4.3）

> **证据 ≠ 覆盖 ≠ 限定 ≠ 方法。** 一组来源强但只覆盖 2% Agent 的事件不是
> 市场数据。本文件定义**七维质量模型**、Measurement Use Classes 与
> Measurement Label 披露要求。

## 1. 七维质量模型（Measurement Quality Model）

| # | 维度 | 问题 | 披露 |
| --- | --- | --- | --- |
| 1 | **Provenance Strength** | 这条 observation 来自哪里，其来源能被支持到什么程度？（签名证明来源与完整性，**不证明事件事实绝对真实**） | 签名比例、corroborated 比例 |
| 2 | **Representativeness / Coverage** | 看到多少世界（含 coverage_basis） | Runtime/Client/Invocation 覆盖 |
| 3 | **Observability** | 信号能测多少 | 每信号的可观察率 |
| 4 | **Qualification** | 算不算真实生产使用 | Context/Validity 分布（默认 unknown，只有证据升级） |
| 5 | **Sampling & Uncertainty** | 采样了吗？不确定性多少 | sampling method、uncertainty |
| 6 | **Identity Resolution** | 标识归一得怎么样（entity/caller） | 解析率、resolution 分布 |
| 7 | **Method & Version** | 用什么统计、哪个 spec/registry 版本 | spec_version、registry_version、policy 版本 |

> **Draft 0.4.4 不变量：** 质量/可靠性声明必须声明 measurement grain
> （Attempt / Operation / Task）。Attempt reliability 与 Operation reliability
> 不得互相顶替（External Consensus：Arthi / 김지훈 / Suraj）。


## 2. Coverage（多维）

```text
Runtime Coverage        各 runtime 的观察覆盖
Client Coverage         覆盖的伪匿名 client 占比
Invocation Coverage     调用级覆盖
Opportunity Observability    Presented 可观察率
Consumption Observability    Consumed 可观察率
Identity Coverage       身份可解析率
Context Classification Coverage   context 可分类率
Category Classification Coverage  category 可分类率
Operation Resolution Coverage     attempts 中能解析出 operation 的比例（M3.5）
```

### Composition ≠ Coverage（必须分开）

```text
Composition（构成）
  Claude = 20% of observed clients        ← Runtime Distribution，不是 Coverage

Coverage（覆盖，只有已知总体才能算）
  observed / eligible population
```

参与式测量网络通常没有已知总体 → 只能说 **Observed clients / Participating
installations / Observed runtimes**，不得包装成市场覆盖率。

### coverage_basis（覆盖基座，MUST 声明）

```text
coverage_basis
├── census              全量已知（可声称 x% coverage）
├── probability_sample  概率抽样（可声称带误差的 coverage）
├── participating_network  参与式网络（只说 Observed / Participating）
└── unknown
```

> 这决定了"Agent Market Share"类声称是否合法：参与式测量网络只能说
> *Observed Selection Share*，不能说 *Agent Market Share*。

## 3. Observability 披露（每指标）

每指标必须声明各状态的可观察率：TRUE / FALSE / UNKNOWN / UNOBSERVABLE。
UNOBSERVABLE 必须单列——绝不并入 FALSE（不变量 17）。

## 4. Measurement Use Profiles（测量用途画像：fit-for-purpose）

同一批数据，用于内部趋势与用于对外收费，所需可信度完全不同。**Measurement
Quality 按用途画像**（是用途，不是严格的大小等级）：

```text
use_profile:
  first_party_analytics     Provider 自己观察：产品分析、reliability、内部趋势
  comparative               标准 metric + coverage 披露 + entity resolution + qualification
  cross_side_attribution    Provider + Runtime 双侧独立观察：更强的 Agent 归属、公共信任信号
  billable_audit            operation/effect 证据 + versioned metering policy + replay
                            protection + immutable revisions + 双方协议（必要时第三方证言）
```

每个 profile 声明自己的 requirements（非等级序列）：例如两个企业合同完全可以接受
`provider-authenticated + idempotency key` 作为 billable 数据，而无需 Runtime
Correlation。

**声称规则：数据的 Use Profile 必须与其证据匹配。** first_party_analytics 数据
不能发布为 comparative/cross_side 声称；billable_audit 还额外要求
billing_requirements（extensions/COMMERCIAL.md §6）。

## 5. Measurement Label（披露要求）

```text
Agent Usage Measurement Label
Standard version:   0.4
Metric:             M2.2 Observed Selection Rate
Use profile:        comparative
Window:             30 days
Grain:              decision-opportunity
Usage context:      production (context_source: provider_configuration)
Validity:           normal (validity_source: collector_derived)
Decision authority: model / router / policy   # 三轴披露（Core §6）
Selection constraint: autonomous / forced
Agent hosts:        Claude Code, Codex
Coverage:           partial
Coverage basis:     participating_network
Collection:         client + server
Corroborated:       68%
Sampling:           none
Unknown context:    8%
Unknown validity:   3%
Observability:      presented 可观察率 15%
Identity coverage:  91%
Operation resolution coverage: 51.4%
Category:           search.web.general/v1
Choice mode:        exclusive
```

## 6. Claim Discipline（陈述纪律）

| 覆盖 | 可说的 | 不可说 |
| --- | --- | --- |
| partial / participating_network | Observed Selection Share | Agent Market Share |
| 单平台完整 | Claude Code Selection Share | Global Agent Selection Share |
| 总体推断条件满足 | Estimated Agent Ecosystem Share | — |
| first_party_analytics 数据 | First-party analytics | Comparative / market 声称 |
| UA/clientInfo 匹配 | Caller (declared) | Caller (correlated) / "Agent 使用量" |
