"""实验:在 TQM 上叠加"大盘择时闸门"(SPY>200日线)+ 收紧阈值 + 长持有期,
观察绝对正确率能被推到多高,以及相对(alpha)正确率是否同步提升。

目的是诚实地拆解"高正确率"来自哪里:漂移 + 牛市择时 + 选择性,而非预测 alpha。
"""
from __future__ import annotations

import json
import os

import numpy as np

import data as datamod
import engine
import factors

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    data_all = {tk: d for tk in uni["universe"]
                if (d := datamod.load(tk)) and len(d.get("adjclose", [])) > 260}

    bench = datamod.load("SPY")
    bench_adj = np.asarray(bench["adjclose"], dtype=float)
    bench_ts = np.asarray(bench["ts"], dtype=np.int64)

    # SPY 200日线择时:date -> 是否牛市(SPY>SMA200)
    sma200 = factors._sma(bench_adj, 200)
    regime_by_day = {int(bench_ts[i]): (not np.isnan(sma200[i]) and bench_adj[i] > sma200[i])
                     for i in range(len(bench_adj))}

    configs = [
        ("TQM 基础", dict(trend_min=1.0, mom_min=0.05, qual_min=0.5, rsi_max=80), False),
        ("TQM 收紧", dict(trend_min=1.0, mom_min=0.15, qual_min=1.0, rsi_max=75), False),
        ("TQM 收紧 + 大盘择时", dict(trend_min=1.0, mom_min=0.15, qual_min=1.0, rsi_max=75), True),
        ("TQM 强选 + 大盘择时", dict(trend_min=1.0, mom_min=0.20, qual_min=1.2, rsi_max=72), True),
    ]
    horizon = 252

    print(f"universe {len(data_all)} 只, 持有期 H={horizon} 日\n")
    print(f"{'配置':<24} {'信号数':>7} {'绝对正确率':>9} {'相对正确率':>9} {'均值收益':>8} {'超额':>7}")
    print("-" * 72)
    for name, params, use_regime in configs:
        signals = {}
        for tk, d in data_all.items():
            px = np.asarray(d["adjclose"], dtype=float)
            sig = factors.tqm_signal(px, **params)
            if use_regime:
                ts = np.asarray(d["ts"], dtype=np.int64)
                mask = np.array([regime_by_day.get(int(t), False) for t in ts])
                sig = sig & mask
            signals[tk] = sig
        res = engine.evaluate(signals, data_all, bench_adj, bench_ts,
                              horizon=horizon, non_overlap=True)
        print(f"{name:<22} {res['n_signals']:>7} "
              f"{res['abs_hit_rate']*100:>8.1f}% "
              f"{res['rel_hit_rate']*100:>8.1f}% "
              f"{res['avg_fwd_return']*100:>7.1f}% "
              f"{res['avg_excess_return']*100:>6.1f}%")


if __name__ == "__main__":
    main()
