# CI 纪律：测试先行

> 2026-09-19 订立。根因：三轮同型 bug（半截子签名重构、lab 模块搬运遗漏、action.yml
> 拼写错误）的根因都是声称完成前没有跑 `python3 -m unittest discover -s tests`。

## 规则

1. **任何变更推送前 MUST 跑单元测试并全绿**：
   ```bash
   cd healthcheck && python3 -m unittest discover -s tests
   ```
   `selftest` 子命令（校验 adapter + fixture 契约）不是单元测试的替代品——两套都要过。

2. **新功能 = 新测试**。新增一个检查/模块/CLI 子命令，必须在同一推送中包含 ≥1 个测试。
   - 新 check 函数 → `tests/test_checks.py` 加 ≥1 个断言
   - 新 CLI 子命令 → `tests/test_cli.py` 加命令解析和冒烟
   - 新模块 → 建 `tests/test_<module>.py`

3. **当前基线**：118 tests / 0.7s，目标 ≤0.1s/10tests。

4. **CI 红 = 阻断**
   - 推送前发现 CI 红了先修绿再合
   - 因为自己没跑测试 → 违规可追溯

## 例外

- README / 文档 / YAML 格式类变更：不需要新测试
- 紧急修复（CI 已红）：先修绿，再补测试