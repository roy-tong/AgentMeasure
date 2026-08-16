# AgentMeasure Quality — Measurement Quality（Draft 0.3）

> **证据 ≠ 覆盖 ≠ 限定 ≠ 方法。** 一组 100% 真实但只覆盖 2% Agent 的事件不是
> 市场数据。本文件定义质量四维 + Measurement Label 披露要求。

## 1. 质量四维

| 维 | 问题 | 披露 |
| --- | --- | --- |
| Evidence | 事件真实吗 | 签名比例、corroborated 比例 |
| Coverage | 看到多少世界 | Runtime/Client/Invocation 覆盖 |
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
Claude user coverage = 20%
但在这 20% 内：Invocation observable 100% · Presented observable 5% · Consumed observable 70%
```

## 3. Observability 披露（每指标）

每指标必须声明各状态的可观察率：TRUE / FALSE / UNKNOWN / UNOBSERVABLE。
UNOBSERVABLE 必须单列——绝不并入 FALSE（不变量 17）。

## 4. Measurement Label v1（披露要求）

```text
Agent Usage Measurement Label
Standard version:   0.3
Metric:             M2.2 Selection Rate
Window:             30 days
Grain:              decision-opportunity
Usage context:      production
Validity:           normal
Agent hosts:        Claude Code, Codex
Coverage:           partial
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
