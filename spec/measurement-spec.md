# AUAS-CORE — Agent Usage Attribution Standard（Draft 0.1）

> **agent-used 是 AUAS 的参考实现。** AUAS 定义 AI Agent 软件使用证据如何被表示、
> 认证、关联、定级与聚合，使不同主体能够在不依赖单一平台、不采集用户内容的
> 前提下，对 Agent 软件使用情况进行可验证、可比较的测量。
>
> **AUAS 不定义谁是真相来源，而定义什么证据、按照什么规则，可以支持什么结论。**
>
> 本文件是 Core：vendor-neutral、transport-neutral。MCP/OTel 是 Transport/Telemetry
> Binding；Codex/Claude/DSH 是 Agent Runtime Profile——都不是协议成立的前提。

## 0. 版本与状态

- 版本：**Draft 0.1**（未稳定；Evidence/Identity/Correlation/Receipt 仍在演进）
- 毕业到 AUAS 1.0 的标准（Graduation Criteria）：2 个独立实现 + 3 个 agent runtime
  profiles + 2 个 tool-side 实现 + 公开 conformance + canonical test vectors +
  5-10 个真实项目 + discrepancy report + security/privacy review
- 变更机制：AUP（Agent Usage Proposal）：Draft → Discussion → Accepted →
  Experimental → Stable → Deprecated

## 1. 定位

**协议目标**：在不信任工具作者自报数据、不依赖单一 Agent 平台、又不能收集用户
内容的情况下，产生可验证、可比较的 Agent 软件使用数据。

**核心机制**（详见 AUAS-DATA/TRUST/CORR）：

```text
Signed Observations (Usage Receipts)
        │
        ▼
Identity Verification
        │
        ▼
Invocation Reconstruction
        │
        ▼
Evidence Qualification
        │
        ▼
Privacy-preserving Aggregation
        │
        ▼
Usage Metrics（必须携带 Policy + Scope）
```

**确定性**：同一组输入 + 同一个 Measurement Policy，任何符合规范的实现必须得到
相同结果（见 §5 不变量）。

## 2. 参与者（Actors）

| Actor | 职责 | 信任假设 |
| --- | --- | --- |
| Agent Runtime | 执行 agent；产生调用 | 不假设可信（可能被刷） |
| Tool Runtime | 执行工具；服务调用 | 不假设可信（可能自刷） |
| Observer | 在 runtime 边界产生观察（发出 Receipt） | 有可验证身份（公钥） |
| Verifier | 验签、判定观察有效性 | 诚实执行验证规则 |
| Correlator | 把观察确定性合并为 Invocation | 诚实执行匹配规则 |
| Attestor | 平台级背书（E3/attestation） | 受信任平台 |
| Aggregator | 按 Policy 聚合 | 只拿到聚合/收据，无内容 |
| Registry | 项目身份、observer 身份声明 | 认证 claim |

**信任最小化**：任何单一主体都不能伪造"被独立佐证的使用"。E2 需要 ≥2 个
independently controlled observer（AUAS-TRUST：trust domain 判定）。

## 3. 使用漏斗（Usage Funnel）

**Install ≠ Usage。** Observable fact 与 inferred value 严格分离——能观测的才叫
事实；需要推断的一律标注为推断（不能推断就 unknown）。

| 阶段 | 定义 | 事实/推断 | 可观察者 |
| --- | --- | --- | --- |
| D0 Available | 工具进入 Agent 可见集合 | 事实 | Registry / runtime |
| D1 Discovered | Agent/runtime 检索或加载定义（tools/list、skill 加载） | 事实 | Agent runtime |
| S0 Selected | 模型/runtime 生成 tool_use、决定调用 | 事实 | Agent runtime |
| S1 Execution Started | runtime 开始执行 | 事实 | 双侧 |
| S2 Execution Completed | 返回 success/failure/denied | 事实 | 双侧 |
| S3 Result Delivered | 结果进入 Agent context | 事实 | Agent runtime |
| S4 Result Consumed | 后续模型请求实际消费结果 | 事实（部分平台可观测） | Agent runtime（部分） |
| S5 Task Contribution | 结果影响最终任务结果 | **推断** | 研究 |

**注意**：D1（discovered）≠ S0（selected）——tools/list 命中只证明可用/被发现。
lifecycle（AUAS-DATA 的 L0-L3）是简化生命周期；证据（AUAS-TRUST）是独立维度。

## 4. 标准不变量（Standard Invariants）

> 任何 AUAS 实现必须遵守。相当于协议的 consensus rules。

1. **Same input + same policy = same result**（确定性）
2. **One invocation MUST be counted at most once**
3. **Duplicate observations MUST NOT increase invocation count**
4. **Evidence MUST NOT be self-declared**（adapter 只报事实）
5. **Unsigned fields MUST NOT affect authenticated claims**（签名字段覆盖见 AUAS-TRUST）
6. **Ambiguous observations MUST NOT be promoted to corroborated**（fail-closed）
7. **Unknown MUST NOT be inferred as success**
8. **Metrics MUST declare scope + policy + window**（AUAS-COVERAGE + AUAS-METRICS）
9. **Public receipts MUST NOT contain user content**
10. **Corroboration MUST NOT assume independent = different strings**（trust domain 判定）
11. **E3/platform attestation 未验证时 = UNSUPPORTED，绝不由字符串授予**
12. **Outcome 冲突 MUST 被保留**（derived_outcome = inconsistent），不得压平

## 5. AUAS 文档结构

| 文档 | 负责 |
| --- | --- |
| AUAS-CORE（本文） | Actors、漏斗、不变量 |
| AUAS-DATA | Receipt / Manifest / Aggregate schemas（含 canonical JSON） |
| AUAS-TRUST | Principal、Key、Signature、Trust Domain、Attestation、Evidence Profile |
| AUAS-CORR | Observation → Invocation 的确定性规则（含 ambiguity fail-closed） |
| AUAS-METRICS | ACD、Invocation、Consumption、窗口、denominator |
| AUAS-COVERAGE | Scope、sampling、coverage、uncertainty |
| AUAS-PRIVACY | Identifier、retention、aggregation、redaction |
| AUAS-SECURITY | Sybil、collusion、replay、forgery、malicious aggregator |
| AUAS-BIND-* | MCP / OTel 如何承载 AUAS（transport binding） |
| AUAS-PROFILE-* | Codex / Claude / DSH 具体实现（agent runtime profile） |
| Verification | Conformance + Test Vectors（语言无关） |
| Evolution | AUP 流程 |
