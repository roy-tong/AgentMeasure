# agent-used

**agent-used 是 [AUAS](whitepaper/AUAS.md)（Agent Usage Attribution Standard）的参考实现。**

> OpenTelemetry tells us how telemetry travels.
> **AUAS defines what evidence, under what rules, can support what conclusions.**

AUAS 定义 AI Agent 软件使用证据如何被表示、认证、关联、定级与聚合，使不同主体
能够在不依赖单一平台、不采集用户内容的前提下，对 Agent 软件使用情况进行可验证、
可比较的测量。

**AUAS 不定义谁是真相来源，而定义什么证据、按照什么规则，可以支持什么结论。**

这不是又一个 Agent observability 工具。Langfuse / Grafana 回答"我的 Agent 运行得
怎么样"；AUAS 回答"整个生态里，哪些第三方工具真的被 Agent 使用——以及凭什么
相信这些数字"。

[Canonical Whitepaper (EN)](whitepaper/AUAS.md) · [《如何测量 Agent Tool Economy》（中文）](whitepaper/agent-tool-economy-zh.md) · [AUAS-CORE](spec/measurement-spec.md) · [English](README.en.md)

## Try it in 2 minutes

```bash
# 1. 安装（零依赖，Python 3.9+）
git clone https://github.com/roy-tong/agent-used && cd agent-used

# 2. 模拟一次双侧调用（client + server 观察同一 tool_call_id）
python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from collector.correlator.correlator import connect, store_observation, match_invocations
from collector.aggregator.aggregator import compute
from collector.usage import empty_observation, new_observation_id

conn = connect()  # ./collector.db
for side, principal in (("client", "codex-hook@you"), ("server", "mcp-wrapper@you")):
    o = empty_observation(); o.update(dict(
        observation_id=new_observation_id(), observed_at="2026-08-16T03:00:00Z",
        observer_principal=principal, observer_side=side, provenance="hook" if side=="client" else "wrapper",
        project_id="github.com/you/your-tool", tool="your.search", tool_call_id="tc-1",
        session_key="sess-1" if side=="client" else None, outcome="success", lifecycle_stage="L2"))
    store_observation(conn, o)
match_invocations(conn)
print(compute(conn, "github.com/you/your-tool")["corroborated_share"])  # 1.0 = 双侧独立佐证
PY

# 3. 数据全在本地。README 徽章（M4 后公开）
```

## 核心概念

### 使用漏斗：Install ≠ Usage

| 阶段 | 定义 | MVP |
| --- | --- | --- |
| S0 Selected | Agent 选择了该工具 | ✅ |
| S1 Executed | Runtime 实际执行了调用 | ✅ |
| S2 Execution Success | 工具成功返回 | ✅ |
| S3 Result Consumed | Agent 实际使用了返回结果 | 🔶 部分 |
| S4 Task Contribution | 结果对下游任务有贡献 | 🔬 研究 |

### 证据等级：签名 ≠ 真实

| 等级 | 名称 | 能证明什么 |
| --- | --- | --- |
| Observed | 单边观察 | 某一方声称 |
| Authenticated | Ed25519 签名观察 | 来源与完整性 |
| **Corroborated** | ≥2 条独立 observer 观察 | **同一次真实调用（核心）** |
| Independently Corroborated | 跨 trust domain 的独立观察 | 最强可获证据 |
| Platform Attested | 平台 attestation（未验证 = UNSUPPORTED） | 平台确认 |

签名只证明"数据来自持 key 主体且未被篡改"，不证明"真的有 Agent 调用"——所以证据是分级的（由 verifier 计算，adapter 不自声明），`independently corroborated`（≥2 个独立 trust domain 的观察）才是可信度核心。

### 指标：Raw Calls 不是北极星

- **Adoption**（首要）：ACD（Active Client-Days，按 Measurement Policy 限定口径）
- **Engagement**：Repeat Usage、7d/30d 回访率
- **Quality**：Execution Success / Result Consumption
- **Trust**：Corroborated Usage Share

排名按 sessions 而非 calls——防拆 API 刷榜。一次任务 6 次调用 ≠ 6 倍使用。

## 架构

```text
Public Usage Layer（Dashboard / API / Badge / Rankings / Trends）
        ▲   aggregated only
agent-used Attribution Layer
  Identity Resolution · Dedup · Cross-side Correlation
  Evidence Grading · Privacy Aggregation · Metric Normalization
        ▲               ▲
 Agent Adapters        Tool Adapters
  codex / claude / dsh   mcp / http / cli
        ▲               ▲
   OTel / MCP existing standards
```

agent-used **站在 OTel 之上**：复用 `gen_ai.tool.name`、`mcp.method.name`、trace 字段；只增加 6 个 `agentused.*` 扩展字段（[otel-mapping](spec/otel-mapping.md)）。

## 目录

```text
agent-used/
├── spec/          # 标准（测量/证据/指标/隐私/身份/威胁模型/OTel 映射）
├── adapters/
│   ├── codex/           # PostToolUse hooks → 本地事件
│   ├── claude-code/     # OTLP → agent-used Collector（设计）
│   ├── deepseek-harness/# DSH plugin（tools/pre-execute → post-execute，设计）
│   └── mcp/             # legacy zero-config wrapper（wrapper.py）
├── collector/
│   ├── normalizer/      # 跨 Agent 统一口径（待实现）
│   ├── correlator/      # 双边 trace 匹配 → E2（待实现）
│   ├── redactor/        # 默认 DROP 敏感字段（待实现）
│   └── aggregator/      # 本地统计 + 徽章 SVG（已有 aggregator.py）
├── registry/
│   └── project-identity/ # 项目身份映射（待填充）
├── examples/
└── whitepaper/          # 《如何测量 Agent Tool Economy》
```

## 隐私

**Raw telemetry stays local. Public infrastructure receives aggregates by default.**

prompt / tool_input / tool_output / path / raw session id——代码级默认 DROP（adapter 含泄漏测试）。伪匿名 installation id（本地 secret + 按月轮换）支持 unique installations 与 repeat usage，云端无法反推身份。`DO_NOT_TRACK=1` 全程生效。

## 当前状态（M1-M2）

跨宿主统一已跑通：codex hook（client）+ MCP wrapper（server）+ DSH plugin（harness 生命周期观察）
三类 observation 可并入同一 project 统计——`invocations / corroborated share / ACD / host 分布`，
证据由 verifier 计算（adapter 只报事实）。

```bash
# 导入三类事件 → 关联 → 统计
python3 -m collector.correlator.correlator   # 见测试：correlate() 生成 E2
python3 collector/aggregator/aggregator.py stats --project github.com/foo/bar
```

## 路线图

| Stage | 目标 | 关键产物 |
| --- | --- | --- |
| M0 Definition | 讲清"什么算 Agent Usage" | ✅ Whitepaper + Measurement Spec + Threat Model |
| M1 Cross-Agent Proof | 证明跨 Agent 可统一 | Codex + Claude + DSH adapter |
| M2 OTel Native | 标准采集链 | Collector + OTel mapping + MCP adapter |
| M3 Attribution | 项目核心 | Identity Graph + Correlation + Evidence |
| M4 Public Network | 公开数据 | API + Dashboard + Badge |
| M5 External Validation | 指标是否真被需要 | 外部项目接入 + discrepancy report |
| M6 Ecosystem | 公共基础设施 | MCP / OTel / Agent Platform / Registry 合作 |

**不做的事**：不替代 OTel；不做自动 star/follow；不采集内容；不按 raw calls 排名；不在 M3 之前做聚合云。

## License

MIT
