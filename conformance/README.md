# AgentMeasure Conformance

## Conformance Levels（Draft 0.4）

一个平台可能根本观察不到 Presented——不能要求它支持全部标准。按能力分层认证：

| Level | 覆盖 | 当前 vectors 状态 |
| --- | --- | --- |
| **AgentMeasure Core Conformant** | 收据格式、签名、隐私、不变量 1-24 | receipt/correlation fixtures 已发布（`verify_vectors.py`） |
| **AgentMeasure Choice Conformant** | M2.1-M2.5 | M2.2 / M2.5 vectors 已发布（含三轴 scope：authority/constraint）；M2.1 / M2.3 / M2.4 待发布 |
| **AgentMeasure Execution Conformant** | M3.1-M3.3 | M3.1/M3.3 grain vectors 已发布（retry chain 归并 / 无证据 fail-closed / 双 grain 披露，DR-006）；M3.2 待发布 |
| **AgentMeasure Utility Conformant** | M4.1 | consumption vectors 已发布 |
| **AgentMeasure Reporting Conformant** | Measurement Label + 口径披露 | 待发布 |
| **Verified Measurement Profile** | 签名、证据、Receipt（Core §10 高级符合性） | 参考实现支持；非采用前置 |

> **声称纪律**：通过某一 Level 只代表该 Level **已发布**的 vectors 全过；
> 未发布 vectors 的部分不得宣称覆盖。例：Choice Conformant 目前 = M2.2 + M2.5
> vectors 全过 + presented 可观察声明，不等于 M2.1-M2.5 全部验证。

认证声明示例：`<your implementation> — AgentMeasure Choice Conformant (Draft 0.4)`

### 结算场景渐进阶梯（AMS-1 · Stage 0…3）

面向只需结算声明能力的实现方（PEAC 式渐进采用，与上表指标族正交）：

| 阶梯 | 能力 | 验证 |
| --- | --- | --- |
| **Stage 0 — Discovery** | 读懂 [standard/SETTLEMENT.md](../standard/SETTLEMENT.md) 与 [settlement.manifest.json](../standard/settlement.manifest.json) | — |
| **Stage 1 — Transport** | effect-confirmed JSONL 收发（schema 校验族） | settle 校验测试 |
| **Stage 2 — Policy** | OUT 审计（UNPROVABLE fail-closed + OUT-005 对称披露） | `run_outcome_audit.py` |
| **Stage 3 — Commerce** | 生成 ADB + AMS-1 一页纸声明 | `settle --format md`（`test_settle.py`） |

## 运行

```bash
python3 conformance/runners/run_metrics.py    # 指标 vectors（M2.2 / M2.5 / M3.1+M3.3 / M4.1）
python3 verify_vectors.py                      # receipt/correlation vectors
python3 conformance/runners/run_external_fixture.py  # 外部 fixture（Urusilla-001，#8/#9 守卫）
python3 conformance/runners/run_outcome_audit.py     # 效果审计（OUT-001..004）
python3 conformance/runners/run_delegation.py        # 多 Agent 委托（DELEGATION-001..003）
```

### 检查家族与对应不变量

| 家族 | 覆盖 | 钉住的不变量 |
| --- | --- | --- |
| M2/M3/M4 metric vectors | 选择率、执行粒度、消费率 | 1–26 |
| OUT-001..004 | outcome 可判定性、effect 可追溯、重开去重、主张—证据匹配 | 14 / 16 / 17 |
| DELEGATION-001..003 | 不压平为 Operation、DAG 深度、跨 harness 成本归属 | **27–31** |

## Evidence Cases（公开 artifact 分析，≠ conformance vectors）

`conformance/evidence/<case>/` 存放对公开 artifact 的覆盖分析案例——
不验证实现，只演示口径纪律（coverage-first 报告 + claim boundary）：

- **langfuse-demo-traces** — Langfuse 官方 demo seed 的三份真实框架 trace
  （langgraph / openai-agents / pydantic-ai-tools，commit-pinned，不分发源文件）：
  12 attempts、operation grouping evidence 100% ungrouped、**safe operation
  coverage = 0%**、4 处 retry/loop 不可分辨 sibling 模式、token usage 0/26。
  一次性 adapter + 双模式 pipeline 全可复现（`fetch_source.py` + `run_case.py`）。

## 外部 Fixture

`conformance/vectors/external/<source>-<seq>/` 接收第三方提交的 fixture
（含 mutations）。首个被接收的：

- **urusilla-001** — @jaden3824 (Urusilla) 的 project-authored synthetic
  8-event fixture（cache/retry/fallback 拓扑，FMT-002），来自首次外部
  conformance pass（langfuse/langfuse#16383），按 #8/#9 的承诺接入。
  Runner 守卫：schema 有效性、#8 root-sibling 变异必须被拒、指标逐项复现
  expected.json、#9 篡改声明必须显式 `reconciliation: failed`。
  **Claim boundary 原样保留**：synthetic evidence，非 endorsement、非外部复现。

提交新 fixture：PR 附 events + expected + mapping（或 sidecar）三件套，
runner 按上面四类守卫生成；claim boundary 由提交方声明、AgentMeasure 复核。

## 语言无关性

`conformance/vectors/*.json` 是语言无关契约：Go/Rust/TS 实现应对同一 vectors
产生同一结果。runner 只是参考实现的验证器。
