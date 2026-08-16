# AgentMeasure Data — Observation Envelope（Draft 0.3）

> Receipt 是系统间流动的最小签名单位；本版本定义六类观察的 Envelope，
> 使 schema 真正表达 Presented/Selected/Invoked/Completed/Consumed。

## 1. Observation Envelope（统一外壳）

```jsonc
{
  "spec_version": "agentmeasure-0.3",
  "observation_id": "uuid",
  "observation_type": "presentation | selection | invocation | completion | consumption | task_outcome",
  "observer": {"principal": "codex-hook@acme", "trust_domain": "acme", "side": "client"},
  "observed_at": "2026-08-16T03:00:00Z",
  "project_id": "github.com/foo/bar",
  "tool_id": "foo.search",
  "client_key": "p-...",              // 伪匿名，内存内生成
  "usage_context": "production",      // 见 AgentMeasure Core §7
  "validity": "normal",               // 见 AgentMeasure Core §7
  "sampling": null,
  "provenance": "hook",
  "payload": { /* 类型特有字段 */ },
  "signature": "base64", "key_id": "k1"
}
```

## 2. 六类 Payload

### presentation
```jsonc
{ "decision_id": "d1", "candidate_set_id": "cs1", "category_id": "search.web.general",
  "category_version": "v1", "choice_mode": "exclusive", "rank_in_candidate_set": 3 }
```

### selection
```jsonc
{ "decision_id": "d1", "selection_id": "s1", "rank": 1,
  "selection_reason_observable": false }
```

### invocation
```jsonc
{ "tool_call_id": "tc-9", "trace_id": "t-9", "started_at": "..." }
```

### completion
```jsonc
{ "tool_call_id": "tc-9", "outcome": "success|failure|denied", "duration_ms": 1200,
  "error_type": null }
```

### consumption
```jsonc
{ "tool_call_id": "tc-9", "consumed_by_request_seq": 42 }   // 后续请求实际使用
```

### task_outcome
```jsonc
{ "task_id": "tk-1", "task_success": true, "model": "gpt-5.6",
  "task_type": "research", "ended_at": "..." }
```

## 3. 签名与 canonical（不变）

- SIGNED_FIELDS 覆盖全部 attribution 字段（AgentMeasure Core 不变量 5）
- canonical JSON：排序键、无空白、NFC（确定性字节）
- 六类 payload 的 attribution 字段全部入签名

## 4. Manifest / Aggregate Statement（不变，见 Draft 0.1 版）

## 5. 纪律

- 一类观察一个 Envelope；不把多类塞进一条
- 不可观察的状态不产生观察（UNOBSERVABLE 是元级信息，在 Profile 能力矩阵声明，
  不伪造 FALSE 观察）
