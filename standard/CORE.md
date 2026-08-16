# AgentMeasure Core Specification — Open Measurement Standard for AI-Agent Software Usage（Draft 0.4）

> **Draft 0.4：Measurement Objects & Verification Decoupling。** 0.3 解决了"怎么算"；
> 0.4 解决"算的是什么"——把测量对象扩展为完整的
> **Software Entity → Capability → Interaction Surface** 模型，补齐
> decision → operation → attempt → result/effect → outcome 的端到端谱系，
> 并把 Core 与 Verification Profile 解耦。
>
> 参考实现（`reference/`）与标准文档同仓演进。**AgentMeasure 不定义谁是真相来源，
> 而定义什么证据、按照什么规则，可以支持什么结论。**

## 0. 版本与治理

- 版本路线：Draft 0.2（框架）→ 0.3（语义）→ **0.4（对象与质量）** → 0.5（价值测量）→ 1.0
- 指标变更走 **AUP**（`proposals/`）；**AgentMeasure Metrics 是变更最频繁的文档**，whitepaper 保持稳定
- 毕业标准（不变）：2 独立实现 + 3 profiles + 2 tool-side + conformance + vectors + 5-10 项目 + discrepancy report + 双 review

## 1. 核心命题（不变）

Reach → Choice → Use → Utility → Value。五问不变。

**规范语言（BCP 14）**：本规范及所有 AgentMeasure 文档中，MUST / MUST NOT /
SHOULD / SHOULD NOT / MAY 按 RFC 2119（BCP 14）解释。实现必须满足全部 MUST；
SHOULD 是强烈建议，偏离 MUST 在 Measurement Label 中披露。

## 2. Measurement Objects（Draft 0.4：实体化）

### 2.0 三层结构

测量对象分三层：

1. **Software Entity**（存在的软件）——被度量的"谁"
2. **Capability**（能做什么）——实体的具名功能
3. **Interaction Surface**（怎么交互）——可观察的调用界面

**观察发生在 Interaction Surface 上；统计归属到 Entity。** Observer 直接看到的是
surface，不一定知道 entity——entity 身份由 registry 的 alias 归并推导
（见 AgentMeasure Entity）。无法归并时，实体归属 MUST 记为 UNKNOWN，绝不猜测。

### 2.1 Software Entity（实体类型）

| 类型 | 定义 | 示例 |
| --- | --- | --- |
| **Tool** | 可执行的具名功能单元 | MCP tool、CLI 命令、SDK 函数 |
| **Skill** | 打包的能力包（过程 + 提示 + 工具） | Agent Skill 文件、自定义 skill 包 |
| **API** | 网络服务接口 | REST/GraphQL endpoint、第三方 API |
| **Data Source** | 结构化数据访问 | 搜索引擎、向量库、知识库 |
| **Agent** | 可被其他 Agent 调用的子 Agent | sub-agent、delegated agent |
| **Application** | 端到端应用 | 以 UI/API 形态被使用的完整应用 |
| **Runtime Capability** | 运行时内置能力 | 文件编辑、Bash、Web Fetch |
| `unknown` | 无法判定 | — |

实体身份规则：
- 每个 Entity 有且仅有一个规范标识 `entity_id`（registry 权威，见 AgentMeasure Entity）
- 同一逻辑软件的不同形态（MCP server / CLI / skill）由 registry alias 归并；
  **alias 归并前的观察 MUST NOT 跨形态合并计数**（不变量 21）

### 2.2 Capability

- Capability = Entity 的具名功能；标识 `capability_id`（`<entity_id>:<name>`）
- Category 是**版本化的 measurement construct**（`category_id + category_version`），
  建立在 Capability 之上，不是永久真理（AgentMeasure Taxonomy，Draft 0.4 立项）
- 同一 Capability 可经多个 Interaction Surface 暴露

### 2.3 Interaction Surface

