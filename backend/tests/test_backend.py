"""离线验证:缓存 / 单飞 / 增量入库 / 降级链 / 熔断 / 批量报价。"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone

os.environ["CACHE_DB"] = "/tmp/test_cache.db"
os.environ["STORE_DB"] = "/tmp/test_store.db"
for f in ("/tmp/test_cache.db", "/tmp/test_store.db"):
    if os.path.exists(f):
        os.remove(f)

import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import barstore, cache, store  # noqa: E402
from app.models import OHLCV, Bar, Quote, Symbol  # noqa: E402
from app.providers import router  # noqa: E402
from app.providers.base import Unsupported  # noqa: E402

PASS = 0


def ok(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ✓ {name}")


def mkbars(n, start=None, interval_s=86400):
    start = start or (datetime.now(tz=timezone.utc) - timedelta(seconds=n * interval_s))
    return [
        Bar(ts=start + timedelta(seconds=i * interval_s),
            open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1000 + i)
        for i in range(n)
    ]


class FakeProvider:
    def __init__(self, name, fail=False, bars_n=200, unsupported=False):
        self.name = name
        self.fail = fail
        self.unsupported = unsupported
        self.bars_n = bars_n
        self.quote_calls = 0
        self.ohlcv_calls = []

    async def get_quote(self, client, s):
        self.quote_calls += 1
        if self.unsupported:
            raise Unsupported("nope")
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return Quote(symbol=str(s), price=123.0, change=1.0, change_pct=0.8, source=self.name)

    async def get_ohlcv(self, client, s, interval, range_):
        self.ohlcv_calls.append(range_)
        if self.unsupported:
            raise Unsupported("nope")
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return OHLCV(symbol=str(s), interval=interval, bars=mkbars(self.bars_n), source=self.name)


async def main():
    print("== cache: 新鲜/陈旧/宽限 ==")
    cache.set_json("k1", {"a": 1}, ttl=60)
    ok("fresh hit", cache.get_json("k1") == {"a": 1})
    cache.set_json("k2", {"b": 2}, ttl=-1)  # 立即过期但在宽限期
    ok("stale entry 返回 (值, False)", cache.get_entry("k2") == ({"b": 2}, False))
    ok("get_json 不回 stale", cache.get_json("k2") is None)

    print("== 降级链 + 熔断 ==")
    p1, p2 = FakeProvider("P1", fail=True), FakeProvider("P2")
    router.CHAINS["US"] = [p1, p2]
    router._breakers.clear()
    s = Symbol.parse("US:TEST")
    q = await router.get_quote(None, s)
    ok("主源挂 → 备源接管", q.source == "P2")
    for _ in range(3):
        try:
            await router.get_quote(None, s)
        except Exception:
            pass
    calls_before = p1.quote_calls
    await router.get_quote(None, s)
    ok("熔断后跳过故障源", p1.quote_calls == calls_before)
    pu = FakeProvider("PU", unsupported=True)
    router.CHAINS["US"] = [pu, p2]
    router._breakers.clear()
    await router.get_quote(None, s)
    ok("Unsupported 跳过不计失败", router._breakers[f"PU:quote"].fails == 0)

    print("== barstore 增量入库 ==")
    pd = FakeProvider("PD", bars_n=200)
    router.CHAINS["US"] = [pd]
    sym = Symbol.parse("US:INCR")
    o1 = await store.get_ohlcv_cached(None, sym, "1d", "6mo")
    ok("首次全量入库", len(o1.bars) > 150 and pd.ohlcv_calls == ["6mo"])
    o2 = await store.get_ohlcv_cached(None, sym, "1d", "6mo")
    ok("TTL 内零外呼", pd.ohlcv_calls == ["6mo"] and o1.bars[-1].ts == o2.bars[-1].ts)
    # 手动把 last_sync 调旧 → 触发增量补尾(只要 1mo)
    with barstore._lock:
        barstore._conn.execute("UPDATE bars_meta SET last_sync=0 WHERE symbol=?", (str(sym),))
    o3 = await store.get_ohlcv_cached(None, sym, "1d", "6mo")
    ok("过期后只补尾巴(1mo)", pd.ohlcv_calls == ["6mo", "1mo"])
    ok("库内数据仍完整", len(o3.bars) >= len(o1.bars) - 1)
    # 外部源全挂 → 降级返回库内旧数据
    pd.fail = True
    with barstore._lock:
        barstore._conn.execute("UPDATE bars_meta SET last_sync=0 WHERE symbol=?", (str(sym),))
    router._breakers.clear()
    o4 = await store.get_ohlcv_cached(None, sym, "1d", "6mo")
    ok("源全挂降级返回旧数据", len(o4.bars) > 150 and "stale" in o4.source)

    print("== 时间戳归一(跨源防重) ==")
    d1 = datetime(2026, 6, 8, 13, 30, tzinfo=timezone.utc)   # Yahoo 风格开盘时刻
    d2 = datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc)     # 腾讯风格零点
    barstore.upsert_bars("X:A", "1d", [Bar(ts=d1, open=1, high=1, low=1, close=1)], "S1")
    barstore.upsert_bars("X:A", "1d", [Bar(ts=d2, open=2, high=2, low=2, close=2)], "S2")
    rows = barstore.load_bars("X:A", "1d", 36500)
    ok("同日不同源只留一根K线", len(rows) == 1 and rows[0].close == 2)

    print("== 单飞合并 ==")
    pslow = FakeProvider("SLOW")
    orig = pslow.get_ohlcv

    async def slow(client, s, interval, range_):
        await asyncio.sleep(0.05)
        return await orig(client, s, interval, range_)
    pslow.get_ohlcv = slow
    router.CHAINS["US"] = [pslow]
    sym2 = Symbol.parse("US:SF")
    await asyncio.gather(*[store.get_ohlcv_cached(None, sym2, "1d", "1y") for _ in range(8)])
    ok("8 并发只外呼 1 次", len(pslow.ohlcv_calls) == 1)

    print("== 批量报价(缓存+批量+降级) ==")
    class FakeTencent(FakeProvider):
        def __init__(self):
            super().__init__("Tencent")
            self.batch_calls = 0
        async def get_quotes_batch(self, client, syms):
            self.batch_calls += 1
            return {str(x): Quote(symbol=str(x), price=9.9, source="Tencent") for x in syms}
    ft = FakeTencent()
    router._TENCENT = ft
    router.CHAINS["CN"] = [ft]
    router.CHAINS["HK"] = [ft]
    router._breakers.clear()
    syms = [Symbol.parse(x) for x in ("CN:600519", "HK:0700", "CN:000001")]
    rows = await store.get_quotes_cached(None, syms)
    ok("CN/HK 一次批量全中", ft.batch_calls == 1 and all("error" not in r for r in rows))
    rows2 = await store.get_quotes_cached(None, syms)
    ok("二次请求走缓存(零外呼)", ft.batch_calls == 1)

    print(f"\n全部通过:{PASS} 项")


asyncio.run(main())
