"""数据源路由:多源降级链 + 熔断。

每个市场配一条 provider 链,首选挂了自动切备援;
连续失败的源进入熔断冷却(120s),冷却期内直接跳过,避免反复等超时。
缓存不在本层做(统一在 store 层,避免双层缓存键不一致)。
"""
from __future__ import annotations

import asyncio
import time

import httpx

from ..models import OHLCV, Quote, Symbol
from .base import Unsupported
from .binance import BinanceProvider
from .okx import OKXProvider
from .stooq import StooqProvider
from .tencent import TencentProvider
from .yahoo import YahooProvider

_YAHOO = YahooProvider()
_BINANCE = BinanceProvider()
_TENCENT = TencentProvider()
_OKX = OKXProvider()
_STOOQ = StooqProvider()

# 市场 → 降级链(顺序即优先级)
CHAINS: dict[str, list] = {
    "US": [_YAHOO, _TENCENT, _STOOQ],   # Tencent 只接美股报价,K线自动跳到 Stooq
    "HK": [_TENCENT, _YAHOO],           # 腾讯对港股快且支持批量
    "CN": [_TENCENT, _YAHOO],
    "CRYPTO": [_BINANCE, _OKX],
    "IDX": [_YAHOO],                    # 指数:Yahoo 代码直传(^GSPC / 000001.SS)
}

_FAIL_THRESHOLD = 3
_COOLDOWN = 120.0


class _Breaker:
    """简易熔断:连续失败 N 次 → 冷却期内跳过该源。"""

    def __init__(self) -> None:
        self.fails = 0
        self.open_until = 0.0

    def available(self) -> bool:
        return time.time() >= self.open_until

    def ok(self) -> None:
        self.fails = 0
        self.open_until = 0.0

    def fail(self) -> None:
        self.fails += 1
        if self.fails >= _FAIL_THRESHOLD:
            self.open_until = time.time() + _COOLDOWN


_breakers: dict[str, _Breaker] = {}


def _breaker(provider_name: str, op: str) -> _Breaker:
    return _breakers.setdefault(f"{provider_name}:{op}", _Breaker())


def breaker_stats() -> dict:
    now = time.time()
    return {
        k: {"fails": b.fails, "cooling_s": max(0, round(b.open_until - now))}
        for k, b in _breakers.items() if b.fails or b.open_until > now
    }


async def _try_chain(s: Symbol, op: str, call):
    """沿降级链依次尝试;全熔断时仍强制试一遍(半开),避免永久拒绝。"""
    chain = CHAINS.get(s.market, [])
    errors: list[str] = []
    candidates = [p for p in chain if _breaker(p.name, op).available()] or chain
    for p in candidates:
        br = _breaker(p.name, op)
        try:
            result = await call(p)
            br.ok()
            return result
        except Unsupported:
            continue  # 能力不匹配,不计失败
        except Exception as e:  # noqa: BLE001
            br.fail()
            errors.append(f"{p.name}: {e}")
    raise RuntimeError(f"{s} {op} 全部数据源失败 → " + (" | ".join(errors) or "无可用源"))


async def get_quote(client: httpx.AsyncClient, s: Symbol) -> Quote:
    return await _try_chain(s, "quote", lambda p: p.get_quote(client, s))


async def get_ohlcv(client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
    return await _try_chain(s, "ohlcv", lambda p: p.get_ohlcv(client, s, interval, range_))


async def get_quotes_batch(
    client: httpx.AsyncClient, syms: list[Symbol]
) -> tuple[dict[str, Quote], dict[str, str]]:
    """批量报价 → (成功结果, 失败原因)。

    CN/HK 用腾讯单请求批量(看板 20 个标的:20 次外呼 → 通常 2-3 次);
    美股以 Yahoo 为主源、腾讯批量结果兜底;加密并发走链。
    """
    out: dict[str, Quote] = {}
    fallback_us: dict[str, Quote] = {}

    t_batch = [s for s in syms if s.market in ("CN", "HK", "US")]
    br = _breaker(_TENCENT.name, "quote")
    if t_batch and br.available():
        try:
            got = await _TENCENT.get_quotes_batch(client, t_batch)
            br.ok()
            for k, q in got.items():
                # 美股腾讯数据只做兜底;A股/港股直接采纳
                (fallback_us if k.startswith("US:") else out).__setitem__(k, q)
        except Exception:  # noqa: BLE001
            br.fail()

    c_batch = [s for s in syms if s.market == "CRYPTO"]
    bbr = _breaker(_BINANCE.name, "quote")
    if len(c_batch) > 1 and bbr.available():
        try:
            out.update(await _BINANCE.get_quotes_batch(client, c_batch))
            bbr.ok()
        except Exception:  # noqa: BLE001
            bbr.fail()

    rest = [s for s in syms if str(s) not in out]
    results = await asyncio.gather(
        *[get_quote(client, s) for s in rest], return_exceptions=True
    )
    errors: dict[str, str] = {}
    for s, r in zip(rest, results):
        key = str(s)
        if isinstance(r, Exception):
            if key in fallback_us:
                out[key] = fallback_us[key]
            else:
                errors[key] = str(r)
        else:
            out[key] = r
    return out, errors
