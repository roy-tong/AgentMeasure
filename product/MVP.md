# AgentMeasure MVP — Provider-observed Capability Usage（Draft 0.4.2）

## 一句话

> **我的 capability 被观察到多少次 provider-side 请求与结果？其中多少能归因到 Agent？**

产品定位：**Provider-observed Capability Usage**（Agent-facing Usage Analytics）。
不是 "Real Agent Usage"——归因强度分层披露。

## 范围

```text
@agentmeasure/mcp
        ↓
provider observations（observe first, qualify later）
        ↓
local buffer（durable best-effort + source_sequence）
        ↓
hosted ingestion
        ↓
minimal dashboard
```

### Dashboard（MVP）

```text
company.research — last 30 days (Strict Qualified)

Observed requests                  12,481        ← 全部请求（attempts）
Resolved Operations                 6,410
Operation Resolution Coverage       51.4%
Unresolved Attempts                 6,071

Success Rate                       91.8%        unknown outcomes 3.1%
Retry Rate                          9.4%
Latency p95                        <2s

Caller attribution
  correlated                       3,214
  declared                         5,892
  unknown                          3,375

Measurement Coverage               participating_network · observed clients 142
```

**Operations 只在 Operation Resolution Coverage 足够高时突出显示。**

## 验收标准（MVP-1 里程碑）

- [ ] 真实 MCP server 接入 SDK，产生本地 observation（unknown 默认、无内容字段、伪匿名）
- [ ] 断网 10 分钟 → 缓冲恢复后批量补传，`source_sequence` 缺口可被云端检出
- [ ] SDK 异常不影响业务（fail-open 注入测试）
- [ ] Caller identity 分级显示（UA/clientInfo 只到 declared；绝无裸 "Claude Code"）
- [ ] Operation Resolution Coverage 正确披露（unresolved 不伪装成 operations）
- [ ] 与 reference collector 数据打通（同一 envelope 可被 verify）

## Alpha Graduation（真正的 Product Validation）

**MVP-1 的"≥1 个 Provider 接入"只是起点**；Alpha 毕业标准：

```text
3–5 个外部 Provider，至少包含：
  1 remote MCP
  1 agent-facing HTTP API
  1 closed-source provider

≥ 2 周真实流量

观察：他们有没有第二次主动打开 Dashboard？
```

因为真正要验证的不是"愿不愿意装"，而是 **这些数据会不会改变他们的产品决策**。

## Actionability（最重要的业务指标）

Alpha 期间记录 `Measurement insight → action`：

```text
发现 12% retry        → 修 SDK
发现 unknown caller 60% → 增加 MCP metadata
发现 tool A latency 高  → 优化 service
发现某 runtime failure 高 → 修兼容性
```

> 验证目标：**AgentMeasure 是分析工具，不只是日志面板。**

## 非目标（明确不做）

- ❌ Observed Selection Rate / Share of Choice（无信号）
- ❌ Consumption 链（无 agent 侧）
- ❌ Metering / 账单（COMMERCIAL 是语义；支付是别人的 rails）
- ❌ 跨 Provider 排名（coverage_basis 限制）
- ❌ 冒充"AgentMeasure 官方 SDK"——未实现前全部标注 in development

## 里程碑

| M | 内容 | 状态 |
| --- | --- | --- |
| MVP-1 | SDK 观测装饰器 + 本地缓冲 + 本地 collector 打通 | 未开始 |
| MVP-2 | Hosted ingestion + minimal dashboard | 未开始 |
| Alpha | 3–5 外部 Provider + 2 周真实流量 + Actionability 记录 | 未开始 |
