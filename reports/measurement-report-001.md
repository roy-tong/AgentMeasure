# Measurement Report #001 — First Local Pipeline（Draft 0.4.3 demo）

> **状态：本地合成流量验证（非真实外部 Provider）。** 本报告证明
> `Provider SDK → Canonical Observation → Collector → Metrics` 端到端成立，
> 并展示 0.4.3 的 fail-closed 语义如何在真实管道中生效。
> 真实外部数据见未来 Measurement Report（Product Gate A 验收项）。

## 设置

- 被测面：`acme-weather`（@modelcontextprotocol/sdk 注册的第三方风格 MCP server）
- 接入：`@agentmeasure/mcp` v0.1.0 中间件（注册时包装 handler）
- 流量：42 次模拟调用（claude / codex / unknown 三类调用方混合），含 ~12% 上游失败
- 采集：本地缓冲 → Canonical Observation JSONL（126 条）→ reference collector
- 窗口：单次运行

## 结果

```text
Canonical observations accepted : 126   rejected: 0
Observed attempts               : 42
Strict Qualified attempts      : 0 (0.0%)
  qualification status         : {'unknown': 42}
Success / Failure              : success-rate 88.1%  unknown/inconsistent 0
Operation resolution           : resolved 0 / 42 attempts (coverage 0.0%)
  resolution                   : {'unknown': 42}
```

## 关键发现（对 0.4.3 语义的验证）

1. **0 rejection**：SDK 输出的 126 条观察全部通过 Canonical Schema 校验
   （schemas/observation.schema.json + per-type payload）——"唯一 Canonical 输入"
   在真实管道中成立。
2. **Strict Qualified = 0% 是正确的，不是缺陷**：SDK 默认
   `usage_context=unknown`（observe first）。42 条 attempt 全部是 unknown——
   没有部署配置证据，任何数字都不得伪装成 production。
3. **Operation Resolution Coverage = 0% 是正确的，不是缺陷**：Provider-only
   拓扑没有 operation 证据（无 runtime 传播的 operation_id），fail-closed 输出
   0 operations / 42 attempts——这正是 M3.5 存在的意义。
4. **Success 88.1%**：中间件通过异常 + MCP `isError` 元数据判定 outcome
   （不读取内容）；模拟的 ~12% 失败被如实捕获。
5. **Caller 纪律**：caller 为 declared（SDK 配置声明），绝无 attested/correlated
   冒充。

## 下一步（Product Gate A）

- [x] P0-1 Canonical 端到端（Adapter → SDK → Collector → Metrics）
- [x] P0-2 Provider SDK（@agentmeasure/mcp v0.1.0）
- [x] P0-3 Local Analytics（product/local-analytics.py）
- [ ] P0-4 第一个**真实外部** MCP server 接入（本报告为本地验证）
- [ ] Hosted ingestion（P1）
- [ ] 3–5 Provider Alpha（P1）
- [ ] 数据驱动的真实 Actionability 案例（P1）
