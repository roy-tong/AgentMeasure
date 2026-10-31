# Verovo

<img src="assets/verovo-logo-card.png" alt="Verovo" width="300">

**算清每项 AI 任务的真实成本，以及业务结果值不值得。**

Verovo 连接买方日志、供应商账单、财务记录和业务结果：先核查费用与交付，再归集直接成本、分摊共享费用，计算单任务成本、成功任务成本和有证据支持的 ROI。

面向采购或运营 AI 服务的业务、工程和财务团队，交付可复算的经济账与待补证清单。主分支已提供本地 `economics` 计算；自动票据解析、流程优化和保险仍是后续方向。[当前能力与技术取舍](docs/feature-status.md)。

<p align="center">
  <img src="assets/launch/hero.svg" alt="Verovo 将收费规则、用量与费用记录、交付证据汇入一次本地买方核验，费用与交付分别给出 PASS / FAIL / UNPROVABLE 结论" width="720">
</p>

[官网](https://roy-tong.github.io/verovo/) · [English](README.md) ·
[产品定义](docs/product-definition.md) · [核验任务指南](docs/buyer-review.md)

## 从费用和交付到单任务经济性

| 任务 | 回答什么 | 支持什么行动 |
|---|---|---|
| **费用核验** | 收费是否符合适用约定，费用与用量能否对应 | 对账、付款、补证、供应商复核 |
| **任务经济性** | 每项任务及每次成功交付花了多少钱 | 成本分摊、价值核算与资源决策 |
| **交付核验** | 实际工作是否达到买方明确的业务要求 | 验收、补救、范围调整、续约 |

两项任务可以分别开展，也可组合。账单没有错误，仍然可以需要交付核验；
交付不达标，也不能自动推定收费违规或应当退款。缺证据保留 **UNPROVABLE（无法判断）**。

核心用户是承担 AI 支出或业务结果的业务、工程和团队负责人，财务与采购协作。
客服是首批应用场景；编程 Agent、自动化平台、工具/API 和模型服务属于长期对象范围，
具体覆盖逐项验证。账本、SDK 和接入工具是能力，POC 是阶段安排。

## 本地运行一次完整核验

新 `review` 命令是 **main 分支预览功能，尚不在 v0.9.0 标签中**。需要 Python 3.9+，无额外运行依赖。

```bash
git clone https://github.com/roy-tong/verovo.git
cd verovo
python3 healthcheck/verovo review --sample --html buyer-review.html --json buyer-review.json
```

合成示例输出：**费用 PASS、交付 FAIL，另一项交付证据 UNPROVABLE**。
打开 HTML 可查看独立结论、判据、观察值、来源与文件摘要。
[查看合成示例报告](https://roy-tong.github.io/verovo/examples/buyer-review.html)。

每份报告附带三层**结论分层**，互相独立、不合并成评分：**Level 1 规则一致性**（本次运行
所能确立的）、**Level 2 证据可信性**（规则适用性、来源真实性与覆盖面——缺失时如实标注
未确立，可选的 `basis.confirmed_by/confirmed_at` 人工确认会被回显计数，绝不推断）、
**Level 3 买方业务裁决**（工具之外，指向 `verovo decisions` 记录）。六个操作阶段
（Intake → Source Check → Rule Resolution → Reconciliation → Delivery Assessment →
Buyer Decision，每步对应一条已发布命令与人工职责）见
[docs/review-method/buyer-review-stages.md](docs/review-method/buyer-review-stages.md)。
Agent 宿主可通过 MCP 只读调用同一核验（`verovo-mcp`：`verovo_review` /
`verovo_review_template` / `verovo_recount`；不暴露任何写入或提交动作）。

自己的任务按照[输入指南](docs/buyer-review.md)准备：明确买方、服务、账户/任务、窗口、决定和负责人，
分别填写收费规则与业务判据，并指定本地 JSON 证据字段。工具比较所提供的判据和记录；
规则是否适用、来源是否可信仍须人工复核，不自动解析任意合同或评价所有 AI 输出。

## 使用已有核账工具

```bash
python3 -m pip install "git+https://github.com/roy-tong/verovo@v0.9.0#subdirectory=healthcheck"
verovo recount --sample
```

截至 2026-10-31，`verovo` 尚未发布到 PyPI。标签安装提供已有命令；新 `review` 功能使用上面的 main 分支。
CLI 与 Provider SDK 独立发布，不共用版本号。

`prepare` 整理支持的导出，`recount` 按选定规则复算，`dispute` 整理差异，
`recovery` 单独记录供应商认可与实际更正。规则估算差额不是已追回金额。

## 当前能力与边界

- **买方核验任务**：本地判据与 JSON 证据比较，费用/交付分列，HTML 与 JSON 输出；main 预览。
- **费用复算**：有限导出格式与具名规则，需要核对合同、配置与账期的适用性。
- **Buyer Ledger**：工具费用处理与 26 项能力目录；目录不等于接通，仍无真实客户账单验收。
- **开发者工具**：本地 Agent 日志诊断、计量与符合性检查，保持独立技术价值。
- **人工企业核验**：按具体任务确认范围和费用，付费与重复采购仍待验证。

[账本说明](buyer-ledger/README.md) · [工程边界](buyer-ledger/REVIEW-20261029.md) ·
[开发者 CLI](healthcheck/README.md) · [路线图](ROADMAP.md)

## 带着具体任务开始

[描述核验任务](https://roy-tong.github.io/verovo/first-look.html#contact)：服务商、账户/任务、
账期或决定日期、可用资料和负责人。交付验收可以独立提出，无需先有费用争议。

免费测量通道 / Free measurement lane：带 20–100 行脱敏数据提交到
[issue #6](https://github.com/roy-tong/verovo/issues/6) 或
[官网表单](https://roy-tong.github.io/verovo/services.html) —
free: bring 20–100 sanitized rows to issue #6 or the website form.

服务商核对上游支出时属于买方；核对下游收费时，仅围绕具体争议、收入差异或采购要求扩展。
现有[免费测量任务](https://roy-tong.github.io/verovo/services.html)保留样本测量范围，
与企业发票、业务验收任务分开。没有统一企业报价或追回保证。

本地命令不会上传数据。可选 GitHub 托管流程会上传至 GitHub，须使用私有仓库。
工程测试、合成示例、开源采用与企业付费分别记录。

发射案例卡（每个数字都标注来源与日期）：
[tokendash #37](docs/launch/case-tokendash-37.md)（一条消息按三条计费）、
[claude-hud #758](docs/launch/case-claude-hud-758.md)（1 小时缓存写入按 5 分钟档计价）、
[VibeMirror-coder-001](docs/launch/case-vibemirror-coder-001.md)
（免费通道的一次独立复测）。索引与分步图：[docs/launch](docs/launch/README.md)。

[CI](https://github.com/roy-tong/verovo/actions/workflows/conformance.yml) ·
[公开证据](https://roy-tong.github.io/verovo/claims.html) · [贡献指南](CONTRIBUTING.md) · [MIT](LICENSE)
