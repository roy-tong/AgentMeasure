# Identity（Canonical Identity Graph）

> 回答：这条 usage 属于哪个项目？同一项目的不同形态（repo/npm/MCP server/tool/CLI/skill）如何归一？

## 1. 问题

一个项目有多个身份形态：

```text
github.com/foo/bar          ← repo
@foo/bar-mcp               ← npm 包
io.github.foo/bar          ← MCP registry
bar.search / bar.fetch     ← tools
bar-cli                    ← CLI
bar-skill                  ← skill
```

如果各自计数，同一个项目会被拆成 6 份数据——排名与统计都会失真（也给了拆 API 刷榜的空间）。

## 2. 身份模型

```text
Project（归一身份，唯一）
  ├─ id: github.com/foo/bar（优先 GitHub 身份）
  ├─ aliases: [npm, registry, cli, skill, ...]
  ├─ tools: [bar.search, bar.fetch, ...]
  └─ evidence: {declared, verified}
```

### 身份来源与优先级

| 来源 | 提供 | 优先级 |
| --- | --- | --- |
| GitHub repo（声明） | canonical id、ownership | 1 |
| MCP registry | server/publisher identity | 2 |
| npm / package | package name、version | 3 |
| 工具自身声明（adapter 配置） | tool 集合、project.id | 4 |

### 归并规则

- 工具作者在 adapter 配置中声明 `AGENT_USED_PROJECT=github.com/foo/bar` → 显式声明（最高）
- 未声明时按来源优先级推断（registry → npm → repo）
- 冲突时：声明优先；无声明则分开展示并标记 `unresolved`

## 3. 注册表（registry/project-identity）

- 维护公开映射：`project.id ↔ aliases ↔ tools`
- 由工具作者提交（PR/表单），机器可读（JSON）
- 作为 Usage Attribution Layer 的基础数据面之一

## 4. 与 MCP Registry 的关系

MCP Registry 解决"这个 server 是谁"；agent-used identity graph 解决"这些形态属于同一个谁"。
两者互补：registry 提供权威身份起点，agent-used 在其上做 alias 归并与使用数据挂载。

## 5. 度量纪律

- 所有公开统计按 project roll-up 后展示（tools 明细可下钻）
- 排名、adoption、engagement 均以 project 为单位
- raw tool-level 数据仅用于作者自查与下钻
