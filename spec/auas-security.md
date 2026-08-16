# AUAS-SECURITY — Sybil、Collusion、Replay、Forgery、Malicious Aggregator（Draft 0.1）

## 1. 攻击与缓解

| # | 攻击 | 缓解 |
| --- | --- | --- |
| S1 | 工具作者自签刷量（E1 合法） | E1 不计入 corroborated；E2 需独立 trust domain；行为异常检测；与独立信号交叉验证 |
| S2 | 双侧合谋（作者控制 agent + server） | 无法完全防御；跨 trust domain 判定 + 样本审计；平台 attestation（T1）是唯一强对抗 |
| S3 | Sybil observer（字符串不同实则一人） | trust_domain + identity claims 认证；principal 注册制 |
| S4 | 重放旧收据 | receipt_id 唯一性 + 时间窗 |
| S5 | 篡改未签名语义字段 | SIGNED_FIELDS 全覆盖（AUAS-DATA §2）；篡改即验签失败 |
| S6 | 伪 commitment 关联 | commitment 输入字段全部被签名；同侧永不佐证 |
| S7 | 恶意聚合器（误报/漏报） | 聚合规则公开 + test vectors + 独立实现交叉验证；未来：signed aggregate + Merkle commitment + transparency log |
| S8 | 隐私反推 | 只发布聚合与比率；最小样本量门槛；伪匿名轮换；本地 cohort 聚合 |
| S9 | 重试链刷量 | invocation 归一 + retry 折叠 |
| S10 | 拆 API 刷榜 | 按 project roll-up；排名按 ACD 而非 raw calls |

## 2. fail-closed 原则

- 验签失败 → 无效
- 时间解析失败 → 不关联
- 模糊匹配 → 不佐证
- 平台 attestation 未验证 → UNSUPPORTED
- 无 observation_id → 拒绝入库

## 3. 标准不变量（安全相关，AUAS-CORE §4 摘录）

- Unsigned fields MUST NOT affect authenticated claims
- Ambiguous observations MUST NOT be promoted to corroborated
- Unknown MUST NOT be inferred as success
- E3 未验证时绝不由字符串授予

## 4. 未来（无区块链）

- signed aggregate statement + Merkle commitment + append-only transparency log
  提供公共可审计性——不需要 token/chain
- **标准化证据与计算，而不是标准化谁拥有真相**（无"唯一官方真相数据库"）
