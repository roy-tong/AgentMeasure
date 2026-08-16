# agent-used Roadmap（M0-M6）

> 顺序原则：**先定义"什么算使用"，再证明跨 Agent 可统一，最后才做公开数据面。**
> 不做聚合云直到 M3（避免在"什么数据值得统计"未定义前建管道）。

| Stage | 目标 | 关键产物 | 状态 |
| --- | --- | --- | --- |
| **M0 Definition** | 讲清"什么算 Agent Usage" | Whitepaper《How to Measure the Agent Tool Economy》+ Measurement Spec + Threat Model | ✅ 完成（spec/ 7 文档 + whitepaper/ 中英） |
| **M1 Cross-Agent Proof** | 证明跨 Agent 可统一 | Codex Adapter（hooks）+ Claude Adapter（OTLP）+ DSH Plugin | 🔵 Codex 已有实现；Claude/DSH 设计完成，实现中 |
| **M2 OTel Native** | 标准采集链 | Collector（normalizer/correlator/redactor/aggregator）+ OTel mapping + MCP adapter | 🔵 Collector 已实现并测试；MCP wrapper 已降级为 legacy adapter |
| **M3 Attribution** | 项目核心 | Identity Graph + Correlation（E2）+ Evidence Grading | 🔵 correlator 已实现（E2）；identity graph 待填 |
| **M4 Public Network** | 公开数据 | API + Dashboard + Badge | ⬜ Badge 已有（本地）；云端待 M3 后 |
| **M5 External Validation** | 指标是否真被需要 | 5-10 个外部 Tool 项目接入 + 《State of Agent Tool Usage》实验报告 | ⬜ |
| **M6 Ecosystem** | 公共基础设施 | MCP / OTel / Agent Platform / Registry 合作 | ⬜ |

## 当前阶段：M1-M2（Cross-Agent Proof + OTel Native）

**本月目标**：
1. 三个 adapter 全部跑通（codex hooks 已实现 → claude OTLP → dsh plugin）
2. 同一 project 在三个宿主的数据并入同一 collector 统计（跨宿主统一 demo）
3. 白皮书 + 标准对外发布（站点中英 ✅、X 线程 ✅，HN/社区讨论进行中）

**M3 前置**：collector 已有 correlator（E2）；identity graph 需要首个真实项目数据驱动设计（M5 外部接入后填充 registry）。

## 明确不做（直到对应阶段）

- ❌ 不替代 OTel（永远）
- ❌ 不按 raw calls 排名（永远）
- ❌ 聚合云（直到 M4，且先回答"什么数据值得统计"）
- ❌ 自动 star/follow（永远，GitHub AUP 红线）
- ❌ 内容采集（永远，隐私架构）

## 里程碑验收

| 里程碑 | 验收 |
| --- | --- |
| M1 完成 | 三个 adapter 各产生统一格式本地事件；codex + dsh 双侧数据可 E2 关联 |
| M2 完成 | collector 全链路（normalizer→redactor→correlator→aggregator）测试绿；OTel span 输入可消费 |
| M3 完成 | identity graph 首个 5 项目解析；E2 关联在真实数据上运行 |
| M4 完成 | 公开 API + badge 对真实项目可用；隐私审计通过 |
| M5 完成 | 5-10 个外部项目接入；公开第一份 discrepancy report（不同观察方式误差） |
| M6 完成 | 任一生态合作（MCP Registry / OTel / 平台）落地 |
