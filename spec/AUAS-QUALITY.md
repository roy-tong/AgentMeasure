# AUAS-COVERAGE — Scope、Sampling、Coverage、Uncertainty（Draft 0.1）

> **Evidence 和 Coverage 是两个不同问题。** 数据真实 ≠ 数据有代表性。
> 任何公开 Metric 必须携带 Measurement Scope。

## 1. Measurement Scope（每个公开指标必须声明）

```jsonc
{
  "hosts": ["claude-code", "codex"],        // 覆盖了哪些 Agent runtime
  "observer_population": "participating",   // 参与观察网络的主体
  "time_window": {"start": "...", "end": "...", "days": 30},
  "sampling": {"method": "unsampled-only"},
  "coverage_claim": "partial"               // partial | platform-complete
}
```

**展示纪律**：不显示"这个 MCP 本月有 12,347 个 Agent 用户"，而显示
"在参与 AUAS 观察网络的 Claude Code + Codex observers 中，过去 30 天观察到
12,347 个 qualified active clients（coverage: partial）"。

## 2. Sampling（Receipt 可携带）

```jsonc
"sampling": {"method": "fixed", "probability": 0.1, "unit": "call"}
```

| sampling_policy | 语义 |
| --- | --- |
| `unsampled-only` | 只接受未采样数据（当前默认；保守） |
| `weighted-estimate` | 按概率加权估计；**必须报告 uncertainty**（置信区间） |

收到 `probability=0.1` 的 100 条记录 ≠ 100 次调用——是"约 1000 次的 10% 样本"。
不声明 sampling 的聚合是无意义聚合。

## 3. Coverage 层级

| coverage_claim | 含义 | 能否做总体推断 |
| --- | --- | --- |
| partial | 参与网络的部分 observers | 不能 |
| platform-complete | 某平台全量 telemetry | 可以（该平台范围内） |

## 4. Uncertainty

- weighted-estimate 必须报告：样本量、概率、估计值、95% 置信区间
- partial coverage 必须声明：观察面列表与缺口（如"未接入 DSH"）
- Discrepancy Report 是 coverage 差异的实证载体
