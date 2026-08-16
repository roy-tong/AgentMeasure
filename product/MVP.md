# AgentMeasure MVP — Remote Capability Analytics（Draft 0.4.1）

## 一句话

> **我的 capability 被观察到多少次真实 provider-side usage？**

## 范围

```text
@agentmeasure/mcp
        ↓
provider observations
        ↓
local buffer
        ↓
hosted ingestion
        ↓
minimal dashboard
```

### 交付物

1. **Provider SDK（Python 先行）**：MCP server / HTTP API 的观测装饰器
   （PROVIDER-SDK.md 契约：fail-open、异步、缓冲、Caller Identity 分级）
2. **Local buffer**：磁盘队列，崩溃恢复（DEPLOYMENT.md）
3. **Hosted ingestion**：envelope 校验 + 鉴权 + 配额
4. **Minimal dashboard**：Operations · Attempts · Success · Retry · Latency ·
   Caller runtime（declared/unknown）· Measurement Coverage

### Dashboard 示例（Mock）

```text
company.research — last 30 days (Strict Qualified)
Operations         1,204        attempts/operation  1.3
Attempts           1,565
Success Rate       91.8%        unknown outcomes    3.1%
Retry Rate         9.4%
Latency p95        <2s (bucket 1s-10s: 94%)
Caller runtime     claude (declared) 58% · codex (declared) 12% · unknown 30%
Coverage           participating_network · observed clients 142
```

## 验收标准

- [ ] 真实 MCP server 接入 SDK，产生本地 observation（无内容字段，伪匿名）
- [ ] 断网 10 分钟 → 缓冲不丢；恢复后批量补传
- [ ] SDK 异常不影响业务（fail-open 注入测试）
- [ ] Caller identity 分级显示（绝无裸 "Claude Code"）
- [ ] 与 reference collector 数据打通（同一 envelope 可被 verify）
- [ ] **≥1 个真实 Provider 愿意接入**——本轮唯一的业务验证目标

## 非目标（明确不做）

- ❌ Selection Rate / Share of Choice（无信号）
- ❌ Consumption 链（无 agent 侧）
- ❌ Metering / 账单（COMMERCIAL 是语义；支付是别人的 rails）
- ❌ 跨 Provider 排名（coverage_basis 限制）
- ❌ 冒充"AgentMeasure 官方 SDK"——未实现前全部标注 in development

## 里程碑

| M | 内容 | 状态 |
| --- | --- | --- |
| MVP-1 | SDK 观测装饰器 + 本地缓冲 + 本地 collector 打通 | 未开始 |
| MVP-2 | Hosted ingestion + minimal dashboard | 未开始 |
| MVP-3 | 首个真实 Provider 接入 + 第一份 provider-scoped 报告 | 未开始 |
