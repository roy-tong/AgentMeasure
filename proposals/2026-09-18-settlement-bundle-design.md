# 结算证据包（Settlement Evidence Bundle）概念设计

> 对应 uplift-audit 提案 P3 项。本文件在 P1 落地过程中同步设计概念模板，
> 使 P3 的结算证据包格式在 P1 阶段就有可讨论的形态，而非等到转正才从零开始。
> 复用模式：bundles/ 四件套 + CI 重算（live-codex-desc-clarity-001 先例）+ Lab 校准报告模板。

---

## 1. 用途场景

结算证据包是**效果费合同双方对账的标准化文档**。当 Provider 按 outcome 计费时，
买方（Consumer）要求审计"这些 outcome 是不是真的、是不是增量"——证据包是对此
的直接回答。

典型周期：
1. Provider 在结算期运行 Metering Policy → 产出账单
2. 买方要求审计账单中的 outcome 行 → Provider 出具结算证据包
3. 买方审计员 / 第三方独立复算 → 确认或异议
4. 有异议 → 进入争议解决流程（涉 reversed 记录、stability_window 验证）

## 2. 模板结构

证据包复用现有 Lab 校准报告格式，加上 COMMERCIAL §10 对账表。

```yaml
settlement_evidence_bundle:
  schema: agentmeasure.commercial/settlement-bundle
  schema_version: "0.1.0"
  
  # PART 0: 元数据
  billing_period:
    start: "2026-10-01T00:00:00Z"
    end: "2026-10-31T23:59:59Z"
  provider_id: com.example
  offering_id: com.example.support:basic
  metering_policy_version: "2026.3"
  pricing_policy_version: "2026.1"
  
  # PART 1: 计量声明
  metering_summary:
    total_billable_events: 1250
    by_billing_basis:
      operation: 850          # 按发生计费
      outcome: 400            # 按效果计费
    by_outcome_class:
      resolved: 310
      assumed_resolved: 65
      escalated: 15
      abandoned: 10
  
  # PART 2: 效果声明（逐行可追溯）
  outcome_lines:
    - line_id: ol-001
      effect_confirmation_ref: eff-c-001
      operation_id: op-1001
      outcome_class: resolved
      observer_grade: affected_party      # 工单系统 confirm
      confirmed_at: "2026-10-03T14:22:00Z"
      stability_window_hours: 72
      stability_deadline: "2026-10-06T14:22:00Z"
      settlement_grade: true              # 已过稳定窗
      billing_basis: outcome
      billable_quantity: 1
  
  # PART 3: 增量证据（仅 outcome 行需要）
  incrementality_section:
    evidence_level: v3_quasi_experiment    # 全线走 V3 准实验
    evidence_provider: com.example        # provider 自证（非独立审计）
    m5_lift_table:                         # M5 按条件分层
      overall:
        baseline_resolution_rate: 0.32    # 反事实面的 solve rate
        treatment_resolution_rate: 0.58
        incremental_lift: 0.26
        lift_significant: true
        p_value: 0.003
      by_task_type:
        - task_type: billing_query
          baseline: 0.45
          treatment: 0.67
          lift: 0.22
          significant: true
        - task_type: technical_support
          baseline: 0.18
          treatment: 0.49
          lift: 0.31
          significant: true
    unprovable_share: 0.12                 # 12% 的 calls 因 instrumentation 不可观察
    unprovable_reason: "span-layer retry invisibility on HTTP auto-retry paths (known limit)"
```

## 3. 校验规则

| 条件 | 行为 |
|------|------|
| outcome_class=resolved 且 observer_grade=self_attested | 标记降档（提醒买方：无受影响方确认） |
| billing_basis=outcome 且 incrementality_evidence=none | 该行自动降至 operation basis |
| stability_deadline > current_time | 标记为 preliminary（未过稳定窗） |
| 同一 task_id 在 window 内出现两次 resolved | 可能的重复计费，触发手动审查 |
| M5 lift 显著为负 | production 效果反方向 → 证据包附加 direction_mismatch 警告 |

## 4. 与现有资产的复用关系

| 证据包组件 | 复用来源 | 修改方式 |
|-----------|---------|---------|
| 逐行 outcome_lines | schemas/payloads/effect-confirmed | 批量校验 + 汇总 |
| M5 lift table | lab/calibrate.py calibrate report | 指标名称扩展（outcome_rate 加入 primary_metric） |
| 对账校验 | COMMERCIAL §4 Metering Ledger | revision/supersedes/reversal_of 链 |
| 双语一页决策版 | lab/report.py render_calibration_html | 模板扩展 |
| UNPROVABLE 率和 reason | known-limits-unprovable-by-surface.md | 对照 topology 预期表 |

## 5. 首个公开案例目标

ILO（International Labour Organization）或 AI 客服垂直——我们已经有 langfuse 的
cache_write 修复案例、Cloudflare docs 的计数语义案例。建议第一个结算证据包以
**第三方独立审计**而非 Provider 自证的身份出现，以最大化信任信号。