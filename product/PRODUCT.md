# AgentMeasure Product

> 三种资产的边界（ROADMAP.md）：**Standard**（最开放）· **Open-source Reference
> Infrastructure**（开源）· **Commercial Network / Product**（商业层不得控制第 1 层）。
> 本目录描述第 3 种资产——产品线。

## 产品线

| 阶段 | 产品 | 状态 |
| --- | --- | --- |
| **MVP** | Remote Capability Analytics（Provider 侧测量 Remote MCP / API 的真实 Agent 使用） | 设计（本目录） |
| Next | Provider SDK + Hosted Analytics | in development |
| Then | Runtime 集成 + Optimize（跨 runtime 信号、效果确认） | 规划 |
| Later | Metering（计费事实输出，对接外部支付 rails） | 规划 |
| Long term | Intelligence / Ecosystem（跨能力比较信号、生态数据面） | 规划 |

## MVP 只回答一个问题

> **我的 capability 被观察到多少次真实 provider-side usage？**

Dashboard 展示：Operations · Attempts · Success · Retry · Latency ·
Caller runtime（declared / unknown）· Measurement Coverage。

**不要** Observed Selection Rate / Share of Choice / Metering（标准先行，产品后行）。

## 产品文档索引

- [ARCHITECTURE.md](ARCHITECTURE.md) — 四层架构与工程原则
- [DEPLOYMENT.md](DEPLOYMENT.md) — self-hosted / hosted 两种部署
- [PROVIDER-SDK.md](PROVIDER-SDK.md) — Provider SDK 契约（含 Caller Identity）
- [HOSTED-ANALYTICS.md](HOSTED-ANALYTICS.md) — 托管分析管道与指标口径
- [MVP.md](MVP.md) — MVP 范围、验收标准与非目标

## 与标准的关系

- 产品消费 Core 的测量事实（Observation Envelope），**不修改标准定义**
- Provider SDK 未实现前，任何产品能力不得自称"AgentMeasure 官方"——文档标注
  in development
- 商业层（托管分析）不得成为标准采用的前置条件
