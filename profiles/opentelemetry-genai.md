# AgentMeasure Interoperability Profile — OpenTelemetry GenAI

> Draft 0.4.4 / Draft 0.5 方向。Route B：已有 telemetry → Mapping Profile → Canonical Observation。
> AgentMeasure 不要求成熟 observability 项目接入 SDK；本 profile 定义如何把 OTel GenAI 语义
> 映射为 AgentMeasure 的 Attempt / Operation / Consumption 对象。

## 映射表

| OTel GenAI | AgentMeasure | 说明 |
|---|---|---|
| `gen_ai.operation.name` | Attempt（执行层） | 一次 model 调用 = 一个 attempt 候选 |
| `gen_ai.agent.name` | Caller 线索（claimed） | agent 身份声明，非 attestation |
| `gen_ai.usage.input_tokens` | attempt_usage.uncached_input（当 cache 未拆分时=total input） | 消费归 attempt |
| `gen_ai.usage.output_tokens` | attempt_usage.output_tokens | 含 reasoning subset（见下）|
| `gen_ai.usage.reasoning.output_tokens` | attempt_usage.subquantity reasoning | **subset，不相加** |
| `gen_ai.client.token.usage{token_type}` | 仅 input/output 两桶 | reasoning 不作为第三个 token_type（DR-003）|
| `gen_ai.system` / `gen_ai.provider.name` | provider_side 证据 | 跨侧 correlation 键之一 |
| span `trace_id` / `span_id` | external_ids（correlation 证据） | 非 AgentMeasure identity |
| `gen_ai.completion`（完整响应） | result / effect 证据候选 | 是否被 downstream 消费 → probe vs use |

## 关键规则
1. **OTel span ≠ Operation**：一个 trace 内的多次 span 未必是同一 operation；operation 归并
   遵循 CORR §3.1（explicit id / idempotency / structural inference）。
2. **消费归 attempt**：input/output tokens 记录在产生它们的 span/attempt 上。
3. **reasoning ⊆ output，不相加**（DR-003）。
4. **cache 明细缺失 → cache allocation = unknown**，不做 fabricated normalization。

## 状态
Draft。与 OTel GenAI semantic conventions 对齐（2026-08 版本）。
