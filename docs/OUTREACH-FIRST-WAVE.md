# First-Wave Outreach — External Provider #001

> 目标从 content output 切成 **external implementation acquisition**。
> 漏斗：**10 个真正匹配的 TS Remote MCP Provider → 3 个回复 → 1 个愿意安装
> → 跑 3–7 天 → 输出 Measurement Report #001 → 产生 1 个 Action**。
>
> 成功定义（不是 star、不是 PR）：
> **External Provider #001 接入后，AgentMeasure 告诉了他一件他原来不知道的
> 事实，并且他因此改了产品。**
>
> 纪律：前 10 个 Outreach 全部投 **Pool A**。不追大 logo。

---

## 0. 话术原则（v0.1.1 RC 修订）

**不要说**：

> "We built an open SDK that answers both questions."

Provider-only 拓扑的真实能力边界是：agent 身份可以给到 declared/unknown 分级，
但 **Agent vs human/CI 不能保证 100% 分类**；没有 operation_id / retry_of /
runtime correlation 时，Operation Resolution Coverage 就是 0%——Pipeline
Validation #001 自己证明了这一点。

**要说**：

> "We show you what can actually be known — and, just as importantly, what cannot.
> See what share of your traffic carries an attributable agent identity, what
> remains unknown, and how much of the execution stream can actually be resolved
> into logical operations."

AgentMeasure 的卖点不是"我们什么都知道"，而是
**"我们不会把不知道的事情伪装成知道"**。

**另外**：`@agentmeasure/mcp` 尚未发布到 npm（验证：registry 404）。
**在 npm publish 完成之前，邮件里不要写 `npm install @agentmeasure/mcp`**——
统一用仓库链接。发布后把第 1 封邮件里的安装行换成一行 npm install。

---

## 1. 四个池（只追 Pool A）

### Pool A — Product Alpha（当前唯一 P0）

满足全部条件：**Remote/deployed MCP · TypeScript · maintainer 可触达 ·
有真实流量 · 控制部署 · 能连跑 7 天**。

| # | 项目 | 语言 | 触达方式 | 备注 |
|---|---|---|---|---|
| 1 | [executeautomation/mcp-playwright](https://github.com/executeautomation/mcp-playwright) | TS | GitHub issue / 主页 email | 独立维护者、活跃、TS 栈与 SDK 同构 |
| 2 | [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare) | TS | GitHub issue + 产品团队 | 公司型、公开仓库、云厂商视角 |
| 3 | [mark3labs/mcp-filesystem-server](https://github.com/mark3labs/mcp-filesystem-server) | Go | GitHub issue / email | 小维护者、最容易答应"试试看" |
| 4–10 | 从 awesome-mcp-servers / skills 目录补：TS、独立维护者、活跃、有真实流量 | TS | GitHub issue | 每封引用对方项目一个具体事实 |

### Pool B — Runtime validation（Gate B 用）

Codex / Claude / Cursor / Gemini CLI / DeepSeek Harness 的运行时观察能力边界。
不承担 Product Gate A。

### Pool C — Benchmark / Measurement debate（Benchmark 用）

skills.sh / 官方 MCP registry / 徽章生态（Glama、Smithery…）。
Benchmark Run #001 的 cohort，不是安装目标。

### Pool D — Strategic logos（Gate C 用）

GitHub MCP Server / MCP 官方 servers / Vercel skills。大 logo 的接入需要产品先
被 Pool A 验证，否则拿到 logo 也守不住。

---

## 2. 第一封邮件（按 executeautomation/mcp-playwright 定制，可直接发）

> Subject: A question only your MCP server can answer (agent usage measurement)
>
> Hi <name>,
>
> I've been reading mcp-playwright — 5,600+ stars, and it's the tool I reach for
> whenever I need a browser inside an agent. I'm writing because your server can
> answer a question nobody in the ecosystem can answer today:
>
> **Of the calls hitting your server, how many carry an attributable agent
> identity — and how much of the execution stream can actually be resolved into
> logical operations (vs retries of the same task)?**
>
> We're building AgentMeasure, an open measurement standard for exactly this
> question. Our provider SDK wraps an MCP handler at registration time and emits
> canonical observations — no content captured, nothing on the request critical
> path, caller identity resolved per request (v2 `_meta.clientInfo` / v1 session
> echo). By default everything is labeled `unknown` until evidence upgrades it.
>
> Here's what I'm proposing:
>
> 1. You wrap mcp-playwright with the SDK (or we do it together in a PR you review);
> 2. We run the pipeline on your real traffic for a week (nothing leaves your machine;
>    **Private Alpha** — the report is shared only with you);
> 3. **We tell you one thing about your server's usage that you didn't know** —
>    and, just as importantly, what we *couldn't* know: what share of your traffic
>    stays unidentified, and how much of it can't be resolved into operations with
>    today's lineage. If the numbers come out wrong or the definitions feel broken,
>    that's the most useful feedback we can get.
>
> Everything is open: [github.com/roy-tong/AgentMeasure](https://github.com/roy-tong/AgentMeasure)
> (standard draft 0.4.3, reference implementation, deterministic pipeline validation,
> evidence-profile benchmark of ecosystem claims). The SDK is one install away once
> published — or clone and `cd sdk && npm install` today.
>
> Want to try it? Happy to walk you through the 10 minutes.
>
> — Roy

## 3. 接入模式：Private Alpha 默认，Public 显式 opt-in

第一波 Provider **默认不要要求 public**。真实开发者愿意本地跑数据，但不愿意
第一周就把 usage 公开。

```text
Private Alpha（默认）
→ report 只发给 Provider；数据不出其机器

Public Alpha（显式 opt-in）
→ Provider 同意后，其数字以 Claim Label 形式进入 Benchmark
  （多轴 Evidence Profile，不排名、不评 A/B/C/D）
```

Issue #2 的价值主张同步为两种模式（粘贴文案见 §5）。

## 4. 节奏与纪律

- 每周 5–7 封（不群发；每封引用对方项目的一个具体事实）；
- 每个目标只触达 2 次（首封 + 7 天后一条 follow-up），无回复即换人；
- 回复里无论"好/坏/质疑"都算赢——质疑定义的人是最有价值的第一批贡献者；
- 有人安装后：48h 内给 ta 一份单项目报告草稿（local-analytics 输出 +
  一条对方不知道的发现 + 一条"我们不知道什么"），并问
  **"这个数字哪里不对"**，而不是"你觉得怎么样"；
- 接入后 7 天：产出 **Measurement Report #001**（Private 版先发 Provider，
  公开版仅在其 opt-in 后发布）。

## 5. Issue #2 同步文案（粘贴用）

```text
Two onboarding modes for first-wave providers:

Private Alpha (default): instrument with the SDK, run locally for 3–7 days,
the report is shared only with you. Nothing leaves your machine.

Public Alpha (opt-in): after you've seen your private report, you may opt in
to having your numbers published as a Measurement Claim Label (multi-axis
Evidence Profile — no ranking, no composite scores).

First deliverable: one fact about your server's usage you didn't know —
plus an honest statement of what cannot be known with today's lineage.
```

## 6. 素材包

- 旗舰文章：https://roy-tong.github.io/notes/when-the-software-consumer-becomes-an-agent/
- Pipeline Validation #001：`reports/pipeline-validation-001.md`（确定性 fixture）
- Benchmark Run #001：`reports/benchmark-run-001.md`（Draft 0.3 方法）
- 2 分钟 demo：`./examples/demo-e2e.sh`（隔离 workspace，逐位可复现）
