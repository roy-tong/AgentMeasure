# AgentMeasure Marketing & Operations Plan（GitHub × X）

> 原则：**Concrete Problem → Real Data → Framework → Capability Economy**。
> 不再传播"我写了一套很完整的标准"；只传播"有一个真实问题 + 一个正在变好的答案"。
> 所有数字必须可追溯到 Measurement Report / pipeline 输出；合成数据必须标注。

## 1. 内容支柱（4 类，循环使用）

| # | 类型 | 钩子 | 素材来源 |
|---|---|---|---|
| C1 | Counter-intuitive fact | **3 Tool Calls ≠ 3 Agent Uses**（Operation/Attempt） | 标准语义 + 反例 |
| C2 | Measurement failure | **你的 MCP 显示 10,000 calls，多少真的是 Agent？**（declared/correlated/unknown） | Caller Identity 分级 |
| C3 | Real case | 接入后发现的真实数字（如 0% strict qualified / 0% operation resolution） | Measurement Report #001（合成流量，须标注） |
| C4 | Thesis | Capability Economy 需要自己的 measurement layer | Whitepaper / docs/CAPABILITY-ECONOMY.md |

## 2. X 执行

- 发布器：`publish_agent/`（CDP 驱动已登录 Chrome，无凭据存储，45-90s 随机间隔）
- 节奏：每 3-5 天 1 条线程；**先发 C2（本计划已执行）→ C1 → C3（真实数据后）→ C4**
- 语言：EN 为主（全球开发者），中文本地化可选（C1/C4 中文版）
- 每条线程结尾：GitHub 链接 + 具体行动召唤（"告诉我们哪里定义不成立" > "求 star"）

## 3. GitHub 执行

| 项 | 状态 | 动作 |
|---|---|---|
| README | ✅ 已就绪 | — |
| Issue Templates（4 类，反例驱动） | ✅ 已就绪 | — |
| Description / Topics / Homepage / Discussions | ⏳ 待 Roy 粘贴 | `GITHUB_LAUNCH.md` 提供精确配置值 |
| 第一份公开 Measurement Report | ✅ #001（本地验证） | 真实外部数据后发 #002 |

## 4. 社区运营（找对的人，不是要 star）

三类目标人群与邀请话术（见下文 outreach 模板）：
1. **Agent runtime / harness 开发者** — 请他们指出 observation 能力边界哪里不成立
2. **MCP / API capability 开发者** — 请他们装 SDK，报告第一个真实数字
3. **Observability / measurement 背景的人** — 请他们 review 定义与 denominator

**运营纪律**：反驳 > star。每个 issue/讨论都是标准演进素材；Measurement
Discrepancy 模板专门收集"数字对不上"的案例。

## 5. 成功指标（4 周）

- GitHub：≥5 issues（其中 ≥1 个外部提交）、≥1 PR、topics/homepage 已配置
- X：每条线程 ≥5 互动；C3（真实数据）发布后观察 DM/mention
- 产品：≥1 个外部 Provider 接入 SDK（Gate A 验收项）
