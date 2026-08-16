# AgentMeasure Correlation — Observation → Invocation 确定性规则（Draft 0.1）

## 1. 匹配优先级

```text
1. Exact match        tool_call_id / protocol invocation id（同 project + tool）
2. Structural match   trace parent-child / span 关系（MCP _meta trace context）
3. Commitment match   correlation_commitment 相等（跨主体，无原始数据）
4. Deterministic one-to-one（同一键内按确定性规则配对）
5. Ambiguous          → 不关联（fail-closed，绝不强行匹配成佐证）
```

**规则**：Exact > Structural > Commitment。只有 1-3 匹配且无歧义时才产生
invocation；其余观察各自独立（不提升证据）。

## 2. 关键纪律

- **同侧永不佐证**：client+client 或 server+server 不构成 corroboration
- **时间窗不用于强行匹配**：连续同名调用（search A / search B）不得因时间窗
  产生笛卡尔积配对；无精确/结构/承诺匹配时宁可不关联
- **时间解析 fail-closed**：无法解析的时间戳不参与关联（绝不假设 now）
- **确定性**：同一输入 + 同一 policy → 同一 invocation 划分（可复现）

## 3. 输出

```jsonc
{
  "invocation_id": "uuid",
  "project_id": "...",
  "tool": "...",
  "started_at": "...",
  "outcome": "success|failure|inconsistent|unknown",
  "lifecycle": "L0-L3",
  "evidence": {"vector": {...}, "display": "independently-corroborated"},
  "matched_by": "exact-call-id | structural-trace | commitment | none",
  "observations": ["receipt_id", "..."]
}
```

## 4. 不变量映射（AgentMeasure Core §4）

- 一个 invocation 最多计数一次
- 重复观察不增计数
- 模糊观察不得提升为 corroborated
- outcome 冲突保留为 `inconsistent`（client success + server failure → 差异数据，供 Discrepancy Report）
