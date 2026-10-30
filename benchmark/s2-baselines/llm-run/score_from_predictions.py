#!/usr/bin/env python3
"""LLM 对账员 step2 评分驱动（包外两步式的第二步）。

输入：
  --instances  verovobench-instances.jsonl（含 ground_truth，仅评分用）
  --preds      llm-run/predictions/*.jsonl（每行 {"instance_id":..., "output": {...}}）

流程：读预测 → eval_reconciler.parse_prediction() 校验 → score_instance() 评分 →
聚合（与 eval_reconciler.evaluate 同口径：类召回/精确匹配/预测精确率/行引用命中/置信度）。

纪律：不修改 verovobench 评测包；本脚本仅 import 其公开评分函数（parse_prediction /
score_instance / CLASSES），被测 LLM 在包外已运行完毕（step1=分片代理）。
"""
import argparse, glob, json, sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # llm-run/
sys.path.insert(0, str(_HERE.parent.parent / "verovobench"))
from eval_reconciler import parse_prediction, score_instance, CLASSES  # noqa: E402

# 默认路径基于脚本位置（llm-run/），与运行时 CWD 无关
_DEF_INSTANCES = str(_HERE.parent.parent / "verovobench" / "verovobench-instances.jsonl")
_DEF_PREDS = str(_HERE / "predictions" / "*.jsonl")
_DEF_OUT = str(_HERE / "llm-eval-report-v1.3-rerun.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default=_DEF_INSTANCES)
    ap.add_argument("--preds", default=_DEF_PREDS)
    ap.add_argument("--out", default=_DEF_OUT)
    args = ap.parse_args()

    inst = {}
    with open(args.instances, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                inst[r["instance_id"]] = r

    preds = {}
    n_pred_rows = 0
    pred_files = sorted(glob.glob(args.preds))
    for pf in pred_files:
        with open(pf, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_pred_rows += 1
                r = json.loads(line)
                preds[r["instance_id"]] = r["output"]

    missing = [iid for iid in inst if iid not in preds]
    per_class = {c: {"n": 0, "hit": 0} for c in CLASSES}
    n_scored = n_hit = n_exact = n_line = n_location = total_preds = 0
    n_not_applicable = n_na_with_predictions = n_na_prediction_count = 0
    schema_error_count = 0
    confs = []
    for iid, instance in inst.items():
        if iid not in preds:
            continue
        pred, schema_errors = parse_prediction(preds[iid])
        schema_error_count += len(schema_errors)
        s = score_instance(instance, pred)
        if s["status"] != "scored":
            if s["status"] == "not_applicable":
                n_not_applicable += 1
                na_preds = pred["discrepancies"]
                n_na_prediction_count += len(na_preds)
                if na_preds:
                    n_na_with_predictions += 1
            continue
        n_scored += 1
        total_preds += s["n_predictions"]
        per_class[instance["class"]]["n"] += 1
        if s["hit"]:
            n_hit += 1
            per_class[instance["class"]]["hit"] += 1
            confs.append(s["confidence"])
            if s["line_ref_hit"]:
                n_line += 1
            if s.get("location_complete"):
                n_location += 1
        if s["exact"]:
            n_exact += 1

    class_recalls = [d["hit"] / d["n"] for d in per_class.values() if d["n"]]
    report = {
        "reconciler": "llm-two-step (GLM agent run, 2026-10-26)",
        "scoring_protocol": "v1.3 (2026-10-29): event/line_index must agree; exact requires "
                            "location_complete.",
        "n_instances_total": len(inst),
        "n_predictions_loaded": n_pred_rows,
        "n_missing_predictions": len(missing),
        "n_instances_evaluated": n_scored + n_not_applicable,
        "n_scored": n_scored,
        "n_not_applicable": n_not_applicable,
        "not_applicable_false_alarm_rate": (round(n_na_with_predictions / n_not_applicable, 4)
                                            if n_not_applicable else None),
        "not_applicable_instances_with_predictions": n_na_with_predictions,
        "not_applicable_prediction_count": n_na_prediction_count,
        "class_recall": round(n_hit / n_scored, 4) if n_scored else None,
        "macro_class_recall": (round(sum(class_recalls) / len(class_recalls), 4)
                               if class_recalls else None),
        "exact_match_rate": round(n_exact / n_scored, 4) if n_scored else None,
        "prediction_precision": round(n_hit / total_preds, 4) if total_preds else None,
        "prediction_precision_scope": "injected instances only; not_applicable false alarms reported separately",
        "line_ref_hit_rate_given_hit": round(n_line / n_hit, 4) if n_hit else None,
        "location_complete_rate_given_hit": round(n_location / n_hit, 4) if n_hit else None,
        "mean_confidence_on_hits": round(sum(confs) / len(confs), 4) if confs else None,
        "schema_errors": schema_error_count,
        "per_class": per_class,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_class"}, ensure_ascii=False, indent=1))
    print("per_class recall:")
    for c in CLASSES:
        d = per_class[c]
        if d["n"]:
            print(f"  {c}: {d['hit']}/{d['n']} = {d['hit']/d['n']:.3f}")


if __name__ == "__main__":
    main()
