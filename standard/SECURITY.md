# AgentMeasure Security — Sybil、Collusion、Replay、Forgery、Malicious Aggregator（Draft 0.4）

## 1. 攻击与缓解

| # | 攻击 | 缓解 |
| --- | --- | --- |
| TH1 | 工具作者自签刷量（E1 合法） | E1 不计入 corroborated；cross-side corroborated 需独立 trust domain；行为异常检测；与独立信号交叉验证 |
| TH2 | 双侧合谋（作者控制 agent + server） | 无法完全防御；跨 trust domain 判定 + 样本审计；平台 attestation（T1）是唯一强对抗 |
| TH3 | Sybil observer（字符串不同实则一人） | trust_domain + identity claims 认证；principal 注册制 |
| TH4 | 重放旧观察 | observation_id 唯一性 + 时间窗 |
| TH5 | 篡改未签名语义字段 | SIGNED_FIELDS 全覆盖（AgentMeasure Data §5）；篡改即验签失败 |
| TH6 | 伪 commitment 关联 | commitment 输入字段全部被签名；同侧永不佐证 |
| TH7 | 恶意聚合器（误报/漏报） | 聚合规则公开 + test vectors + 独立实现交叉验证；未来：signed aggregate + Merkle commitment + transparency log |
| TH8 | 隐私反推 | 只发布聚合与比率；最小样本量门槛；伪匿名轮换；本地 cohort 聚合 |
| TH9 | 重试链刷量 | Operation 归一（同 operation 多 attempt 只计 1 逻辑使用） |
| TH10 | 拆 API 刷榜 | 按 entity roll-up；排名按 ACD 而非 raw calls |

## 2. fail-closed 原则

- 验签失败 → 无效
- 时间解析失败 → 不关联
- 模糊匹配 → 不佐证
- 平台 attestation 未验证 → UNSUPPORTED
- 无 observation_id → 拒绝入库

## 3. 标准不变量（安全相关，AgentMeasure Core §9 摘录）

- Unsigned fields MUST NOT affect authenticated claims
- Ambiguous observations MUST NOT be promoted to corroborated
- Unknown MUST NOT be inferred as success
- E3 未验证时绝不由字符串授予

## 4. 未来（无区块链）

- signed aggregate statement + Merkle commitment + append-only transparency log
  提供公共可审计性——不需要 token/chain
- **标准化证据与计算，而不是标准化谁拥有真相**（无"唯一官方真相数据库"）
