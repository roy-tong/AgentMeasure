#!/usr/bin/env python3
"""S2 四被测系统跑分（论文线：规则引擎/朴素 diff/阈值/LLM 两步式）。

被测系统（行级差异预测 [{event, direction}]，direction∈over/under）：
  rule_engine : 仓库 recount 引擎（healthcheck/verovo_healthcheck/vendors.recount）。
                VerovoBench 实例事件流 → judgement CSV 行 → recount(verdicts)。
                双实现边界：verovobench 评测包不 import 本仓库引擎；本驱动器在包外
                （benchmark/s2-baselines/）以被测系统身份调用它，属黑盒评测。
  naive_diff  : 仅发票内部一致性（无合约）：amount≠qty×unit_price、同 event 重复行、
                行内 human_replies>0 却计费、summary 与行和不符。
  threshold   : 纯统计异常：行 amount z-score≥2 → over；amount < 单价×0.5 → under。
  llm         : 两步式 step1 —— 生成子样本 prompts JSONL（模型调用在包外另跑）。

评分（score_baselines）：
  instance_recall  有差异实例中被检出（预测行∩GT 行 ≠ ∅）的比例
  line_precision  预测行中命中 GT 行的比例（not_applicable 实例的任何预测=误报）
  direction_acc   命中行中方向一致的比例
用法：
  python3 s2_baselines.py --limit 0          # 全量 5600（规则引擎较慢）
  python3 s2_baselines.py --limit 500        # 子样本
  python3 s2_baselines.py --llm-prompts 200  # 只生成 LLM step1 prompts
"""
import argparse, json, math, random, statistics, sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent / "verovobench"
sys.path.insert(0, str(BENCH))
import generator as G  # 事件流重建=取得厂商 conversation log（对账输入）

PROFILE_BY_ID = {p["id"]: p for p in G.SEED_PROFILES}

# ---------------- 实例加载与事件重建 ----------------

def iter_instances(path, limit=0):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                yield json.loads(line)


def rebuild_events(inst):
    rng = random.Random(f"events|{inst['profile']}|{inst['gen_seed']}")
    return G.synth_events(PROFILE_BY_ID[inst["profile"]], rng, inst["n_events"])


def billed_events(inst):
    return {li.get("event") for li in inst["invoice"].get("line_items", [])
            if li.get("event") and _is_charge_line(li)}


def _is_charge_line(li):
    return li.get("amount") is not None and li.get("unit") not in ("info", "credit_note_meta")


# ---------------- 被测系统 a：规则引擎（仓库 recount） ----------------

_HEALTHCHECK = Path(__file__).resolve().parents[2] / "healthcheck"


def load_rule_engine():
    sys.path.insert(0, str(_HEALTHCHECK))
    from verovo_healthcheck import vendors as V
    return V


def rule_engine_predict(V, vendor_id, inst):
    rows = []
    for e in rebuild_events(inst):
        rows.append({
            "conversation_id": e["event_id"],
            "human_agent_participated": e["human_replies"] > 0,
            "issue_addressed": e["ai_answers"] > 0,
            "customer_recontacted_within_window": e["reopened_same_conversation"],
            "vendor_billed": e["event_id"] in billed_events(inst),
        })
    export = {"records": rows, "columns_missing": [], "export_columns": sorted(rows[0]),
              "columns_found": sorted(rows[0])} if rows else {"records": [], "columns_missing": [], "export_columns": [], "columns_found": []}
    result = V.recount(export, vendor_id)
    preds = []
    for v in result["verdicts"]:
        if v["verdict"] == "billed_but_not_billable":
            preds.append({"event": v["conversation_id"], "direction": "over"})
        elif v["verdict"] == "billable_but_not_billed":
            preds.append({"event": v["conversation_id"], "direction": "under"})
    return preds, result


# ---------------- 被测系统 b：朴素 diff（仅发票） ----------------

def naive_diff_predict(inst):
    preds = []
    lines = inst["invoice"].get("line_items", [])
    seen = {}
    unit_price = None
    for li in lines:
        ev, amt = li.get("event"), li.get("amount")
        if amt is None:
            continue
        qty, up = li.get("qty"), li.get("unit_price")
        if up:
            unit_price = up
        # D1 行内算术不一致
        if qty is not None and up is not None and abs(amt - qty * up) > 0.011:
            preds.append({"event": ev, "direction": "over" if amt > qty * up else "under"})
        # D2 同 event 重复计费行
        if ev and li.get("unit") != "info":
            if ev in seen:
                preds.append({"event": ev, "direction": "over"})
            seen[ev] = True
        # D3 行内自证矛盾：人工参与却按 AI 计费
        if (li.get("human_replies") or 0) > 0 and li.get("unit") in ("resolution", "conversation", "ai_interaction"):
            preds.append({"event": ev, "direction": "over"})
    # D4 汇总与行和不符（不定位行，记 instance 级首行）
    total = inst["invoice"].get("summary", {}).get("total")
    if total is not None and lines:
        s = sum(li.get("amount") or 0 for li in lines)
        if abs(total - s) > 0.011:
            first = next((li.get("event") for li in lines if li.get("event")), None)
            if first:
                preds.append({"event": first, "direction": "over" if total > s else "under"})
    # 去重
    out, got = [], set()
    for p in preds:
        k = (p["event"], p["direction"])
        if k not in got:
            got.add(k)
            out.append(p)
    return out


# ---------------- 被测系统 c：阈值 ----------------

