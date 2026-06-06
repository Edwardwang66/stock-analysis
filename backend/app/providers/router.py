from __future__ import annotations

import httpx

from ..models import OHLCV, Quote, Symbol
from .binance import BinanceProvider
from .yahoo import YahooProvider

_YAHOO = YahooProvider()
_BINANCE = BinanceProvider()


def _provider(s: Symbol):
    if s.market == "CRYPTO":
        return _BINANCE
    return _YAHOO  # US / HK / CN


async def get_quote(client: httpx.AsyncClient, s: Symbol) -> Quote:
    return await _provider(s).get_quote(client, s)


async def get_ohlcv(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
    return await _provider(s).get_ohlcv(client, s, interval, range_)
