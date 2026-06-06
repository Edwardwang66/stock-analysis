"""Hyperliquid 永续数据获取与缓存:日线 K + 资金费率(分页)。

API: POST https://api.hyperliquid.xyz/info
  - meta / metaAndAssetCtxs : 币种列表 + 当前 OI/funding/成交量快照
  - candleSnapshot          : 日线 OHLCV(单次上限 ~5000 根)
  - fundingHistory          : 资金费率(每小时一条,单次上限 500 条 -> 需分页)

缓存:crypto_cache/<COIN>_candles.csv 与 <COIN>_funding.csv(已按日聚合)。
funding 每小时一条;按 UTC 日聚合为"当日资金费之和"(≈日 carry)与均值。
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "crypto_cache")
URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json", "User-Agent": "stock-backtest/0.1"}
MS_DAY = 86400_000


def _post(body: dict, retries: int = 4):
    data = json.dumps(body).encode()
    last = None
    for a in range(retries):
        try:
            req = urllib.request.Request(URL, data=data, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (a + 1))
    raise last


def select_universe(top_n: int = 30, min_vol_usd: float = 2e7) -> list[str]:
    """按 24h 名义成交额取流动性最高的 top_n 币(排除稳定币代理)。"""
    meta, ctxs = _post({"type": "metaAndAssetCtxs"})
    names = [c["name"] for c in meta["universe"]]
    rows = []
    for i, n in enumerate(names):
        vol = float(ctxs[i].get("dayNtlVlm", 0) or 0)
        if vol >= min_vol_usd:
            rows.append((n, vol))
    rows.sort(key=lambda x: -x[1])
    return [n for n, _ in rows[:top_n]]


def fetch_candles(coin: str, days: int = 1500, force: bool = False) -> int:
    path = os.path.join(CACHE, f"{coin}_candles.csv")
    if not force and os.path.exists(path) and os.path.getsize(path) > 100:
        with open(path) as f:
            return sum(1 for _ in f) - 1
    end = int(time.time() * 1000)
    start = end - days * MS_DAY
    res = _post({"type": "candleSnapshot",
                 "req": {"coin": coin, "interval": "1d", "startTime": start, "endTime": end}})
    if not res:
        return 0
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "vol", "ntrades"])
        for c in res:
            w.writerow([int(c["t"] // 1000), c["o"], c["h"], c["l"], c["c"], c["v"], c["n"]])
    return len(res)


def fetch_funding(coin: str, days: int = 730, force: bool = False) -> int:
    """分页拉取每小时资金费,按 UTC 日聚合(sum=日 carry, mean, count)。"""
    path = os.path.join(CACHE, f"{coin}_funding.csv")
    if not force and os.path.exists(path) and os.path.getsize(path) > 60:
        with open(path) as f:
            return sum(1 for _ in f) - 1
    end = int(time.time() * 1000)
    start = end - days * MS_DAY
    daily: dict[int, list[float]] = {}   # day_epoch -> list of hourly funding
    daily_prem: dict[int, list[float]] = {}
    cursor = start
    guard = 0
    while cursor < end and guard < 250:
        guard += 1
        res = _post({"type": "fundingHistory", "coin": coin,
                     "startTime": cursor, "endTime": end})
        if not res:
            break
        for p in res:
            day = (p["time"] // MS_DAY) * 86400
            daily.setdefault(day, []).append(float(p["fundingRate"]))
            daily_prem.setdefault(day, []).append(float(p.get("premium", 0) or 0))
        last_t = res[-1]["time"]
        if last_t <= cursor:
            break
        cursor = last_t + 1
        time.sleep(0.05)
    if not daily:
        return 0
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "fund_sum", "fund_mean", "prem_mean", "n"])
        for day in sorted(daily):
            fl = daily[day]
            pl = daily_prem[day]
            w.writerow([day, sum(fl), sum(fl) / len(fl), sum(pl) / len(pl), len(fl)])
    return len(daily)


def load_candles(coin: str) -> dict:
    path = os.path.join(CACHE, f"{coin}_candles.csv")
    if not os.path.exists(path):
        return {}
    cols = {k: [] for k in ["ts", "open", "high", "low", "close", "vol", "ntrades"]}
    with open(path) as f:
        for row in csv.DictReader(f):
            cols["ts"].append(int(row["ts"]))
            for k in ["open", "high", "low", "close", "vol", "ntrades"]:
                cols[k].append(float(row[k]))
    return cols


def load_funding(coin: str) -> dict:
    path = os.path.join(CACHE, f"{coin}_funding.csv")
    if not os.path.exists(path):
        return {}
    out = {}  # ts(day) -> (fund_sum, fund_mean, prem_mean)
    with open(path) as f:
        for row in csv.DictReader(f):
            out[int(row["ts"])] = (float(row["fund_sum"]), float(row["fund_mean"]),
                                   float(row["prem_mean"]))
    return out


if __name__ == "__main__":
    uni = select_universe(top_n=30)
    json.dump(uni, open(os.path.join(HERE, "crypto_universe.json"), "w"))
    print(f"universe ({len(uni)}):", uni)
    ok_c = ok_f = 0
    for i, coin in enumerate(uni):
        nc = fetch_candles(coin, days=1500)
        nf = fetch_funding(coin, days=730)
        ok_c += nc > 200
        ok_f += nf > 60
        print(f"  [{i+1}/{len(uni)}] {coin:8} candles={nc:5} funding_days={nf}")
    print(f"完成:candles ok {ok_c}/{len(uni)}, funding ok {ok_f}/{len(uni)}")
