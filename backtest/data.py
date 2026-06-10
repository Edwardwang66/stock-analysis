"""历史日线数据获取与本地缓存(Yahoo Finance chart 端点)。

仅依赖标准库 + 已缓存 CSV;下载用 urllib,避免额外依赖。
缓存为每只标的一个 CSV:data_cache/<TICKER>.csv,列 ts,open,high,low,close,volume。

⚠️ Yahoo 非官方接口、仅个人研究用途,商用须换授权源(见 docs/compliance.md)。
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data_cache")
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-backtest/0.1)"}


def _yahoo_symbol(ticker: str) -> str:
    # Yahoo 用 '-' 表示 BRK.B -> BRK-B(我们的 universe 已做替换)
    return ticker


def _cache_path(ticker: str) -> str:
    return os.path.join(CACHE, f"{ticker}.csv")


def _fetch_rows(url: str) -> list[tuple]:
    """请求 Yahoo chart 端点,返回 [(ts,o,h,l,c,adj,v), ...](过滤空 bar)。"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
    res = data["chart"]["result"][0]
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    adj = None
    if "adjclose" in res["indicators"]:
        adj = res["indicators"]["adjclose"][0].get("adjclose")
    rows = []
    for i, t in enumerate(ts):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        ac = adj[i] if (adj and adj[i] is not None) else c
        v = (q.get("volume") or [0])[i] or 0
        rows.append((int(t), o, h, l, c, ac, v))
    return rows


def fetch_one(ticker: str, range_: str = "10y", interval: str = "1d",
              retries: int = 3, force: bool = False, max_age_hours: float = 12.0) -> int:
    """下载单只标的并写缓存,返回 bar 数;失败返回 0。

    max_age_hours: 缓存文件超过此时长视为陈旧,自动重新下载(修复 CI 恢复昨日缓存后
    引擎一直跑在旧数据上的问题;设 0/负值 = 永不过期,沿用旧行为)。
    """
    path = _cache_path(ticker)
    if not force and os.path.exists(path) and os.path.getsize(path) > 100:
        fresh = (max_age_hours <= 0
                 or (time.time() - os.path.getmtime(path)) < max_age_hours * 3600)
        if fresh:
            with open(path) as f:
                return sum(1 for _ in f) - 1
    url = f"{BASE}{_yahoo_symbol(ticker)}?interval={interval}&range={range_}"
    last_err = None
    for attempt in range(retries):
        try:
            rows = _fetch_rows(url)
            if not rows:
                return 0
            # 实效性补丁:Yahoo 长区间(10y 等)接口常比短区间滞后 1 个交易日,
            # 用 range=5d 的尾部合并补齐(审计 2026-06-10 发现)。
            if range_ not in ("1d", "5d") and interval == "1d":
                for host in (BASE, BASE.replace("query1", "query2")):
                    try:
                        tail = _fetch_rows(f"{host}{_yahoo_symbol(ticker)}?interval=1d&range=5d")
                        have = {r0[0] for r0 in rows}
                        new = [r0 for r0 in tail if r0[0] not in have]
                        if new:
                            rows += new
                            rows.sort(key=lambda r0: r0[0])
                            break          # 拿到更新的尾部即停(代理节点间数据可能不一致)
                    except Exception:  # noqa: BLE001  尾部补丁失败不影响主数据
                        pass
            os.makedirs(CACHE, exist_ok=True)
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["ts", "open", "high", "low", "close", "adjclose", "volume"])
                w.writerows(rows)
            return len(rows)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    print(f"  ! {ticker} 下载失败: {last_err}")
    return 0


def fetch_universe(tickers: list[str], range_: str = "10y", workers: int = 8,
                   force: bool = False) -> dict[str, int]:
    """并发下载整组标的;返回 {ticker: bar数}。"""
    out: dict[str, int] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one, t, range_, "1d", 3, force): t for t in tickers}
        for fut in as_completed(futs):
            t = futs[fut]
            out[t] = fut.result()
            done += 1
            if done % 25 == 0:
                ok = sum(1 for v in out.values() if v > 0)
                print(f"  进度 {done}/{len(tickers)}  成功 {ok}")
    return out


def load(ticker: str) -> dict[str, list]:
    """读取缓存为列式 dict:ts/open/high/low/close/adjclose/volume(list)。"""
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return {}
    cols: dict[str, list] = {k: [] for k in
                             ["ts", "open", "high", "low", "close", "adjclose", "volume"]}
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            cols["ts"].append(int(row["ts"]))
            for k in ["open", "high", "low", "close", "adjclose", "volume"]:
                cols[k].append(float(row[k]))
    return cols


if __name__ == "__main__":
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    tickers = uni["universe"] + ["SPY", "QQQ"]  # 加基准
    print(f"下载 {len(tickers)} 只标的 10 年日线 ...")
    t0 = time.time()
    res = fetch_universe(tickers, range_="10y", workers=8)
    ok = sum(1 for v in res.values() if v > 0)
    print(f"完成:{ok}/{len(tickers)} 成功,用时 {time.time()-t0:.0f}s")
