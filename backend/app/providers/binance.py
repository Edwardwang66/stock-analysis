"""Binance 公开数据镜像 data-api.binance.vision(无地域限制、无 key)。"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import OHLCV, Bar, Quote, Symbol

_BASE = "https://data-api.binance.vision"
_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d", "1wk": "1w", "1mo": "1M"}
_LIMIT = {"1d": 2, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1000, "max": 1000}


class BinanceProvider:
    name = "Binance"
    markets = {"CRYPTO"}
    commercial_redistribution = True  # 公开行情;遵守 Binance API 条款

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote:
        r = await client.get(f"{_BASE}/api/v3/ticker/24hr", params={"symbol": s.code}, timeout=15)
        r.raise_for_status()
        d = r.json()
        return Quote(
            symbol=str(s), price=float(d["lastPrice"]), change=float(d["priceChange"]),
            change_pct=float(d["priceChangePercent"]), open=float(d["openPrice"]),
            high=float(d["highPrice"]), low=float(d["lowPrice"]), prev_close=float(d["prevClosePrice"]),
            volume=float(d["volume"]), currency="USDT",
            ts=datetime.now(tz=timezone.utc), source=self.name,
        )

    async def get_ohlcv(self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
        params = {"symbol": s.code, "interval": _INTERVAL.get(interval, "1d"), "limit": _LIMIT.get(range_, 365)}
        r = await client.get(f"{_BASE}/api/v3/klines", params=params, timeout=15)
        r.raise_for_status()
        bars = [
            Bar(
                ts=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                open=float(k[1]), high=float(k[2]), low=float(k[3]), close=float(k[4]), volume=float(k[5]),
            )
            for k in r.json()
        ]
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)
