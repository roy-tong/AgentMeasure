# Evidence Model（证据模型）

> 回答：这条 usage 记录有多可信？二元"真/假"在开放生态里不成立，证据是分级的。
>
> **核心原则：Evidence is derived, never self-declared.**
> adapter 只报告观察事实（observer/side/provenance/signature）；证据等级一律由
> verifier 从事实计算。任何"我是 E2"的自声明都无效——这条原则与
> "OpenTelemetry tells us how telemetry travels" 同等重要。

## 1. 证据等级（verifier 计算，adapter 不声明）

| 等级 | 名称 | 判定规则（verifier） | 可被什么攻击 | 公共统计用途 |
| --- | --- | --- | --- | --- |
| **E0** | Observed | 有观察事实，但无认证 | 任意一方伪造 | 不计入 attributed 统计 |
| **E1** | Source-authenticated | 观察带有效 **Ed25519** 签名（非对称：验签公钥可公开） | 持私钥方自刷 | 计入 source-authenticated |
| **E2** | Correlated | 同一 invocation 有 ≥2 条**独立 observer**（不同 principal）的观察 | 双侧合谋 | **计入 corroborated（核心）** |
| **E3** | Platform-attested | provenance=platform 且平台 attestation 验证通过 | 平台自身 | 最高可信 |

**E1 密码学**：Ed25519 非对称签名。HMAC 是对称密钥——验签密钥公开即等于公开签名
密钥，任何人均可伪造，不满足 public verification。E1 只证明"某主体确实签发了这条
观察"，不证明真实使用（signature ≠ usage truth）。

## 2. 判定规则

### E1：Source-authenticated

- 观察含 `signature`（Ed25519 over canonical fields）+ `key_id`
- `key_id` 对应公开目录中的公钥（`keys/<key_id>.pub`）
- 验签通过 → E1
- 注意：E1 不等于"真的有 Agent 调用"——持私钥方可以自签。E1 只证明来源与完整性。

### E2：Correlated（corroborated usage）

同一 invocation 有 ≥2 条**独立 observer principal** 的观察（匹配见 invocation
matcher：精确 tool_call_id 优先，其次 trace+tool+时间窗）。同侧多条观察、同
harness 内部生命周期配对都不构成独立佐证。

### E3：Platform-attested

- provenance=platform 且平台 attestation（平台签名/API 确认）验证通过
- 需要平台合作或平台开放 attestation 接口（升级路径，非前置）

## 2.5 生命周期 ≠ 证据（Lifecycle vs Evidence）

同一 harness 内部的 `tool/call → tool/result` 配对只证明**生命周期完成**，
不构成独立佐证。两个维度严格分离：

| 维度 | 内容 | 谁能提供 |
| --- | --- | --- |
| Lifecycle L0-L3 | Selected → Started → Returned → Consumed | 单个 runtime 即可 |
| Evidence E0-E3 | 观察是否可信 | verifier（多来源/签名/平台） |

DSH 的 call/result 配对 → `lifecycle_stage: L2 (Returned)`，证据由 verifier 判定
（provenance=platform 单侧 → E0/E1，配合工具侧观察才可能 E2）。

## 3. 反合谋说明

E2 无法防御"工具作者与自己的另一个 agent 合谋刷量"。
缓解：身份图（identity.md）+ 行为异常检测 + 与独立信号交叉验证（GitHub API clone、npm 下载、registry 收录）。
E3 是唯一对抗合谋的强证据——这也是平台路径的长期价值所在。

## 4. 公开口径

| 口径 | 定义 | 展示 |
| --- | --- | --- |
| observed calls | E0+ | 不单独展示 |
| source-verified calls | E1+ | 明细（带 provenance 标注） |
| **corroborated usage** | E2+ | **默认首要展示** |
| platform-attested usage | E3 | 标记 ✅ |

徽章示例：

```
Agent Usage · 30d
18.4k verified calls     ← E1+
2.7k active sessions    ← Adoption 首要指标
96.2% success
71% corroborated        ← E2 占比
Codex · Claude Code · DSH
```