- Surface = 具体可调用界面；标识 `surface_id`
- 类型：`mcp_tool` · `cli_command` · `http_endpoint` · `function_call` ·
  `skill_file` · `plugin_hook` · `runtime_builtin` · `unknown`
- 观察发生在 surface 层；surface → entity 映射由 registry 提供（见 AgentMeasure Entity）

### 2.4 行为对象（决策 → 执行谱系）

| 对象 | 定义 | 关键标识 |
| --- | --- | --- |
| **Task** | 一次任务单位（Agent 为之工作的目标） | `task_id` |
| **Decision Opportunity** | 一次工具选择决策 | `decision_id` |
| **Candidate Set** | 该次决策中真正可供选择的集合 | `candidate_set_id` |
| **Tool Presentation** | 某 selectable 出现在该 Candidate Set | `presentation_id` |
| **Selection** | Agent 选择某 selectable | `selection_id` |
| **Operation** | 对某 Capability 的一次**逻辑使用**（为某 task 而用） | `operation_id` |
| **Attempt** | Operation 的一次实际执行 | `attempt_id`（= tool_call_id） |
| **Result / Effect** | 执行产生的返回值 / 世界状态改变 | — |
| **Outcome** | Task 或 Operation 的最终结果 | — |

完整谱系（一条链路）：

```text
Task ──▶ Decision Opportunity ──▶ Selection
                                      │
                                      ▼
                                  Operation ──▶ Attempt 1 ──▶ Result / Effect
                                      │             │  (retry)
                                      │             ▼
                                      │          Attempt 2 ──▶ Result / Effect
                                      ▼
                                  Outcome
```

**Operation / Attempt 拆分**（Draft 0.4 核心）：
- **Operation** = 逻辑使用（"为任务 T 使用能力 C"），是 M3.1 的计数对象
- **Attempt** = 单次执行；**重试 = 同一 Operation 的多个 Attempt，不再是 validity 分类**
  （validity 只保留 duplicate / replay / suspected_invalid 等观察质量分类）
- 无 Operation 证据时，观察只能形成 Attempt；Operation 归并 MUST 遵循
  AgentMeasure Correlation 的确定性规则（不变量 23：无证据不归并）

### 2.5 Decision Authority（决策主体）

一次 Selection 由谁作出：

| Authority | 定义 |
| --- | --- |
| `model` | 模型自主选择 |
| `router` | 路由/编排层选择 |
| `workflow` | 预定义流程选择 |
| `user` | 用户直接指定 |
| `policy` | 策略/规则强制 |
| `platform` | 平台自动选择 |
| `unknown` | 无法判定 |

### 2.6 Selection Constraint（选择约束）

| Constraint | 定义 |
| --- | --- |
| `autonomous` | 完全自由选择 |
| `recommended` | 有推荐但可拒绝 |
| `required` | 必须使用（无替代） |
| `user_requested` | 用户点名要求 |
| `fallback` | 作为回退被选 |
| `forced` | 被强制注入 |
| `unknown` | 无法判定 |

**不变量：不同 authority / constraint 的 Selection 默认 MUST NOT 直接比较
Selection 类指标**（或必须声明标准化方法）——required/forced 的"选择"不是偏好。

### 2.7 Interaction Classes（交互类别）

Capability 按交互性质分类，决定 Utility 的度量方式：

| Class | 定义 | Result（返回值） | Effect（世界改变） |
| --- | --- | --- | --- |
| **Information** | 只读获取 | 返回数据 | 无（或上下文更新） |
| **Action** | 对外部世界产生副作用 | 确认 / ack | 状态改变 |
| **Transaction** | 多步原子操作 | 最终结果 | 全部或全无的状态改变 |
| **Computation** | 计算 / 处理 | 派生输出 | 无 |
| **Communication** | 消息 / 通知 | 投递确认 | 消息送达 |
| **Control** | 编排 / 控制流 | 后续执行指令 | 下游执行发生 |
| **Storage** | 持久化 | 写入确认 | 存储状态改变 |
| **Sensing** | 感知 / 输入 | 传感器数据 | 无 |
| `unknown` | 无法判定 | — | — |

