# AgentMeasure 标准全文交叉引用地图 — 2026-09-18

> 完整阅读了 standard/ 全部 11 个文件、extensions/COMMERCIAL.md、known-limits、
> registry/vocabularies.yaml、registry/metrics.yaml 后的结构审计。
> 供提案写作者和实现者使用——知道有什么可用，避免重复发明 wheel。

## 一、引用拓扑（关键依赖链）

```text
CORE（语义对象 & 不变量）
  ├── DATA（payload schema & observation_type）
  ├── CORR（关联规则）
  ├── ENTITY（身份解析）
  ├── BIND（绑定层）
  │
  ├── METRICS（指标合同）
  │     └── registry/metrics.yaml（机器可读发行）
  │
  ├── QUALITY（质量模型 & 用途画像）
  │     └── §4 billable_audit ← 这是效果审计的入口
  │
  ├── TRUST（证据档案 & 5 轴）
  │     └── §3 Evidence Profile（A/C/I/T/M 五轴）
  │
  ├── PROFILES（能力画像——认证声明）
  │
  ├── PRIVACY（隐私纪律）
  │
  ├── SECURITY（安全纪律）
  │
  └── known-limits-unprovable-by-surface（已知限制——新增）
        └── COMMERCIAL（经济语义——实验性扩展）
              └── §3/§5/§9（单位注册、计量 predicate、对账报告预告）
```

## 二、增量审计相关定义的完整索引

### 主题：Effect / Outcome

| 位置 | 内容 | 缺口 |
|------|------|------|
| CORE §2.4 | Result/Effect 双元定义（一行）| 无对象、无状态机、无 payload |
| CORE §2.7 | 8 种 Interaction Classes 各有 Effect 含义 | Effect 验证延至 0.5 |
| CORE §9 I22 | Utility 指标 MUST 声明度量 Result 还是 Effect | — |
| COMMERCIAL §3 | `effect_confirmed` / `outcome_qualified` 作为 billable_event | payload 当时不存在（悬空引用） |
| COMMERCIAL §9 | Metering 对账报告预告 | 未实现 |
| **现修复** | effect-confirmed.schema.json / task-outcome v2 | — |

### 主题：Outcome 分类

| 位置 | 内容 | 缺口 |
|------|------|------|
| CORE §2.4 | Outcome = Task/Operation 最终结果（一行）| 无分类、无状态机 |
| schemas/payloads/task-outcome.json（v1）| `task_success: boolean` | 只有二值 |
| **现修复** | vocabularies.yaml 新增 `outcome_class` + `outcome_observer_grade` | — |
| **现修复** | task-outcome.json v2 添加 outcome_class 等字段 | — |

### 主题：计费 / 商业化

| 位置 | 内容 | 缺口 |
|------|------|------|
| COMMERCIAL §3 | Event/Unit/Quantity 三分离 + Metering Policy | — |
| COMMERCIAL §5 | `billing_basis: attempt\|operation\|effect\|outcome` + `minimum_resolution` + `billing_requirements` 4 predicate | — |
| COMMERCIAL §4 | Metering Ledger（revision/supersedes/reversal_of）| — |
| COMMERCIAL §6 | Commercial Attribution；attribution ≠ causal incrementality（I14）| — |
| COMMERCIAL §9 | 毕业路径 | — |
| known-limits §4.2 | `incrementality_evidence: none` → billing 降档规则 | 未写入 COMMERCIAL |
| QUALITY §4 | `billable_audit` use profile | — |
| TRUST §5 | billing_requirements 为第四正交维度 | — |

### 主题：UNPROVABLE / UNOBSERVABLE

| 位置 | 内容 | 缺口 |
|------|------|------|
| CORE §9 I17 | UNOBSERVABLE ≠ FALSE（不变量 17）| 只覆盖 UNOBSERVABLE |
| CORE §4 | 4 种 observability 状态：TRUE / FALSE / UNKNOWN / UNOBSERVABLE | **UNPROVABLE 不在其中** |
| known-limits（新增） | UNPROVABLE-by-surface 定义 + 按拓扑的预期率表 | 未在 CORE §4 中注册 |
| METRICS §6 | M5 = Incremental Lift | 待 AUP（提案已写）|
| QUALITY §6 | 可说/不可说表 | 无因果行 |

### 主题：证据 / 因果关系

| 位置 | 内容 | 缺口 |
|------|------|------|
| TRUST §3 | 5 轴证据档案：A/C/I/T/M | **无因果轴**（V-ladder missing）|
| CORE §9 I14 | attribution ≠ causation | 无执行机制 |
| LAB calibrate.py | production_confirmed / direction_mismatch / not_comparable | 未映射到 V-ladder |
| PROFILES | P2 反事实指标建议 | 未实现 |
| **uplift-audit 提案** | V0–V4 因果轴 + M5 合同 + OUT-004 | Draft |

