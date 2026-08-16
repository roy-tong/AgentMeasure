# agent-used-dsh — DeepSeek Harness Adapter（设计）

> DSH 是 agent-used 的第一方深集成目标：everything is a plugin；base profile 原生包含 telemetry；
> tool 执行暴露 `pre-execute / execute / post-execute` seam；session 是可持久化事件流。
> 目标：证明同一套 Usage Attribution Spec 横跨 Codex / Claude Code / DSH。

## 1. 架构

```text
DSH（DeepSeek Harness）
 └ agent-used plugin（Cordis plugin）
      ├─ listen tools/pre-execute     → S1 Executed 起点
      ├─ listen tools/post-execute    → outcome + duration + S2
      ├─ correlate session events     → session 级归一
      ├─ emit OTel（agentused.* 扩展属性）
      └─ generate safe usage records → 本地 collector
```

## 2. 事件映射（spec/otel-mapping.md）

| DSH 事件 | agent-used 字段 |
| --- | --- |
| tools/pre-execute（tool 名、trace_id、session） | stage=S1, observer_side=client, provenance=platform |
| tools/post-execute（outcome、耗时、trace_id） | stage=S2, outcome, duration_bucket |
| skill 加载 | surface=skill（能力获取，S0 Selected 的 proxy） |
| job / subagent / goal 上下文 | session_id 伪匿名化 |

## 3. 为什么 DSH 能给出 E2/E3 级证据

DSH 与 Codex/Claude Code 的关键差异：**harness 本身是 runtime**。
- 插件运行在 harness 内，工具调用经过 harness 的执行 seam——不是外部 hooks 观察，而是执行链路的原生部分
- `observer.side=client` + provenance=`platform`：接近 E3 的强证据（harness 原生证明）
- 若工具侧同时接入 wrapper/OTel，trace_id 传播 → E2 双边关联同样成立

## 4. 实现计划

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| P1 | Cordis plugin 骨架：注册 tools/pre-execute、post-execute 监听 | 待开发 |
| P2 | 事件归一 + 伪匿名 session + 本地 JSONL 落盘 | 待开发 |
| P3 | OTel span 输出（agentused.* 属性） | 待开发 |
| P4 | 与 collector 打通：本地 collector 消费 → E2/E3 统计 | 待开发 |
| P5 | 公开 demo：DSH 侧真实使用数据 → 徽章 | 待开发 |

## 5. 验证标准

- [ ] 插件安装后，DSH 每次工具调用产生 1 条本地 usage 记录
- [ ] 记录含 trace_id 且与工具侧一致时可关联为 E2
- [ ] 敏感字段零泄漏（复用 redactor 泄漏测试）
- [ ] 同一 project 在 Codex + DSH 双宿主数据可并入同一统计
