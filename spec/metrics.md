# Metrics（指标模型 v3）

> **统计对象是 invocation（一次逻辑调用），不是 observation（一次观察）。**
> Observation/Invocation 拆分后：一次双边调用的两方观察 = 1 个 invocation。
> 若按 observation 计数，100% 双边关联的数据 corroborated share 最高只能显示 50%。

## 1. 核心指标

### 首要：VACD（Verified Active Client-Days）

> 某 project 在某 UTC 日，被一个 privacy-preserving client identity 产生
> ≥1 次 eligible invocation = 1 Active Client-Day。

优势：不受 tool API 数量、retries、session 生命周期差异影响；可跨
Codex / Claude / DSH 比较；类似 DAU，是成熟的 adoption 心智。派生指标：
7d active client-days、30d active clients、active days/client、retention。

（Active Agent Sessions 因不同 harness 的 session 生命周期定义不一（MCP
2026-07-28 已去 protocol-level session），不适合做跨平台首要指标。）

### 第二：Corroborated Usage

- corroborated invocations = evidence=E2 的 invocation 数
- **corroborated share = corroborated / eligible**（100% 双边关联 → 1.0）

### 第三：Execution Quality

- success rate（invocation 级，eligible 内）
- error / retry 归一

### 第四：Engagement / Contribution

- repeat usage（client-day 内多次 eligible invocation 占比）
- **Result Consumed Rate**（Claude Code 的 mcp_tool.name 信号可实证，见 adapters/claude-code）

## 2. 归一化规则（防刷榜）

1. **invocation 归一**：多 observation 折叠为一个 invocation；重试链折叠
2. **禁用拆 API 刷榜**：排名按 VACD / active clients；tool 先 roll-up 到 project（identity.md）
3. **证据门槛**：eligible = evidence != E0；attributed 统计只含 E1+；corroborated 单列
4. **异常检测**：单日突刺、单一 client 异常贡献 → 标记 suspicious，不计入 attributed

## 3. 公开展示（badge / dashboard 最小集）

```
Agent Usage · 30d

2.8k active clients
11.4k active client-days
18.3k attributed invocations
73% independently corroborated
97% execution success
```

**用词纪律**：Observed / Source-authenticated / Corroborated / Platform-attested。
避免 true / real / verified / objective 等过度承诺词（E1 只是 source-authenticated，
不是"验证了真实发生"）。

## 4. 明确不做

- 不按 raw observation 或 raw calls 排名
- 不展示任何可反推个人/组织身份的数据
- 不做"好评"类指标（测量使用，不是评价）
