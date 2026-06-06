"""横截面(cross-sectional)因子库 —— 纯价量,无未来函数。

与 §1.1 一致:这里做的是"同一时点给所有股票排序"的横截面因子,
而非上一版 backtest/factors.py 的时序择时信号。每个因子在某 rebalance 日 d
只用 d 及之前的数据计算,符号统一为"越大 = 预期未来收益越高"(便于合成)。

四个纯价量因子(value/quality/PEAD 需财报数据,本数据集没有,诚实略去):
  - mom_12_1  : 12-1 动量(过去 252 日收益,跳过最近 21 日)        方向 +
  - reversal  : 1 月短期反转(过去 21 日收益),合成时取负          方向 -(原值)
  - hi52      : 价格 / 过去 252 日最高(52 周高点接近度,George-Hwang) 方向 +
  - lowvol    : 过去 63 日日收益年化波动,合成时取负                方向 -(原值)
"""
from __future__ import annotations

import numpy as np

# 每个因子在合成时的方向(+1 原值越大越好,-1 取负后越大越好)
FACTOR_SIGN = {"mom_12_1": +1, "reversal": -1, "hi52": +1, "lowvol": -1}


def factor_values(adj: np.ndarray, i: int) -> dict | None:
    """在位置 i(某 rebalance 日)计算四个因子的原始值;数据不足返回 None。"""
    if i < 252:
        return None
    win252 = adj[i - 252:i + 1]
    mx = win252.max()
    if mx <= 0 or adj[i - 252] <= 0 or adj[i - 21] <= 0:
        return None
    # 日对数收益(过去 63 日)算波动
    seg = adj[i - 63:i + 1]
    rets = np.log(seg[1:] / seg[:-1])
    vol = float(rets.std(ddof=1) * np.sqrt(252)) if len(rets) > 2 else np.nan
    return {
        "mom_12_1": adj[i - 21] / adj[i - 252] - 1.0,
        "reversal": adj[i] / adj[i - 21] - 1.0,
        "hi52": adj[i] / mx,
        "lowvol": vol,
    }


def zscore(x: np.ndarray) -> np.ndarray:
    """横截面 z-score(对 nan 稳健)。"""
    m = np.nanmean(x)
    s = np.nanstd(x)
    if not np.isfinite(s) or s == 0:
        return np.zeros_like(x)
    return (x - m) / s


def rankdata(a: np.ndarray) -> np.ndarray:
    """平均秩(等价 scipy.stats.rankdata 'average'),用于 Spearman。"""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1)
    # 处理并列:同值取平均秩
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    csum = np.cumsum(counts)
    start = csum - counts
    avg = (start + csum + 1) / 2.0
    return avg[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman 秩相关(= 秩上的 Pearson)。"""
    if len(x) < 5:
        return np.nan
    rx, ry = rankdata(x), rankdata(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / denom) if denom > 0 else np.nan
