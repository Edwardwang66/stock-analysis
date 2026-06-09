"""腾讯行情(qt.gtimg.cn / ifzq.gtimg.cn)—— A股/港股主备源,美股报价备源。

优点:国内访问快、支持一次请求批量报价、对 A股/港股覆盖好。
限制:非官方接口,仅自用/演示;美股 K线代码需交易所后缀,这里不支持(raise Unsupported)。
编码:GBK。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from ..models import OHLCV, Bar, Quote, Symbol
from .base import Unsupported

_QUOTE_URL = "https://qt.gtimg.cn/q="
_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_MKLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/mkline"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard/0.2)", "Referer": "https://gu.qq.com/"}

_CN_TZ = timezone(timedelta(hours=8))
_KPERIOD = {"1d": "day", "1wk": "week", "1mo": "month"}
_MPERIOD = {"1m": "m1", "5m": "m5", "15m": "m15", "30m": "m30", "1h": "m60"}
_MCOUNT = {"1m": 320, "5m": 320, "15m": 320, "30m": 320, "1h": 320}
_CURRENCY = {"CN": "CNY", "HK": "HKD", "US": "USD"}


def tencent_code(s: Symbol) -> str:
    if s.market == "CN":
        return ("sh" if s.code.startswith(("6", "9", "5")) else "sz") + s.code
    if s.market == "HK":
        return "hk" + s.code.zfill(5)
    if s.market == "US":
        return "us" + s.code.upper()
    raise Unsupported(f"tencent 不支持市场 {s.market}")


def _f(v: str) -> float | None:
    try:
        x = float(v)
        return x
    except (TypeError, ValueError):
        return None


def _parse_quote_line(s: Symbol, line: str) -> Quote | None:
    # v_sh600519="1~贵州茅台~600519~1700.00~1690.00~1695.00~...";字段以 ~ 分隔
    if '"' not in line:
        return None
    body = line.split('"', 2)[1]
    p = body.split("~")
    if len(p) < 35:
        return None
    price, prev, open_ = _f(p[3]), _f(p[4]), _f(p[5])
    if price is None or price <= 0:
        return None
    change, change_pct = _f(p[31]), _f(p[32])
    if change is None and prev:
        change = price - prev
        change_pct = change / prev * 100 if prev else None
    vol = _f(p[36]) or _f(p[6])
    if vol is not None and s.market == "CN":
        vol *= 100  # 手 → 股
    ts = None
    raw_t = (p[30] or "").strip()
    for fmt in ("%Y%m%d%H%M%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            ts = datetime.strptime(raw_t, fmt).replace(tzinfo=_CN_TZ).astimezone(timezone.utc)
            break
        except ValueError:
            continue
    return Quote(
        symbol=str(s), price=price, change=change, change_pct=change_pct,
        open=open_, high=_f(p[33]), low=_f(p[34]), prev_close=prev, volume=vol,
        currency=_CURRENCY.get(s.market, ""), ts=ts or datetime.now(tz=timezone.utc),
        source="Tencent",
    )


class TencentProvider:
    name = "Tencent"
    markets = {"CN", "HK", "US"}
    commercial_redistribution = False

    async def get_quotes_batch(self, client: httpx.AsyncClient, syms: list[Symbol]) -> dict[str, Quote]:
        """一次 HTTP 拿 N 个标的报价 —— 看板批量场景的主要提速点。"""
        if not syms:
            return {}
        codes = ",".join(tencent_code(s) for s in syms)
        r = await client.get(_QUOTE_URL + codes, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        text = r.content.decode("gbk", errors="replace")
        out: dict[str, Quote] = {}
        lines = [ln for ln in text.split(";") if "=" in ln]
        by_code = {ln.split("=", 1)[0].strip().removeprefix("v_"): ln for ln in lines}
        for s in syms:
            ln = by_code.get(tencent_code(s))
            if not ln:
                continue
            q = _parse_quote_line(s, ln)
            if q:
                out[str(s)] = q
        return out

    async def get_quote(self, client: httpx.AsyncClient, s: Symbol) -> Quote:
        got = await self.get_quotes_batch(client, [s])
        q = got.get(str(s))
        if q is None:
            raise ValueError(f"tencent 无 {s} 报价")
        return q

    async def get_ohlcv(self, client: httpx.AsyncClient, s: Symbol, interval: str, range_: str) -> OHLCV:
        if s.market == "US":
            raise Unsupported("tencent 美股K线需交易所后缀,跳过")
        if interval in _MPERIOD:
            return await self._mkline(client, s, interval)
        period = _KPERIOD.get(interval)
        if period is None:
            raise Unsupported(f"tencent 不支持周期 {interval}")
        from .. import barstore
        days = barstore.RANGE_DAYS.get(range_, 366)
        count = min(800, days if period == "day" else days // 7 + 8 if period == "week" else days // 28 + 4)
        code = tencent_code(s)
        params = {"param": f"{code},{period},,,{max(count, 30)},qfq"}
        r = await client.get(_KLINE_URL, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", {}).get(code, {})
        rows = data.get(f"qfq{period}") or data.get(period) or []
        bars: list[Bar] = []
        for row in rows:
            # [日期, 开, 收, 高, 低, 量(手), ...] —— 注意顺序是 开/收/高/低
            if len(row) < 6:
                continue
            o, c, h, l, v = _f(row[1]), _f(row[2]), _f(row[3]), _f(row[4]), _f(row[5]) or 0.0
            if None in (o, c, h, l):
                continue
            try:
                ts = datetime.strptime(row[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if s.market == "CN":
                v *= 100
            bars.append(Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v))
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)

    async def _mkline(self, client: httpx.AsyncClient, s: Symbol, interval: str) -> OHLCV:
        code = tencent_code(s)
        period = _MPERIOD[interval]
        params = {"param": f"{code},{period},,{_MCOUNT[interval]}"}
        r = await client.get(_MKLINE_URL, params=params, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        rows = r.json().get("data", {}).get(code, {}).get(period) or []
        bars: list[Bar] = []
        for row in rows:
            if len(row) < 6:
                continue
            o, c, h, l, v = _f(row[1]), _f(row[2]), _f(row[3]), _f(row[4]), _f(row[5]) or 0.0
            if None in (o, c, h, l):
                continue
            try:
                ts = datetime.strptime(row[0], "%Y%m%d%H%M").replace(tzinfo=_CN_TZ).astimezone(timezone.utc)
            except ValueError:
                continue
            if s.market == "CN":
                v *= 100
            bars.append(Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v))
        return OHLCV(symbol=str(s), interval=interval, bars=bars, source=self.name)
