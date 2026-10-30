#!/usr/bin/env python3
"""VerovoBench 生成数据校验器。

检查项：
  V1 结构：instance_id 唯一，且与 sha1(seed_key|gen_seed) 一致；family 与 taxonomy v2 一致
  V2 数值：全量 JSON 无 NaN / Infinity（json parse_constant 拒绝）
  V3 分布：16 类分布完全均匀；status 构成统计（injected / not_applicable）
  V4 复现：每实例可由 (seed_key, gen_seed, n_events) 独立重建，
          ground_truth 与 invoice 逐字段一致（不依赖全量重放顺序）

纪律：仅标准库；不 import 仓库内 reconcile/引擎代码（仅 import 同目录 generator）；
不使用 subprocess；输出 utf-8。

用法：
  python3 validate.py --instances verovobench-instances.jsonl
  python3 validate.py --instances verovobench-instances.jsonl --sample 200
"""
import argparse, hashlib, json, random, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import generator as G


def _reject_const(x):
    raise ValueError(f"non-finite JSON constant: {x}")


def load_instances(path):
    rows, errors = [], []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line, parse_constant=_reject_const))
            except ValueError as ex:
                errors.append(f"line {lineno}: {ex}")
    return rows, errors


def rebuild(inst, profiles):
    """从 seed_key + gen_seed + n_events 独立重建单实例。"""
    p = profiles[inst["profile"]]
    rng = random.Random(f"events|{inst['profile']}|{inst['gen_seed']}")
    events = G.synth_events(p, rng, inst["n_events"])
    k = int(inst["seed_key"].rsplit("|", 1)[-1])
    return G.build_instance(p, events, inst["class"], k, inst["gen_seed"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="verovobench-instances.jsonl")
    ap.add_argument("--sample", type=int, default=0, help="只复现校验前 N 条（0=全量）")
    a = ap.parse_args()

    rows, parse_errors = load_instances(a.instances)
    problems = []
    if parse_errors:
        problems.extend(f"V2 {e}" for e in parse_errors[:10])

    profiles = {p["id"]: p for p in G.SEED_PROFILES}

    # V1 结构
    dup = [i for i, c in Counter(r.get("instance_id") for r in rows).items() if c > 1]
    if dup:
        problems.append(f"V1 duplicate instance_id: {dup[:5]}")
    for r in rows:
        expect = hashlib.sha1(f"{r['seed_key']}|{r['gen_seed']}".encode()).hexdigest()[:12]
        if expect != r.get("instance_id"):
            problems.append(f"V1 instance_id 与 seed_key|gen_seed 不一致: {r.get('seed_key')}")
            break
    fam_bad = [r["seed_key"] for r in rows
               if G.FAMILY_OF.get(r.get("class")) != r.get("family")]
    if fam_bad:
        problems.append(f"V1 family 与 taxonomy 不一致: {fam_bad[:5]}")

    # V3 类分布
    counts = Counter(r["class"] for r in rows)
    missing = [c for c in G.CLASSES if c not in counts]
    if missing:
        problems.append(f"V3 缺类: {missing}")
    if counts and len(set(counts.values())) != 1:
        problems.append(f"V3 类分布不均匀: {dict(counts)}")
    statuses = Counter(r.get("ground_truth", {}).get("status") for r in rows)

    # V4 seed_key 复现
    sample = rows if a.sample <= 0 else rows[:a.sample]
    mismatches = []
    for r in sample:
        try:
            rebuilt = rebuild(r, profiles)
        except Exception as ex:  # noqa: BLE001 — 校验器需汇总一切重建失败
            mismatches.append(f"{r['seed_key']}: rebuild error {ex}")
            continue
        if rebuilt["ground_truth"] != r.get("ground_truth") or rebuilt["invoice"] != r.get("invoice"):
            mismatches.append(r["seed_key"])
    if mismatches:
        problems.append(f"V4 不可复现 {len(mismatches)} 条, 例: {mismatches[:5]}")

    report = {
        "file": a.instances,
        "n_instances": len(rows),
        "n_classes": len(counts),
        "per_class_count": dict(sorted(counts.items())),
        "uniform_class_distribution": bool(counts) and len(set(counts.values())) == 1,
        "status_counts": dict(statuses),
        "per_profile": dict(sorted(Counter(r.get("profile") for r in rows).items())),
        "repro_checked": len(sample),
        "repro_mismatches": len(mismatches),
        "nan_inf_check": "pass" if not parse_errors else "fail",
        "problems": problems[:20],
        "ok": not problems,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
