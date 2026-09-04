# AgentMeasure Roadmap

> **Positioning（2026-09-04）**：公开叙事统一为"开放公尺"——usage 与 outcome 同一套语义（官网 Why now / Principles 两节与 README 已同步）。按效果计费的场景（per-resolution 计费的 AI 客服生态）是标准落地的第一个目标场景；当前唯一产品验收是采用指标：生产接入家数、月度被计量交互量、opt-in 数据回流率、被外部项目合并的规则数。原则红线：免费清单写进治理；原始数据本地默认；不卖排名、不碰资金。

> **Timebox（2026-08-21 → 09-04）**：standard 轨暂停非 blocking 变更（AUP 一律排队，除非阻塞接入）；关键路径是双假设实验与 **9/3 Gate Review**（判据预注册见 PRD v0.5 §8.2）。Audit 以 concierge 形态受试：[product/AUDIT.md](product/AUDIT.md)。

> **Status（2026-08-25）**：v0.2.2 已发布（conformance hardening：#8/#9 修复 + 首个外部 fixture Urusilla-001 入库）。
> **双假设实验 Day 1 完成**：假设 A（Measurement Conformance——已有真实 pull：外部 fixture、M3 执行粒度向量、4 条上游语义探针、OpenLIT PR 在审）与假设 B（Usage Integrity Audit——入口已修复：mailto 双路径 CTA；concierge #1 fallback 已完成并公开）并行受试，9/3 按预注册判据四分支裁决。
> 信任债全部清偿：conformance 复现 bundle ✅、SDK tarball 上 release ✅、**live A/B 诚实出处 bundle ✅（stats-recomputable，`bundles/live-codex-desc-clarity-001/`）**。
> 开放讨论：#11 消费语义（两状态重构已入 DR-005，M4.1 rename 待决）。欢迎在任何环节提出异议。

> 顺序原则（标准轨）：**先统一尺子（语义），再统一如何证明尺子可信（质量），最后才谈价值与生态。**
> 顺序原则（产品轨）：**产品验证不能等标准毕业**——concierge audit 现在就可以验证
> "有没有 Provider 真愿意接"，但商业产品不得控制标准定义。

## 双轨路线

| 阶段 | Standard Track | Product Track |
| --- | --- | --- |
| **Now** | Draft 0.4.4（Evidence Preservation & Resolution Semantics + DR-005 两状态消费语义 + DR-006 三粒度）+ **conformance 向量集扩张**（Urusilla-001 外部 fixture、M3 执行粒度 ×3、首个公开 Evidence Case langfuse-demo-traces）；CI 六套件全绿（含外部 fixture 守卫与 bundle 复算） | **双假设实验（→ 9/3 Gate）**：假设 A=conformance 协作（人际线+探针线）；假设 B=concierge audit ×2–3（入口已修复：mailto 双路径+暖池直达）；**Gate 后才进入产品化**（Audit CLI 或 conformance toolkit，按预注册判据裁决）。Lab v0.4 已落地（真实 harness 适配器 live-validated、78 tests） |
| **Next** | Draft 0.5 — Utility & Economic Semantics（Result/Effect 双元 Utility、Interaction Classes 指标化） | 按 gate 分支：Audit 产品化（CLI+真实 adapter）或 conformance toolkit 为 wedge（与 Lab 开源发布 M2 合流）；Provider SDK + Hosted Analytics |
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
2. Core 与 Verification Profile 解耦；BCP14 规范语言；**DR-005 两状态消费语义 + DR-006 三粒度已入库**
3. 机器可读 registry（schemas/ + registry/）+ CI 校验
4. ~~待办：M3.x conformance vectors 发布~~ ✅ **已发布**（metric-execution-grain ×3）；待办：Interaction Classes 指标化（0.5 前置）、#11 M4.1 rename AUP

**Product — 双假设实验（→ 9/3 Gate）**：
1. Provider SDK（provider 侧观测，无 Agent 侧安装）——v0.1.1 已发布（21/21 测试，release tarball 可装）；npm publish 待凭据
2. 假设 B 入口已修复：官网 Trial 双路径（mailto 主＋issue 次）＋暖池直达；concierge #1（fallback：langfuse demo 公开 artifact）已完成并公开
3. 验证目标（预注册判据，PRD v0.5 §8.2）：真实 production telemetry ≥2＋强反应（"再测一组"/"怎么接进 CI"级）≥2 人（假设 B）；外部 PR/mapping ≥2＋主动 fixture ≥2（假设 A）

**Substrate — AgentMeasure Lab（开源实验引擎，[lab/](lab/README.md)）**：
1. v0.4 已落地：预注册锁定 + 规模/功效/预算预估、均衡分配、种子确定性、预算熔断、漏斗采集、诚实统计（效应量+CI+guardrail+null+下轮加样指引）、假增长决策出口拦截（`unverified_growth`）、支配关系标注、双语决策人一页版、价值公式、离线报告、CLI 错误友好化；**真实 Harness 适配器**（claude-code 完整 / codex 实验性：候选集注入=本地 MCP 工具服务器 + headless CLI + transcript 解析；脚本化 transcript 集成测试全绿）；校准分析（生产复测/分条件迁移/not_comparable/再加权）；Connector 数据面（授权三档/撤回/签名导出）；只读 MCP 接口；`am lab history` 本地假设库；local-analytics 基线漏斗（BASE0-002）；74 tests + selftest；**codex 适配器 live-validated（v0.2.1）**
2. 待办：claude-code live 轮（gate 后）→ 开源发布 M2 → 外部自助实验 ≥10 例（开源采用 Gate）；真实生产事件接入（前置 G0 数据权）；hosted 历史/持续监控（商业层，Next）
3. **发布纪律（新增）**：live run 后、tag 前，把四件套导出到 `bundles/<experiment-id>/`（见 lab/README.md 清单）；release.yml 自动把 bundles 挂为 release asset

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
