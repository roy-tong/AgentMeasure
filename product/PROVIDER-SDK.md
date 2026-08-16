# AgentMeasure Provider SDK（Draft 0.4.1 — in development）

> Provider 侧观测库：让 capability 的**真实 agent 使用**在 Provider 侧被度量，
> 无需 Agent 侧安装、无需开源、不在请求关键路径上。

## 1. 契约（SDK 做什么）

```text
输入：capability 请求/响应边界（业务 handler 内一行调用）
输出：Observation Envelope（Core DATA.md），伪匿名、异步、批量
```

```python
# 概念示例（Python 先行）
from agentmeasure import observe

@observe(capability="company.research", surface="mcp_tool:research")
def handler(request):
    return run_search(request)
```

SDK 自动构造：operation_id（按调用绑定）、tool_call_id、outcome、duration_bucket、
surface_id、caller_claim（见 §2）、usage_context / validity（默认 production/normal，
业务可覆盖）。

## 2. Caller Identity Confidence（硬约束）

普通 HTTP API 服务器通常只能知道"有客户端调用了"，不能知道是不是 Agent。
因此 SDK 必须分级披露身份强度——**Dashboard 必须显示 `Claude Code (declared)`，
而不是 `Claude Code`**：

```text
caller_type
├── unknown              无法判定（默认）
├── claimed_agent        caller 自声明是 agent（User-Agent / 协议字段）
├── correlated_agent     与已知 agent runtime 信号关联（trace/UA 匹配）
└── platform_attested    runtime 平台证言（未来，需验证，不信任字符串）

caller_identity_strength
├── unknown
├── declared             自声明（弱）
├── correlated           关联证据（中）
└── attested             平台证言（强，未验证前 MUST 显示 UNSUPPORTED）

caller_runtime           claude | codex | deepseek-harness | other | unknown
```

规则：
- `platform_attested` 未经验证前 MUST 显示为 `UNSUPPORTED`（不变量 11）
- 身份强度 MUST 随每个 observation 携带，聚合时按强度分层披露
- 声称纪律：`declared` 的数据永远不能表述为"Agent 使用量"——只能表述为
  "Agent 声明使用量（declared）"

## 3. 观测字段（元数据 only）

见 Core DATA.md Envelope；SDK 补充 `caller` 块：

```jsonc
"caller": {
  "type": "claimed_agent",
  "runtime": "claude",
  "identity_strength": "declared"
}
```

## 4. SDK 行为要求

| 要求 | 实现 |
| --- | --- |
| fail-open | 任何异常 → 记录并继续业务，绝不抛出到 handler |
| 异步 | 观察入队即返回；worker 批量上报 |
| 缓冲 | 磁盘队列，进程崩溃可恢复 |
| 背压 | 上报失败指数退避；缓冲满丢最旧并披露 drop 计数 |
| 幂等 | observation_id 唯一；重试不重复计数 |
| 零内容 | prompt/input/output/路径 代码级不可达（redactor 测试覆盖） |

## 5. 非目标（MVP）

- ❌ 不做选择/呈现观察（那是 runtime 侧；Provider-only 拓扑没有该信号）
- ❌ 不做消费链（无 agent 侧信息）
- ❌ 不做计费（extensions/COMMERCIAL.md 是语义，不是执行）
- ❌ 不猜 caller 身份（分级披露，绝不提升声明强度）
