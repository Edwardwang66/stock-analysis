#!/usr/bin/env python3
"""Build the weekly >=80 picks win-rate summary from Winter's local Postgres.

Reads the local `picks` table, marks each historical pick to current Yahoo
prices, and writes feed/screener/winrate.json for the dashboard/digest.

Usage:
  python scripts/winter_pg/winrate.py
  python scripts/winter_pg/winrate.py --if-due   # only run Friday after 20:00 UTC
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path.home() / ".config/stock-analysis/openclaw.env"
OUT = ROOT / "feed" / "screener" / "winrate.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-analysis-winrate/0.1)"}
WINDOWS = {"d1": 1, "d5": 5, "d20": 20}
BANDS = (("80-84", 80, 84), ("85-89", 85, 89), ("90+", 90, 10_000))


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


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


def current_price(symbol: str) -> float | None:
    try:
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(yahoo_code(symbol))}?range=1d&interval=1d"
        )
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
            meta = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        return float(price) if price is not None else None
    except Exception as e:  # noqa: BLE001
        print(f"  ! {symbol}: {e}", file=sys.stderr)
        return None


def band_for(score: int | None) -> str | None:
    if score is None:
        return None
    for name, lo, hi in BANDS:
        if lo <= score <= hi:
            return name
    return None


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "win_rate": None, "avg_ret": None, "best": None, "worst": None}
    rows = sorted(rows, key=lambda r: r["ret"], reverse=True)
    avg = sum(r["ret"] for r in rows) / len(rows)
    return {
        "n": len(rows),
        "win_rate": round(sum(1 for r in rows if r["ret"] > 0) / len(rows), 4),
        "avg_ret": round(avg, 4),
        "best": pick_view(rows[0]),
        "worst": pick_view(rows[-1]),
    }


def pick_view(row: dict) -> dict:
    return {
        "symbol": row["symbol"],
        "date": row["date"].isoformat() if isinstance(row["date"], date) else str(row["date"]),
        "score": row["score"],
        "pick_price": round(row["pick_price"], 4),
        "current_price": round(row["current_price"], 4),
        "ret": round(row["ret"], 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-due", action="store_true", help="run only Friday after 20:00 UTC")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    if args.if_due and not (now.weekday() == 4 and now.hour >= 20):
        print("winrate: not due")
        return 0

    load_local_env()
    dsn = os.environ.get("WINTER_PG_DSN")
    if not dsn:
        print("缺 WINTER_PG_DSN", file=sys.stderr)
        return 2

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT date, symbol, score, pick_price
                FROM picks
                WHERE score >= 80 AND pick_price IS NOT NULL AND pick_price > 0
                ORDER BY date ASC, symbol ASC
                """
            )
            picks = [dict(r) for r in cur.fetchall()]

    symbols = sorted({r["symbol"] for r in picks})
    prices: dict[str, float] = {}
    for sym in symbols:
        p = current_price(sym)
        if p is not None:
            prices[sym] = p
        time.sleep(0.2)

    marked = []
    today = now.date()
    for r in picks:
        price = prices.get(r["symbol"])
        if price is None:
            continue
        pick_date = r["date"]
        age_days = (today - pick_date).days
        ret = price / float(r["pick_price"]) - 1
        marked.append({**r, "age_days": age_days, "current_price": price, "ret": ret})

    windows = {}
    for name, min_age in WINDOWS.items():
        cohort = [r for r in marked if r["age_days"] >= min_age]
        by_band = {}
        for band, _, _ in BANDS:
            by_band[band] = summarize([r for r in cohort if band_for(r["score"]) == band])
        windows[name] = {**summarize(cohort), "by_score_band": by_band}

    doc = {
        "generated_at": now.isoformat(timespec="seconds"),
        "source": "winter local Postgres picks + Yahoo current prices",
        "method": "For each window, includes picks at least that many calendar days old; returns are current_price / pick_price - 1.",
        "picks_total": len(picks),
        "priced": len(marked),
        "windows": windows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"winrate: {len(marked)}/{len(picks)} priced -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
