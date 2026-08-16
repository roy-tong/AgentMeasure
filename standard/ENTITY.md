# AgentMeasure Entity — Software Entity Identity & Alias Resolution（Draft 0.4）

> 观察发生在 Interaction Surface 上，统计归属到 Software Entity。
> 本文定义：entity 身份是什么、surface → entity 如何解析、registry 的机器可读格式、
> 以及 alias 归并的 fail-closed 规则。

## 1. 身份模型

```
entity_id（规范标识，registry 权威）
   └── aliases：同一逻辑软件的不同形态
         ├── mcp_server: "io.github.foo/bar"        → surface: mcp_tool:bar.search
         ├── npm: "@foo/bar-mcp"                    → surface: function_call / mcp_tool
         ├── cli: "bar-cli"                         → surface: cli_command:bar-cli
         ├── skill: "bar-skill"                     → surface: skill_file
         ├── http: "api.bar.dev/v1"                 → surface: http_endpoint
         └── runtime_builtin: "file_edit"           → surface: runtime_builtin
```

- `entity_id`：唯一规范标识，形如 `github.com/<owner>/<repo>` 或 registry 分配
- `alias`：一种形态的稳定标识（MCP registry id、npm 包名、CLI 名、skill 名…）
- `surface_id`：一次具体观察中出现的界面标识（`mcp_tool:bar.search`、`cli_command:bar-cli`…）

## 2. 解析规则（fail-closed）

1. 观察记录 surface 层标识（`surface_id`），MUST NOT 在观察时猜测 entity
2. 解析顺序：exact alias match → registry 声明 → UNKNOWN
3. **无匹配时 entity 归属 = UNKNOWN，MUST NOT 按字符串相似度推断**
4. 一个 alias 同时被多个 registry 条目声明 = 冲突，归属 MUST 记 `ambiguous`，
   该观察不计入任何 entity 的计数（不变量 21）
5. 归并发生在统计层（aggregator），不发生在观察层（adapter）
6. alias 归并表 MUST 带版本（`registry_version`），公开指标 MUST 披露所用版本

## 3. 实体类型

见 AgentMeasure Core §2.1：Tool · Skill · API · Data Source · Agent ·
Application · Runtime Capability · unknown。类型影响 Utility 度量方式
（Interaction Class，见 Core §2.7），不影响计数。

## 4. Registry 格式（机器可读）

每个 Entity 一个文件：`registry/entities/<owner>-<repo>.yaml`，
schema 见 `schemas/entity.schema.json`（JSON Schema），CI 与本地
`python3 registry/validate_entities.py` 强制校验（零依赖实现：`registry/mini_yaml.py`）。

```yaml
schema_version: "agentmeasure-0.4"
entity:
  entity_id: github.com/foo/bar
  entity_type: tool            # tool | skill | api | data_source | agent | application | runtime_capability | unknown
  name: bar
  declared_by: github.com/foo/bar
  verified: false              # AgentMeasure 验证后置 true
  aliases:
    mcp_server: io.github.foo/bar
    npm: "@foo/bar-mcp"
    cli: bar-cli
    skill: bar-skill
  capabilities:                # 可选的 capability 声明（Taxonomy Draft 0.4）
    - capability_id: github.com/foo/bar:search
      interaction_class: information
      category_id: search
      category_version: "2026.1"
  surfaces:                    # 已知 surface → alias 映射
    - surface_id: mcp_tool:bar.search
      alias: io.github.foo/bar
```

- `aliases` 是解析依据；`surfaces` 是已确认映射的缓存（可由 alias 推导）
- 提交方式：作者 fork + PR；`verified=false` 时不得用于公共 market metric 的
  **权威归属**（可作候选，Label 披露 `registry_version` 与 verified 比例）

## 5. 与 project-identity 的关系

`registry/project-identity/`（既有 JSON 格式）是 Project 级身份（Client 侧）；
本文档的 `registry/entities/`（YAML）是 Entity 级身份（被使用侧）。
两者互补：project_id 标识"谁在用"，entity_id 标识"被用什么"。
project-identity 的字段（aliases/tools/declared_by/verified）与新格式对齐后
统一迁移到 `registry/entities/`。

## 6. 计数纪律

- 未归并观察：surface 层计数可用（如 M2/M3 的 tool 级指标按 surface 名计），
  MUST 在 Label 中声明 `entity_resolution: surface-only`
- 归并后：同一 entity 的多个 surface 的计数合并，MUST 声明 `entity_resolution: merged`
- 冲突/无法判定：不计入 entity 级指标，单列 `Identity Conflict Share` 披露

## 7. 验证标准

- [ ] 两个观察（同一 entity、不同 surface）经 registry 归并为同一 entity_id
- [ ] 无 registry 条目时归属为 UNKNOWN，不产生错误计数
- [ ] alias 冲突时标记 ambiguous 且不计入
- [ ] `registry/entities/*.yaml` 通过 schema 校验（`schemas/entity.yaml`）
