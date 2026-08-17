# Pipeline Validation #001 — SDK → Canonical → Collector → Metrics（Draft 0.4.3）

> **状态：本地合成流量验证（非真实外部 Provider）。** 本报告验证 Provider SDK
> 的端到端管道在 canonical boundary 下成立：`Provider SDK → Canonical
> Observation JSONL → 校验 → Collector → Metrics`，以及 0.4.3 的 fail-closed
> 语义如何在真实管道中生效。
>
> **Measurement Report #001 的编号预留给第一个外部 Provider**（[Issue #2](https://github.com/roy-tong/AgentMeasure/issues/2)）。
> 本报告只验证管道，不产生任何"使用量"结论——合成流量不证明任何真实使用。

## 设置

- 被测面：`acme-weather`（MCP SDK 注册路径，42 次调用，3 类 caller）
- 接入：`@agentmeasure/mcp` v0.1.1 中间件（注册时包装 handler，参数/结果零接触）
- 流量：42 次合成调用（claude ×14 / codex ×14 / unknown ×14），~12% 上游失败
- 语义：`usage_context=synthetic`（源头标注，绝不计入 production）
- 采集：内存队列 → 批量落盘 → Canonical JSONL → reference collector（唯一 canonical 输入）
- 窗口：单次运行；demo 使用隔离 workspace（`mktemp -d`），不触碰 `~/.agentmeasure`
- 可复现：`./examples/demo-e2e.sh` —— 相同 fixture + 相同 policy = 相同结果（42 calls → 84 observations）

## 结果（2026-08-17 单次运行示例）

```text
Canonical observations accepted : 84   rejected: 0
  reject reasons               : none

Observed attempts               : 42
Strict Qualified attempts      : 0 (0.0%)
  qualification status         : {'unknown': 42}

Success / Failure              : success-rate 88.1%  unknown/inconsistent 0
Latency (duration_ms)          : n=42 mean=173.1ms p50=176ms p95=306ms min=29ms max=321ms

Operation resolution           : resolved 0 / 42 attempts (coverage 0.0%)
  resolution                   : {'unknown': 42}
  legacy_attempt_equivalent    : 42 (0.3 迁移期)

Caller attribution             : claude:14 codex:14 unknown:14 (strength: declared=28 / unknown=14)
```

> 延迟数字随每次运行的随机延迟（20–320ms）变化；计数与分布是确定性的。

## 验证点（对 0.4.3 语义的验证）

1. **0 rejection**：SDK 输出的 84 条观察全部通过 Canonical Schema 校验
   （`schemas/observation.schema.json` + per-type payload）——"唯一 Canonical 输入"
   在真实管道中成立。
2. **42 calls → 84 observations**：attempt_started + attempt_completed 各 42 条，
   call id 一一配对。**没有 result_consumed**——Provider 侧 MCP server 无法观测
   Agent 是否消费了结果；UNOBSERVABLE 不伪造成 TRUE。
3. **Caller 逐请求解析**：initialize 捕获 clientInfo → session 映射；每次请求按
   `_meta.sessionId` 回显解析 CallerClaim。claude/codex 自称 agent → `declared`；
   curl（无 agent 声称）→ `unknown`。服务端没有配置级 caller 冒充。
4. **Strict Qualified = 0% 是正确的，不是缺陷**：流量源头标注 `synthetic`，
   任何合成流量都不得伪装成 production。
5. **Operation Resolution Coverage = 0% 是正确的，不是缺陷**：Provider-only
   拓扑没有 operation 证据（无 runtime 传播的 operation_id），fail-closed 输出
   0 operations / 42 attempts。
6. **Success 88.1%**：中间件通过异常 + MCP `isError` 元数据判定 outcome
   （不读取内容）；模拟的 ~12% 失败被如实捕获。
7. **Latency 可披露**：attempt_completed 携带非敏感 `duration_ms`（p50/p95），
   不暴露请求内容。

## 下一步（Product Gate A）

- [x] P0-1 Canonical 端到端（Adapter → SDK → Collector → Metrics）
- [x] P0-2 Provider SDK（@agentmeasure/mcp v0.1.1：async queue + spool、per-request caller、MCP v1/v2）
- [x] P0-3 Local Analytics（--days / latency histogram / caller attribution）
- [ ] P0-4 第一个**真实外部** MCP server 接入 → 发布真正的 **Measurement Report #001**
- [ ] Hosted ingestion（P1）
- [ ] 3–5 Provider Alpha（P1）
- [ ] 数据驱动的真实 Actionability 案例（P1）
