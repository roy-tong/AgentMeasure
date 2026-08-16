# Adapter Capability Matrix

> 每个 adapter 能可靠提供什么、不能提供什么——公开声明局限是测量项目的可信度基础。
> ✅ = 稳定可靠 · ⚠️ = 部分/受限 · ❌ = 不提供 · ? = 待验证
> 词汇（Draft 0.4.1）：Selection / Operation / Attempt / Completion / Consumption；
> 生命周期阶段 = selected · invoked · completed · consumed。

| Capability | Codex Hook | Claude OTel | DSH Plugin | MCP Server (wrapper) |
| --- | --- | --- | --- | --- |
| Selection（生命周期 selected） | ✅ | ✅ | ✅ | — |
| Executed（invoked） | ✅ | ✅ | ✅ | ✅ |
| Completion outcome（completed） | ⚠️ 不可靠（Bash 非零退出仍触发 PostToolUse） | ✅ | ✅ | ✅ |
| Duration | ⚠️ 无官方时间戳 | ✅ | ✅ | ✅ |
| Tool call ID | ✅ `tool_use_id` | ✅ `gen_ai.tool.call.id` | ✅ `callId` | depends on server |
| Trace ID | ❌ 官方 schema 无 | ✅ | depends | ✅ |
| Consumption（result consumed） | ❌ | ✅ **MCP 消费信号**（`mcp_server.name`/`mcp_tool.name` 出现在后续 request telemetry） | ? | — |
| Agent-side observation | ✅ | ✅ | ✅ | ❌ |
| Server-side observation | ❌ | ❌ | ❌ | ✅ |
| 独立构成 cross-side corroborated | ❌（单侧） | ❌（单侧） | ❌（单侧，harness 内配对仅生命周期） | ❌（单侧） |

## 说明

- **Codex Hook 能力边界**来自官方 `PostToolUse` schema：`session_id / model / turn_id / tool_name / tool_use_id`；无 trace_id、无可靠时间戳、无成败判定。
- **Claude Code 是 Consumption 的第一个实证平台**：`claude_code.tool_result` span 提供 `tool_name/tool_use_id/success/duration_ms/error_type`；v2.1.222+ 的 API request telemetry 在**实际消费了某个 MCP tool result** 时才带 `mcp_server.name/mcp_tool.name`——tool_result（tool_use_id=X）→ 下一次 request（mcp_tool.name）即消费证据链。
- **DSH Plugin**：`tool/call ↔ tool/result` 的 harness 内配对只证明生命周期完成（completed），不构成独立佐证；evidence 由 verifier 计算。
- **cross-side corroborated 需要跨侧**：任何单侧 adapter 都无法独立构成；同一 attempt 的 ≥2 条独立 observer 观察。
