# 如何度量 AI Agent 对软件的使用

**面向 CaaS 与 Agent Capability Economy 的统一计量基础**

*Whitepaper v0.2 · AgentMeasure Standard Draft 0.4*

> 作者：Roy Tong（仝夏瑞）
> 参考实现：AgentMeasure 仓库（GitHub）。

## 摘要

AI Agent 正在同时成为软件消费者与自主经济行动者。当 Skill、MCP server、API、CLI
这些接口越来越容易创建与分发时，经济价值日益向它们背后的稀缺能力集中：专有数据、
算力、执行、权限、交易与真实世界的履约。

这在产生支付问题之前，先产生了计量问题。一个能力要能被可靠地定价、比较、计费与
优化，生态必须先就"什么算选择、什么算一次操作、什么算成功交付、什么算结果被消费、
什么算结果、什么算计费单位"达成共识。

AgentMeasure 为这个正在形成的 Capability Economy 提出一套开放计量标准：Reach →
Choice → Use → Utility → Value 的共同数据语言，加上未来 Metering、Marketplace 与
支付轨道可以构建其上的测量语义。目标不是仪表盘，而是让 **Capability as a Service
（CaaS）成为可能的计量基础**。

## 一、从 SaaS 到 Capability Economy

软件分发曾有一条可读的链路：下载、安装、使用。每个时代有自己的经济单元：

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

> **Capability 是经济对象。Interaction Surface 是交付界面。Software Entity 是身份与容器。**

| 对象 | 定义 | 层 |
| --- | --- | --- |
| Software Entity | 被度量的软件：Tool、Skill、API、Data Source、Agent、Application、Runtime Capability | Market |
| Capability | 实体的具名功能——经济对象 | Market |
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
| Observation | 对上述行为的证据性观察（签名收据） | **Evidence** |

观察发生在 **Interaction Surface** 层；归属到 **Software Entity** 经机器可读
registry 解析——观察时绝不猜测。

**定价不是核心模型的对象。** `Offering`（定价模型、计费单位、价格、SLA、商业约束）
定义在 Commercial Extension（实验性、非规范性）中，使测量语义的演进不被任何支付
设计绑架。

## 四、Agent–Capability 交互模型

**Reach → Value 是测量视角，不是普适执行状态机。** 不同类别的能力有不同的有意义链路：

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

AgentMeasure 定义 **Metric Families**，不定义全局北极星。

**M1 Distribution — Reach。** 能力进入 Agent 世界了吗？
`Available Clients · Eligible Opportunities · Presentations · Presentation Rate · Distribution Coverage`

**M2 Choice — 最 Agent-native。** Agent 有机会时会选它吗？
`选择数 · Observed Selection Rate（Observed Selected ÷ Presented）· Conditional Choice Share · 首选率`

**M3 Execution — Use。** 选了以后好用吗？Draft 0.4 分开计数 Operation 与 Attempt——
这正是未来 Metering 需要的区分：

```text
Operations · Attempts · Attempts per Operation
Operation 完成率 · Operation 成功率
Attempt 失败率 · 重试率 · 延迟
```

**M4 Utility — 有效使用。** 能力交付了可用信息，还是引发了预期效应？

```text
Result Utility     已交付 · 已消费 · 已接受
Effect Utility     已应用 · 已确认 · 已回退 / 失败
```

**M5 Outcome — Value。** 改善任务了吗？
`任务成功关联 · 增量提升 · 节省时间 · 节省成本`

