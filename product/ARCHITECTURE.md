# AgentMeasure Product Architecture（Draft 0.4.1）

## 1. 四层架构（Provider 侧）

```text
Provider SDK
    ↓（异步、批量、本地缓冲）
Local Buffer / Collector
    ↓（重试 / 背压）
Hosted Ingestion
    ↓
Metrics / Dashboard
```

### Runtime 侧（可选，未来）

```text
Runtime Adapter（Claude/Codex/DSH）
    ↓
Collector（本地，与 provider 侧同构）
```

## 2. 工程原则（不可谈判）

| 原则 | 含义 |
| --- | --- |
| **主业务 fail-open** | SDK 异常、缓冲满、网络断——绝不阻塞或拖慢被度量的 capability 请求 |
| **测量 fail-closed** | 观察不完整/冲突时，宁可不计数也不猜测（Core fail-closed） |
| **异步 batching** | 观察异步批量上报，不在请求关键路径上（不变量：AgentMeasure 不在关键路径） |
| **durable best-effort buffering** | 磁盘缓冲 + 重试；缓冲满丢最旧并**显式记账**（dropped_observation_count）；不承诺"断网不丢" |
| **source_sequence** | 每个观察源携带单调递增序号；云端据此检出缺口（丢 1004-1006 立即可见） |
| **重试 / 背压** | 指数退避重试；服务端 429/5xx → 背压到本地缓冲 |
| **默认无内容** | prompt / input / output / 路径 默认不采集（PRIVACY.md 红线，代码级） |
| **伪匿名先于落盘** | 内存内 pseudonymize（usage.py 模式），原始标识符不落盘 |
| **确定性** | 同一输入 + 同一 policy → 同一指标（不变量 1） |

## 3. 组件

```text
agentmeasure-sdk            Provider 侧观测库（语言绑定：Python 先行）
agentmeasure-buffer         ​​本地缓冲（磁盘队列，崩溃恢复）
agentmeasure-collector      归一 / 关联 / 聚合（复用 reference/collector）
agentmeasure-ingest         ​​托管接收（OTLP 或原生 JSONL，带鉴权与配额）
agentmeasure-store          聚合存储（指标 + 原始观察的保留策略）
agentmeasure-dashboard      指标面板（MVP 字段见 HOSTED-ANALYTICS.md）
```

## 4. 数据流（一次调用）

```text
capability 请求进入
    ↓（SDK hook：仅元数据；context/validity 默认 unknown）
observation 构造（surface_id / tool / outcome / duration / caller_claim / source_sequence）
    ↓
本地缓冲（伪匿名后落盘；durable best-effort + 丢失记账）
    ↓（批量，退避重试）
Hosted Ingestion（校验 envelope → source_sequence 缺口检测 → 入库）
    ↓
Collector（match → derive operations（fail-closed）→ aggregate）
    ↓
Dashboard（Observed requests / Resolved Operations / Resolution Coverage / Success / Retry / Latency / Caller / Coverage）
```

## 5. 拓扑

| 拓扑 | 谁装 SDK | 能测什么 | 声称限制 |
| --- | --- | --- | --- |
| Provider-only（MVP） | Capability Provider | operation / attempts / result / caller_claim | 无选择数据；caller 身份按声明强度披露 |
| Runtime-only | Agent runtime | presentation / choice / consumption | 无执行细节（见 adapters 矩阵） |
| 双侧 | 两者 | 完整谱系 + cross-side corroborated | — |
