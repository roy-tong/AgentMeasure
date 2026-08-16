# OTel Mapping（agent-used 最小扩展字段）

> agent-used 站在 OpenTelemetry 之上。已有 OTel 标准字段一律复用，不重复发明。
> MCP 2026-07-28 RC 已在 `_meta` 传递 `traceparent / tracestate / baggage`——trace 传播本身交给协议。

## 1. 复用现有字段（不定义）

| 领域 | 字段 | 说明 |
| --- | --- | --- |
| 工具 | `gen_ai.tool.name` | OTel GenAI 语义约定 |
| 调用 ID | `gen_ai.tool.call.id` | 内部模型 `tool_use_id` 直接映射此字段，不建立平行概念 |
| 协议 | `mcp.method.name` | MCP OTel 语义约定（定义中） |
| 错误 | `error.type` | 标准错误字段 |
| 服务 | `service.name` / `service.version` | 资源属性 |
| 追踪 | `trace_id` / `span_id` / `parent_span_id` | 标准 trace 字段 |
| 执行 | Execute tool span | OTel GenAI（Development 状态） |

## 2. agent-used 最小扩展（仅 6 个字段）

在 OTel 语义约定之上，agent-used 只增加以下字段（前缀 `agentused.*`）：

| 字段 | 类型 | 取值 | 说明 |
| --- | --- | --- | --- |
| `agentused.project.id` | string | 归一项目标识 | 见 identity.md；`github.com/foo/bar` |
| `agentused.project.version` | string | 语义版本 | 工具版本（用于版本分布） |
| `agentused.observer.side` | enum | `client` / `server` / `platform` | 观测发生在哪一侧 |
| `agentused.agent.host` | enum | `codex` / `claude-code` / `deepseek-harness` / `other` | 宿主标识 |
| `agentused.provenance` | enum | `otel` / `hook` / `wrapper` / `platform` | 数据来源机制 |
| `agentused.evidence.level` | enum | `E0` / `E1` / `E2` / `E3` | **仅出现在 Invocation/Attribution Record 上**（verifier 派生属性），不出现在 instrumentation span——证据是验证+关联后的结果，不是插桩时能声明的事实 |

## 3. 映射示例

### Codex PostToolUse hook → OTel span 属性

```jsonc
{
  "gen_ai.tool.name": "Bash",
  "agentused.agent.host": "codex",
  "agentused.observer.side": "client",
  "agentused.provenance": "hook",
  "agentused.evidence.level": "E1",
  "agentused.project.id": "github.com/foo/bar",
  // prompt / tool_input / tool_output 默认 DROP（见 privacy.md）
}
```

### MCP server execute_tool span → 服务端

```jsonc
{
  "mcp.method.name": "tools/call",
  "gen_ai.tool.name": "foo.search",
  "agentused.observer.side": "server",
  "agentused.provenance": "otel",
  "agentused.evidence.level": "E1",   // 与 client 侧 trace_id 匹配后升级为 E2
  "trace_id": "abc"
}
```

## 4. 与 OTel GenAI 工作组的关系

- `agentused.*` 字段保持最小、可合并进标准的方向
- 目标：若 OTel GenAI 采纳（如增加 `gen_ai.tool.usage` 语义），agent-used 字段并入标准，自身退化为纯语义层
