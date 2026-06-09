"""Stooq 免费 EOD 数据 —— 美股日线备援(Yahoo 全挂时仍有图可看)。

仅日线、收盘级延迟;report 用足够,实时性要求高的场景仅作兜底。
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

import httpx

from ..models import OHLCV, Bar, Quote, Symbol
from .base import Unsupported

_BASE = "https://stooq.com/q/d/l/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.2)"}


def _stooq_code(s: Symbol) -> str:
    if s.market == "US":
        return f"{s.code.lower()}.us"
    raise Unsupported(f"stooq 仅作美股备援,跳过 {s.market}")


class StooqProvider:
    name = "Stooq"
    markets = {"US"}
    commercial_redistribution = False

    async def _daily(self, client: httpx.AsyncClient, s: Symbol, days: int) -> list[Bar]:
        d2 = datetime.now(tz=timezone.utc)
        d1 = d2 - timedelta(days=days)
        params = {"s": _stooq_code(s), "i": "d",
                  "d1": d1.strftime("%Y%m%d"), "d2": d2.strftime("%Y%m%d")}
        r = await client.get(_BASE, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        bars: list[Bar] = []
        for row in csv.DictReader(io.StringIO(r.text)):
            try:
                bars.append(Bar(
                    ts=datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
                    open=float(row["Open"]), high=float(row["High"]),
                    low=float(row["Low"]), close=float(row["Close"]),
                    volume=float(row.get("Volume") or 0),
                ))
            except (KeyError, ValueError):
                continue
        return bars

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote:
        bars = await self._daily(client, s, 14)
        if not bars:
            raise ValueError(f"stooq 无 {s} 数据")
        last = bars[-1]
        prev = bars[-2].close if len(bars) > 1 else None
        change = last.close - prev if prev else None
        return Quote(
            symbol=str(s), price=last.close, change=change,
            change_pct=(change / prev * 100) if change is not None and prev else None,
            open=last.open, high=last.high, low=last.low, prev_close=prev,
            volume=last.volume, currency="USD", ts=last.ts, source="Stooq(EOD)",
        )

    async def get_ohlcv(self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
        if interval != "1d":
            raise Unsupported("stooq 仅日线")
        from .. import barstore
        days = barstore.RANGE_DAYS.get(range_, 366)
        bars = await self._daily(client, s, days)
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)
