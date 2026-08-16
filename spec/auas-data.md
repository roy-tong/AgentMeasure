# AUAS-DATA — Receipt / Manifest / Aggregate Schemas（Draft 0.1）

## 1. Usage Receipt（一等公民）

Receipt 是系统间流动的最小单位：某个可验证 Observer 对一次 Agent-tool interaction
所做的签名、隐私安全声明。

```jsonc
{
  "spec_version": "auas-0.1",
  "receipt_id": "uuid",
  "observed_at": "2026-08-16T03:00:00Z",
  "observer_principal": "codex-hook@acme",
  "observer_side": "client",            // client | server | platform
  "provenance": "hook",                  // hook | otel | wrapper | platform
  "trust_domain": "acme",                // 独立佐证判定的关键（AUAS-TRUST）
  "project_id": "github.com/foo/bar",
  "tool": "foo.search",
  "tool_call_id": "tc-9",                // 精确关联键（如可得）
  "trace_id": "trace-9",                 // 结构关联键（如可得）
  "session_key": "p-...",                // 伪匿名（内存内生成，绝不落原始值）
  "outcome": "success",                  // success|failure|retry|denied|unknown
  "lifecycle_stage": "L2",               // L0-L3（生命周期，非证据）
  "correlation_commitment": "c-...",     // H(protocol||project||trace||call_id)
  "sampling": null,                      // 或 {"method":"fixed","probability":0.1}
  "signature": "base64",                 // Ed25519 over canonical(SIGNED_FIELDS)
  "key_id": "receipt-key"
}
```

**MUST NOT 包含**：prompt、tool input/output、path、conversation、user identity。

## 2. Canonical Serialization（签名字节确定性）

规范：AUAS canonical JSON（RFC 8785 精神）：
1. 对象键按 UTF-8 字节序排序
2. 无空白
3. 字符串 UTF-8 + NFC 归一化 + JSON 转义（ensure_ascii=False）
4. 数字：整数原样；浮点 ES6 风格（规范字段限整数/字符串/null）
5. 递归嵌套

**SIGNED_FIELDS**（影响 attribution/correlation/qualification，MUST 签名）：
`receipt_id, spec_version, observed_at, observer_principal, observer_side,
provenance, project_id, tool, tool_call_id, trace_id, session_key, outcome,
lifecycle_stage, source_event_id, sampling, trust_domain`

`signature` 与 `key_id` 不参与签名（key_id 是验签密钥选择器）。

## 3. Manifest（批量传输）

```jsonc
{
  "spec_version": "auas-0.1",
  "manifest_id": "uuid",
  "observer_principal": "...",
  "created_at": "...",
  "receipts": [ ...UsageReceipt... ],
  "signature": "..."
}
```

## 4. Aggregate Statement（公开数据面）

```jsonc
{
  "spec_version": "auas-0.1",
  "policy": "AUAS/Core-1",
  "project_id": "github.com/foo/bar",
  "window": {"start": "...", "end": "...", "days": 30},
  "coverage": {"hosts": ["codex"], "observer_population": "participating",
               "sampling": "unsampled-only", "coverage_claim": "partial"},
  "metrics": {
    "acd": 2841,
    "attributed_invocations": 18321,
    "corroborated_share": 0.73,
    "success_rate": 0.97
  },
  "signed_by": "aggregator-key"
}
```

## 5. 版本与演进

- 任何字段变更走 AUP；`spec_version` 递增
- 不向后兼容的字段变更 → 新 spec_version；实现必须显式声明支持版本