**Result / Effect 双元 Utility**（Draft 0.5 前置）：
- Result = 能力返回的直接产物（可由 Consumption observation 观察）
- Effect = 世界状态的实际改变（需要 Consumption 之外的验证）
- Utility 指标 MUST 声明度量的是 Result 还是 Effect（不变量 22）

## 3. Measurement Grain（统计粒度）

| Family | Grain |
| --- | --- |
| Distribution | Client / Client-Day |
| **Choice** | **Decision Opportunity** |
| Execution | Attempt（= Invocation） |
| Utility | Result / Invocation |
| Outcome | Task / Operation |
| Relationship | Client × Project × Window |

**不变量：不同 Grain 的指标不可互换。** 10 attempts ≠ 10 operations ≠ 10 decision
opportunities ≠ 10 tasks。任何指标必须声明 Grain。

## 4. Observability States（可观测四态，不变）

观测结果不是二值。正式定义：

| 状态 | 含义 |
| --- | --- |
| **TRUE** | 确认发生 |
| **FALSE** | 有能力判断，并确认未发生 |
| **UNKNOWN** | 应该可以判断，但数据缺失/冲突 |
| **UNOBSERVABLE** | 当前 observation surface 根本无法观察 |

**不变量：An unobservable outcome MUST NOT be interpreted as a negative
outcome.**

示例：Codex 的 Consumed 不可观察 → 记为 UNOBSERVABLE，不记 FALSE：

```text
Consumption Rate = Consumed ÷ Consumption-observable eligible invocations
```

## 5. Metric Eligibility（指标资格，不变）

**Qualified Usage ≠ Metric Eligible Sample。**

- **Qualified Usage**：这条数据是否值得统计的真实生产使用（Context × Validity × Policy）
- **Metric Eligibility**：这条数据是否有资格进入**这个具体指标**的分母
  （如：Presented 不可观察的 runtime 不进入 Observed Selection Rate 分母；
  Consumption 不可观察的不进入 Consumption Rate 分母）

## 6. Choice Mode、Decision Authority、Selection Constraint（三轴正交）

| 轴 | 回答 | 取值 |
| --- | --- | --- |
| **Choice Mode** | 决策结构是什么 | exclusive · multi_select · parallel · sequential · ordered_fallback · router_preselected · unknown |
| **Decision Authority** | 谁作出决策 | model · router · workflow · user · policy · platform · unknown |
| **Selection Constraint** | 选择多自由 | autonomous · recommended · required · user_requested · fallback · forced · unknown |

**不变量：不同 Choice Mode 默认不得直接比较 Observed Selection Rate / Share of Choice**；
authority 与 constraint 同样适用（不变量 24）。比较类指标 MUST 声明三轴。

## 7. Qualification：Context × Validity（不变）

### Usage Context（数据来源环境）

```text
production · development · test · benchmark · evaluation · synthetic · ci · demo · unknown
```

### Invocation Validity（调用有效性）

```text
normal · retry · duplicate · replay · agent_loop · health_check · load_test · suspected_invalid · unknown
```

> Draft 0.4 注：`retry` 作为 validity 值保留用于**无 Operation 上下文**的旧数据；
> 有 Operation 上下文时，重试 MUST 建模为同一 Operation 的多个 Attempt
> （见 §2.4），不再使用 validity=retry。

### 口径定义

| 口径 | 组成 | 用途 |
| --- | --- | --- |
| **Strict Qualified Usage** | `production` + `validity=normal` | 公共 leaderboard / market metric 默认 |
| **Extended Observed Usage** | `production + unknown` | 研究与内部诊断 |

同时公开：`Unknown Context Share`、`Unknown Validity Share`。
**Unknown 默认不得进入 Strict 口径**（避免"不知道是什么流量→报 unknown→进排行榜"
的激励漏洞）。

