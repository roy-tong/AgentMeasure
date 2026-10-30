#!/usr/bin/env python3
"""VerovoBench generator v0.2 — 构造式 ground truth 基准生成器（论文线卡 A）。

架构（论文研究框架 §4.2 + §11）：
  SEED_PROFILES（7 厂商计费画像，参数已扰动去污染）
    → synth_events()          确定性合成事件流（rng 由 profile_id+seed 派生）
    → correct_invoice()       逐 profile 语义的确定性正确账单
    → ERROR_INJECTORS[class]  按 taxonomy v2 对账单做自然形态变异
    → build_instance()        instance = {invoice, profile_doc, ground_truth}
  每个实例仅由 (seed_key, gen_seed, n_events) 决定，可独立复现（validate.py 据此校验）。

双实现隔离声明：本生成器与仓库内 reconcile CLI / 计费引擎零共享代码，
不 import 其任何模块；仅用 Python 标准库；不调用 subprocess；输出一律 utf-8。

用法：
  python3 generator.py --smoke                 # 2 profile × 16 类 × 2 实例冒烟
  python3 generator.py --full --seed 42        # 7 profile × 16 类 × 50 = 5600 实例
  python3 generator.py --full --per-class 10 --n-events 120 --seed 7
"""
import argparse, hashlib, json, math, random
from datetime import datetime, timedelta
from pathlib import Path

TAXONOMY = json.loads((Path(__file__).parent / "taxonomy.json").read_text(encoding="utf-8"))
FAMILY_OF, CLASSES = {}, []
for _fam, _body in TAXONOMY["families"].items():
    for _cls in _body["classes"]:
        FAMILY_OF[_cls] = _fam
        CLASSES.append(_cls)

PERIOD = "2031-01"
PERIOD_START = datetime(2031, 1, 1)

# ---- 种子 profile（S1 正标 T0 语义最丰富厂商的形式化）----
# 纪律：既有扰动单价一律不动。v0.2 仅"新增"个别缺失的金额常数（标注 # added），
# 否则金额无法计算；结构性常数（额度/阈值）统一放 RULES，不写入价格。
SEED_PROFILES = [
    {
        "id": "P-finlike", "vendor_anonymized": "ALPHA",
        "unit": "per_resolution", "price": 0.83,
        "one_per_conversation": True, "no_reply_counts": True,
        "reopen_same_conversation_credit": True,
        "split_threshold_days": None, "handoff": "conditional",
        "minimum_commit": {"unit_floor": 41}, "trial_days": 14,
    },
    {
        "id": "P-zendeskalike", "vendor_anonymized": "BETA",
        "unit": "per_resolution", "price_committed": 1.27, "price_payg": 1.73,
        "included_per_agent_month": 7, "no_reply_counts": True,
        "split_hours": {"messaging": 2, "email": 72},
        "handoff": "ai_only_billed", "oracle": "llm_internal",
        "tiers": "volume_tiers;blocks_prepaid",
    },
    {
        "id": "P-conversationlike", "vendor_anonymized": "GAMMA",
        "unit": "per_conversation", "price": 0.41,
        "min_user_messages": 2, "no_reply_counts": False,
        "split_minutes": 15, "handoff": "conditional",
        "cross_month_double_count": True, "auto_recharge": {"at_pct": 95, "pack": 100, "disableable": False},
    },
    {
        "id": "P-gorgiaslike", "vendor_anonymized": "DELTA",
        "unit": "other_dual", "price_ticket": 0.34, "price_ai_interaction": 0.87,
        "no_reply_counts": True, "handoff_window_hours": 72,
        "split_days": {"email": 10, "other": 3}, "spam_filter": True,
    },
    {
        "id": "P-cognigylike", "vendor_anonymized": "EPSILON",
        "unit": "per_conversation", "max_inputs_per_window": 50, "window_hours": 24,
        "voice_minutes_per_conversation": 10, "handoff": "billed_once",
        "transformer_execs_per_extra_conversation": 50,
        "price": 0.29,  # added v0.2（扰动值，补充缺失单价）
    },
    {
        "id": "P-creditlike", "vendor_anonymized": "ZETA",
        "unit": "per_action_credit", "action_costs": {"basic": 1, "advanced": 3},
        "credits_expire": "subscription_period", "no_rollover": True, "not_refundable": True,
        "price_per_credit": 0.11,  # added v0.2（扰动值，补充缺失单价）
    },
    {
        "id": "P-parloalike", "vendor_anonymized": "ETA",
        "unit": "other_dual", "voice": {"per_minute": True, "round_up_seconds": 60,
                                        "price_per_minute": 0.06},  # price added v0.2
        "chat": {"per_turn": True, "welcome_free": True, "price_per_turn": 0.13},  # price added v0.2
        "multi_agent_metered_independently": True, "pass_through_markup_pct": 15,
        "pass_through_base_per_voice_minute": 0.02,  # added v0.2（通行成本基数常数）
    },
]

# 结构常数（非单价）：承诺档容量 / 信用期初余额 / 含额度。可调，不影响价格语义。
RULES = {
    "P-zendeskalike": {"committed_cap": 30},
    "P-conversationlike": {"opening_credits": 200},
    "P-creditlike": {"included_credits_month": 150},
}

