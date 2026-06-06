// 规则化(非 LLM)技术分析,与 backend/app/analysis/signals.py 一致。
import { bollinger, last, macd, pctReturn, rsi, sma } from "./indicators";
import type { Bar } from "./datasource";

export interface Signal { name: string; verdict: string; detail: string }
export interface Analysis {
  price: number | null;
  score: number;
  verdict: string;
  summary: string;
  signals: Signal[];
  indicators: Record<string, number | null>;
}

export function analyze(bars: Bar[]): Analysis {
  const closes = bars.map((b) => b.close);
  const price = closes.length ? closes[closes.length - 1] : null;
  const sma50 = last(sma(closes, 50));
  const sma200 = last(sma(closes, 200));
  const rsi14 = last(rsi(closes, 14));
  const m = macd(closes);
  const macdV = last(m.line), macdS = last(m.sig);
  const bb = bollinger(closes, 20, 2);
  const bbUp = last(bb.up), bbLo = last(bb.lo);

  const signals: Signal[] = [];
  let score = 0;

  if (price !== null && sma50 !== null) {
    if (price > sma50) { signals.push({ name: "趋势(MA50)", verdict: "看多", detail: `价格 ${price.toFixed(2)} 在 50 日均线 ${sma50.toFixed(2)} 上方` }); score += 20; }
    else { signals.push({ name: "趋势(MA50)", verdict: "看空", detail: `价格 ${price.toFixed(2)} 在 50 日均线 ${sma50.toFixed(2)} 下方` }); score -= 20; }
  }
  if (sma50 !== null && sma200 !== null) {
    if (sma50 > sma200) { signals.push({ name: "MA50/MA200", verdict: "看多", detail: "多头排列(50>200)" }); score += 15; }
    else { signals.push({ name: "MA50/MA200", verdict: "看空", detail: "空头排列(50<200)" }); score -= 15; }
  }
  if (rsi14 !== null) {
    if (rsi14 >= 70) { signals.push({ name: "RSI(14)", verdict: "超买", detail: `RSI ${rsi14.toFixed(1)} ≥ 70` }); score -= 10; }
    else if (rsi14 <= 30) { signals.push({ name: "RSI(14)", verdict: "超卖", detail: `RSI ${rsi14.toFixed(1)} ≤ 30` }); score += 10; }
    else signals.push({ name: "RSI(14)", verdict: "中性", detail: `RSI ${rsi14.toFixed(1)}` });
  }
  if (macdV !== null && macdS !== null) {
    if (macdV > macdS) { signals.push({ name: "MACD", verdict: "看多", detail: "MACD 在信号线上方" }); score += 15; }
    else { signals.push({ name: "MACD", verdict: "看空", detail: "MACD 在信号线下方" }); score -= 15; }
  }
  if (price !== null && bbUp !== null && bbLo !== null) {
    if (price >= bbUp) { signals.push({ name: "布林带", verdict: "超买", detail: "触及上轨" }); score -= 5; }
    else if (price <= bbLo) { signals.push({ name: "布林带", verdict: "超卖", detail: "触及下轨" }); score += 5; }
    else signals.push({ name: "布林带", verdict: "中性", detail: "通道内" });
  }

  score = Math.max(-100, Math.min(100, score));
  const verdict = score >= 50 ? "强烈看多" : score >= 20 ? "看多" : score > -20 ? "中性" : score > -50 ? "看空" : "强烈看空";
  const bull = signals.filter((s) => s.verdict === "看多" || s.verdict === "超卖").length;
  const bear = signals.filter((s) => s.verdict === "看空" || s.verdict === "超买").length;
  const summary = `综合技术面【${verdict}】(评分 ${score})。看多 ${bull} 项、看空 ${bear} 项。仅供信息参考,非投资建议。`;

  return {
    price, score, verdict, summary, signals,
    indicators: {
      sma50, sma200, rsi14, macd: macdV, macd_signal: macdS, bb_upper: bbUp, bb_lower: bbLo,
      return_1m_pct: pctReturn(closes, 21), return_3m_pct: pctReturn(closes, 63),
      high_52w: closes.length ? Math.max(...closes.slice(-252)) : null,
      low_52w: closes.length ? Math.min(...closes.slice(-252)) : null,
    },
  };
}
