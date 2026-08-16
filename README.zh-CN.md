# AgentMeasure

**面向 Agent Capability Economy 的开放计量基础设施。**

AgentMeasure 定义一套共同语言，衡量 AI Agent 如何发现、选择、使用软件能力，以及从这些能力中获得多少价值。

**今天：** 度量 Agent 对软件能力的使用。
**下一步：** 让 Capability 可以跨 Agent 被统一度量、比较和计量。
**长期：** 成为 Capability as a Service（CaaS）的计量基础。

**Reach → Choice → Use → Utility → Value**

> AgentMeasure **不是**支付协议、市场或通用排名系统。
> 它标准化的是这些系统可以构建于其上的事实与测量语义。

---

## 为什么 Capability 需要新的测量层

软件消费者正在从人变成 Agent，经济单元正在从软件席位转向可调用的能力（callable capabilities）。

```text
Skill / MCP / CLI / SDK
        ↓
描述 / 暴露 / 分发一个 capability

Capability
        ↓
数据 / 算力 / 动作 / 权限 / 交易
        ↓
创造稀缺经济价值
```

**接口可能变得廉价易造；能力依然是稀缺的交付物。**

第一代能力分发已经到来——开放的 Skill、开放的 MCP adapter、开放的 CLI。它们底下的稀缺层才是下一个经济体的基石：专有数据、算力、执行、权限与真实世界的履约。

## 从软件经济到 Capability Economy

```text
人的软件经济
用户 → UI → SaaS → 席位 / 月

             ↓

Agent Capability Economy
Agent → Capability → 执行 → 结果
                       ↓
              使用 / 价值 / 交易
```

如果 Capability 要成为 Agent 可以自动发现、比较、最终自动采购的经济单元，它必须先能被**统一地识别、度量和比较**。这正是 AgentMeasure 提供的。

传统使用指标支撑不了这个经济体——旧链路每一环都在断裂，而最后一环是新的：

```text
安装 ≠ 可用
可用 ≠ 被呈现
被呈现 ≠ 被选择
被选择 ≠ 被使用
被使用 ≠ 有用
有用 ≠ 增量价值
被度量的使用 ≠ 可计费的使用
```

最后一个不等式正是 Operation/Attempt 模型的商业意义：一次 Operation 的 3 次
Attempt ≠ 3 次可计费操作——除非计量策略如此规定。

## Measurement View：Reach → Choice → Use → Utility → Value

AgentMeasure 定义 **Metric Families**，不定义全局北极星。搜索能力、预订 API、计算任务的价值结构各不相同。

| 层 | 回答 | 代表指标 |
| --- | --- | --- |
| **Reach** | 能力有没有进入 Agent 的选择范围？ | Eligible Opportunities · Presentations · Presentation Rate · Distribution Coverage |
| **Choice** | Agent 有机会时会选它吗？ | Observed Selection Rate · Conditional Choice Share |
| **Use** | 选了以后真的用了吗？ | Operations · Attempts · Completion Rate · Success Rate |
| **Utility** | 产生了可用结果或确认的效应吗？ | Result Consumption · Effect Confirmation |
| **Value** | 改善任务结果了吗？ | Incremental Task Success（Draft 0.5） |

五层是**测量视角**。同一批事实也映射到经济视角：

| CaaS 域 | AgentMeasure |
| --- | --- |
| Demand（需求） | Reach + Choice |
| Delivery（交付） | Use + Utility |
| Outcome（结果） | Value |
| Economics（经济） | Metering / Attribution（未来扩展） |

全程保持声称纪律：*observed choice ≠ preference*。选择可能由模型、路由、工作流、
用户、策略或平台作出；**Observed Selection Rate** 只报告观测到的选择，而
**Conditional Choice Share** 是*可比候选条件下观测到的正面竞争选择份额*——可比
意味着声明相同的候选集、类别、Choice Mode 与决策轴（Decision Authority /
Selection Constraint）。

## AgentMeasure 在生产中如何工作

```text
Agent Runtime                     Capability Provider

Claude / Codex
      │
      │ MCP / API
      ▼
                         ┌──────────────────────┐
                         │ 客户自有 Capability  │
                         │                      │
                         │ AgentMeasure SDK     │
                         │ Business Handler     │
                         └──────────┬───────────┘
                                    │
                                observations
                                    │
                                    ▼
                              Collector
                                    │
                                    ▼
                            AgentMeasure Cloud
```

真实开发者最关心的四句话：

> 你的软件**不需要**开源。
>
> MCP **不是必须的**——它只是第一个参考 surface。
>
> 第三方 Agent **不需要**安装 AgentMeasure 也能在 Provider 侧度量使用。
>
> AgentMeasure **不在请求关键路径上**。

## 今天测量什么

