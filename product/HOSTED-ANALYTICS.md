# AgentMeasure Hosted Analytics（Draft 0.4.2 — in development）

## 1. 管道

```text
ingest 端点（鉴权 + envelope 校验 + source_sequence 缺口检测 + 配额）
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
| Observed requests（attempts） | attempt 数（全部请求） | — |
| Resolved Operations | M3.1（COUNT(DISTINCT operation_id)） | operation_resolution 分布 |
| **Operation Resolution Coverage** | resolved attempts ÷ attempts | 覆盖率低时 Operations 不突出显示 |
| Unresolved Attempts | attempts − resolved | fail-closed 披露 |
| Success Rate | M3.3（Attempt Success Rate） | unknown/inconsistent 单列 |
| Retry-chain Rate | 仅 resolved operations 内（M3.5 覆盖之外无法判定 retry，不得展示全量 Retry Rate） | 与 Operation 计数区分 |
| Latency | duration_ms 可用时 p50/p95；否则仅 buckets 分布（bucket 算不出可信 p95） | — |
| Caller attribution | correlated / declared / unknown 分层 | **强度分层，绝不裸标 "Claude Code"** |
| Measurement Coverage | coverage_basis=participating_network | 只能说 Observed/Participating（QUALITY.md） |

**不要**：Observed Selection Rate / Share of Choice / Consumption（Provider-only 拓扑没有
该信号；标准支持但产品不做，避免"看起来比实际测得更多"）。

## 3. 口径纪律（与标准一致）

- **默认 unknown**：usage_context / validity 默认 unknown，只有证据（部署配置 /
  collector 派生）才升级为 production/normal——绝不默认 Strict Qualified
- Strict Qualified（production + normal）为默认视图；unknown 单列
- coverage_basis 强制声明（participating_network → 只说 Observed）
- 最小样本量门槛内不显示比率（privacy_threshold）
- 所有数字带 Measurement Label 链接（offer/metric 口径、窗口、采集侧）

## 4. 数据保留策略（正式，不留问号）

### Developer

```text
raw observations:   30 days
aggregates:         12 months
```

### Enterprise

可配置，并支持删除级联：

```text
delete project
  → delete raw observations
  → delete derived (invocations/operations)
  → delete aggregates
```

**公共统计例外**：如果某聚合已经匿名进入 public statistics 而无法删除，必须在
服务条款中提前定义（"public aggregates are permanent once published"）。

## 5. 隐私

- 只收伪匿名 observation（无 prompt/input/output）
- API key 鉴权；按 Provider 隔离（租户）
- `consumer_account_ref` 只做 Provider/Offering 级作用域（COMMERCIAL §2），
  **不得成为跨 Provider 的生态级身份**

## 6. 非目标（MVP）

- ❌ 不做选择/偏好指标（无该信号）
- ❌ 不做计费或账单（COMMERCIAL 是语义）
- ❌ 不做跨 Provider 排名（Claim Discipline：participating_network 不能当市场）
