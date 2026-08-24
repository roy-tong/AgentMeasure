# GTM · 官网枢纽方案（Website-Led GTM v2）

> 状态：官网已上线（`https://roy-tong.github.io/AgentMeasure/`），漏斗末端已打通
> 一键申请（`5-provider-trial.yml` 模板）。本文档把官网接进**全部**获客与承接动作。
>
> 前置文档，仍然有效：
> [OUTREACH-STRATEGY](OUTREACH-STRATEGY.md)（分池 / 话术原型 / 节奏）、
> [OUTREACH-FIRST-WAVE](OUTREACH-FIRST-WAVE.md)（Pool A 名单 / 首封邮件）、
> [MARKETING](MARKETING.md)（内容支柱 C1–C4）。
> 本文只补它们没覆盖的部分：**官网作为枢纽的漏斗、上线清单、发布动作、
> 承接 Runbook、我们自己的度量**。

## 0. 一句话

**所有外部触点指向官网；官网站回答六个问题并收口到一键申请；私有运营区负责承接与交付。**

上一个阶段的问题是"材料分散"：旗舰文章讲叙事、README 讲工程、Issue #2 讲合作，
彼此不通。现在官网把这六层按漏斗顺序排完了（Why → Claims → Model → How →
Available → Try → Trial → Standard/Lab/Thesis），每个入口都只需要一个链接。

## 1. 官网在漏斗里的角色

| 漏斗问题 | 官网哪屏回答 | 转化事件 | 我们能看到的信号 |
|---|---|---|---|
| Do I understand the problem? | 01 Why（The software consumer changed） | 继续下滑 | 无——接受不测 |
| Why is this different? | 02 Claims（≠ 链）+ 04 品类句* | 继续下滑 | 无——接受不测 |
| Do I believe it exists? | 03 Measurement Model + 05 Available today + 06 proofs | 点 GitHub | GitHub traffic API：views / referrers |
| Can I try it? | Hero "Run the 2-minute demo" + 08 Try it | clone 仓库 | GitHub clones（14 天窗口） |
| What's in it for me? | 07 Trial（Retry inflation / Execution economics / Traffic quality） | 打开申请表 | 测不到——接受不测 |
| Can I start with one click? | 07 CTA → issue 模板 | **提交申请 issue** | issues（可数，硬信号） |

\* 04 的品类句："Telemetry records events. AgentMeasure defines what those
events mean." —— 这是回答"你跟 Langfuse / OTel 什么区别"的标准答案，
外联邮件 B 型（已有 telemetry 的 Provider）直接引用它。

**品牌一致性测量原则**：官网**不装第三方 tracker**（GA / Hotjar 与产品
"Data stays local" 的承诺直接冲突）。可用信号全部来自一方：GitHub traffic
API、issues、私有运营区记录。测不到的（demo 本地运行、模板打开率）如实列为
unmeasured——**我们卖的就是"不把不知道伪装成知道"，量自己时同一个纪律。**

## 2. 上线前清单（Launch Checklist，半天内完成）

- [ ] GitHub 仓库建 label：`provider-trial`（模板引用了它；不建不报错，但不打标）
- [ ] Repo **About**：Website 改为 `https://roy-tong.github.io/AgentMeasure/`；
      Description 换成与官网统一的
      `Open measurement infrastructure for agent-facing software. Separate operations from attempts, evidence from inference, and usage from value.`
      （粘贴块已更新进 [GITHUB_LAUNCH.md](../GITHUB_LAUNCH.md)）
- [ ] push 本轮 website 改动 → 确认 Pages Actions 部署成功；
      手测 `og:image`（social-preview.png）线上可访问
- [ ] push [ISSUE-2.md](ISSUE-2.md)（已加一键申请行）→ issue-sync workflow 同步
- [ ] README 首屏 "Free 7-day audit — apply" 链接已改为申请模板（本轮已改）
- [ ] X 账号置顶换为官网链接（原来是旗舰文章；文章保留在官网 Story 入口）

**验收**：从 X / HN / 直邮三个入口分别点入，都能在 **3 次点击内**到达申请表。

## 3. 流量策略（按当前阶段 ROI 排序）

### 3.1 Pool A 直邮（仍是 P0）

唯一能可控产出 Report #001 的通道，节奏不变（每周 5–8 封、每目标最多 2 次触达、
concierge 代做 PR）。唯一变化：邮件里 GitHub 链接前加官网链接——
"想先自己看的话，10 分钟的入口在这里"。开发者先读官网再读代码，转化路径更短。

### 3.2 Launch 帖（放大器，一次性）

