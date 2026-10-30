#!/usr/bin/env python3
"""评分协议 v1.3 回归测试 — 2026-10-29。

背景：
  v1.1 两处缺陷：机制行只认 event id；exact 不查定位。
  v1.2 修复 event-less 行的 line_index 匹配，但事件行“event 正确 + 矛盾行号”
       仍会绕过定位检查（event=e00083, line_index=999999 → exact=True）。
  v1.3：event 与 line_index 必须一致；exact 要求 location_complete。
纯标准库，无依赖。

运行：python3 test_score_fix.py   （退出码 0=全过）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_reconciler import score_instance  # noqa: E402


def _inst(cls, refs):
    return {"class": cls, "ground_truth": {"status": "injected", "class": cls,
                                           "line_refs": refs}}


def _pred(cls, line_index=None, event=None):
    return {"discrepancies": [
        {"error_class": cls, "line_ref": {"line_index": line_index, "event": event},
         "confidence": 0.9, "explanation": "t"}]}


E11 = "E11_pass_through_markup"

CASES = [
    # (说明, 实例, 预测, 期望 line_ref_hit, 期望 exact)
    ("机制行·正确行下标应命中（v1.1 下必 False=缺陷）",
     _inst(E11, [{"line_index": 3, "event": None}]),
     _pred(E11, line_index=3), True, True),
    ("机制行·错误行下标不算 exact（v1.1 下 exact=True=缺陷）",
     _inst(E11, [{"line_index": 3, "event": None}]),
     _pred(E11, line_index=5), False, False),
    ("机制行·event 字段缺失但行下标正确仍应命中",
     _inst(E11, [{"line_index": 3, "event": None}]),
     {"discrepancies": [{"error_class": E11, "line_ref": {"line_index": 3},
                         "confidence": 0.9, "explanation": "t"}]}, True, True),
    ("事件行·event 与行号均正确→完整定位",
     _inst("E01_unit_mismatch", [{"line_index": 2, "event": "ev-7"}]),
     _pred("E01_unit_mismatch", line_index=2, event="ev-7"), True, True),
    ("事件行·event 正确但行号矛盾→定位必须失败（v1.2 漏洞）",
     _inst("E01_unit_mismatch", [{"line_index": 2, "event": "ev-7"}]),
     _pred("E01_unit_mismatch", line_index=999999, event="ev-7"), False, False),
    ("事件行·event 正确但无行号→身份命中但不 complete，不算 exact",
     _inst("E01_unit_mismatch", [{"line_index": 2, "event": "ev-7"}]),
     _pred("E01_unit_mismatch", event="ev-7"), True, False),
    ("事件行·错误 event 不命中",
     _inst("E01_unit_mismatch", [{"line_index": 2, "event": "ev-7"}]),
     _pred("E01_unit_mismatch", line_index=2, event="ev-9"), False, False),
    ("事件行·仅行下标对、event 缺失→不命中（保守：事件行仍以 event 为准）",
     _inst("E01_unit_mismatch", [{"line_index": 2, "event": "ev-7"}]),
     _pred("E01_unit_mismatch", line_index=2), False, False),
    ("多条预测不算 exact",
     _inst(E11, [{"line_index": 3, "event": None}]),
     {"discrepancies": [
         {"error_class": E11, "line_ref": {"line_index": 3}, "confidence": 0.9,
          "explanation": "t"},
         {"error_class": "E13_handoff_window_reclassification",
          "line_ref": {"line_index": 1}, "confidence": 0.5, "explanation": "t"}]},
     True, False),
    ("not_applicable 不计分",
     {"class": E11, "ground_truth": {"status": "not_applicable", "class": E11}},
     _pred(E11, line_index=3), None, None),
]


def main():
    failures = []
    for i, (name, inst, pred, want_line, want_exact) in enumerate(CASES, 1):
        s = score_instance(inst, pred)
        if s["status"] != "scored":
            if want_line is None:
                print(f"  ok  [{i}] {name}")
                continue
            failures.append(f"[{i}] {name}: 预期 scored，得到 {s}")
            continue
        ok = (s["hit"] is True and s["line_ref_hit"] is want_line
              and s["exact"] is want_exact)
        if ok:
            print(f"  ok  [{i}] {name} (line={s['line_ref_hit']}, exact={s['exact']})")
        else:
            failures.append(f"[{i}] {name}: line={s['line_ref_hit']} (want {want_line}), "
                            f"exact={s['exact']} (want {want_exact})")
    if failures:
        print("\nFAIL:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\n全部通过：评分协议 v1.3 行为与复核诊断一致。")


if __name__ == "__main__":
    main()
