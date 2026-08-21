# AgentMeasure Experiments（Draft 0.4，P3 实证闭环）

> 目的：不是做排行榜，而是**找标准的漏洞**。三类统一实验。

## Experiment A — Choice（验证 M2 家族）

同一任务、同一 Candidate Set（Exa/Tavily/Brave），记录：
presented / selected / choice_mode / model / task_type。
验证：Selection Rate、Conditional Choice Share、不同 Choice Mode 的比较纪律。

## Experiment B — Consumption（验证 M4.1）

Claude 等 consumption 可观察平台：Invoked → Completed → Delivered → Consumed。
验证：**Completed ≠ Consumed**；真实 Consumption Rate 的分母纪律
（consumption-observable eligible invocations）。

## Experiment C — Incrementality（验证 M5，Draft 0.5 前置）

控制 Tool availability：Treatment=可用 / Control=隐藏。
测：task success、time、token、calls、human intervention、quality。
区分 **Tool Incrementality**（Exa vs 替代品仍在）与 **Capability Incrementality**
（整个 search 能力移除）。

## Experiment D — Cross-Harness Compatibility（验证 portable semantics 的必要性）

同一任务链（fail → retry → fallback → success）在 Codex / Claude Code / DSH 中
运行，比较各自如何用不同对象和单位描述同一行为。
设计：[EXPERIMENT-D-cross-harness-compatibility.md](EXPERIMENT-D-cross-harness-compatibility.md)。
产出：Compatibility Report（语义差异披露，不是排名）。

## 输出

每类实验产出 → `reports/`（第一份是 Discrepancy Report #1，不是排行榜）。
