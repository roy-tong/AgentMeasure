# Experiment D — Cross-Harness Measurement Compatibility（跨 Harness 测量兼容性）

> Draft 0.4 实验族新增一类。目的：不是排名，而是证明/证伪一个核心命题——
> **同一行为，在不同 Harness 中会被不同对象和单位描述**。若成立，这是
> portable measurement semantics 必要性的最直接证据。

## 动机

Harness Profiles（profiles/codex.md、deepseek-harness.md、claude-code.md）
在纸面上已经显示出词汇差异。本实验用同一条脚本化任务链在三个 harness 中真实
运行，把差异变成可引用的数据表。

## 设计

### 统一任务脚本（one intent → fail → retry → fallback → success）

1. 一个明确用户意图（如"查 X 并给我带引用的摘要"）；
2. 首选 capability 被配置为**确定性失败**（mock provider 返回 timeout）；
3. 观察 harness 是否 retry；再次失败后 fallback 到备选 capability；
4. 备选成功，任务完成。

同一 fixture、同一 mock 矩阵、同一 policy 跑三遍，分别采集原生遥测。

### 被测系统（第一版）

```text
Codex CLI          （hook + App Server 事件流）
Claude Code        （OTLP telemetry）
DeepSeek Harness   （session event log）
```

### 采集问题（每个 harness 回答同一张表）

| 维度 | 问题 |
|---|---|
| Runs | 这个概念在本系统叫什么？边界如何切？ |
| Operations | 逻辑使用意图如何表达？还是不存在？ |
| Attempts | 真实执行如何表达？几次？ |
| Retry | retry 有原生标记吗？还是靠推断？推断规则是什么？ |
| Fallback | 换 provider 是新 attempt、新 operation，还是不可见？ |
| Cost | tokens / 花费挂在哪一层？能否归到 attempt？ |
| Outcome | 成败判定在哪一层？谁判定？ |
| Consumption | 结果被后续使用，可见吗？ |
| Delegation | （若启用 subagent）委托边界可见吗？ |

### 输出

`reports/compatibility-report-001.md`：一张主表（同行为 × 三系统的对象/单位
映射）+ 每系统一段不可观察清单 + 对 AgentMeasure 映射规则的修订清单。

预期形如：

| System | Calls | Runs | Operations | Attempts | Retry 标记 | Cost 粒度 | Outcome 判定 |
|---|---:|---:|---:|---:|---|---|---|
| Codex | ? | ? | ? | ? | 无（需推断） | ? | ? |
| Claude Code | ? | ? | ? | ? | 无（需推断） | attempt | 内置 |
| DSH | ? | ? | ? | ? | 无（需推断） | step | 配对推导 |

**任何一格为空或语义不一致，都是标准的证据，不是实验的失败。**

## 纪律

- 不做系统间"谁更好"的排名；只做语义兼容性差异披露（与 Benchmark Run #001
  同样的 no-composite-scores 纪律）。
- 所有推断（retry、fallback 判定）必须标 `inferred` 并写明规则。
- Mock provider 的失败注入方式在报告中完整披露（可复现）。
- 本仓库自身 fixture 仍不参与任何生态排名。

## 与提案的关系

- 结果 feeding proposals/2026-08-21-delegation-graph.md（Delegation 语义的
  现实必要性）与 profiles/ 三份 harness profile（观察矩阵的实证修正）。