- **Decision Opportunity / Candidate Set / Presentation / Selection** —— 选择的四个对象；Observed Selection Rate 的分母是 Presented，不是 Available
- **Software Entity → Capability → Interaction Surface** —— 存在什么、能做什么、怎么交互；观察发生在 surface 层，归属经机器可读 registry 解析到 entity
- **Operation / Attempt** —— 一次逻辑使用 vs 一次执行；**重试 = 同一 Operation 的多个 Attempt，不再是 validity 分类**（作为可靠性信号保留，不当作多次逻辑使用计数）
- **Qualified Usage** —— 按策略排除 test / benchmark / synthetic / replay / duplicate 等无效流量后的生产使用
- **Result Consumption / Effect Confirmation** —— 结果被任务使用，或预期的世界状态改变被确认（Interaction Classes：Information / Action / Transaction / Computation / Communication / …）
- **Measurement Label** —— 每个公开数字的营养成分表（覆盖 / 采样 / 口径 / 方法）

完整模型见 [Core Specification](standard/CORE.md) / [Metrics](standard/METRICS.md) /
[Entity](standard/ENTITY.md) / [Quality](standard/QUALITY.md)。README 不是 spec 摘要。

## 从 Measurement 到 CaaS

```text
Capability
    │
    ▼
Discover → Choose → Use → Deliver Value → Measure → Meter → Price / Pay / Settle
```

AgentMeasure 标准化**前五步**——从发现到测量——产生的数据与语义。计量与商业归因
是未来扩展；支付轨道可以由现有支付基础设施提供。

> **AgentMeasure 标准化经济事实，不移动金钱。**

## AgentMeasure 是 / 不是

| AgentMeasure 是 | AgentMeasure 不是 |
| --- | --- |
| 测量标准 | 支付协议 |
| 使用分析的基础设施 | 市场 / Marketplace |
| 计量语义 | 钱包 |
| 可比较的质量信号 | 通用声誉分 |
| 归因框架 | 唯一真相来源 |

## 给谁用

| 受众 | 为什么 |
| --- | --- |
| **Capability Provider** | 度量并最终计量 Agent 对你能力的使用 |
| **Agent Runtime** | 一致地暴露决策 / 使用信号 |
| **Registry / Marketplace** | 用标准化信号比较能力 |
| **数据 / 测量服务商** | 产出可比较的 Agent 使用分析 |
| **商业 / 支付基础设施** | 在未来 profile 中消费标准化计费事件 |
| **研究者 / 标准贡献者** | 演进方法论 |

## 试用标准

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure
python3 conformance/runners/run_metrics.py   # 指标 vectors（M2.2 / M2.5 / M4.1）
python3 verify_vectors.py                     # receipt / correlation / operation vectors
python3 registry/validate_entities.py         # 校验机器可读 registry
```

## 产品 MVP —— 开发中

第一条产品路径是 **Remote MCP / API Capability Measurement**：AgentMeasure Provider
SDK 在 Provider 侧产出 observations（无需 Agent 侧安装），接入 collector 与托管分析。
SDK 与托管分析尚未实现——标准、参考 collector 与 conformance 套件已就绪。

## 仓库结构

```text
AgentMeasure/
├── standard/          # 规范性标准本体（CORE / METRICS / QUALITY / DATA / ...）
├── extensions/        # 实验性、非规范性 profile（COMMERCIAL.md）
├── whitepaper/        # 方法论论文（中英）
├── conformance/       # 语言无关 test vectors + runners
├── reference/         # 参考实现（collector + adapters）
│   ├── collector/     #   归一、关联、聚合、证据
│   └── adapters/      #   codex / claude / dsh / mcp 观察适配
├── schemas/           # 机器可读 schema（entity registry）
├── registry/          # 机器可读注册表（entities / project identity）
├── experiments/       # 三类实证实验设计
├── reports/           # 公开报告（Discrepancy Report）
├── proposals/         # 指标与规范变更提案（AUP）
└── archive/           # 已废弃的早期文档
```

**标准是本体；代码是参考实现。** 使用标准不意味着向任何中心服务器上传数据。

## 状态与路线图

**Draft 0.4（Measurement Objects & Verification Decoupling）** —— 测量对象实体化、
Operation/Attempt、Core 与 Verification Profile 解耦。

| 能力 | 标准 | 参考实现 | 真实运行 |
| --- | --- | --- | --- |
| Observed Selection Rate | Defined | Implemented | Limited |
| Conditional Choice Share | Defined | Implemented | Experimental |
| Operations / Attempts | Defined | Implemented | Yes |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage | Defined | Implemented | Yes |

路线图双轨运行——标准轨（0.4 对象与质量 → 0.5 效用与经济语义 → 1.0）与产品轨
（Remote Capability Analytics → Provider SDK + 托管分析 → Metering）。见
[ROADMAP.md](ROADMAP.md)。

## 参与

- **讨论测量语义**：GitHub Discussions（Metric Semantics / Measurement Quality / Runtime Profiles / Proposals / Experiments / General）
- **提标准变更**：`proposals/`（AUP：Draft → Discussion → Accepted → Experimental → Stable）
- **报告测量偏差**：`reports/`（Discrepancy Report 模板）
- **修参考实现**：PR 必须通过 `conformance/` 全部 vectors

---

*AgentMeasure 不定义谁是真相来源，而定义什么证据、按照什么规则，可以支持什么结论。*
