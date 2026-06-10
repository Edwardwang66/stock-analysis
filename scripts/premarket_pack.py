#!/usr/bin/env python3
"""盘前隔夜要素包(premarket-pack.yml 每个交易日 12:40 UTC 自动生成)。

给 OpenClaw 盘前 report 供数(首跑实测 2026-06-10),免得她自己抓:
  - 美股期货:ES=F(标普)/ NQ=F(纳指)/ YM=F(道指)实时
  - 亚洲收盘:上证 / 恒指 / 日经 / KOSPI;欧洲盘中:DAX / FTSE
  - 隔夜加密:BTC / ETH 24h
  - 昨日美股异动:自选池+screener 中 |当日涨跌| ≥ 3% 的标的(昨收口径)
输出 feed/intraday/overnight.json;/desk 与盘前报告共用。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feed" / "intraday" / "overnight.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-premarket/0.1)"}

FUTURES = {"ES=F": "标普期货", "NQ=F": "纳指期货", "YM=F": "道指期货"}
ASIA = {"000001.SS": "上证指数", "^HSI": "恒生指数", "^N225": "日经225", "^KS11": "KOSPI"}
EUROPE = {"^GDAXI": "德国DAX", "^FTSE": "富时100"}


def yahoo(code: str) -> dict | None:
    try:
        u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             f"{urllib.parse.quote(code)}?range=1d&interval=1d")
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=12) as r:
            m = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
        price = m.get("regularMarketPrice")
        prev = m.get("regularMarketPreviousClose") or m.get("chartPreviousClose")
        if price is None or not prev:
            return None
        return {"price": round(price, 2), "pct": round((price / prev - 1) * 100, 2)}
    except Exception as e:  # noqa: BLE001
        print(f"  ! {code}: {e}", file=sys.stderr)
        return None


def binance(sym: str) -> dict | None:
    try:
        u = f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={sym}"
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=12) as r:
            d = json.loads(r.read().decode())
        return {"price": float(d["lastPrice"]), "pct": float(d["priceChangePercent"])}
    except Exception:  # noqa: BLE001
        return None


def block(codes: dict[str, str]) -> dict:
    out = {}
    for code, name in codes.items():
        q = yahoo(code)
        time.sleep(0.3)
        if q:
            out[code] = {"name": name, **q}
    return out


def main() -> int:
    def jload(p, default):
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            return default

    # 昨日异动(用 5 分钟快照兜底数据源:live latest.json 若新鲜则优先,否则跳过)
    movers = []
    snap = jload(ROOT / "feed" / "intraday" / "latest.json", {})
    for s, v in (snap.get("snapshot") or {}).items():
        if v.get("pct") is not None and abs(v["pct"]) >= 3:
            movers.append({"symbol": s, "pct": v["pct"], "price": v.get("price")})
    movers.sort(key=lambda x: -abs(x["pct"]))

    # 24/7 永续夜盘异动(Hyperliquid equity_perps,|24h|≥4%;盘前重要预警)
    perp_movers = []
    hl = jload(ROOT / "feed" / "crypto" / "state.json", {})
    ep = hl.get("equity_perps") or {}
    for grp in ("stocks", "indices", "private"):
        for x in ep.get(grp) or []:
            c = x.get("chg24h")
            if c is not None and abs(c) >= 0.04:
                perp_movers.append({"symbol": x.get("symbol"), "kind": x.get("kind"),
                                    "mark": x.get("mark"), "chg24h": round(c * 100, 2),
                                    "funding_apr": x.get("funding_apr")})
    perp_movers.sort(key=lambda x: -abs(x["chg24h"]))

    doc = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "perp_movers": perp_movers[:15],
        "futures": block(FUTURES),
        "asia": block(ASIA),
        "europe": block(EUROPE),
        "crypto": {k: v for k, v in (("BTCUSDT", binance("BTCUSDT")), ("ETHUSDT", binance("ETHUSDT"))) if v},
        "yesterday_movers": movers[:20],
        "note": "盘前要素包:期货/亚欧指数/隔夜加密/昨日异动;供 OpenClaw 盘前 report 与 /desk。",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    n = len(doc["futures"]) + len(doc["asia"]) + len(doc["europe"]) + len(doc["crypto"])
    print(f"overnight: {n} 项行情 + {len(movers)} 异动")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
