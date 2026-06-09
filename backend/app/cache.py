"""轻量 SQLite 缓存(标准库 sqlite3,无额外依赖)。

升级点(v2):
- WAL 模式 + synchronous=NORMAL:写入快一个量级,读写不互斥;
- autocommit(isolation_level=None):省去每次 set 的显式 commit;
- 过期数据保留宽限期(STALE_GRACE),支持 stale-while-revalidate:
  get_entry() 可返回 (值, 是否新鲜),上层先回旧数据再后台刷新;
- 周期性清理 + 条目上限,防 /tmp 无限膨胀;
- 失败时自动回退到进程内字典。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any, Optional

_DB_PATH = os.environ.get("CACHE_DB", "/tmp/stock_cache.db")
STALE_GRACE = float(os.environ.get("CACHE_STALE_GRACE", 24 * 3600))  # 过期后仍保留的秒数
_MAX_ENTRIES = int(os.environ.get("CACHE_MAX_ENTRIES", 20000))
_PURGE_EVERY = 200  # 每 N 次写触发一次清理

_lock = threading.Lock()
_mem: dict[str, tuple[float, str]] = {}
_conn: Optional[sqlite3.Connection] = None
_writes = 0
_hits = 0
_misses = 0

try:
    _conn = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA synchronous=NORMAL")
    _conn.execute("PRAGMA busy_timeout=3000")
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, expires_at REAL)"
    )
    _conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_exp ON cache(expires_at)")
except Exception:  # noqa: BLE001 — 文件系统不可写时回退内存
    _conn = None


def get_entry(key: str) -> Optional[tuple[Any, bool]]:
    """返回 (值, 是否新鲜)。过期但在宽限期内 → (值, False);彻底没有 → None。"""
    global _hits, _misses
    now = time.time()
    with _lock:
        if _conn is not None:
            row = _conn.execute(
                "SELECT value, expires_at FROM cache WHERE key=?", (key,)
            ).fetchone()
            if row and row[1] + STALE_GRACE > now:
                _hits += 1
                return json.loads(row[0]), row[1] > now
            _misses += 1
            return None
        item = _mem.get(key)
        if item and item[0] + STALE_GRACE > now:
            _hits += 1
            return json.loads(item[1]), item[0] > now
        _misses += 1
        return None


def get_json(key: str) -> Optional[Any]:
    """仅返回新鲜数据(兼容旧调用方)。"""
    entry = get_entry(key)
    if entry is not None and entry[1]:
        return entry[0]
    return None


def set_json(key: str, obj: Any, ttl: float) -> None:
    global _writes
    exp = time.time() + ttl
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with _lock:
        if _conn is not None:
            _conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, payload, exp),
            )
            _writes += 1
            if _writes % _PURGE_EVERY == 0:
                _purge_locked()
        else:
            _mem[key] = (exp, payload)
            if len(_mem) > _MAX_ENTRIES:
                now = time.time()
                for k in [k for k, v in _mem.items() if v[0] + STALE_GRACE <= now]:
                    _mem.pop(k, None)


def _purge_locked() -> None:
    """清掉宽限期外的死数据;超上限再按最早过期淘汰。须在持锁状态下调用。"""
    if _conn is None:
        return
    now = time.time()
    _conn.execute("DELETE FROM cache WHERE expires_at + ? <= ?", (STALE_GRACE, now))
    n = _conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    if n > _MAX_ENTRIES:
        _conn.execute(
            "DELETE FROM cache WHERE key IN "
            "(SELECT key FROM cache ORDER BY expires_at ASC LIMIT ?)",
            (n - _MAX_ENTRIES,),
        )


def stats() -> dict:
    with _lock:
        total = _hits + _misses
        hit_rate = round(_hits / total, 3) if total else None
        if _conn is not None:
            n = _conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            return {"backend": "sqlite", "path": _DB_PATH, "entries": n, "hit_rate": hit_rate}
        return {"backend": "memory", "entries": len(_mem), "hit_rate": hit_rate}
