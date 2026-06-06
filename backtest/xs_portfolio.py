"""把 Rank-IC 落到真实 P&L:月度(非重叠)分层长短组合。

每 21 交易日 rebalance:按因子分(方向调整后)分 10 层,
做多 top decile、做空 bottom decile(美元中性),持有 21 日。
报告 年化收益/波动/Sharpe/胜率/换手,以及 long-only top decile vs SPY。

非重叠(step==horizon==21)=> 收益序列互相独立,Sharpe 可直接年化(×√12)。
"""
from __future__ import annotations

import numpy as np

import data as datamod
import factors_xs as fx
import xs_backtest as xb

STEP = 21


def factor_score(cs, name):
    if name == "composite":
        s = np.zeros_like(cs["_fwd"])
        for f in xb.FACTORS:
            s = s + fx.FACTOR_SIGN[f] * fx.zscore(cs[f])
        return s
    return fx.FACTOR_SIGN[name] * cs[name]


def long_short_series(css, name, n=10):
    ls, lo, prev_top = [], [], None
    turnover = []
    for d, cs in css:
        score = factor_score(cs, name)
        order = np.argsort(score)
        buckets = np.array_split(order, n)
        bot, top = buckets[0], buckets[-1]
        ls.append(float(cs["_fwd"][top].mean() - cs["_fwd"][bot].mean()))
        lo.append(float(cs["_fwd"][top].mean()))
        # 换手:相邻期 top decile 成分变化比例(用排名位置近似)
        cur = set(top.tolist())
        if prev_top is not None:
            inter = len(cur & prev_top)
            turnover.append(1 - inter / max(len(cur), 1))
        prev_top = cur
    return np.asarray(ls), np.asarray(lo), np.asarray(turnover)


def stats(r):
    mean, vol = r.mean(), r.std(ddof=1)
    sharpe = mean / vol * np.sqrt(12) if vol > 0 else float("nan")
    ann = mean * 12
    return ann, vol * np.sqrt(12), sharpe, (r > 0).mean()


def main():
    panel = xb.load_panel()
    dates = xb.rebalance_dates(panel, STEP)
    css = []
    for d in dates:
        cs = xb.cross_section(panel, d, STEP)
        if cs is not None:
            css.append((d, cs))
    print(f"月度非重叠组合:{len(css)} 期 (~{len(css)/12:.1f} 年)\n")

    # SPY 月度基准
    spy = datamod.load("SPY")
    sts = np.asarray(spy["ts"], dtype=np.int64)
    sadj = np.asarray(spy["adjclose"], dtype=float)
    smap = {int(t): i for i, t in enumerate(sts)}
    spy_r = []
    for d, _ in css:
        i = smap.get(d)
        if i is not None and i + STEP < len(sadj):
            spy_r.append(sadj[i + STEP] / sadj[i] - 1.0)
    spy_r = np.asarray(spy_r)
    sa, sv, ss, sw = stats(spy_r)
    print(f"基准 SPY(月度买入持有):年化 {sa*100:+.1f}%  波动 {sv*100:.1f}%  "
          f"Sharpe {ss:.2f}  正收益月占比 {sw*100:.0f}%\n")

    print(f"{'策略':<14}{'年化(L/S)':>11}{'波动':>8}{'Sharpe':>8}{'胜率':>7}"
          f"{'月换手':>8}{'TopDecile年化':>13}")
    print("-" * 72)
    for name in ["mom_12_1", "reversal", "hi52", "lowvol", "composite"]:
        ls, lo, to = long_short_series(css, name)
        a, v, s, w = stats(ls)
        la, _, _, _ = stats(lo)
        print(f"{name:<14}{a*100:>10.1f}%{v*100:>7.1f}%{s:>8.2f}{w*100:>6.0f}%"
              f"{to.mean()*100:>7.0f}%{la*100:>12.1f}%")
    print("-" * 72)
    print("注:L/S=做多top decile-做空bottom decile(美元中性);未计交易成本。")
    print("    月换手 ~高 => 扣成本后实际 Sharpe 会明显下降(见研报 §1.4/§5.4)。")


if __name__ == "__main__":
    main()
