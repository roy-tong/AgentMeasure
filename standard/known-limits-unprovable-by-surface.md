# Known Limit: UNPROVABLE-by-surface

> 标准文档 revision 0.4.4 增补
> 识别：2026-09（经 OpenTelemetry .NET SDK 维护者 lmolkova 在架构讨论中指出。
> 确认：span-layer 重试盲区是原则性约束，不是可 instrument 的缺口。）

## 1. 定义

**UNPROVABLE-by-surface** 是指测量表层（instrumentation surface）无法观察到
某个测量事实，且该事实不可通过推断获得。这是**设计输出**，不是未实现的特性。

关键区别（与「下次修复」的区别）：

| 状态 | 含义 | 后续动作 |
|------|------|----------|
| Not Yet Implemented | 我们知道怎么测，但还没做 | 推入 roadmap |
| **UNPROVABLE-by-surface** | 当前测量拓扑原则上无法观察到这个事实 | 不修复。可通过扩大 measurement surface 缩小 scope |
| Unobservable ≠ False | 我们知道自己不知道，且不会将此状态归入 FALSE | 已编码为不变量 17 |

## 2. 不可见性来源（by 拓扑）

| 拓扑 | 不可见来源 | 典型 UNPROVABLE 对象 |
|------|-----------|---------------------|
| **Provider-only**（仅 API 日志 / 无 instrumentation） | 无任何 agent 侧事件可见 | operation 解析（M3.1=0）、attempt 粒度、choice 事件 |
| **Span-based OTel**（OpenLIT / Traceloop 等 collector） | 中间件吞掉重试（HTTP auto-retry）；batch processor 合并 span；无 agent 侧 choice/consumption 事件 | retry 计数（absorbed retries）、attempt 级去重、consumption 事件 |
| **Runtime hook**（Claude Code / Codex hook 路径） | session restart 断链；compaction 丢弃旧事件；agent 素材库对 collector 不可见 | 跨 session 连续性、素材库选择 |
| **Platform attestation**（受信任平台直接报告） | 平台可能不暴露 agent 侧判断逻辑 | agent 决策原因 |

## 3. 预期 UNPROVABLE 率表

对每种 Metric Family，在不同拓扑下的预期 UNPROVABLE 率区间。

> 区间基于 2026 年 9 月审计数据集（110+ 仓库、65+ 实证发现）。
> 这些值反映**设计预期**，不是个体 provider 的实测值。实际值取决于具体
> instrumentation 部署质量。

| Metric | Provider-only | Span OTel | Runtime Hook | Platform |
|--------|:------------:|:---------:|:------------:|:--------:|
| M2.1 Presented Opportunities | 100% UNPROVABLE | 85–100% | 10–30% | depends |
| M2.2 Observed Selection Rate | 100% | 90–100% | 15–35% | depends |
| M3.1 Operation Count | 0 (N/A per I25) | 40–60% resolvable | 70–85% resolvable | >95% |
| M3.2 Attempt Completion Rate | 100% UNOBSERVABLE | 30–50% | 70–90% | >95% |
| M3.3 Attempt Success Rate | 100% UNOBSERVABLE | 25–45% | 65–85% | >95% |
| M3.5 Op Resolution Coverage | 0% (design) | 30–50% | 65–80% | >90% |
| M4.1 Result Consumed Rate | 100% UNOBSERVABLE | 90–100% UNOBSERVABLE | 40–60% | depends |
| M5 Incremental Lift（提案） | UNPROVABLE | 条件性（需 holdout） | 条件性 | 条件性 |

**读法**：
- `100% UNPROVABLE` = 该拓扑对此指标无法产生任何数字（正确输出）
- `30–50%` = 预估该拓扑下约 30–50% 的调用可产生有效观察
- UNOBSERVABLE 与 UNPROVABLE 的区分：前者完全不可观察（不进入任何分母），
  后者观察到但无法 resolve（进入 UNPROVABLE 分类）

## 4. UNPROVABLE 在标准中的含义

### 4.1 对指标聚合

UNPROVABLE 元素：
- **不进入**指标的 positive 总和
- **不进入**指标的 denominator（不同于 FALSE）
- **单独披露**为 `UNPROVABLE share`（与 UNOBSERVABLE 分开）

### 4.2 对计费（COMMERCIAL §5）

`incrementality_evidence: none` 的效果：
- `billing_basis: outcome` 的账单行降档为 `billing_basis: operation`
- **绝不导致账单归零**（回退计费，不是不计费）
- `effect_confirmed` 事件仍可计费（按 occurrence 而非 incrementality）
- 见 COMMERCIAL §5 与 uplift-audit 提案

### 4.3 对 PASS/FAIL/UNPROVABLE

UNPROVABLE-by-surface 的 PASS/FAIL 含义：
- PASS：主张强度 ≤ 可用证据等级 ∧ 主张不超出 measurement surface 的可观察范围
- FAIL：主张超出现有证据等级、或试图将 UNPROVABLE 陈述为可证明
- UNPROVABLE：当前测量拓扑无法产生该主张所需的证据

这是 PASS/FAIL/UNPROVABLE 从「什么算一次/结果可不可证明」向「主张可不可证明」的自然延伸。

## 5. Scope 演进

UNPROVABLE-by-surface 的 scope 随 measurement surface 扩大而缩小。

| 阶段 | Surface | 新增可观察对象 |
|------|---------|----------------|
| 当前（0.4.x） | Provider-only + Span OTel + Runtime Hook（partial） | Attempt、Operation（partial）、Choice（partial） |
| 0.5 | + Claude Code adapter（骨架上） | Claude 侧的 operation resolution、consumption |
| 0.6 | + SDK 自带 attempt-attestation hook | Attempt 级签名 |
| Future | + Platform attestation | 受信任平台可直接报告 operation/attempt |