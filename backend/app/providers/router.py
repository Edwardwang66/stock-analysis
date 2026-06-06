from __future__ import annotations

import httpx

from .. import cache
from ..models import OHLCV, Quote, Symbol
from .binance import BinanceProvider
from .yahoo import YahooProvider

_YAHOO = YahooProvider()
_BINANCE = BinanceProvider()

QUOTE_TTL_SECONDS = 60
OHLCV_TTL_SECONDS = 15 * 60


def _provider(s: Symbol):
    if s.market == "CRYPTO":
        return _BINANCE
    return _YAHOO  # US / HK / CN


async def get_quote(client: httpx.AsyncClient, s: Symbol) -> Quote:
    key = f"quote:v1:{s}"
    if cached := cache.get_json(key):
        quote = Quote.model_validate(cached)
        quote.source = f"{quote.source} cache"
        return quote
    quote = await _provider(s).get_quote(client, s)
    cache.set_json(key, quote.model_dump(mode="json"), QUOTE_TTL_SECONDS)
    return quote


async def get_ohlcv(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
    key = f"ohlcv:v1:{s}:{interval}:{range_}"
    if cached := cache.get_json(key):
        ohlcv = OHLCV.model_validate(cached)
        ohlcv.source = f"{ohlcv.source} cache"
        return ohlcv
    ohlcv = await _provider(s).get_ohlcv(client, s, interval, range_)
    cache.set_json(key, ohlcv.model_dump(mode="json"), OHLCV_TTL_SECONDS)
    return ohlcv
