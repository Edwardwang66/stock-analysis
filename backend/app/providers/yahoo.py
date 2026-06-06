"""Yahoo Finance chart 端点。服务端直连(无 CORS 问题)。

⚠️ 非官方接口、Yahoo ToS 仅个人非商用——商用须换授权源(见 docs/compliance.md)。
覆盖 US/HK/CN(通过 Yahoo 后缀)。
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import OHLCV, Bar, Quote, Symbol

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.1)"}

# 统一 interval/range -> Yahoo
_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d", "1wk": "1wk", "1mo": "1mo"}
_RANGE = {"1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y", "max": "max"}


def _yahoo_code(s: Symbol) -> str:
    if s.market == "US":
        return s.code
    if s.market == "HK":
        return f"{s.code.zfill(4)}.HK"
    if s.market == "CN":
        # 6 开头沪市 .SS,其余深市 .SZ
        return f"{s.code}.SS" if s.code.startswith("6") else f"{s.code}.SZ"
    raise ValueError(f"yahoo 不支持市场 {s.market}")


class YahooProvider:
    name = "Yahoo"
    markets = {"US", "HK", "CN"}
    commercial_redistribution = False

    async def _chart(self, client, s, interval, range_):
        url = _BASE + _yahoo_code(s)
        params = {"interval": _INTERVAL.get(interval, "1d"), "range": _RANGE.get(range_, "1y")}
        r = await client.get(url, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        return res

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote:
        res = await self._chart(client, s, "1d", "1d")
        m = res["meta"]
        price = m.get("regularMarketPrice")
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        change = (price - prev) if (price is not None and prev is not None) else None
        change_pct = (change / prev * 100.0) if (change is not None and prev) else None
        return Quote(
            symbol=str(s), price=float(price), change=change, change_pct=change_pct,
            prev_close=prev, high=m.get("regularMarketDayHigh"), low=m.get("regularMarketDayLow"),
            volume=m.get("regularMarketVolume"), currency=m.get("currency", ""),
            ts=datetime.fromtimestamp(m["regularMarketTime"], tz=timezone.utc) if m.get("regularMarketTime") else None,
            source=self.name,
        )

    async def get_ohlcv(self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
        res = await self._chart(client, s, interval, range_)
        ts = res.get("timestamp", []) or []
        q = res["indicators"]["quote"][0]
        bars: list[Bar] = []
        for i, t in enumerate(ts):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if None in (o, h, l, c):
                continue
            bars.append(Bar(
                ts=datetime.fromtimestamp(t, tz=timezone.utc),
                open=o, high=h, low=l, close=c, volume=(q.get("volume") or [0])[i] or 0,
            ))
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)
