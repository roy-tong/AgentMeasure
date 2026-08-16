#!/usr/bin/env python3
"""AgentMeasure spec-drift check（Draft 0.4.2，文档一致性 CI）。

防止"两代世界"再次出现：
  1. 文档层禁用遗留词汇（S0-S4 / L0-L3 / E0-E3 / VACD / agent-used / AUAS /
     CORE_POLICY_V1 / QUALIFIED_CONTEXTS / agentmeasure-0.1）
     —— 允许出现在 archive/、CHANGELOG*、fixtures/、conformance/vectors/、
        reference/（数据码与历史测试）
  2. 版本一致性：standard/ 文档的 spec_version 必须为 agentmeasure-0.4，
     不允许残留 agentmeasure-0.1 / auas-0.3

用法: python3 scripts/spec_drift.py
退出码：0 = 无漂移；1 = 发现漂移。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOC_DIRS = ("standard", "whitepaper", "docs", "product", "extensions",
            "proposals", "conformance")
DOC_FILES = ("README.md", "README.zh-CN.md", "ROADMAP.md", "GOVERNANCE.md",
             "CONTRIBUTING.md")
ALLOWED_SUBSTR = ("archive", "fixtures", "conformance/vectors", "reference",
                  "CHANGELOG")

# (pattern, label) —— 文档层禁用
BANNED = [
    (r"\bS[0-4]\b", "S0-S4 signal 词汇"),
    (r"\bL[0-3]\b", "L0-L3 lifecycle 码"),
    (r"\bE[0-3]\b", "E0-E3 evidence 码"),
    (r"\bVACD\b", "VACD 遗留名"),
    (r"agent-used", "agent-used 旧品牌"),
    (r"\bAUAS\b", "AUAS 旧品牌"),
    (r"CORE_POLICY_V1", "CORE_POLICY_V1 遗留"),
    (r"QUALIFIED_CONTEXTS", "QUALIFIED_CONTEXTS 遗留"),
    (r"agentmeasure-0\.1", "0.1 spec_version"),
    (r"auas-0\.3", "auas spec_version"),
    (r"(?<!Observed )\bSelection Rate\b", "裸 Selection Rate（应为 Observed Selection Rate）"),
]

VERSION_RE = re.compile(r'"spec_version"\s*:\s*"([^"]+)"')


def _is_allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(seg in rel for seg in ALLOWED_SUBSTR)


def main() -> int:
    failed = 0
    files = []
    for d in DOC_DIRS:
        files += list((ROOT / d).rglob("*.md"))
    for f in DOC_FILES:
        p = ROOT / f
        if p.exists():
            files.append(p)

    for path in sorted(set(files)):
        if _is_allowed(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, label in BANNED:
            for m in re.finditer(pattern, text):
                line = text[: m.start()].count("\n") + 1
                print(f"  ✗ {path.relative_to(ROOT)}:{line} — {label}: {m.group(0)!r}")
                failed += 1
        # 版本一致性：standard/ 文档中的 spec_version 必须一致
        if "standard" in path.relative_to(ROOT).parts:
            for m in VERSION_RE.finditer(text):
                if m.group(1) not in ("agentmeasure-0.4", "agentmeasure-0.4.1"):
                    print(f"  ✗ {path.relative_to(ROOT)} — spec_version {m.group(1)!r}（应为 0.4）")
                    failed += 1

    print(f"\nspec-drift {'CLEAN' if failed == 0 else f'{failed} DRIFT(S)'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
