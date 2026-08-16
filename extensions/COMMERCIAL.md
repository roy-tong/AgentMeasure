# AgentMeasure Commercial Extension（COMMERCIAL）— Experimental

> **Status: Experimental / Informative.** 本文件**不是**规范性标准的一部分，不参与
> conformance 认证。它定义 CaaS 所需的*经济语义*（economic semantics），为未来的
> Commercial Measurement Profile 铺路——**不定义任何支付机制**。
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
- **CaaS 是项目的 Vision，不是 Core Standard 成立的必要条件**：AgentMeasure Core
  即使没有任何商业化，也应成立为 Agent 软件测量标准（独立毕业，见 §9）

## 2. 对象模型（关系模型，不是树）

CORE 的测量对象链（规范性）：

```text
Software Entity = 身份容器
Capability      = 功能 / 能力单元（主要测量对象）
Interaction Surface = 交付界面
```

Commercial Extension 在其上加一层商业关系（实验性）：

```text
Provider
  ↓ owns
Software Entity
  ↓ exposes
Capability
  ↓ available through
Interaction Surface

Provider
  ↓ publishes
Offering
  ↓ references
Capability(s)           ← 一个 Offering 可含多个 Capability
  ↓ permits
Surface(s)              ← 一个 Capability 可经多个 Surface 提供
```

**Offering 不插入 Core lineage**——它是商业包装，不是测量对象。

> **Capability 是主要的功能与测量对象；Offering 是一个或多个 Capability 的商业包装。**

示例：

```text
Capability: company.research

Offering A  Basic  / per_operation / $0.05
Offering B  Deep   / per_quantity / $0.50 / 100 records

同一 Capability、不同商业条款；Basic/Pro 可共享同一 API surface
```

### Provider

- 定义：**发布或商业化提供能力的已识别主体**（an identified party that publishes
  or commercially offers capabilities）
- `legal_identity_verified: true/false` 是**可选**信息（不提前卷入 KYC / 法律主体验证）
- 一个 Provider 可以有多个 Software Entity；一个 Entity 可以有多个 Capability

### Offering

一个或多个 Capability 的**可售形态**：

```yaml
offering_id: com.example.research:basic
offering_version: "1.2"
capability_ids: [com.example.research]
provider_id: com.example
permitted_surfaces: [mcp_tool:research, http_endpoint:/v1/research]
pricing_policy_id: com.example:pp-2026.1
currency: USD
service_level_objectives:
  availability_target: "0.99"
  p95_latency_ms: 2000
commercial_constraints: {min_commitment: null, credits: true}
```

| 字段 | 定义 |
| --- | --- |
| `capability_ids` | 本 Offering 引用的 Capability（可多个） |
| `permitted_surfaces` | 本 Offering 允许的交付界面 |
| `pricing_policy_id` | 引用的定价政策（见 §4），价格不直接挂在 Offering 上 |
| `service_level_objectives` | 可用性 / 延迟目标（SLO，不是合同 SLA：不涉及 credits/remedies） |
| `commercial_constraints` | 最低承诺、信用额度等 |

### Purchasing Principal / Consumer Account（消费侧）

Agent 自己不一定是付款主体。商业语义（**不含个人 PII**）：

```yaml
consumer_account_ref: acct_9f2c        # 商业账户引用（伪匿名 / 由调用方提供）
principal_type: user | company | agent_principal | unknown
delegation_context: direct | delegated_by_user | delegated_by_company | unknown
billing_scope: project | department | account | unknown
```

用途：回答"这次 Capability Usage 应该计入谁的账单"。原始标识符不进 Core；
`consumer_account_ref` 由 Provider 侧维护，不要求 AgentMeasure 认识真实身份。

**隐私硬约束：`consumer_account_ref` MUST 以 Provider 或 Offering 为作用域
（provider_scoped_account_ref），不得成为跨 Provider 的生态级身份。**
跨 Provider 的计费身份应由 payment/commerce infrastructure 处理，不由
AgentMeasure 建立——否则托管层可能重建"一个账户跨不同 Provider 的消费轨迹"。

## 3. 计量语义：Event / Unit / Quantity 三分离

### 三个概念必须绝对分开

