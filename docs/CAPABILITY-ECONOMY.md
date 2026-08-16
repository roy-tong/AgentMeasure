# The Agent Capability Economy — Extended Thesis

> 这是项目 Vision 的展开叙事（非规范性）。README 只保留摘要；
> 规范定义见 `standard/`，经济语义见 `extensions/COMMERCIAL.md`（Experimental）。

## 1. 经济单位在变（增量，不是替代）

```text
SaaS
Human → Application → Seat / Month

API Economy
Software → API → Request / Token

Agent Capability Economy
Agent → Capability → Operation / Outcome
```

**Alongside** seat-based SaaS and request-based APIs, callable capabilities are
emerging as a new economic unit for agent-mediated software consumption. Seats will
not disappear; requests will not disappear; capability/outcome units add a new layer.

## 2. 稀缺性下移

接口（Skill / MCP adapter / CLI）越来越廉价易造；稀缺层是接口背后的访问权：

```text
Data · Compute · Action · Permission · Trust · Real-world fulfillment
```

> **Interfaces may become cheap to create; capabilities remain scarce to deliver.**

## 3. 计量先于变现

CaaS 要能定价、计费与建立声誉，先要有共同的测量语义：

```text
1 user task → 1 Operation → 3 retries：收 1 次还是 3 次？（Metering Policy 决定）
返回成功但 Agent 忽略结果：价值交付了吗？（Consumption / Effect）
预订 API 执行了但从未确认：能力履约了吗？（Effect Confirmation）
任务成功了但没有这个能力也能成功：Provider 能主张价值吗？（Incrementality）
```

**Measurement before monetization** —— 这就是 AgentMeasure 的 wedge。

## 4. 现实证据：商业先于计量到来

- Cloudflare Agents SDK：MCP Tool 按调用定价并经 x402 收费
  （[Charge for MCP tools](https://developers.cloudflare.com/agents/agentic-payments/x402/charge-for-mcp-tools/)）
- Coinbase x402 Bazaar：Agent 搜索带价格/schema 的服务并经 MCP 付费调用
  （[x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar)）
- OpenAI × Stripe Agentic Commerce Protocol（ACP）：真实 agentic commerce 流程
  （[报道](https://www.digitaltransactions.net/openai-and-stripe-are-the-latest-fintechs-to-enable-agentic-commerce/)）

> **Payment and discovery infrastructure is arriving before common capability
> measurement semantics.**

## 5. 从测量到计费（语义链）

```text
Capability → Discover → Choose → Use → Deliver Value → Measure → Meter → Price / Pay / Settle
```

- AgentMeasure 渐进标准化前五步产生的数据与语义（当前已定义：Core usage semantics）
- Metering / commercial attribution 是未来扩展（extensions/COMMERCIAL.md）
- Payment rails 由现有支付基础设施提供

> **AgentMeasure standardizes economic facts, not money movement.**

## 6. 三条线永不耦合

| 线 | 负责 | 文档 |
| --- | --- | --- |
| Core | 测事实 | standard/（规范性） |
| Commercial Extension | 事实 → 经济单位的解释 | extensions/COMMERCIAL.md（实验性） |
| Product | 帮用户获得这些事实 | product/（in development） |
| Payment 系统 | 钱 | 外部 |

**CaaS 是 Vision，不是 Core Standard 成立的必要条件**：AgentMeasure Core 1.0
独立毕业为 Agent 软件测量标准。

## 7. 叙事锁定

- **Today**：让开发者知道 Agent 如何真实使用自己的能力（Remote Capability Analytics）
- **Direction**：让 Capability 可以跨 Agent 被统一度量、比较和计量
- **Vision**：成为 CaaS 与 Agent Capability Economy 的统一计量基础
