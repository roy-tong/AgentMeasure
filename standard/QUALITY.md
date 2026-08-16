# AgentMeasure Quality — Measurement Quality（Draft 0.4.1）

> **证据 ≠ 覆盖 ≠ 限定 ≠ 方法。** 一组来源强但只覆盖 2% Agent 的事件不是
> 市场数据。本文件定义质量四维 + Measurement Label 披露要求。

## 1. 质量四维

| 维 | 问题 | 披露 |
| --- | --- | --- |
| Provenance / Evidence Strength | 这条 observation 来自哪里，其来源能被支持到什么程度？（签名证明来源与完整性，**不证明事件事实绝对真实**） | 签名比例、corroborated 比例 |
| Coverage | 看到多少世界 | Runtime/Client/Invocation 覆盖（含 coverage_basis） |
| Qualification | 算不算真实生产使用 | Context/Validity 分布 |
| Observability | 信号能测多少 | 每信号的可观察率 |

## 2. Coverage（多维，不再只有 partial/complete）

```text
Runtime Coverage        各 runtime 的观察覆盖
Client Coverage         覆盖的伪匿名 client 占比
Invocation Coverage     调用级覆盖
Opportunity Observability    Presented 可观察率
Consumption Observability    Consumed 可观察率
Identity Coverage       身份可解析率
Context Classification Coverage   context 可分类率
Category Classification Coverage  category 可分类率
```

**Population Coverage（覆盖多少总体）≠ Signal Observability（覆盖内某信号能测多少）**：

```text
Observed Claude clients = 20%（participating_network 内的观察占比）
但在这 20% 内：Invocation observable 100% · Presented observable 5% · Consumed observable 70%
```

### coverage_basis（覆盖基座，MUST 声明）

只有**已知分母**才能声称覆盖率百分比；否则只能说观察量，不能说覆盖：

```text
coverage_basis
├── census              全量已知（可声称 x% coverage）
├── probability_sample  概率抽样（可声称带误差的 coverage）
├── participating_network  参与式网络（只说 Observed clients / Participating
│                          installations / Observed runtimes，不得包装为市场覆盖率）
└── unknown
```

> 这决定了"Agent Market Share"类声称是否合法：参与式测量网络只能说
> *Observed Selection Share*，不能说 *Agent Market Share*。

## 3. Observability 披露（每指标）

每指标必须声明各状态的可观察率：TRUE / FALSE / UNKNOWN / UNOBSERVABLE。
UNOBSERVABLE 必须单列——绝不并入 FALSE（不变量 17）。

## 4. Measurement Label v1（披露要求）

```text
Agent Usage Measurement Label
Standard version:   0.4
Metric:             M2.2 Observed Selection Rate
Window:             30 days
Grain:              decision-opportunity
Usage context:      production
Validity:           normal
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
Category:           search.web.general/v1
Choice mode:        exclusive
```

## 5. Claim Discipline（陈述纪律）

| 覆盖 | 可说的 | 不可说 |
| --- | --- | --- |
| partial | Observed Selection Share | Agent Market Share |
| 单平台完整 | Claude Code Selection Share | Global Agent Selection Share |
| 总体推断条件满足 | Estimated Agent Ecosystem Share | — |