def threshold_predict(inst):
    lines = [li for li in inst["invoice"].get("line_items", []) if li.get("amount") is not None]
    amts = [li["amount"] for li in lines]
    preds = []
    if len(amts) < 3:
        return preds
    mean = statistics.fmean(amts)
    sd = statistics.pstdev(amts)
    prices = {li.get("unit_price") for li in lines if li.get("unit_price")}
    base = max(prices) if prices else mean
    for li in lines:
        if not li.get("event") or li.get("unit") in ("info", "credit_note_meta"):
            continue
        z = (li["amount"] - mean) / sd if sd > 1e-9 else 0
        if z >= 2.0:
            preds.append({"event": li.get("event"), "direction": "over"})
        elif base and 0 < li["amount"] < base * 0.5 and (li.get("qty") or 0) >= 1:
            preds.append({"event": li.get("event"), "direction": "under"})
    return [p for p in preds if p["event"]]


# ---------------- 被测系统 d：LLM 两步式 step1 ----------------

def llm_step1_prompts(instances, n, out_path):
    sys.path.insert(0, str(BENCH))
    import eval_reconciler as ER
    sample = instances[:n] if n else instances
    with open(out_path, "w", encoding="utf-8") as f:
        for inst in sample:
            f.write(json.dumps({
                "instance_id": inst["instance_id"],
                "seed_key": inst["seed_key"],
                "profile": inst["profile"],
                "class": inst["class"],
                "prompt": ER.build_prompt(inst),
            }, ensure_ascii=False) + "\n")
    return len(sample)


# ---------------- 评分 ----------------

def score(preds_by_system, instances):
    gt_all = []
    for inst in instances:
        gt = inst["ground_truth"]
        if gt.get("status") != "injected":
            gt_all.append(None)
            continue
        evs = {r.get("event") for r in gt.get("line_refs", []) if r.get("event")}
        gt_all.append((evs, gt.get("direction")))
    n_detectable_total = sum(1 for g in gt_all if g and g[0])
    reports = {}
    for name, preds in preds_by_system.items():
        n_pos = n_hit = n_pred = n_pred_hit = n_dir_hit = n_fp_on_clean = 0
        n_det_pos = n_det_hit = 0
        for (g, preds_i) in zip(gt_all, preds):
            if g is None:
                n_fp_on_clean += len(preds_i)
                n_pred += len(preds_i)
                continue
            evs, direction = g
            n_pos += 1
            if evs:
                n_det_pos += 1
            hit_events = {p["event"] for p in preds_i} & evs
            if hit_events:
                n_hit += 1
                if evs:
                    n_det_hit += 1
            n_pred += len(preds_i)
            for p in preds_i:
                if p["event"] in evs:
                    n_pred_hit += 1
                    d = p["direction"]
                    if (direction == "overcharge" and d == "over") or (direction == "undercharge" and d == "under"):
                        n_dir_hit += 1
        reports[name] = {
            "instance_recall": round(n_hit / n_pos, 4) if n_pos else None,
            "instance_recall_detectable_only": round(n_det_hit / n_det_pos, 4) if n_det_pos else None,
            "n_detectable_instances": n_det_pos,
            "line_precision": round(n_pred_hit / n_pred, 4) if n_pred else None,
            "direction_acc_given_hit": round(n_dir_hit / n_pred_hit, 4) if n_pred_hit else None,
            "n_positive_instances": n_pos,
            "n_detected": n_hit,
            "n_predictions": n_pred,
            "n_false_predictions_on_clean": n_fp_on_clean,
        }
    return reports


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default=str(BENCH / "verovobench-instances.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--llm-prompts", type=int, default=0, help=">0: 只生成 LLM step1 prompts 后退出")
    ap.add_argument("--llm-prompts-out", default="llm-prompts-sample.jsonl")
    ap.add_argument("--vendor", default="intercom", help="规则引擎使用的 CLI vendor 语义")
    ap.add_argument("--out", default="s2-baselines-report.json")
    a = ap.parse_args()

    instances = list(iter_instances(a.instances, a.limit))
    print(f"loaded {len(instances)} instances")

    if a.llm_prompts:
        n = llm_step1_prompts(instances, a.llm_prompts, a.llm_prompts_out)
        print(f"llm step1: {n} prompts -> {a.llm_prompts_out}")
        return

    V = load_rule_engine()
    vendor_ids = [v["id"] for v in V.list_vendors()]
    vendor = a.vendor if a.vendor in vendor_ids else vendor_ids[0]
    print(f"rule engine vendor={vendor} (available: {vendor_ids})")

    preds_by_system = {"rule_engine": [], "naive_diff": [], "threshold": []}
    rule_meta = {"cannot_settle_rows": 0, "total_rows": 0}
    for i, inst in enumerate(instances):
        p_rule, result = rule_engine_predict(V, vendor, inst)
        rule_meta["cannot_settle_rows"] += result["counts"].get("cannot_settle", 0)
        rule_meta["total_rows"] += result["total_conversations"]
        preds_by_system["rule_engine"].append(p_rule)
        preds_by_system["naive_diff"].append(naive_diff_predict(inst))
        preds_by_system["threshold"].append(threshold_predict(inst))
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(instances)}")

    reports = score(preds_by_system, instances)
    reports["_meta"] = {
        "n_instances": len(instances),
        "rule_engine_vendor": vendor,
        "rule_engine_cannot_settle_share": round(rule_meta["cannot_settle_rows"] / rule_meta["total_rows"], 4) if rule_meta["total_rows"] else None,
        "llm": "two-step: prompts via --llm-prompts; model call out of package",
    }
    Path(a.out).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in reports.items() if k != "_meta"}, ensure_ascii=False, indent=2))
    print(f"report -> {a.out}")


if __name__ == "__main__":
    main()
