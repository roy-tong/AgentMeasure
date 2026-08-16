# AgentMeasure Roadmap

> 顺序原则：**先统一尺子（语义），再统一如何证明尺子可信（质量），最后才谈价值与生态。**
> 每一版本都要求垂直闭环：概念 → spec → schema → 指标合同 → 参考实现 → conformance vectors → 声称。

## 版本路线

| 版本 | 目标 | 关键产物 | 状态 |
| --- | --- | --- | --- |
| **Draft 0.3 — Metric Semantics** | 每个指标都能被独立实现且算出同一个数字 | Decision Opportunity、Measurement Grain、Observability 4-states、Strict Qualified、Reach→Value 五层框架 | ✅ 已发布 |
| **Draft 0.4 — Entity & Quality** | 测量对象可标识、读数可信度可验证 | Software Entity→Capability→Interaction Surface、Interaction Classes、Core/Verification 解耦、Measurement Quality、机器可读 registry | 🔵 当前 |
| **Draft 0.5 — Utility & Value** | 从"被使用"走向"产出价值" | Result/Effect 双元 Utility、Value 家族（M5） | ⬜ |
| **Draft 0.6 — External Validation** | 指标在真实环境稳定 | 5-10 个外部项目接入、第一份《Measurement Discrepancy Report》、实验报告 | ⬜ |
| **Draft 0.7 — Interoperability** | 跨实现可互操作 | 独立实现（Go/Rust/TS）、OTel/MCP 生态对齐、Measurement Profiles | ⬜ |
| **1.0 — Candidate Standard** | 毕业 | 2 独立实现 + 3 profiles + conformance + 5-10 项目 + 双 review | ⬜ |

## 当前阶段：Draft 0.4（Entity & Quality）

**本月目标**：
1. 领域模型落地：Software Entity → Capability → Interaction Surface；Interaction Classes（Information/Action/Transaction…）
2. Core 与 Verification Profile 解耦——验证是高级符合性，不是采用前置条件
3. 机器可读 registry（`schemas/` + `registry/*.yaml`）+ BCP14 规范语言
4. 指标合同补全 vectors（M2.1 / M2.3 / M2.4 / M3.x）

## 明确不做（直到对应阶段）

- ❌ 不替代 OTel（永远）
- ❌ 不按 raw calls 排名（永远）
- ❌ 聚合云（直到 0.6，且先回答"什么数据值得统计"）
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
