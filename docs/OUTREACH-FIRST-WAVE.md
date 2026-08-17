# First-Wave Outreach — External Provider #001

> 目标从 content output 切成 **external implementation acquisition**。
> 漏斗：**20 个精准 Provider → 5 个回复 → 3 个安装 → 1 个持续跑**。
>
> 成功定义（不是 star、不是 PR）：
> **External Provider #001 接入后，AgentMeasure 告诉了他一件他原来不知道的
> 事实，并且他因此改了产品。** 这件事一旦发生，AgentMeasure 就从"一个很完整的
> 标准项目"迈进"有实际需求的基础设施项目"。

---

## 1. 目标清单（按优先级）

| # | 项目 | Stars | 语言 | 为什么是它 | 触达方式 |
|---|---|---|---|---|---|
| 1 | [executeautomation/mcp-playwright](https://github.com/executeautomation/mcp-playwright) | 5.6k | TS | 独立维护者、活跃、TS 栈与 SDK 同构、MCP server 本体（Provider 侧） | GitHub issue / 仓库主页 email |
| 2 | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 29k | TS | skills.sh 安装计数正是 Benchmark Run #001 claim 的对象；"agent 使用量"定义之争的震中 | GitHub issue（引用我们的 claim 审计） |
| 3 | [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare) | 4.1k | TS | 公司型、公开仓库、云厂商视角的用量口径 | GitHub issue + 产品团队 |
| 4 | [mark3labs/mcp-filesystem-server](https://github.com/mark3labs/mcp-filesystem-server) | 678 | Go | 小维护者、独立、最容易答应"试试看" | GitHub issue / email |
| 5 | [github/github-mcp-server](https://github.com/github/github-mcp-server) | 32k | Go | 官方 server，若接入则是最强社会证明 | GitHub issue（先观察 issue 文化） |
| 6 | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 89k | TS | 官方参考 servers——让 canonical 观测进官方示例 | GitHub issue / AAIF |

其余 14 个从 cohort 里补：skills 目录上榜者、awesome-mcp-servers 里 TS 且活跃的
独立维护者项目。

## 2. 第一封邮件（已按 executeautomation/mcp-playwright 定制，可直接发）

> Subject: A question only your MCP server can answer (agent usage measurement)
>
> Hi <name>,
>
> I've been reading mcp-playwright — 5,600+ stars, and it's the tool I reach for
> whenever I need a browser inside an agent. I'm writing because your server can
> answer a question nobody in the ecosystem can answer today:
>
> **Of the calls hitting your server, how many come from agents vs CI/curl/tests —
> and how many are retries of the same logical operation?**
>
> We're building AgentMeasure, an open measurement standard for exactly this
> question. Our provider SDK wraps an MCP handler at registration time and emits
> canonical observations — no content captured, nothing on the request critical
> path, caller identity resolved per request (v2 `_meta.clientInfo` / v1 session
> echo), and by default everything is labeled `unknown` until evidence upgrades it.
>
> ```bash
> npm install @agentmeasure/mcp
> server.tool = (name, schema, mw.wrapTool(name, handler))   # v1
> server.registerTool(name, { inputSchema }, mw.wrapTool(...)) # v2
> ```
>
> 10-minute install, local-only, no cloud. Here's what I'm proposing:
>
> 1. You wrap mcp-playwright with the SDK (or we do it together in a PR you review);
> 2. We run the pipeline on your real traffic for a week (nothing leaves your machine);
> 3. **We tell you one thing about your server's usage that you didn't know** —
>    and if the numbers come out wrong or the definitions feel broken, that's the
>    most useful feedback we can get. We'd rather learn where our model breaks than
>    collect stars.
>
> Everything is open: [github.com/roy-tong/AgentMeasure](https://github.com/roy-tong/AgentMeasure)
> (standard draft 0.4.3, reference implementation, pipeline validation report).
>
> Want to try it? Happy to walk you through the 10 minutes.
>
> — Roy

## 3. 通用模板（换掉加粗部分）

```
Hi <name> — you build <server>. Two numbers you probably can't get today:

1. How many of your MCP calls come from agents vs CI/curl/tests?
2. How many of those are retries of the same logical operation?

We built an open SDK that answers both from the provider side without touching
your code paths or content (npm install @agentmeasure/mcp, wrap at registration,
local-only, no cloud). If the numbers come out wrong or the definitions feel
broken, that's the most useful feedback we can get:
https://github.com/roy-tong/AgentMeasure/issues
```

## 4. 节奏与纪律

- 每周 5–7 封（不群发；每封引用对方项目的一个具体事实）；
- 每个目标只触达 2 次（首封 + 7 天后一条 follow-up），无回复即换人；
- 回复里无论"好/坏/质疑"都算赢——质疑定义的人是最有价值的第一批贡献者
  （docs/DISCUSSIONS.md 讨论守则）；
- 有人安装后：48h 内给 ta 一份 Pipeline Validation 风格的单项目报告草稿
  （用 local-analytics 输出 + 一条对方不知道的发现），并问
  **"这个数字哪里不对"**，而不是"你觉得怎么样"。

## 5. 接入后的承诺

1. 对方项目的 claim 进入 Benchmark（多轴 Evidence Profile，不排名、不评 A/B/C/D）；
2. 发现即发布 Discrepancy Report（差异是数据，不是 bug）；
3. 对方对定义的任何挑战优先进入标准讨论（Discussions / proposals AUP）。

## 6. 素材包

- 旗舰文章：https://roy-tong.github.io/notes/when-the-software-consumer-becomes-an-agent/
- Pipeline Validation #001：`reports/pipeline-validation-001.md`
- Benchmark Run #001：`reports/benchmark-run-001.md`
- 2 分钟 demo：`./examples/demo-e2e.sh`
