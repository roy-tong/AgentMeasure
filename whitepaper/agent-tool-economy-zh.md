# 如何度量 AI Agent 对软件的使用

**AgentMeasure — 度量 AI Agent 对软件使用的开放标准提案（Draft 0.3）**

> 作者：Roy Tong（仝夏瑞）
> 参考实现：AgentMeasure 仓库（GitHub）。

## 摘要

Agent 正在成为软件的新消费者，但行业没有统一的方法衡量 Agent 如何发现、选择、使用和依赖软件。下载量、star、自报安装数——既不测量 Agent，也不测量价值。本文定义 AgentMeasure：一套 Agent 软件生态的度量标准——什么算机会、什么算选择、什么算调用、什么算消费、什么算贡献；这些如何计数、如何比较、如何限定；每一级证据能支持什么结论。目标不是仪表盘，而是 Tool 开发者、Agent 平台、模型公司、Registry、投资者和第三方研究机构之间的**共同数据语言**。

## 一、为什么 Agent 使用需要新的度量模型

软件分发曾有一条可读的链路：下载、安装、使用。Agent 经济打破了每一个环节：

```text
安装 ≠ 可用
可用 ≠ 被呈现
被呈现 ≠ 被选择
被选择 ≠ 被使用
被使用 ≠ 有用
有用 ≠ 增量价值
```

- *安装*与*可用*描述工具的存在，不描述 Agent 的行为。
- *被呈现*——进入 Agent 的决策上下文——是选择行为的真正分母，而今天几乎不可观测。
- *被选择*是决策；*被调用*是执行；*完成*是结果。
- *被消费*意味着结果进入了任务；*有用*意味着它产生了作用。
- *增量价值*是反事实：没有这个工具，结果会不会更差？

广告行业用了几十年学会：曝光不是转化，点击不是价值，归因不是增量。Agent 软件生态可以从第一天就采用这门纪律。AgentMeasure 回答五个问题：

> **Reach（触达）**——我的 Tool 有没有进入 Agent 的选择范围？
> **Choice（选择）**——Agent 有机会时，会不会选我？
> **Use（使用）**——选了以后，有没有真正使用？
> **Utility（效用）**——使用以后，有没有产生有效结果？
> **Value（价值）**——没有我，Agent 的结果会不会更差？

## 二、测量对象

**Observation（观察）是证据单位，不是业务测量单位。** AgentMeasure 先定义业务单位：

| 对象 | 定义 | 层 |
| --- | --- | --- |
| Opportunity | Agent 的决策上下文里有这个 Tool | Behavior |
| Invocation | Tool 实际执行了调用 | Behavior |
| Task | Invocation 所服务的任务单位 | Behavior |
| Client | 独立 Agent runtime / installation | Market |
| Project | package/MCP/skill 归属的软件项目 | Market |
| Category | 可比较的能力类别（搜索、编码…） | Market |
| Observation | 对上述行为的证据性观察（签名收据） | **Evidence** |

把 observation 当成 usage 计数，会双计每一次被佐证的调用；把 invocation 当成价值，会混淆行为与效用。层级不可互换。

## 三、Agent Tool 交互生命周期

每个阶段必须明确：分子、分母、可观测还是推断、最低证据。

| 阶段 | 定义 | 可观测 | 最低证据 |
| --- | --- | --- | --- |
| Presented | Tool 进入 Agent 决策上下文（候选集） | Agent runtime（routing 层） | runtime 级观察 |
| Selected | Agent/runtime 决定调用 | Agent runtime | runtime 级观察 |
| Invoked | 开始执行 | 双侧 | 任意侧观察 |
| Completed | 返回 success/failure/denied | 双侧 | 任意侧观察 |
| Consumed | 后续模型请求使用了结果 | 部分平台 | 平台信号 |
| Contributed | 结果影响任务结果 | — | **推断** |

**Discovered 被 Presented 取代**：`tools/list`、registry 检索、skill 搜索只说明工具存在；Presented 说明工具真正进入了 Agent 的决策上下文——就像"租了广告牌"不等于"广告被展示"。三个商业意义不同的状态：

```text
可用 ✓ 被呈现 ✓ 被选择 ✓   ← 被选中
可用 ✓ 被呈现 ✓ 被选择 ✗   ← 错过的机会（Selection Rate 的分母）
可用 ✓ 被呈现 ✗            ← 根本没上场（分发缺口）
```

## 四、测量框架：五大指标家族

**AgentMeasure 定义 Metric Families，不定义全局北极星。** 搜索工具、支付工具、企业 SaaS 工具的价值结构不同，一个 KPI 无法通用。

**M1 Distribution（分发）— Reach。** 我的 Tool 进入 Agent 的世界了吗？
`可用 Clients · 被呈现机会数 · Presentation Rate · Agent Host 覆盖 · 模型覆盖`

**M2 Choice（选择）— 最 Agent-native。** Agent 有机会时会不会选我？
`选择数 · Selection Rate（Selected÷Presented）· Share of Choice · 首选率 · 替代率 · 切换率`

**M3 Execution（执行）— Use。** 选了以后好不好用？
`逻辑调用数 · 完成率 · 成功率 · 错误/重试率 · 延迟 · 成本`

**M4 Utility（效用）— 有效使用。** 返回的东西 Agent 到底用没用？
`结果送达率 · 结果消费率 · 继续使用率 · 纠错率 · 回退率`

**M5 Outcome（价值）— Value。** 最终是否改善任务？
`任务成功关联 · 贡献 · 增量提升 · 节省时间 · 节省成本 · 减少人工干预`

### Selection Rate（选择率）

