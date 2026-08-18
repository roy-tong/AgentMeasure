# AgentMeasure Roadmap

> **Status（2026-08-18）**：v0.1.1 已发布（Standard Draft 0.4.4 — Evidence Preservation & Resolution Semantics + @agentmeasure/mcp SDK），
> 正在推进 **Product Gate A**（第一个真实外部 Provider + 第一份 Measurement Report 的实数据版）。
> 开放讨论：#1 Strict Qualified Usage 默认值 · #3 首个 benchmark 设计。欢迎在任何环节提出异议。

> 顺序原则（标准轨）：**先统一尺子（语义），再统一如何证明尺子可信（质量），最后才谈价值与生态。**
> 顺序原则（产品轨）：**产品验证不能等标准毕业**——最小 hosted analytics 现在就可以验证
> "有没有 Provider 真愿意接"，但商业产品不得控制标准定义。

## 双轨路线

| 阶段 | Standard Track | Product Track |
| --- | --- | --- |
| **Now** | Draft 0.4.4 — Evidence Preservation & Resolution Semantics（Attempt 不可变账本、Operation 派生语义、resolution status×method、inferred share、DR-001~004） | **Product Gate A — First Real Measurement**：Provider SDK（@agentmeasure/mcp）+ Local Analytics + 第一个真实外部 Provider + 第一份 Measurement Report；**完成后才进入 Draft 0.5** |
| **Next** | Draft 0.5 — Utility & Economic Semantics（Result/Effect 双元 Utility、Interaction Classes 指标化） | Provider SDK + Hosted Analytics（SDK 产出 observations，托管 collector/分析） |
| **Then** | Draft 0.6 — External Validation（5-10 外部项目、第一份《Measurement Discrepancy Report》） | Runtime 集成 + Optimize（跨 runtime 信号、效果确认） |
| **Later** | Commercial Measurement Profile（COMMERCIAL 转正：Billable Event/Unit/Metering Policy） | Metering（计费事实输出，对接外部支付 rails） |
| **Long term** | **AgentMeasure Core 1.0 独立毕业**（2 独立实现 + 3 profiles + conformance + 5-10 项目 + 双 review；**不依赖任何商业化**）＋ Commercial Measurement Profile 0.x 独立毕业 | Intelligence / Ecosystem（跨能力比较信号、生态数据面） |

## 三种资产（从第一天分开）

| 资产 | 内容 | 开放度 |
| --- | --- | --- |
| **1. Standard** | Objects、Metrics、Measurement Quality、Metering Semantics（CORE/METRICS/QUALITY/…） | 最开放 |
| **2. Open-source Reference Infrastructure** | SDK、Collector、Runtime Adapters、Conformance | 开源 |
| **3. Commercial Network / Product** | Analytics、Optimize、Meter、Intelligence | 商业层不得控制第 1 层 |

## 当前阶段（双轨并行）

**Standard — Draft 0.4（Objects & Quality）**：
1. 领域模型已落地（Entity→Capability→Surface、Operation/Attempt、三轴、lineage）
2. Core 与 Verification Profile 解耦；BCP14 规范语言
3. 机器可读 registry（schemas/ + registry/）+ CI 校验
4. 待办：M3.x conformance vectors 发布；Interaction Classes 指标化（0.5 前置）

**Product — Remote Capability Analytics（MVP）**：
1. AgentMeasure Provider SDK（provider 侧观测，无 Agent 侧安装）——**未实现**
2. 托管 Collector + 分析（远程 MCP / API 能力的使用面板）——**未实现**
3. 验证目标：≥1 个真实 Provider 愿意接入并产出第一份 provider-scoped 报告

## 明确不做（直到对应阶段）

- ❌ 不替代 OTel（永远）
- ❌ 不按 raw calls 排名（永远）
- ❌ 不实现支付 rails / 钱包 / 结算（永远，见 extensions/COMMERCIAL.md）
- ❌ 聚合云只服务于标准毕业指标（0.6）；hosted analytics 服务于产品验证（Now）
- ❌ 自动 star/follow（永远）
- ❌ 内容采集（永远，隐私架构）

## 每个版本的验收（垂直闭环）

| 层 | 验收 |
| --- | --- |
| 概念 | 反例驱动：每个定义配一个"不成立"的例子 |
| Spec | BCP14 语言；章节之间无循环引用 |
| Schema | 机器可读；与 spec 术语一一对应 |
| 指标合同 | 公式、grain、eligibility、counterexample 齐全 |
| 参考实现 | 与指标合同一致；测试绿 |
| Conformance | 每个指标至少 3 个 vectors（正常 / 边界 / fail-closed） |
| 声称 | 只宣称有 vectors 支撑的部分 |
| 产品 | MVP 只承诺已实现的能力；SDK/Analytics 标注 in development |
