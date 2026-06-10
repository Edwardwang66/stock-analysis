"""PIT 过滤在 516 全名单上的「咬合」量化 —— 指数成员前视到底污染了多少?(Cycle 11)

DEMO 面板(老牌大盘)上 PIT 剔除为 0;本研究换到 universe.json 的 516 全名单
(S&P500∪NDX100,含 ABNB/APP/PLTR 等近年新增),对照 PIT 开/关:
  1. 咬合度:被剔除的「名·期」占比(=指数成员前视的暴露面);
  2. 影响:同一套预注册候选(N=304)的 train 段 top |t| 与过门数,PIT 开 vs 关
     → 前视给因子统计「白送」了多少显著性。

用法: python backtest/study_pit_bite.py [--publish](先下载 516 名单数据,全程 ~10-15 分钟)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import data as datamod         # noqa: E402
import factor_factory as ffy   # noqa: E402


def eval_panel(cross, dates, label: str) -> dict:
    import datetime as _dt
    cut = int(_dt.datetime.strptime(ffy.TRAIN_END, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc).timestamp())
    train_idx = [i for i, t in enumerate(dates) if t < cut]
    cands = ffy.propose_candidates()
    for c in cands:
        c["train"] = ffy.score_candidate(c, cross, train_idx)
    ts = np.asarray([abs(c["train"]["t"]) for c in cands])
    pvals = np.asarray([2 * (1 - 0.5 * (1 + math.erf(t / math.sqrt(2)))) for t in ts])
    sig = ffy.by_fdr(pvals, q=0.10)
    n_pass = sum(1 for i, c in enumerate(cands)
                 if sig[i] and abs(c["train"]["t"]) >= 3.0
                 and np.isfinite(c["train"]["net_ir_per_period"]) and c["train"]["net_ir_per_period"] > 0
                 and c["train"]["net_ann"] > 0)
    top = sorted(cands, key=lambda c: -abs(c["train"]["t"]))[:5]
    return {"label": label, "n_periods": len(dates), "n_pass": n_pass,
            "avg_xsec": float(np.mean([len(c0["fwd"]) for c0 in cross])),
            "top": [{"expr": c["expr"], "t": round(c["train"]["t"], 2),
                     "ic": round(c["train"]["ic"], 4)} for c in top]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    uni = json.load(open(os.path.join(HERE, "universe.json")))["universe"]
    print(f"universe.json 全名单 {len(uni)} 只")
    if not args.skip_download:
        res = datamod.fetch_universe(uni + ["SPY"], range_="10y", workers=12)
        print(f"下载 {sum(1 for v in res.values() if v > 0)}/{len(set(uni))+1} 成功")

    results = []
    bite = None
    for pit_on in (True, False):
        print(f"\n=== 构面板 pit_filter={pit_on} ===")
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            dates, cross = ffy.build_panel(pit_filter=pit_on, tickers=uni)
        log = buf.getvalue()
        print(log.strip())
        if pit_on and "剔除" in log:
            import re
            m = re.search(r"剔除 (\d+)/(\d+)", log)
            if m:
                bite = (int(m.group(1)), int(m.group(2)))
        r = eval_panel(cross, dates, "PIT开(时点成分)" if pit_on else "PIT关(当前成分=有前视)")
        results.append(r)
        print(f"  期数 {r['n_periods']} 平均横截面 {r['avg_xsec']:.0f} 过门 {r['n_pass']} "
              f"top|t| {r['top'][0]['t']:+.2f} ({r['top'][0]['expr']})")

    date_s = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bite_s = f"{bite[0]}/{bite[1]}({bite[0]/bite[1]*100:.1f}%)" if bite else "n/a"
    lines = [
        f"# PIT 过滤咬合量化:516 全名单({date_s})",
        "",
        f"**咬合度:剔除 {bite_s} 名·期** —— 这就是「用今天的成分回测过去」在真实研究 universe 上的前视暴露面。",
        "",
        "| 面板 | 期数 | 平均横截面 | 过六门候选 | top1 |t| | top1 表达式 |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['label']} | {r['n_periods']} | {r['avg_xsec']:.0f} | {r['n_pass']} "
                     f"| {abs(r['top'][0]['t']):.2f} | `{r['top'][0]['expr']}` |")
    dt_pass = results[1]["n_pass"] - results[0]["n_pass"]
    lines += [
        "",
        f"前视「白送」的过门候选数:{dt_pass:+d}(关-开)。",
        "## top5 对照(PIT开 → 关)",
    ] + [f"- `{a['expr']}` t {a['t']:+.2f} | 无PIT版 t {b['t']:+.2f}"
         for a, b in zip(results[0]["top"], results[1]["top"])] + [
        "",
        "## 诚实声明",
        "- 仍有幸存者偏差残留:被剔的是「当时不在指数」的票,但「当时在指数后来退市」的票本就缺数据",
        "  (Cycle 9 量化:2021 缺失率 ~10%),PIT 过滤无法找回它们,只能消「未来赢家提早入场」这一半。",
        "- NDX100 成员资格未做 PIT(只有 S&P500 变更史);516 名单中纯 NDX 票不受过滤。",
    ]
    md = "\n".join(lines)
    out = os.path.join(os.path.dirname(HERE), "docs", f"study-pit-bite-{date_s}.md")
    open(out, "w", encoding="utf-8").write(md + "\n")
    print("\n" + md)

    if args.publish:
        import feed_lib as fl
        now = datetime.now(timezone.utc)
        spy_ts = datamod.load("SPY")["ts"]
        asof = datetime.utcfromtimestamp(int(spy_ts[-1])).strftime("%Y-%m-%d")
        report = {
            "schema_version": "1.0",
            "id": f"study-pitbite-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": asof,
            "producer": {"name": "study-pit-bite", "agent_role": "engine"},
            "alerts": [{"level": "info", "code": "pit-bite",
                        "message": f"516 全名单 PIT 咬合:剔除 {bite_s} 名·期;"
                                   f"无 PIT 面板多过门 {dt_pass:+d} 个候选(前视白送的显著性)。", "tickers": []}],
            "contribution": {"type": "regime_update",
                             "summary": f"指数成员前视量化:咬合 {bite_s};过门差 {dt_pass:+d}。"},
            "notes": "PIT 只消『未来赢家提早入场』;退市缺数据(~10%@2021)仍在,见 Cycle 9。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("feed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
