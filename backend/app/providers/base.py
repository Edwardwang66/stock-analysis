from __future__ import annotations

from typing import Protocol

import httpx

from ..models import OHLCV, Quote, Symbol


class Unsupported(Exception):
    """该数据源不支持此 市场/周期 组合 —— 降级链跳过它,不计入熔断失败。"""


class DataProvider(Protocol):
    name: str
    markets: set[str]
    commercial_redistribution: bool

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote: ...
    async def get_ohlcv(
        self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str
    ) -> OHLCV: ...
