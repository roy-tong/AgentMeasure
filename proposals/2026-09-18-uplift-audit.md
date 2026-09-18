# Proposal 2026-09-18 — 增量审计（Uplift Audit）：从「什么算一次」到「增量可证明」

- 状态：Draft
- 作者：Roy Tong
- 日期：2026-09-18
- 相关：AgentMeasure Core Draft 0.4 / METRICS M5（新增）/ QUALITY §4 billable_audit / TRUST §3 / extensions/COMMERCIAL §3–5 / whitepaper §8.1 / DR-005

## 问题

按结果收费已是规模化生意（Zendesk $1.50/resolution、Intercom Fin $0.99 附退款担保、Sierra 企业级 outcome 合同），但**「效果是不是增量」没有标准**。AgentMeasure 当前回答的是「什么算一次、结果可不可证明」（usage 语义一致性，PASS / FAIL / UNPROVABLE）；效果费结算还差一层：**效果费能不能收上来，取决于增量能不能被审计——合作方不会为「我们觉得有效」付钱。**

具体缺口（每条配反例）：

1. **Effect / Outcome 在标准中只有一行定义**。CORE §2.4：`Result / Effect = 执行产生的返回值 / 世界状态改变`——无对象、无状态机、无 payload。反例：COMMERCIAL §3 的 billable event 表已引用 `effect_confirmed` / `outcome_qualified`，且纪律要求「quantity MUST 可追溯到已发布的测量事实」——但该测量事实在标准中**不存在**，是悬空引用。
2. **无 outcome 分类词表，沉默无法与解决区分**。反例：Intercom 的 "assumed resolution"（静默即视为解决）在社区引发持续反弹；有客户被承诺 70% resolution rate 实际拿到 30%。当前 spec 无法表达「resolved / assumed_resolved / reopened / abandoned」的区分，也无注册的 billable unit 定义。
3. **重开不回滚账单**。反例：工单被标记解决并计费，3 天后重开——一次逻辑解决变成一次收费 + 一次失败。usage 侧我们有 retry 语义（一次逻辑操作 ≠ 两次请求），outcome 侧同构纪律缺失（reopened ≠ resolved 已写在 blog，未进 spec）。
4. **归因冒充增量**。反例：厂商宣称「AI 解决了 70% 工单」，其中 30% 不用 AI 也会经自助文档解决——不变量 14（归因不得陈述为因果）已存在，但没有证据等级机制去执行。whitepaper §8.1 的 V0–V4 证据阶梯停留在论文层，TRUST §3 的 Evidence Profile 五轴无因果轴。
5. **增量指标无合同**。METRICS §6 显式留白「Incremental Lift（实验设计见 AgentMeasure 0.5）」；registry/metrics.yaml 止于 M4.1。无 Numerator/Denominator/Eligibility/反例，两个实现可以算出两个数。

## 提案

五件套，全部复用既有模式（AUP + schema + conformance vector 三件套、Lab 引擎、bundles 证据包）。

### 1. Effect Confirmation 对象与状态机（CORE §2.4 展开）

新语义对象 **Effect Confirmation**：对「一次 Effect 发生且成立」的带证据判定。

- 状态机：`confirmed → disputed → reversed`；`unconfirmed` 为初始态。**reversed 必须可追溯到 confirmed 记录**（对应重开：resolution 计费后重开 → reversal，而非静默删除）。
- 观察方分级（复用 TRUST §3 C0–C1 佐证轴）：self-attested（执行方自证）< affected-party（受影响方确认，如客户回复/工单系统状态）< third-party-corroborated。状态与观察方分级**成对披露**。
- 稳定窗纪律：confirmed 需存活 `stability_window`（默认建议 72h，垂直 profile 可覆盖）方为 settlement-grade；COMMERCIAL §5 的 `minimum_resolution` 语义并轨到此处，消除双重定义。
- 新 payload：`schemas/payloads/effect-confirmed.schema.json`（effect_id / operation_id / outcome_class / observer_grade / stability_window / reversal_of?）。

### 2. Outcome Classification 词表 + 可计费单位注册（registry/）

- `registry/vocabularies.yaml` 新增 `outcome_class` 词表：`resolved / assumed_resolved / escalated / abandoned / reopened / not_outcome`。**沉默 ≠ 解决**：`assumed_resolved` 是合法类目但**不得**聚合进 `resolved`（同 invariant 16 精神：不同 grain 不可互换）。
- `registry/` 新增 **Billable Unit 注册表**：per-resolution 场景的「resolution」作为单位注册，挂靠 outcome_class + qualification 规则 + 稳定窗。厂商价差 4 倍（$0.50–$2.00）说明「一次 resolution 值多少钱」无共识——先把**单位**统一，价格留给市场。
- 分层（stratification）：`task_outcome` payload v2 增加 `outcome_class` 与轻量归因字段（capability_ids + primary_operation_id），使「5 分钟解决」与「3 天两次重开」不可互换混算。

### 3. M5 Incremental Lift 指标合同（METRICS + registry/metrics.yaml）

按 METRICS Contract 模板：

| 项 | 内容 |
|---|---|
| 名称 | M5 Incremental Outcome Lift |
| 公式 | `P(outcome_qualified | capability) − P(outcome_qualified | counterfactual arm)`，按条件（harness × task distribution）报告；汇总值必须与分条件值并列披露 |
| Grain | Outcome（Task 级） |
| Eligibility | 仅当反事实面存在（V2 ablation / V4 holdout，见第 4 节）；无反事实面 → **UNPROVABLE**，不输出点估计 |
| 证据要求 | 主指标必须预注册（Lab FMT-001 机制）；生产复测走 calibrate 口径（production_confirmed / direction_mismatch / …） |
| 反例 | ① 跨异质任务分布的合并 lift（掩盖方向相反的分条件效应）；② 无 holdout 的面板前后差分冒充 lift；③ guardrail 违例仍上报 significant（Lab 已拦截为 `effective_not_qualified`，进标准） |
| 计费含义 | M5 = UNPROVABLE 时：**不可按效果计费，但可回退按发生计费（operation）**——分档 billing basis，绝不「计为零」 |

