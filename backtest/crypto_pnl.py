"""加密因子可交易性诊断:拟合打分 + 单因子的分层单调性与长短 P&L(非重叠月度)。

回答关键问题:正 Rank-IC 是否translate成可交易的长短收益?(等权合成被证明非单调不可交易)
拟合(Ridge, Purged walk-forward)打分逐期生成,只用样本外打分做组合。
"""
from __future__ import annotations

import numpy as np

import crypto_backtest as cb
import crypto_factors as cf
import factors_xs as fx

H = 30
STEP = 3
EMBARGO = 5
LAM = 5.0
F = cf.FACTORS


def fitted_scores(css):
    """逐期 Purged walk-forward Ridge,返回每期(样本外)打分与拟合权重。"""
    out = []
    for k in range(len(css)):
        tr = list(range(0, k - EMBARGO))
        if len(tr) < 8:
            out.append((None, None))
            continue
        X = np.vstack([cb.zmat(css[j][1]) for j in tr])
        y = np.concatenate([(r := fx.rankdata(css[j][1]["_fwd"])) - r.mean() for j in tr])
        w = np.linalg.solve(X.T @ X + LAM * np.eye(X.shape[1]), X.T @ y)
        out.append((cb.zmat(css[k][1]) @ w, w))
    return out


def tertiles(score, fwd):
    o = np.argsort(score); k = len(o) // 3
    return fwd[o[:k]].mean(), fwd[o[k:2*k]].mean(), fwd[o[-k:]].mean()


def main():
    panel = cb.build_panel()
    dates = cb.master_dates(panel, STEP)
    css = [(d, cs) for d in dates if (cs := cb.cross_section(panel, d, H)) is not None]
    fs = fitted_scores(css)

    # 非重叠抽样(每 H/STEP=10 期取一)避免重叠样本
    idx = list(range(0, len(css), H // STEP))
    print(f"加密 {len(panel)} 币, H={H}d, 非重叠 {len(idx)} 期 (~{len(idx)} 月)\n")

    def report(name, scorer):
        acc = np.zeros(3); ls = []; cnt = 0
        for k in idx:
            sc = scorer(k)
            if sc is None:
                continue
            fwd = css[k][1]["_fwd"]
            b, m, t = tertiles(sc, fwd)
            acc += [b, m, t]; ls.append(t - b); cnt += 1
        acc /= cnt; ls = np.asarray(ls)
        sharpe = ls.mean() / ls.std(ddof=1) * np.sqrt(12) if ls.std(ddof=1) > 0 else float("nan")
        print(f"{name:<18} 分层(低/中/高 %): {acc[0]*100:+.1f} {acc[1]*100:+.1f} {acc[2]*100:+.1f}"
              f" | L/S {ls.mean()*100:+.2f}%/月 Sharpe {sharpe:+.2f} 胜率 {(ls>0).mean()*100:.0f}% (n={cnt})")

    report("拟合(OOS Ridge)", lambda k: fs[k][0])
    report("低波 vol_20", lambda k: cf.SIGN["vol_20"] * fx.zscore(css[k][1]["vol_20"]))
    report("动量 mom_14", lambda k: cf.SIGN["mom_14"] * fx.zscore(css[k][1]["mom_14"]))
    report("等权合成", lambda k: cb.zmat(css[k][1]).sum(1))

    # 平均拟合权重(看模型学到了什么)
    ws = np.array([w for _, w in fs if w is not None])
    print("\n平均拟合权重(Ridge 学到的因子载荷):")
    for j, f in enumerate(F):
        print(f"  {f:<12} {ws[:, j].mean():+.3f}")

    # 基准:等权持有所有币(beta)
    bench = []
    for k in idx:
        bench.append(css[k][1]["_fwd"].mean())
    bench = np.asarray(bench)
    bs = bench.mean() / bench.std(ddof=1) * np.sqrt(12) if bench.std(ddof=1) > 0 else float("nan")
    print(f"\n基准(等权持有全部币): {bench.mean()*100:+.2f}%/月 Sharpe {bs:+.2f}")


if __name__ == "__main__":
    main()
