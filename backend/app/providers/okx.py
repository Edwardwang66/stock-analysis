"""OKX 公开行情 —— 加密市场备援源(Binance 不可用时自动切换)。

公开接口无需 key;candles 单次最多 300 根,作为备援足够(分析需 ~250 根)。
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import OHLCV, Bar, Quote, Symbol
from .base import Unsupported

_BASE = "https://www.okx.com"
_BAR = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1H",
        "1d": "1Dutc", "1wk": "1Wutc", "1mo": "1Mutc"}
_LIMIT = {"1d": 2, "5d": 5, "1mo": 31, "3mo": 92, "6mo": 183,
          "1y": 300, "2y": 300, "5y": 300, "max": 300}
_QUOTES = ("USDT", "USDC", "BTC", "ETH", "USD")


def _inst_id(code: str) -> str:
    """BTCUSDT -> BTC-USDT。"""
    for q in _QUOTES:
        if code.endswith(q) and len(code) > len(q):
            return f"{code[: -len(q)]}-{q}"
    raise Unsupported(f"okx 无法识别交易对 {code}")


class OKXProvider:
    name = "OKX"
    markets = {"CRYPTO"}
    commercial_redistribution = True

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote:
        r = await client.get(f"{_BASE}/api/v5/market/ticker",
                             params={"instId": _inst_id(s.code)}, timeout=10)
        r.raise_for_status()
        data = r.json().get("data") or []
        if not data:
            raise ValueError(f"okx 无 {s} 报价")
        d = data[0]
        last, open24 = float(d["last"]), float(d.get("open24h") or 0)
        change = last - open24 if open24 else None
        return Quote(
            symbol=str(s), price=last, change=change,
            change_pct=(change / open24 * 100) if change is not None and open24 else None,
            open=open24 or None, high=float(d.get("high24h") or 0) or None,
            low=float(d.get("low24h") or 0) or None, prev_close=open24 or None,
            volume=float(d.get("vol24h") or 0) or None, currency="USDT",
            ts=datetime.now(tz=timezone.utc), source=self.name,
        )

    async def get_ohlcv(self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
        bar = _BAR.get(interval)
        if bar is None:
            raise Unsupported(f"okx 不支持周期 {interval}")
        limit = _LIMIT.get(range_, 300) if interval in ("1d", "1wk", "1mo") else 300
        r = await client.get(f"{_BASE}/api/v5/market/candles",
                             params={"instId": _inst_id(s.code), "bar": bar, "limit": limit},
                             timeout=15)
        r.raise_for_status()
        rows = r.json().get("data") or []
        bars = [
            Bar(ts=datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc),
                open=float(k[1]), high=float(k[2]), low=float(k[3]), close=float(k[4]),
                volume=float(k[5]))
            for k in reversed(rows)  # OKX 返回新→旧
        ]
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)
