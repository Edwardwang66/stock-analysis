#!/usr/bin/env python3
"""盘中机器报告(5 分钟节拍,确定性计算,非 LLM)。

覆盖池 = 云端自选池(含 SA LP)∪ 当日 screener ≥80 全名单。
每轮:批量拉实时报价 → 与上一轮快照对比 → 产出:
  - snapshot: 每只 {price, pct, high, low}
  - events:   5 分钟异动(|Δ|≥0.8%)、当日新高/新低、放量提示
  - summary:  池内涨跌家数/中位涨跌/最强最弱
写入 feed/intraday/latest.json。由 intraday-report.yml 提交到 live 分支
(main 历史不被 78 次/日的心跳 commit 污染)。LLM 深读由 OpenClaw 按 events 触发。
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
OUT = ROOT / "feed" / "intraday" / "latest.json"
MOVE_THRESHOLD = 0.8   # 两轮之间 |Δ%| ≥ 0.8 记为异动事件
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-intraday/0.1)"}


def jload(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default


def yahoo_code(symbol: str) -> str:
    market, code = symbol.split(":", 1)
    if market in ("US", "IDX"):
        return code
    if market == "HK":
        return f"{code.zfill(4)}.HK"
    if market == "CN":
        return f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
    if market == "JP":
        return f"{code}.T"
    if market == "KR":
        return f"{code}.KS"
    if market == "DE":
        return f"{code}.DE"
    if market == "GB":
        return f"{code}.L"
    return code


def quote(symbol: str):
    try:
        market, code = symbol.split(":", 1)
        if market == "CRYPTO":
            u = f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={code}"
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=12) as r:
                d = json.loads(r.read().decode())
            return {"price": float(d["lastPrice"]), "pct": float(d["priceChangePercent"]),
                    "high": float(d["highPrice"]), "low": float(d["lowPrice"])}
        u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             f"{urllib.parse.quote(yahoo_code(symbol))}?range=1d&interval=1d")
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=12) as r:
            m = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
        price = m.get("regularMarketPrice")
        prev = m.get("regularMarketPreviousClose") or m.get("chartPreviousClose") or m.get("previousClose")
        if price is None:
            return None
        return {
            "price": price,
            "pct": round((price - prev) / prev * 100, 2) if prev else None,
            "high": m.get("regularMarketDayHigh"), "low": m.get("regularMarketDayLow"),
        }
    except Exception as e:  # noqa: BLE001
        print(f"  ! {symbol}: {e}", file=sys.stderr)
        return None


def main() -> int:
    wl = jload(ROOT / "feed" / "watchlist.json", {})
    pool = list(dict.fromkeys(
        (wl.get("symbols") or [])
        + [f"US:{x['symbol']}" for x in (jload(ROOT / "feed" / "screener" / "latest.json", {}) or {}).get("items", [])]
    ))
    prev_doc = jload(OUT, {})
    prev_snap = prev_doc.get("snapshot", {})

    snap, events = {}, []
    for s in pool:
        q = quote(s)
        time.sleep(0.25)
        if not q:
            continue
        snap[s] = q
        p = prev_snap.get(s)
        if p and p.get("price") and q["price"]:
            d5 = (q["price"] / p["price"] - 1) * 100
            if abs(d5) >= MOVE_THRESHOLD:
                events.append({"symbol": s, "type": "异动", "detail": f"5分钟 {d5:+.2f}%", "price": q["price"]})
        if p and q.get("high") and p.get("high") and q["high"] > p["high"]:
            events.append({"symbol": s, "type": "新高", "detail": f"刷新当日高点 {q['high']}", "price": q["price"]})
        if p and q.get("low") and p.get("low") and q["low"] < p["low"]:
            events.append({"symbol": s, "type": "新低", "detail": f"刷新当日低点 {q['low']}", "price": q["price"]})

    rows = [(s, v["pct"]) for s, v in snap.items() if v.get("pct") is not None]
    rows.sort(key=lambda x: x[1], reverse=True)
    ups = sum(1 for _, p in rows if p > 0)
    doc = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pool_size": len(pool), "quoted": len(snap),
        "summary": {
            "up": ups, "down": sum(1 for _, p in rows if p < 0),
            "median_pct": rows[len(rows) // 2][1] if rows else None,
            "top": [{"symbol": s, "pct": p} for s, p in rows[:5]],
            "bottom": [{"symbol": s, "pct": p} for s, p in rows[-5:]],
        },
        "events": events[:50],
        "snapshot": snap,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"intraday: {len(snap)}/{len(pool)} 报价 · {len(events)} 事件")
    return 0 if snap else 1


if __name__ == "__main__":
    raise SystemExit(main())