# 对账员可读的规则文档（instance.profile_doc；与 correct_invoice 实现一一对应）
PROFILE_DOCS = {
    "P-finlike": (
        "【ALPHA 计费规则】单位=per_resolution，单价 0.83/次。同一会话至多计 1 次；"
        "AI 未回复也计为已解决。同一会话重开（行内 reopened=true）应冲减为 0，不得计费。"
        "试用期（2031-01-14 及之前）会话不计费。转人工（human_replies>0）后须 "
        "customer_confirmed=true 才计为解决。最低承诺 41 次/周期：计费次数不足 41 时以 "
        "minimum_commit 行补足至 41；已达 41 后不得再追加补差行。"
    ),
    "P-zendeskalike": (
        "【BETA 计费规则】单位=per_resolution。每 agent 每月前 7 次免费（included_allowance，"
        "unit_price=0）。其后累计 30 次内按承诺价 1.27（committed_tier），超出按 1.73（payg_tier）。"
        "会话切分：messaging 类渠道（chat/sms/voice）2 小时、email 72 小时，超时再开计为新会话；"
        "行内 segments 为切分后段数，qty 应等于 segments。仅 AI 处理的会话计费："
        "human_replies>0 的会话不得计为 AI resolution（应 qty=0）。"
    ),
    "P-conversationlike": (
        "【GAMMA 计费规则】单位=per_conversation，单价 0.41/次。仅 user_inputs>=2 且 "
        "ai_answers>=1 的会话计费。会话切分 15 分钟（行内 segments=段数，qty 应等于 segments）。"
        "同一客户同一渠道 15 分钟内重复开启合并为一次（merged_into 指向被合并事件，该行应 qty=0）。"
        "转人工（human_replies>0）后须 customer_confirmed=true 才计。自动充值：信用余额期初 200，"
        "用量达 95%（190 次）时自动购 100 次包；信用包购买不构成本账单费用，"
        "auto_recharge_pack 应仅为 amount=0 的信息行，任何收费的充值包行均为错误。"
    ),
    "P-gorgiaslike": (
        "【DELTA 计费规则】双单位：ticket 0.34/张 + ai_interaction 0.87/次。spam 会话过滤不计。"
        "会话切分：email 10 天、其他渠道 3 天（行内 segments=段数，ticket qty 应等于 segments）。"
        "转人工窗口：human_replies>0（72h 窗口内转人工）时会话的 ai_interaction 应全额冲减"
        "（qty=0，handoff_window_credit）；ticket 照计。"
    ),
    "P-cognigylike": (
        "【EPSILON 计费规则】单位=per_conversation，单价 0.29/次。文本会话：user_inputs 每 50 次"
        "计 1 个会话（qty=max(1,ceil(inputs/50))），活动间隔超 24h 每多一段 +1（行内 segments）。"
        "语音会话：每 10 分钟计 1 个会话，分钟数按 60 秒向上取整"
        "（qty 应等于 ceil(ceil(duration_seconds/60)/10)）。handoff 会话只计一次。"
        "平台 Transformer 执行每 50 次折 1 个额外会话（transformer_executions 行内 "
        "transformer_execs 为总执行数，qty 应为 floor(execs/50)）；内部组件执行按次计费均为错误。"
    ),
    "P-creditlike": (
        "【ZETA 计费规则】单位=per_action_credit，1 credit=0.11。action 成本：basic=1、advanced=3"
        "（行内 action_type 应与 qty 一致）。每周期含 150 credits 额度（额度内 unit_price=0），"
        "超出按 0.11 计。额度周期末过期、不结转、不退款：未用完额度仅出现在 credit_expiry"
        "（amount=0）信息行；任何 credit_carryover 抵扣行均为错误。"
    ),
    "P-parloalike": (
        "【ETA 计费规则】语音：按分钟计 0.06/分钟，每会话秒数按 60 秒向上取整"
        "（voice_minute 行 qty 应=ceil(duration_seconds/60)）。聊天（含 email/sms）：按轮计 "
        "0.13/轮，欢迎轮免费（qty=max(0,user_inputs-1)）。多 agent 独立计量（行内 agent 标识，"
        "无跨 agent 合并或共享额度）。渠道通行成本加价：仅对语音通行成本（0.02/分钟）收 15% "
        "加价（pass_through_markup 行的 markup_base/rate 应为该基数与 0.15）。"
    ),
}


# ---------------- 事件流 ----------------
def synth_events(profile, rng, n_events):
    """确定性合成底层事件流（会话/工单/动作），仅用扰动后参数；ts 限制在 2031-01 内。"""
    events = []
    for i in range(n_events):
        base = PERIOD_START + timedelta(minutes=rng.randrange(0, 31 * 24 * 60))
        gaps = []
        if rng.random() < 0.35:
            gaps = [rng.randrange(2, 20000) for _ in range(rng.randrange(1, 3))]
        events.append({
            "event_id": f"e{i:05d}",
            "ts": base.isoformat(),
            "channel": rng.choice(["chat", "email", "voice", "sms"]),
            "customer_ref": f"c{rng.randrange(0, 60):03d}",
            "agent_id": rng.choice(["agent-1", "agent-2", "agent-3"]),
            "user_inputs": rng.randrange(1, 120),
            "ai_answers": rng.randrange(0, 8),
            "human_replies": rng.randrange(0, 3),
            "customer_confirmed": rng.random() < 0.3,
            "reopened_same_conversation": rng.random() < 0.12,
            "spam": rng.random() < 0.07,
            "duration_seconds": rng.randrange(15, 1800),
            "gaps_min": gaps,
            "transformer_execs": rng.randrange(0, 25),
            "action_type": rng.choice(["basic", "advanced"]),
        })
    return events


# ---------------- 正确账单 ----------------
def _segments(e, threshold_min):
    """按切分阈值计算会话段数（gaps_min 中超过阈值的间隙各多一段）。"""
    n = 1
    for g in e.get("gaps_min", []):
        if g > threshold_min:
            n += 1
    return n


def _split_threshold_min(profile, channel):
    pid = profile["id"]
    if pid == "P-zendeskalike":
        h = profile["split_hours"]
        return (h["email"] if channel == "email" else h["messaging"]) * 60
    if pid == "P-conversationlike":
        return profile["split_minutes"]
    if pid == "P-gorgiaslike":
        d = profile["split_days"]
        return (d["email"] if channel == "email" else d["other"]) * 1440
    if pid == "P-cognigylike":
        return profile["window_hours"] * 60
    return None