| 渠道 | 钩子 | 注意 |
|---|---|---|
| **Show HN** | "Show HN: AgentMeasure – Open measurement semantics for agent-facing software" | 首评讲故事：codex 上第一次预注册实验 +25pp、p=0.285、**我们报了 null**。HN 惩罚营销腔，奖励"我做了个东西 + 这是它做不到的" |
| **X 线程** | C1："3 tool calls ≠ 3 agent uses"（1 intent / 2 attempts / 1 operation） | 结尾 GitHub + 官网双链接；CTA 用"告诉我们哪里定义不成立" |
| **r/mcp · r/LocalLLaMA** | 提问式："你的 MCP 显示 10k calls，多少是重试？" | 以评论参与为主，链接放 profile / 相关回复；先读各版 self-promo 规则 |
| **V2EX / Linux.do**（可选，中文） | 求锤贴："我们连自己的 +25pp 都判了 null，来挑战我们的定义" | 社区吃"诚实到自残"这一套；准备好被挑刺并逐条回应 |

Launch 周连发（周二 HN 早晨美东、X 同日晚 2h、Reddit 次日），之后回落到
MARKETING.md 的 C1–C4 循环（每 3–5 天一条），**所有内容的落地页从旗舰文章
逐步换成官网**（文章保留，作为 Story 层入口）。

### 3.3 不做（当前阶段 ROI 为负）

SEO 关键词页面、付费投放、目录站批量提交、"顶级 MCP 工具榜"投稿。

## 4. 承接 Runbook（模板提交进来之后）

| 时点 | 动作 | 交付物 |
|---|---|---|
| T+0（SLA 24h） | 回复 issue：确认收到 + 约半小时通话（或纯异步） | 一条人话回复，不是模板感谢 |
| T+0 | 30 分钟集成：wrap 工具处理器（**可以我们代做 PR**） | 合入的 SDK 包装 |
| T+1–3 | 真实流量积累，数据全在对方机器 | 无——明确告诉对方"这一步我们看不到任何东西" |
| T+4 | 预览发现（AUDIT.md 流程）：方法不适用就地终止 | 一页预览 |
| T+7 | **Measurement Report #001**（Private）+ 45 分钟 review | 报告 + 第一个问题问 **"这个数字哪里不对"**（不是"你觉得怎么样"） |
| T+7 后 | 行动菜单 → 对方选一项 → 同口径复测 7 天 | before / after |

纪律不变：Private 默认（公开需显式 opt-in）；报告编号预留 Measurement
Report #001 给第一个外部 Provider；每个 Provider 无论"好/坏/质疑"都进证据账本。

## 5. 商业层时点（什么时候谈钱）

当前官网**不放价格**，是对的。价格进入对话的触发条件：

1. **申请与集成阶段**：不谈。免费的是方法校准，不是永久免费。
2. **Report #001 交付、对方确认数字有用之后**：从第二家起报
   **Founding Audit $1,500**（话术："第一家的投入免费，因为它定义了方法"）。
3. **3 个 trial 走完、≥1 个 actionability case 后**：官网加 `/audit` 价格页；
   对达门槛客户提 **Verified Lift $15–30K/轮**。
4. 门槛判断照 BP v4.2：年渠道毛利 ≥ $1M / 月机会 ≥ 500 万 / 单次毛利 ≥ $0.10；
   不达标的只做诊断档，或直接说"你这个品类撑不起这个项目"。

## 6. 我们怎么量自己（Weekly Review，周一 30 分钟）

| 指标 | 定义 | 来源 | 当前目标 |
|---|---|---|---|
| Template 提交 | `provider-trial` issue 数 | GitHub issues | Launch 周 ≥ 3 |
| 集成完成 | SDK wrap 合入并开始跑 | 私有运营区 log | Launch 周 ≥ 2 |
| 7 天跑完 → 报告 | Report 交付数 | reports/ 编号 | 30 天 = 1（Report #001） |
| Actionability | 对方因报告改了产品 | 证据账本新 EVID 条目 | 60 天 ≥ 1 |
| GitHub views / clones / referrers | 仓库流量与来源 | traffic API（周三拉） | 只看趋势，不设 KPI |
| Site visits / 模板打开率 | **不测**（无 tracker，品牌决定） | — | — |

规则：数字进私有运营区（`publish_agent/outreach/` 周报），结论进证据账本；
**凡是测不到的，表里写 unmeasured，不估。**

## 7. 90 天里程碑

| 周 | 里程碑 |
|---|---|
| W1 | 上线清单完成；第二批 Pool A 直邮 5–8 封发出 |
| W2 | Launch（HN / X / Reddit）；首批模板提交；concierge 开始 |
| W3–4 | Provider #001 集成 → 7 天 → **Report #001**（Private） |
| W5–6 | Actionability case 落地；（opt-in 则）公开 writeup；Provider #2/#3 启动 |
| W7–9 | **首单 Founding Audit $1,500**；三池名单复评（OUTREACH-STRATEGY §2） |
| W10–12 | `/audit` 价格页决策；status.json 接 CI（release + 测试数自动生成）；BP 数据回填 |

## 8. 纪律（与产品同一套）

不展示虚构 logo；合成数据必须标注；null 是一等结论；Private 默认；
每目标最多 2 次触达；**量自己的漏斗时，和量别人的渠道用同一条纪律——
不知道就写不知道。**
