# 如何度量 AI Agent 对软件的使用

**面向 CaaS 与 Agent Capability Economy 的统一计量基础**

*Whitepaper v0.3 · AgentMeasure Standard Draft 0.4.4*

> 作者：Roy Tong（仝夏瑞）
> 参考实现与开放实验引擎（[`lab/`](../lab/README.md)）均在 AgentMeasure 仓库发布。

## 摘要

AI Agent 越来越多地**代表用户与组织**选择、调用并与软件交易。当 Skill、MCP server、
API、CLI 这些接口越来越容易创建与分发时，经济价值日益向它们背后的稀缺能力集中：
专有数据、算力、执行、权限、交易与真实世界的履约。

这在产生支付问题之前，先产生了计量问题。一个能力要能被可靠地定价、比较、计费与
优化，生态必须先就"什么算选择、什么算一次操作、什么算成功交付、什么算结果被消费、
什么算结果、什么算计费单位"达成共识。而当钱开始在这些数字上流动时，第二个问题随
之出现：**区分真增长与假增长**——retry 膨胀、未被消费的结果、内部循环交易——在任何
人据此做预算之前。

AgentMeasure 为这个正在形成的 Capability Economy 提出一套开放计量标准：Reach →
Choice → Use → Utility → Value 的共同数据语言，未来 Metering、Marketplace 与支付
轨道可以构建其上的测量语义，以及把测量从被动观察变成可检验主张的实验语义（预注册、
guardrail、分条件效应量）。目标不是仪表盘，而是让 **Capability as a Service（CaaS，
本文用法）成为可能的计量基础**——并且可信。

## 〇.二、与 Observability 的关系

> **AgentMeasure 假设遥测可能已经存在。它的目的不是替代 tracing、logging 或
> evaluation 系统，而是在其证据之上定义可移植的测量对象与规则。**

不同系统可以观测到同一 agent 行为，却报出不同的 usage 数字：

```text
1 次逻辑操作，2 次重试

系统 A：usage = 3
系统 B：usage = 1

两个遥测系统都是对的。
它们的测量语义并不相同。
```

AgentMeasure 不重新采集 observability 数据；它在已有证据（OTel / Langfuse /
Logfire / Phoenix / 运行时日志）之上定义可跨系统比较的测量对象、统计单位与推导
规则：

```text
证据 → 测量语义 → 记账 → 结算
```

## 〇.五、测量原则

> 本节是全文档的**不可违反数据不变量**（Draft 0.4.4）。以下五条由外部工程反馈
> （attempt ledger / cache attribution / reasoning token subset / decision
> provenance / agent-assigned value）反复验证形成。

**1. 事实在解释之上存活。**
底层事实（attempt、consumption、evaluation 证据）保持不可变；语义、归并、评价、
计量与决策只能建立在事实之上，而不能覆盖事实。

**2. 统计粒度回答问题。**
Attempt 回答消费；Operation 回答逻辑使用；Task 回答结果。不同问题不得偷偷共用
统计单位（10 attempts ≠ 10 operations ≠ 10 decisions）。

**3. 不确定性是数据。**
```text
Unknown ≠ Zero
Unobservable ≠ False
Unresolved ≠ Operation
```

**4. 派生事实携带出处。**
所有 inferred operation / attribution / value 主张必须携带产生它的证据、规则与
版本（rule_id / rule_version / source_attempt_ids）。

**5. 结算不是价值。**
```text
Payment ≠ Utility
Reward ≠ Value
Settlement ≠ Incremental Value
Assigned ≠ Settled ≠ Realized ≠ Incremental
```

一句话总结：**Preserve facts. Derive semantics. Expose uncertainty.**
（保留事实，推导语义，暴露不确定性。）

## 一、从 SaaS 到 Capability Economy

软件分发曾有一条可读的链路：下载、安装、使用。每个时代有自己的经济单元。下面描述
的转变是**增量，不是替代**：与 seat-based SaaS、request-based API 并存的，
callable capabilities 正在成为 Agent 中介的软件消费的一种新经济单元。

```text
SaaS
人 → 应用 → 席位 / 月

API Economy
软件 → API → 请求 / Token

Capability Economy
Agent → Capability → 操作 / 结果
```

