# Zendesk "Verified Resolution" — who verifies the verifier?

> 案例日期：2026-09-19。来源：Zendesk 官方帮助中心文档（见文末引用）。
> 置信度：**官方文档一级引用**（本机浏览器抓取，非二手转述）。
> 性质：公开文档分析，不是对 Zendesk 的指控。目的是展示「效果费审计」在
> 一个比 Intercom 更强的声称上长什么样。

## 一句话

Intercom 至少把「确认解决」和「假定解决」分开；**Zendesk 把两者合并后命名为
"Verified Resolution"，而验证者是 Zendesk 自己的 LLM。**

## 官方定义（逐字引用）

Zendesk 帮助中心《About the automated resolutions platform》：

> "Automated resolutions are the usage metric for AI agents and **the basis for
> billing**. You're charged only when a customer's issue is resolved without
> human help, and **each resolution is verified by an LLM**."

> "Conversations flagged as resolved are also **verified by a large language
> model (LLM)**, ensuring its accuracy and delivering a true automation rate."

关键点：**验证方是卖方自己的模型**。买方从外部无法复现这个判断。

补充（Relate 2026 发布报道）：Zendesk 的表述是每次计费 resolution **由 agent 本身
加一个独立的评估模型双重检查**。仍是卖方侧的两个模型，不是买方确认。

## 2026-05-18 引入的 Resolution Tiers

| Tier | 官方描述 | 是否计费 |
|------|---------|---------|
| **Assisted escalation** | AI 参与后由人工完成解决 | **不计费** |
| **Contained resolution** | 「AI 把交互处理到完成，**且客户没有要求进一步帮助**」；LLM 验证**未通过**的归入此档 | **不计费** |
| **Verified resolution** | 「AI 成功解决了交互」；LLM 验证**通过**的归入此档 | **计费** |

注意 Contained resolution 的判定条件逐字是：

> "the customer did not do any of the following: Request further clarification.
> Provide feedback on the AI agent's answer. Ask to speak to a human."

**客户沉默 = 解决。** 这正是 Intercom「assumed resolution」的同一模式，只是
Zendesk 把它放在「验证」这个词后面。

## 会话何时算「结束」（决定计费时点）

| 渠道 | 结束条件 |
|------|---------|
| Email | 最后一封邮件后 **72 小时** |
| Messaging | 默认最后一条消息后 **2 小时**（可调至 72 小时） |
| Voice | 挂断即刻 |

**2 小时的默认窗口意味着**：客户在 messenger 里没回话两小时，这次对话就可能
被判为已解决并计费。

## ⚠️ 官方文档自己承认的多收费路径

Zendesk 文档原文（《About the automated resolutions platform》）：

> "Note: For email AI agents, make sure you've created the automation trigger to
> ensure accurate human agent intervention detection. **If you don't, any replies
> made by human agents during conversations in which the email AI agent also
> participated don't appear in the conversation logs. As a result, automated
> resolutions might be consumed for conversations they shouldn't be.**"

翻译：**如果客户没配置某个 automation trigger，人工客服的回复不会进入对话日志，
于是本不该计费的对话会被计费。** 这是厂商文档里写明的计费错误路径——买方只能
靠自己审计发现。

## 审计问题清单（AgentMeasure 视角）

对照我们的 outcome 语义，Zendesk 场景下买方需要能回答：

1. **这次 "Verified" 是谁判的？** —— 卖方 LLM，买方无法复现
2. **客户有没有任何肯定表示？** —— 官方定义不要求客户确认，只要求客户没反对
3. **人工有没有介入？** —— 依赖 automation trigger 配置，配置错就漏记
4. **会话在哪一刻结束的？** —— 2h/72h 窗口，决定同一次交互是否重复计费
5. **重开怎么算？** —— Intercom 有 24h 重开扣减规则；Zendesk 的对应规则未在
   本文档中给出

这五问正好映射到 AgentMeasure 的 outcome_class 词表（`resolved` /
`assumed_resolved` / `escalated` / `abandoned` / `reopened`）与结算证据包格式。

## 与 Intercom 的对比

| 维度 | Intercom Fin | Zendesk |
|------|-------------|---------|
| 声称用词 | resolution（分 confirmed / assumed） | **Verified** resolution |
| 验证方 | 客户确认 或 沉默 | **卖方自己的 LLM** |
| 沉默是否计费 | assumed 档（争议焦点） | Contained 档不计费，但 LLM 判定边界不可见 |
| 文档承认的错误路径 | 曾公开撤回定价声明（2025-06） | 文档写明配置错误会多计费 |
| 已知第三方审计 | TareCount、Supportman、Drag | **无** |

**Zendesk 是更大的机会**：声称更强（"verified"）、验证更不可复现（卖方 LLM）、
且**没有任何人发布过 Zendesk 审计**。

## 引用来源

- [About the automated resolutions platform (prior to resolution tiers)](https://support.zendesk.com/hc/en-us/articles/5352026794010) — Zendesk Documentation Team, Aimee Spanier, edited Aug 25 2026
- [About automated resolution tiers](https://support.zendesk.com/hc/en-us/articles/9570369117338) — Zendesk Documentation Team, Erin O'Callaghan, edited Aug 25 2026
- [Announcing changes to AI agent reporting](https://support.zendesk.com/hc/en-us/articles/10677925692698) — Zendesk Documentation Team
- [What happens when I exceed my automated resolutions limit?](https://support.zendesk.com/hc/en-us/articles/9751536041754) — Zendesk Documentation Team
- [Zendesk Relate 2026 press release](https://www.zendesk.com/newsroom/press-releases/relate-2026/) — 双重检查（agent + 独立评估模型）
- [Salesforce signs definitive agreement to acquire Fin](https://www.salesforce.com/news/press-releases/2026/06/15/salesforce-signs-definitive-agreement-to-acquire-fin/)（2026-06-15）— Fin 声称 76% 端到端解决率，按成功 outcome 计费
- [Outcome-Based AI Support Pricing: What Counts as Resolved](https://agentkit.ai/zh-tw/blog/ai-support-pricing-outcomes-not-tickets) — 相邻厂商的内容营销，但独立复述了同一命题，并给出 `false-resolution rate = reopened / bot-resolved` 这一买方自测公式

## 市场规模参照

- Adobe 2026 AI & Digital Trends：78% 的组织预期 18 个月内 agentic AI 处理至少一半客服交互，但只有 **16%** 说 agentic AI 已在组织范围内落地
- Salesforce 2026-06-15 宣布收购 Fin；Fin 约 $400M run-rate 中约 $100M 来自 per-resolution 计费

## Claim boundary

本文只引用 Zendesk 公开文档，不声称 Zendesk 的实现在任何具体客户处出错。
「卖方 LLM 验证」是官方描述，不是本文的推断。配置错误路径是官方文档自己列出的
注意事项。本案例的价值在于：**当一个「已验证」的声称由卖方自己产生时，买方需要
什么才能独立复核**——这是 AgentMeasure 效果审计层要回答的问题。
