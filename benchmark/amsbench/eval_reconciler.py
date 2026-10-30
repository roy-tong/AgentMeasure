#!/usr/bin/env python3
"""AMSBench LLM 对账员评测接口（论文线卡 A）。

流程：
  instance（invoice + profile_doc，ground_truth 对被评测方不可见）
    → build_prompt()      构造对账 prompt（规则文档 + 账单 + 输出 schema + 类枚举）
    → reconciler(prompt)  对账员输出原始 JSON
    → parse_prediction()  schema 校验（错误类枚举 + 行引用 + 置信度 0-1）
    → score_instance()    与 ground_truth 评分（类命中 / 行引用命中 / 置信度）

输出 schema（对账员必须返回）：
  {"discrepancies": [
      {"error_class": "<taxonomy v2 16 类枚举之一>",
       "line_ref": {"line_index": int, "event": str|null},
       "confidence": 0.0-1.0,
       "explanation": str}
  ]}

纪律：
  - call_llm() 为 API 调用占位，不实际调用外部模型；接入时替换该函数即可。
  - 双实现隔离：不 import 仓库内 reconcile CLI / 计费引擎代码。
  - 不使用 subprocess；仅标准库；输出 utf-8。
  - 默认 reconciler=null（空预测基线），用于打通评测链路（recall=0 属预期）。

用法：
  python3 eval_reconciler.py --instances amsbench-instances.jsonl --reconciler null
  python3 eval_reconciler.py --instances amsbench-instances.jsonl --limit 100 --out eval-report.json
"""
import argparse, json
from pathlib import Path

TAXONOMY = json.loads((Path(__file__).parent / "taxonomy.json").read_text(encoding="utf-8"))
CLASSES = [c for fam in TAXONOMY["families"].values() for c in fam["classes"]]
CLASS_DESC = {c: fam["classes"][c]["desc"]
              for fam in TAXONOMY["families"].values() for c in fam["classes"]}

OUTPUT_SCHEMA = {
    "discrepancies": [
        {"error_class": "枚举之一（E01..E16，见 prompt 内类清单）",
         "line_ref": {"line_index": "int：账单 line_items 数组下标",
                      "event": "str|null：行内 event 字段"},
         "confidence": "0.0-1.0",
         "explanation": "一句话差异说明"}
    ]
}

PROMPT_TEMPLATE = """你是计费对账员（reconciler）。给定厂商计费规则文档与一张账单，逐行核对并找出所有与规则不符的差异。

【厂商计费规则】
{profile_doc}

【账单（JSON）】
{invoice}

【输出要求】
仅输出一个 JSON 对象（不要输出其他文字），schema 如下：
{schema}

error_class 必须是以下枚举之一：
{classes}

各类含义：
{class_desc}

若账单与规则完全一致，输出 {{"discrepancies": []}}。"""


def build_prompt(instance):
    """构造对账 prompt；注意不得引用 instance['ground_truth']。"""
    invoice = json.dumps(instance["invoice"], ensure_ascii=False, indent=1)
    schema = json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=1)
    class_desc = "\n".join(f"- {c}: {CLASS_DESC[c]}" for c in CLASSES)
    return PROMPT_TEMPLATE.format(profile_doc=instance["profile_doc"],
                                  invoice=invoice, schema=schema,
                                  classes=", ".join(CLASSES), class_desc=class_desc)


def call_llm(prompt, model=None):
    """LLM API 调用占位。

    接入真实对账员时替换此函数（例如用 urllib/httpx POST 厂商 chat/completions
    API，把 prompt 发给模型并返回其 JSON 文本）。本仓库评测纪律：不实际调用
    外部模型、不使用 subprocess，故默认返回 None（按空预测处理）。
    """
    return None


def null_reconciler(prompt):
    """空预测基线：永不出差异。用于打通链路与计算特异性下界。"""
    return {"discrepancies": []}


RECONCILERS = {"null": null_reconciler}


def parse_prediction(raw):
    """把对账员原始输出解析并校验为标准预测结构。返回 (prediction, schema_errors)。"""
    errors = []
    if raw is None:
        return {"discrepancies": []}, ["llm_output_missing"]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as ex:
            return {"discrepancies": []}, [f"invalid_json: {ex}"]
    if not isinstance(raw, dict) or not isinstance(raw.get("discrepancies", []), list):
        return {"discrepancies": []}, ["missing_discrepancies_array"]
    preds = []
    for i, d in enumerate(raw.get("discrepancies", [])):
        if not isinstance(d, dict) or d.get("error_class") not in CLASSES:
            errors.append(f"discrepancy[{i}].error_class_not_in_enum")
            continue
        conf = d.get("confidence", 0.5)
        try:
            conf = float(conf)
            if not 0.0 <= conf <= 1.0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"discrepancy[{i}].confidence_invalid")
            conf = 0.5
        preds.append({"error_class": d["error_class"],
                      "line_ref": d.get("line_ref") if isinstance(d.get("line_ref"), dict) else {},
                      "confidence": conf,
                      "explanation": str(d.get("explanation", ""))})
    return {"discrepancies": preds}, errors


