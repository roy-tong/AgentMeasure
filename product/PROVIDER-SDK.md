# AgentMeasure Provider SDK（Draft 0.4.2 — in development）

> Provider 侧观测库：让 capability 的**真实请求与结果**在 Provider 侧被度量——
> 不做 Agent 归属的猜测。产品定位：**Provider-observed Capability Usage**
> （Agent-facing Usage Analytics），不是"Real Agent Usage"。

## 1. 三步模型：Observe first, qualify later

```text
Observation    SDK 只做这个：某个 Interaction Surface 收到了一次请求，并产生了这个结果
    ↓
Qualification  collector 做：production? valid? duplicate? replay? synthetic?
    ↓
Attribution    collector/产品做：was it an agent? which runtime? which operation?
```

**SDK 永远不回答"这是不是 Agent 使用"**。它只产生观察事实。

```text
Provider sees a request               ≠ Agent usage
Provider sees MCP clientInfo=Claude   = declared Agent usage（自声明）
Provider event + runtime event        = correlated Agent usage（双侧证据）
```

## 2. 默认值：unknown，只有证据才升级

```text
usage_context = unknown        # 默认
validity = unknown             # 默认
```

升级路径（示例）：

```text
部署者配置 deployment_environment=production
  → context = production, context_source = provider_configuration

collector 检测 duplicate / replay / synthetic marker / healthcheck rule
  → validity 派生（validity_source = collector_derived）
```

SDK/collector 必须携带分类来源：

```jsonc
"context":  {"value": "production", "source": "provider_configuration"},
"validity": {"value": "normal",     "source": "collector_derived"}
```

**绝不默认 production/normal**——CI、benchmark、health check、cron、人工 API 调用
只要进了 production server 就会被误计为 Strict Qualified，污染公开数字。

## 3. Provider-only 只天然产生 Attempt

```text
HTTP request / MCP call
    = Attempt（一次真实执行）
```

**Operation（逻辑使用）需要 resolution evidence**：

```text
✓ runtime 传播统一的 operation_id
✓ API 有 idempotency key
✓ runtime-side + provider-side correlation（共享 call_id/trace/token）
✓ provider 自己知道 retry chain（同请求方连续重试的严格证据）
✗ 其他情况 → operation_id = null, operation_resolution = unknown（fail-closed）
```

3 次超时重试在 Provider 侧通常是 **3 个 Attempt、0 个可证 Operation**——这不可耻，
这是诚实的测量，也是 AgentMeasure 价值的证明（没有它，Metering 无法区分）。

## 4. Caller Identity Confidence（硬约束）

```text
caller_type
├── unknown              无法判定（默认）
├── claimed_agent        caller 自声明（User-Agent / MCP clientInfo / 协议字段）
├── correlated_agent     Provider 观察 + 独立 runtime 观察 + 共享 call_id/trace/token
└── platform_attested    runtime 平台证言（未来；未验证 MUST 显示 UNSUPPORTED）

caller_identity_strength
├── unknown
├── declared             自声明（UA/clientInfo 只到这一级！）
├── correlated           双侧独立证据（≠ UA 匹配）
└── attested             平台证言
```

**UA / MCP clientInfo 匹配永远只是 `declared`，不是 `correlated`。**
真正的 correlated 必须同时满足：Provider Observation + 独立 Runtime Observation +
共享关联键。

Dashboard 必须显示 `Claude Code (declared)`，而不是 `Claude Code`。

## 5. 观测字段（元数据 only）

见 Core DATA.md Envelope；SDK 补充：

```jsonc
"surface": {"surface_id": "mcp_tool:research", "surface_namespace": "io.github.foo"},
"caller": {"type": "claimed_agent", "runtime": "claude", "identity_strength": "declared"},
"source_sequence": 1007,          // 单调递增；云端据此发现丢失（1004-1006 缺失）
"dropped_observation_count": 3    // SDK 自身丢了多少（进入 Measurement Coverage）
```

## 6. SDK 行为要求

| 要求 | 实现 |
| --- | --- |
| fail-open | 任何异常 → 记录并继续业务，绝不抛出到 handler |
| 异步 | 观察入队即返回；worker 批量上报 |
| 缓冲 | **durable best-effort**：磁盘队列 + 显式丢失计数（不承诺"断网不丢"） |
| 背压 | 上报失败指数退避；缓冲满丢最旧，`dropped_observation_count` 随下批上报 |
| 幂等 | observation_id 唯一；source_sequence 供云端缺口检测 |
| 零内容 | prompt/input/output/路径 代码级不可达（redactor 测试覆盖） |

## 7. 非目标（MVP）

- ❌ 不做选择/呈现观察（runtime 侧信号；Provider-only 拓扑没有）
- ❌ 不做消费链（无 agent 侧信息）
- ❌ 不做计费（COMMERCIAL 是语义，不是执行）
- ❌ 不猜 caller 身份（分级披露，绝不提升声明强度）
- ❌ 不把请求解释成"Agent 使用"（只报告 Observed requests + attribution 分层）
