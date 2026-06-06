from __future__ import annotations

from typing import Protocol

import httpx

from ..models import OHLCV, Quote, Symbol


class DataProvider(Protocol):
    name: str
    markets: set[str]
    commercial_redistribution: bool

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote: ...
    async def get_ohlcv(
        self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str
    ) -> OHLCV: ...
