# AgentMeasure

**度量 AI Agent 软件使用的开放标准（提案）**

> AgentMeasure 是一套开放度量标准，用统一的数据语言衡量 AI Agent 如何发现、选择、
> 使用软件，以及软件最终创造了多少价值。
>
> 传统软件指标衡量人下载和使用了什么；AgentMeasure 衡量 Agent 看到了什么、
> 选择了什么、真正用了什么，以及这些选择有没有创造价值。

[Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [中文白皮书](whitepaper/agent-tool-economy-zh.md) · [Core Specification](standard/CORE.md) · [English](README.md)

## 为什么需要

Agent 正在成为软件的新消费者，但现有信号全部失效——下载量衡量人，不衡量 Agent；
自报安装数可刷；Registry 不提供采纳数据。

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
```

AgentMeasure 回答五个问题：**Reach → Choice → Use → Utility → Value**

1. **Reach** — 我的软件有没有进入 Agent 的选择范围？
2. **Choice** — Agent 有机会时会不会选我？（Observed Selection Rate / Conditional Choice Share）
3. **Use** — 选了以后有没有真正使用？
4. **Utility** — 使用以后有没有产生有效结果？（Result Consumption）
5. **Value** — 如果没有我，Agent 的结果会不会更差？（Incrementality）

## 五层 Measurement Framework

| 层 | 回答 | 代表指标 |
| --- | --- | --- |
| Reach | 进入 Agent 世界了吗 | Presented Opportunities、Active Clients |
| Choice | 有机会时会选我吗 | Observed Selection Rate、Conditional Choice Share |
| Use | 选了以后好用吗 | Logical Invocations、Completion Rate、Success Rate |
| Utility | 结果被用了吗 | Result Consumed Rate |
| Value | 创造价值了吗 | Incremental Task Success（Draft 0.5） |

## Core concepts

- **Decision Opportunity / Candidate Set / Presentation / Selection** —— 选择行为的
  四个对象；Observed Selection Rate 的分母是被呈现（Presented），不是可用（Available）
- **Observed Selection Rate** = Observed Selected ÷ Presented —— Agent 真正有机会时选你的概率
  （observed ≠ preference：required/forced 的"选择"不是偏好，按轴披露）
- **Conditional Choice Share** —— A、B 同台竞争时的选择份额（Agent Preference）
- **Qualified Usage** —— 排除 benchmark / test / synthetic / retry 后的真实生产使用
- **Result Consumption** —— 结果被后续任务实际使用（≠ 成功返回）
- **Incrementality** —— 没有这个工具，任务结果会不会更差
- **Measurement Label** —— 每个公开数字的营养成分表（覆盖/采样/口径/方法）

## Who is this for?

| 用户 | 入口 |
| --- | --- |
| Tool / MCP 开发者 | [Quickstart](#quickstart) · [Runtime Profiles](standard/PROFILES.md) |
| Agent Runtime 平台 | [Runtime Profile](standard/PROFILES.md) · Observability |
| 数据研究者 | [Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [Metrics](standard/METRICS.md) |
| 标准贡献者 | [Core](standard/CORE.md) · [Proposals](proposals/) |
| 第三方实现者 | [Conformance](conformance/) |

## Repository map

```text
AgentMeasure/
├── standard/          # 标准本体（CORE / METRICS / QUALITY / DATA / ...）
├── whitepaper/        # 方法论论文（中英）
├── conformance/       # 语言无关 test vectors + runners
├── reference/         # 参考实现（collector + adapters）
│   ├── collector/     #   归一、关联、聚合、证据
│   └── adapters/      #   codex / claude / dsh / mcp 观察适配
├── experiments/       # 三类实证实验设计
├── reports/           # Discrepancy Report 等公开报告
├── proposals/         # 指标与规范变更提案（AUP）
└── archive/           # 已废弃的早期文档
```

**标准是本体，代码是参考实现。** 使用标准不意味着向任何中心服务器上传数据。

## Quickstart

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure
python3 conformance/runners/run_metrics.py   # 运行指标 vectors（16/16）
```

喂入 Decision Opportunity 事件后，参考实现输出示例：

```text
AgentMeasure Demo

Reach
Presented Opportunities    150

Choice
Selections                   65
Observed Selection Rate   43.3%

Use
Invocations                  62
Completion Rate           96.8%

Utility
Observable Results           41
Consumed Results             28
Consumption Rate          68.3%

Measurement Quality
Usage Context        production
Coverage             partial
Sampling             none
```

数据默认留在本地；公开指标必须携带 [Measurement Label](standard/QUALITY.md)。

## Current status

**Draft 0.4（Measurement Objects & Verification Decoupling）** — 测量对象实体化
（Software Entity → Capability → Interaction Surface）、Core 与验证解耦。

| Capability | Standard | Reference | Real Runtime |
| --- | --- | --- | --- |
| Observed Selection Rate | Defined | Implemented | Limited |
| Conditional Choice Share | Defined | Implemented | Experimental |
| Logical Invocations | Defined | Implemented | Yes |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage | Defined | Implemented | Yes |

标准已定义 ≠ 现在已经能全面测。按能力逐项验证中。

版本路线：Draft 0.3（语义）→ **0.4（对象与质量）** → 0.5（价值测量）→ 1.0
（毕业标准：2 个独立实现 + 3 个 runtime profiles + 公开 conformance + 5-10 个真实项目）。

## How to contribute

- **讨论测量语义**：GitHub Discussions（Metric Semantics / Measurement Quality / Runtime Profiles / Proposals / Experiments / General）
- **提标准变更**：`proposals/`（AUP 流程：Draft → Discussion → Accepted → Experimental → Stable）
- **报告测量偏差**：reports/（Discrepancy Report 模板）
- **修参考实现**：PR 必须通过 `conformance/` 全部 vectors

---

*AgentMeasure 不定义谁是真相来源，而定义什么证据、按照什么规则，可以支持什么结论。*
