"""K线持久存储(SQLite):增量入库,历史不再重复外拉。

设计:
- bars(symbol, interval, ts) 主键去重,UPSERT 合并;
- bars_meta 记录每个 (symbol, interval) 已完整拉取过的最大跨度 full_days
  和最近同步时间 last_sync、来源 source;
- 请求命中已覆盖范围 → 只从外部源拉一小段"尾巴"补最新,其余直接读库;
- 外部源全挂时可降级返回库内旧数据(由 store 层决定);
- 分钟级数据保留 35 天,日线长期保存。

文件路径默认 /tmp(Render 免费实例重启即失,等同冷缓存);
挂了持久磁盘的环境可用 STORE_DB 指到持久路径,历史即长期累积。
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import OHLCV, Bar

_DB_PATH = os.environ.get("STORE_DB", "/tmp/stock_store.db")
_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

# range -> 天数
RANGE_DAYS = {"1d": 1, "5d": 5, "1mo": 31, "3mo": 92, "6mo": 183,
              "1y": 366, "2y": 731, "5y": 1827, "max": 3660}
# 增量补尾时向外部源要的小范围(覆盖节假日/停牌间隙,留足冗余)
TAIL_RANGE = {"1m": "1d", "5m": "1d", "15m": "5d", "30m": "5d", "1h": "5d",
              "1d": "1mo", "1wk": "3mo", "1mo": "1y"}
# 同步新鲜度:窗口内不再外拉
SYNC_TTL = {"1m": 30, "5m": 60, "15m": 90, "30m": 120, "1h": 120,
            "1d": 600, "1wk": 3600, "1mo": 7200}
_INTRADAY = {"1m", "5m", "15m", "30m", "1h"}
_INTRADAY_KEEP_DAYS = 35

try:
    _conn = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA synchronous=NORMAL")
    _conn.execute("PRAGMA busy_timeout=3000")
    _conn.execute(
        """CREATE TABLE IF NOT EXISTS bars (
            symbol TEXT NOT NULL, interval TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, interval, ts))"""
    )
    _conn.execute(
        """CREATE TABLE IF NOT EXISTS bars_meta (
            symbol TEXT NOT NULL, interval TEXT NOT NULL,
            last_sync REAL DEFAULT 0, full_days INTEGER DEFAULT 0, source TEXT,
            PRIMARY KEY (symbol, interval))"""
    )
except Exception:  # noqa: BLE001 — 不可写则禁用持久层(store 会直接走外部源)
    _conn = None


def enabled() -> bool:
    return _conn is not None


def get_meta(symbol: str, interval: str) -> Optional[dict]:
    if _conn is None:
        return None
    with _lock:
        row = _conn.execute(
            "SELECT last_sync, full_days, source FROM bars_meta WHERE symbol=? AND interval=?",
            (symbol, interval),
        ).fetchone()
    if not row:
        return None
    return {"last_sync": row[0], "full_days": row[1], "source": row[2] or ""}


def _norm_ts(interval: str, ts: datetime) -> int:
    """日/周/月线时间戳归一到 UTC 零点(周→周一、月→1号)。

    不同源对同一交易日的时间戳不一致(Yahoo=开盘时刻、腾讯=日期),
    不归一会在源切换时产生重复 K 线。
    """
    if interval not in ("1d", "1wk", "1mo"):
        return int(ts.timestamp())
    d = ts.astimezone(timezone.utc)
    if interval == "1wk":
        d = d - timedelta(days=d.weekday())
    elif interval == "1mo":
        d = d.replace(day=1)
    return int(d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def upsert_bars(symbol: str, interval: str, bars: list[Bar], source: str,
                full_days: int | None = None) -> int:
    """合并写入;full_days 给定时抬高已覆盖跨度水位。返回写入行数。"""
    if _conn is None:
        return 0
    rows = [
        (symbol, interval, _norm_ts(interval, b.ts), b.open, b.high, b.low, b.close, b.volume)
        for b in bars
    ]
    with _lock:
        if rows:
            _conn.executemany(
                "INSERT OR REPLACE INTO bars (symbol, interval, ts, open, high, low, close, volume)"
                " VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
        _conn.execute(
            """INSERT INTO bars_meta (symbol, interval, last_sync, full_days, source)
               VALUES (?,?,?,?,?)
               ON CONFLICT(symbol, interval) DO UPDATE SET
                 last_sync=excluded.last_sync,
                 full_days=MAX(bars_meta.full_days, excluded.full_days),
                 source=excluded.source""",
            (symbol, interval, time.time(), int(full_days or 0), source),
        )
    return len(rows)


def load_bars(symbol: str, interval: str, days: int) -> list[Bar]:
    if _conn is None:
        return []
    since = int(time.time()) - days * 86400
    with _lock:
        rows = _conn.execute(
            "SELECT ts, open, high, low, close, volume FROM bars"
            " WHERE symbol=? AND interval=? AND ts>=? ORDER BY ts ASC",
            (symbol, interval, since),
        ).fetchall()
    return [
        Bar(ts=datetime.fromtimestamp(r[0], tz=timezone.utc),
            open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5] or 0.0)
        for r in rows
    ]


def load_ohlcv(symbol: str, interval: str, range_: str, source: str) -> OHLCV:
    days = RANGE_DAYS.get(range_, 366)
    return OHLCV(symbol=symbol, interval=interval,
                 bars=load_bars(symbol, interval, days), source=source)


def purge() -> None:
    """分钟级数据只留近 35 天,控制库体积。"""
    if _conn is None:
        return
    cutoff = int(time.time()) - _INTRADAY_KEEP_DAYS * 86400
    with _lock:
        for iv in _INTRADAY:
            _conn.execute("DELETE FROM bars WHERE interval=? AND ts<?", (iv, cutoff))


def stats() -> dict:
    if _conn is None:
        return {"enabled": False}
    with _lock:
        n = _conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0]
        m = _conn.execute("SELECT COUNT(*) FROM bars_meta").fetchone()[0]
    return {"enabled": True, "path": _DB_PATH, "bars": n, "series": m}