三股力量推动向第三行迁移：

**接口被 Agent 吸收。** UI 与工作流越来越多地由 Agent 执行，而不是呈现给人。软件
剩下的是一件可调用的外衣——skill 文件、MCP tool、CLI、endpoint。

**分发制品正在商品化。** 开放的 Skill、开放的 MCP adapter、开放的 CLI，任何人都能
在几小时内创作并发布。**接口可能变得廉价易造；能力依然是稀缺的交付物。**

**稀缺性下移。** 稀缺层不再是应用外壳，而是可调用外衣所控制的访问权：

```text
数据 · 算力 · 动作 · 权限 · 信任 · 真实世界履约
```

搜索能力因索引而稀缺；预订能力因能确认预订而稀缺；支付能力因能移动金钱而稀缺。
当商业价值集中在能力上，自然的经济单元就变成操作、数量、效应、结果——或其中任何
一项的收入分成。

**如果 Capability 成为经济单元，Capability 计量就变成基础设施。** 这是本文的论点。

### 论点与假设（Thesis and assumptions）

AgentMeasure 建立在三个**尚未完全证实**的趋势判断上：

1. Agent 将中介越来越多的软件选择与执行。
2. 更多软件能力将脱离其人类 UI 被独立暴露。
3. 基于使用、效应与结果的商业模型将与 seat-based 定价并存。

即使这些趋势发展不均衡，测量标准依然有用：对象、质量规则与声称纪律本身成立为一
套 Agent 软件测量标准。

## 一.五、Harness-native 软件与测量问题

还有一个变化正在让测量问题变得更难、也更有价值：Agent Harness 正在成为可复用
的软件运行时。DeepSeek Harness 把模型、工具、Skill、会话、沙箱、存储、Loop、
调度和 UI 都做成运行时组合的插件；Codex 通过 App Server 把同一套 Harness 暴露给
CLI、IDE、Web 和桌面客户端。一个 Harness 已经可以把另一个 Agent 运行时当作
subagent provider 来委托任务。

三个后果随之而来：

**1. 软件正在变得可组合。** Harness 在运行时按任务组合模型、Skill、Agent、
Capability、数据和执行。持久的经济单位越来越多地是任务结束后仍然存在的能力，
而不是产生它的封装应用。

**2. 遥测正在碎片化。** 每个 Harness 有自己的词汇表——run、turn、span、tool
call、subagent、request——也有自己的盲区（哪些候选能力被呈现给模型；结果是否
真的被消费）。同一行为在不同 Harness 中被不同对象和单位描述，而 Agent 调
Agent 的委托会跨越 Harness 边界，没有任何单一观察者能看到完整任务。

**3. 测量必须位于它们之上。** 软件越可组合，可移植的测量语义越重要。这正是
AgentMeasure 在既有遥测之上定义语义对象（Operation、Attempt、Delegation、
证据等级）而不是再造一种遥测格式的原因，也是 Harness Profiles——每个运行时
能/不能观察到什么的公开记录——本身成为标准一部分的原因。

我们保守地表述：随着 Agent Harness 吸收更多编排与交互逻辑，软件的经济单位
可能日益从封装应用转向可独立调用的能力。这一转变是否发生、走多远，是经验
问题。测量标准不依赖于最极端的结果成立；而是每向它走近一步，标准都变得
更必要。

## 二、先计量，后变现（Measurement Before Monetization）

CaaS 要能定价、计费与建立声誉，先要有共同的测量语义。四个问题说明这一点：

```text
一个用户任务 → 1 个 Operation → 3 次重试
收 1 次钱还是 3 次？

工具成功返回 → Agent 忽略了结果
价值交付了吗？

预订 API 执行了 → 预订从未被确认
能力履约了吗？

任务成功 → 没有这个能力也能成功吗？
Provider 能主张价值吗？
```

这些问题都无法由原始调用次数回答，也无法由支付轨道回答。它们需要关于
*operation / attempt / delivery / consumption / effect / outcome* 的一致定义，以及
把观察转化为这些对象的一致规则。这个共识就是切入点：**先计量，后变现**。

### 现实证据：商业先于计量到来