> **Event = 为什么计费**（哪个测量事实触发）
> **Unit = 按什么单位计**（计量单位）
> **Quantity = 多少单位**

| Capability | billable_event | billable_unit | billable_quantity |
| --- | --- | --- | --- |
| Search | `operation_succeeded` | `operation` | 1 |
| Data API | `result_delivered` | `record` | 1,382 |
| Compute | `compute_completed` | `gpu_second` | 47.2 |
| Booking | `effect_confirmed` | `booking` | 1 |
| Lead Generation | `outcome_qualified` | `qualified_lead` | 5 |
| Commerce | `transaction_settled` | `transaction` | 0.03（收入分成份额） |

**Measurement Unit ≠ Billable Unit**：`successful_search` 是事件条件，不是单位。
测量事实（Core）永远是计费语义的输入，计费折算 MUST 在 Metering Policy 中声明。

### Metering Policy

```yaml
metering_policy_id: com.example:mp-2026.1
metering_policy_version: "2026.1"
rules:
  - billable_event: operation_succeeded
    billable_unit: operation
    billable_quantity: 1
    exclusions: [replay, duplicate, suspected_invalid]
  - billable_event: effect_confirmed
    billable_unit: booking
    billable_quantity: 1
rounding: round_down_half_up
bundling: null
```

纪律（与 CORE 一致的 fail-closed）：

1. Billable Quantity MUST 可追溯到已发布的测量事实（operation_id / effect confirmation）
2. 未确认的 Effect 不得计为成功交付（UNOBSERVABLE ≠ FALSE，不变量 17）
3. 重试（同 operation 的多 attempt）默认不计为多次计费，除非 Policy 明示
4. **Policy MUST 版本化，并对依赖其结果收费的各方可用**（versioned and available
   to all parties relying on the resulting charge）
5. 公共 Marketplace / 公共 Offering 的 Policy **SHOULD** 公开或提供稳定的公开
   policy 标识符；企业合同价（Company A ≠ Company B）无需公开
6. 测量与计费之间的任何折算（rounding、bundling）MUST 在 Policy 中声明

### Quote / Pricing Policy

价格规则与单次调用适用条款分开：

```yaml
# Pricing Policy = 怎么定价（版本化）
pricing_policy_id: com.example:pp-2026.1
pricing_policy_version: "2026.1"
model: volume_tiered | flat | dynamic | enterprise_agreement | free_quota | surge
tiers: [{unit_from: 0, unit_price: "0.050000"}, {unit_from: 10000, unit_price: "0.030000"}]

# Quote = 本次调用实际适用什么商业条件
quote_id: q-8f31
offering_id: com.example.research:basic
pricing_policy_version: "2026.1"
unit_price: "0.050000"
currency: USD
valid_until: "2026-08-31T00:00:00Z"
commercial_scope: {region: null, model: null, account: acct_9f2c}
```

**价格一律用字符串**（`"0.050000"`），避免商业系统中的浮点误差。

AgentMeasure 不负责付款；但可靠的 Metering 必须知道**当时适用的是哪个价格规则**
（quote_id / pricing_policy_version）。

## 4. Metering Ledger（计量账本）

现实账单最麻烦的是重放与纠错。Metering Ledger 是 measurement facts →
commercial facts 之间**可重放、可纠错的账本**（不是付款账本）：

```yaml
meter_event_id: me-71c2
measurement_event_ref: obs-8f31       # 引用的测量事实
operation_id: op-3
metering_policy_version: "2026.1"
pricing_policy_version: "2026.1"
quantity: 1
event_time: "2026-08-16T03:00:05Z"
revision: 1
supersedes: null                       # 纠错：指向被取代的 meter event
reversal_of: null                      # 冲销：指向被撤销的 meter event
```

**核心不变量：同一个 Meter Event 重放 100 次，Billable Quantity 不能增加 100 倍。**
幂等键 = `meter_event_id`；纠错走 `revision` / `supersedes` / `reversal_of`，
而不是删除历史事实。

## 5. Billability Evidence Requirement（计费资格证据要求）

**什么等级的 measurement fact 有资格成为 billable fact？** 仅"可追溯到已发布
measurement fact"不够——Provider 自己生成、自己声明 production、自己声明
operation 的事实，不能天然成为中立的结算依据。

