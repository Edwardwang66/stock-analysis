"""参数网格 × CSCV-PBO 研究 —— 「我的参数选择本身过拟合了吗?」(设计文档 §6.7)

跑一组经济动机的参数变体(围绕 StatArbParams 默认值),把各配置的日净收益拼成矩阵,
用 CSCV(Bailey-LdP 2014)估计 PBO:IS 最优配置在 OOS 落入后半段的概率。
  PBO ≈ 0.5 → 配置间排名纯随机(参数不敏感或全无 edge)
  PBO  < 0.1 → IS 选择在 OOS 大概率保持 → 选择过程可信
  PBO  > 0.5 → IS 最优系统性地 OOS 反转 → 网格本身在过拟合

同时输出每个配置 train/holdout 净 Sharpe,直接回答「vol-scaling/更宽半衰期等变体是否更好」。
产出: docs/study-pbo-<date>.md + (可选 --publish) feed 报告(kind=manual)。

用法: python backtest/study_pbo.py [--publish] [--fast]
注意: 全量约 8-10 分钟(10 配置 × ~45s)。--fast 用 2024 起的短样本(~2 分钟,结论仅供冒烟)。
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import statarb as sa          # noqa: E402
import validation as val      # noqa: E402

# 经济动机的变体网格(每个只动一个旋钮;不是为了搜出"最好",是为了测排名稳定性)
GRID: list[tuple[str, dict]] = [
    ("base", {}),
    ("s_open=1.0(更松开仓)", {"s_open": 1.0}),
    ("s_open=1.5(更严开仓)", {"s_open": 1.5}),
    ("window=40(短窗)", {"window": 40}),
    ("window=90(长窗)", {"window": 90}),
    ("trade_rate=0.10(更粘)", {"trade_rate": 0.10}),
    ("trade_rate=0.25(更快)", {"trade_rate": 0.25}),
    ("max_positions=50(更专注)", {"max_positions": 50}),
    ("vol_target=4%(波动缩放)", {"vol_target": 0.04}),
    ("hl=[3,40](宽半衰期带)", {"hl_min": 3.0, "hl_max": 40.0}),
]


def run_grid(fast: bool) -> tuple[list[dict], np.ndarray]:
    rows, series = [], []
    t0 = time.time()
    for i, (label, overrides) in enumerate(GRID):
        p = sa.StatArbParams(**overrides)
        if fast:
            p.start_year = 2024
        rep = sa.run(p=p, verbose=False)
        net = np.asarray(rep["_net_series"])
        rows.append({
            "label": label, "overrides": overrides,
            "net_sharpe": rep["net"]["sharpe"],
            "train_sharpe": rep["train"]["sharpe"],
            "holdout_sharpe": rep["holdout"]["sharpe"],
            "max_dd": rep["net"]["max_drawdown"],
            "turnover_daily": rep["turnover"]["avg_daily"],
            "n_days": len(net),
        })
        series.append(net)
        print(f"  [{i+1}/{len(GRID)}] {label:<28} 净SR {rep['net']['sharpe']:+.2f} "
              f"(train {rep['train']['sharpe']:+.2f} / holdout {rep['holdout']['sharpe']:+.2f})"
              f"  累计 {time.time()-t0:.0f}s")
    L = min(len(s) for s in series)
    M = np.vstack([s[-L:] for s in series])     # 对齐尾部(各配置预热长度略差)
    return rows, M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--publish", action="store_true", help="把结论发布为 feed 报告(kind=manual)")
    args = ap.parse_args()

    print(f"参数网格 {len(GRID)} 配置 × CSCV-PBO  (fast={args.fast})")
    rows, M = run_grid(args.fast)
    pbo = val.cscv_pbo(M, n_blocks=8)

    best_train = max(rows, key=lambda r: r["train_sharpe"])
    best_holdout = max(rows, key=lambda r: r["holdout_sharpe"])
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"# 参数网格 × CSCV-PBO 研究({date})",
        "",
        f"问题:围绕默认参数的 {len(GRID)} 个经济变体,IS 选优在 OOS 是否站得住?(设计文档 §6.7)",
        "",
        f"**PBO = {pbo['pbo']:.2f}**(C(8,4)={pbo['n_combos']} 组合;≈0.5=排名纯随机,<0.1=选择可信)",
        f"IS 最优的平均 OOS 排名分位:{pbo['avg_oos_rank']:.2f}(1=最好)",
        "",
        "| 配置 | 净SR(全) | train | holdout | 回撤 | 日换手 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['label']} | {r['net_sharpe']:+.2f} | {r['train_sharpe']:+.2f} "
                     f"| {r['holdout_sharpe']:+.2f} | {r['max_dd']*100:.1f}% | {r['turnover_daily']*100:.0f}% |")
    lines += [
        "",
        f"train 最优:{best_train['label']}(train {best_train['train_sharpe']:+.2f} → holdout {best_train['holdout_sharpe']:+.2f})",
        f"holdout 最优:{best_holdout['label']}(holdout {best_holdout['holdout_sharpe']:+.2f})——只记录,不据此改默认(否则 holdout 就被污染)",
        "",
        "## 诚实解读",
        f"- 所有配置净 Sharpe 均 {'≤0' if all(r['net_sharpe'] <= 0 for r in rows) else '见表'}:参数旋钮不改变「免费数据上无净 alpha」的结论(R4)。",
        "- PBO 高 → IS 选优不可信,任何「调参改进」大概率是噪声;这正是本研究要先于调参回答的问题。",
        "- 本网格已预注册于本文件(GRID),试验次数 N 已计入 —— 后续 DSR 申报应据此累加(§6.7 元过拟合)。",
        "",
        f"_runtime: fast={args.fast}, 区间尾部对齐 {rows[0]['n_days']} 日_",
    ]
    md = "\n".join(lines)
    out = os.path.join(os.path.dirname(HERE), "docs", f"study-pbo-{date}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(f"\n已写 {os.path.relpath(out)}\nPBO={pbo['pbo']:.2f}  avg_oos_rank={pbo['avg_oos_rank']:.2f}")

    if args.publish:
        import feed_lib as fl
        import datetime as _dt
        import data as datamod
        now = datetime.now(timezone.utc)
        spy_ts = datamod.load("SPY")["ts"]
        asof = _dt.datetime.utcfromtimestamp(int(spy_ts[-1])).strftime("%Y-%m-%d")
        report = {
            "schema_version": "1.0",
            "id": f"study-pbo-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": asof,
            "producer": {"name": "study-pbo", "agent_role": "engine"},
            "alerts": [{
                "level": "info" if pbo["pbo"] < 0.5 else "warning", "code": "pbo-study",
                "message": f"参数网格({len(GRID)}配置)CSCV PBO={pbo['pbo']:.2f};"
                           f"全部配置净SR≤0={all(r['net_sharpe'] <= 0 for r in rows)};详见 docs/study-pbo-{date}.md",
                "tickers": [],
            }],
            "contribution": {
                "type": "regime_update",
                "summary": f"PBO 研究:{len(GRID)} 参数变体 CSCV PBO={pbo['pbo']:.2f},"
                           f"train最优={best_train['label']},holdout 上 {best_train['holdout_sharpe']:+.2f}。",
            },
            "notes": "预注册参数网格的过拟合概率测量;不据 holdout 调参。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("feed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
