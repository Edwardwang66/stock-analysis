"""HTTP 层冒烟:端点 / 响应头 / 压缩 / 错误码(假数据源)。"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ["CACHE_DB"] = "/tmp/test_api_cache.db"
os.environ["STORE_DB"] = "/tmp/test_api_store.db"
for f in (os.environ["CACHE_DB"], os.environ["STORE_DB"]):
    if os.path.exists(f):
        os.remove(f)

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models import OHLCV, Bar, Quote  # noqa: E402
from app.providers import router  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


def mkbars(n):
    start = datetime.now(tz=timezone.utc) - timedelta(days=n)
    out = []
    price = 100.0
    for i in range(n):
        price *= 1.001 if i % 3 else 0.998
        out.append(Bar(ts=start + timedelta(days=i), open=price, high=price * 1.01,
                       low=price * 0.99, close=price * 1.002, volume=10000 + i * 7))
    return out


class FP:
    name = "FP"
    async def get_quote(self, client, s):
        return Quote(symbol=str(s), price=100.0, change=1.0, change_pct=1.0, source="FP")
    async def get_ohlcv(self, client, s, interval, range_):
        return OHLCV(symbol=str(s), interval=interval, bars=mkbars(300), source="FP")
    async def get_quotes_batch(self, client, syms):
        return {str(x): Quote(symbol=str(x), price=5.0, change=0.1, change_pct=2.0, source="FP") for x in syms}


fp = FP()
for m in ("US", "HK", "CN", "CRYPTO"):
    router.CHAINS[m] = [fp]
router._TENCENT = fp
router._BINANCE = fp

with TestClient(app) as c:
    r = c.get("/api/v1/health")
    ok("health 200 + 模块状态", r.status_code == 200 and "barstore" in r.json() and "breakers" in r.json())

    r = c.get("/api/v1/quotes", params={"symbols": "US:AAPL,CRYPTO:BTCUSDT,HK:0700"})
    body = r.json()
    ok("quotes 批量 3 标的", r.status_code == 200 and len(body) == 3 and all(x.get("price") for x in body))
    ok("quotes Cache-Control", "max-age=15" in r.headers.get("cache-control", ""))

    r = c.get("/api/v1/ohlcv", params={"symbol": "US:AAPL", "range": "1y"})
    ok("ohlcv 200 + bars + store标记", r.status_code == 200 and len(r.json()["bars"]) > 250
       and "store" in r.json()["source"])

    r = c.get("/api/v1/ohlcv", params={"symbol": "US:AAPL", "range": "1y"},
              headers={"accept-encoding": "gzip"})
    ok("ohlcv GZip 生效", r.headers.get("content-encoding") == "gzip")

    for ep in ("analysis", "chan", "chips"):
        r = c.get(f"/api/v1/{ep}", params={"symbol": "US:AAPL", "range": "1y"})
        ok(f"{ep} 200", r.status_code == 200, r.text[:120])
    r = c.get("/api/v1/moneyflow", params={"symbol": "US:AAPL"})
    ok("moneyflow 200", r.status_code == 200, r.text[:120])

    # 计算缓存命中:第二次相同请求应直出(用响应一致性近似验证)
    a1 = c.get("/api/v1/analysis", params={"symbol": "US:AAPL", "range": "1y"}).json()
    a2 = c.get("/api/v1/analysis", params={"symbol": "US:AAPL", "range": "1y"}).json()
    ok("analysis 二次一致(缓存)", a1 == a2)

    r = c.get("/api/v1/quotes", params={"symbols": "BAD"})
    ok("非法 symbol → 422", r.status_code == 422)
    r = c.get("/api/v1/quotes", params={"symbols": ",".join(f"US:S{i}" for i in range(60))})
    ok("超量标的 → 422", r.status_code == 422)

    r = c.get("/api/v1/search", params={"q": "btc"})
    ok("search 本地命中", r.status_code == 200 and any("BTC" in x["symbol"] for x in r.json()))

print(f"\nHTTP 层全部通过:{PASS} 项")