def score_instance(instance, prediction):
    """单实例评分：not_applicable 实例不计分（对账员本应输出空差异）。

    评分协议 v1.3（2026-10-29 注册修订；v1.2 历史结果保留）：
    - v1.1 缺陷 1：行命中只认 event id；v1.2 已修 event 为空时按 line_index 匹配。
    - v1.1 缺陷 2：exact 不查定位；v1.2 已修。
    - v1.3 缺陷修复：事件行同时给出 event 与 line_index 时，line_index 必须与该
      event 的金标行一致；否则定位失败，不能由正确 event 绕过矛盾行号。
    - v1.3 语义：line_ref_hit 表示事件/行引用至少有一致的身份证据；
      location_complete 要求行下标完整一致；exact 只基于 location_complete。
    - 历史 v1.1/v1.2 数字与 v1.3 不得直接比较；旧事件-only 正确定位不再算 exact。
    """
    gt = instance["ground_truth"]
    if gt.get("status") != "injected":
        return {"status": "not_applicable"}
    preds = prediction["discrepancies"]
    hit_idx = next((i for i, p in enumerate(preds) if p["error_class"] == gt["class"]), None)
    line_hit = None
    location_complete = False
    event_match = False
    index_consistent = None
    if hit_idx is not None:
        gt_refs = gt.get("line_refs", [])
        gt_events = {r.get("event") for r in gt_refs if r.get("event")}
        event_indices = {}
        eventless_indices = set()
        for r in gt_refs:
            idx = r.get("line_index")
            ev = r.get("event")
            if ev:
                if isinstance(idx, int):
                    event_indices.setdefault(ev, set()).add(idx)
            elif isinstance(idx, int):
                eventless_indices.add(idx)
        pr = preds[hit_idx].get("line_ref") or {}
        pr_idx = pr.get("line_index")
        pr_event = pr.get("event")
        index_present = isinstance(pr_idx, int)
        event_match = bool(pr_event) and pr_event in gt_events
        if event_match:
            allowed = event_indices.get(pr_event, set())
            if index_present:
                index_consistent = pr_idx in allowed
                location_complete = index_consistent
                line_hit = index_consistent
            else:
                # 事件身份正确，但没有行下标：可算身份命中，不算完整定位。
                line_hit = True
                location_complete = False
                index_consistent = None
        elif index_present and not pr_event:
            line_hit = pr_idx in eventless_indices
            location_complete = line_hit
            index_consistent = line_hit
        else:
            line_hit = False
            location_complete = False
            index_consistent = False
    return {"status": "scored",
            "hit": hit_idx is not None,
            "exact": (hit_idx is not None and len(preds) == 1 and location_complete),
            "line_ref_hit": line_hit,
            "location_complete": location_complete,
            "event_match": event_match,
            "line_index_consistent": index_consistent,
            "confidence": preds[hit_idx]["confidence"] if hit_idx is not None else None,
            "n_predictions": len(preds)}


def evaluate(instances, reconciler_name="null"):
    """批量评测并聚合：类召回 / 精确匹配率 / 预测精确率 / 行引用命中 / 置信度。"""
    fn = RECONCILERS.get(reconciler_name)
    per_class = {c: {"n": 0, "hit": 0} for c in CLASSES}
    n_scored = n_hit = n_exact = n_line = n_complete = total_preds = 0
    schema_error_count = 0
    confs = []
    for inst in instances:
        prompt = build_prompt(inst)
        if reconciler_name == "llm":
            raw = call_llm(prompt)
            if raw is None:
                raw = {"discrepancies": []}
        else:
            raw = fn(prompt)
        pred, schema_errors = parse_prediction(raw)
        schema_error_count += len(schema_errors)
        s = score_instance(inst, pred)
        if s["status"] != "scored":
            continue
        n_scored += 1
        total_preds += s["n_predictions"]
        per_class[inst["class"]]["n"] += 1
        if s["hit"]:
            n_hit += 1
            per_class[inst["class"]]["hit"] += 1
            confs.append(s["confidence"])
            if s["line_ref_hit"]:
                n_line += 1
            if s.get("location_complete"):
                n_complete += 1
        if s["exact"]:
            n_exact += 1
    return {
        "reconciler": reconciler_name,
        "n_instances": len(instances),
        "n_scored": n_scored,
        "n_not_applicable": len(instances) - n_scored,
        "class_recall": round(n_hit / n_scored, 4) if n_scored else None,
        "exact_match_rate": round(n_exact / n_scored, 4) if n_scored else None,
        "prediction_precision": round(n_hit / total_preds, 4) if total_preds else None,
        "line_ref_hit_rate_given_hit": round(n_line / n_hit, 4) if n_hit else None,
        "location_complete_rate_given_hit": round(n_complete / n_hit, 4) if n_hit else None,
        "mean_confidence_on_hits": round(sum(confs) / len(confs), 4) if confs else None,
        "schema_errors": schema_error_count,
        "per_class": per_class,
        "scoring_protocol": "v1.3 (2026-10-29): event/line_index must agree; exact requires "
                            "location_complete. v1.1/v1.2 numbers not comparable.",
        "note": "call_llm 为占位、reconciler=null 为空预测基线：recall=0 属预期，"
                "仅用于打通评测链路与特异性参照。",
    }


def load_instances(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="amsbench-instances.jsonl")
    ap.add_argument("--reconciler", default="null", choices=sorted(RECONCILERS) + ["llm"],
                    help="null=空预测基线；llm=走 call_llm 占位（当前等效 null）")
    ap.add_argument("--limit", type=int, default=0, help="只评前 N 条（0=全量）")
    ap.add_argument("--out", default=None, help="报告写入文件（utf-8）")
    a = ap.parse_args()
    instances = load_instances(a.instances)
    if a.limit > 0:
        instances = instances[:a.limit]
    report = evaluate(instances, a.reconciler)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
