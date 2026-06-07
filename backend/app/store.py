"""带缓存的数据访问 + 标的搜索。"""
from __future__ import annotations

import httpx

from . import cache
from .models import OHLCV, Quote, Symbol
from .providers import router as data

# 加密常用对(Yahoo 搜索不覆盖 Binance 交易对,单列)
CRYPTO_LIST = [
    ("BTCUSDT", "比特币 Bitcoin"), ("ETHUSDT", "以太坊 Ethereum"), ("SOLUSDT", "Solana"),
    ("BNBUSDT", "BNB"), ("XRPUSDT", "瑞波 XRP"), ("DOGEUSDT", "狗狗币 Dogecoin"),
    ("ADAUSDT", "Cardano"), ("TRXUSDT", "波场 TRON"), ("LINKUSDT", "Chainlink"),
    ("AVAXUSDT", "Avalanche"), ("DOTUSDT", "Polkadot"), ("MATICUSDT", "Polygon"),
    ("LTCUSDT", "莱特币 Litecoin"), ("SHIBUSDT", "Shiba Inu"), ("TONUSDT", "Toncoin"),
]


async def get_quote_cached(client: httpx.AsyncClient, s: Symbol) -> Quote:
    key = f"quote:{s}"
    c = cache.get_json(key)
    if c is not None:
        return Quote.model_validate(c)
    q = await data.get_quote(client, s)
    cache.set_json(key, q.model_dump(mode="json"), ttl=30)
    return q


async def get_ohlcv_cached(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
    key = f"ohlcv:{s}:{interval}:{range_}"
    c = cache.get_json(key)
    if c is not None:
        return OHLCV.model_validate(c)
    o = await data.get_ohlcv(client, s, interval, range_)
    # 日线缓存 10 分钟;小时线 2 分钟
    ttl = 120 if interval == "1h" else 600
    cache.set_json(key, o.model_dump(mode="json"), ttl=ttl)
    return o


def _map_yahoo(sym: str) -> str | None:
    if sym.endswith(".HK"):
        return f"HK:{sym[:-3]}"
    if sym.endswith(".SS") or sym.endswith(".SZ"):
        return f"CN:{sym[:-3]}"
    if "." not in sym and "-" not in sym and "=" not in sym:
        return f"US:{sym}"
    return None


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


async def search_symbols(client: httpx.AsyncClient, q: str) -> list[dict]:
    ql = q.strip().lower()
    if not ql:
        return []
    key = f"search:{ql}"
    c = cache.get_json(key)
    if c is not None:
        return c

    results: list[dict] = []
    for code, name in CRYPTO_LIST:
        if ql in code.lower() or ql in name.lower():
            results.append({"symbol": f"CRYPTO:{code}", "name": name, "market": "CRYPTO"})
    for sym, name in EQUITY_LIST:
        if ql in sym.lower() or ql in name.lower():
            results.append({"symbol": sym, "name": name, "market": sym.split(":")[0]})

    try:
        r = await client.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": q, "quotesCount": 10, "newsCount": 0},
            headers={"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.1)"},
            timeout=10,
        )
        for it in r.json().get("quotes", []):
            sym = it.get("symbol", "")
            m = _map_yahoo(sym)
            if not m:
                continue
            name = it.get("shortname") or it.get("longname") or sym
            results.append({"symbol": m, "name": name, "market": m.split(":")[0]})
    except Exception:  # noqa: BLE001 — 搜索失败不致命
        pass

    # 去重 + 截断
    seen: set[str] = set()
    out: list[dict] = []
    for r0 in results:
        if r0["symbol"] not in seen:
            seen.add(r0["symbol"])
            out.append(r0)
    out = out[:12]
    cache.set_json(key, out, ttl=86400)
    return out
