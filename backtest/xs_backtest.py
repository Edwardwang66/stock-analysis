"""横截面多因子回测 —— Rank-IC / 分层单调性 / Purged walk-forward。

方法论严格对齐 research/quant-factor-deep-research.md:
  - 评估指标用 Rank-IC(而非"命中率"):每个 rebalance 日,横截面上"因子值排序"与
    "未来 H 日收益排序"的 Spearman 相关。报告 均值 Rank-IC、ICIR、t 统计、分层 decile spread。
  - 多周期:H = 5(周)/21(月)/63(季)。
  - 因子合成两种:① 等权 z-score;② 滚动 IC 加权(权重只用"当前日之前"的 IC,无未来函数)。
  - Purged + Embargo:滚动 IC 估计时,跳过标签窗口会探入当前的近 H 个 rebalance 日(embargo)。
  - 无未来函数:rebalance 日 d 的因子只用 ≤d 数据;未来收益用 d..d+H 复权价。
  - **PIT 成分过滤(默认开)**:每个 rebalance 日只保留当日真正在 S&P500 的票(membership_asof),
    消「前视性成员偏差」(把后来才纳入的赢家提前算进早年)。无 S&P500 变更史的 NDX-only 名不过滤。
    `--no-pit` 可关闭对照(实测 |IC| 偏大,印证偏差方向)。

诚实声明:PIT 过滤只消「前视性成员」偏差;universe = 当前可得票,仍缺**已退市**名 → 残留幸存者偏差
(需含退市行情才能全消);未计交易成本/换手。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np

import data as datamod
import factors_xs as fx
import pit_membership as pm

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORS = ["mom_12_1", "reversal", "hi52", "lowvol"]


def _daystr(d: int) -> str:
    return dt.datetime.utcfromtimestamp(d).strftime("%Y-%m-%d")


def load_panel():
    """加载所有标的为 {ticker: (ts_array, adj_array, ts->idx map)}。"""
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    panel = {}
    for tk in uni["universe"]:
        d = datamod.load(tk)
        if not d or len(d.get("adjclose", [])) <= 320:
            continue
        ts = np.asarray(d["ts"], dtype=np.int64)
        adj = np.asarray(d["adjclose"], dtype=float)
        panel[tk] = (ts, adj, {int(t): i for i, t in enumerate(ts)})
    return panel


def rebalance_dates(panel, step=21):
    """用 SPY 交易日作主时钟,每 step 日一个 rebalance 日。"""
    spy = datamod.load("SPY")
    ts = np.asarray(spy["ts"], dtype=np.int64)
    # 留出 252 预热 + 末尾后面单独按 horizon 过滤
    idx = list(range(252, len(ts), step))
    return [int(ts[i]) for i in idx]


def cross_section(panel, d: int, horizon: int, pit_allowed=None):
    """在 rebalance 日 d 收集横截面:每因子值数组 + 未来 H 日收益数组(对齐)。
    pit_allowed(tk, date_str)->bool:PIT 成分过滤器(消前视性成员偏差),None=不过滤。"""
    cols = {f: [] for f in FACTORS}
    fwd = []
    day = _daystr(d) if pit_allowed is not None else None
    for tk, (ts, adj, m) in panel.items():
        if pit_allowed is not None and not pit_allowed(tk, day):
            continue
        i = m.get(d)
        if i is None or i + horizon >= len(adj):
            continue
        fv = fx.factor_values(adj, i)
        if fv is None or not all(np.isfinite(fv[f]) for f in FACTORS):
            continue
        if adj[i] <= 0:
            continue
        for f in FACTORS:
            cols[f].append(fv[f])
        fwd.append(adj[i + horizon] / adj[i] - 1.0)
    if len(fwd) < 20:
        return None
    out = {f: np.asarray(cols[f]) for f in FACTORS}
    out["_fwd"] = np.asarray(fwd)
    return out


def summarize_ic(ics: list[float]) -> tuple[float, float, float, int]:
    a = np.asarray([x for x in ics if np.isfinite(x)])
    if len(a) < 2:
        return float("nan"), float("nan"), float("nan"), len(a)
    mean = a.mean()
    icir = mean / a.std(ddof=1) if a.std(ddof=1) > 0 else float("nan")
    t = icir * np.sqrt(len(a)) if np.isfinite(icir) else float("nan")
    return float(mean), float(icir), float(t), len(a)


def composite_equal(cs) -> np.ndarray:
    """等权:各因子横截面 z-score 后按方向求和。"""
    s = np.zeros_like(cs["_fwd"])
    for f in FACTORS:
        s = s + fx.FACTOR_SIGN[f] * fx.zscore(cs[f])
    return s


def composite_icw(cs, weights: dict) -> np.ndarray:
    """滚动 IC 加权:权重来自过去(无未来函数)。"""
    s = np.zeros_like(cs["_fwd"])
    for f in FACTORS:
        w = weights.get(f, 0.0)
        s = s + w * fx.zscore(cs[f])
    return s


def decile_spread(score: np.ndarray, fwd: np.ndarray, n=10):
    """按 score 分 n 层,返回各层平均未来收益(用于看单调性)与 top-bottom 价差。"""
    order = np.argsort(score)
    buckets = np.array_split(order, n)
    means = [float(fwd[b].mean()) for b in buckets]
    return means, means[-1] - means[0]


def run(step=21, horizons=(5, 21, 63), embargo_periods=3, pit_filter=True):
    print("加载面板 ...")
    panel = load_panel()
    dates = rebalance_dates(panel, step)
    pit_allowed = None
    if pit_filter:
        db = pm.load_db()
        if db is not None:
            pit_allowed = pm.make_pit_filter(db)
            print("PIT 成分过滤:开(S&P500 时点成分;无变更史的 NDX-only 名不过滤)")
        else:
            print("PIT 成分过滤:请求开但缺 pit_sp500.json,降级为关")
    else:
        print("PIT 成分过滤:关(⚠ 含前视性成员偏差,IC 偏高)")
    print(f"标的 {len(panel)} 只,rebalance 日 {len(dates)} 个(每 {step} 交易日)\n")

    for H in horizons:
        # 预扫所有 rebalance 日的横截面
        css = []
        for d in dates:
            cs = cross_section(panel, d, H, pit_allowed)
            if cs is not None:
                css.append((d, cs))
        # 单因子 Rank-IC
        per_factor = {f: [] for f in FACTORS}
        eq_ic = []
        for d, cs in css:
            for f in FACTORS:
                ic = fx.spearman(fx.FACTOR_SIGN[f] * cs[f], cs["_fwd"])
                per_factor[f].append(ic)
            eq_ic.append(fx.spearman(composite_equal(cs), cs["_fwd"]))

        print("=" * 74)
        print(f"持有期 H = {H} 交易日   (横截面 {len(css)} 期)")
        print(f"{'因子':<12}{'均值 Rank-IC':>14}{'ICIR':>10}{'t 统计':>10}{'期数':>8}")
        print("-" * 74)
        for f in FACTORS:
            m, icir, t, n = summarize_ic(per_factor[f])
            print(f"{f:<12}{m:>14.4f}{icir:>10.3f}{t:>10.2f}{n:>8}")
        m, icir, t, n = summarize_ic(eq_ic)
        print(f"{'合成(等权)':<10}{m:>14.4f}{icir:>10.3f}{t:>10.2f}{n:>8}")

        # 等权合成的分层单调性(H=21 这种代表期重点看)
        sp = []
        bucket_acc = np.zeros(10)
        cnt = 0
        for d, cs in css:
            means, spread = decile_spread(composite_equal(cs), cs["_fwd"])
            bucket_acc += np.asarray(means)
            sp.append(spread)
            cnt += 1
        bucket_acc /= cnt
        sp = np.asarray(sp)
        print(f"\n  等权合成 分层平均未来收益(D1 最低 -> D10 最高,%):")
        print("   " + "  ".join(f"{x*100:+.2f}" for x in bucket_acc))
        tstat = sp.mean() / sp.std(ddof=1) * np.sqrt(len(sp))
        print(f"  Top-Bottom(D10-D1)均值 = {sp.mean()*100:+.2f}% / 期, "
              f"t = {tstat:.2f}, 胜率 = {(sp>0).mean()*100:.0f}%")

        # 滚动 IC 加权(无未来函数:权重 = 截至上一期之前、再 embargo 后的累计平均单因子IC)
        icw_ic = []
        hist = {f: [] for f in FACTORS}
        for k, (d, cs) in enumerate(css):
            usable = k - embargo_periods  # embargo:不用最近 embargo 期(其标签窗口与当前重叠)
            weights = {}
            for f in FACTORS:
                past = [hist[f][j] for j in range(max(0, usable)) if np.isfinite(hist[f][j])]
                weights[f] = float(np.mean(past)) if len(past) >= 6 else fx.FACTOR_SIGN[f] * 0.01
            icw_ic.append(fx.spearman(composite_icw(cs, weights), cs["_fwd"]))
            for f in FACTORS:
                hist[f].append(fx.spearman(fx.FACTOR_SIGN[f] * cs[f], cs["_fwd"]))
        m, icir, t, n = summarize_ic(icw_ic)
        print(f"\n  合成(滚动IC加权, 无未来函数, embargo={embargo_periods}期): "
              f"均值 Rank-IC={m:.4f}, ICIR={icir:.3f}, t={t:.2f}")
        print("=" * 74 + "\n")


if __name__ == "__main__":
    import sys
    run(pit_filter=("--no-pit" not in sys.argv))
