# 如何测量 Agent Tool Economy

**An Open Standard for Usage Attribution in the Agent Ecosystem**

> 作者：Roy Tong（仝夏瑞）· 产品经理 · 连续创业者
> 配套实现：[agent-used](https://github.com/roy-tong/agent-used)（Attribution Layer 的 reference implementation）
> 状态：v1 草案，随社区讨论演进

## 一个基本问题

**What does it mean for software to be "used by an agent"?**

2026 年，Agent 正在成为软件分发最重要的新渠道。Claude Code、Codex、DeepSeek Harness 会替用户选择工具、安装 skill、调用 MCP server。工具作者第一次面对一个无法回答的问题：**我的工具到底有没有被 Agent 用？**

现有信号全部失效：

- GitHub star / clone 显示的是人，不是 Agent
- skills.sh 安装数是自报遥测（可刷、无 API、无验证）
- MCP registry 明确不做采纳数据
- llms.txt 声明了，审计显示 97% 零 AI 请求

于是工具作者只能靠感觉决策：该不该继续维护这个 MCP server？该把算力投到哪个工具？Agent 是怎么发现工具的？

本文想做的第一件事不是给答案，而是**把问题定义清楚**。

## 概念贡献：使用不是一个事件，是一条链

工具生态过去有一个隐含假设：下载了 = 用了。Agent 生态把这个假设彻底打破。

```text
Install ≠ Usage
Discovery ≠ Selection
Selection ≠ Execution
Execution ≠ Success
Success ≠ Consumption
Consumption ≠ Contribution
```

每一层都不能替代下一层：

| 阶段 | 定义 | 谁可观察 | 意义 |
| --- | --- | --- | --- |
| S0 Selected | Agent 选择了该工具 | Agent runtime | 被发现且被选中 |
| S1 Executed | 实际执行了调用 | 双侧 | 选择变成了行为 |
| S2 Execution Success | 成功返回 | 双侧 | 行为变成了结果 |
| S3 Result Consumed | 结果被后续上下文使用 | Agent runtime（部分） | 结果变成了输入 |
| S4 Task Contribution | 对下游任务完成有贡献 | 研究方向 | 输入变成了价值 |

**"调用成功"不等于"工具有用"。** 一个被反复调用但结果从不被 Agent 使用的工具，和没有被调用没有本质区别。长期来看，**Result Consumed Rate 比 Tool Calls 更接近工具的真实价值**——这是整个测量框架最重要的研究方向。

## 证据分级：签名不等于真实

开放生态里不存在绝对 ground truth。任何"客观真实"的宣称都需要回答：**你凭什么证明？**

一个工具作者可以生成 100 万条假调用，用自己的 key 做 HMAC——全部是合法签名。所以 HMAC 只证明"数据来自持 key 主体且未被篡改"，不证明"真的有 Agent 调用了它"。

因此测量体系必须用**证据等级**取代二元判断：

| 等级 | 名称 | 能证明什么 | 公共统计可信度 |
| --- | --- | --- | --- |
| E0 Observed | 单边日志 | 某一方声称 | 低 |
| E1 Source-authenticated | 签名事件 | 来源与完整性 | 中低 |
| **E2 Correlated** | 双边独立观测匹配 | 同一次真实调用 | **高（核心）** |
| E3 Platform-attested | 平台直接证明 | 平台确认 | 很高 |

**E2 是技术上的关键突破点**：当 Agent 侧与 Tool 侧通过同一 OTel trace（`trace_id`）独立记录到同一次调用，两侧无法单方伪造对方的观测，这才构成 **corroborated usage**。

MCP 2026-07-28 Release Candidate 把 OTel trace context（`traceparent / tracestate / baggage`）正式纳入 `_meta` 传递——**协议级双边关联首次成为现实**。这是本框架最重要的技术基础：不是我们发明了 trace 传播，而是我们第一次定义"trace 对上之后，什么才算一次可信的使用"。

## 测量模型：六要素

```
Agent Usage Measurement Model
        ├─ Identity     这次使用属于哪个项目（repo↔npm↔MCP↔tool↔CLI↔skill 归一）
        ├─ Observation  谁观测的（client / server / platform）
        ├─ Correlation  双边是否对上（trace_id / tool_use_id）
        ├─ Evidence     可信到什么程度（E0-E3）
        ├─ Aggregation  如何归一化（session 归一、重试归一、防拆 API）
        └─ Privacy      如何公开而不泄露（raw stays local）
```

其中 **Identity** 是被低估的难点：同一项目在 GitHub、npm、MCP registry、tool 名、CLI、skill 下有六种身份。不做归一，同一个项目会被拆成六份数据——排名失真，也给"拆 API 刷榜"留了空间。Canonical Identity Graph 是测量体系的底层资产。

## 指标：为什么 Raw Call Count 不是北极星

一个 Agent 完成任务需要 `search → fetch → parse` × 2 = 6 次调用；另一个 Agent 用高度封装工具 `research()` = 1 次调用。前者不意味着 6 倍使用。失败重试链 `call → fail → retry → success` 反而产生 3 条记录。

因此公开指标按四层组织，优先级递减：

1. **Adoption**（首要）：Active Agent Sessions——过去 30 天产生 verified usage 的会话数
2. **Engagement**：Repeat Usage、7d / 30d 回访率
3. **Quality**：Execution Success、Result Consumption
4. **Trust**：Corroborated Usage Share（E2 占比）

排行榜按 Active Sessions 而非 calls——否则必然出现"为刷榜把工具拆成 50 个 API"。

## 与现有标准的关系：站在 OTel 上面

agent-used 不替代 OpenTelemetry，也不替代 MCP：

- **OTel 解决 telemetry 怎么传**：trace 传播、span、字段约定
- **MCP 解决工具怎么调**：协议、`_meta` trace context
- **agent-used 解决什么才算使用**：语义、证据、身份、指标、隐私

实现上只增加 6 个 `agentused.*` 扩展字段（`project.id`、`observer.side`、`agent.host`、`provenance`、`evidence.level`、`project.version`），其余全部复用标准字段。若 OTel GenAI 工作组未来采纳，字段并入标准，agent-used 退化为纯语义层——这是设计目标。

## 架构：Attribution Layer

```text
Public Usage Layer（Dashboard / API / Badge / Rankings / Trends）
        ▲  aggregated only
Attribution Layer
  Identity Resolution · Dedup · Correlation · Evidence Grading
  Privacy Aggregation · Metric Normalization
        ▲                ▲
 Agent Adapters        Tool Adapters
  codex / claude / dsh   mcp / http / cli
        ▲                ▲
   OTel / MCP existing standards
```

三个 Agent 侧 adapter 证明跨平台可统一：

- **Codex**：`PreToolUse / PostToolUse` hooks 观测 MCP、shell 与 local function tools；`prompt / tool_input / tool_output` 默认 DROP——adapter 的意义不是记录更多，而是**证明 Codex 这一侧真的发起了调用**
- **Claude Code**：原生 OTLP 输出（metrics/events/traces），agent-used 作为 OTel Processor/Exporter 接入——**不要求用户放弃现有 observability backend**
- **DeepSeek Harness**：everything is a plugin，tool 执行暴露 `pre-execute / execute / post-execute` seam，session 是可持久化事件流——可以做最深的第一方集成

同一套 Measurement Model 横跨三套完全不同的 harness——这就是"标准"的意义。

## 隐私：Raw stays local

```
Raw Events → 本地 Collector（identity/dedup/redact/aggregate/evidence）→ SAFE AGGREGATES → 公开
```

云端默认拿不到：prompt、input、output、path、email、username、raw session id。伪匿名 installation id（本地 secret + 按月轮换）支持 unique installations 与 repeat usage 计算，云端无法反推身份。

**为什么"我们绝不记录参数"不够**：那是承诺；体系是架构。把 redaction 放进采集链路的默认路径，让泄漏在代码层不可能发生（adapter 带泄漏测试）。

## 政策红线

1. 不自动 star / follow（GitHub AUP 明确禁止 automated starring）
2. 不爬 GitHub 网页采集数据（交叉验证走官方 API）
3. 不按 raw calls 排名（防拆 API 刷榜）
4. 测量"使用"，不是"好评"

## 生态路径

三条路不是竞争，是互补：

| 伙伴 | 解决什么 | 角色 |
| --- | --- | --- |
| **Agent 平台**（OpenAI / Anthropic / DeepSeek） | 谁真正调用了 | 证据的最高权威（E3） |
| **GitHub** | 项目是谁的、代码在哪 | 身份与归属（repo identity、badge） |
| **MCP Registry** | 这个 server 是谁 | **第一批生态合作的自然起点**——registry 是身份，agent-used 是实际使用；官方明确欢迎 downstream aggregator 增加 ratings / security / usage 等额外信息 |

## 行动号召

- **工具作者**：接入 adapter，先看自己的真实数据（不急着上榜）
- **Agent 平台**：开放 attestation 接口，让"使用证明"成为平台原生能力
- **标准社区**：讨论 S0-S4 漏斗与 E0-E3 证据模型——这是可以进 AAIF / OTel GenAI 的草案
- **研究者**：Result Consumption（S3）与 Task Contribution（S4）的测量方法，是开放问题

**先推动问题定义，再推动实现。** 本文是问题定义；[agent-used](https://github.com/roy-tong/agent-used) 是 reference implementation。

---

*反馈：GitHub Issues（agent-used 仓库）或 X @elliwoodtong。Spec 全文见仓库 `spec/`（measurement-spec / evidence-model / metrics / privacy / identity / threat-model / otel-mapping）。*
