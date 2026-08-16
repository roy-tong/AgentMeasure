# AgentMeasure Data — Observation Envelope（Draft 0.4.1）

> Observation Envelope 是 Core 的系统间交换对象（interchange object）。
> 签名与认证是 **Verified Measurement Profile** 的可选能力（Core §10），
> Core-conformant 实现不实现 Ed25519 也成立。
> Draft 0.4.1：Envelope 拆分 raw surface 层与 derived 解析层——原始观察不携带
> 看似权威的实体标识（Entity fail-closed，见 AgentMeasure Entity §2）。

## 1. Observation Envelope（统一外壳）

### Canonical 示例：**默认 unknown**（只有证据才升级）

```jsonc
{
  "spec_version": "agentmeasure-0.4",
  "observation_id": "uuid",
  "observation_type": "presentation | selection | invocation | completion | consumption | task_outcome",
  "observer": {"principal": "codex-hook@acme", "trust_domain": "acme", "side": "client"},
  "observed_at": "2026-08-16T03:00:00Z",
  "deployment_context": {
    "project_id": "github.com/foo/bar"      // 采集方内部数据组织的标识；
                                            // 不是实体权威（见 surface 层与 Entity §2）
  },
  "surface": {                              // RAW 层：观察发生在 surface（Core §2.3）
    "surface_id": "mcp_tool:bar.search",
    "surface_namespace": "io.github.foo",   // surface 的注册/命名空间（尽力而为）
    "provider_claim": null,                 // 可选：provider 自声明（不视为权威）
    "capability_claim": null                // 可选：capability 自声明（不视为权威）
  },
  "client_key": "p-...",                    // 伪匿名，内存内生成
  "usage_context": "unknown",               // 默认 unknown（Draft 0.4.2）
  "validity": "unknown",                    // 默认 unknown（Draft 0.4.2）
  "context_source": "none",                 // none | provider_configuration | collector_derived | runtime_propagated
  "validity_source": "none",                // none | collector_derived | runtime_propagated
  "source_sequence": 1007,                  // 单调递增；云端据此检出丢失缺口
  "sampling": null,
  "provenance": "hook",
  "payload": { /* 类型特有字段 */ },
  "signature": null,                        // OPTIONAL — Verified Measurement Profile
  "key_id": null                            // OPTIONAL — Verified Measurement Profile
}
```

> **默认 unknown 是纪律，不是缺陷。** CI、benchmark、health check、cron、人工调用
> 只要进了 production server 就可能污染 Strict Qualified；只有证据（部署配置 /
> collector 派生的重复/重放/合成检测）才允许升级，且必须携带
> `context_source` / `validity_source`。

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
> operation_id …）；不知道的字段留 null，MUST NOT 编造。谱系完整度是
> 指标的披露维度（Measurement Label：lineage coverage）。

## 2. Derived 层（解析结果，不在 adapter 产生）

entity / capability 归属由统计层（registry 解析）产生，**不是观察的一部分**：

```jsonc
// Derived resolution（aggregator/解析器写入；adapter 永不产生）
{
  "resolved_entity_id": "github.com/foo/bar",
  "resolved_capability_id": "github.com/foo/bar:search",
  "registry_version": "2026.1",
  "resolution_status": "resolved | ambiguous | unknown"
}
```

- 无匹配 → `resolution_status=unknown`（不猜测）
- 多 registry 条目冲突 → `ambiguous`，该观察不计入任何 entity 计数（不变量 21）
- 公开指标 MUST 披露 `registry_version` 与 resolution 分布

## 3. 六类 Payload

### presentation
```jsonc
{ "decision_id": "d1", "candidate_set_id": "cs1", "category_id": "search.web.general",
  "category_version": "v1", "choice_mode": "exclusive", "rank_in_candidate_set": 3 }
```

### selection
```jsonc
{ "decision_id": "d1", "selection_id": "s1", "rank": 1,
  "decision_authority": "model",        // Core §2.5：model|router|workflow|user|policy|platform|unknown
  "selection_constraint": "autonomous", // Core §2.6：autonomous|recommended|required|user_requested|fallback|forced|unknown
  "selection_reason_observable": false }
```

### invocation（= Attempt，Core §2.4）
```jsonc
{ "tool_call_id": "tc-9", "trace_id": "t-9", "started_at": "...",
  "operation_id": "op-3",               // 逻辑使用；未知留 null（不变量 23）
  "task_id": "tk-1" }
```

### completion
```jsonc
{ "tool_call_id": "tc-9", "outcome": "success|failure|denied", "duration_ms": 1200,
  "error_type": null }
```

### consumption
```jsonc
{ "tool_call_id": "tc-9", "consumed_by_request_seq": 42 }   // 后续请求实际使用
```

### task_outcome
```jsonc
{ "task_id": "tk-1", "task_success": true, "model": "gpt-5.6",
  "task_type": "research", "ended_at": "..." }
```

## 4. Canonical 序列化（Core 确定性要求）

- canonical JSON：排序键、无空白、NFC（确定性字节）——所有实现 MUST 对同一
  Envelope 产生完全相同的字节（可复现性，不变量 1）
- `SIGNED_FIELDS` 覆盖全部 attribution 字段（Core 不变量 5）
- Draft 0.4：`surface_id` / `decision_authority` / `selection_constraint` /
  `operation_id` 属于 attribution 字段

## 5. 签名与认证（Verified Measurement Profile，可选）

- 签名（Ed25519 等）是 **Verified Measurement Profile** 的能力，不是 Core 前置
- 未签名的 Observation 是合法 Core 对象：证据等级为 observed（最低显示等级），Label 披露即可
- 认证观察（Signed Observation）承载：来源（principal）、完整性（canonical 签名）、
  防重放（nonce/时间窗）
- 签名不证明事件事实绝对真实——只证明来源与完整性（见 AgentMeasure Quality）

## 6. 纪律

- 一类观察一个 Envelope；不把多类塞进一条
- 不可观察的状态不产生观察（UNOBSERVABLE 是元级信息，在 Profile 能力矩阵声明，
  不伪造 FALSE 观察）
- entity 归属不在观察层推断（Core §2.0 / AgentMeasure Entity §2）
