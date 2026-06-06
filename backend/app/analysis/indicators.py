"""纯 Python 技术指标(无 pandas/numpy 依赖)。

输入均为收盘价/价格序列 list[float],返回与输入等长的序列(前导不足处为 None),
或标量。供 signals.py 与 API 使用;前端 TS 版本逻辑一致(frontend/lib/indicators.ts)。
"""
from __future__ import annotations

from typing import Optional


def sma(values: list[float], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if period <= 0:
        return out
    run = 0.0
    for i, v in enumerate(values):
        run += v
        if i >= period:
            run -= values[i - period]
        if i >= period - 1:
            out[i] = run / period
    return out


def ema(values: list[float], period: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1)
    # 用前 period 个的 SMA 作为种子
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1 + avg_gain / avg_loss)
    return out


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """返回 (macd_line, signal_line, histogram)。"""
    ef = ema(values, fast)
    es = ema(values, slow)
    line: list[Optional[float]] = [
        (a - b) if (a is not None and b is not None) else None for a, b in zip(ef, es)
    ]
    # 对 line 中非 None 段做 EMA(signal)
    idx = [i for i, v in enumerate(line) if v is not None]
    sig: list[Optional[float]] = [None] * len(values)
    if len(idx) >= signal:
        seq = [line[i] for i in idx]  # type: ignore[misc]
        es2 = ema(seq, signal)  # type: ignore[arg-type]
        for j, i in enumerate(idx):
            sig[i] = es2[j]
    hist: list[Optional[float]] = [
        (l - s) if (l is not None and s is not None) else None for l, s in zip(line, sig)
    ]
    return line, sig, hist


def bollinger(values: list[float], period: int = 20, mult: float = 2.0):
    """返回 (mid, upper, lower)。"""
    mid = sma(values, period)
    upper: list[Optional[float]] = [None] * len(values)
    lower: list[Optional[float]] = [None] * len(values)
    for i in range(len(values)):
        if i >= period - 1:
            window = values[i - period + 1 : i + 1]
            m = mid[i]
            if m is None:
                continue
            var = sum((x - m) ** 2 for x in window) / period
            sd = var ** 0.5
            upper[i] = m + mult * sd
            lower[i] = m - mult * sd
    return mid, upper, lower


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Optional[float]:
    n = len(closes)
    if n <= period:
        return None
    trs: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    # 简单平均(Wilder 平滑亦可,这里取近 period TR 均值)
    return sum(trs[-period:]) / period


def pct_return(values: list[float], lookback: int) -> Optional[float]:
    if len(values) <= lookback or values[-1 - lookback] == 0:
        return None
    return (values[-1] / values[-1 - lookback] - 1.0) * 100.0


def volatility(values: list[float], lookback: int = 20) -> Optional[float]:
    """近 lookback 日对数收益的年化波动率(%)。"""
    import math

    if len(values) <= lookback:
        return None
    rets = []
    for i in range(len(values) - lookback, len(values)):
        if values[i - 1] > 0:
            rets.append(math.log(values[i] / values[i - 1]))
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return (var ** 0.5) * (252 ** 0.5) * 100.0


def last(values: list[Optional[float]]) -> Optional[float]:
    for v in reversed(values):
        if v is not None:
            return v
    return None