## 8. Measurement Label（Draft 0.4 补三轴与 grain 披露）

见 AgentMeasure Quality。每个指标除 label 外必须披露：Numerator / Denominator /
Observable population / Qualified population / Runtime coverage / Choice mode
（+ Draft 0.4：Decision authority / Selection constraint / Grain）。

## 9. 标准不变量（Draft 0.4 完整版）

1. Same input + same policy = same result
2. One invocation counted at most once
3. Duplicate observations never increase counts
4. Evidence never self-declared
5. Unsigned fields never affect authenticated claims
6. Ambiguous observations never promoted to corroborated
7. `unknown` never inferred as `success`
8. Metrics always declare scope + policy + window + **grain** + label
9. Public observations never contain user content
10. Corroboration never assumes different strings = independent control
11. Platform attestation UNSUPPORTED until verified
12. Outcome conflicts preserved (inconsistent)
13. Qualified usage never mixes with benchmark/test/synthetic/CI
14. Attribution claims never stated as causation
15. Observed Selection Rate denominator = Presented, not Available
16. **Different grains are not interchangeable**
17. **Unobservable MUST NOT be interpreted as negative**
18. **Presentations count per Decision Opportunity（presentation ≠ decision）**
19. **Different Choice Modes are not directly comparable**
20. **Strict Qualified Usage excludes unknown context/validity**
21. **Surface 观察未经 alias 归并 MUST NOT 跨形态合并计数**
22. **Utility 指标 MUST 声明度量 Result 还是 Effect**
23. **无 Operation 证据时 MUST NOT 把 Attempt 归并为逻辑调用**（fail-closed 归并）
24. **不同 decision_authority / selection_constraint 默认 MUST NOT 直接比较 Selection 类指标**

## 10. 分层：Core 与 Verification Profile 解耦（Draft 0.4）

| 层 | 内容 | 门槛 |
| --- | --- | --- |
| **Core**（本文） | Objects、Grain、Observability、Eligibility、Qualification、Lineage、不变量 | **采用前置**（MUST 满足） |
| **Data** | Observation Envelope schema | 采用前置 |
| **Reporting** | Measurement Label / Policy / Profiles | 采用前置（公开指标 MUST） |
| **Verified Measurement Profile** | Ed25519 签名、Evidence Profile（单词显示等级）、Signed Observation（可选认证载体） | **高级符合性，非采用前置** |
| **Bindings** | OTel / MCP / CLI 映射 | 随实现 |

**不变量（P0-7）：验证是高级符合性，不是采用前置条件。** 一个不签名的采集器
也能产生有效的 AgentMeasure 指标——只是证据等级为 observed（最低显示等级），MUST 在 Label 中声明。

## 11. 文档结构（Draft 0.4）

| 文档 | 负责 |
| --- | --- |
| AgentMeasure Core（本文） | Objects、Grain、Observability、Eligibility、Qualification、分层、不变量 |
| AgentMeasure Entity | Entity 身份、alias 归并、registry 格式（Draft 0.4 新增） |
| AgentMeasure Data | Observation Envelope（六类型）schema |
| AgentMeasure Metrics | Metric Registry + 指标合同（变更最频繁） |
| AgentMeasure Trust | Principal、Signature、Trust Domain、Evidence（Verified Profile） |
| AgentMeasure Correlation | Observation → Attempt → Operation 确定性规则 |
| AgentMeasure Quality | Context/Validity/Coverage/Observability/Label |
| AgentMeasure Privacy / SECURITY / BIND / PROFILES | 不变 |
| AgentMeasure Taxonomy | Category/Capability 分类（Draft 0.4 立项） |
| extensions/COMMERCIAL.md | 经济语义（Offering / Billable Unit / Metering Policy）——**Experimental / Informative，非规范性，不参与 conformance** |
| proposals/ | 指标与规范变更提案（AUP） |
