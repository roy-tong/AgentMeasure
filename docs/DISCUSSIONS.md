# AgentMeasure Discussions — Topics & Ground Rules

> 中文 | [English](#english)

Discussions 是 AgentMeasure 的社区讨论区。它不是一个问答论坛，而是一个**围绕计量语义与证据纪律的公开工作坊**——规格提案、口径争议、基准审计与真实部署案例在这里被公开讨论、被反驳、被修订。

> **Status:** Discussions 功能待开启。开启后本页的议题分类与守则即刻生效。

---

## 分类与议题种子

### Metric Semantics（计量语义）

- "使用量"到底应该包含哪五环？Reach / Choice / Use / Utility / Value 的边界争议
- 一个 MCP 调用失败后重试 3 次，算几次 Use？
- Choice 是否应该只统计"候选集中被选中"的比例，而不是"被展示"？

### Measurement Quality（测量质量）

- Context × Validity 是否足够？还需要哪些维度？
- E0–E5 证据分级的实际判定案例（把一个真实声称贴上来，大家一起定级）
- Fail-closed 语义：观测不到时，应该记为 0 还是"未知"？

### Runtime Profiles（运行时画像）

- 每个 Agent 运行时（Claude Code / Cursor / Codex / Gemini CLI / DeepSeek Harness…）能观测到什么、观测不到什么
- 网关层观测（Glama 等）与服务端自报的偏差如何披露

### Proposals（提案）

- 新测量对象、新指标族的提案讨论（正式提案走 `proposals/` AUP 流程）
- 0.5 效用与经济语义的草案讨论

### Experiments（实验）

- 基准审计周期 1 的实验设计（skills.sh + MCP registry + llms.txt）
- 灵巧手/网页浏览等新型交互面的观测实验

### General（综合）

- CaaS、Agentic Commerce（x402 / ACP / ACP-like）与计量层的关系
- "被 Agent 使用"的社会证明与徽章生态（可验证性优先）
- 维护者自述：你们如何度量自己的 MCP server 被使用？

---

## Ground Rules（讨论守则）

1. **声称必须带证据等级**：讨论中给出数字时，标注 E0–E5 与观测上下文，否则按 E0 对待。
2. **反驳的是口径，不是人**：计量争议天然激烈，请针对定义与证据，不针对发言者。
3. **结论可变**：任何讨论结论都可以被新证据推翻；被推翻的结论会记录在案（保留修订过程）。
4. **提案走流程**：想改变标准本身，从 Discussion 开始，但正式变更走 `proposals/` 的 AUP。
5. **不讨论 token 价格、不吹捧项目**：这里是计量语义的工坊，不是营销区。

---

## 开启 Discussions 后立刻要做的事

1. 按上述 categories 建立分类；
2. 置顶一篇 **"Welcome — 如何参与计量语义讨论"**（本页内容即可）；
3. 置顶 **Benchmark Draft 0.1 评审帖**（见 `benchmark/BENCHMARK-DRAFT.md`）；
4. 置顶 **Measurement Report #001 反馈帖**。

---

## English

AgentMeasure Discussions is a public workshop on measurement semantics and evidence
discipline — where spec disputes, calibration disputes, benchmark audits, and real
deployment cases get discussed, rebutted, and revised in the open.

**Categories:** Metric Semantics · Measurement Quality · Runtime Profiles ·
Proposals · Experiments · General (seed topics above).

**Ground rules:**

1. Claims in discussion must carry an evidence level (E0–E5) and observation context; otherwise they are treated as E0.
2. Rebut the semantics, not the speaker.
3. Conclusions are revisable; revisions are recorded.
4. Standard changes go through the `proposals/` AUP; Discussions is where they start.
5. No token-price talk, no promotion — this is a workshop, not a marketing channel.

**Once Discussions is enabled:** create the categories, pin a welcome post, pin the
Benchmark Draft 0.1 review thread, and pin the Measurement Report #001 feedback thread.
