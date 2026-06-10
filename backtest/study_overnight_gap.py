"""隔夜缺口研究 —— HIP-3 永续盘后走势对次日开盘/盘中的信息含量(Cycle 8)。

动机:本仓因子工厂 304 候选中最强落选者是 gap_oc(隔夜跳空,t=1.7);HIP-3 合成美股永续
24/7 交易,给了隔夜信息一个**实时领先版**。本研究回答两个问题(全程无未来函数):

  Q1 代理质量:盘后永续累计走势 ≈ 次日真实开盘缺口吗?
     overnight_perp(D) = P_perp(开盘前30min) / P_perp(前日收盘时刻) - 1
     vs actual_gap(D)  = Open(D)/Close(D-1) - 1(Yahoo 原始价)
     → corr / 方向命中率。高 → 「盘后代理」看板功能成立。

  Q2 信号价值:盘后永续走势能预测**开盘后**的日内走势吗?
     corr(overnight_perp, Close(D)/Open(D)-1) → 缺口延续/反转,这是可交易部分
     (开盘缺口本身无法交易:你只能以开盘价进场)。

时区:美东开盘 = Yahoo 日线 bar 的 ts(13:30 EDT / 14:30 EST,数据自带,无需手工 DST)。
诚实声明:HIP-3 历史短(60~140 交易日/资产)、永续 mark 价含资金费/溢价、
Yahoo 原始价在除息日有小误差;结论按「信息质量测量」解读,不是策略回测。

用法: python backtest/study_overnight_gap.py [--publish]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import data as datamod  # noqa: E402

URL = "https://api.hyperliquid.xyz/info"
# (HL 永续, Yahoo 标的);指数对 ETF(价格水平不同不影响收益率比较)
PAIRS = [
    ("xyz:SP500", "SPY"), ("xyz:XYZ100", "QQQ"), ("xyz:MU", "MU"),
    ("cash:NVDA", "NVDA"), ("cash:GOOGL", "GOOGL"), ("cash:INTC", "INTC"),
]
PRE_OPEN_MARGIN_S = 1800          # 开盘前 30 分钟截止(因果余量)
SESSION_S = int(6.5 * 3600)       # 美股常规时段 6.5h


def post(body: dict):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())


def hl_hourly_closes(coin: str, days: int = 300) -> dict[int, float]:
    """{bar结束时刻(s): close};1h K。"""
    end = int(time.time() * 1000)
    c = post({"type": "candleSnapshot",
              "req": {"coin": coin, "interval": "1h", "startTime": end - days * 86400_000, "endTime": end}})
    return {int(b["T"] // 1000): float(b["c"]) for b in (c or [])}


def perp_at(closes: dict[int, float], target_s: int, tol_s: int = 7200) -> float | None:
    """target 时刻或之前最近一根已完成 1h bar 的 close(差距>tol 视为缺数据)。"""
    ts = max((t for t in closes if t <= target_s), default=None)
    if ts is None or target_s - ts > tol_s:
        return None
    return closes[ts]


def study_pair(perp_coin: str, yh: str):
    closes = hl_hourly_closes(perp_coin)
    if len(closes) < 200:
        return None
    d = datamod.load(yh)
    if not d or len(d.get("ts", [])) < 30:
        datamod.fetch_one(yh)
        d = datamod.load(yh)
        if not d:
            return None
    ts = np.asarray(d["ts"], dtype=np.int64)       # = 当日开盘时刻(Yahoo 自带 DST)
    op = np.asarray(d["open"], dtype=float)
    cl = np.asarray(d["close"], dtype=float)
    hl_start = min(closes)
    rows = []
    for i in range(1, len(ts)):
        t_open = int(ts[i])
        t_prev_close = int(ts[i - 1]) + SESSION_S
        if t_prev_close < hl_start:
            continue
        p_pre = perp_at(closes, t_open - PRE_OPEN_MARGIN_S)
        p_prev = perp_at(closes, t_prev_close)
        if p_pre is None or p_prev is None or p_prev <= 0:
            continue
        if op[i] <= 0 or cl[i - 1] <= 0:
            continue
        rows.append({
            "overnight_perp": p_pre / p_prev - 1.0,
            "actual_gap": op[i] / cl[i - 1] - 1.0,
            "post_open": cl[i] / op[i] - 1.0,
        })
    if len(rows) < 25:
        return None
    on = np.array([r["overnight_perp"] for r in rows])
    gap = np.array([r["actual_gap"] for r in rows])
    po = np.array([r["post_open"] for r in rows])

    def corr(a, b):
        if a.std() < 1e-12 or b.std() < 1e-12:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])
    sign_mask = np.abs(gap) > 1e-4
    return {
        "pair": f"{perp_coin} → {yh}", "n_days": len(rows),
        "proxy_corr": corr(on, gap),
        "proxy_hit": float((np.sign(on) == np.sign(gap))[sign_mask].mean()) if sign_mask.any() else float("nan"),
        "proxy_mae_bps": float(np.mean(np.abs(on - gap)) * 1e4),
        "signal_corr_postopen": corr(on, po),
        "_z_on": (on - on.mean()) / (on.std() + 1e-12),
        "_po": po,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    results = []
    for perp_coin, yh in PAIRS:
        try:
            r = study_pair(perp_coin, yh)
            if r:
                results.append(r)
                print(f"{r['pair']:<22} n={r['n_days']:<4} 代理corr={r['proxy_corr']:+.3f} "
                      f"方向命中={r['proxy_hit']*100:.0f}% MAE={r['proxy_mae_bps']:.0f}bps "
                      f"| 信号→盘中corr={r['signal_corr_postopen']:+.3f}")
            else:
                print(f"{perp_coin:<22} 样本不足/数据缺")
        except Exception as e:  # noqa: BLE001
            print(f"{perp_coin:<22} FAIL {type(e).__name__} {e}")
    if not results:
        print("无可用结果")
        return

    # 合并信号检验(各资产 z 分后汇总):盘后永续走势 → 开盘后日内收益
    Z = np.concatenate([r["_z_on"] for r in results])
    PO = np.concatenate([r["_po"] for r in results])
    pooled_corr = float(np.corrcoef(Z, PO)[0, 1])
    n_pool = len(Z)
    t_stat = pooled_corr * np.sqrt(max(n_pool - 2, 1)) / np.sqrt(max(1e-12, 1 - pooled_corr ** 2))
    avg_proxy = float(np.mean([r["proxy_corr"] for r in results]))

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# 隔夜缺口研究:HIP-3 永续盘后走势的信息含量({date})",
        "",
        "| 资产对 | 天数 | 代理 corr | 方向命中 | MAE | 盘后走势→开盘后盘中 corr |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['pair']} | {r['n_days']} | {r['proxy_corr']:+.3f} | {r['proxy_hit']*100:.0f}% "
                     f"| {r['proxy_mae_bps']:.0f}bps | {r['signal_corr_postopen']:+.3f} |")
    lines += [
        "",
        f"**Q1 代理质量**:平均 corr={avg_proxy:+.3f} —— {'成立:看板「盘后代理」功能有真实信息' if avg_proxy > 0.7 else '一般/不成立,谨慎使用盘后代理'}。",
        f"**Q2 信号价值**:合并 {n_pool} 天,盘后走势→开盘后盘中收益 corr={pooled_corr:+.3f}(t≈{t_stat:.1f})"
        f" —— {'有苗头,值得进六门控管线' if abs(t_stat) >= 2 else '无显著预测力(开盘价已吸收信息,与有效市场一致)'}。",
        "",
        "## 诚实声明",
        f"- 样本极短(HIP-3 历史 3-7 个月);t 未经多重检验校正;本研究 1 次试验已登记。",
        "- 永续 mark 价含资金费/溢价;Yahoo 原始价除息日有小误差;未建模任何交易成本。",
        "- Q2 若不显著恰恰符合预期:开盘集合竞价会吸收隔夜公开信息(§3.8)。",
    ]
    md = "\n".join(lines)
    out = os.path.join(os.path.dirname(HERE), "docs", f"study-overnight-gap-{date}.md")
    open(out, "w", encoding="utf-8").write(md + "\n")
    print("\n" + "\n".join(lines[2:]))
    print(f"\n已写 {os.path.relpath(out)}")

    if args.publish:
        import feed_lib as fl
        spy_ts = datamod.load("SPY")["ts"]
        asof = datetime.utcfromtimestamp(int(spy_ts[-1])).strftime("%Y-%m-%d")
        now = datetime.now(timezone.utc)
        report = {
            "schema_version": "1.0",
            "id": f"study-overnight-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": asof,
            "producer": {"name": "study-overnight-gap", "agent_role": "engine"},
            "alerts": [{"level": "info", "code": "overnight-gap-study",
                        "message": f"HIP-3 盘后代理质量 corr={avg_proxy:+.2f}(6 资产对);"
                                   f"盘后走势→开盘后盘中 corr={pooled_corr:+.3f}(t≈{t_stat:.1f},n={n_pool})。"
                                   f"详见 docs/study-overnight-gap-{date}.md", "tickers": []}],
            "contribution": {"type": "regime_update",
                             "summary": f"隔夜缺口研究:代理质量 {avg_proxy:+.2f},信号价值 t≈{t_stat:.1f}。"},
            "notes": "信息质量测量,非策略回测;样本短,1 次试验已登记。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("feed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
