# AgentMeasure Settlement Statement — AMS-1（Draft 0.1）

> 结算声明的公开标准。对照物：TareCount ARS-1（LinkedIn Pulse，单作者）——我们采纳了其中
> 三条最扎实的实践（见 COMMERCIAL §5.1 的 D-1/D-2/D-3），本文将其与 AgentMeasure 既有纪律
> 合并为一份**开放治理、工具免费、第三方可复现**的标准。条款 S-1…S-8 每条都引用其执行测试
> ——「声明里的名字就是代码里的名字」（ARS-1 最好的纪律，我们用 conformance 向量匹配它）。

## 0. 判决词表（verdict taxonomy）

| 判决 | 来源 | 结算含义 |
| --- | --- | --- |
| **settled (settlement-grade)** | `outcome_class=resolved` × `observer_grade=affected_party` | Tier 2 可结算 |
| **assumed** | `outcome_class=assumed_resolved` | 计入 Tier 1（对方自己的口径），永不计入 Tier 2 |
| **escalated** | `outcome_class=escalated` | 升级 ≠ 解决：任何线的结算都不得计入 |
| **cannot settle** | 无 `incrementality_evidence`（UNPROVABLE 族） | **从索赔中移除（S-2）**，列明缺失项而非降档 |
| **out of scope** | spam / 厂商发起 / 仅资格判定 / 合并重复 | 声明范围外，单列不混入（S-8） |

## 1. 条款

### S-1 · 两线并跑，绝不混算（承 D-3）

- **Tier 1**：被审方自己的规则会计费的全部（resolved + assumed）。
  谈判以 Tier 1 领衔：对方无法反驳自己的规则，只能反驳数据——而数据在你手里。
- **Tier 2**：AgentMeasure 结算级（affected party 确认的 resolved）。
  Tier 2 是续约议价依据，**不是**争议条款。
- 两线的差额是**争议类**，永远呈现为两个独立数字，不得合并为单一「真实值」。
- **类 × 等级必须交叉计算**：边缘聚合会骗人（escalated × affected_party 不是 resolved）。
  执行测试：`healthcheck/tests/test_settle.py::TestSettlementStatement`。

### S-2 · 移除你无法举证的（承 D-1 / UNPROVABLE）

- 无增量性证据的行**从索赔中移除**，并逐行列明缺失项，供对方补证或折让。
- 理由：一条你无法举证的索赔，正是对方用来否定其余全部的那一行。
- 降档计费仅作为合同方的显式选项，不得为默认。
- 执行测试：`conformance/vectors/outcome-audit`（UNPROVABLE 拒绝推断）。

### S-3 · 双向披露（承 D-2 / OUT-005）

- 声明 MUST 同时包含：**多计方向**（billed but not settlement-grade，附 self-attested
  子计数）与**少计方向**（billable but not billed）。
- 少计方向无法从当前输入判定时，MUST 写明「cannot determine from this input」，
  不得省略——只报告单向发现的声明是倡导文件，不是对账文件。
- 执行测试：`conformance/vectors/outcome-audit` OUT-005（3 向量：未做有利方向搜索 → FAIL；
  披露少计仍报毛额 → FAIL）。

### S-4 · Absent ≠ zero

- 缺失的字段（证据、重置时间、计数）不得被解释为零或猜一个值。
- 执行测试：healthcheck settle 校验族（`_validate_effect`：None 保持 None，
  显式 0 保持测量值）。

### S-5 · 来源与复现（我们的「盲读者」）

ARS-1 的自我修正机制是盲读者分歧（「读者分歧 = 文本有罪」）。开放标准的等价物是
**第三方可复现**：任何人用声明中给出的命令，必须得到相同的数字。

- 声明 MUST 携带**来源块**：输入文件 sha256、生成命令全文、spec 版本。
- 同一 fixtures 对任何符合本标准的实现必须产生相同结果（实现分歧 = 规范有罪）。
  执行测试：`verify_vectors.py`（跨实现等价承诺）+ `run_case.py`（CI 锁定数字）。

### S-6 · 范围（承 ARS-1 C8）

以下不计入结算声明，单列：spam 与滥用流量、厂商主动发起的会话、仅资格判定
（未进入服务）、声明内已合并的重复行。移出理由逐条标注，不得静默丢弃。

### S-7 · 工具与价格

- 生成结算声明的工具**免费开源**；标准的演进走开放治理（`GOVERNANCE.md`）。
- 本标准不绑定任何服务提供方；审计方、被审方、第三方均可使用同一工具复核同一声明。

### S-8 · 演进

条款修改 MUST 同时更新其执行测试；测试分歧时**先改规范文本、再合测试**
（与 ARS-1 盲读者机制同构：分歧即文本之罪）。

## 2. 结算声明格式（一页纸规范）

一份合规的 Settlement Statement（Markdown 交付物）按序包含：

1. **Provenance 头**：被审方 / offering / 证据等级 / spec 版本 / 输入 sha256 / 生成命令
2. **The claim, two ways**：Tier 1 / Tier 2 / 争议类（S-1）
3. **Dollars**：双方金额 + 差额 + 回本数学（审计成本 ÷ 月差额）
4. **Both directions**（S-3）：多计明细（含 self-attested 子计数）+ 少计方向如实标注
5. **Cannot settle**（S-2）：移除行数与缺失项清单
6. **Out of scope**（S-6）
7. **Reproduce**（S-5）：第三方复现命令 + 预期输出锚点

生成命令：

```bash
agentmeasure settle --effects effects.jsonl --format md \
  --price 0.99 --audit-cost 2500 --out statement.md
```

## 3. 与人工重数服务的关系

本标准与重数服务（如 TareCount）是**能力等价的两种形态**：服务把判断包成一次
人工交付（按次收费、产能受限于人）；本标准把同样的判断纪律做成任何人可执行、
CI 可锁定、第三方可复现的公开规范。二者可共存：服务可以用本标准作为其方法论文档，
客户可以在购买服务前后用本工具自行复核。差异只在形态，不在诚意。
