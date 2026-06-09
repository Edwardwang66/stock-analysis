"""数据访问层:缓存 + 单飞合并 + stale-while-revalidate + K线增量入库。

请求路径:
  quotes  : 内存/SQLite 缓存(30s 新鲜) → 过期≤10min 旧值直接回 + 后台刷新 → 否则同步拉
  ohlcv   : barstore 已覆盖范围 → 只增量补尾;未覆盖 → 全量拉一次入库;
            外部源全挂 → 降级返回库内旧数据(source 标 stale)
  search  : 本地表 + Yahoo + 腾讯 smartbox,24h 缓存

单飞(single-flight):同 key 并发请求只外呼一次,其余等同一结果 —— 防外部源被并发击穿。
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from . import barstore, cache
from .models import OHLCV, Quote, Symbol
from .providers import router as data

log = logging.getLogger("store")

QUOTE_TTL = 30          # 报价新鲜期
QUOTE_STALE_MAX = 600   # 报价可接受的最大陈旧度(SWR 上限)
SEARCH_TTL = 86400

# ---------------- 单飞合并 ----------------
_inflight: dict[str, asyncio.Task] = {}


async def _single_flight(key: str, factory):
    task = _inflight.get(key)
    if task is None:
        task = asyncio.create_task(factory())
        _inflight[key] = task
        task.add_done_callback(lambda _t: _inflight.pop(key, None))
    # shield:某个等待方断连不影响其他等待方共享的拉取
    return await asyncio.shield(task)


def _spawn_bg(key: str, factory) -> None:
    """后台刷新(不阻塞当前响应),单飞去重。"""
    if key in _inflight:
        return
    task = asyncio.create_task(factory())
    _inflight[key] = task

    def _done(t: asyncio.Task) -> None:
        _inflight.pop(key, None)
        if not t.cancelled() and t.exception():
            log.warning("bg refresh %s failed: %s", key, t.exception())

    task.add_done_callback(_done)


# ---------------- 报价 ----------------
async def _fetch_quote(client: httpx.AsyncClient, s: Symbol) -> Quote:
    q = await data.get_quote(client, s)
    cache.set_json(f"quote:{s}", {"at": time.time(), "q": q.model_dump(mode="json")}, ttl=QUOTE_TTL)
    return q


async def get_quote_cached(client: httpx.AsyncClient, s: Symbol) -> Quote:
    key = f"quote:{s}"
    entry = cache.get_entry(key)
    if entry is not None:
        payload, fresh = entry
        age = time.time() - payload.get("at", 0)
        quote = Quote.model_validate(payload["q"])
        if fresh:
            return quote
        if age <= QUOTE_STALE_MAX:
            # 旧值直接回,后台刷新 —— 下个轮询周期自然拿到新值
            _spawn_bg(key, lambda: _fetch_quote(client, s))
            quote.source = f"{quote.source}·stale"
            return quote
    return await _single_flight(key, lambda: _fetch_quote(client, s))


async def get_quotes_cached(client: httpx.AsyncClient, syms: list[Symbol]) -> list[dict]:
    """批量报价:缓存命中直出,未命中合并成一次批量外呼。"""
    out: dict[str, dict] = {}
    missing: list[Symbol] = []
    now = time.time()
    for s in syms:
        entry = cache.get_entry(f"quote:{s}")
        if entry is not None:
            payload, fresh = entry
            age = now - payload.get("at", 0)
            if fresh:
                out[str(s)] = payload["q"]
                continue
            if age <= QUOTE_STALE_MAX:
                q = dict(payload["q"])
                q["source"] = f"{q.get('source', '')}·stale"
                out[str(s)] = q
                missing.append(s)  # 仍然去刷新,但本次响应用旧值
                continue
        missing.append(s)

    fresh_syms = [s for s in missing if str(s) not in out]
    bg_syms = [s for s in missing if str(s) in out]

    async def _refresh(targets: list[Symbol]) -> dict[str, Quote]:
        quotes, errors = await data.get_quotes_batch(client, targets)
        for k, q in quotes.items():
            cache.set_json(f"quote:{k}", {"at": time.time(), "q": q.model_dump(mode="json")}, ttl=QUOTE_TTL)
        for k, msg in errors.items():
            log.warning("quote %s failed: %s", k, msg)
        return quotes

    if bg_syms:
        _spawn_bg("quotes:bg:" + ",".join(sorted(str(s) for s in bg_syms)),
                  lambda: _refresh(bg_syms))
    errors: dict[str, str] = {}
    if fresh_syms:
        quotes, errors = await data.get_quotes_batch(client, fresh_syms)
        for k, q in quotes.items():
            d = q.model_dump(mode="json")
            cache.set_json(f"quote:{k}", {"at": time.time(), "q": d}, ttl=QUOTE_TTL)
            out[k] = d

    results: list[dict] = []
    for s in syms:
        d = out.get(str(s))
        if d is not None:
            results.append(d)
        else:
            results.append({"symbol": str(s), "error": errors.get(str(s), "无可用数据源")})
    return results


# ---------------- K线(增量入库) ----------------
def _series_key(s: Symbol, interval: str) -> str:
    return f"{s}|{interval}"


async def _sync_bars(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> str:
    """按需同步外部源 → barstore。返回数据来源名。"""
    sym, days = str(s), barstore.RANGE_DAYS.get(range_, 366)
    meta = barstore.get_meta(sym, interval)
    covered = meta is not None and meta["full_days"] >= days
    fetch_range = barstore.TAIL_RANGE.get(interval, "1mo") if covered else range_
    o = await data.get_ohlcv(client, s, interval, fetch_range)
    barstore.upsert_bars(sym, interval, o.bars, o.source,
                         full_days=None if covered else days)
    return o.source


async def get_ohlcv_cached(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
    sym = str(s)
    if not barstore.enabled():
        # 持久层不可用 → 退回纯透传(罕见,如只读文件系统)
        return await _single_flight(f"ohlcv:{sym}:{interval}:{range_}",
                                    lambda: data.get_ohlcv(client, s, interval, range_))

    days = barstore.RANGE_DAYS.get(range_, 366)
    meta = barstore.get_meta(sym, interval)
    ttl = barstore.SYNC_TTL.get(interval, 600)
    fresh = meta is not None and (time.time() - meta["last_sync"]) < ttl
    covered = meta is not None and meta["full_days"] >= days

    if fresh and covered:
        return barstore.load_ohlcv(sym, interval, range_, meta["source"] + "·store")

    try:
        source = await _single_flight(
            f"sync:{sym}:{interval}:{range_}",
            lambda: _sync_bars(client, s, interval, range_),
        )
    except Exception:
        # 外部源全挂:有旧数据就降级返回,没有才抛
        old = barstore.load_bars(sym, interval, days)
        if old:
            log.warning("ohlcv %s %s 外部源失败,返回库内旧数据", sym, interval)
            return OHLCV(symbol=sym, interval=interval, bars=old,
                         source=(meta or {}).get("source", "") + "·stale")
        raise
    return barstore.load_ohlcv(sym, interval, range_, source + "·store")


# ---------------- 搜索 ----------------
# 加密常用对(Yahoo 搜索不覆盖 Binance 交易对,单列)
CRYPTO_LIST = [
    ("BTCUSDT", "比特币 Bitcoin"), ("ETHUSDT", "以太坊 Ethereum"), ("SOLUSDT", "Solana"),
    ("BNBUSDT", "BNB"), ("XRPUSDT", "瑞波 XRP"), ("DOGEUSDT", "狗狗币 Dogecoin"),
    ("ADAUSDT", "Cardano"), ("TRXUSDT", "波场 TRON"), ("LINKUSDT", "Chainlink"),
    ("AVAXUSDT", "Avalanche"), ("DOTUSDT", "Polkadot"), ("MATICUSDT", "Polygon"),
    ("LTCUSDT", "莱特币 Litecoin"), ("SHIBUSDT", "Shiba Inu"), ("TONUSDT", "Toncoin"),
]

# 本地常用股票(含中文名)—— Yahoo 搜索对中文名支持差,本地表保证"茅台/腾讯"等可搜
EQUITY_LIST: list[tuple[str, str]] = [
    ("CN:600519", "贵州茅台"), ("CN:000001", "平安银行"), ("CN:600036", "招商银行"),
    ("CN:601318", "中国平安"), ("CN:300750", "宁德时代"), ("CN:000858", "五粮液"),
    ("CN:600276", "恒瑞医药"), ("CN:002594", "比亚迪"), ("CN:601899", "紫金矿业"),
    ("CN:600900", "长江电力"), ("CN:000333", "美的集团"), ("CN:600030", "中信证券"),
    ("HK:0700", "腾讯控股 Tencent"), ("HK:9988", "阿里巴巴 Alibaba"), ("HK:3690", "美团 Meituan"),
    ("HK:0939", "建设银行"), ("HK:1810", "小米集团 Xiaomi"), ("HK:9618", "京东 JD"),
    ("HK:0941", "中国移动"), ("HK:1299", "友邦保险 AIA"), ("HK:2318", "中国平安"),
    ("US:AAPL", "苹果 Apple"), ("US:MSFT", "微软 Microsoft"), ("US:NVDA", "英伟达 Nvidia"),
    ("US:TSLA", "特斯拉 Tesla"), ("US:GOOGL", "谷歌 Google"), ("US:AMZN", "亚马逊 Amazon"),
    ("US:META", "Meta 脸书"), ("US:NFLX", "奈飞 Netflix"), ("US:BABA", "阿里巴巴 Alibaba"),
]


def _map_yahoo(sym: str) -> str | None:
    if sym.endswith(".HK"):
        return f"HK:{sym[:-3]}"
    if sym.endswith(".SS") or sym.endswith(".SZ"):
        return f"CN:{sym[:-3]}"
    if "." not in sym and "-" not in sym and "=" not in sym:
        return f"US:{sym}"
    return None


async def _yahoo_search(client: httpx.AsyncClient, q: str) -> list[dict]:
    r = await client.get(
        "https://query1.finance.yahoo.com/v1/finance/search",
        params={"q": q, "quotesCount": 10, "newsCount": 0},
        headers={"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.2)"},
        timeout=8,
    )
    out = []
    for it in r.json().get("quotes", []):
        m = _map_yahoo(it.get("symbol", ""))
        if m:
            out.append({"symbol": m, "name": it.get("shortname") or it.get("longname") or m,
                        "market": m.split(":")[0]})
    return out


_SMARTBOX_MARKET = {"sh": "CN", "sz": "CN", "hk": "HK", "us": "US"}


async def _tencent_search(client: httpx.AsyncClient, q: str) -> list[dict]:
    """腾讯 smartbox:中文名/拼音搜索 A股/港股/美股,补 Yahoo 中文短板。"""
    r = await client.get(
        "https://smartbox.gtimg.cn/s3/", params={"v": 2, "q": q, "t": "all"},
        headers={"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.2)"},
        timeout=8,
    )
    text = r.content.decode("gbk", errors="replace")
    if '"' not in text:
        return []
    out = []
    for item in text.split('"')[1].split("^"):
        p = item.split("~")
        if len(p) < 3:
            continue
        mkt = _SMARTBOX_MARKET.get(p[0])
        if not mkt:
            continue
        code = p[1].upper()
        if mkt == "US":
            code = code.split(".")[0]
        if mkt == "HK":
            code = code[-4:] if len(code) > 4 and code.startswith("0") else code
        name = p[2].replace("\\u", "").strip() or code
        try:  # smartbox 名称是 unicode 转义
            name = p[2].encode().decode("unicode_escape")
        except Exception:  # noqa: BLE001
            pass
        out.append({"symbol": f"{mkt}:{code}", "name": name, "market": mkt})
    return out


async def search_symbols(client: httpx.AsyncClient, q: str) -> list[dict]:
    ql = q.strip().lower()
    if not ql:
        return []
    key = f"search:{ql}"
    if (c := cache.get_json(key)) is not None:
        return c

    results: list[dict] = []
    for code, name in CRYPTO_LIST:
        if ql in code.lower() or ql in name.lower():
            results.append({"symbol": f"CRYPTO:{code}", "name": name, "market": "CRYPTO"})
    for sym, name in EQUITY_LIST:
        if ql in sym.lower() or ql in name.lower():
            results.append({"symbol": sym, "name": name, "market": sym.split(":")[0]})

    # 两路远程搜索并发,谁成功用谁(都成功则合并)
    remote = await asyncio.gather(
        _yahoo_search(client, q), _tencent_search(client, q), return_exceptions=True
    )
    for batch in remote:
        if isinstance(batch, list):
            results.extend(batch)

    seen: set[str] = set()
    out = []
    for r0 in results:
        if r0["symbol"] not in seen:
            seen.add(r0["symbol"])
            out.append(r0)
    out = out[:12]
    cache.set_json(key, out, ttl=SEARCH_TTL)
    return out
