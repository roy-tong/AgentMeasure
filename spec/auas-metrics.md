# AUAS-METRICS — ACD、Invocation、Consumption、窗口、denominator（Draft 0.1）

## 1. Metric 与 Policy 解耦

Metric 不能脱离 Policy。`12,481 ACD` 必须携带 `policy_id`：

```text
ACD(project=X, window=30d, qualification=AUAS/Core-1)
  @ authenticated
  @ corroborated
  @ independently-corroborated
```

## 2. 核心指标

| 指标 | 定义 | 备注 |
| --- | --- | --- |
| **ACD**（Active Client-Days） | 某 project 某 UTC 日，某伪匿名 client 产生 ≥1 次 eligible invocation | 首要 adoption 指标；跨宿主可比 |
| Active Clients | 30 天内有 eligible invocation 的伪匿名 client 数 | |
| Attributed Invocations | 逻辑调用数（evidence != E0） | 计数单位是 invocation 不是 observation |
| Corroborated Share | corroborated invocations / eligible invocations | 100% 双边关联 → 1.0 |
| Success Rate | invocation 级（eligible 内） | 冲突 outcome 不计为 success |
| Result Consumed Rate | consumption links / eligible invocations | S4，部分平台可测 |

## 3. Denominator 纪律

- 所有比率必须声明分母（eligible invocations / observed calls / sampled calls）
- 最小样本量门槛（privacy_threshold）：低于门槛不发布比率
- 窗口必须声明（7d / 30d / 90d）

## 4. 用词纪律

Observed / Source-authenticated / Corroborated / Independently Corroborated /
Platform Attested。**禁止** true / real / verified / objective 等过度承诺词
（E1 只是 source-authenticated，不是"验证了真实发生"）。
