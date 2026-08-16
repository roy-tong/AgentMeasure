# AgentMeasure Hosted Analytics（Draft 0.4.1 — in development）

## 1. 管道

```text
ingest 端点（鉴权 + envelope 校验 + 配额）
    ↓
collector（match → derive operations → aggregate，复用 reference/collector）
    ↓
store（聚合表 + 原始观察保留策略）
    ↓
dashboard（MVP 字段）
```

## 2. MVP Dashboard 字段

| 字段 | 口径 | 披露要求 |
| --- | --- | --- |
| Operations | M3.1（COUNT(DISTINCT operation_id)） | operation_resolution 分布 |
| Attempts | attempt 数 | — |
| Success | M3.3（Attempt Success Rate） | unknown/inconsistent 单列 |
| Retry | attempts per operation / retry rate | 与 Operation 计数区分 |
| Latency | duration_bucket 分布 | — |
| Caller runtime | declared / correlated / unknown 分层 | **强度分层，绝不裸标 "Claude Code"** |
| Measurement Coverage | coverage_basis=participating_network | 只能说 Observed/Participating（QUALITY.md） |

**不要**：Selection Rate / Share of Choice / Consumption（Provider-only 拓扑没有
该信号；标准支持但产品不做，避免"看起来比实际测得更多"）。

## 3. 口径纪律（与标准一致）

- Strict Qualified（production + normal）为默认视图；unknown 单列
- coverage_basis 强制声明（participating_network → 只说 Observed）
- 最小样本量门槛内不显示比率（privacy_threshold）
- 所有数字带 Measurement Label 链接（offer/metric 口径、窗口、采集侧）

## 4. 隐私

- 只收伪匿名 observation（无 prompt/input/output）
- API key 鉴权；按 Provider 隔离（租户）
- 保留期可配置（默认 90 天原始、永久聚合？——**默认聚合保留，原始可删**）

## 5. 非目标（MVP）

- ❌ 不做选择/偏好指标（无该信号）
- ❌ 不做计费或账单（COMMERCIAL 是语义）
- ❌ 不做跨 Provider 排名（Claim Discipline：participating_network 不能当市场）
