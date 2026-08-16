# AgentMeasure Reports

## Discrepancy Report #1（模板）

```markdown
# Agent Usage Measurement Discrepancy Report #1

## 设置
- 工具：<tool>（<test MCP server>）
- 观察面：<runtime>（client）/ <wrapper>（server）
- 任务：N 个，每任务 K 次调用，X% 故意失败

## 漏斗数据（真实）
| Stage | 计数 |
|---|---|
| Presented | ? |
| Selected | ? |
| Invoked | ? |
| Completed | ? |
| Consumed | ? |

## 差异分析
| 面 A | 面 B | Delta | 原因假设 | 验证 |
|---|---|---|---|---|
| ? | ? | ? | ? | ? |

## 对标准的修正建议
- AUP-XXXX：...

## 结论
- 哪些指标跨面稳定（可公开）
- 哪些指标面敏感（必须标注 observer）
```

## 纪律
- 第一份报告不做行业排行榜
- 每份报告必须携带 Measurement Label（口径/覆盖/采样）
- 差异是数据，不是 bug——分歧推动标准演进
