#!/usr/bin/env python3
"""Build the 7-day intraday event heat leaderboard from Winter's Postgres.

Usage:
  python scripts/winter_pg/event_heat.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path.home() / ".config/stock-analysis/openclaw.env"
OUT = ROOT / "feed" / "signals" / "event-heat.json"
WINDOW_DAYS = 7


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_local_env()
    dsn = os.environ.get("WINTER_PG_DSN")
    if not dsn:
        print("缺 WINTER_PG_DSN", file=sys.stderr)
        return 2

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                  symbol,
                  COUNT(*) FILTER (WHERE type IN ('move', '异动'))::int AS moves,
                  COUNT(*) FILTER (WHERE type IN ('new_high', '新高'))::int AS highs,
                  COUNT(*) FILTER (WHERE type IN ('new_low', '新低'))::int AS lows,
                  COUNT(*)::int AS total
                FROM intraday_events
                WHERE at >= NOW() - (%s || ' days')::interval
                GROUP BY symbol
                ORDER BY total DESC, moves DESC, highs DESC, lows DESC, symbol ASC
                LIMIT 20
                """,
                (WINDOW_DAYS,),
            )
            items = [dict(r) for r in cur.fetchall()]

    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "winter local Postgres intraday_events",
        "window_days": WINDOW_DAYS,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"event-heat: {len(items)} symbols -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
