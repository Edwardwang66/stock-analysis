"""FastAPI 骨架:多市场行情 + 非 LLM 技术分析。

运行: uvicorn app.main:app --reload  (在 backend/ 目录下)
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import cache
from .analysis.chan import compute_chan
from .analysis.chips import compute_chips
from .analysis.moneyflow import compute_moneyflow
from .analysis.signals import analyze
from .models import Symbol
from .providers import router as data
from . import cache, store

app = FastAPI(title="Stock Dashboard API", version="0.1.0")

# 允许静态前端(GitHub Pages 等)跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"ok": True, "cache": cache.stats()}


@app.get("/api/v1/search")
async def search(q: str = Query(..., description="关键词:代码或名称,如 apple / 茅台 / BTC")):
    """标的联想搜索(Yahoo 搜索 + 加密常用对),带 SQLite 缓存。"""
    async with httpx.AsyncClient() as client:
        return await store.search_symbols(client, q)


@app.get("/api/v1/cache")
async def cache_status():
    return cache.stats()


@app.get("/api/v1/quotes")
async def quotes(symbols: str = Query(..., description="逗号分隔,如 US:AAPL,CRYPTO:BTCUSDT")):
    syms = [Symbol.parse(x) for x in symbols.split(",") if x.strip()]
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[store.get_quote_cached(client, s) for s in syms], return_exceptions=True
        )
    out = []
    for s, r in zip(syms, results):
        if isinstance(r, Exception):
            out.append({"symbol": str(s), "error": str(r)})
        else:
            out.append(r.model_dump(mode="json"))
    return out


@app.get("/api/v1/ohlcv")
async def ohlcv(symbol: str, interval: str = "1d", range: str = "1y"):
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            return (await store.get_ohlcv_cached(client, s, interval, range)).model_dump(mode="json")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/analysis")
async def analysis(symbol: str, interval: str = "1d", range: str = "1y"):
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            o = await store.get_ohlcv_cached(client, s, interval, range)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    if not o.bars:
        raise HTTPException(status_code=404, detail="no data")
    return analyze(str(s), o.bars, source=o.source).model_dump(mode="json")


@app.get("/api/v1/moneyflow")
async def moneyflow(symbol: str, interval: str = "5m", range: str = "1d"):
    """资金流向 / 主力资金(估算):分钟 K 线成交额分档 + 涨跌定方向,主力=特大+大。非 LLM、非真实逐笔。"""
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            o = await data.get_ohlcv(client, s, interval, range)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    return {"symbol": str(s), "interval": interval, "source": o.source, **compute_moneyflow(o.bars)}


@app.get("/api/v1/chips")
async def chips(symbol: str, interval: str = "1d", range: str = "1y"):
    """筹码分布(成本分布 · 估算):获利比例 / 平均成本 / 支撑位 / 压力位。非 LLM、非真实持仓。"""
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            o = await data.get_ohlcv(client, s, interval, range)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    if not o.bars:
        raise HTTPException(status_code=404, detail="no data")
    result = compute_chips(o.bars, o.bars[-1].close)
    if result is None:
        raise HTTPException(status_code=404, detail="insufficient data for chips")
    return {"symbol": str(s), "source": o.source, **result}


@app.get("/api/v1/chan")
async def chan(symbol: str, interval: str = "1d", range: str = "1y"):
    """简化版缠论结构识别(分型/笔/中枢/买卖点,含 MACD 背驰),非 LLM。"""
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            o = await store.get_ohlcv_cached(client, s, interval, range)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    if not o.bars:
        raise HTTPException(status_code=404, detail="no data")
    return {"symbol": str(s), "interval": interval, "source": o.source, **compute_chan(o.bars)}
