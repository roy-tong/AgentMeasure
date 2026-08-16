# AgentMeasure Registry（机器可读）

两个互补的机器可读注册表：

| 注册表 | 回答 | 格式 | 校验 |
| --- | --- | --- | --- |
| `entities/` | 被用什么（Software Entity 身份） | YAML（`schemas/entity.schema.json`） | `python3 registry/validate_entities.py` |
| `project-identity/` | 谁在用（Project 身份，Client 侧） | JSON | 同上（结构性检查） |

## entities/（Entity Registry）

每个 Entity 一个文件：`registry/entities/<owner>-<repo>.yaml`
（格式见 [standard/ENTITY.md](../standard/ENTITY.md) §4）。

- 由工具作者提交（fork + PR）；`verified: false` 时不用于公共 market metric 的
  权威归属
- alias 归并：观察记录 surface 层标识，统计层按 `aliases` 解析到 `entity_id`；
  无匹配 → UNKNOWN，冲突 → ambiguous 且不计入（不变量 21）
- 提交前本地校验：`python3 registry/validate_entities.py`（CI 同样执行）

## project-identity/（既有格式）

Project 级身份（`project.id ↔ aliases ↔ tools`），dogfooding 见
`roy-tong-AgentMeasure.json`。字段与 entities/ 对齐后统一迁移到 entities/。

## 校验器

`validate_entities.py` 零依赖（stdlib only）：
- `mini_yaml.py` —— registry YAML 专用子集解析器（非通用 YAML 实现）
- JSON Schema 子集校验（type / required / properties / additionalProperties /
  items / enum / pattern）

```bash
python3 registry/validate_entities.py   # 全部通过 → exit 0
```