### 主题：Conformance 向量体系

| 位置 | 内容 | 缺口 |
|------|------|------|
| conformance/runners/run_metrics.py | 4 个 metric runners（M2.2/M2.5/M4.1/M3.1+3.3）| — |
| conformance/pack/run_pack.py | 5 invariants 的 pack 系统 | 无 outcome/incrementality invariants |
| conformance/README.md | 6 个认证 Level | 无 Outcome Audit Level |
| conformance/evidence/ | 6 个 evidence case | 无 outcome/effect evidence case |
| **本日新增** | run_outcome_audit.py + out-001-004.json | — |

## 三、发现的关键盲区（Gaps）

### Gap 1：UNPROVABLE 在 CORE §4 中不存在（严重）

`known-limits-unprovable-by-surface.md` 定义了 UNPROVABLE 但不被 CORE §4 引用。
CORE §4 的 observability 状态是 TRUE / FALSE / UNKNOWN / UNOBSERVABLE——UNPROVABLE
无处安放。

**建议**：在 CORE §4 或 §9 中将 UNPROVABLE 注册为第五状态，并在 DATA.md 中定义
observation 级 `unprovable_reason` 字段。

### Gap 2：Effect 没有独立的规范页面

CORE §2.4 一行定义 + §2.7 交互类别 + COMMERCIAL §3 `effect_confirmed` ——但
Effect 的测量对象定义、observability、证据要求、不变量分散在三份文档中。

**建议**：新建 standard/EFFECT.md（类似 METRICS.md 的独立页），集中存放 Effect 的
完整契约。这是 0.5 的明确前置。

### Gap 3：M5 Incremental Lift 零实现

METRICS §6 留白 "实验设计见 AgentMeasure 0.5"。metrics.yaml 也止于 M4.1。
known-limits §3 表 M5 行写"条件性"。**Lab 引擎已有 80% 实现**。

**建议**：将 M5 指标合同提前到 0.4.x 补丁（见 §8 分析），因为引擎就绪，缺的只是
primary_metric 允许列表扩展（已做）和 metrics.yaml 注册。

### Gap 4：COMMERCIAL 是实验性扩展但已被大量引用

COMMERCIAL 的状态是 Experimental / Informative，不参与 conformance。但：
- QUALITY §4 `billable_audit` 引用之
- TRUST §5 将其列为第四正交维度
- uplift-audit 提案的结算证据包完全建立在其上

**建议**：在 COMMERCIAL.md 增加免责声明定位页眉，注明哪些部分已被其他标准文档
引用（已引用部分应视为半规范引用，非纯实验）。

### Gap 5：名称不一致

| 差异 | 位置 | 
|------|------|
| M2.5 名称 | METRICS.md 用全名 "Observed Head-to-Head Choice Share"，registry/metrics.yaml 仍是未带前缀的旧短名 |
| `outcome_class` 枚举已加入 vocabularies.yaml | 但尚未被任何 runner/index 生成脚本消费 |
| known-limits 使用 `incrementality_evidence` | COMMERCIAL §5 无此字段 |

## 四、与增量审计提案的关系矩阵

| 提案五件套 | 现有标准覆盖率 | 缺口填补 |
|-----------|--------------|---------|
| 1. Effect Confirmation 状态机 | COMMERCIAL §3 有 `effect_confirmed` 事件 | effect-confirmed schema（已做）|
| 2. Outcome 词表 + Billable Unit 注册 | vocabularies.yaml 已有枚举骨架 | outcome_class（已做）|
| 3. M5 Incremental Lift 合同 | METRICS §6 留白；Lab 有校准引擎 | primary_metric 扩展（已做）+ metrics.yaml 注册（待做）|
| 4. 主张-证据匹配（V-ladder） | TRUST §3 五轴缺因果轴；I14 无执行机制 | 因果轴进 TRUST + QUALITY §6（P2，待做）|
| 5. OUT- 检查家族 + 结算证据包 | 零 conformance 覆盖 | out-001-004 向量 + runner（已做）|

## 五、标准使用建议

1. **写 EFFECT.md 前先读 CORE §2.4 + §2.7 + COMMERCIAL §3 + §5**——这三处已有效果审计的全部概念引子，统一到一页即可，不是从零发明。
2. **COMMERCIAL 已经定义了 billing_requirements 四 predicate**。OUT-004 直接引用它们即可，不需定义新的计费 predicate。
3. **Lab 的 calibrate.py 已经实现「离线 vs 生产效果对比」**，与 M5 的 incremental lift 同构。改 prereg.py 的允许列表已做；下一步是 metrics.yaml 注册和导出层扩展。
4. **UNPROVABLE 需要进入 CORE §4**。在更新提案前先在标准层注入第五状态。