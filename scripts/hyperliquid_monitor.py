"""Hyperliquid 衍生品情报监控 —— 用 HL 公开接口补系统的实时信息缺口。

接口与用途(全部免 key、POST https://api.hyperliquid.xyz/info):
  metaAndAssetCtxs            主 DEX 230 永续:funding/OI/premium/markPx/24h量
                              → 加密持仓面/拥挤度(设计文档 §7.2:拥挤是尾部风险信号)
  metaAndAssetCtxs + dex=...  HIP-3 builder DEX:**24/7 合成美股/指数/大宗/私有公司永续**
                              → 美股盘后/周末价格发现(xyz:SP500 日成交 ~$7亿)
  predictedFundings           Binance/HL/Bybit 同资产预测资金费并排 → 跨所错位计数

产出:
  feed/crypto/state.json      看板「衍生品情报」卡片的数据源(含上次快照对比的 OI 变化)
  feed 报告(kind=routine)     market_state 增量 + 资金费极端/拥挤 alerts

用法: python scripts/hyperliquid_monitor.py [--publish] [--quiet]
设计:纯 stdlib;任何子项失败不影响其余(免费接口,builder DEX 随时可能下线)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402

URL = "https://api.hyperliquid.xyz/info"
STATE_PATH = os.path.join(fl.FEED, "crypto", "state.json")

# 关注的 builder DEX(2026-06 实测;探测失败自动跳过)
EQUITY_DEXES = ["xyz", "cash", "flx", "km", "vntl"]
INDEX_NAMES = {"SP500", "XYZ100", "US500", "USTECH", "USA500", "USA100", "MAG7", "INFOTECH"}
PRIVATE_NAMES = {"SPACEX", "OPENAI", "ANTHROPIC"}
COMMODITY_NAMES = {"CL", "SILVER", "BRENTOIL", "WTI", "GOLD", "GAS", "OIL", "WHEAT", "USOIL",
                   "COPPER", "NATGAS", "PLATINUM"}
HOURS_PER_YEAR = 24 * 365            # HL 资金费每小时一次 → 年化倍数


def post(body: dict, timeout: int = 20):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "stock-analysis-intel/0.1"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# ----------------------------- 主 DEX:持仓面/拥挤 -----------------------------

def crypto_positioning(prev: dict | None) -> dict:
    meta, ctxs = post({"type": "metaAndAssetCtxs"})
    rows = []
    for u, c in zip(meta["universe"], ctxs):
        mark = f(c.get("markPx"))
        oi_usd = f(c.get("openInterest")) * mark
        rows.append({
            "coin": u["name"], "funding_1h": f(c.get("funding")),
            "funding_apr": f(c.get("funding")) * HOURS_PER_YEAR,
            "oi_usd": oi_usd, "premium": f(c.get("premium")),
            "mark": mark, "prev_day": f(c.get("prevDayPx")),
            "vol24h_usd": f(c.get("dayNtlVlm")),
        })
    rows.sort(key=lambda r: -r["vol24h_usd"])
    liquid = [r for r in rows if r["vol24h_usd"] > 5e6]      # 只统计有流动性的
    pos_share = sum(1 for r in liquid if r["funding_1h"] > 0) / max(1, len(liquid))
    total_oi = sum(r["oi_usd"] for r in liquid)
    prev_oi = (prev or {}).get("crypto", {}).get("total_oi_usd")
    oi_chg = (total_oi / prev_oi - 1.0) if prev_oi else None
    extremes = sorted(liquid, key=lambda r: -abs(r["funding_apr"]))[:5]
    btc = next((r for r in rows if r["coin"] == "BTC"), None)
    eth = next((r for r in rows if r["coin"] == "ETH"), None)

    def brief(r):
        return {"coin": r["coin"], "funding_apr": round(r["funding_apr"], 4),
                "oi_usd": round(r["oi_usd"]), "premium": round(r["premium"], 5),
                "chg24h": round(r["mark"] / r["prev_day"] - 1, 4) if r["prev_day"] else None,
                "vol24h_usd": round(r["vol24h_usd"])}
    return {
        "n_perps": len(rows), "n_liquid": len(liquid),
        "btc": brief(btc) if btc else None, "eth": brief(eth) if eth else None,
        "pct_positive_funding": round(pos_share, 3),
        "total_oi_usd": round(total_oi),
        "oi_change_since_last": round(oi_chg, 4) if oi_chg is not None else None,
        "funding_extremes": [brief(r) for r in extremes],
        # 拥挤启发式(§7.2):资金费一边倒 + OI 快速膨胀 → 持仓拥挤,尾部风险升
        "crowding_flag": bool(abs(pos_share - 0.5) > 0.35 or (oi_chg is not None and abs(oi_chg) > 0.15)),
    }


# ----------------------------- 跨所资金费错位 -----------------------------

def venue_dislocations(threshold_apr: float = 0.10) -> dict:
    pf = post({"type": "predictedFundings"})
    out = []
    for coin, venues in pf:
        d = {}
        for vname, vdata in venues:
            if isinstance(vdata, dict) and vdata.get("fundingRate") is not None:
                # 不同所结算周期不同,统一年化:HL 1h、Binance/Bybit 8h
                hours = 1.0 if vname == "HlPerp" else 8.0
                d[vname] = f(vdata["fundingRate"]) * (24 / hours) * 365
        if "HlPerp" in d and "BinPerp" in d:
            spread = d["HlPerp"] - d["BinPerp"]
            if abs(spread) > threshold_apr:
                out.append({"coin": coin, "hl_apr": round(d["HlPerp"], 4),
                            "binance_apr": round(d["BinPerp"], 4), "spread_apr": round(spread, 4)})
    out.sort(key=lambda r: -abs(r["spread_apr"]))
    return {"n_compared": len(pf), "n_dislocated": len(out), "threshold_apr": threshold_apr,
            "top": out[:8]}


# ----------------------------- HIP-3:24/7 合成美股/指数永续 -----------------------------

def classify(name: str) -> str:
    if name in INDEX_NAMES:
        return "index"
    if name in PRIVATE_NAMES:
        return "private"
    if name in COMMODITY_NAMES:
        return "commodity"
    return "stock"


def equity_perps() -> dict:
    assets = []
    dex_ok = []
    for dex in EQUITY_DEXES:
        try:
            meta, ctxs = post({"type": "metaAndAssetCtxs", "dex": dex})
        except Exception:  # noqa: BLE001  builder DEX 可能随时下线
            continue
        dex_ok.append(dex)
        for u, c in zip(meta["universe"], ctxs):
            raw = u["name"]
            name = raw.split(":", 1)[-1]
            mark, prevd = f(c.get("markPx")), f(c.get("prevDayPx"))
            vol = f(c.get("dayNtlVlm"))
            if vol < 1e4 or mark <= 0:
                continue
            assets.append({
                "symbol": name, "dex": dex, "kind": classify(name),
                "mark": mark, "chg24h": round(mark / prevd - 1, 4) if prevd else None,
                "vol24h_usd": round(vol), "funding_apr": round(f(c.get("funding")) * HOURS_PER_YEAR, 4),
            })
    # 同名取成交额最大的一个(xyz 与 cash 都有 NVDA 之类)
    best: dict[str, dict] = {}
    for a in assets:
        k = a["symbol"]
        if k not in best or a["vol24h_usd"] > best[k]["vol24h_usd"]:
            best[k] = a
    rows = sorted(best.values(), key=lambda r: -r["vol24h_usd"])
    by_kind: dict[str, list] = {"index": [], "stock": [], "commodity": [], "private": []}
    for r in rows:
        by_kind[r["kind"]].append(r)
    return {
        "dexes_alive": dex_ok, "n_assets": len(rows),
        "indices": by_kind["index"][:6],
        "stocks": by_kind["stock"][:10],
        "commodities": by_kind["commodity"][:6],
        "private": by_kind["private"][:5],
        "note": "HIP-3 builder 永续,24/7 交易;价格为永续 mark(含资金费/溢价,非证券交易所成交价),仅作盘后参考。",
    }


# ----------------------------- 汇总/发布 -----------------------------

def build_state() -> dict:
    prev = fl.load_json(STATE_PATH)
    state = {"updated_at": fl.now_iso(), "source": "hyperliquid api.hyperliquid.xyz/info"}
    errs = []
    for key, fn in (("crypto", lambda: crypto_positioning(prev)),
                    ("venues", venue_dislocations),
                    ("equity_perps", equity_perps)):
        try:
            state[key] = fn()
        except Exception as e:  # noqa: BLE001
            errs.append(f"{key}: {type(e).__name__} {e}")
            state[key] = (prev or {}).get(key)               # 失败回退上次快照
    state["errors"] = errs
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="同时发布 feed 报告(alerts+contribution)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    state = build_state()
    fl.save_json(STATE_PATH, state)
    c, eq, ven = state.get("crypto") or {}, state.get("equity_perps") or {}, state.get("venues") or {}
    if not args.quiet:
        btc = c.get("btc") or {}
        print(f"[hl] 永续 {c.get('n_perps')}(流动 {c.get('n_liquid')}) | BTC funding {btc.get('funding_apr', 0)*100:.1f}%APR "
              f"OI ${btc.get('oi_usd', 0)/1e9:.2f}B | 多头资金费占比 {c.get('pct_positive_funding')} "
              f"| 拥挤 {c.get('crowding_flag')}")
        print(f"[hl] 跨所错位 {ven.get('n_dislocated')}/{ven.get('n_compared')}(>{ven.get('threshold_apr')}APR)")
        print(f"[hl] HIP-3 资产 {eq.get('n_assets')} @ {eq.get('dexes_alive')} | "
              f"指数 {[x['symbol'] for x in eq.get('indices', [])][:3]} | 私有 {[x['symbol'] for x in eq.get('private', [])]}")
        if state["errors"]:
            print("[hl] 子项失败:", state["errors"])

    if args.publish:
        alerts = []
        if c.get("crowding_flag"):
            alerts.append({"level": "warning", "code": "crypto-crowding",
                           "message": f"加密持仓面拥挤:多头资金费占比 {c.get('pct_positive_funding')},"
                                      f"OI 变化 {c.get('oi_change_since_last')}(§7.2 尾部风险信号,先于人群减杠杆 R7)。",
                           "tickers": []})
        for x in (c.get("funding_extremes") or [])[:2]:
            if abs(x.get("funding_apr", 0)) > 0.5:
                alerts.append({"level": "info", "code": "funding-extreme",
                               "message": f"{x['coin']} 资金费年化 {x['funding_apr']*100:.0f}%(OI ${x['oi_usd']/1e6:.0f}M)"
                                          f"——挤压/单边持仓信号。", "tickers": [x["coin"]]})
        sp = next((i for i in (eq.get("indices") or []) if i["symbol"] in ("SP500", "US500", "USA500")), None)
        if sp and sp.get("chg24h") is not None:
            alerts.append({"level": "info", "code": "afterhours-proxy",
                           "message": f"24/7 美股代理:SP500 永续 24h {sp['chg24h']*100:+.2f}% "
                                      f"(mark {sp['mark']},${sp['vol24h_usd']/1e6:.0f}M/日)——盘后/周末缺口参考。",
                           "tickers": []})
        report = {
            "schema_version": "1.0",
            "id": f"hl-monitor-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "routine",
            "produced_at": fl.now_iso(),
            "asof_data": fl.now_iso()[:10],     # 实时快照:asof=快照时刻(真实)
            "producer": {"name": "hyperliquid-monitor", "agent_role": "crowding-monitor",
                         "run_url": os.environ.get("GITHUB_RUN_URL", "")},
            # 注意:不带 market_state —— 否则 write_report_files 会用两个字段覆盖
            # 引擎的完整 market/state.json(连贯性);加密持仓面在 feed/crypto/state.json。
            "alerts": alerts,
            "contribution": {"type": "regime_update",
                             "summary": f"HL 衍生品情报:{c.get('n_liquid')} 流动永续持仓面,"
                                        f"跨所错位 {ven.get('n_dislocated')},HIP-3 24/7 资产 {eq.get('n_assets')}。"},
            "notes": "数据源 Hyperliquid 公开 info 接口;HIP-3 永续价为 mark 价,仅作参考,非证券报价。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("[hl] feed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
