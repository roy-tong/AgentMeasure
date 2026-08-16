# AgentMeasure Correlation — Observation → Attempt → Operation 确定性规则（Draft 0.4）

## 1. 匹配优先级（Observation → Attempt）

```text
1. Exact match        tool_call_id / protocol invocation id（同 project + tool）
2. Structural match   trace parent-child / span 关系（MCP _meta trace context）
3. Commitment match   correlation_commitment 相等（跨主体，无原始数据）
4. Deterministic one-to-one（同一键内按确定性规则配对）
5. Ambiguous          → 不关联（fail-closed，绝不强行匹配成佐证）
```

**规则**：Exact > Structural > Commitment。只有 1-3 匹配且无歧义时才产生
attempt；其余观察各自独立（不提升证据）。

## 2. 关键纪律

- **同侧永不佐证**：client+client 或 server+server 不构成 corroboration
- **时间窗不用于强行匹配**：连续同名调用（search A / search B）不得因时间窗
  产生笛卡尔积配对；无精确/结构/承诺匹配时宁可不关联
- **时间解析 fail-closed**：无法解析的时间戳不参与关联（绝不假设 now）
- **确定性**：同一输入 + 同一 policy → 同一 attempt 划分（可复现）

## 3. Attempt → Operation 归并（Draft 0.4，AgentMeasure Core §2.4）

Operation = 逻辑使用（"为任务 T 使用能力 C"）。归并规则（fail-closed）：

```text
1. explicit（默认唯一启用）   observation 自带 operation_id / idempotency key /
                             精确关联 → 直接归组
2. structural（experimental） task_id + capability + 同一选择（selection_id）+
                             无其他 selection 介入 → 同一 operation。
                             **默认关闭（Draft 0.4.3）**：Provider 看不到中间
                             decision，失败后同 tool 调用未必是重试——宁可
                             resolution coverage 低，也不要错
3. 无证据                   → operation_id = null, resolution = unknown
                            （不归并、不伪装，不变量 23）
```

- **重试 = 同一 Operation 的多个 Attempt**（`retry_of` / `operation_id` 表达），
  不再是 validity 分类（Core §7）
- 归并 MUST 确定性：同一输入 + 同一 policy → 同一 operation 划分
- **M3.1 只计已解析 operation，无回退**（不变量 25）；0.3 数据迁移期仅提供
  Legacy Attempt-equivalent Count（LEGACY-MIGRATION.md §2）
- Measurement Label 披露 `operation_resolution: explicit|unknown`（+ experimental
  structural 启用声明）

## 4. 谱系（Lineage，Draft 0.4）

完整链路：`task_id → decision_id → selection_id → operation_id → attempt_id →
result/effect → outcome`

- 每条观察携带**它所知道的**谱系 id；未知字段留 null，MUST NOT 编造
- 谱系完整度是披露维度：`lineage coverage = 带完整谱系的观察 ÷ eligible 观察`
- 断链处理：`task_id` 缺失的 attempt 仍可计数（execution 级），但不得用于
  outcome/task 级指标（grain 纪律，不变量 16）

## 5. 输出

```jsonc
{
  "invocation_id": "uuid",          // attempt_id
  "operation_id": "op-3",           // 逻辑使用；未知 = null
  "project_id": "...",
  "tool": "...",
  "started_at": "...",
  "outcome": "success|failure|inconsistent|unknown",
  "lifecycle": "selected|invoked|completed|consumed",
  "evidence": {"vector": {...}, "display": "independently-corroborated"},
  "matched_by": "exact-call-id | structural-trace | commitment | none",
  "lineage": {"task_id": "tk-1", "decision_id": "d1", "selection_id": "s1"},
  "observations": ["observation_id", "..."]
}
```

## 6. 不变量映射（AgentMeasure Core §9）

- 一个 invocation 最多计数一次（不变量 2）
- 重复观察不增计数（不变量 3）
- 模糊观察不得提升为 corroborated（不变量 6）
- outcome 冲突保留为 `inconsistent`（client success + server failure → 差异数据，供 Discrepancy Report）
- 无 Operation 证据不得把 Attempt 归并为逻辑调用（不变量 23）
