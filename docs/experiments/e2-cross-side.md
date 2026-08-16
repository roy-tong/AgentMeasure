# Experiment: Cross-side Corroboration & Discrepancy Report #1（设计）

> 目的：在真实 runtime 上验证 cross-side corroborated（双侧独立观察）关联，
> 并产出第一份《Agent Usage Measurement Discrepancy Report》。
> 前置：Claude Code 可用（OTLP）+ 一个测试 MCP server（双侧插桩）。
> 本设计 fixture 可先行（consumption.py 已实现消费链）；真实数据待运行时。

## 实验设置

```text
同一测试 MCP Tool（foo.search）

Claude Code ──OTLP──▶ AgentMeasure collector（client 侧观察）
   │
   └──MCP──▶ 测试 MCP server ──wrapper──▶ AgentMeasure collector（server 侧观察）
```

100 个任务，每个任务 3-8 次工具调用（含故意失败样本 10%）。

## 采集矩阵（预期输出）

| 阶段 | Claude (client) | MCP Server (server) | 双侧关联 |
| --- | --- | --- | --- |
| Selection | N | — | — |
| Executed | N | N | tool_call_id 匹配 |
| Completed | success/failure | success/failure | 一致性 |
| Consumption | mcp_tool.name 信号 | — | 消费链 |
| cross-side corroborated | — | — | 双侧独立观察数 |

## Discrepancy Report #1 模板

```markdown
# Agent Usage Measurement Discrepancy Report #1

## 设置
- 工具：foo.search（测试 MCP server）
- 观察面：Claude Code OTLP（client）/ MCP wrapper（server）
- 任务：100 个，3-8 次调用/任务，10% 故意失败

## 观察结果
| 阶段 | Claude | Server | Delta | 原因假设 |
| --- | --- | --- | --- | --- |
| Executed | ? | ? | ? | ? |

## 已确认的差异
1. ...（如：client 看到 310 次、server 看到 271 次——超时/断连差异）
2. ...

## 结论
- 哪些指标跨面稳定（可公开）
- 哪些指标面敏感（需标注 observer）
- 对 spec 的修正建议
```

## 验证标准

- [ ] 双侧 tool_call_id 匹配率 ≥ 95%
- [ ] 失败样本在双侧一致（或差异可解释）
- [ ] 消费链（Consumption）在 Claude 侧可复现
- [ ] 报告发布到 whitepaper/ + 站点 + HN/X（M4）

## 状态

- [x] 消费链逻辑（consumption.py）fixture 测试通过
- [ ] 真实 Claude Code runtime 实验（待运行时与配额）
- [ ] 报告发布
