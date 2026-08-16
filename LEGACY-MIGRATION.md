# AgentMeasure LEGACY-MIGRATION（非规范性）

> 本文件定义旧数据模型值到 Draft 0.4.3 干净模型的迁移。**不污染规范性模型**：
> 新世界只有一种 Canonical Observation（DATA.md）、一种标准对象（Attempt）。

## 1. `validity=retry` → retry 关系

旧值 `validity=retry` 不再属于 Attempt Validity（CORE §7）。

迁移：

```text
validity=retry 的旧 observation
  → 保留为历史数据（不删除）
  → 若可与同 operation_id / retry_of 关联：转为 Attempt 关系
  → 否则标记 legacy_retry=true（不计入 Strict Qualified 的 validity=normal 口径）
```

新世界表达重试：`attempt_started.payload.retry_of`（指向被重试的 attempt）+
同一 `operation_id`。

## 2. `invocation` → `attempt`

| 旧概念 | 新概念 |
| --- | --- |
| invocation（observation_type=invocation / completion） | attempt_started / attempt_completed |
| invocation_id | attempt_id（= tool_call_id 或派生） |
| Logical Invocations（0.3 回退语义） | **已废弃**：M3.1 只计已解析 operation（不变量 25） |
| Legacy Attempt-equivalent Count | 独立字段，仅 0.3 数据迁移期披露，不得命名 Operation Count |

`invocation` 只保留为外部协议原始概念（如 MCP invocation）。

## 3. 生命周期 `L0-L3` → 单词

| 旧码 | 新表达 |
| --- | --- |
| L0 | selected（生命周期阶段，非证据） |
| L1 | invoked |
| L2 | completed |
| L3 | consumed |

数据码仍可在参考实现内部使用（稳定字段值），文档与产品词汇一律用单词。

## 4. 证据码 `E0-E3` → 单词显示等级

| 旧码 | 新表达（TRUST §4） |
| --- | --- |
| E0 | observed |
| E1 | authenticated |
| E2 | corroborated / independently-corroborated |
| E3 | platform-attested（UNSUPPORTED） |

## 5. `eligible` 全局概念 → metric-specific eligibility

旧 `invocation.eligible`（evidence != observed 才 eligible）已废弃：单边 Provider
observed 数据现在可进入 Class A / first-party analytics（QUALITY §4）。eligibility
由 `is_eligible(observation, metric_policy)` 按指标判定（registry/metrics.yaml）。

## 6. `M0-M3` 码

- Evidence Match 轴：`none | heuristic | exact-call-id | trace-verified`（单词）
- 旧的 Metering Assurance M0-M3：改为 `billing_requirements` predicate（COMMERCIAL §6）
- 不再新增任何字母阶梯

## 7. 0.3 spec_version / CORE_POLICY_V1 / VACD

- `agentmeasure-0.1`：仅 Verified Profile 收据工件的内部版本
- `CORE_POLICY_V1`：由 MeasurementPolicy v2（metric-bound）取代
- `VACD`：更名为 ACD（Active Client-Days）
