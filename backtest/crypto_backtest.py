"""加密多因子回测 + 拟合(Hyperliquid 永续)。

流程对齐研报 §3/§5:
  1. 横截面 Rank-IC / ICIR / t(多周期 1/7/30 日)。
  2. 三种合成对比:
       (a) 等权 z-score;
       (b) 手配权重(human prior,见 HAND_WEIGHTS);
       (c) 拟合权重(Ridge 回归)——Purged 时间序列 walk-forward + embargo,只报样本外。
  3. Top/Bottom 三分组长短组合 P&L(币数少,用 tertile)。

无未来函数:rebalance 日因子只用 ≤d 数据;拟合权重只用"测试期之前"的样本训练,
并对标签前瞻窗口做 embargo 隔离。
"""
from __future__ import annotations

import json
import os

import numpy as np

import crypto_factors as cf
import cryptodata as cd
import factors_xs as fx   # 复用 spearman/zscore/rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
F = cf.FACTORS

# 手配权重(human prior):动量+反转为主,funding/basis 拥挤反转次之,波动小权重
HAND_WEIGHTS = {"mom_14": 1.0, "reversal_3": 1.0, "vol_20": 0.3,
                "fund_carry": 0.8, "basis": 0.5}


def build_panel():
    uni = json.load(open(os.path.join(HERE, "crypto_universe.json")))
    panel = {}
    for coin in uni:
        c = cd.load_candles(coin)
        if not c or len(c["close"]) < 120:
            continue
        ts = np.asarray(c["ts"], dtype=np.int64)
        adj = np.asarray(c["close"], dtype=float)
        fund = cd.load_funding(coin)
        fs = np.array([fund.get(int(t), (np.nan, np.nan, np.nan))[0] for t in ts])
        pm = np.array([fund.get(int(t), (np.nan, np.nan, np.nan))[2] for t in ts])
        panel[coin] = (ts, adj, fs, pm, {int(t): i for i, t in enumerate(ts)})
    return panel


def master_dates(panel, step):
    # 用 BTC 日历作主时钟
    ts, *_ = panel["BTC"]
    idx = list(range(40, len(ts), step))
    return [int(ts[i]) for i in idx]


def cross_section(panel, d, horizon):
    cols = {f: [] for f in F}
    fwd, coins = [], []
    for coin, (ts, adj, fs, pm, m) in panel.items():
        i = m.get(d)
        if i is None or i + horizon >= len(adj):
            continue
        fv = cf.compute(adj, i, fs, pm)
        if fv is None or not all(np.isfinite(fv[f]) for f in F):
            continue
        for f in F:
            cols[f].append(fv[f])
        fwd.append(adj[i + horizon] / adj[i] - 1.0)
        coins.append(coin)
    if len(fwd) < 8:
        return None
    out = {f: np.asarray(cols[f]) for f in F}
    out["_fwd"] = np.asarray(fwd)
    return out


def zmat(cs):
    """各因子横截面 z-score,堆成 (n_coins, n_factors) 矩阵(已按 SIGN 调向)。"""
    return np.column_stack([cf.SIGN[f] * fx.zscore(cs[f]) for f in F])


def summarize(ics):
    a = np.asarray([x for x in ics if np.isfinite(x)])
    if len(a) < 2:
        return float("nan"), float("nan"), float("nan"), len(a)
    icir = a.mean() / a.std(ddof=1) if a.std(ddof=1) > 0 else float("nan")
    return float(a.mean()), float(icir), float(icir * np.sqrt(len(a))), len(a)


def tertile_ls(score, fwd):
    order = np.argsort(score)
    k = max(1, len(order) // 3)
    return float(fwd[order[-k:]].mean() - fwd[order[:k]].mean())


def run(step=3, horizons=(1, 7, 30), embargo=5, ridge_lambda=5.0):
    panel = build_panel()
    print(f"加密 universe:{len(panel)} 币,日线对齐\n")
    dates = master_dates(panel, step)

    for H in horizons:
        css = [(d, cs) for d in dates if (cs := cross_section(panel, d, H)) is not None]
        if len(css) < 20:
            print(f"H={H}: 期数不足({len(css)}),跳过\n")
            continue

        # 单因子 Rank-IC
        per = {f: [] for f in F}
        eq_ic, hand_ic = [], []
        for d, cs in css:
            for f in F:
                per[f].append(fx.spearman(cf.SIGN[f] * cs[f], cs["_fwd"]))
            Z = zmat(cs)
            eq_ic.append(fx.spearman(Z.sum(1), cs["_fwd"]))
            hw = np.array([HAND_WEIGHTS[f] for f in F])
            hand_ic.append(fx.spearman(Z @ hw, cs["_fwd"]))

        print("=" * 70)
        print(f"持有期 H = {H} 日   (横截面 {len(css)} 期, ~{len(css)*step/30:.0f} 月)")
        print(f"{'因子':<12}{'Rank-IC':>10}{'ICIR':>9}{'t':>8}{'期数':>7}")
        print("-" * 70)
        for f in F:
            m, ic, t, n = summarize(per[f])
            print(f"{f:<12}{m:>10.4f}{ic:>9.3f}{t:>8.2f}{n:>7}")
        for nm, ics in [("合成(等权)", eq_ic), ("合成(手配)", hand_ic)]:
            m, ic, t, n = summarize(ics)
            print(f"{nm:<10}{m:>10.4f}{ic:>9.3f}{t:>8.2f}{n:>7}")

        # ---- 拟合权重:Purged walk-forward Ridge,只报样本外 ----
        oos_ic = []
        for k in range(len(css)):
            train_idx = list(range(0, k - embargo))   # embargo:跳过最近 embargo 期
            if len(train_idx) < 8:
                continue
            Xtr = np.vstack([zmat(css[j][1]) for j in train_idx])
            ytr = np.concatenate([fx.rankdata(css[j][1]["_fwd"]) -
                                  fx.rankdata(css[j][1]["_fwd"]).mean() for j in train_idx])
            # Ridge 闭式解:w = (X'X + λI)^-1 X'y
            A = Xtr.T @ Xtr + ridge_lambda * np.eye(Xtr.shape[1])
            w = np.linalg.solve(A, Xtr.T @ ytr)
            cs = css[k][1]
            oos_ic.append(fx.spearman(zmat(cs) @ w, cs["_fwd"]))
        m, ic, t, n = summarize(oos_ic)
        print(f"{'合成(拟合/OOS)':<8}{m:>11.4f}{ic:>9.3f}{t:>8.2f}{n:>7}  <- Purged walk-forward Ridge")

        # 长短组合(等权 vs 手配 vs 单因子最佳),H 作为持有,step 重叠->看相对
        print("  长短(tertile)平均每期收益:", end="  ")
        for nm, scorer in [
            ("等权", lambda cs: zmat(cs).sum(1)),
            ("手配", lambda cs: zmat(cs) @ np.array([HAND_WEIGHTS[f] for f in F])),
        ]:
            ls = np.array([tertile_ls(scorer(cs), cs["_fwd"]) for _, cs in css])
            print(f"{nm} {ls.mean()*100:+.2f}%/期", end="   ")
        print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    run()
