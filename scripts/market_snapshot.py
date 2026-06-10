#!/usr/bin/env python3
"""每日市场快照 → feed/market/history.json(追加式,保留 400 天)。

抓取(全部免费、服务端直连无 CORS 问题):
  - 指数收盘与涨跌:Yahoo chart meta(标普/纳指/道指/上证/恒指/日经/KOSPI/DAX)
  - 加密恐惧贪婪指数:alternative.me
  - BTC 24h:Binance data-api

由 .github/workflows/market-snapshot.yml 定时运行;前端用该序列画历史曲线。
任何单项失败不影响其他项(字段缺失即为 null)。
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
OUT = ROOT / "feed" / "market" / "history.json"
KEEP_DAYS = 400

INDICES = {
    "^GSPC": "标普500", "^IXIC": "纳斯达克", "^DJI": "道琼斯",
    "000001.SS": "上证指数", "^HSI": "恒生指数",
    "^N225": "日经225", "^KS11": "KOSPI", "^GDAXI": "DAX",
}
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-snapshot/0.1)"}


def fetch_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def index_quote(code: str):
    try:
        j = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(code)}?range=5d&interval=1d")
        m = j["chart"]["result"][0]["meta"]
        price = m.get("regularMarketPrice")
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        pct = ((price - prev) / prev * 100.0) if (price is not None and prev) else None
        return {"close": price, "change_pct": round(pct, 4) if pct is not None else None}
    except Exception as e:  # noqa: BLE001
        print(f"  ! {code}: {e}", file=sys.stderr)
        return {"close": None, "change_pct": None}


def fng():
    try:
        d = fetch_json("https://api.alternative.me/fng/?limit=1")["data"][0]
        return {"value": int(d["value"]), "label": d.get("value_classification")}
    except Exception as e:  # noqa: BLE001
        print(f"  ! FNG: {e}", file=sys.stderr)
        return {"value": None, "label": None}


def btc():
    try:
        d = fetch_json("https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT")
        return {"price": float(d["lastPrice"]), "change_pct_24h": float(d["priceChangePercent"])}
    except Exception as e:  # noqa: BLE001
        print(f"  ! BTC: {e}", file=sys.stderr)
        return {"price": None, "change_pct_24h": None}


def main() -> int:
    now = datetime.now(timezone.utc)
    rec = {
        "date": now.strftime("%Y-%m-%d"),
        "at": now.isoformat(timespec="seconds"),
        "indices": {},
        "fng": fng(),
        "btc": btc(),
    }
    for code in INDICES:
        rec["indices"][code] = index_quote(code)
        time.sleep(0.4)  # 温和限速

    hist = []
    if OUT.exists():
        try:
            hist = json.loads(OUT.read_text())
        except Exception:  # noqa: BLE001
            hist = []
    # 同日覆盖(一天可能跑两次:A股收盘后 + 美股收盘后,后者数据更全)
    hist = [h for h in hist if h.get("date") != rec["date"]]
    hist.append(rec)
    hist = hist[-KEEP_DAYS:]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")) + "\n")

    got = sum(1 for v in rec["indices"].values() if v["close"] is not None)
    print(f"快照完成:{rec['date']} 指数 {got}/{len(INDICES)} · FNG {rec['fng']['value']} · BTC {rec['btc']['price']}")
    # 指数全挂视为失败(让工作流亮红灯),个别缺失放过
    return 0 if got > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