\[
Selection\ Rate = \frac{Selected}{Presented}
\]

Tool A：呈现 100,000、选择 5,000 → 5%。Tool B：呈现 10,000、选择 4,000 → 40%。绝对调用量偏向 A，但 Agent 明显更偏好 B。这才是开发者真正关心的数据。

### Share of Agent Choice（Agent 选择份额）

在一个能力类别（如网页搜索）下，若干可替代工具：

\[
SoC = \frac{该工具的选择数}{类别内全部选择数}
\]

开发者看到的将不只是 "1.2M calls"，而是：

```text
Search 类别
Exa       呈现份额 31% · 选择份额 44% · 选择率 58% · 重复选择 71%
```

这是 Agent 软件的市场数据，不是遥测。

## 五、关系测量（Relationship Measurement）

跨时间关系，用 Agent-native 行为定义：

| 关系 | 定义 |
| --- | --- |
| Trial | 首次使用 |
| Active | 周期内有 eligible usage |
| Repeated | 跨多个窗口重复使用 |
| Preferred | 同等候选集中持续首选 |
| Dependent | 移除工具后任务表现显著下降 |

**Dependency 是长期资产指标**：最有价值的工具不是调用最多的，而是最不可替代的。`Adoption → Preference → Utility → Dependency` 是一条 Agent-native 的工具关系模型。

## 六、归因 ≠ 增量（Attribution vs Incrementality）

**工具参与了成功任务，不等于它导致了成功。**

- **归因测量**（observational）：哪些工具参与了任务链——只能支持"关联"与"参与执行链"的结论。
- **增量测量**（counterfactual）：工具的存在创造了多少额外价值——随机对照（Treatment=可用 / Control=不可见），比较任务成功、时间、token 成本、总调用数、人工干预、质量：

```text
增量任务成功 = P(成功|有工具) − P(成功|无工具)
时间提升 = 对照组时间 − 工具组时间
成本提升 = 对照组成本 − 工具组成本
```

广告行业从 last-click 归因走向 holdout 分组与增量测试，正是这个原因。Agent 工具第一天就应分离这两个测量体制。

## 七、测量质量（Measurement Quality）

**证据质量不是覆盖质量，两者都不是限定质量，也都不是方法论。** 一组 100% 真实但只覆盖 2% Agent 的事件，不是市场数据。

```text
Measurement Quality
├── Evidence        事件真实吗？（签名、佐证）
├── Coverage        我们看到了多少世界？
├── Qualification   这算不算真实生产使用？
├── Sampling        采样了吗？不确定性多少？
├── Identity        标识归一得怎么样？
└── Method/version  用什么统计、哪个规范版本？
```

### Qualified Agent Usage（限定使用）

**Raw Invocation ≠ Qualified Usage。** 未来大量工具流量不代表采用：开发者自测、CI、benchmark、eval、synthetic agent、health check、重试风暴、agent loop、replay、压测、demo。AgentMeasure 要求每条观察携带 **Usage Context**：

```text
production · development · test · benchmark · evaluation · synthetic · ci · unknown
```

公开采用指标默认为 `production` + 单独披露的 `unknown`；benchmark/eval/test/CI/synthetic **绝不混入 qualified usage**。在决定排行榜是否可信上，上下文限定可能比证据分级更直接。

## 八、标准报告（Standard Reporting）

### Measurement Label（测量标签——数字的营养成分表）

每个公开指标必须携带：

```text
Agent Usage Measurement Label
Standard version:   0.2
Window:             30 days
Usage context:      production
Agent hosts:        Claude Code, Codex
Coverage:           partial
Collection:         client + server
Corroborated:       68%
Sampling:           none
Unknown context:    12%
Synthetic excluded: yes
Identity coverage:  91%
```

标签不给数据打分；它披露数字是怎么来的，让使用者自行判断适用性。

### Measurement Profiles（测量画像）

| Profile | North Star | Guardrails | Diagnostics |
| --- | --- | --- | --- |
| Adoption | Active Clients | Qualified Usage Rate, Coverage | Presented, Selection Rate, Repeat |
| Reliability | 成功完成调用数 | p95 延迟, 成本, 重试 | 错误类型, host, 版本 |
| Utility | Consumed Results | 纠错率, 回退率 | 完成→消费转化 |
| Value | 增量任务成功 | 成本, 延迟, 安全 | 任务类型, 模型, 替代工具 |

## 九、互操作（Interoperability）

标准是 transport-neutral、vendor-neutral 的。现有基础设施作为实现例子而非前提：MCP 承载生命周期事件与 trace context；OpenTelemetry 承载工具 span；Codex/Claude Code/DeepSeek Harness 暴露带能力声明的观察点。技术选择（签名算法、采集格式、存储）属于参考实现与 profiles——方法论不会因技术换代而过时。

## 十、开放问题

1. **任务边界**：什么算一个"任务"，由谁定义？
2. **贡献**：如何测量消费之外的结果贡献？
3. **增量**：如何在生态规模上运行反事实实验而不干扰生产？
4. **候选集可观测性**：Presented 是关键分母，但多数 runtime 尚未暴露 routing 层信号。
5. **隐私**：伪匿名下关联与留存能走多远？
6. **跨 Agent 身份**：同一 client 跨 Codex/Claude/DSH——何时可知？

---

*规范全文（测量对象、生命周期、指标家族、质量、报告）与参考实现（AgentMeasure）均已开源。AgentMeasure 1.0 毕业标准：2 个独立实现、3 个 runtime profiles、2 个 tool-side 实现、公开 conformance + canonical test vectors、5-10 个真实项目、已发布的 discrepancy report、安全与隐私审查。*
