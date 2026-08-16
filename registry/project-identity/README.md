# project-identity registry

> Canonical Identity Graph 的数据面（spec/identity.md）。
> 由工具作者提交（PR），机器可读：`project.id ↔ aliases ↔ tools`。

## 格式（每个项目一个 JSON 文件，`<owner>-<repo>.json`）

```jsonc
{
  "project_id": "github.com/foo/bar",
  "name": "bar",
  "aliases": {
    "npm": "@foo/bar-mcp",
    "mcp_registry": "io.github.foo/bar",
    "cli": "bar-cli",
    "skill": "bar-skill"
  },
  "tools": ["bar.search", "bar.fetch", "bar.create"],
  "declared_by": "github.com/foo/bar",   // 声明来源
  "verified": false                       // 由 AgentMeasure 验证后置 true
}
```

## 提交方式

- 工具作者 fork 本仓库 → `registry/project-identity/<owner>-<repo>.json` → PR
- 或通过 `agentmeasure register --project github.com/foo/bar --npm @foo/bar-mcp`（待实现）

## 示例

- [roy-tong-AgentMeasure.json](roy-tong-AgentMeasure.json)：AgentMeasure 自身（dogfooding）