### 4. 主张—证据匹配规则（V-ladder 进标准，PASS/FAIL/UNPROVABLE 延伸到因果主张）

- TRUST §3 Evidence Profile 增加**因果轴**：`V0 association / V1 matched-observational / V2 offline-ablation / V3 quasi-experiment / V4 randomized-holdout`（取值与定义直接引自 whitepaper §8.1，DR-005 的 State 1/State 2 为其在消费语义上的先例）。
- QUALITY §6 可说/不可说表增加因果行：**主张强度 ≤ 证据等级**方可宣称（PASS）；观测性归因陈述为因果增量 = FAIL（不变量 14 的可执行化）；direction_mismatch / unverified_growth = FAIL；无反事实面 = UNPROVABLE。
- COMMERCIAL §5 `billing_requirements` 新增 predicate：`incrementality_evidence: none | v2_ablation | v4_holdout`。`billing_basis: outcome` 的账单行必须携带该字段；为 `none` 时账单行降档为 operation 计费或标记待裁决——**UNPROVABLE 在效果费场景的经济含义是「不可计费」，不是「计为零」**，与 conformance pack 的 `--require`（UNPROVABLE 可被合同方升级为 blocking）天然衔接。

### 5. OUT- 检查家族 + 结算证据包（conformance + bundles）

新 conformance 家族（向量遵循 urusilla-001 三件套模式：事件 + 期望 + 映射）：

| 编号 | 检查 | FAIL 反例 |
|---|---|---|
| OUT-001 | Outcome 可判定性：计费声明的 outcome 单位有注册定义且事件可映射到 outcome_class | 「resolution」无注册定义即计费 |
| OUT-002 | Effect confirmation 可追溯：每笔 effect 类账单行可追溯至带观察方分级与稳定窗的 confirmation 记录 | quantity 无法回溯到测量事实 |
| OUT-003 | 重开/重复去重：同一 task 的 outcome 不产生两次计费单元；reversed 必须链接原 confirmation | resume/fork 后 86% token 消失的 outcome 版；重开再计费 |
| OUT-004 | 主张—证据匹配：`billing_basis: outcome` 而无 `incrementality_evidence` → FAIL；有证据但主张超等级 → FAIL | assumed_resolved 按 resolved 计费 |

**结算证据包（Settlement Evidence Bundle）**：复用 bundles/ 四件套 + CI 重算模式（`live-codex-desc-clarity-001` 先例），组合：metering policy 版本 + 达到 minimum_resolution 的证明 + incrementality V 等级 + calibrate 状态 + 分条件 M5 表 + 双语一页决策版（Lab 已有模板）。这是「合作方不会为『我们觉得有效』付钱」的直接回答物。

### 分期

- **P1（0.4.x，立即可做，不动指标）**：outcome_class 词表、effect-confirmed payload、task_outcome v2、OUT-001..003 向量。
- **P2（0.5，随 Utility & Economic Semantics）**：M5 合同、因果轴进 TRUST/QUALITY、`incrementality_evidence` predicate、OUT-004。
- **P3（0.6 / COMMERCIAL 转正前）**：Billable Unit 注册表、结算证据包 schema、《Metering 对账报告》格式（COMMERCIAL §9 已预告）。

## 影响

- standard/：CORE（§2.4 展开、§9 新不变量：reversed 可追溯、assumed_resolved 不得并入 resolved）、METRICS（M5）、QUALITY（§6 因果行、billable_audit 更新）、TRUST（因果轴）、COMMERCIAL（predicate、单位注册）
- schemas/registry：effect-confirmed payload、task-outcome v2、vocabularies、metrics.yaml、billable-unit 注册表
- conformance：OUT 家族 4 检查 + 向量集
- lab：引擎已具备（预注册/功效/校准/guardrail 拦截），需做 M5 指标实现与 CORE-MAPPING 增补
- 报告生态：结算证据包模板 + 首个公开案例（目标：AI 客服垂直，对齐 outcome-yardstick 博文的四缺口）

## 备选方案

- **否定：增量审计只做在商业层、不进标准。** 后果：各家「经核验解决率」自成口径、不可比，重蹈 benchmark-run-001 记录的自我报告覆辙；标准失去第一个付费场景的锚点。
- **否定：要求一切效果计费必须 RCT（V4）。** 一刀切会把大多数真实合同挡在门外；V2 ablation / V3 准实验可支撑较弱主张——阶梯与主张强度匹配，而不是与理想实验匹配。
- **否定：引入通用因果推断形式体系（do-calculus 等）。** 超出计量标准职责；只规范化**证据等级与主张边界**，推断方法留给实现。

## 开放问题

1. 反事实证据的出具方：provider 自证 / 买方 holdout / 第三方——是否映射 TRUST independence I0–I2 作为信任等级？
2. stability_window 默认值（72h? 7d?）与垂直 profile 的覆盖机制。
3. M5 分条件报告的最小样本与「不可合并」的边界（何时允许池化）。
4. 双边/多边结算的证据交换格式（connector 目前只覆盖单侧聚合导出；G0 数据权延伸）。
5. `assumed_resolved` 在买方明确同意的合同里是否可作为降档计费单位（类似 operation 回退）？
