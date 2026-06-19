"""空头可行性研究:下沉层(小盘)的「真 alpha」扣**借券费 + 做空可得性**后是否还站得住(待办)。

调研指出真 alpha 在容量受限的冷门层(study_downshift 量化了毛 Sharpe 下沉增益)。但冷门=小盘=
**借券贵 / 常借不到**。本研究对 big(S&P500 拥挤层)与 small(S&P600 下沉层)各跑 statarb,
取其空头簿,用 costs.borrow_drag_annual(ADV 分档代理)估:
  - 年化借券拖累(占 NAV);
  - 不可做空权重占比(借不到券的部分);
  - 扣借券后的净 Sharpe ≈ (净年化收益 − 借券拖累) / 净波动。

诚实:借券率是 ADV 分档**代理**(免费数据无真实 borrow rate);空头簿为**最新快照**(非时序均值);
结论方向稳健即可——若小盘扣借券后净 Sharpe 增益消失,则「下沉救 alpha」在做空成本前证伪。

用法:python backtest/study_short_feasibility.py [--sample 80]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import statarb as sa  # noqa: E402
import costs  # noqa: E402
import data as datamod  # noqa: E402
import study_downshift as ds  # noqa: E402


def recent_adv(ticker: str, lookback: int = 60) -> float:
    """近 lookback 日均美元成交额(close×volume)。无数据返回 0。"""
    d = datamod.load(ticker)
    c, v = d.get("close"), d.get("volume")
    if not c or not v or len(c) < 5:
        return 0.0
    c = np.asarray(c[-lookback:], dtype=float)
    v = np.asarray(v[-lookback:], dtype=float)
    return float(np.nanmean(c * v))


def short_book_drag(rep: dict) -> dict:
    book = rep.get("latest_book") or {}
    shorts = [p for p in book.get("positions", []) if p["side"] == "SHORT"]
    if not shorts:
        return {"ann_borrow_cost": 0.0, "unshortable_frac": 0.0, "mean_rate": 0.0,
                "n_short": 0, "n_unshortable": 0, "short_gross": 0.0}
    w = np.array([abs(p["weight"]) for p in shorts])
    adv = np.array([recent_adv(p["ticker"]) for p in shorts])
    drag = costs.borrow_drag_annual(w, adv)
    drag["short_gross"] = float(w.sum())
    return drag


def summarize(rep: dict, label: str) -> dict:
    drag = short_book_drag(rep)
    net = rep["net"]
    net_ann, net_vol = net["ann_return"], net.get("ann_vol", float("nan"))
    sharpe_after = ((net_ann - drag["ann_borrow_cost"]) / net_vol
                    if net_vol and np.isfinite(net_vol) and net_vol > 0 else float("nan"))
    return {
        "label": label,
        "net_sharpe": net["sharpe"],
        "net_ann": net_ann,
        "net_vol": net_vol,
        "borrow_ann": drag["ann_borrow_cost"],
        "sharpe_after_borrow": sharpe_after,
        "unshortable_frac": drag["unshortable_frac"],
        "n_short": drag["n_short"],
        "n_unshortable": drag["n_unshortable"],
        "short_gross": drag["short_gross"],
        "mean_borrow_rate": drag["mean_rate"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="空头可行性(借券费/做空可得性)研究")
    ap.add_argument("--sample", type=int, default=80, help="S&P600 分层抽样数")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "feed", "longterm", "short_feasibility.json"))
    args = ap.parse_args()

    print("S&P600 成分 + 分层抽样 ...")
    uni600 = ds.fetch_sp600()
    small = ds.stratified_sample(uni600, args.sample)
    big = sa.DEMO_UNIVERSE

    need = sorted(set(small + big + sa.SECTOR_ETFS + ["SPY"]))
    print(f"下载行情 {len(need)} 只 ...")
    datamod.fetch_universe(need, range_="8y", workers=12)

    print("跑 statarb:big 拥挤层 ...")
    rep_big = sa.run(big, sa.StatArbParams(), verbose=False)
    print("跑 statarb:small 下沉层 ...")
    rep_small = sa.run(small, sa.StatArbParams(), verbose=False, sector_map=uni600)

    rows = [summarize(rep_big, "大盘 S&P500 拥挤层"), summarize(rep_small, "小盘 S&P600 下沉层")]
    erosion = rows[1]["net_sharpe"] - rows[1]["sharpe_after_borrow"]
    net_gain_before = rows[1]["net_sharpe"] - rows[0]["net_sharpe"]
    net_gain_after = rows[1]["sharpe_after_borrow"] - rows[0]["sharpe_after_borrow"]
    small_borrow = rows[1]["borrow_ann"]
    # 精确归因:区分「借券侵蚀了正增益」vs「增益本就为负(借券不是元凶)」vs「借券可忽略」
    if net_gain_before > 0 and net_gain_after <= 0:
        verdict = "下沉净增益由正转负**正是借券费造成** → 「下沉救 alpha」被做空成本证伪。"
    elif net_gain_before <= 0:
        verdict = (f"下沉净增益**扣借券前就为负**({net_gain_before:+.2f}),借券非元凶;"
                   f"且 S&P600 借券拖累仅 {small_borrow*100:.1f}%/年(0 不可做空)——"
                   f"S&P600 有流动性入选门槛,仍属 general-collateral。**真正的借券墙在 S&P600 以下的微盘**"
                   f"(调研所指『容量受限冷门层』),需 microcap universe + 真实 borrow rate 才咬合。")
    else:
        verdict = (f"下沉净增益扣借券后仍为正({net_gain_after:+.2f});S&P600 借券拖累 "
                   f"{small_borrow*100:.1f}%/年,可忽略——结论须在更深微盘层 + 真实 borrow rate 复核。")
    out = {
        "schema_version": "1.0", "kind": "short_feasibility_study",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "borrow_model": {"tiers": costs.BORROW_TIERS, "shortable_min_adv": costs.SHORTABLE_MIN_ADV,
                         "note": "ADV 分档代理,非真实 borrow rate"},
        "rows": rows,
        "net_gain_before_borrow": net_gain_before,
        "net_gain_after_borrow": net_gain_after,
        "small_borrow_erosion": erosion,
        "verdict": verdict,
        "caveats": [
            "借券率为 ADV 分档代理(免费数据无真实 rate);空头簿为最新快照非时序均值",
            "不可做空名按最贵档惩罚(保守);实盘可能直接无券",
            "statarb 净 alpha 本身≈0/负;此研究量化的是『下沉增益』被借券进一步侵蚀的程度",
        ],
    }
    op = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("=" * 70)
    print(f"{'层':<22}{'净SR':>8}{'借券/年':>9}{'扣借券SR':>10}{'不可做空':>9}{'空头数':>7}")
    for r in rows:
        print(f"{r['label']:<22}{r['net_sharpe']:>8.2f}{r['borrow_ann']*100:>8.1f}%"
              f"{r['sharpe_after_borrow']:>10.2f}{r['unshortable_frac']*100:>8.0f}%{r['n_short']:>7}")
    print("-" * 70)
    print(f"  下沉净SR增益:扣借券前 {net_gain_before:+.2f} → 扣借券后 {net_gain_after:+.2f}")
    print(f"  诚实裁决:{verdict}")
    print("=" * 70)
    print(f"写入 {op}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
