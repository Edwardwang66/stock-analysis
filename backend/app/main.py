"""FastAPI:多市场行情 + 非 LLM 技术分析。

运行: uvicorn app.main:app --reload  (在 backend/ 目录下)

性能要点:
- lifespan 共享 httpx.AsyncClient(连接池/keep-alive,告别每请求新建连接);
- GZip 压缩(K线 JSON 普遍 50KB+,压后 ~5KB);
- Cache-Control 响应头,浏览器/CDN 二级缓存;
- 计算类结果(analysis/chan/chips/moneyflow)短缓存,避免重复计算;
- 行情多源降级 + SQLite 增量存储见 store.py / providers/router.py。
"""
from __future__ import annotations

import asyncio
import contextlib
import time

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import barstore, cache, store
from .analysis.chan import compute_chan
from .analysis.chips import compute_chips
from .analysis.moneyflow import compute_moneyflow
from .analysis.signals import analyze
from .models import Symbol
from .providers import router as data

_PURGE_INTERVAL = 6 * 3600


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        timeout=httpx.Timeout(15.0, connect=5.0),
        follow_redirects=True,
    )
    app.state.started_at = time.time()

    async def _janitor():
        while True:
            await asyncio.sleep(_PURGE_INTERVAL)
            try:
                barstore.purge()
            except Exception:  # noqa: BLE001
                pass

    janitor = asyncio.create_task(_janitor())
    try:
        yield
    finally:
        janitor.cancel()
        await app.state.client.aclose()


app = FastAPI(title="Stock Dashboard API", version="0.2.0", lifespan=lifespan)

# 允许静态前端(GitHub Pages 等)跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


def _client(request: Request) -> httpx.AsyncClient:
    return request.app.state.client


def _cc(response: Response, seconds: int) -> None:
    response.headers["Cache-Control"] = f"public, max-age={seconds}, stale-while-revalidate={seconds * 4}"


def _parse(symbol: str) -> Symbol:
    try:
        return Symbol.parse(symbol)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


async def _ohlcv_or_502(request: Request, s: Symbol, interval: str, range_: str):
    try:
        return await store.get_ohlcv_cached(_client(request), s, interval, range_)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))


async def _computed(request: Request, response: Response, symbol: str, interval: str,
                    range_: str, kind: str, ttl: int, fn):
    """K线衍生计算的统一壳:取数 → 缓存命中直出 → 计算 → 缓存。"""
    s = _parse(symbol)
    _cc(response, min(ttl, 120))
    o = await _ohlcv_or_502(request, s, interval, range_)
    if not o.bars:
        raise HTTPException(status_code=404, detail="no data")
    ckey = f"{kind}:{s}:{interval}:{range_}:{int(o.bars[-1].ts.timestamp())}:{len(o.bars)}"
    if (hit := cache.get_json(ckey)) is not None:
        return hit
    result = fn(o)
    if result is None:
        raise HTTPException(status_code=404, detail=f"insufficient data for {kind}")
    cache.set_json(ckey, result, ttl=ttl)
    return result


@app.get("/api/v1/health")
async def health(request: Request):
    return {
        "ok": True,
        "uptime_s": round(time.time() - request.app.state.started_at),
        "cache": cache.stats(),
        "barstore": barstore.stats(),
        "breakers": data.breaker_stats(),
    }


@app.get("/api/v1/cache")
async def cache_status():
    return {"cache": cache.stats(), "barstore": barstore.stats()}


@app.get("/api/v1/search")
async def search(request: Request, response: Response,
                 q: str = Query(..., description="关键词:代码或名称,如 apple / 茅台 / BTC")):
    """标的联想搜索(本地表 + Yahoo + 腾讯 smartbox),带缓存。"""
    _cc(response, 3600)
    return await store.search_symbols(_client(request), q)


@app.get("/api/v1/quotes")
async def quotes(request: Request, response: Response,
                 symbols: str = Query(..., description="逗号分隔,如 US:AAPL,CRYPTO:BTCUSDT")):
    """批量报价:缓存直出 + 腾讯/Binance 批量接口合并外呼 + 旧值先回后台刷新。"""
    syms: list[Symbol] = []
    for x in symbols.split(","):
        if x.strip():
            syms.append(_parse(x.strip()))
    if not syms:
        return []
    if len(syms) > 50:
        raise HTTPException(status_code=422, detail="单次最多 50 个标的")
    _cc(response, 15)
    return await store.get_quotes_cached(_client(request), syms)


@app.get("/api/v1/ohlcv")
async def ohlcv(request: Request, response: Response,
                symbol: str, interval: str = "1d", range: str = "1y"):
    s = _parse(symbol)
    _cc(response, 60 if interval in ("1d", "1wk", "1mo") else 30)
    return (await _ohlcv_or_502(request, s, interval, range)).model_dump(mode="json")


@app.get("/api/v1/analysis")
async def analysis(request: Request, response: Response,
                   symbol: str, interval: str = "1d", range: str = "1y"):
    return await _computed(
        request, response, symbol, interval, range, "analysis", ttl=300,
        fn=lambda o: analyze(o.symbol, o.bars, source=o.source).model_dump(mode="json"),
    )


@app.get("/api/v1/moneyflow")
async def moneyflow(request: Request, response: Response,
                    symbol: str, interval: str = "5m", range: str = "1d"):
    """资金流向 / 主力资金(估算):分钟 K 线成交额分档 + 涨跌定方向,主力=特大+大。非 LLM、非真实逐笔。"""
    return await _computed(
        request, response, symbol, interval, range, "moneyflow", ttl=120,
        fn=lambda o: {"symbol": o.symbol, "interval": interval, "source": o.source,
                      **compute_moneyflow(o.bars)},
    )


@app.get("/api/v1/chips")
async def chips(request: Request, response: Response,
                symbol: str, interval: str = "1d", range: str = "1y"):
    """筹码分布(成本分布 · 估算):获利比例 / 平均成本 / 支撑位 / 压力位。非 LLM、非真实持仓。"""
    def _fn(o):
        r = compute_chips(o.bars, o.bars[-1].close)
        return None if r is None else {"symbol": o.symbol, "source": o.source, **r}
    return await _computed(request, response, symbol, interval, range, "chips", ttl=300, fn=_fn)


@app.get("/api/v1/chan")
async def chan(request: Request, response: Response,
               symbol: str, interval: str = "1d", range: str = "1y"):
    """简化版缠论结构识别(分型/笔/中枢/买卖点,含 MACD 背驰),非 LLM。"""
    return await _computed(
        request, response, symbol, interval, range, "chan", ttl=300,
        fn=lambda o: {"symbol": o.symbol, "interval": interval, "source": o.source,
                      **compute_chan(o.bars)},
    )
