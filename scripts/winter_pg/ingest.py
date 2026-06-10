#!/usr/bin/env python3
"""把 repo 的 feed 产物增量入 Winter 本地 Postgres(每轮循环/每日投递后调用)。

用法:
  pip install psycopg2-binary
  export WINTER_PG_DSN=postgresql://winter:***@localhost:5432/stocks
  python scripts/winter_pg/ingest.py            # 入 当日快照/事件/分数/picks/notes/13F
  python scripts/winter_pg/ingest.py --init     # 首次建表(执行 schema.sql)

幂等:全部 UPSERT;重复跑无副作用。bars 全量K线由你的循环另行按需写入(可选)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path.home() / ".config/stock-analysis/openclaw.env"


def load_local_env() -> None:
    """Load local Winter config without requiring callers to source it first."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def jload(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    args = ap.parse_args()
    load_local_env()
    dsn = os.environ.get("WINTER_PG_DSN")
    if not dsn:
        print("缺 WINTER_PG_DSN", file=sys.stderr)
        return 2
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    if args.init:
        cur.execute((ROOT / "scripts/winter_pg/schema.sql").read_text())
        conn.commit()
        print("schema OK")

    n = {"snap": 0, "ev": 0, "score": 0, "pick": 0, "note": 0, "fund": 0}

    intraday_path = os.environ.get("WINTER_INTRADAY_LATEST") or ROOT / "feed/intraday/latest.json"
    intr = jload(intraday_path, None)
    if intr and intr.get("at"):
        at = intr["at"]
        rows = [(at, s, v.get("price"), v.get("pct"), v.get("high"), v.get("low"))
                for s, v in (intr.get("snapshot") or {}).items()]
        psycopg2.extras.execute_values(cur,
            "INSERT INTO intraday_snapshots (at,symbol,price,pct,high,low) VALUES %s ON CONFLICT DO NOTHING", rows)
        n["snap"] = len(rows)
        ev = [(at, e["symbol"], e["type"], e.get("detail"), e.get("price")) for e in intr.get("events") or []]
        if ev:
            psycopg2.extras.execute_values(cur,
                "INSERT INTO intraday_events (at,symbol,type,detail,price) VALUES %s ON CONFLICT DO NOTHING", ev)
        n["ev"] = len(ev)

    sc = jload(ROOT / "feed/screener/scores.json", None)
    if sc and sc.get("date"):
        sectors = sc.get("sectors") or {}
        rows = [(sc["date"], f"US:{k}", v, sectors.get(k)) for k, v in (sc.get("scores") or {}).items()]
        psycopg2.extras.execute_values(cur,
            "INSERT INTO scores (date,symbol,score,sector) VALUES %s "
            "ON CONFLICT (date,symbol) DO UPDATE SET score=EXCLUDED.score, sector=EXCLUDED.sector", rows)
        n["score"] = len(rows)

    for day in jload(ROOT / "feed/screener/history.json", []):
        rows = [(day["date"], it["symbol"], it.get("score"), it.get("pick_price")) for it in day.get("items", [])]
        if rows:
            psycopg2.extras.execute_values(cur,
                "INSERT INTO picks (date,symbol,score,pick_price) VALUES %s ON CONFLICT DO NOTHING", rows)
            n["pick"] += len(rows)

    notes_dir = ROOT / "feed/stock-notes"
    for f in notes_dir.glob("*.json"):
        if f.name == "index.json":
            continue
        d = jload(f, None)
        if not d or not d.get("symbol") or not d.get("date"):
            continue
        cur.execute(
            "INSERT INTO notes (symbol,date,stance,view,payload) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (symbol,date) DO UPDATE SET stance=EXCLUDED.stance, view=EXCLUDED.view, payload=EXCLUDED.payload",
            (d["symbol"], d["date"], d.get("stance"), d.get("view"), json.dumps(d, ensure_ascii=False)))
        n["note"] += 1

    fund = jload(ROOT / "feed/funds/situational-awareness.json", None)
    if fund and fund.get("asof"):
        rows = [(fund["asof"], p.get("ticker"), p.get("name"), p.get("type"), p.get("value"), p.get("shares"))
                for p in fund.get("positions", [])]
        psycopg2.extras.execute_values(cur,
            "INSERT INTO fund_positions (asof,ticker,name,type,value,shares) VALUES %s ON CONFLICT DO NOTHING", rows)
        n["fund"] = len(rows)

    conn.commit()
    cur.close(); conn.close()
    print("ingest:", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
