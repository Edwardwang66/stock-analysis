#!/usr/bin/env python3
"""事件概率信号实证检验:Polymarket BTC 价格目标市场的隐含概率是「机械复制现货」还是「含独立信息」?

动机(纪律):新因子上线前必须证明它有独立信息,不能只看它"动得像那么回事"。
BTC 价格目标市场(如「BTC 是否高于 $X」)的隐含概率本质≈现货的数字期权 → 先验上应**机械地**随现货走,
无独立预测力。本脚本量化:
  - 机械性:corr(Δ隐含概率, 当期 BTC 收益)——高=机械(只是重定价现货)。
  - 信号性:corr(Δ隐含概率_t, 次期 BTC 收益)——显著>0 才说明信念领先价格(罕见)。

诚实预期:大概率机械、无领先信号 → 结论「BTC 价格目标市场=情绪温度计,非预测器;
宏观市场(Fed/衰退)才是值得看的」。这本身是有用的诚实发现。

数据:Polymarket prices-history(keyless)+ BTC-USD 日线(data.py)。需时间对齐(本环境已对齐 2026)。
用法:python backtest/study_event_signal.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import data as datamod  # noqa: E402
import polymarket_events as pe  # noqa: E402


def btc_close_by_date() -> dict:
    datamod.fetch_one("BTC-USD", range_="2y", force=False)
    d = datamod.load("BTC-USD")
    out = {}
    for t, c in zip(d.get("ts", []), d.get("close", [])):
        out[datetime.utcfromtimestamp(int(t)).strftime("%Y-%m-%d")] = float(c)
    return out


def is_btc_price_market(q: str) -> bool:
    ql = q.lower()
    return ("bitcoin" in ql or "btc" in ql) and any(s in ql for s in ["$", "k ", "k?", "000"])


def align(history: list[dict], btc: dict):
    """把 prob 历史(日)与 BTC 收盘按日期对齐,返回 (prob[], btc_close[]) 同序。"""
    rows = {}
    for h in history:
        if not h.get("t") or h.get("p") is None:
            continue
        day = datetime.utcfromtimestamp(int(h["t"])).strftime("%Y-%m-%d")
        if day in btc:
            rows[day] = (float(h["p"]), btc[day])
    days = sorted(rows)
    if len(days) < 12:
        return None
    p = np.array([rows[d][0] for d in days])
    b = np.array([rows[d][1] for d in days])
    return p, b


def corr(a, b):
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def main() -> int:
    print("拉取 BTC 价格目标市场 + 历史 ...")
    btc = btc_close_by_date()
    if len(btc) < 30:
        print("BTC 价格数据不足,无法对齐")
        return 1
    raw = pe.fetch_markets(2000)
    cands = []
    for m in raw:
        q = m.get("question", "")
        if not is_btc_price_market(q):
            continue
        pm = pe.parse_market(m)
        if pm and pm.get("token_id") and 0.05 <= pm["prob"] <= 0.95:  # 仅近价市场有动
            cands.append((q, pm["token_id"]))
    print(f"近价 BTC 市场 {len(cands)} 个(prob∈[0.05,0.95])")

    mech, lead = [], []
    rows = []
    for q, tid in cands[:20]:
        hist = pe.fetch_history(tid)
        al = align(hist, btc)
        if al is None:
            continue
        p, b = al
        dp = np.diff(p)                      # Δ隐含概率
        rb = b[1:] / b[:-1] - 1.0            # 当期 BTC 收益
        c_mech = corr(dp, rb)                # 机械性(同期)
        # 信号性:Δprob_t 对 次期 BTC 收益
        if len(dp) >= 4:
            c_lead = corr(dp[:-1], rb[1:])
        else:
            c_lead = float("nan")
        if np.isfinite(c_mech):
            mech.append(c_mech)
            rows.append({"q": q[:50], "n": len(p), "mech_corr": round(c_mech, 3),
                         "lead_corr": round(c_lead, 3) if np.isfinite(c_lead) else None})
        if np.isfinite(c_lead):
            lead.append(c_lead)

    if not mech:
        print("有效市场不足,无法裁决")
        return 1
    mech_mean = float(np.mean(mech))
    lead_mean = float(np.mean(lead)) if lead else float("nan")
    # 信号性 t 检验(跨市场)
    lead_t = (lead_mean / (np.std(lead, ddof=1) / np.sqrt(len(lead)))
              if len(lead) > 1 and np.std(lead, ddof=1) > 0 else float("nan"))
    lead_sig = np.isfinite(lead_t) and abs(lead_t) >= 2
    if lead_sig:
        verdict = (f"⚠ 领先信号 t={lead_t:.2f} 显著(罕见)→ 需独立复现 + 净·扣成本 + OOS 才可信,"
                   "谨防小样本假阳性。")
    elif abs(mech_mean) > 0.3:
        verdict = ("机械性高且无领先信号 → BTC 价格目标市场≈现货数字期权,**无独立预测力**;"
                   "作情绪温度计可,作预测器否。")
    else:
        verdict = (f"机械性弱(corr={mech_mean:.2f})且无领先信号(t={lead_t:.2f})→ 这些市场**黏滞/低流动**,"
                   "日频既不紧跟现货也不领先现货=**噪声**,不作日频信号。用 LEVEL 作情绪温度计即可;"
                   "宏观市场(Fed/衰退)才是值得看的前瞻因子。")
    out = {
        "schema_version": "1.0", "kind": "event_signal_study",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_markets": len(mech),
        "mechanical_corr_mean": round(mech_mean, 4),
        "lead_corr_mean": round(lead_mean, 4) if np.isfinite(lead_mean) else None,
        "lead_t": round(lead_t, 3) if np.isfinite(lead_t) else None,
        "per_market": rows,
        "verdict": verdict,
        "caveats": ["仅 BTC 价格目标市场;宏观市场(Fed/衰退)无干净标的,未在此测",
                    "样本小、prediction-market 历史短;corr 估计噪声大",
                    "隐含概率=市场价格,本就含现货信息;此测只问『有无超出现货的独立信息』"],
    }
    op = os.path.join(os.path.dirname(HERE), "feed", "events", "signal_study.json")
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("=" * 60)
    print(f"  机械性 corr(Δprob, BTC收益) 均值 = {mech_mean:+.3f}  (n={len(mech)} 市场)")
    print(f"  领先信号 corr(Δprob_t, BTC收益_t+1) 均值 = {lead_mean:+.3f}  t={lead_t:+.2f}")
    print(f"  诚实裁决:{verdict}")
    print("=" * 60)
    print(f"写入 {op}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
