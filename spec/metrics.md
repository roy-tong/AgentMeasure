# Metrics（四层指标模型）

> **Raw call count 不是北极星。** 一次任务 6 次调用 ≠ 6 倍使用；失败重试 3 次 ≠ 3 次使用。
> 指标按四层组织，优先级递减。排名默认按 **Active Agent Sessions**，防"拆 API 刷榜"。

## 1. 四层指标

### 第一层：Execution（执行）

| 指标 | 定义 | 备注 |
| --- | --- | --- |
| Tool Calls | raw 调用数 | supporting metric，不主导排名 |
| Successful Executions | 成功执行数 | S2 |
| Error Rate | 失败占比 | 含 retry 归一 |
| p50 / p95 Latency | 耗时分布 | 粗粒度桶（privacy） |

### 第二层：Adoption（采用）★ 首要

| 指标 | 定义 |
| --- | --- |
| **Active Agent Sessions** | 过去 30 天至少发生 1 次 verified usage 的伪匿名会话数 |
| Sessions Using Tool | 使用该工具的会话数 |
| Active Installations | 活跃安装数（伪匿名 installation id，见 privacy.md） |
| Agent Host Distribution | codex / claude-code / dsh 分布 |
| Version Distribution | 工具版本分布 |

### 第三层：Engagement（粘性）

| 指标 | 定义 |
| --- | --- |
| Calls / Active Session | 会话内平均调用（按 session 归一，不按任务内重复） |
| Repeat Usage | 会话复用工具 |
| 7d / 30d Repeat Session Rate | 跨周期回访率 |

### 第四层：Contribution（贡献）★ 最有价值、最难

```
Tool Result Produced → Result Consumed by Agent → Agent Continued Task → Task Completed
```

| 指标 | 定义 | 可行性 |
| --- | --- | --- |
| Result Consumed Rate | S3 / S1：返回结果被后续上下文实际引用 | 部分 Agent 可测（Claude Code OTel 有基础） |
| Task Contribution | S4：对下游任务完成有贡献 | 研究方向（需要任务级完成信号） |

**长期研究重点：Result Consumed Rate 比 Tool Calls 更能反映工具价值。**

## 2. 归一化规则（防刷榜）

1. **会话归一**：同 session 内重复调用折叠为会话级使用（Engagement 层单独展示次数）
2. **重试归一**：`call → fail → retry → success` 计为 1 次会话使用 + 1 次成功；错误率单列
3. **禁用拆 API 刷榜**：排名按 sessions 而非 calls；同一 project 的多个 tool 先 roll-up（identity.md）
4. **异常检测**：单日突刺（> 30 天中位数 ×10）、单一 installation 异常贡献 → 标记 suspicious，不计入 verified 统计
5. **证据门槛**：verified 统计只含 E1+；corroborated 单列

## 3. 公开展示（badge / dashboard 最小集）

```
Agent Usage · 30d
2.7k active agent sessions   ← 第一指标
18.4k verified calls         ← supporting
96.2% success
71% corroborated
Codex · Claude Code · DSH    ← host 分布
```

## 4. 明确不做

- 不按 raw calls 排名
- 不展示任何可反推个人/组织身份的数据
- 不做"好评"类指标（测量使用，不是评价）
