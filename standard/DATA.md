# AgentMeasure Data — Canonical Observation Envelope（Document revision 0.4.3）

> **Canonical Observation 是唯一 ingestion 输入。** 所有 Adapter、Provider SDK、
> Runtime Adapter 只允许产出这一种 Envelope（schemas/observation.schema.json）。
> Collector 不接受任何第二套格式。
> 签名与认证是 **Verified Measurement Profile** 的可选能力（Core §10）；
> Core-conformant 实现不实现 Ed25519 也成立。
>
> 版本：Standard Compatibility `agentmeasure-0.4` · Document revision `0.4.3`

## 1. Observation Envelope（统一外壳）

### Canonical 示例：**默认 unknown**（只有证据才升级）

```jsonc
{
  "spec_version": "agentmeasure-0.4",
  "observation_id": "uuid",
  "observation_type": "presentation | selection | attempt_started | attempt_completed | result_consumed | task_outcome",
  "observer": {"principal": "am-sdk@acme", "trust_domain": "acme", "side": "server"},
  "observed_at": "2026-08-16T03:00:00Z",
  "deployment_context": {
    "project_id": "github.com/foo/bar"      // 采集方内部数据组织的标识；非实体权威
  },
  "surface": {                              // RAW 层（Core §2.3）
    "surface_id": "mcp_tool:bar.search",
    "surface_namespace": "io.github.foo",
    "provider_claim": null,                 // provider 自声明（不视为权威）
    "capability_claim": null                // capability 自声明（不视为权威）
  },
  "caller": {                               // Caller Claim：调用者自声称（Draft 0.4.3）
    "type": "claimed_agent",                // unknown | claimed_agent | correlated_agent | platform_attested
    "runtime": "claude",
    "identity_strength": "declared"         // unknown | declared | correlated | attested
  },
  "client_key": "p-...",                    // 伪匿名 client 标识（内存内生成）
  "usage_context": "unknown",               // 默认 unknown
  "validity": "unknown",                    // 默认 unknown
  "context_source": "none",                 // none | provider_configuration | collector_derived | runtime_propagated
  "validity_source": "none",                // none | collector_derived | runtime_propagated
  "collection_health": {                    // Collection Health（Draft 0.4.3）
    "source_instance_id": "srv-7",          // 采集实例标识（进程重启后 sequence 从 1 开始可识别）
    "source_sequence": 1007,                // 单调递增
    "sequence_epoch": "2026-08",            // 序号纪元（重启/轮换分界）
    "dropped_since_last_report": 3,         // SDK 自身丢失数（进入 Measurement Coverage）
    "buffer_overflow": false
  },
  "sampling": null,
  "provenance": "hook | otel | wrapper | platform",
  "payload": { /* 类型特有字段，见 §3 */ },
  "signature": null,                        // OPTIONAL — Verified Measurement Profile
  "key_id": null
}
```

> **默认 unknown 是纪律，不是缺陷。** 只有证据（部署配置 / collector 派生的重复、
> 重放、合成检测）才允许升级，且必须携带 `context_source` / `validity_source`。

### Fully classified 示例（证据齐备时）

```jsonc
{
  "usage_context": "production",            // 部署者配置 deployment_environment=production
  "validity": "normal",                     // collector 派生：无重复/重放/合成标记
  "context_source": "provider_configuration",
  "validity_source": "collector_derived"
}
```

> 谱系纪律：每条观察携带**它所知道的**谱系 id（task_id / decision_id /
> operation_id …）；不知道的字段不携带（或 null），MUST NOT 编造。谱系完整度是
> 指标的披露维度（Measurement Label：lineage coverage）。

## 2. Derived 层（解析结果，不在 adapter 产生）

entity / capability 归属与 Attempt/Operation 重建由统计层完成：

```jsonc
// Derived（aggregator/解析器写入；adapter 永不产生）
{
  "resolved_entity_id": "github.com/foo/bar",
  "resolved_capability_id": "github.com/foo/bar:search",
  "registry_version": "2026.1",
  "resolution_status": "resolved | ambiguous | unknown",
  "attempt_id": "uuid",
  "operation_id": "op-3",                   // 无 resolution evidence 时为 null
  "operation_resolution": "explicit | unknown"
}
```

