# GitHub Launch Pack（复制粘贴即用）

> 需要 Roy 在 GitHub UI 完成（无 token，agent 无法代做）。三步约 5 分钟。

## 1. Repository Settings → About

**Description**（粘贴）：

```text
Open measurement infrastructure for the Agent Capability Economy — how AI agents discover, choose, use, and derive value from software capabilities (Reach → Choice → Use → Utility → Value). A proposed open measurement standard.
```

**Website（homepage）**：

```text
https://roy-tong.github.io/en/notes/how-agent-usage-should-be-measured/
```

**Topics**（逐个添加，共 10 个）：

```text
ai-agents  agent-tools  measurement  metrics  standards
mcp  opentelemetry  llm  agent-economy  open-standard
```

## 2. Discussions（Settings → General → Discussions → Set up）

Categories（按顺序创建）：

| Category | 说明 |
| --- | --- |
| Metric Semantics | 指标定义/分母/eligibility 讨论（对应 Issue Template #1） |
| Runtime Observation | runtime 观察能力边界（对应 #2） |
| Experiments | 实证实验设计与结果 |
| Capability Economy | CaaS 叙事与商业语义 |
| Implementers | 第三方实现者互通（conformance） |

## 3. 发布后 48h 内的运营动作

1. 在 Discussions「Metric Semantics」发第一篇：**"Is Strict Qualified Usage the right default for public metrics?"**（带 QUALITY.md 链接）——制造第一个讨论
2. 在仓库开第一个 issue：**"First external Provider onboarding"**（邀请 MCP 开发者接入 SDK，附 Measurement Report #001 链接）
3. 用 Docs → 首页 pinned 两条：README + Whitepaper

## 4. 传播引用素材（4 类内容）

见 docs/MARKETING.md 与 publish_agent/thread.json（X 线程已按
Concrete Problem → Real Data → Framework → Thesis 排序）。
