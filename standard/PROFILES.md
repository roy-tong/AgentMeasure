# AgentMeasure-PROFILE — Agent Runtime Profiles（Draft 0.4.1）

> Profile 声明"这个 runtime 能可靠观察到什么"——能力矩阵是测量可信度的基础。
> 完整矩阵见 docs/adapters.md；本文是协议侧摘要。
>
> 词汇：Selection / Operation / Attempt / Completion / Consumption /
> Evidence Profile（corroborated）。观察 = Observation；签名 = Verified Profile 的可选能力。

## P1. Codex Profile（hook 观察）

- 可靠：tool_name、tool_use_id、session（伪匿名后）、model、turn_id
- 不可靠（官方 PostToolUse schema 无）：trace_id、精确时间戳、成败判定
- Observation：`observer_side=client, provenance=hook, outcome=unknown（默认）`
- 关联能力：Exact（tool_use_id）；无 trace → Structural/Commitment 依赖工具侧
- 不可观察：Consumption（UNOBSERVABLE，绝不记为未消费）

## P2. Claude Code Profile（OTLP 观察）

- 可靠：tool result（tool_name/tool_use_id/success/duration_ms/error_type）、
  **Context Availability 信号**（API request telemetry 带 mcp_server.name/mcp_tool.name =
  该 tool result 进入后续 model context）、trace
- Observation：`observer_side=client, provenance=otel`
- **Context Availability 的第一个可实证平台**：tool_result(tool_use_id=X) → 后续
  request(mcp_tool.name) 即 availability 链（reference/collector/consumption.py 已实现）
- 边界（#11）：available ≠ referenced ≠ counterfactually influential。本 profile 只实证
  availability；reference 是弱行为证据；causal influence 需 ablation/rerun，属 experiment
  层（Lab），single trace 不可证

## P3. DeepSeek Harness Profile（插件观察）

- 可靠：tool/call + tool/result（sourceEventSeqs 原生配对）、session 事件流
- 注意：harness 内配对只证明**生命周期完成**（completed lifecycle observation），
  不构成独立佐证
- Observation：`observer_side=client, provenance=platform, lifecycle_stage=completed`
- 证据由 verifier 判定（Evidence Profile）；与工具侧观察匹配才可能 cross-side
  corroborated

## P4. Tool-side Profile（wrapper/OTel server 观察）

- 可靠：真实调用边界（execution/completion）、outcome、duration、trace
- Observation：`observer_side=server`
- 单侧永不构成 corroborated

## 能力矩阵（协议视角）

| Capability | Codex | Claude | DSH | Tool-side |
| --- | --- | --- | --- | --- |
| Exact call id | ✅ | ✅ | ✅ | depends |
| Trace | ❌ | ✅ | depends | ✅ |
| Success 判定 | ⚠️ | ✅ | ✅ | ✅ |
| Duration | ⚠️ | ✅ | ✅ | ✅ |
| Context Availability 可观察 | ❌ | ✅ MCP | ? | — |
| 独立构成 cross-side corroborated | ❌ | ❌ | ❌ | ❌ |
