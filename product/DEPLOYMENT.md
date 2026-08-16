# AgentMeasure Deployment（Draft 0.4.1）

## 两种模式

| | Self-hosted | Hosted |
| --- | --- | --- |
| 谁运行 | Provider 自己 | AgentMeasure 托管 |
| 数据去向 | 自己的存储 | 托管 ingestion（可配置保留期） |
| 适合 | 数据主权敏感 / 企业 | 快速开始 / 中小 Provider |
| 支持 | Collector + Dashboard 本地部署 | Hosted Analytics（产品线） |

**默认立场**：数据留在本地是标准的使用方式（不意味着向任何中心服务器上传数据）。
Hosted 是显式选择。

## 组件部署

```text
┌─ Provider 环境 ─────────────────────────────┐
│  app / MCP server / API                     │
│    └─ agentmeasure-sdk（进程内，fail-open）  │
│         └─ agentmeasure-buffer（磁盘队列）    │
└──────────────────────┬──────────────────────┘
                       │ 批量上报（异步）
              ┌────────▼────────┐
              │  ingest 端点     │  ← self-hosted: 自建 collector
              └────────┬────────┘     hosted: agentmeasure.cloud
                       ▼
              collector → store → dashboard
```

## 环境变量（沿用 reference 约定）

```text
AGENTMEASURE_EVENTS_DIR    本地事件目录（默认 ~/.agentmeasure/events）
AGENTMEASURE_INGEST_URL    hosted/self-hosted 上报端点（空 = 仅本地）
AGENTMEASURE_API_KEY       ingest 鉴权（hosted 必填）
AGENTMEASURE_BUFFER_LIMIT  缓冲上限（默认 10k 条，超出丢最旧并披露）
AGENTMEASURE_OPTIN         显式开启上报（默认仅本地）
DO_NOT_TRACK=1             完全禁用
```

## 隐私部署要求（代码级）

1. 伪匿名在**落盘前、内存内**完成（usage.py pseudonymize）
2. prompt / input / output / 路径 默认不采集；采集即违反 PRIVACY.md
3. 原始 session / caller 标识不离开 Provider 环境（除非显式 opt-in 且经伪匿名）
4. 保留策略 MUST 可配置；删除后不可恢复

## 运维

- 健康检查：缓冲积压深度、上报失败率、丢弃率（Measurement Coverage 的一部分）
- 背压：ingest 429/5xx → 指数退避；持续失败 → 本地保留 + 面板披露 coverage 下降
- 版本对齐：SDK 与 Collector 的 spec_version 必须一致（envelope 校验）
