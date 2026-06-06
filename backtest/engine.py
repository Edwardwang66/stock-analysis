"""回测引擎:把因子信号映射到"前瞻收益",统计正确率(hit rate)。

正确率定义(两种,都报告,避免只挑好看的口径):
  1) 绝对正确率:信号触发后,持有 H 日的前瞻收益 > 0 的比例。
  2) 相对正确率:同期跑赢基准(SPY)的比例 —— 这是更严格的 alpha 口径。

无未来函数:t 日收盘确认信号,t+1 开盘视为建仓(用 t 日收盘价近似,
对日线长持影响极小),持有到 t+H。前瞻收益用复权价。

为避免重叠样本把同一行情重复计数,提供 non_overlap 选项:同一标的相邻信号
至少间隔 H 日才计一次。
"""
from __future__ import annotations

import datetime as dt
import numpy as np


def _year_of(ts_epoch: int) -> int:
    return dt.datetime.utcfromtimestamp(ts_epoch).year


def forward_returns(adj: np.ndarray, h: int) -> np.ndarray:
    """每个位置 i 的未来 h 日收益(到 i+h);末尾 h 个为 nan。"""
    fr = np.full_like(adj, float("nan"), dtype=float)
    fr[:-h] = adj[h:] / adj[:-h] - 1.0
    return fr


def evaluate(signals: dict[str, np.ndarray],
             data: dict[str, dict],
             bench_adj: np.ndarray | None,
             bench_ts: np.ndarray | None,
             horizon: int = 63,
             non_overlap: bool = True) -> dict:
    """统计一组标的的信号正确率。

    signals[ticker]: 布尔数组,与 data[ticker]['adjclose'] 对齐。
    data[ticker]: load() 返回的列式 dict。
    bench_*: 基准(SPY)的复权价与时间戳,用于相对口径(按日期对齐)。
    返回汇总统计 + 逐年明细。
    """
    bench_by_day = {}
    if bench_adj is not None:
        bench_fr = forward_returns(bench_adj, horizon)
        for i, t in enumerate(bench_ts):
            bench_by_day[int(t)] = bench_fr[i]

    n_sig = 0
    abs_hits = 0          # 前瞻收益 > 0
    rel_hits = 0          # 跑赢基准
    rel_total = 0         # 有基准可比的样本数
    frs: list[float] = []
    excess: list[float] = []
    per_year: dict[int, list[int]] = {}   # year -> [n, abs_hits]

    for tk, sig in signals.items():
        d = data.get(tk)
        if not d:
            continue
        adj = np.asarray(d["adjclose"], dtype=float)
        ts = np.asarray(d["ts"], dtype=np.int64)
        if len(adj) <= horizon:
            continue
        fr = forward_returns(adj, horizon)
        last_taken = -10 ** 9
        for i in range(len(adj)):
            if not sig[i] or np.isnan(fr[i]):
                continue
            if non_overlap and (i - last_taken) < horizon:
                continue
            last_taken = i
            n_sig += 1
            frs.append(fr[i])
            if fr[i] > 0:
                abs_hits += 1
            yr = _year_of(int(ts[i]))
            slot = per_year.setdefault(yr, [0, 0])
            slot[0] += 1
            slot[1] += 1 if fr[i] > 0 else 0
            bfr = bench_by_day.get(int(ts[i]))
            if bfr is not None and not np.isnan(bfr):
                rel_total += 1
                ex = fr[i] - bfr
                excess.append(ex)
                if ex > 0:
                    rel_hits += 1

    frs_a = np.asarray(frs) if frs else np.array([0.0])
    out = {
        "horizon": horizon,
        "n_signals": n_sig,
        "abs_hit_rate": abs_hits / n_sig if n_sig else float("nan"),
        "rel_hit_rate": rel_hits / rel_total if rel_total else float("nan"),
        "avg_fwd_return": float(frs_a.mean()),
        "median_fwd_return": float(np.median(frs_a)),
        "avg_excess_return": float(np.mean(excess)) if excess else float("nan"),
        "per_year": {y: {"n": v[0], "hit_rate": v[1] / v[0] if v[0] else float("nan")}
                     for y, v in sorted(per_year.items())},
    }
    return out


def base_rate(data: dict[str, dict], horizon: int, sample_every: int = 5) -> dict:
    """基准:不挑信号,所有日(每 sample_every 取一)的前瞻收益正比例。

    用于回答"因子相对随机/买入持有提升了多少正确率"。
    """
    n = 0
    hits = 0
    for tk, d in data.items():
        adj = np.asarray(d["adjclose"], dtype=float)
        if len(adj) <= horizon:
            continue
        fr = forward_returns(adj, horizon)
        for i in range(0, len(adj), sample_every):
            if np.isnan(fr[i]):
                continue
            n += 1
            if fr[i] > 0:
                hits += 1
    return {"n": n, "base_hit_rate": hits / n if n else float("nan")}