def _mk(e, unit, qty, price, reason=None, **extra):
    li = {"event": e["event_id"] if e else None,
          "unit": unit, "qty": qty, "unit_price": price,
          "amount": round(qty * price, 2)}
    if e:
        li["channel"] = e["channel"]
    if reason:
        li["reason"] = reason
    li.update(extra)
    return li


def _retotal(inv):
    s = inv.get("summary", {})
    s["line_count"] = len(inv["line_items"])
    s["billable_qty"] = sum(li["qty"] for li in inv["line_items"])
    s["subtotal"] = round(sum(li["amount"] for li in inv["line_items"]), 2)
    s["total"] = s["subtotal"]
    inv["summary"] = s
    return inv


def correct_invoice(profile, events, period=PERIOD):
    """按 profile 规则确定性计算正确账单（覆盖全部 7 个 profile 的核心语义）。"""
    pid = profile["id"]
    items = []
    extras = {}

    if pid == "P-finlike":
        trial_end = PERIOD_START + timedelta(days=profile["trial_days"])
        for e in events:
            if datetime.fromisoformat(e["ts"]) < trial_end:
                continue  # 试用期内不计费
            meta = {"reopened": e["reopened_same_conversation"],
                    "human_replies": e["human_replies"]}
            if e["reopened_same_conversation"] and profile.get("reopen_same_conversation_credit"):
                items.append(_mk(e, "resolution", 0, profile["price"], "reopen_credit", **meta))
                continue
            billed = profile.get("no_reply_counts") or e["customer_confirmed"]
            if e["human_replies"] > 0 and not e["customer_confirmed"]:
                billed = False  # conditional handoff：转人工后须确认
            if billed:
                items.append(_mk(e, "resolution", 1, profile["price"], **meta))
            else:
                items.append(_mk(e, "resolution", 0, profile["price"], "handoff_unconfirmed",
                                 customer_confirmed=e["customer_confirmed"], **meta))
        used = sum(li["qty"] for li in items if li["unit"] == "resolution")
        floor = profile["minimum_commit"]["unit_floor"]
        if used < floor:  # 最低承诺下限
            items.append(_mk(None, "minimum_commit", floor - used, profile["price"],
                             "minimum_commit_topup"))

    elif pid == "P-zendeskalike":
        evs = sorted(events, key=lambda x: x["ts"])
        per_agent, committed_used = {}, 0
        cap = RULES[pid]["committed_cap"]
        for e in evs:
            segs = _segments(e, _split_threshold_min(profile, e["channel"]))
            if e["human_replies"] > 0:  # ai_only_billed：转人工不计 AI resolution
                items.append(_mk(e, "resolution", 0, profile["price_committed"], "handoff_not_ai",
                                 agent=e["agent_id"], human_replies=e["human_replies"], segments=segs))
                continue
            au = per_agent.get(e["agent_id"], 0)
            if au < profile["included_per_agent_month"] and \
                    segs <= profile["included_per_agent_month"] - au:
                items.append(_mk(e, "resolution", segs, 0.0, "included_allowance",
                                 agent=e["agent_id"], segments=segs))
                per_agent[e["agent_id"]] = au + segs
            elif committed_used < cap:
                items.append(_mk(e, "resolution", segs, profile["price_committed"], "committed_tier",
                                 agent=e["agent_id"], segments=segs))
                committed_used += segs
            else:
                items.append(_mk(e, "resolution", segs, profile["price_payg"], "payg_tier",
                                 agent=e["agent_id"], segments=segs))

    elif pid == "P-conversationlike":
        evs = sorted([dict(e) for e in events],
                     key=lambda x: (x["customer_ref"], x["channel"], x["ts"]))
        last, merged_into = {}, {}
        for e in evs:  # 同客户同渠道 15 分钟内重复开启 → 合并（per-user 去重）
            key = (e["customer_ref"], e["channel"])
            p = last.get(key)
            if p is not None:
                gap = (datetime.fromisoformat(e["ts"]) -
                       datetime.fromisoformat(p["ts"])).total_seconds() / 60
                if gap <= profile["split_minutes"]:
                    merged_into[e["event_id"]] = p["event_id"]
            last[key] = e
        price = profile["price"]
        for e in events:
            segs = _segments(e, profile["split_minutes"])
            meta = {"segments": segs, "human_replies": e["human_replies"]}
            if e["user_inputs"] < profile.get("min_user_messages", 1):
                items.append(_mk(e, "conversation", 0, price, "below_min_user_messages",
                                 user_inputs=e["user_inputs"], **meta))
                continue
            if e["ai_answers"] < 1:  # no_reply_counts=False：无 AI 回复不计
                items.append(_mk(e, "conversation", 0, price, "no_ai_reply",
                                 ai_answers=e["ai_answers"], **meta))
                continue
            if e["human_replies"] > 0 and not e["customer_confirmed"]:
                items.append(_mk(e, "conversation", 0, price, "handoff_unconfirmed",
                                 customer_confirmed=False, **meta))
                continue
            if e["event_id"] in merged_into:
                items.append(_mk(e, "conversation", 0, price, "merged_duplicate_user_session",
                                 merged_into=merged_into[e["event_id"]], **meta))
                continue
            items.append(_mk(e, "conversation", segs, price, **meta))
        # 自动充值（信用余额模拟；按规则文档仅出 amount=0 信息行）
        used = sum(li["qty"] for li in items if li["unit"] == "conversation")
        opening = RULES[pid]["opening_credits"]
        pack = profile["auto_recharge"]["pack"]
        trigger = opening * profile["auto_recharge"]["at_pct"] / 100
        bal, packs = opening, 0
        for _ in range(used):
            bal -= 1
            if bal <= opening - trigger:
                bal += pack
                packs += 1
        items.append({"event": None, "unit": "auto_recharge_pack", "qty": packs * pack,
                      "unit_price": 0.0, "amount": 0.0, "reason": "auto_recharge_info",
                      "packs": packs, "trigger_at_used": int(trigger)})

    elif pid == "P-gorgiaslike":
        for e in events:
            if e["spam"] and profile.get("spam_filter"):
                continue
            segs = _segments(e, _split_threshold_min(profile, e["channel"]))
            items.append(_mk(e, "ticket", segs, profile["price_ticket"], segments=segs))
            if e["human_replies"] > 0:  # 72h 转人工窗口：AI 费全额冲减
                items.append(_mk(e, "ai_interaction", 0, profile["price_ai_interaction"],
                                 "handoff_window_credit", human_replies=e["human_replies"],
                                 ai_answers=e["ai_answers"]))
            else:
                items.append(_mk(e, "ai_interaction", e["ai_answers"],
                                 profile["price_ai_interaction"], human_replies=0,
                                 ai_answers=e["ai_answers"]))

    elif pid == "P-cognigylike":
        total_execs, price = 0, profile["price"]
        for e in events:
            total_execs += e["transformer_execs"]
            segs = _segments(e, profile["window_hours"] * 60)
            if e["channel"] == "voice":  # 语音：分钟按 60s 向上取整，每 10 分钟 1 会话
                minutes = math.ceil(e["duration_seconds"] / 60)
                qty = math.ceil(minutes / 10)
                items.append(_mk(e, "conversation", qty, price, duration_seconds=e["duration_seconds"],
                                 voice_minutes=minutes, segments=1, human_replies=e["human_replies"]))
            else:
                qty = max(1, math.ceil(e["user_inputs"] / 50)) + (segs - 1)
                items.append(_mk(e, "conversation", qty, price, user_inputs=e["user_inputs"],
                                 segments=segs, human_replies=e["human_replies"]))
        if total_execs >= profile["transformer_execs_per_extra_conversation"]:
            qty = total_execs // profile["transformer_execs_per_extra_conversation"]
            items.append({"event": None, "unit": "conversation", "qty": qty,
                          "unit_price": price, "amount": round(qty * price, 2),
                          "reason": "transformer_executions", "transformer_execs": total_execs})

    elif pid == "P-creditlike":
        rem = RULES[pid]["included_credits_month"]
        price = profile["price_per_credit"]
        for e in events:
            cost = profile["action_costs"][e["action_type"]]
            if rem >= cost:
                items.append(_mk(e, "action_credit", cost, 0.0, "included_credits",
                                 action_type=e["action_type"]))
                rem -= cost
            elif rem > 0:
                items.append(_mk(e, "action_credit", rem, 0.0, "included_credits_partial",
                                 action_type=e["action_type"]))
                items.append(_mk(e, "action_credit", cost - rem, price,
                                 action_type=e["action_type"]))
                rem = 0
            else:
                items.append(_mk(e, "action_credit", cost, price, action_type=e["action_type"]))
        items.append({"event": None, "unit": "credit_expiry", "qty": rem, "unit_price": 0.0,
                      "amount": 0.0, "reason": "expired_no_rollover"})  # 不结转不退款

    elif pid == "P-parloalike":
        pt_base, per_agent = 0.0, {}
        for e in events:  # 多 agent 分别计量
            agent = e["agent_id"]
            if e["channel"] == "voice":  # 语音取整到 60 秒
                minutes = math.ceil(e["duration_seconds"] / profile["voice"]["round_up_seconds"])
                items.append(_mk(e, "voice_minute", minutes, profile["voice"]["price_per_minute"],
                                 duration_seconds=e["duration_seconds"], agent=agent))
                pt_base += minutes * profile["pass_through_base_per_voice_minute"]
            else:  # 按轮计，欢迎轮免费
                qty = max(0, e["user_inputs"] - 1)
                items.append(_mk(e, "chat_turn", qty, profile["chat"]["price_per_turn"],
                                 user_inputs=e["user_inputs"], agent=agent))
            per_agent[agent] = per_agent.get(agent, 0.0) + items[-1]["amount"]
        rate = profile["pass_through_markup_pct"] / 100  # mark channel 15%
        amt = round(pt_base * rate, 2)
        items.append({"event": None, "unit": "pass_through_markup", "qty": 1,
                      "unit_price": amt, "amount": amt,
                      "markup_base": round(pt_base, 2), "markup_rate": rate})
        extras["per_agent_subtotal"] = {a: round(v, 2) for a, v in sorted(per_agent.items())}

    inv = {"period": period, "profile": pid, "currency": "USD",
           "price_table_version": period,
           "line_items": items, "summary": dict(extras)}
    return _retotal(inv)


