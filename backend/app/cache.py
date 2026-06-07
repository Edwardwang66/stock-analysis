"""轻量 SQLite 缓存(标准库 sqlite3,无额外依赖)。

用于缓存行情/K线/搜索结果,降低外部 API 调用、加快二次加载。
Render 等平台文件系统是临时的,缓存重启即失效 —— 对"缓存"用途无妨。
失败时自动回退到进程内字典。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any, Optional

_DB_PATH = os.environ.get("CACHE_DB", "/tmp/stock_cache.db")
_lock = threading.Lock()
_mem: dict[str, tuple[float, str]] = {}
_conn: Optional[sqlite3.Connection] = None

try:
    _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    _conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, expires_at REAL)")
    _conn.commit()
except Exception:  # noqa: BLE001 — 文件系统不可写时回退内存
    _conn = None


def get_json(key: str) -> Optional[Any]:
    now = time.time()
    with _lock:
        if _conn is not None:
            row = _conn.execute("SELECT value, expires_at FROM cache WHERE key=?", (key,)).fetchone()
            if row and row[1] > now:
                return json.loads(row[0])
            return None
        item = _mem.get(key)
        if item and item[0] > now:
            return json.loads(item[1])
        return None


def set_json(key: str, obj: Any, ttl: float) -> None:
    exp = time.time() + ttl
    payload = json.dumps(obj)
    with _lock:
        if _conn is not None:
            _conn.execute("INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)", (key, payload, exp))
            _conn.commit()
        else:
            _mem[key] = (exp, payload)


def stats() -> dict:
    with _lock:
        if _conn is not None:
            n = _conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            return {"backend": "sqlite", "path": _DB_PATH, "entries": n}
        return {"backend": "memory", "entries": len(_mem)}
