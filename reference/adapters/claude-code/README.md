# agentmeasure-claude — Claude Code Adapter（设计）

> Claude Code 原生支持 OTLP 输出（metrics / events / traces），官方文档明确工具调用频率、
> 成功率、耗时与 MCP activity 作为 telemetry 场景。
> 原则：**不要求用户放弃现有 observability backend**——AgentMeasure 作为 OTel Processor/Exporter。

## 1. 架构

```text
Claude Code
      ↓ OTLP
agentmeasure Collector（本地）
        ├─→ 用户自己的 Grafana / Langfuse / 现有 backend（原样转发）
        └─→ privacy-safe aggregates → AgentMeasure 公开统计
```

## 2. 设计要点

| 决策 | 说明 |
| --- | --- |
| 接入形态 | OTel Collector Processor + Exporter 组合（AgentMeasure 发行独立 collector 配置） |
| 数据分流 | 同一 OTLP 流：全量转发给用户 backend；AgentMeasure 只消费 execute_tool / mcp 相关 span |
| 字段映射 | `gen_ai.tool.name`、`mcp.method.name` → unified tool；`agentmeasure.*` 扩展属性由 Claude adapter 注入 |
| 证据等级 | Claude OTel 输出为 client 侧观测 → authenticated 级起点；与工具侧 trace_id 匹配 → cross-side corroborated |
| 敏感处理 | 官方提示 tool details 可能含 command/path/URL——AgentMeasure 消费端默认 DROP（复用 redactor） |
| Session | Claude session 标识 → 伪匿名（本地哈希，不落原始值） |

## 3. 实现计划

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| P1 | AgentMeasure Collector 配置模板（OTLP 接收 → 分流 → 本地聚合） | 待开发 |
| P2 | execute_tool span → unified record 的映射实现（normalizer 已有 otel-span 分支） | 部分（normalizer 已支持） |
| P3 | 与工具侧 trace_id 关联（复用 correlator） | 复用 |
| P4 | 文档：Claude Code 侧启用 OTLP 的配置指引 | 待开发 |

## 4. 验证标准

- [ ] Claude Code 配置 AgentMeasure collector 后，工具调用产生本地 usage 记录
- [ ] 用户现有 OTLP 后端不受影响（数据原样通过）
- [ ] 敏感字段零泄漏
- [ ] 与 Codex / DSH 数据并入同一统计（跨宿主统一）