# ---------------- 错误注入器 ----------------
def _set_qty(li, qty):
    li["qty"] = qty
    li["amount"] = round(qty * li.get("unit_price", 0), 2)


def _set_price(li, price):
    li["unit_price"] = price
    li["amount"] = round(li["qty"] * price, 2)


def _ref(li, inv):
    idx = None
    for i, x in enumerate(inv["line_items"]):
        if x is li:
            idx = i
            break
    return {"line_index": idx, "event": li["event"], "unit": li["unit"]}


def _gt(cls, before_total, inv, refs, expected, actual, note):
    _retotal(inv)  # 变异后重算合计，delta/direction 才能反映金额影响
    delta = round(inv["summary"]["total"] - before_total, 2)
    direction = "overcharge" if delta > 0 else ("undercharge" if delta < 0 else "semantic_mislabel")
    return {"class": cls, "family": FAMILY_OF[cls], "status": "injected",
            "line_refs": refs, "expected": expected, "actual": actual,
            "direction": direction, "delta_amount": delta, "note": note}


def _main_price(profile):
    pid = profile["id"]
    if pid == "P-finlike":
        return profile["price"]
    if pid == "P-zendeskalike":
        return profile["price_committed"]
    if pid == "P-conversationlike":
        return profile["price"]
    if pid == "P-gorgiaslike":
        return profile["price_ai_interaction"]
    if pid == "P-cognigylike":
        return profile["price"]
    if pid == "P-creditlike":
        return profile["price_per_credit"]
    return profile["chat"]["price_per_turn"]


