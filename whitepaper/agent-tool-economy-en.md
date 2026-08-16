# How to Measure the Agent Tool Economy

**An Open Standard for Usage Attribution in the Agent Ecosystem**

> By Roy Tong · Product Manager · Serial Entrepreneur
> Reference implementation: [agent-used](https://github.com/roy-tong/agent-used)
> Status: v1 draft, evolving with community discussion

## The question

**What does it mean for software to be "used by an agent"?**

In 2026, agents are becoming the most important new distribution channel for software. Claude Code, Codex and DeepSeek Harness pick tools for users, install skills and call MCP servers. Tool authors face a question they cannot answer: **is my tool actually being used by agents?**

Every existing signal fails:

- GitHub stars/clones show humans, not agents
- skills.sh installs are self-reported telemetry (gameable, no API, no verification)
- The MCP registry explicitly publishes no adoption data
- llms.txt: declared — a study of 137K sites found that among sites publishing a valid llms.txt, 97% of files received zero requests in May 2026

The first job of this paper is not to give answers, but to define the question properly.

## The conceptual contribution: usage is not an event, it's a chain

The tool ecosystem once assumed: downloaded = used. Agents break that assumption completely.

```text
Install ≠ Usage
Discovery ≠ Selection
Selection ≠ Execution
Execution ≠ Success
Success ≠ Consumption
Consumption ≠ Contribution
```

Each layer is not a proxy for the next:

| Stage | Definition | Observable by | Meaning |
| --- | --- | --- | --- |
| S0 Selected | Agent chose the tool | Agent runtime | discovered and picked |
| S1 Executed | Runtime actually ran the call | both sides | choice became behavior |
| S2 Execution Success | Tool returned successfully | both sides | behavior became a result |
| S3 Result Consumed | Agent used the returned result | Agent runtime (partial) | result became input |
| S4 Task Contribution | Result contributed to downstream completion | research | input became value |

**A successful call is not a useful tool.** A tool that is repeatedly called but whose results are never used is indistinguishable from one that was never called. Long-term, **Result Consumed Rate matters more than Tool Calls** — that is the most important research direction in this framework.

## Evidence grading: signature is not truth

Open ecosystems have no absolute ground truth. Any claim of objectivity must answer: **how do you know?**

A tool author can generate one million fake calls and HMAC-sign them with their own key — all legally signed. HMAC proves "this data came from the key holder and was not modified in transit." It does not prove "a real agent called this."

So measurement must replace binary judgment with evidence levels:

| Level | Name | Proves | Public-stat credibility |
| --- | --- | --- | --- |
| E0 Observed | One-sided log | one party claims | low |
| E1 Source-authenticated | Signed event | origin and integrity | medium-low |
| **E2 Correlated** | Both sides independently observed, matched | the same real call | **high (core)** |
| E3 Platform-attested | Platform directly confirms | platform confirms | very high |

**E2 is the technical breakthrough point**: when the agent side and the tool side independently record the same call via the same OTel trace (`trace_id`), neither side can fabricate the other's observation. That constitutes **corroborated usage**.

The the MCP 2026-07-28 specification folds OTel trace context (`traceparent / tracestate / baggage`) into `_meta` — **protocol-level two-sided correlation is now real**. This is the framework's most important technical foundation: we did not invent trace propagation; we define, for the first time, what counts as a credible usage once traces align.

## The measurement model: six elements

```text
Agent Usage Measurement Model
        ├─ Identity     which project does this belong to (repo↔npm↔MCP↔tool↔CLI↔skill)
        ├─ Observation  who observed (client / server / platform)
        ├─ Correlation  did both sides align (trace_id / tool_use_id)
        ├─ Evidence     how credible (E0-E3)
        ├─ Aggregation  how to normalize (session normalization, retry folding, anti-splitting)
        └─ Privacy      how to publish without leaking
```

**Identity** is the underrated hard part: one project has six identities across GitHub, npm, the MCP registry, tool names, CLIs and skills. Without normalization, one project becomes six data rows — rankings distort, and "split the API to farm the leaderboard" becomes viable. A canonical identity graph is the base asset of any measurement system.

## Metrics: why raw call count is not the north star

One agent completes a task in `search → fetch → parse` × 2 = 6 calls; another uses a highly encapsulated tool `research()` = 1 call. The first is not 6× the usage. A failing retry chain `call → fail → retry → success` produces 3 records.

Public metrics are therefore organized in four layers, in priority order:

1. **Adoption** (primary): Active Agent Sessions — sessions with verified usage in the last 30 days
2. **Engagement**: Repeat Usage, 7d / 30d return rates
3. **Quality**: Execution Success, Result Consumption
4. **Trust**: Corroborated Usage Share (E2 share)

Leaderboards rank by Active Sessions, never by raw calls — otherwise "split your tool into 50 APIs to farm the board" is inevitable.

## Relationship to existing standards: standing on top of OTel

agent-used does not replace OpenTelemetry, nor MCP:

- **OTel solves how telemetry travels**: trace propagation, spans, field conventions
- **MCP solves how tools are called**: the protocol, `_meta` trace context
- **agent-used solves what counts as usage**: semantics, evidence, identity, metrics, privacy

The implementation adds only six `agentused.*` extension fields (`project.id`, `observer.side`, `agent.host`, `provenance`, `evidence.level`, `project.version`); everything else reuses standard fields. If the OTel GenAI working group adopts them, the fields merge into the standard and agent-used degenerates into a pure semantic layer — that is the design goal.

## Architecture: the attribution layer

```text
Public Usage Layer (dashboard / api / badge / rankings / trends)
        ▲  aggregated only
Attribution Layer
  identity resolution · dedup · correlation · evidence grading
  privacy aggregation · metric normalization
        ▲                    ▲
 Agent Adapters            Tool Adapters
  codex / claude / dsh       mcp / http / cli
        ▲                    ▲
   OTel / MCP existing standards
```

Three agent-side adapters prove cross-platform unification:

- **Codex**: `PreToolUse / PostToolUse` hooks observe MCP, shell and local function tools; `prompt / tool_input / tool_output` are dropped by default — the adapter's purpose is not to record more, but to **prove this side really initiated the call**
- **Claude Code**: native OTLP output (metrics / events / traces); agent-used plugs in as an OTel processor/exporter — **users keep their existing observability backend**
- **DeepSeek Harness**: everything is a plugin; tool execution exposes a `pre-execute / execute / post-execute` seam; sessions are persistent event streams — the deepest first-party integration target

One measurement model spanning three completely different harnesses — that is what a standard means.

## Privacy: raw stays local

```
Raw events → local collector (identity/dedup/redact/aggregate/evidence) → SAFE AGGREGATES → public
```

The cloud never receives: prompt, input, output, path, email, username, raw session id. Pseudonymous installation ids (local secret, rotating epochs) support unique-installation and repeat-usage computation without reversible identity.

**Why "we never record arguments" is not enough**: that is a promise; the system is architecture. Redaction lives in the default path of the ingestion pipeline, making leakage impossible at the code level (adapters carry leak tests).

## Policy red lines

1. No automated starring or following (GitHub AUP explicitly prohibits automated starring)
2. No scraping of GitHub web pages (cross-checks use the official API)
3. No raw-call rankings (anti-splitting)
4. Measuring usage, not "reviews"

## Ecosystem path

Three partners are complementary, not competing:

| Partner | Solves | Role |
| --- | --- | --- |
| **Agent platforms** (OpenAI / Anthropic / DeepSeek) | who really called | highest authority on evidence (E3) |
| **GitHub** | whose project, where's the code | identity and ownership (repo identity, badge) |
| **MCP Registry** | who this server is | **the natural first ecosystem partner** — registry is identity, agent-used is actual usage; the registry explicitly reserves value-add metadata space for downstream aggregators (ratings, download counts, security results); usage attribution is naturally compatible with that architecture and is the direction agent-used aims to explore |

## Call to action

- **Tool authors**: adopt an adapter, look at your own real data first
- **Agent platforms**: open attestation interfaces — make usage proof a native platform capability
- **Standards community**: debate the S0-S4 funnel and E0-E3 evidence model — this is a draftable contribution to AAIF / OTel GenAI
- **Researchers**: measuring Result Consumption (S3) and Task Contribution (S4) is an open problem

**Drive the problem definition first, then the implementation.** This paper is the definition; [agent-used](https://github.com/roy-tong/agent-used) is the reference implementation.

---

*Feedback: GitHub Issues (agent-used repo) or X @elliwoodtong. Full specs in `spec/` (measurement-spec / evidence-model / metrics / privacy / identity / threat-model / otel-mapping).*