重建链：`Observation → Reconstruction → Decision / Attempt / Operation / Result → Metrics`
（Choice 与 Execution 从**同一** Envelope 派生，没有第二套输入格式。）

## 3. 六类 Payload（schemas/payloads/）

### presentation
```jsonc
{ "decision_id": "d1", "candidate_set_id": "cs1", "category_id": "search.web.general",
  "category_version": "v1", "choice_mode": "exclusive", "rank_in_candidate_set": 3 }
```

### selection
```jsonc
{ "decision_id": "d1", "selection_id": "s1", "rank": 1,
  "decision_authority": "model",        // Core §2.5
  "selection_constraint": "autonomous", // Core §2.6
  "selection_reason_observable": false }
```

### attempt_started
```jsonc
{ "tool_call_id": "tc-9", "trace_id": "t-9", "started_at": "...",
  "operation_id": "op-3",               // 有证据才携带；未知不携带（不变量 23）
  "task_id": "tk-1",
  "retry_of": null }                    // retry 关系：指向被重试的 attempt（Draft 0.4.3）
```

### attempt_completed
```jsonc
{ "tool_call_id": "tc-9", "outcome": "success|failure|denied|unknown",  // retry 不是 outcome（Draft 0.4.4）
  "duration_ms": 1250,                  // 非敏感；支持 p50/p95（Draft 0.4.3）
  "error_type": null }
```

> **Draft 0.4.4 — `retry` 不是 outcome 值。** 重试是 attempt 之间的关系（`retry_of`），不是单次 attempt 的状态。
> 正确模型：`attempt_1.outcome = failure`；`attempt_2.retry_of = attempt_1`；`attempt_2.outcome = success`。
> 原因：retry 若作为 outcome 值，会把"关系"伪装成"状态"，丢失被重试对象与重试次数（External Design Signal #001 / DR-001）。

### result_consumed
```jsonc
{ "tool_call_id": "tc-9", "consumed_by_request_seq": 42 }
```

### task_outcome
```jsonc
{ "task_id": "tk-1", "task_success": true, "model": "gpt-5.6",
  "task_type": "research", "ended_at": "..." }
```

## 4. Qualification Resolution（跨 Observation 合并，Draft 0.4.3）

一次 Attempt 可能有多条 observation（runtime + provider），各自带 context/validity。
Attempt 级口径不是"存在一条 production+normal 就算"：

| Attempt Context | 规则 |
| --- | --- |
| 全部一致 | 取该值 |
| 部分 unknown | 取最高权威已知值（partial classification，披露） |
| 冲突（production vs test） | `inconsistent`（不压平） |

| Attempt Validity | 规则 |
| --- | --- |
| 全部一致 | 取该值 |
| normal + unknown | `partially_classified` |
| normal + suspected_invalid | `suspected_invalid`（冲突保留，不取乐观值） |

指标只查询 **derived_attempt_qualification**（attempt_context / attempt_validity /
qualification_status），不在统计 SQL 里临时 join 原始 observations 决定。

## 5. Canonical 序列化（Core 确定性要求）

- canonical JSON：排序键、无空白、NFC——所有实现 MUST 对同一 Envelope 产生完全
  相同的字节（不变量 1）
- `SIGNED_FIELDS` 覆盖全部 attribution 字段（Core 不变量 5）
- Draft 0.4.3：`surface_id` / `caller` / `decision_authority` /
  `selection_constraint` / `operation_id` / `retry_of` 属于 attribution 字段

## 6. 签名与认证（Verified Measurement Profile，可选）

- 签名是 **Verified Measurement Profile** 的能力，不是 Core 前置
- 未签名的 Observation 是合法 Core 对象：证据等级为 observed（最低显示等级）
- 签名证明来源与完整性，不证明事件事实绝对真实（见 Quality）

## 7. 纪律

- 一类观察一个 Envelope；不把多类塞进一条
- 不可观察的状态不产生观察（UNOBSERVABLE 是元级信息，在 Profile 能力矩阵声明）
- entity 归属不在观察层推断（Entity §2）
- `invocation` 一词只作为**外部协议的原始概念**（如 MCP invocation）；
  标准对象是 **Attempt**（attempt_started / attempt_completed）。旧命名迁移见
  LEGACY-MIGRATION.md