**关系测量**（从独立章节降级为小节）：Trial → Active → Repeated → Preferred →
Dependent。最不可替代的 Dependent 依然是长期资产信号。

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
```

**限定使用。** 每条观察携带两条轴——Usage Context（流量来源）与 Validity（观察是否
真实）。**Strict Qualified Usage** = `production` + `validity=normal`：公共指标的
默认口径。unknown 的 context/validity 单独披露，绝不静默计入——没有"报 unknown →
进排行榜"的激励。重试是同一 Operation 的另一次 Attempt，作为可靠性信号保留，不算
多次逻辑使用。

**声称纪律。** 每个公开指标携带 Measurement Label：分子、分母、可观测人群、合格
人群、runtime 覆盖、grain、choice mode、decision authority、selection constraint。
观测到的选择绝不说成偏好；关联绝不说成因果；不可观测绝不说成负面。

## 七、测量与计量（Measurement and Metering）

从测量标准通向 CaaS 的桥是语义的：**测量单位 ≠ 计费单位**。

| 能力 | 测量 | 可计费 |
| --- | --- | --- |
| 搜索 | Operation | 成功搜索 |
| 数据 | Query | 1,000 条记录 |
| 算力 | Job | GPU-秒 |
| 动作 | Operation | 已确认的效应 |
| 预订 | Transaction | 成功预订 |
| 线索 | Task | 合格线索 |
| 电商 | Transaction | 交易额的 % |

因此，计量语义按 Offering 定义：

```text
Billable Event        哪个测量事实触发计费
Billable Unit         计量单位（操作、记录、GPU-秒、效应…）
Billable Quantity     单位如何计数（按策略：attempts、确认…）
Pricing Model         按操作 · 按数量 · 按效应 · 按结果 · 收入分成
Metering Policy       测量事实如何映射到计费事实（规则、排除）
Commercial Attribution  哪些参与方贡献了发现 / 选择 / 收入
```

**支付不在范围内。** AgentMeasure 不定义支付轨道、钱包、结算货币、商户记录关系或
金融托管。它产出支付系统消费的事实——合格操作、已确认效应、合格结果、计费数量、
商业归因。

> **AgentMeasure 标准化经济事实，不移动金钱。**

## 八、归因与增量

**能力参与了成功任务，不等于它导致了成功。**

- **归因测量**（observational）：哪些能力参与了任务链——只能支持"关联"与"参与执行链"的结论。
- **增量测量**（counterfactual）：能力的存在创造了多少额外价值——随机对照（有 / 无），比较任务成功、时间、成本与质量。

商业归因扩展观察侧到分发链：

```text
GitHub Skill → Registry → Agent 推荐 → Capability → 支付
```

谁贡献了发现、选择与收入？这是未来 Agent affiliate 与收入分成模型的基础——且绝不
与因果增量混为一谈。

## 九、能力信任与可比性（Capability Trust and Comparability）

能力消费者（Agent、Marketplace 或人）比较的是信号，不是品牌：

```text
Capability Signals
可靠性 · 延迟 · 价格 · 新鲜度 · 消费 · 效应成功 · 结果 · 安全 · 测量覆盖
```

AgentMeasure **不计算通用 AgentMeasure Score**。Agent A 在乎价格，Agent B 在乎延迟，
Agent C 在乎隐私。排名是 Agent 与 Marketplace 的产品决策；标准只定义可比较的信号
与让它们可比较的 Label。Measurement Label 是这种可比性的基础。

## 十、观察与部署架构（Observation & Deployment Architecture）

不同测量 surface 能看到的东西不同；单边接入就有价值，但声称必须匹配 surface：

```text
分发侧 → Agent Runtime 侧 → Provider 侧 → 效应 / 结果侧
```

| Surface | 能看什么 |
| --- | --- |
| Registry | 发现 / 可用性 |
| Agent runtime | 呈现 / 选择 / 消费 |
| Capability provider | 操作 / attempts / 结果 |
| 目标系统 | 效应 / 交易 |
| 实验层 | 增量 |

双侧观察（Agent runtime + provider）构成佐证（E2）；仅 Provider 侧也足以支持
provider-scoped 的使用指标。标准不在请求关键路径上：观察异步产出、仅元数据、
落盘前伪匿名。

## 十一、互操作

标准是 transport-neutral、vendor-neutral 的。现有基础设施作为实现例子而非前提：
MCP 承载生命周期事件与 trace context；OpenTelemetry 承载工具 span；Codex/Claude
Code/DeepSeek Harness 暴露带能力声明的观察点；registry 提供实体身份。未来的支付
轨道消费标准的事实，而不是扩展标准的核心。

## 十二、不做什么与治理

AgentMeasure **不是**支付协议、Marketplace、钱包或通用声誉系统。标准不：

- 移动金钱或托管资金；
- 给能力排名或给 Provider 打分；
- 定义什么是"好"能力；
- 要求任何中心服务器、Agent 侧安装或开源 Provider。

标准本身由社区治理（AUP 流程，`proposals/`）；建立在它之上的商业产品不得控制
标准的定义。

## 十三、开放问题

1. **任务边界**：什么算一个"任务"，由谁定义？
2. **效应验证**：不深度集成每个目标系统，如何确认效应（预订确认、支付结算）？
3. **规模化增量**：如何在不干扰生产的情况下跨生态运行反事实实验？
4. **候选集可观测性**：Presented 是关键分母，多数 runtime 尚未暴露 routing 层信号。
5. **跨 Agent 身份**：同一 client 跨 Codex/Claude/DSH——何时可知？
6. **计费单位共识**：Provider 与支付轨道最终会就哪些测量事实达成一致，误计量的代价多大？
7. **隐私**：伪匿名下关联与留存能走多远？

## 十四、结论

软件消费者正在从人变成 Agent，经济单元正在从席位转向可调用的能力。在能力被定价、
计费与比较之前，生态需要一套共享的测量语言——什么算选择、什么算操作、什么算交付、
消费、效应与结果，以及哪些数字能支持哪些结论。

AgentMeasure 就是那个提案：测量语义作为基础设施，商业语义作为未来扩展，支付交给
别人的轨道。**今天：让开发者知道 Agent 如何真实使用自己的能力。下一步：让
Capability 可以跨 Agent 被统一度量、比较和计量。长期：成为 CaaS 与 Agent Capability
Economy 的统一计量基础。**

## 参考文献

1. RFC 2119 / BCP 14 — *Key words for use in RFCs to Indicate Requirement Levels*。
2. OpenTelemetry GenAI semantic conventions — `gen_ai.*` 工具调用遥测字段。
3. Model Context Protocol (MCP) 规范 — 工具发现与调用 surface。
4. MCP Registry — 实体解析的 server 身份入口。
5. EDPB — 伪匿名化指引（伪匿名数据仍可能属于 personal data）。
6. AgentMeasure 规范 — Core / Metrics / Data / Entity / Quality / Correlation
   （`standard/`）；Commercial Extension（`extensions/COMMERCIAL.md`，实验性）；
   机器可读 registry（`schemas/`、`registry/`）；参考实现与 conformance vectors
   同仓发布。

---

*规范全文（测量对象、生命周期、指标家族、质量、报告）与参考实现（AgentMeasure）均已开源。AgentMeasure 1.0 毕业标准：2 个独立实现、3 个 runtime profiles、2 个 tool-side 实现、公开 conformance + canonical test vectors、5-10 个真实项目、已发布的 discrepancy report、安全与隐私审查。*
