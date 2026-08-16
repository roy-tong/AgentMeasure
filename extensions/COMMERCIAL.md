# AgentMeasure Commercial Extension（COMMERCIAL）— Experimental

> **Status: Experimental / Informative.** 本文件**不是**规范性标准的一部分，不参与
> conformance 认证。它定义 CaaS 所需的*经济语义*（economic semantics），为未来的
> Metering Profile 铺路——**不定义任何支付机制**。
>
> 核心原则：**AgentMeasure 标准化经济事实，不移动金钱。**
> Payment rails、wallets、settlement currencies、merchant-of-record relationships、
> financial custody 一律不在范围内。

## 1. 为什么需要 Commercial Extension

CORE 的测量对象回答"发生了什么"（Core，规范性）；Commercial Extension 回答
"什么可以据此计费"（经济语义，实验性）。两者分离的原因：

- 测量语义（Operation/Attempt/Result/Effect）不应被任何定价设计绑架
- 计费口径是商业决策（`3 attempts` 是否等于 `3 billable operations` 由 Metering
  Policy 决定），不是测量事实
- Marketplace / 支付方可以各自实现自己的 Metering Profile，共享同一批测量事实

## 2. 对象模型

```text
Provider
    ↓
Software Entity
    ↓
Capability            ← 经济对象（CORE §2.2）
    ↓
Offering             ← 本扩展新增：可售形态
    ↓
Interaction Surface  ← 交付界面（CORE §2.3）
```

### Provider

- 提供 Capability 的法律/商业主体；`provider_id`（registry 可选字段）
- 一个 Provider 可以有多个 Software Entity；一个 Entity 可以有多个 Capability

### Offering

一个 Capability 的一种**可售形态**：

```yaml
offering_id: com.example.research:basic
capability_id: com.example.research
provider_id: com.example
pricing_model: per_operation        # per_operation | per_quantity | per_effect | per_outcome | revenue_share
billable_unit: successful_search
price: 0.05
currency: USD
sla: {availability: "0.99", latency_p95_ms: 2000}
commercial_constraints: {min_commitment: null, credits: true}
```

| 字段 | 定义 |
| --- | --- |
| `pricing_model` | 计费方式：按操作 / 按数量 / 按效应 / 按结果 / 收入分成 |
| `billable_unit` | 计量单位（operation、record、GPU-second、confirmed effect…） |
| `price` + `currency` | 单价与币种（仅声明，不结算） |
| `sla` | 服务等级承诺（可用于 Reliability 类测量对照） |
| `commercial_constraints` | 最低承诺、信用额度等商业约束 |

## 3. 计量语义（Metering Semantics）

### 核心不变量：Measurement Unit ≠ Billable Unit

| Capability | Measurement（Core） | Billable（Offering 决定） |
| --- | --- | --- |
| Search | Operation | Successful Search |
| Data | Query | 1,000 Records |
| Compute | Job | GPU-second |
| Action | Operation | Confirmed Effect |
| Booking | Transaction | Successful Booking |
| Lead Generation | Task | Qualified Lead |
| Commerce | Transaction | % of Transaction |

### 定义

```text
Billable Event         哪个测量事实触发计费
Billable Unit          计量单位
Billable Quantity      单位如何计数（按 Metering Policy：attempts、确认、排除…）
Pricing Model          per_operation · per_quantity · per_effect · per_outcome · revenue_share
Metering Policy        测量事实 → 计费事实的确定性映射（规则、排除、取整）
Commercial Attribution 哪些参与方贡献了 discovery / selection / revenue
```

### Metering Policy 的纪律（与 CORE 一致的 fail-closed）

1. 计费数量 MUST 可追溯到已发布的测量事实（operation_id / effect confirmation）
2. 未确认的 Effect 不得计为成功交付（UNOBSERVABLE ≠ FALSE，不变量 17）
3. 重试（同 operation 的多 attempt）默认不计为多次计费，除非 Policy 明示
4. Policy 本身 MUST 公开（版本化），作为 Measurement Label 的一部分披露
5. 测量与计费之间的任何折算（rounding、bundling）MUST 在 Policy 中声明

## 4. Commercial Attribution（商业归因）

```text
GitHub Skill → Registry → Agent Recommendation → Capability → Payment
```

- 归因对象：discovery / selection / revenue
- **Commercial attribution ≠ causal incrementality**（CORE 不变量 14）
- 归属规则（first-touch / last-touch / 按贡献分成）是商业决策，由各方协议决定；
  本扩展只定义**事实字段**：`attribution_hop_id`、`hop_type`、`participant_id`、
  `conversion_scope`

## 5. 与 Core 的关系

| 层 | 文档 | 状态 |
| --- | --- | --- |
| 测量事实 | standard/CORE.md · DATA.md · METRICS.md | 规范性 |
| 经济语义 | 本文件（extensions/COMMERCIAL.md） | **Experimental / Informative** |
| 支付机制 | 不存在于本仓库 | 由外部支付基础设施提供 |

## 6. 明确的 Non-goals

- ❌ 不定义支付轨道 / 钱包 / 结算币种 / 商户记录关系 / 金融托管
- ❌ 不实现任何计费执行（billing execution）
- ❌ 不定义通用定价（每个 Provider 自定）
- ❌ 不进入 conformance 认证范围（在转正为 Profile 之前）

## 7. 转正标准（Experimental → Profile）

1. ≥2 个真实 Provider 用同一套测量事实 + 各自 Metering Policy 产出可对账账单
2. 与 ≥1 个支付/Marketplace 方完成字段级对接评审
3. 公开一份《Metering 对账报告》（discrepancy 类型报告）
4. 通过 AUP 流程（`proposals/`）进入 `standard/profiles/`
