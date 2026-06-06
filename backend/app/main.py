"""FastAPI 骨架:多市场行情 + 非 LLM 技术分析。

运行: uvicorn app.main:app --reload  (在 backend/ 目录下)
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analysis.signals import analyze
from .models import Symbol
from .providers import router as data

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
    return {"ok": True}


@app.get("/api/v1/quotes")
async def quotes(symbols: str = Query(..., description="逗号分隔,如 US:AAPL,CRYPTO:BTCUSDT")):
    syms = [Symbol.parse(x) for x in symbols.split(",") if x.strip()]
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[data.get_quote(client, s) for s in syms], return_exceptions=True
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
            return (await data.get_ohlcv(client, s, interval, range)).model_dump(mode="json")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/v1/analysis")
async def analysis(symbol: str, interval: str = "1d", range: str = "1y"):
    s = Symbol.parse(symbol)
    try:
        async with httpx.AsyncClient() as client:
            o = await data.get_ohlcv(client, s, interval, range)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(e))
    if not o.bars:
        raise HTTPException(status_code=404, detail="no data")
    return analyze(str(s), o.bars, source=o.source).model_dump(mode="json")
