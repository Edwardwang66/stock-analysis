"""规则化(非 LLM)技术分析:把指标转成多空信号、综合评分与中文摘要。

逻辑与 frontend/lib/analysis.ts 保持一致。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..models import AnalysisResult, Bar
from . import indicators as ind


def analyze(symbol: str, bars: list[Bar], source: str = "") -> AnalysisResult:
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    price = closes[-1] if closes else None

    sma20 = ind.last(ind.sma(closes, 20))
    sma50 = ind.last(ind.sma(closes, 50))
    sma200 = ind.last(ind.sma(closes, 200))
    rsi14 = ind.last(ind.rsi(closes, 14))
    macd_line, macd_sig, macd_hist = ind.macd(closes)
    macd_v = ind.last(macd_line)
    macd_s = ind.last(macd_sig)
    macd_h = ind.last(macd_hist)
    bb_mid, bb_up, bb_low = ind.bollinger(closes, 20, 2.0)
    bb_up_v, bb_low_v = ind.last(bb_up), ind.last(bb_low)
    atr14 = ind.atr(highs, lows, closes, 14)
    ret_1m = ind.pct_return(closes, 21)
    ret_3m = ind.pct_return(closes, 63)
    vol = ind.volatility(closes, 20)
    hi52 = max(closes[-252:]) if closes else None
    lo52 = min(closes[-252:]) if closes else None

    signals: list[dict] = []
    score = 0

    # ===== 评分 v2(2026-06-09,与 frontend/lib/analysis.ts 与 routines/methodology.md 严格同口径)=====
    # v1 缺陷:正分只有 趋势20+排列15+MACD15=50,RSI/布林加分项与上升趋势互斥 → 全部卡在 50。
    # v2:10 因子,强趋势+强动能+接近新高可拉开 50~90 区分度。

    # 1) 趋势:价格 vs MA50(±20)
    if price is not None and sma50 is not None:
        if price > sma50:
            signals.append({"name": "趋势(MA50)", "verdict": "看多", "detail": f"价格 {price:.2f} 在 50 日均线 {sma50:.2f} 上方"})
            score += 20
        else:
            signals.append({"name": "趋势(MA50)", "verdict": "看空", "detail": f"价格 {price:.2f} 在 50 日均线 {sma50:.2f} 下方"})
            score -= 20

    # 2) 长期排列:MA50 vs MA200(±15)
    if sma50 is not None and sma200 is not None:
        if sma50 > sma200:
            signals.append({"name": "MA50/MA200", "verdict": "看多", "detail": "50 日均线在 200 日均线上方(多头排列)"})
            score += 15
        else:
            signals.append({"name": "MA50/MA200", "verdict": "看空", "detail": "50 日均线在 200 日均线下方(空头排列)"})
            score -= 15

    # 3) 短期动能:MA20 vs MA50(±10)
    if sma20 is not None and sma50 is not None:
        if sma20 > sma50:
            signals.append({"name": "MA20/MA50", "verdict": "看多", "detail": "短期均线在中期均线上方(动能向上)"})
            score += 10
        else:
            signals.append({"name": "MA20/MA50", "verdict": "看空", "detail": "短期均线在中期均线下方(动能转弱)"})
            score -= 10

    # 4) RSI 分段(强势区加分,过热减分)
    if rsi14 is not None:
        if rsi14 >= 80:
            signals.append({"name": "RSI(14)", "verdict": "超买", "detail": f"RSI {rsi14:.1f} ≥ 80,显著过热"})
            score -= 15
        elif rsi14 >= 70:
            signals.append({"name": "RSI(14)", "verdict": "超买", "detail": f"RSI {rsi14:.1f} ≥ 70,短期或回调"})
            score -= 5
        elif rsi14 >= 55:
            signals.append({"name": "RSI(14)", "verdict": "看多", "detail": f"RSI {rsi14:.1f} 处 55-70 强势区"})
            score += 10
        elif rsi14 > 45:
            signals.append({"name": "RSI(14)", "verdict": "中性", "detail": f"RSI {rsi14:.1f}"})
        elif rsi14 > 30:
            signals.append({"name": "RSI(14)", "verdict": "看空", "detail": f"RSI {rsi14:.1f} 处 30-45 弱势区"})
            score -= 5
        else:
            signals.append({"name": "RSI(14)", "verdict": "超卖", "detail": f"RSI {rsi14:.1f} ≤ 30,短期或反弹"})
            score += 10

    # 5) MACD 线 vs 信号线(±10) + 6) 零轴(±5)
    if macd_v is not None and macd_s is not None:
        if macd_v > macd_s:
            signals.append({"name": "MACD", "verdict": "看多", "detail": "MACD 在信号线上方"})
            score += 10
        else:
            signals.append({"name": "MACD", "verdict": "看空", "detail": "MACD 在信号线下方"})
            score -= 10
        if macd_v > 0:
            signals.append({"name": "MACD零轴", "verdict": "看多", "detail": "DIF 在零轴上方(多头市场)"})
            score += 5
        else:
            signals.append({"name": "MACD零轴", "verdict": "看空", "detail": "DIF 在零轴下方"})
            score -= 5

    # 7) 布林带位置(±5)
    if price is not None and bb_up_v is not None and bb_low_v is not None:
        if price >= bb_up_v:
            signals.append({"name": "布林带", "verdict": "超买", "detail": "触及上轨"})
            score -= 5
        elif price <= bb_low_v:
            signals.append({"name": "布林带", "verdict": "超卖", "detail": "触及下轨"})
            score += 5
        else:
            signals.append({"name": "布林带", "verdict": "中性", "detail": "在通道内"})

    # 8) 52周接近度(George-Hwang;需 ≥200 根)
    if price is not None and hi52 is not None and len(closes) >= 200 and hi52 > 0:
        near = price / hi52
        if near >= 0.95:
            signals.append({"name": "52周位置", "verdict": "看多", "detail": f"距 52 周高 {((near - 1) * 100):.1f}%,接近新高(动量偏强)"})
            score += 10
        elif near >= 0.80:
            signals.append({"name": "52周位置", "verdict": "看多", "detail": f"价格处 52 周区间上沿(距高点 {((near - 1) * 100):.1f}%)"})
            score += 5
        elif near <= 0.60:
            signals.append({"name": "52周位置", "verdict": "看空", "detail": f"距 52 周高回撤 {((1 - near) * 100):.0f}%,深度回撤区"})
            score -= 5
        else:
            signals.append({"name": "52周位置", "verdict": "中性", "detail": f"距 52 周高 {((near - 1) * 100):.1f}%"})

    # 9) 近1月动量(±5)
    if ret_1m is not None:
        if ret_1m >= 8:
            signals.append({"name": "1月动量", "verdict": "看多", "detail": f"近 21 交易日 +{ret_1m:.1f}%"})
            score += 5
        elif ret_1m <= -8:
            signals.append({"name": "1月动量", "verdict": "看空", "detail": f"近 21 交易日 {ret_1m:.1f}%"})
            score -= 5

    # 10) 量价配合:量比≥1.5 时,放量上涨加分、放量下跌减分(±5)
    vols = [b.volume for b in bars]
    if len(vols) >= 21 and len(closes) >= 2:
        base_vol = sum(vols[-21:-1]) / 20
        if base_vol > 0:
            vr = vols[-1] / base_vol
            if vr >= 1.5:
                if closes[-1] >= closes[-2]:
                    signals.append({"name": "量价", "verdict": "看多", "detail": f"量比 {vr:.1f} 放量上涨"})
                    score += 5
                else:
                    signals.append({"name": "量价", "verdict": "看空", "detail": f"量比 {vr:.1f} 放量下跌"})
                    score -= 5

    score = max(-100, min(100, score))
    if score >= 50:
        verdict = "强烈看多"
    elif score >= 20:
        verdict = "看多"
    elif score > -20:
        verdict = "中性"
    elif score > -50:
        verdict = "看空"
    else:
        verdict = "强烈看空"

    bull = sum(1 for s in signals if s["verdict"] in ("看多", "超卖"))
    bear = sum(1 for s in signals if s["verdict"] in ("看空", "超买"))
    summary = (
        f"综合技术面【{verdict}】(评分 {score})。看多信号 {bull} 项、看空 {bear} 项。"
        f"{'RSI 提示超买,注意回调。' if (rsi14 or 0) >= 70 else ''}"
        f"{'RSI 提示超卖,或有反弹。' if (rsi14 and rsi14 <= 30) else ''}"
        " 仅供信息参考,非投资建议。"
    )

    return AnalysisResult(
        symbol=symbol,
        as_of=bars[-1].ts if bars else None,
        price=price,
        indicators={
            "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "rsi14": rsi14, "macd": macd_v, "macd_signal": macd_s, "macd_hist": macd_h,
            "bb_upper": bb_up_v, "bb_lower": bb_low_v, "atr14": atr14,
            "return_1m_pct": ret_1m, "return_3m_pct": ret_3m, "volatility_pct": vol,
            "high_52w": hi52, "low_52w": lo52,
        },
        signals=signals,
        score=score,
        verdict=verdict,
        summary=summary,
        source=source,
    )
