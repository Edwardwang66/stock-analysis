"""回测主程序:加载全市场 -> 计算 TQM 信号 -> 多 horizon 统计正确率 -> 出报告。

用法:
    python run.py                # 默认全 universe,多 horizon
    python run.py --horizon 126  # 指定单一持有期
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

import data as datamod
import engine
import factors

HERE = os.path.dirname(os.path.abspath(__file__))


def load_all(tickers: list[str]) -> dict[str, dict]:
    out = {}
    for tk in tickers:
        d = datamod.load(tk)
        if d and len(d.get("adjclose", [])) > 260:
            out[tk] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=[21, 63, 126, 252])
    ap.add_argument("--trend-min", type=float, default=1.0)
    ap.add_argument("--mom-min", type=float, default=0.05)
    ap.add_argument("--qual-min", type=float, default=0.5)
    ap.add_argument("--rsi-max", type=float, default=80.0)
    ap.add_argument("--overlap", action="store_true", help="允许重叠样本(默认非重叠)")
    args = ap.parse_args()

    uni = json.load(open(os.path.join(HERE, "universe.json")))
    tickers = uni["universe"]
    print(f"universe: {len(tickers)} 只 (S&P500 ∪ Nasdaq-100)")

    t0 = time.time()
    data_all = load_all(tickers)
    print(f"已加载有效历史: {len(data_all)} 只,用时 {time.time()-t0:.1f}s")

    bench = datamod.load("SPY")
    bench_adj = np.asarray(bench["adjclose"], dtype=float) if bench else None
    bench_ts = np.asarray(bench["ts"], dtype=np.int64) if bench else None

    # 预计算每只标的的 TQM 布尔信号(与 horizon 无关)
    t0 = time.time()
    signals = {}
    for tk, d in data_all.items():
        px = np.asarray(d["adjclose"], dtype=float)
        signals[tk] = factors.tqm_signal(
            px, trend_min=args.trend_min, mom_min=args.mom_min,
            qual_min=args.qual_min, rsi_max=args.rsi_max,
        )
    total_sig_days = int(sum(s.sum() for s in signals.values()))
    print(f"已计算信号: 共 {total_sig_days} 个信号日,用时 {time.time()-t0:.1f}s\n")

    report = {"universe_size": len(data_all),
              "params": vars(args),
              "by_horizon": {}}

    print("=" * 70)
    print(f"{'H(日)':>6} {'信号数':>8} {'绝对正确率':>10} {'相对正确率':>10} "
          f"{'均值收益':>9} {'超额':>8} {'基准正比例':>10}")
    print("-" * 70)
    for h in args.horizons:
        res = engine.evaluate(signals, data_all, bench_adj, bench_ts,
                              horizon=h, non_overlap=not args.overlap)
        br = engine.base_rate(data_all, h)
        res["base_rate"] = br
        report["by_horizon"][h] = res
        print(f"{h:>6} {res['n_signals']:>8} "
              f"{res['abs_hit_rate']*100:>9.1f}% "
              f"{res['rel_hit_rate']*100:>9.1f}% "
              f"{res['avg_fwd_return']*100:>8.1f}% "
              f"{res['avg_excess_return']*100:>7.1f}% "
              f"{br['base_hit_rate']*100:>9.1f}%")
    print("=" * 70)

    # 选一个代表 horizon 打印逐年明细
    rep_h = 126 if 126 in args.horizons else args.horizons[-1]
    print(f"\n持有期 H={rep_h} 日 逐年正确率:")
    for y, v in report["by_horizon"][rep_h]["per_year"].items():
        print(f"  {y}: 信号 {v['n']:>5}  正确率 {v['hit_rate']*100:>5.1f}%")

    out_path = os.path.join(HERE, "results", "backtest_report.json")
    json.dump(report, open(out_path, "w"), indent=2, default=float)
    print(f"\n报告已写入 {out_path}")


if __name__ == "__main__":
    main()