每个 Metering Policy 必须声明 `billing_basis` 与 `minimum_resolution`：

```yaml
billing_basis: attempt | operation | effect | outcome

minimum_resolution:
  explicit_operation_id | idempotency_key | correlated | provider_policy
```

**没有达到 minimum_resolution 的 Attempt：不可生成 invoice-grade Meter Event。**

示例：

```text
3 attempts（无 operation 证据）
  ≠ 3 billable operations
  ≠ 1 billable operation
  = 不可计费，直到 resolution evidence 出现
```

### Metering Assurance Profile（计量保证等级）

| 等级 | 定义 | 适用 |
| --- | --- | --- |
| **M0 Provider-declared** | Provider 自己观察、自己声明 | first-party analytics / 内部对账 |
| **M1 Authenticated provider** | Provider 观察带来源认证（签名/密钥） | 防抵赖的 provider 数据 |
| **M2 Bilaterally correlated** | Provider + Runtime 双侧独立观察 + 共享关联键 | 可审计的 Agent 计量 |
| **M3 Platform/third-party attested** | 受信任平台/第三方证言 | 最高等级（当前 UNSUPPORTED，不变量 11） |

**双方合同自行决定 `minimum_metering_assurance`**（如 M2）；AgentMeasure 只定义
等级与判定规则——这就是商业系统里的 auditability requirement。

## 6. Commercial Attribution（商业归因）

```text
GitHub Skill → Registry → Agent Recommendation → Capability → Payment
```

- 归因对象：discovery / selection / revenue
- **Commercial attribution ≠ causal incrementality**（CORE 不变量 14）
- 归属规则（first-touch / last-touch / 按贡献分成）是商业决策，由各方协议决定；
  本扩展只定义**事实字段**：`attribution_hop_id`、`hop_type`（published |
  listed | discovered | presented | selected）、`participant_id`、`conversion_scope`
- 分布侧事实（Published / Listed / Discovered / Presented）见 Whitepaper
  Distribution Events；**Presented 仍是 Choice 的分母，Discovered 只是分布归因事件**

## 7. 商业 Measurement Label（未来 Billable Metric 的披露）

所有可计费数字至少披露：

```text
offering_id · offering_version
metering_policy_id · metering_policy_version
pricing_policy_id / quote_id
measurement_policy
```

否则同一个 "$100 revenue" 无法知道按哪一版规则计算。

## 8. 与 Core 的关系

| 层 | 文档 | 状态 |
| --- | --- | --- |
| 测量事实 | standard/CORE.md · DATA.md · METRICS.md | 规范性 |
| 经济语义 | 本文件（extensions/COMMERCIAL.md） | **Experimental / Informative** |
| 支付机制 | 不存在于本仓库 | 由外部支付基础设施提供 |

## 9. 明确的 Non-goals

- ❌ 不定义支付轨道 / 钱包 / 结算币种 / 商户记录关系 / 金融托管
- ❌ **测量永远不进支付关键路径**：AgentMeasure 是异步的
  metering / reconciliation / audit 层，不是 transaction authorization 层——
  quote/authorization/payment 的同步链路由支付基础设施负责，AgentMeasure 的
  Metering Ledger 在其后异步对账
- ❌ 不实现任何计费执行（billing execution）
- ❌ 不定义通用定价（每个 Provider 自定）
- ❌ 不进入 conformance 认证范围（在转正为 Profile 之前）
- ❌ 不采集或解析购买者个人身份（PII）——`consumer_account_ref` 由 Provider 侧维护

## 10. 毕业路径（与 Core 独立）

**AgentMeasure Core 1.0 与商业扩展独立毕业**：Core 1.0 是 Agent 软件测量标准，
不依赖任何商业化成立；Commercial Measurement Profile 走自己的 0.x 路径。

Commercial Extension（Experimental → Profile）转正标准：

1. ≥2 个真实 Provider 用同一套测量事实 + 各自 Metering Policy 产出可对账账单
2. 与 ≥1 个支付/Marketplace 方完成字段级对接评审
3. 公开一份《Metering 对账报告》（discrepancy 类型报告）
4. 通过 AUP 流程（`proposals/`）进入 `standard/profiles/`
