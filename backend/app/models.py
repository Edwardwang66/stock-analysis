"""统一数据模型(见 docs/data-model-api.md)。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Market = Literal["US", "HK", "CN", "CRYPTO"]


class Symbol(BaseModel):
    market: Market
    code: str

    def __str__(self) -> str:
        return f"{self.market}:{self.code}"

    @classmethod
    def parse(cls, s: str) -> "Symbol":
        if ":" not in s:
            raise ValueError(f"bad symbol (need MARKET:CODE): {s!r}")
        market, code = s.split(":", 1)
        market = market.upper()
        if market not in ("US", "HK", "CN", "CRYPTO"):
            raise ValueError(f"unknown market: {market!r}")
        return cls(market=market, code=code.upper())  # type: ignore[arg-type]


class Quote(BaseModel):
    symbol: str
    price: float
    change: Optional[float] = None
    change_pct: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    prev_close: Optional[float] = None
    volume: Optional[float] = None
    currency: str = ""
    ts: Optional[datetime] = None
    source: str = ""


class Bar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class OHLCV(BaseModel):
    symbol: str
    interval: str
    bars: list[Bar]
    source: str = ""


class AnalysisResult(BaseModel):
    symbol: str
    as_of: Optional[datetime] = None
    price: Optional[float] = None
    indicators: dict[str, Optional[float]]
    signals: list[dict]          # [{name, verdict, detail}]
    score: int                   # -100..100 综合(看空..看多)
    verdict: str                 # 强烈看空/看空/中性/看多/强烈看多
    summary: str                 # 中文一句话(规则生成,非LLM)
    source: str = ""
