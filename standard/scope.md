# Scope — AgentMeasure 是什么，不替代什么

> 结构借鉴 PEAC Protocol 的 `Where PEAC fits (and where it does not)` 章节。
> 作用：**一次性说清边界**，让任何人（包括潜在竞品）在三十秒内判断我们是补位还是竞争。
> 本文是定位文档，不是规范；规范性内容见 `CORE.md` 与 `extensions/COMMERCIAL.md`。

## 一句话

**AgentMeasure 是语义层：它说明一个声称**意味着什么**，
不判断记录是否真实，也不判断钱该不该付。**

## 我们提供

| 提供 | 在哪 |
|------|------|
| **测量语义** —— 什么算一次操作、什么算一个结果 | `standard/CORE.md` |
| **outcome 分类与观察方分级** | `registry/vocabularies.yaml` |
| **证据姿态** —— 什么证据支持什么强度的声称 | `extensions/COMMERCIAL.md` §5.2 |
| **指标合同** —— 任何实现算出同一个数 | `standard/METRICS.md` + `registry/metrics.yaml` |
| **conformance 向量与 runner** —— 可对照、可重放 | `conformance/` |
| **本地检查工具** —— 用户能跑 | `healthcheck/` |
| **可谈判的结算声明** —— 两线对照、对称披露 | `agentmeasure settle --statement` |

## 我们不替代

| 不替代 | 那是谁 | 关系 |
|--------|--------|------|
| **可观测性**（trace / span / metric 采集） | OpenTelemetry、Langfuse、Arize | 我们是**补位层**：在他们之上定义语义，不重新采集 |
| **可验证记录**（签名、防篡改、时间戳） | PEAC Protocol、Glacis、IETF SCITT | 他们让记录**不可篡改**，我们让记录**有含义**。可叠加：签名包住我们的结论 |
| **账单金额核对**（实际用量 vs 开票金额） | Vaudit、Inferock | 他们验证**计数完整性**，我们验证**判定完整性** |
| **质量评分**（答得好不好） | QEval、Supportman、Isara | 我们不判断质量，只判断声称能不能成立 |
| **AI 客服平台本身** | Intercom、Zendesk、Decagon、Sierra、Ada | 我们审计的是**它们的声称**，不参与提供服务 |
| **身份、支付轨道、结算执行** | 支付基础设施 | 见 `extensions/COMMERCIAL.md` §9：**测量永不进支付关键路径** |
| **法律或合规意见** | 律所、审计机构 | 我们产生**可核验的事实**，法律结论由专业人士做 |

## 三个完整性正交

这是理解本领域的关键，也是我们只占其中一层的理由：

```text
计数完整性          记录完整性          判定完整性
tally integrity     record integrity    classification integrity
      │                    │                    │
      ▼                    ▼                    ▼
  金额对不对          记录真不真          结果该叫什么
      │                    │                    │
   Vaudit               PEAC                 AgentMeasure
   Inferock            Glacis
```

**三者可组合，不可互相替代。**

一句值得记住的话（来自 The Colony 对本领域的评论）：

> **"A cryptographically signed, append-only record of a generous classification
> is just a tamper-evident receipt for an inflated bill."**
>
> 一个加密签名、只追加的、宽松分类的记录，只是一张**为虚高账单背书的防篡改收据**。

签名解决不了分类问题。**这正是我们存在的原因。**

## 典型的叠加用法

```text
1. AgentMeasure  判定：这次交互的结果该叫 resolved 还是 assumed_resolved
2. PEAC          签名：把该判定封进可验证收据
3. Vaudit        对账：把判定与账单逐行核对
4. 买方           谈判：用 Settlement Statement 与厂商对账
```

我们不与任何一层竞争；**没有我们这一层，上面三层都在处理一个未定义的词。**

## 与相邻标准的关系

| 标准 | 它定义 | 我们补充 |
|------|--------|---------|
| **PEAC Protocol** | 可验证交互记录的 wire format、policy 发现、Dispute Bundle | outcome 语义可作为其 extension group 挂载（已就此联系） |
| **Inferock Standard** | token 侧的证据姿态与计费完整性收据 | 我们把姿态模型适配到 outcome 侧并引用其来源 |
| **ARS-1** | 「settled resolution」的判定条款（单一作者草案） | 我们采纳其「读者分歧 = 文本有罪」的自我修正原则 |
| **OTel GenAI semconv** | 遥测属性命名 | 我们不重新定义属性，定义**属性的含义边界** |

## 我们明确不做

- ❌ 不提供审计服务（不做按单收费的人工重数）
- ❌ 不判断答案质量
- ❌ 不实现签名与密钥管理
- ❌ 不采集遥测（用现成的 OTel / runtime 日志）
- ❌ 不移动金钱、不托管资金、不做商户记录
- ❌ 不发布厂商自我报告面板（卖方控制计量器是问题本身）