这并非假设——Agent 中介商业的分发与支付基础设施已经存在：

- MCP 生态已超过 **10,000 个已发布 Server**（Linux Foundation / AAIF 口径）；
  A2A 协议已在 **150+ 组织**进入生产使用。
- **Cloudflare Agents SDK** 允许 MCP Tool 按单次调用定价并经 x402 收费
  （[Charge for MCP tools](https://developers.cloudflare.com/agents/agentic-payments/x402/charge-for-mcp-tools/)）；
  **Coinbase x402 Bazaar** 是发现层：Agent 搜索带价格与 schema 的服务，并经 MCP
  完成付费调用（[x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar)）。
- **AWS Bedrock AgentCore Payments** 已正式 GA（2026-08），**Google AP2** 给出了
  Agent 支付协议栈的蓝图——支付轨道已不再是瓶颈。
- **OpenAI 与 Stripe 的 Agentic Commerce Protocol（ACP）** 已在真实 agentic
  commerce 流程中使用（[报道](https://www.digitaltransactions.net/openai-and-stripe-are-the-latest-fintechs-to-enable-agentic-commerce/)）。

### 计量必须可信的证据：假增长已经出现

支付基础设施先于计量到来，有一个可预测的副作用：**可被操纵的指标会被操纵**。
近期的链上分析指出，x402 式支付流水的headline交易量中，相当一部分是内部循环或
可制造交易，而非真实需求。我们不把这读作否定机器支付的理由，而是本文论点最清晰
的信号：**机器消费的商业需要机器可验证的计量**——否则下游的每个决策（定价、排名、
预算、分成）都在继承被制造的输入。

这也是为什么"合格使用"（§六）不是标准上补丁式的精细化条款：在一个流量与交易都可
被制造的经济里，合格轴（这是不是真实生产使用？）与消费轴（结果真的被使用了吗？）
是渠道与老虎机的区别。

## 三、测量对象

**Observation 是证据单位，不是业务测量单位。** AgentMeasure 先定义业务单位：

```text
Provider
    ↓
Software Entity
    ↓
Capability
    ↓
Interaction Surface
```

> **Capability 是主要的功能与测量对象。Offering 是一个或多个 Capability 的商业包装**
> ——定义于 Commercial Extension（实验性），绝不插入 Core 测量谱系。

| 对象 | 定义 | 层 |
| --- | --- | --- |
| Software Entity | 被度量的软件：Tool、Skill、API、Data Source、Agent、Application、Runtime Capability | Market |
| Capability | 实体的具名功能——主要的功能与测量对象 | Market |
| Interaction Surface | 能力的可观察调用界面（mcp_tool、cli_command、http_endpoint…） | Market |
| Decision Opportunity | 一次工具选择决策 | Behavior |
| Candidate Set | 该次决策真正提供的候选集合 | Behavior |
| Presentation | 某 selectable 出现在候选集 | Behavior |
| Selection | Agent 选择某 selectable | Behavior |
| Operation | 为某任务对某 Capability 的一次**逻辑使用** | Behavior |
| Attempt | Operation 的一次实际执行（**重试 = 多个 Attempt**） | Behavior |
| Result / Effect | 能力返回了什么 / 世界改变了什么 | Behavior |
| Task | Operation 所服务的任务单位 | Behavior |
| Client | 独立 Agent runtime / installation | Market |
| Project | package/MCP/skill 归属的软件项目 | Market |
| Category | 可比较的能力类别（搜索、预订…） | Market |
| Observation | 测量事实的证据记录（认证与签名可选，由 verification profiles 定义） | **Evidence** |

观察发生在 **Interaction Surface** 层；归属到 **Software Entity** 经机器可读
registry 解析——观察时绝不猜测。

**定价不是核心模型的对象。** `Offering`——引用一个或多个 Capability 的商业包装，
含允许的 surface、定价政策、服务级别目标与商业约束——定义在 Commercial Extension
（实验性、非规范性）中，使测量语义的演进不被任何支付设计绑架。

### 分布事件（Distribution events）

商业归因进入范围后，discovery 重新获得商业意义——但不成为选择分母：

```text
Published → Listed → Retrieved / Discovered → Presented
```

`Presented` 仍是选择指标的分母；`Discovered` 是分布归因事件，回答
*哪个 Skill / Registry / Marketplace 带来了 Capability 使用*。

## 四、Agent–Capability 交互模型

**Reach → Value 是测量视角，不是普适执行状态机。** 不同类别的能力有不同的有意义
链路：

```text
Information   操作 → 结果 → 消费
Action        操作 → 效应 → 确认
Transaction   操作 → 授权 → 提交 / 结算
```

Interaction Class（information / action / transaction / computation /
communication / control / storage / sensing）决定适用哪条链路、哪些 Utility 信号
有意义。搜索结果被*消费*；预订被*确认*；支付被*结算*。把所有能力塞进一条流水线，
产出的数字会失去含义。

## 五、测量框架

AgentMeasure 定义 **Metric Families**，不定义全局北极星。指标状态明确标注——
**Defined**（正式指标合同）、**Draft**（草案）、**Research**（方向）——概念论文
不冒充标准已全定义。

**M1 Adoption & Relationship。**（Active Clients 是采用指标，不是 Reach；Reach 由
M2 Presented / Eligibility 表达）
`Active Clients (Defined) · Repeat Clients (Draft) · Active Client-Days (Defined)`

**M2 Choice — 最 Agent-native。** Agent 有机会时会选它吗？
`Observed Selection Rate (Defined) · Observed Head-to-Head Choice Share (Defined) · First-choice Rate (Proposed)`

**M3 Execution — Use。** 选了以后好用吗？Draft 0.4 分开计数 Operation 与 Attempt——
这正是未来 Metering 需要的区分：

```text
Operation Count (Defined) · Attempt Completion (Defined) · Attempt Success (Defined)
Operation Success Rate (Defined) · Operation Resolution Coverage (Defined)
Attempts per Operation (Defined)
```

**M4 Utility — 有效使用。** 能力交付了可用信息，还是引发了预期效应？

```text
Result Consumption (Defined) · Effect Confirmation (Draft 0.5)
```

**M5 Outcome — Value。** 改善任务了吗？
`任务成功关联 (Draft) · 增量提升 (Research / Draft 0.5) · 节省时间 (Research) ·
节省成本 (Research)`

**关系测量**：Trial → Active → Repeated → Preferred → Dependent。最不可替代的
Dependent 依然是长期资产信号。

在实验引擎（`lab/`）里，这些指标族收敛为一条可操作的漏斗——
**Reach → Choice → Success → Consumption**——每一级都是可数事件，每个比率都自带
分母。指标族是词汇表；漏斗是这套词汇在受控条件下被使用的方式（§八）。

## 六、测量质量与声称纪律

证据质量不是覆盖质量，两者都不是限定质量，也都不是方法论。一组 100% 真实但只覆盖
2% Agent 的事件，不是市场数据。

```text
Measurement Quality
├── Provenance / Evidence Strength  观察来自哪里？其来源被支持得多强？
├── Coverage                        我们看到了多少世界？
├── Qualification                   这算不算真实生产使用？
├── Sampling                        采样了吗？不确定性多少？
├── Identity                        标识归一得怎么样？
└── Method/version                  用什么统计、哪个规范版本？

质量按 **Measurement Use Profile**（first_party_analytics / comparative /
cross_side_attribution / billable_audit）评估——同一份数据可能适合看内部趋势、
不适合用于计费（见 QUALITY §4）。
```

**限定使用。** 每条观察携带两条轴——Usage Context（流量来源）与 Validity（观察是否
真实）。**Strict Qualified Usage** = `production` + `validity=normal`：公共指标的
默认口径。unknown 的 context/validity 单独披露，绝不静默计入——没有"报 unknown →
进排行榜"的激励。重试是同一 Operation 的另一次 Attempt，作为可靠性信号保留，不算
多次逻辑使用。

**声称纪律。** 每个公开指标携带 Measurement Label：分子、分母、可观测人群、合格
人群、runtime 覆盖、grain、choice mode、decision authority、selection constraint。
观测到的选择绝不说成偏好；关联绝不说成因果；不可观测绝不说成负面。
**选择率的增长在消费轴与合格轴验证它之前，绝不说成毛利增长**——这条防假增长规则
从本节贯穿到 §八的每一份实验报告。

## 七、测量与计量（Measurement and Metering）

从测量标准通向 CaaS 的桥是语义的：**测量单位 ≠ 计费单位**，且三个计量概念必须
绝对分开——**Event** 是为什么计费，**Unit** 是按什么单位计，**Quantity** 是多少单位：

| 能力 | billable_event | billable_unit | billable_quantity |
| --- | --- | --- | --- |
| 搜索 | `operation_succeeded` | operation | 1 |
| 数据 | `result_delivered` | record | 1,382 |
| 算力 | `compute_completed` | gpu_second | 47.2 |
| 动作 | `effect_confirmed` | operation | 1 |
| 预订 | `effect_confirmed` | booking | 1 |
| 线索 | `outcome_qualified` | qualified_lead | 5 |
| 电商 | `transaction_settled` | transaction | 0.03（收入分成） |

因此，计量语义按 Offering 定义：

```text
Billable Event        哪个测量事实触发计费
Billable Unit         计量单位（操作、记录、GPU-秒、效应…）
Billable Quantity     单位如何计数（按策略：attempts、确认…）
Pricing Model         按操作 · 按数量 · 按效应 · 按结果 · 收入分成
Pricing Policy        版本化的价格规则（flat、阶梯、企业协议、surge…）
Quote                 单次调用实际适用的条款（quote_id、policy 版本、单价）
Metering Policy       测量事实 → 计费事实的映射（规则、排除），版本化
Metering Ledger       可重放、可纠错的计量事实账本（revision / supersedes / reversal）
Commercial Attribution  哪些参与方贡献了发现 / 选择 / 收入
```

**支付不在范围内。** AgentMeasure 不定义支付轨道、钱包、结算货币、商户记录关系或
金融托管。它产出支付系统消费的事实——合格操作、已确认效应、合格结果、计费数量、
商业归因。

> **AgentMeasure 标准化经济事实，不移动金钱。**

### 七.五、从测量到毛利：价值公式

对一个 Capability Provider，测量出的量最终合成一句经济陈述——参考实现的报告
生成器内置了这条价值公式：

```text
增量毛利 / 月
  = Agent 机会量 × 选择率提升
    × P(操作成功 | 被选择)              ← 测量值（M3）
    × P(结果被消费 | 成功)              ← 测量值（M4）
    × 付费转化
    × 单次计费事件毛利
    − 新增服务成本
```

公式右侧的每个测量因子都是带 Label 的指标，不是假设；每个业务参数必须由主张方
提供并标注来源。两条纪律适用。第一，**未经验证的提升不进公式**：一个丢失消费的
选择率提升（§二）或爆掉 guardrail 的改动（§八.三）被排除，或按测得的（更低的）
因子重算。第二，**公式对自己的经济学诚实**：在单次计费事件毛利很低的品类（搜索类
能力的单价以分计），即使很大的相对提升，其绝对毛利也供养不起测量与实验——这是
关于这个业务的事实，不是扭曲数字的理由。

## 八、归因、增量——与实验

**能力参与了成功任务，不等于它导致了成功。** 而能力被观测到的选择率也不是它的
固有属性——它是*系统*（描述、schema、候选集构成、Harness、模型）的属性，而这个
系统的大多数旋钮 Provider 自己就能改。两个事实都把测量从观察推向实验。

### 八.一、归因与价值证据阶梯

- **归因测量**（observational）：哪些能力参与了任务链——只能支持"关联"与"参与
  执行链"的结论，仅此而已。
- **增量测量**（counterfactual）：能力的存在创造了多少额外价值？随机对照是最强
  证据，但许多能力无法随机关闭。因此因果声称遵循 **Value Evidence Ladder**：

```text
V0 Association             任务成功时参与过
V1 Matched / Observational 控制已知混淆变量比较
V2 Offline Ablation        重放任务、移除能力
V3 Quasi-experiment        switchback / 自然变异
V4 Randomized Holdout      最强因果证据
```

只允许用实际产出的证据等级支持对应的因果声称强度——与测量质量的纪律一致。

### 八.二、优化空间是真实的——而且有牙齿

近期证据确立了：Agent 的选择对 Provider 可控变量敏感，且拍脑袋优化可能适得其反：

- **Hasan et al.（arXiv 2602.14878）**：103 个 MCP Server、856 个 Tool 中，97.1%
  的 Tool Description 至少有一种质量问题；增强描述使任务成功率 +5.85pp——但执行
  步骤 +67.46%，且 16.67% 的组合*退化*。
- **Microsoft BiasBusters（ICLR 2026）**：小幅修改描述即显著改变 Agent 的工具
  选择，且 Provider 受益于系统性的预训练偏置——选择可争夺，而且有偏。
- **Arcade ToolBench**：已索引的 41,900+ MCP Server（约 21.9 万 Tool）中仅 0.5%
  评 A 或以上，76.6% 评 F——生态尺度的元数据质量很差，"进入候选集之后"的优化
  空间巨大。

合起来读：选择可以被移动（机会是真的），效应有副作用（步骤、成本、消费），还有
不小比例的改动会*更糟*。这正是**运行受控实验不是可选项**的环境——也是每个实验
都需要 guardrail 的环境，因为主指标会兴高采烈地上涨，而能力本身在变坏。

### 八.三、预注册实验闭环

参考实验引擎（本仓库 `lab/`）把这条闭环工程化：

```text
Test        预注册实验：任务集 × Harness 矩阵 × 因子变体
Recommend   带置信区间的效应量 + guardrail 检查
Ship        通过 Provider 自己的发布流程灰度上线
Verify      生产复测（对 holdout）
Learn       采纳 / 回滚 / 迭代——一次有记录的经营决策
```

它不可谈判的语义，继承自 §〇.五与 §六：

1. **预注册。** 假设、主指标、guardrail、样本量与分析计划在运行前哈希锁定；报告
   只按锁定计划出确证性结论；改计划等于开新实验。这是实验引擎与结论生成器的
   区别。
2. **诚实的 null。** 不显著的结果作为 null 报出、带上区间宽度——而不是换个好看
   的次级指标继续挖。样本不足输出"不可判定"加所需样本量，绝不输出欠功效的结论。
3. **Guardrail。** 效应对照预注册阈值（成本、步骤/时延、消费、重试率）评估；
   显著但爆 guardrail 的赢报为*有效但不合格*——正是 §八.二那组
   "+5.85pp 但 +67.46% 步骤"的模式。
4. **防假增长。** 选择率提升而消费率下降时报警，并被排除出毛利主张（§七.五）。
5. **分条件效应。** 效应量按 Harness、按任务分布分别报告，与合并数字并列——
   绝不只有一个全局系数，因为下一节讲的就是那种错误。

### 八.四、离线到生产的迁移是测量问题

实验测量的是*受控*环境；生产不是。两者之间的差距不是该被平均掉的噪声——它是
一个一等公民的被测量：**迁移效应**，按条件（Harness × 任务分布）估计、自带置信
区间，小、零、负都如实报告。一个测量过的离线效应加一个如实报告的迁移差距，是
决策级的主张；一个离线效应加一句"大概能迁移"的假设，是穿着白大褂的赌博。生产
验证（对 holdout 灰度复测、跨侧连接到 Provider 的计费数据）是阶梯上的最强形式
（V4）——而它需要 §十的数据权。

### 八.五、商业归因（观察性，另立）

商业归因扩展观察侧到分发链：

```text
GitHub Skill → Registry → Agent 推荐 → Capability → 支付
```

谁贡献了发现、选择与收入？这是未来 Agent affiliate 与收入分成模型的基础——且绝不
与因果增量混为一谈。

## 九、能力信任与可比性（Capability Trust and Comparability）

能力消费者的选择受多种因素塑造。Agent 与 Marketplace 可以在品牌、政策、价格、
用户偏好与平台约束**之外**越来越多地比较机器可读的性能信号——这正是 AgentMeasure
的 Decision Authority / Selection Constraint 模型描述的轴：

```text
Capability Signals
可靠性 · 延迟 · 价格 · 新鲜度 · 消费 · 效应成功 · 结果 · 安全 · 测量覆盖
```

AgentMeasure **不计算通用 AgentMeasure Score**。Agent A 在乎价格，Agent B 在乎延迟，
Agent C 在乎隐私。排名是 Agent 与 Marketplace 的产品决策；标准只定义可比较的信号
与让它们可比较的 Label。Measurement Label 是这种可比性的基础。

## 十、观察面与数据权（Observation Surfaces and Data Rights）

不同测量 surface 能看到的东西不同；单边接入就有价值，但声称必须匹配 surface——
而且在 Agent 渠道里，**数据在谁手里决定一切声称的上限**，而不是功能存不存在：

```text
分发侧 → Agent Runtime 侧 → Provider 侧 → 效应 / 结果侧
```

| 漏斗环节 | 数据 | 通常掌握者 | Provider 单侧可得 |
| --- | --- | --- | --- |
| 发现 | 机会量、候选集构成、呈现方式 | Runtime / Registry / Agent 应用 | ✗ |
| 选择 | 实验分组、选择事件 | Harness / Agent 应用 | ✗ |
| 执行 | 调用、结果、账单、成本 | Provider | ✓ |
| 消费 | 结果消费、任务结果 | Agent 应用 / 最终用户 | 通常 ✗ |

这是架构事实，不是能靠工程补齐的产品缺口。它推出三档声称纪律——销售话术与合同
必须与所选档位严格一致：

| 数据姿态 | 能诚实主张什么 |
| --- | --- |
| **仅 Provider 侧** | 受控环境表现 + 已发生调用的诊断（去重、成功、成本、重试结构）；不承诺生产选择率与增量 |
| **+ 买方侧 / 客户自有 Agent 应用** | 完整 verified-lift 闭环：选择归因、灰度复测、增量毛利验证 |
| **+ Runtime / Registry 合作** | 机会归因、呈现优化、全漏斗测量 |

双侧观察（Agent runtime + provider）构成 cross-side corroborated；仅 Provider 侧也
足以支持 provider-scoped 的使用指标。标准不在请求关键路径上：观察异步产出、仅元
数据、落盘前伪匿名。

## 十一、互操作

标准是 transport-neutral、vendor-neutral 的。现有基础设施作为实现例子而非前提：
MCP 承载生命周期事件与 trace context；OpenTelemetry 承载工具 span；Codex/Claude
Code/DeepSeek Harness 暴露带能力声明的观察点；registry 提供实体身份。未来的支付
轨道消费标准的事实，而不是扩展标准的核心。实验格式——预注册 manifest、漏斗事件、
报告 schema——以开放 JSON Schema 发布（`lab/schemas/`），第三方可以据此实现自己的
runner 并产出互认的结果；参考实现还内置了只读 MCP 查询接口（`am mcp serve`），
让 Agent 与 CI 消费与工程师相同的证据——带证据等级，不带排名。

## 十二、不做什么与治理

AgentMeasure **不是**支付协议、Marketplace、钱包或通用声誉系统。标准不：

- 移动金钱或托管资金；
- 给能力排名或给 Provider 打分；
- 定义什么是"好"能力；
- 要求任何中心服务器、Agent 侧安装或开源 Provider。

标准本身由社区治理（AUP 流程，`proposals/`）；建立在它之上的商业产品不得控制
标准的定义。开放底座（CLI 引擎、格式、runners、报告渲染器）保持开放；商业价值只
能在其上累积——通过专有数据与交付，绝不通过回收或改许可曾经开放的东西。

## 十三、开放问题

1. **任务边界**：什么算一个"任务"，由谁定义？
2. **效应验证**：不深度集成每个目标系统，如何确认效应（预订确认、支付结算）？
3. **规模化增量**：如何在不干扰生产的情况下跨生态运行反事实实验？
4. **候选集可观测性**：Presented 是关键分母，多数 runtime 尚未暴露 routing 层信号。
5. **跨 Agent 身份**：同一 client 跨 Codex/Claude/DSH——何时可知？
6. **计费单位共识**：Provider 与支付轨道最终会就哪些测量事实达成一致，误计量的代价多大？
7. **隐私**：伪匿名下关联与留存能走多远？
8. **迁移异质性**：当离线效应跨 Harness、跨任务分布迁移不均匀时，什么样的最小
   分条件报告标准能让合并主张保持诚实？
9. **数据权**：Runtime 与买方侧应用在什么条款下会授权增量主张所需的选择侧观察——
   如果永远不授权，哪些主张仍然诚实？

## 十四、结论

软件消费者正在从人变成 Agent，经济单元正在从席位转向可调用的能力。在能力被定价、
计费与比较之前，生态需要一套共享的测量语言——什么算选择、什么算操作、什么算交付、
消费、效应与结果，以及哪些数字能支持哪些结论。而当钱与预算开始在这些数字上流动，
它同样需要把验证过的价值与制造出来的增长分开的纪律：合格性、消费证据、预注册实验、
guardrail、如实报告的迁移效应。

AgentMeasure 就是那个提案：测量语义作为基础设施，实验语义作为它的证明程序，商业
语义作为未来扩展，支付交给别人的轨道。**今天：让开发者知道 Agent 如何真实使用
自己的能力。下一步：让 Capability 可以跨 Agent 被统一度量、比较、计量——并且可以
被实验性地优化。长期：成为 CaaS 与 Agent Capability Economy 的统一计量基础。**

## 参考文献

1. RFC 2119 / BCP 14 — *Key words for use in RFCs to Indicate Requirement Levels*。
2. OpenTelemetry GenAI semantic conventions — `gen_ai.*` 工具调用遥测字段。
3. Model Context Protocol (MCP) 规范 — 工具发现与调用 surface。
4. MCP Registry — 实体解析的 server 身份入口。
5. EDPB — 伪匿名化指引（伪匿名数据仍可能属于 personal data）。
6. Linux Foundation — [AAIF 成立（MCP 生态，10,000+ servers）](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) ·
   [A2A 超 150 组织进入生产](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)。
7. Cloudflare — [Charge for MCP tools（x402 / Agentic Payments）](https://developers.cloudflare.com/agents/agentic-payments/x402/charge-for-mcp-tools/)。
8. Coinbase — [x402 Bazaar：Discover & pay over MCP](https://docs.cdp.coinbase.com/x402/bazaar)。
9. AWS — [Bedrock AgentCore Payments GA（2026-08）](https://aws.amazon.com/about-aws/whats-new/2026/08/bedrock-agentcore-payments-ga/) ·
   Google — [A developer's guide to AI agent protocols（AP2）](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)。
10. OpenAI / Stripe — Agentic Commerce Protocol（ACP），2025 年 9 月发布；见
    [Digital Transactions 报道](https://www.digitaltransactions.net/openai-and-stripe-are-the-latest-fintechs-to-enable-agentic-commerce/)。
11. Hasan et al. — *MCP Tool Descriptions Are Smelly*（[arXiv 2602.14878](https://arxiv.org/abs/2602.14878)）：97.1% 的工具描述有质量问题；成功率 +5.85pp 且步骤 +67.46%；16.67% 的组合退化。
12. Microsoft Research — [BiasBusters：LLM 工具选择偏置（ICLR 2026）](https://www.microsoft.com/en-us/research/publication/biasbusters-uncovering-and-mitigating-tool-selection-bias-in-large-language-models/)。
13. Arcade — [ToolBench：MCP Server 质量基准（41,900+ servers；0.5% 评 A）](https://www.arcade.dev/blog/introducing-toolbench-quality-benchmark-mcp-servers/)。
14. AgentMeasure 规范 — Core / Metrics / Data / Entity / Quality / Correlation
    （`standard/`）；Commercial Extension（`extensions/COMMERCIAL.md`，实验性）；
    机器可读 registry（`schemas/`、`registry/`）；开放实验引擎（`lab/`——预注册、
    漏斗采集、诚实统计、guardrail）；参考实现与 conformance vectors 同仓发布。

---

*规范全文（测量对象、生命周期、指标家族、质量、报告）、开放实验引擎（`lab/`）
与参考实现均已开源。AgentMeasure 1.0 毕业标准：2 个独立实现、3 个 runtime
profiles、2 个 tool-side 实现、公开 conformance + canonical test vectors、5-10 个
真实项目、已发布的 discrepancy report、安全与隐私审查。*
