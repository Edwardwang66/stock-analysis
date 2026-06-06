"""Binance 长历史数据(经公共镜像 data-api.binance.vision,绕开 api.binance.com 的 451 地理封锁)。

- 现货日线 K:回溯 2017-08(BTC 上市),分页(每次 ≤1000 根)。
- 资金费率:期货 ZIP 数据包(data.binance.vision/data/futures/um/monthly/fundingRate),2019+。
- 币种宇宙:按 24h 名义成交额(quoteVolume)取 top_n USDT 现货对,排除稳定币。

缓存:binance_cache/<SYM>_1d.csv,binance_cache/<SYM>_funding.csv。
⚠️ 宇宙取"当前在交易"的对 -> 仍有幸存者偏差(退市币缺失);已在 README 标注。
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.request
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "binance_cache")
SPOT = "https://data-api.binance.vision/api/v3"
DUMP = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; bt/0.1)"}
START_2017 = 1502928000000   # 2017-08-17
STABLES = {"USDCUSDT", "TUSDUSDT", "BUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT",
           "EURUSDT", "GBPUSDT", "AEURUSDT", "USD1USDT", "EURIUSDT"}


def _get(url, timeout=25, retries=4):
    last = None
    for a in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(1.5 * (a + 1))
    raise last


def select_universe(top_n=70):
    data = json.loads(_get(f"{SPOT}/ticker/24hr"))
    rows = [(d["symbol"], float(d.get("quoteVolume", 0)))
            for d in data if d["symbol"].endswith("USDT") and d["symbol"] not in STABLES]
    rows.sort(key=lambda x: -x[1])
    return [s for s, _ in rows[:top_n]]


def fetch_klines(symbol, start=START_2017, force=False):
    path = os.path.join(CACHE, f"{symbol}_1d.csv")
    if not force and os.path.exists(path) and os.path.getsize(path) > 100:
        with open(path) as f:
            return sum(1 for _ in f) - 1
    os.makedirs(CACHE, exist_ok=True)
    rows = []
    cur = start
    now = int(time.time() * 1000)
    guard = 0
    while cur < now and guard < 30:
        guard += 1
        url = f"{SPOT}/klines?symbol={symbol}&interval=1d&startTime={cur}&limit=1000"
        kl = json.loads(_get(url))
        if not kl:
            break
        for k in kl:
            # [openTime,o,h,l,c,vol,closeTime,quoteVol,...]
            rows.append((int(k[0] // 1000), k[1], k[2], k[3], k[4], k[5], k[7]))
        last = kl[-1][0]
        if last <= cur:
            break
        cur = last + 86400000
        if len(kl) < 1000:
            break
        time.sleep(0.03)
    if not rows:
        return 0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "open", "high", "low", "close", "vol", "quote_vol"])
        w.writerows(rows)
    return len(rows)


def fetch_funding(symbol, start_year=2019, force=False):
    """下载期货资金费月度 ZIP,按 UTC 日聚合(sum=日 carry, mean)。"""
    path = os.path.join(CACHE, f"{symbol}_funding.csv")
    if not force and os.path.exists(path) and os.path.getsize(path) > 60:
        with open(path) as f:
            return sum(1 for _ in f) - 1
    daily = {}
    now = datetime.now(timezone.utc)
    for yr in range(start_year, now.year + 1):
        for mo in range(1, 13):
            if yr == now.year and mo > now.month:
                break
            url = f"{DUMP}/{symbol}/{symbol}-fundingRate-{yr}-{mo:02d}.zip"
            try:
                raw = _get(url, timeout=20, retries=2)
            except Exception:
                continue
            try:
                zf = zipfile.ZipFile(io.BytesIO(raw))
                with zf.open(zf.namelist()[0]) as fh:
                    for line in io.TextIOWrapper(fh, "utf-8"):
                        parts = line.strip().split(",")
                        if len(parts) < 3 or not parts[0].isdigit():
                            continue
                        t = int(parts[0]); rate = float(parts[2])
                        day = (t // 86400000) * 86400
                        daily.setdefault(day, []).append(rate)
            except Exception:
                continue
    if not daily:
        return 0
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "fund_sum", "fund_mean", "n"])
        for day in sorted(daily):
            fl = daily[day]
            w.writerow([day, sum(fl), sum(fl) / len(fl), len(fl)])
    return len(daily)


def load(symbol, kind="1d"):
    path = os.path.join(CACHE, f"{symbol}_{kind}.csv")
    if not os.path.exists(path):
        return {}
    cols = None
    out = {}
    with open(path) as f:
        r = csv.DictReader(f)
        cols = r.fieldnames
        for c in cols:
            out[c] = []
        for row in r:
            for c in cols:
                out[c].append(float(row[c]))
    return out


if __name__ == "__main__":
    uni = select_universe(70)
    json.dump(uni, open(os.path.join(HERE, "binance_universe.json"), "w"))
    print(f"universe {len(uni)}: {uni[:20]} ...")
    okc = okf = 0
    for i, s in enumerate(uni):
        nc = fetch_klines(s)
        nf = fetch_funding(s)
        okc += nc > 400; okf += nf > 200
        if (i + 1) % 10 == 0 or nc < 400:
            print(f"  [{i+1}/{len(uni)}] {s:12} klines={nc:5} funding_days={nf}")
    print(f"完成:klines ok {okc}/{len(uni)}, funding ok {okf}/{len(uni)}")