def _billed(inv):
    return [li for li in inv["line_items"] if li["qty"] > 0 and li["event"]]


_SIBLING = {"resolution": "conversation", "conversation": "resolution", "ticket": "resolution",
            "action_credit": "conversation", "voice_minute": "chat_turn",
            "chat_turn": "voice_minute", "ai_interaction": "resolution"}


def _inj_e01(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = [li for li in _billed(inv) if li["unit"] in _SIBLING]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    frm, to = li["unit"], _SIBLING[li["unit"]]
    li["unit"] = to
    return inv, _gt("E01_unit_misclassification", before, inv, [_ref(li, inv)],
                    {"unit": frm}, {"unit": to},
                    f"计费单位误标：{frm} 被计为 {to}（profile 单位见规则文档）")


def _inj_e02(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = _billed(inv)
    if not cands:
        return inv, None
    li = rng.choice(cands)
    expected = li["qty"]
    _set_qty(li, expected + 1)
    li["attempts"] = expected + 1
    return inv, _gt("E02_retry_attribution", before, inv, [_ref(li, inv)],
                    {"qty": expected}, {"qty": expected + 1},
                    "同一操作的重试/多次尝试被单独计数（1 operation / N attempts）")


def _inj_e03(inv, events, profile, rng):
    before = inv["summary"]["total"]
    ev_by_id = {e["event_id"]: e for e in events}
    cands = [li for li in inv["line_items"] if li["qty"] > 0 and li["event"] in ev_by_id]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    e = ev_by_id[li["event"]]
    expected = li["qty"]
    thr = _split_threshold_min(profile, e["channel"])
    if thr:
        wrong = max(1, thr // 10)
        new_qty = _segments(e, wrong)
        if new_qty == expected:
            wrong = thr * 100
            new_qty = _segments(e, wrong)
        if new_qty == expected:
            new_qty = expected + 1
        note = (f"切分阈值误用：按 {wrong} 分钟切分（profile 规则阈值 {thr} 分钟），"
                f"qty 与行内 segments 主张不一致")
    else:
        wrong = rng.choice([1, 5, 30])
        extra = len([g for g in e.get("gaps_min", []) if g > wrong])
        new_qty = expected + max(1, extra)
        li["segments"] = new_qty
        note = f"profile 无会话切分规则，但行内出现 segments={new_qty} 切分主张（单会话被切分多计）"
    _set_qty(li, new_qty)
    return inv, _gt("E03_split_threshold_misapplication", before, inv, [_ref(li, inv)],
                    {"qty": expected}, {"qty": new_qty}, note)


def _inj_e04(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = _billed(inv)
    if not cands:
        return inv, None
    li = rng.choice(cands)
    dup = json.loads(json.dumps(li))
    dup["billed_period"] = "2030-12"
    inv["line_items"].append(dup)
    refs = [_ref(li, inv), _ref(dup, inv)]
    return inv, _gt("E04_cross_period_double_count", before, inv, refs,
                    {"lines_for_event": 1}, {"lines_for_event": 2, "billed_period": "2030-12"},
                    "同一会话跨计费周期双计（重复行标注上一账期 2030-12）")


def _inj_e05(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-cognigylike":
        tl = [li for li in inv["line_items"] if li.get("reason") == "transformer_executions"]
        if not tl:
            return inv, None
        li = tl[0]
        expected, total_execs = li["qty"], li["transformer_execs"]
        _set_qty(li, total_execs)
        refs, exp, act = [_ref(li, inv)], {"qty": expected}, {"qty": total_execs}
        note = "平台 Transformer 内部执行按次计入用量（应为每 50 次折 1 个会话）"
    else:
        cands = _billed(inv)
        if not cands:
            return inv, None
        anchor = rng.choice(cands)
        qty = rng.randrange(20, 80)
        line = {"event": anchor["event"], "channel": anchor.get("channel"),
                "unit": "internal_component_exec", "qty": qty,
                "unit_price": _main_price(profile),
                "amount": round(qty * _main_price(profile), 2),
                "reason": "component_execution", "component": "flow_transformer"}
        inv["line_items"].append(line)
        refs, exp, act = [_ref(line, inv)], {"extra_line": False}, {"extra_line": True, "qty": qty}
        note = "平台内部组件执行被计入用户用量（profile 规则中无可计费的内部组件单位）"
    return inv, _gt("E05_component_execution_billing", before, inv, refs, exp, act, note)


_FLIP = {"chat": "email", "email": "chat", "voice": "sms", "sms": "voice"}


def _inj_e06(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-conversationlike":
        cands = [li for li in inv["line_items"]
                 if li.get("reason") == "merged_duplicate_user_session"]
        if cands:
            li = rng.choice(cands)
            _set_qty(li, 1)
            li.pop("reason", None)
            return inv, _gt("E06_duplicate_conversation_count", before, inv, [_ref(li, inv)],
                            {"qty": 0}, {"qty": 1},
                            "同一客户同渠道 15 分钟内重复开启的会话被分别计数（merged_into 仍在）")
    cands = [li for li in _billed(inv) if li.get("channel") in _FLIP]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    dup = json.loads(json.dumps(li))
    dup["channel"] = _FLIP[li["channel"]]
    inv["line_items"].append(dup)
    refs = [_ref(li, inv), _ref(dup, inv)]
    return inv, _gt("E06_duplicate_conversation_count", before, inv, refs,
                    {"lines_for_event": 1}, {"lines_for_event": 2, "channel": dup["channel"]},
                    "同一事件以另一渠道重复出现（多渠道重复计数）")


def _inj_e07(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = [li for li in _billed(inv) if li["unit_price"] > 0]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    old = li["unit_price"]
    new = round(old * rng.choice([0.85, 1.15]), 2)
    _set_price(li, new)
    li["price_version"] = "2028-06"
    return inv, _gt("E07_stale_price_table", before, inv, [_ref(li, inv)],
                    {"unit_price": old}, {"unit_price": new, "price_version": "2028-06"},
                    "适用过期价表（2028-06）单价，现行价表 2031-01")


def _inj_e08(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = [li for li in _billed(inv) if li["unit_price"] > 0]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    old = li["unit_price"]
    new = round(old * rng.choice([0.9, 1.1]), 2)
    _set_price(li, new)
    li["original_unit_price"] = old
    li["reprice_event"] = "retroactive"
    return inv, _gt("E08_retroactive_repricing", before, inv, [_ref(li, inv)],
                    {"unit_price": old}, {"unit_price": new, "original_unit_price": old},
                    "对已发生用量回溯调价（无价表版本变更，行内 retroactive 重定价）")


def _inj_e09(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-zendeskalike":
        payg = [li for li in inv["line_items"] if li.get("reason") == "payg_tier"]
        com = [li for li in inv["line_items"] if li.get("reason") == "committed_tier"]
        if payg:
            li = rng.choice(payg)
            old, new = li["unit_price"], profile["price_committed"]
            note = "PAYG 段误用承诺价（跨档单价适用错位）"
        elif com:
            li = rng.choice(com)
            old, new = li["unit_price"], profile["price_payg"]
            note = "承诺段误用 PAYG 价（跨档单价适用错位）"
        else:
            return inv, None
        _set_price(li, new)
        exp, act = {"unit_price": old}, {"unit_price": new}
    else:
        cands = [li for li in _billed(inv) if li["unit_price"] > 0]
        if not cands:
            return inv, None
        li = rng.choice(cands)
        old = li["unit_price"]
        new = round(old * 0.9, 2)
        _set_price(li, new)
        li["tier"] = "volume_tier_2"
        exp, act = {"unit_price": old}, {"unit_price": new, "tier": "volume_tier_2"}
        note = "适用不存在的批量折扣档（profile 无分层定价）"
    return inv, _gt("E09_tier_boundary_error", before, inv, [_ref(li, inv)], exp, act, note)


def _inj_e10(inv, events, profile, rng):
    pid = profile["id"]
    if pid not in ("P-parloalike", "P-cognigylike"):
        return inv, None  # 仅含语音时长取整语义的 profile 适用
    before = inv["summary"]["total"]
    ev_by_id = {e["event_id"]: e for e in events}
    cands = []
    for li in inv["line_items"]:
        if li["qty"] <= 0 or li["event"] not in ev_by_id:
            continue
        e = ev_by_id[li["event"]]
        if pid == "P-parloalike" and li["unit"] == "voice_minute":
            floored = e["duration_seconds"] // 60
        elif pid == "P-cognigylike" and e["channel"] == "voice":
            floored = (e["duration_seconds"] // 60) // 10
        else:
            continue
        if floored < li["qty"]:
            cands.append((li, floored))
    if not cands:
        return inv, None
    li, floored = rng.choice(cands)
    expected = li["qty"]
    _set_qty(li, floored)
    li["rounding_mode"] = "truncate"
    return inv, _gt("E10_rounding_error", before, inv, [_ref(li, inv)],
                    {"qty": expected, "rounding": "ceil"},
                    {"qty": floored, "rounding": "truncate"},
                    "语音取整错误：应按 60 秒向上取整，实际截断")


def _inj_e11(inv, events, profile, rng):
    before = inv["summary"]["total"]
    ml = [li for li in inv["line_items"] if li["unit"] == "pass_through_markup"]
    if ml and profile["id"] == "P-parloalike":
        li = ml[0]
        if rng.choice(["rate", "base"]) == "rate":
            li["markup_rate"] = 0.25
            li["unit_price"] = li["amount"] = round(li["markup_base"] * 0.25, 2)
            exp, act = {"markup_rate": 0.15}, {"markup_rate": 0.25}
            note = "通行成本加价费率错误（15% → 25%）"
        else:
            base = round(sum(x["amount"] for x in inv["line_items"]
                             if x["unit"] == "voice_minute"), 2)
            li["markup_base"] = base
            li["unit_price"] = li["amount"] = round(base * 0.15, 2)
            exp, act = {"markup_base": "pass_through_cost_only"}, {"markup_base": "voice_revenue"}
            note = "加价基数错误：对语音收入而非通行成本计 15%"
        refs = [_ref(li, inv)]
    else:
        subtotal = inv["summary"]["subtotal"]
        line = {"event": None, "unit": "pass_through_markup", "qty": 1,
                "unit_price": round(subtotal * 0.15, 2),
                "amount": round(subtotal * 0.15, 2),
                "markup_base": subtotal, "markup_rate": 0.15}
        inv["line_items"].append(line)
        refs = [_ref(line, inv)]
        exp, act = {"extra_line": False}, {"extra_line": True}
        note = "出现通行成本加价行（profile 无 pass-through 加价规则）"
    return inv, _gt("E11_pass_through_markup", before, inv, refs, exp, act, note)


_E12_REASONS = ("reopen_credit", "included_allowance", "included_credits",
                "included_credits_partial")


def _inj_e12(inv, events, profile, rng):
    before = inv["summary"]["total"]
    cands = [li for li in inv["line_items"] if li.get("reason") in _E12_REASONS]
    if not cands:
        return inv, None  # 无信用/额度机制的 profile 不适用
    li = rng.choice(cands)
    if li.get("reason") == "reopen_credit":
        _set_qty(li, 1)
        li.pop("reason", None)
        exp, act = {"qty": 0}, {"qty": 1}
        note = "同会话重开应自动冲减，实际仍计 1 次（行内 reopened=true）"
    else:
        new = _main_price(profile)
        _set_price(li, new)
        li.pop("reason", None)
        exp, act = {"unit_price": 0.0}, {"unit_price": new}
        note = "已触发的额度/信用未应用：免费额度内用量被按价计费"
    return inv, _gt("E12_credit_non_application", before, inv, [_ref(li, inv)],
                    exp, act, note)


_E13_REASONS = ("handoff_not_ai", "handoff_window_credit", "handoff_unconfirmed")


def _inj_e13(inv, events, profile, rng):
    before = inv["summary"]["total"]
    pid = profile["id"]
    ev_by_id = {e["event_id"]: e for e in events}
    if pid == "P-cognigylike":  # billed_once 被破坏：AI 与人工分别计费
        cands = [li for li in _billed(inv)
                 if li["event"] in ev_by_id and ev_by_id[li["event"]]["human_replies"] > 0]
        if not cands:
            return inv, None
        li = rng.choice(cands)
        dup = json.loads(json.dumps(li))
        dup["unit"] = "human_resolution"
        inv["line_items"].append(dup)
        refs = [_ref(li, inv), _ref(dup, inv)]
        return inv, _gt("E13_handoff_window_reclassification", before, inv, refs,
                        {"lines": 1}, {"lines": 2, "extra_unit": "human_resolution"},
                        "handoff 会话应只计一次，AI 与人工被分别计费")
    if pid in ("P-parloalike", "P-creditlike"):  # 无 handoff 费用项的 profile 被加收
        cands = [li for li in _billed(inv)
                 if li["event"] in ev_by_id and ev_by_id[li["event"]]["human_replies"] > 0]
        if not cands:
            return inv, None
        anchor = rng.choice(cands)
        e = ev_by_id[anchor["event"]]
        price = _main_price(profile)
        line = {"event": anchor["event"], "channel": e["channel"], "unit": "handoff_fee",
                "qty": 1, "unit_price": price, "amount": round(price, 2)}
        inv["line_items"].append(line)
        refs = [_ref(line, inv)]
        return inv, _gt("E13_handoff_window_reclassification", before, inv, refs,
                        {"extra_line": False}, {"extra_line": True, "unit": "handoff_fee"},
                        "转人工被加收 handoff_fee（profile 无此费用项）")
    cands = [li for li in inv["line_items"] if li.get("reason") in _E13_REASONS]
    if not cands:
        return inv, None
    li = rng.choice(cands)
    e = ev_by_id.get(li["event"], {})
    restore = e.get("ai_answers", 1) if li.get("reason") == "handoff_window_credit" else 1
    _set_qty(li, restore)
    li.pop("reason", None)
    return inv, _gt("E13_handoff_window_reclassification", before, inv, [_ref(li, inv)],
                    {"qty": 0}, {"qty": restore},
                    "转人工时间窗重分类未执行：handoff 会话仍按 AI 用量计费")


def _inj_e14(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-creditlike":
        el = [li for li in inv["line_items"] if li.get("reason") == "expired_no_rollover"]
        if not el:
            return inv, None
        li = el[0]
        qty = li["qty"] if li["qty"] > 0 else rng.randrange(20, 60)
        price = profile["price_per_credit"]
        li.update({"unit": "credit_carryover_credit", "reason": "carried_to_next_period",
                   "qty": qty, "unit_price": price, "amount": -round(qty * price, 2)})
        refs = [_ref(li, inv)]
        exp = {"unused_credits": "expired", "offset": 0}
        act = {"unused_credits": "carried_over", "offset": -round(qty * price, 2)}
        note = "不结转的额度被结转抵扣下期费用（no_rollover 违反）"
    else:
        cands = [li for li in _billed(inv) if li["unit_price"] > 0]
        if not cands:
            return inv, None
        anchor = rng.choice(cands)
        qty, price = rng.randrange(20, 60), anchor["unit_price"]
        line = {"event": None, "unit": "credit_carryover_credit", "qty": qty,
                "unit_price": price, "amount": -round(qty * price, 2),
                "reason": "carried_from_prev_period"}
        inv["line_items"].append(line)
        refs = [_ref(line, inv)]
        exp, act = {"extra_line": False}, {"extra_line": True, "qty": qty}
        note = "出现上期结转抵扣行（profile 无结转规则）"
    return inv, _gt("E14_rollover_expiry_error", before, inv, refs, exp, act, note)


def _inj_e15(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-finlike":
        floor = profile["minimum_commit"]["unit_floor"]
        used = sum(li["qty"] for li in inv["line_items"] if li["unit"] == "resolution")
        topups = [li for li in inv["line_items"] if li.get("reason") == "minimum_commit_topup"]
        if used < floor and topups:  # 低于下限却按实际计：少收
            li = topups[0]
            _set_qty(li, 0)
            refs = [_ref(li, inv)]
            exp, act = {"total_qty": floor}, {"total_qty": used}
            note = "最低承诺未执行：用量低于下限仍按实际计（topup 行被清零）"
        else:  # 高于下限仍追加补差：多收
            qty = rng.randrange(5, 15)
            line = {"event": None, "unit": "minimum_commit", "qty": qty,
                    "unit_price": profile["price"],
                    "amount": round(qty * profile["price"], 2),
                    "reason": "minimum_commit_topup"}
            inv["line_items"].append(line)
            refs = [_ref(line, inv)]
            exp, act = {"extra_line": False}, {"extra_line": True, "qty": qty}
            note = "已达下限后仍追加最低承诺补差行（过度执行）"
        return inv, _gt("E15_minimum_commit_error", before, inv, refs, exp, act, note)
    cands = _billed(inv)
    if not cands:
        return inv, None
    qty = rng.randrange(10, 40)
    price = _main_price(profile)
    line = {"event": None, "unit": "minimum_commit", "qty": qty, "unit_price": price,
            "amount": round(qty * price, 2), "reason": "minimum_commit_topup"}
    inv["line_items"].append(line)
    refs = [_ref(line, inv)]
    return inv, _gt("E15_minimum_commit_error", before, inv, refs,
                    {"extra_line": False}, {"extra_line": True, "qty": qty},
                    "出现最低承诺补差行（profile 无最低承诺条款）")


def _inj_e16(inv, events, profile, rng):
    before = inv["summary"]["total"]
    if profile["id"] == "P-conversationlike":
        price, pack = profile["price"], profile["auto_recharge"]["pack"]
        note = "自动充值误触发收费：信用包购买按规则不构成本账单费用行"
    else:
        price, pack = _main_price(profile), 100
        note = "出现自动充值包收费行（profile 无自动充值机制）"
    line = {"event": None, "unit": "auto_recharge_pack", "qty": pack, "unit_price": price,
            "amount": round(pack * price, 2), "reason": "auto_recharge"}
    inv["line_items"].append(line)
    refs = [_ref(line, inv)]
    return inv, _gt("E16_auto_recharge_error", before, inv, refs,
                    {"extra_line": False}, {"extra_line": True, "qty": pack}, note)


ERROR_INJECTORS = {
    "E01_unit_misclassification": _inj_e01,
    "E02_retry_attribution": _inj_e02,
    "E03_split_threshold_misapplication": _inj_e03,
    "E04_cross_period_double_count": _inj_e04,
    "E05_component_execution_billing": _inj_e05,
    "E06_duplicate_conversation_count": _inj_e06,
    "E07_stale_price_table": _inj_e07,
    "E08_retroactive_repricing": _inj_e08,
    "E09_tier_boundary_error": _inj_e09,
    "E10_rounding_error": _inj_e10,
    "E11_pass_through_markup": _inj_e11,
    "E12_credit_non_application": _inj_e12,
    "E13_handoff_window_reclassification": _inj_e13,
    "E14_rollover_expiry_error": _inj_e14,
    "E15_minimum_commit_error": _inj_e15,
    "E16_auto_recharge_error": _inj_e16,
}
assert set(ERROR_INJECTORS) == set(CLASSES), "注入器与 taxonomy v2 类集不一致"


# ---------------- 实例组装 ----------------
def build_instance(profile, events, cls, k, seed):
    """单实例构造：仅由 (profile, cls, k, seed) 决定，可独立复现。"""
    seed_key = f"{profile['id']}|{cls}|{k}"
    rng = random.Random(f"inj|{seed_key}|{seed}")
    base = correct_invoice(profile, events)
    mutated = json.loads(json.dumps(base))
    inj = ERROR_INJECTORS.get(cls)
    truth = None
    if inj:
        mutated, truth = inj(mutated, events, profile, rng)
    if truth is None:  # 该类在该 profile 无对应语义 → 不变异，标记 not_applicable
        mutated = json.loads(json.dumps(base))
        truth = {"class": cls, "family": FAMILY_OF[cls], "status": "not_applicable"}
    iid = hashlib.sha1(f"{seed_key}|{seed}".encode()).hexdigest()[:12]
    return {"instance_id": iid, "gen_seed": seed, "n_events": len(events),
            "profile": profile["id"], "vendor": profile["vendor_anonymized"],
            "class": cls, "family": FAMILY_OF[cls], "seed_key": seed_key,
            "period": PERIOD,
            "profile_doc": PROFILE_DOCS[profile["id"]],
            "invoice": mutated,
            "ground_truth": truth}


def generate(profiles, per_class, n_events, seed):
    out = []
    for p in profiles:
        ev_rng = random.Random(f"events|{p['id']}|{seed}")
        events = synth_events(p, ev_rng, n_events)
        for cls in CLASSES:
            for k in range(per_class):
                out.append(build_instance(p, events, cls, k, seed))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-class", type=int, default=None, help="每 profile 每类实例数（full 默认 50）")
    ap.add_argument("--n-events", type=int, default=None, help="每 profile 事件数（full 默认 100）")
    ap.add_argument("--out", default="verovobench-instances.jsonl")
    a = ap.parse_args()
    if a.smoke:
        data = generate(SEED_PROFILES[:2], 2, 60, a.seed)
        print(json.dumps({"n": len(data), "classes": len(CLASSES),
                          "sample": data[0]}, ensure_ascii=False, indent=1)[:1600])
    elif a.full:
        pc = a.per_class or 50
        ne = a.n_events or 100
        data = generate(SEED_PROFILES, pc, ne, a.seed)
        Path(a.out).write_text(
            "\n".join(json.dumps(d, ensure_ascii=False, separators=(",", ":")) for d in data) + "\n",
            encoding="utf-8")
        print(f"written {len(data)} instances -> {a.out} "
              f"(seed={a.seed}, per_class={pc}, n_events={ne})")
    else:
        print(f"taxonomy v2 classes={len(CLASSES)}, seed profiles={len(SEED_PROFILES)}; "
              f"use --smoke / --full --seed 42")
