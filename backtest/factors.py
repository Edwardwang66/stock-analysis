"""因子库:把日线序列转成截面/时序因子值。

纯 numpy 实现。所有函数输入 adjclose(复权收盘)一维数组,输出对齐的因子序列
(前导不足处为 nan),保证"只用 t 时刻及之前的数据"——无未来函数(no look-ahead)。

核心因子:TQM = Trend(趋势) × Quality(质量) × Momentum(动量) 三维合成。
设计动机见 README.md。
"""
from __future__ import annotations

import numpy as np

NAN = float("nan")


def _sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, NAN, dtype=float)
    if len(x) < n:
        return out
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def _rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, NAN, dtype=float)
    for i in range(n - 1, len(x)):
        out[i] = x[i - n + 1:i + 1].std(ddof=1)
    return out


def log_returns(px: np.ndarray) -> np.ndarray:
    r = np.full_like(px, NAN, dtype=float)
    r[1:] = np.log(px[1:] / px[:-1])
    return r


# ---------- 三大支柱 ----------

def trend(px: np.ndarray) -> np.ndarray:
    """趋势分 [0,1]:衡量"是否处于健康上升趋势"。

    三个条件加权:价>200日线、50日线>200日线、价>50日线。
    多头排列得分高。规避在下跌趋势中接刀。
    """
    sma50 = _sma(px, 50)
    sma200 = _sma(px, 200)
    s = np.full_like(px, NAN, dtype=float)
    for i in range(len(px)):
        if np.isnan(sma200[i]):
            continue
        score = 0.0
        score += 0.4 if px[i] > sma200[i] else 0.0
        score += 0.3 if sma50[i] > sma200[i] else 0.0
        score += 0.3 if px[i] > sma50[i] else 0.0
        s[i] = score
    return s


def momentum(px: np.ndarray, lookback: int = 252, skip: int = 21) -> np.ndarray:
    """12-1 动量:过去 lookback 日收益,跳过最近 skip 日(规避短期反转)。

    经典横截面动量因子(Jegadeesh & Titman)。输出为原始收益率(可正可负)。
    """
    m = np.full_like(px, NAN, dtype=float)
    for i in range(len(px)):
        a = i - skip
        b = i - lookback
        if b < 0 or a <= b:
            continue
        m[i] = px[a] / px[b] - 1.0
    return m


def quality(px: np.ndarray, lookback: int = 126) -> np.ndarray:
    """趋势质量分:近 lookback 日的"收益/波动"信息比 + 平滑度。

    高分 = 稳步上行(低回撤、低波动);低分 = 暴涨暴跌或阴跌。
    输出近似年化 Sharpe(可正可负)。
    """
    r = log_returns(px)
    q = np.full_like(px, NAN, dtype=float)
    for i in range(lookback, len(px)):
        w = r[i - lookback + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w) < lookback // 2 or w.std(ddof=1) == 0:
            continue
        q[i] = (w.mean() / w.std(ddof=1)) * np.sqrt(252)
    return q


def rsi(px: np.ndarray, n: int = 14) -> np.ndarray:
    r = np.full_like(px, NAN, dtype=float)
    if len(px) <= n:
        return r
    d = np.diff(px)
    gain = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    ag = gain[:n].mean()
    al = loss[:n].mean()
    r[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n + 1, len(px)):
        ag = (ag * (n - 1) + gain[i - 1]) / n
        al = (al * (n - 1) + loss[i - 1]) / n
        r[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return r


# ---------- 合成 TQM ----------

def tqm_signal(px: np.ndarray,
               trend_min: float = 1.0,
               mom_min: float = 0.05,
               qual_min: float = 0.5,
               rsi_max: float = 80.0) -> np.ndarray:
    """TQM 买入信号(布尔数组)。

    在每根 bar 上,若同时满足:
      - 趋势分 >= trend_min(默认 1.0 = 完美多头排列)
      - 12-1 动量 >= mom_min
      - 趋势质量(年化 Sharpe) >= qual_min
      - RSI < rsi_max(规避极端超买追高)
    则当日收盘后视为"看多"。逻辑:只在确认的、健康的、有动量的上升趋势里做多。
    """
    t = trend(px)
    m = momentum(px)
    q = quality(px)
    rs = rsi(px)
    sig = (
        (t >= trend_min)
        & (m >= mom_min)
        & (q >= qual_min)
        & (rs < rsi_max)
    )
    # nan 比较结果为 False,天然过滤前导不足
    return np.nan_to_num(sig, nan=0.0).astype(bool)


def tqm_score(px: np.ndarray) -> np.ndarray:
    """连续版 TQM 评分(用于排序/分层),非阈值信号。

    标准化三支柱后等权合成,便于做横截面分层回测。
    """
    t = trend(px)
    m = momentum(px)
    q = quality(px)
    # 简单缩放到可比尺度
    return t + np.tanh(m * 3) * 0.5 + np.tanh(q) * 0.5
