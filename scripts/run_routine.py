"""每日/每小时例行任务 —— 运行做多做空引擎 + 市场快照,产出一份情报报告写入 feed/。

这就是「在 Claude 里生成一个 routine,不断 post 报告,静态网页不断接受」的本仓实现端:
  1. 运行流 B 残差统计套利引擎(backtest/statarb.py),得净·扣成本绩效 + 当前持仓簿。
  2. 计算市场状态快照(regime / 广度 / 拥挤代理)。
  3. (可选)调用 LLM 假设工厂产出可审计公式因子候选(默认关闭;见 routines/daily-alpha-routine.md)。
  4. 组装为统一 schema 的报告,publish 到 feed/(刷新 index/signals/market/factory)。

用法:
  python scripts/run_routine.py                  # 全量(下载数据缺失则报错提示)
  python scripts/run_routine.py --fast            # 复用缓存、缩短区间,几秒出结果(CI 友好)
  python scripts/run_routine.py --demo-candidate  # 注入 1 条「契约示例」因子候选(明确标注未过门控)

环境变量:
  FEED_HMAC_SECRET  设置则给报告签名(与 OpenClaw 同一套校验)。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "backtest"))
sys.path.insert(0, HERE)

import data as datamod          # noqa: E402  (backtest/data.py)
import statarb as sa            # noqa: E402  (backtest/statarb.py)
import feed_lib as fl           # noqa: E402


def market_state(tickers: list[str]) -> dict:
    """从价格面板算一个诚实、简单的市场状态快照(无 LLM、无未来函数)。"""
    spy = datamod.load("SPY")
    out = {"regime": "unknown", "spy_above_200dma": None, "spy_vol_20d_annual": None,
           "breadth_pct_above_50dma": None, "crowding_proxy": None, "crowding_alert": False,
           "residual_dispersion": None}
    if spy and len(spy.get("adjclose", [])) > 220:
        adj = np.asarray(spy["adjclose"], dtype=float)
        ma200 = adj[-200:].mean()
        rets = np.diff(np.log(adj[-21:]))
        vol = float(rets.std(ddof=1) * np.sqrt(252)) if len(rets) > 2 else None
        above = bool(adj[-1] > ma200)
        out["spy_above_200dma"] = above
        out["spy_vol_20d_annual"] = round(vol, 4) if vol else None
        if above and vol is not None and vol < 0.18:
            out["regime"] = "risk_on"
        elif (not above) or (vol is not None and vol > 0.28):
            out["regime"] = "risk_off"
        else:
            out["regime"] = "neutral"

    # 广度 + 拥挤代理:用 universe 近 60 日收益
    rmat, above50 = [], 0
    n = 0
    for tk in tickers:
        d = datamod.load(tk)
        if not d or len(d.get("adjclose", [])) < 70:
            continue
        a = np.asarray(d["adjclose"], dtype=float)
        n += 1
        if a[-1] > a[-50:].mean():
            above50 += 1
        r = np.diff(np.log(a[-61:]))
        if len(r) == 60:
            rmat.append(r)
    if n:
        out["breadth_pct_above_50dma"] = round(above50 / n, 3)
    if len(rmat) > 5:
        R = np.array(rmat)
        C = np.corrcoef(R)
        iu = np.triu_indices_from(C, k=1)
        avg_corr = float(np.nanmean(C[iu]))
        out["crowding_proxy"] = round(avg_corr, 3)            # 平均两两相关 = 拥挤代理(§7.2)
        out["crowding_alert"] = bool(avg_corr > 0.55)
        out["residual_dispersion"] = round(float(np.nanmean(np.nanstd(R, axis=1))), 4)
    return out


def build_alerts(rep: dict, ms: dict) -> list[dict]:
    alerts = []
    if ms.get("crowding_alert"):
        alerts.append({"level": "warning", "code": "crowding",
                       "message": f"拥挤代理(平均相关){ms.get('crowding_proxy')} > 0.55:尾部风险升高,"
                                  f"按 R7 应先于人群减杠杆。", "tickers": []})
    br = rep.get("latest_breaker", [])
    if len(br) >= max(3, int(0.4 * rep.get("universe_size", 1))):
        alerts.append({"level": "info", "code": "cointegration_breaker",
                       "message": f"{len(br)} 只标的触发协整断裂熔断(Hurst/半衰期/极端 s),已自动排除。",
                       "tickers": [b["ticker"] for b in br[:10]]})
    net = (rep.get("net") or {})
    if net.get("max_drawdown", 0) <= -0.12:
        alerts.append({"level": "critical", "code": "drawdown",
                       "message": f"回测最大回撤 {net['max_drawdown']*100:.1f}% 触及回撤治理阈值(§7.4)。",
                       "tickers": []})
    return alerts


def demo_candidate() -> dict:
    """一条『契约示例』因子候选 —— 明确标注未接 LLM、未过门控,仅用于演示 feed/看板结构。"""
    return {
        "expr": "rank(-ts_zscore(residual_return, 5)) * sign(adv_20)",
        "hypothesis": "5 日残差被过度外推 -> 反转;以流动性为门(事前经济机制)。",
        "post_cutoff": False, "passed_gates": False, "decision": "reject",
        "note": "示例候选:未接真实 LLM、未跑六门控(§6.2.3),增量 IC/PBO/t 留空。仅演示契约,不可交易。",
    }


def prev_net_sharpe() -> float | None:
    idx = fl.load_json(os.path.join(fl.FEED, "index.json"))
    if idx and idx.get("reports"):
        for r in idx["reports"]:
            ns = r.get("net_sharpe")
            if ns is not None:
                return ns
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="缩短区间、复用缓存(CI 友好)")
    ap.add_argument("--demo-candidate", action="store_true", help="注入 1 条契约示例因子候选")
    ap.add_argument("--start-year", type=int, default=None)
    args = ap.parse_args()

    p = sa.StatArbParams()
    if args.fast:
        p.start_year = 2024
    if args.start_year:
        p.start_year = args.start_year

    tickers = sa.DEMO_UNIVERSE
    print(f"[routine] 运行流 B 引擎,universe {len(tickers)} 只,起始 {p.start_year} ...")
    rep = sa.run(tickers, p, verbose=False)
    ms = market_state(tickers)

    prev = prev_net_sharpe()
    net_sharpe = (rep.get("net") or {}).get("sharpe")
    cands = [demo_candidate()] if args.demo_candidate else []

    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "id": f"routine-{now.strftime('%Y-%m-%dT%H%M')}Z",
        "kind": "routine",
        "produced_at": fl.now_iso(),
        "asof_data": rep["period"]["end"],
        "producer": {"name": "github-actions-routine", "agent_role": "engine",
                     "run_url": os.environ.get("GITHUB_RUN_URL", "")},
        "market_state": ms,
        "engine": {
            "name": rep["engine"], "period": rep["period"], "net": rep["net"], "gross": rep["gross"],
            "cost_drag_ann": rep["cost_drag_ann"], "borrow_cost_ann": rep.get("borrow_cost_ann", 0),
            "turnover": rep["turnover"],
            "deflated_sharpe": rep["deflated_sharpe"], "verdict": rep["verdict"],
            "train": rep.get("train"), "holdout": rep.get("holdout"),
            "equity_curve": rep.get("equity_curve", []),
        },
        "book": rep["latest_book"],
        "factory_candidates": cands,
        "alerts": build_alerts(rep, ms),
        "contribution": {
            "type": "signal_refresh" if not cands else "new_factor",
            "summary": f"刷新做多做空簿(多 {rep['latest_book']['n_long']}/空 {rep['latest_book']['n_short']}),"
                       f"净 Sharpe {net_sharpe:+.2f};市场 {ms['regime']}、广度 "
                       f"{ms.get('breadth_pct_above_50dma')}、拥挤 {ms.get('crowding_proxy')}。",
            "candidates_proposed": len(cands),
            "candidates_accepted": sum(1 for c in cands if c.get("decision") == "accept"),
            "net_sharpe_delta": round(net_sharpe - prev, 3) if (prev is not None and net_sharpe is not None) else None,
        },
        "notes": "净·扣成本为唯一计价货币(R4);LLM 仅生成假设、不决策(R6);结论须真 holdout 终检(R5)。",
    }

    res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
    if not res["ok"]:
        print("[routine] 校验失败:", res["errors"])
        sys.exit(1)
    print(f"[routine] 已发布 {report['id']} -> {os.path.relpath(res['path'], ROOT)}")
    print(f"[routine] 净 Sharpe={net_sharpe:+.2f} | {rep['verdict']}")
    print(f"[routine] feed 统计: {res['index_stats']}")


if __name__ == "__main__":
    main()
