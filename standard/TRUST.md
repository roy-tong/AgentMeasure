# AgentMeasure Trust — Principal、Signature、Trust Domain、Evidence Profile（Document revision 0.4.3）

## 1. Observer Principal

```jsonc
{
  "principal_id": "codex-hook@acme",
  "public_key": "base64(Ed25519)",
  "controlled_by": "acme",          // 控制主体
  "deployment_id": "machine-x",
  "trust_domain": "acme",           // 信任域（核心判定依据）
  "identity_claims": ["github.com/acme", "docs.acme.dev"]
}
```

**关键纪律**：principal 字符串本身不代表独立性。`codex-client@machine-x` 与
`mcp-server@machine-x` 技术上不同但可能同域控制——独立佐证必须问
"有几个 **independently controlled** observer"（按 trust_domain 判定）。

## 2. 签名

- 算法：Ed25519（私钥签名/公钥验证；HMAC 不满足 public verification）
- 覆盖：SIGNED_FIELDS（AgentMeasure Data §2）；任何影响归因的字段未签名即无效
- 密钥管理：`key_id` → 公钥目录（可公开）；私钥本地（chmod 600）；支持撤销
- fail-closed：验签失败/密钥未知/无法验证 → 不提升任何等级

## 3. Evidence Profile（多轴，底层模型）

**不采用单一字母阶梯**（不同概念不在同一轴）。底层保留证据向量，上层才压缩为显示标签：

| 轴 | 取值 | 含义 |
| --- | --- | --- |
| Authentication | A0 none / A1 signed / A2 identity-verified | 我知道是谁说的 |
| Corroboration | C0 single / C1 multiple | 有几方这么说 |
| Independence | I0 unknown / I1 distinct runtime / I2 distinct trust domain | 是否同一主体控制 |
| Attestation | T0 none / T1 platform-attested | 是否有受信任平台背书 |
| Match | none / heuristic / exact-call-id / trace-verified | 关联强度（单词取值；不用 M 码，避免与商业计量等级冲突） |

## 4. 派生显示等级（UI/API 层）

| 显示 | 条件 |
| --- | --- |
| Observed | 有观察 |
| Authenticated | A1+ |
| Corroborated | C1（≥2 observer） |
| Independently Corroborated | C1 + I2（跨 trust domain） |
| Platform Attested | T1（**当前 UNSUPPORTED**——未实现平台签名验证前，任何 `provenance="platform"` 字符串不授予） |

## 5. 四维正交（Draft 0.4.3）

| 维度 | 回答 | 取值体系 |
| --- | --- | --- |
| Evidence Profile | observation 有多可信？ | 多轴向量 → 单词显示等级 |
| Caller Identity | 调用者是谁，判断有多可信？ | unknown / declared / correlated / attested |
| Measurement Use Profile | 这份数据准备用于什么？ | first_party_analytics / comparative / cross_side_attribution / billable_audit（QUALITY §4） |
| Billing Requirements | 若用于收费，需满足哪些 predicate？ | billing_requirements（COMMERCIAL §6，非等级） |

四个维度正交，**不再新增任何字母阶梯**（M 码只存在于过去的文档，见 LEGACY-MIGRATION.md）。

## 6. Attestation（未实现）

- 需要平台私钥签名或平台官方 API 确认
- 未实现前：`PLATFORM_ATTESTATION = UNSUPPORTED`（fail-closed，绝不由字符串授予）
- 实现后需独立的验证规则与密钥目录
