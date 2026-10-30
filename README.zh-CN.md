# Verovo

<p align="left"><img src="assets/verovo-logo-card.png" alt="Verovo" width="300"></p>


**帮助企业核验 AI 服务的费用与交付，为对账、验收和续约提供可复核的依据。**

> **2026-10-30 状态**：已更名为 Verovo（CLI 0.9.0 已在 GitHub 打标签；PyPI 项目
> `verovo` 尚未首次发布）。买方账本为 pre-M1：106 项测试在合成数据上通过，尚无真实
> 平台账单验证。

从按结果收费的 AI 客服买方切入，把适用收费规则、事件记录与业务要求对应起来。
当前开源 CLI 支持有限规则下的计费导出复算、差异整理与后续处理记录。
更广泛的买方核验服务正在逐案验证，不是通用合同解析或自动质量验收平台。
本地 CLI 不上传数据。

| 你的任务 | 入口 |
|---|---|
| 一项具体的 AI 客服账单疑问 | [描述任务、确认适配](https://roy-tong.github.io/verovo/first-look.html#contact)，也可运行下方免费复算 |
| 即将作出验收或续约决定 | [说明决策与证据需求](https://roy-tong.github.io/verovo/first-look.html)，项目范围逐案验证 |
| 本地日志异常或一个计量样本 | [免费测量任务](https://roy-tong.github.io/verovo/services.html)：带脱敏样本来跑 |
| 贡献规则、反例或适配 | [维护者入口](#维护者与服务提供商入口) |

[官网](https://roy-tong.github.io/verovo/) · [English](README.md) · [Healthcheck 指南](healthcheck/README.md) · [发布说明](https://roy-tong.github.io/verovo/releases.html)

## 两种核验，对应不同动作

- **收费是否符合适用约定？** 有依据的差异可以用于供应商复核，发现差异不等于对方认可或已退款。
- **交付是否满足业务要求？** 结论可以支持验收、补救或续约；买方更严格的要求不自动构成收费错误。

客服运营提供业务事实，财务或采购负责费用决策。报告区分双向发现、证据缺口、
供应商接受与实际退款/已使用抵扣；缺失证据保持未知。

自 2026-10-21 起项目全面免费开源——付费诊断与商业收费探索均已停止。
免费测量任务不包含企业发票或业务交付核验。

详见[任务与产品边界](docs/product-scope.md)、[商业与开源合作口径](docs/commercial-narrative.md)。

## 60 秒复算一张账单

把这五行样例存成 `export.csv`（数据是合成的，命令是真的）：

```csv
conversation_id,human_agent_participated,issue_addressed,customer_recontacted_within_window,vendor_billed
c-001,N,Y,N,Y
c-002,N,Y,N,Y
c-003,N,Y,N,Y
c-004,Y,Y,N,Y
c-005,N,Y,Y,Y
```

```bash
# 0.9.0 已在 GitHub 打标签；PyPI 项目 `verovo` 尚未首次发布。
pip install "git+https://github.com/roy-tong/verovo@v0.9.0#subdirectory=healthcheck"
# 发布后：pip install verovo
verovo recount --export export.csv --vendor zendesk
```

输出先是厂商规则及其公开出处，然后是双向核对结果，最后是钱数：

```
Dollars (at USD 2.0 per resolution)
overcharge identified       2.00
undercharge (vendor favour) 0.00
net variance                2.00
```

CLI 0.8.0 可直接运行 `verovo recount --sample`，使用相同的内置合成导出。
样例有4行不可判定；$8不能叫已核实应付金额，$2是按规则计价的发现，不是已追回款。

三个可复现 showcase 案例（拒绝猜测的超收判定 / 双向核对 / 合同航道）在
[examples/showcase](examples/showcase/README.md)，期望输出已冻结、CI 每次
变更都会比对，展示与现实不会悄悄分叉。

## 核对国内外 Agent 工具账单（研究预览）

Buyer Ledger 把同一套证据纪律扩展到 Agent 工具支出：模型 Token、搜索次数、
credits、浏览器小时、沙箱秒数、OCR 页数、语音字符、生成内容数量和席位。
产品区分账单事实、平台用量和按规则复算；一个工具出现在表里，不代表已接通
或已通过真实账单验证。

- **买家视角**：核对平台代收、直接 API、云市场账单，以及免费额度、预付包、
  credits 和第三方现金支出。
- **卖家视角**：检查实际计量用量是否进入计费；未计价或未关联用量只作为
  证据缺口，不直接宣称漏收收入。
- **能力目录**：26 个国内外工具，记录计费模型、计量单位、账单来源、审计能力
  和验证状态。见 [catalog/tools.json](buyer-ledger/catalog/tools.json)。
- **无 API 的账单后台**：附着用户自行启动的 Chrome 本地 CDP，重放受审配方、
  下载账单并进入同一审计管线；系统不接收密码。
- **边界**：当前是“已编目”，不是实时接通；尚无工具完成真实客户账单验证。
  通用 CSV/TSV 与 CDP 管线只有合成 fixture 测试。见
  [Buyer Ledger](buyer-ledger/README.md) 和
  [审查边界](buyer-ledger/REVIEW-20261029.md)。
- **账单不满证据（探索性）**：SURE 1.6 研究从 1,949 条公开发现中审读 150 条，
  得到 **66 条严格证据**；credits 到期、未预期扣费、自动充值和计量不一致是
  主线，涨价仅 2/66。审计 12 门中 3 门未过（仅 3/18 家 vendor、单一地区、
  反证 7 条），不能表述为发生率或市场验证。见
  [边界摘要](buyer-ledger/COMPLAINTS-20261029.md)。
- **CDP discovery 第一阶段**：本地 Chrome CDP 采集 2,734 条公开讨论，分层得到
  **2,437 条可用 discovery**（1,708 条 direct vendor、729 条泛 AI/API 账单），
  另登记 26 个官方计费页；这是发现层，不是严格证据或客户账单。
- **SURE 50,000 发现扩展**：去重后 **50,000 条**公开记录，HN 49,090 条；严格
  证据仍 66、审读仍 150，主审计仍 9/12、exploratory。50,000 条不是 50,000
  名用户，也不是 50,000 条证据。
- **H1–H5 压力测试**：H1 证据形状支持（人工 core 率 credits 30% vs price 6%），
  但提及量接近；H2 不支持（HN 内方向反转）；H3 仅支持英文源不可见；H4 关键词
  初筛降级率 **71.6%**；H5 仅提示。没有假设升级为 validated。

```bash
python3 -m buyer_ledger catalog summary
python3 -m buyer_ledger catalog list --region cn --role buyer
python3 -m buyer_ledger catalog coverage --period 2026-10
python3 -m buyer_ledger report --period 2026-10 --perspective seller --out seller.md
python3 -m buyer_ledger fetch --recipe recipe.json --period 2026-10 \
  --cdp http://127.0.0.1:9222
```

支持矩阵与案例：[website/tools.html](website/tools.html)；
GitHub Pages 部署后由官网路径提供。

## 按账期重复核对

希望数据只留本地，可对每期新导出运行CLI。可选的[GitHub Actions工作流](RECONCILE.md)
要求独立私有仓库，并将数据和报告上传GitHub；公开仓库的fork不是私有存储。
每期必须准备新的、经过核对的导出，工作流不会自动向厂商拉取数据。

今天内置六家厂商规则——Intercom Fin、Zendesk AI Agents、HubSpot Breeze、
Salesforce Agentforce、Ada，以及一个通用按结果基线——每条规则都注明出处
与置信级（`verovo recount --list-vendors`）。复算与账单对不上时：
`verovo prepare` 把 Intercom/Zendesk 原生导出对齐到规范列，
`verovo dispute` 生成争议与追回包，`verovo recovery` 单独记录
厂商实际让步了什么，不与索赔混计。

复算是算术，不是裁决：证据不足的行进 `cannot settle`、从索赔中剔除而不是
记零；“查无差异”是有效结果。厂商账单复算是免费 CLI 能力，不是下面两项
付费服务。

## 先查自己（免费）

`verovo check` 检查本地 Codex / Claude Code 会话的重复记录、重试放大
与 Token 异常——同一套证据纪律，指向你自己的日志。`verovo demo`
跑内置合成样例，无需账号、不上传。缺失证据保留为未知；一次重试不自动算作
一个新的逻辑操作。

Python 3.9+。2026-10-15 核验：[PyPI CLI](https://pypi.org/project/verovo/) 为 **0.8.0**，
[npm SDK](https://www.npmjs.com/package/@verovo/mcp) 为 **0.2.0**；两者独立版本。
macOS/Linux 可使用 `python3 -m pip`，Windows 可使用 `py -m pip`。遇到权限或
externally managed 错误，按[虚拟环境步骤](https://roy-tong.github.io/verovo/#install-help)安装。
同时有两种运行时日志时默认优先 Codex；Claude Code 用
`verovo check --runtime claude`。最近七天没有日志可试 `--all`，或指定
`--dir` 与 `--runtime`。输入缺失不代表检查通过。

## 免费测量任务

工具本身免费、本地运行。如果你希望有人在你自己的数据上跑一次测量检查，同样免费：
带上 20–100 行脱敏样本（或公开导出），我们出测量检查——干净样本起通常 48 小时内交付。
结论一律写成可核验的主张；你的面看不见的地方，报告写 UNPROVABLE，不猜。

我们的请求（完全自愿）：允许把脱敏 fixture 以你的署名入仓，边界由你声明
（synthetic 或 production 你说了算，逐字保留；不含任何可识别客户的信息，哈希或删除）。
如果这次检查对你有用，给仓库一个 star 能帮更多人找到它——完全自愿，不设任何前提。

- 入口：[issue #6](https://github.com/roy-tong/verovo/issues/6)（公开线程，下一位读者能看到你的那次运行），或邮件 tongroy18@gmail.com
- 指南：[docs/provider-onboarding.md]
- 自己跑同样的检查：[docs/review-method/](docs/review-method/README.md)——免费任务背后的收单判定、映射、命令与报告模板全公开(docs/provider-onboarding.md)——三条进入路径、五个步骤、什么算一次成功运行

原有的 $10/$20 付费诊断已于 2026-10-21 下线；项目现在完全免费开源。

本地准备摘要：

```bash
verovo check --json report.json
verovo share report.json --out summary.json
verovo validate summary.json
```

`--out` 会立即写入本地文件，发送前自行检查，不会自动上传。"未发现问题"与"证据不足"
都是有效结论。工具缺陷可免费在 [Issues](https://github.com/roy-tong/verovo/issues/new)
提交脱敏复现。

## 维护者与服务提供商入口

| 资料 | 用途 |
|---|---|
| [Conformance pack](conformance/pack/README.md) | 对样本和上报指标给出 PASS / FAIL / UNPROVABLE |
| [Provider SDK](sdk/README.md) | 采集 MCP 工具调用的规范观测：`npm install @verovo/mcp` |
| [Core](standard/CORE.md) 与 [VSS-1](standard/SETTLEMENT.md) | 定义计量粒度、结论及证据要求 |
| [公开发现索引](https://roy-tong.github.io/verovo/claims.html) | 逐条查看日期、复现证据与上游回应 |
| [Lab](lab/README.md) | 已有实验工具，不承诺托管产品 |

上文买方工具（`recount` / `prepare` / `dispute` / `recovery`）共用一份[端到端走查](https://roy-tong.github.io/verovo/first-look.html)。它们是免费 CLI 能力，不属于当前两项固定价服务。当前开发取舍见[路线图](ROADMAP.md)。

## 证据与验证进度

[9 月审计报告](campaigns/audit-report-2026-09.md)记录了 110 个工具的审查；后续修复与纠错以公开发现索引为准。技术成果不能替代付费需求、客户节省或退款依据。实际用户价值和复购仍在验证。

2026-10-15 本地 511 项 Healthcheck 单元测试通过。最新工程结果见 [CI](https://github.com/roy-tong/verovo/actions/workflows/conformance.yml)，发布范围见 [v0.8.0](https://github.com/roy-tong/verovo/releases/tag/v0.8.0)。合成夹具不是客户生产数据。

## 开源承诺

- MIT 工具和规则保持免费；付费不改变判定。
- 分析在本地运行；分享脱敏样本由用户主动决定。
- 不卖排名、推荐位，不托管支付资金。

[贡献指南](CONTRIBUTING.md) · [安全](SECURITY.md) · [治理](GOVERNANCE.md) · [Agent 指令](AGENTS.md) · [中文白皮书](whitepaper/measuring-software-used-by-ai-agents.zh-CN.md)

[开发者详细指南](docs/developer-guide.zh-CN.md)

## Claude跨文件响应证据

`verovo response-audit first.jsonl fork.jsonl --json responses.json` 按响应标识对照重复用量快照、冲突与缺字段。只读，不改日志，不选取first/last/max，不计算会话或账单总额。见[使用说明](docs/response-audit.md)。

## 为什么免费？

免费不止是自助：你带样本，我们人工跑检查，同样不收费——项目在做的是开放计量行为语料，一次带边界声明的真实运行就是最好的贡献。工具、公开病例、排查说明与测量检查全部免费；原付费选项已于 2026-10-21 下线。
