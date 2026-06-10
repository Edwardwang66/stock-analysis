// 规则化(非 LLM)技术分析,与 backend/app/analysis/signals.py 严格同口径(评分 v2)。
// v1 缺陷:正分只有 趋势20+排列15+MACD15=50,RSI/布林加分与趋势互斥 → 看多股全卡 50。
// v2:10 因子,强趋势+强动能+接近新高可拉开 50~90 区分度。口径见 routines/methodology.md。
import { atr, bollinger, kdj, last, macd, pctReturn, rsi, sma, volumeRatio } from "./indicators";
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
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  const volumes = bars.map((b) => b.volume);
  const price = closes.length ? closes[closes.length - 1] : null;
  const sma20 = last(sma(closes, 20));
  const sma50 = last(sma(closes, 50));
  const sma200 = last(sma(closes, 200));
  const rsi14 = last(rsi(closes, 14));
  const m = macd(closes);
  const macdV = last(m.line), macdS = last(m.sig);
  const bb = bollinger(closes, 20, 2);
  const bbUp = last(bb.up), bbLo = last(bb.lo);
  const kdjV = kdj(highs, lows, closes, 9);
  const ret1m = pctReturn(closes, 21);
  const hi52 = closes.length ? Math.max(...closes.slice(-252)) : null;
  const lo52 = closes.length ? Math.min(...closes.slice(-252)) : null;

  const signals: Signal[] = [];
  let score = 0;

  // 1) 趋势:价格 vs MA50(±20)
  if (price !== null && sma50 !== null) {
    if (price > sma50) { signals.push({ name: "趋势(MA50)", verdict: "看多", detail: `价格 ${price.toFixed(2)} 在 50 日均线 ${sma50.toFixed(2)} 上方` }); score += 20; }
    else { signals.push({ name: "趋势(MA50)", verdict: "看空", detail: `价格 ${price.toFixed(2)} 在 50 日均线 ${sma50.toFixed(2)} 下方` }); score -= 20; }
  }
  // 2) 长期排列:MA50 vs MA200(±15)
  if (sma50 !== null && sma200 !== null) {
    if (sma50 > sma200) { signals.push({ name: "MA50/MA200", verdict: "看多", detail: "多头排列(50>200)" }); score += 15; }
    else { signals.push({ name: "MA50/MA200", verdict: "看空", detail: "空头排列(50<200)" }); score -= 15; }
  }
  // 3) 短期动能:MA20 vs MA50(±10)
  if (sma20 !== null && sma50 !== null) {
    if (sma20 > sma50) { signals.push({ name: "MA20/MA50", verdict: "看多", detail: "短期均线在中期均线上方(动能向上)" }); score += 10; }
    else { signals.push({ name: "MA20/MA50", verdict: "看空", detail: "短期均线在中期均线下方(动能转弱)" }); score -= 10; }
  }
  // 4) RSI 分段
  if (rsi14 !== null) {
    if (rsi14 >= 80) { signals.push({ name: "RSI(14)", verdict: "超买", detail: `RSI ${rsi14.toFixed(1)} ≥ 80,显著过热` }); score -= 15; }
    else if (rsi14 >= 70) { signals.push({ name: "RSI(14)", verdict: "超买", detail: `RSI ${rsi14.toFixed(1)} ≥ 70` }); score -= 5; }
    else if (rsi14 >= 55) { signals.push({ name: "RSI(14)", verdict: "看多", detail: `RSI ${rsi14.toFixed(1)} 处 55-70 强势区` }); score += 10; }
    else if (rsi14 > 45) { signals.push({ name: "RSI(14)", verdict: "中性", detail: `RSI ${rsi14.toFixed(1)}` }); }
    else if (rsi14 > 30) { signals.push({ name: "RSI(14)", verdict: "看空", detail: `RSI ${rsi14.toFixed(1)} 处 30-45 弱势区` }); score -= 5; }
    else { signals.push({ name: "RSI(14)", verdict: "超卖", detail: `RSI ${rsi14.toFixed(1)} ≤ 30` }); score += 10; }
  }
  // 5) MACD vs 信号线(±10)+ 6) 零轴(±5)
  if (macdV !== null && macdS !== null) {
    if (macdV > macdS) { signals.push({ name: "MACD", verdict: "看多", detail: "MACD 在信号线上方" }); score += 10; }
    else { signals.push({ name: "MACD", verdict: "看空", detail: "MACD 在信号线下方" }); score -= 10; }
    if (macdV > 0) { signals.push({ name: "MACD零轴", verdict: "看多", detail: "DIF 在零轴上方(多头市场)" }); score += 5; }
    else { signals.push({ name: "MACD零轴", verdict: "看空", detail: "DIF 在零轴下方" }); score -= 5; }
  }
  // 7) 布林带(±5)
  if (price !== null && bbUp !== null && bbLo !== null) {
    if (price >= bbUp) { signals.push({ name: "布林带", verdict: "超买", detail: "触及上轨" }); score -= 5; }
    else if (price <= bbLo) { signals.push({ name: "布林带", verdict: "超卖", detail: "触及下轨" }); score += 5; }
    else signals.push({ name: "布林带", verdict: "中性", detail: "通道内" });
  }
  // 8) 52周接近度(需 ≥200 根)
  if (price !== null && hi52 !== null && closes.length >= 200 && hi52 > 0) {
    const near = price / hi52;
    if (near >= 0.95) { signals.push({ name: "52周位置", verdict: "看多", detail: `距 52 周高 ${((near - 1) * 100).toFixed(1)}%,接近新高(动量偏强)` }); score += 10; }
    else if (near >= 0.80) { signals.push({ name: "52周位置", verdict: "看多", detail: `区间上沿(距高点 ${((near - 1) * 100).toFixed(1)}%)` }); score += 5; }
    else if (near <= 0.60) { signals.push({ name: "52周位置", verdict: "看空", detail: `距 52 周高回撤 ${((1 - near) * 100).toFixed(0)}%` }); score -= 5; }
    else signals.push({ name: "52周位置", verdict: "中性", detail: `距 52 周高 ${((near - 1) * 100).toFixed(1)}%` });
  }
  // 9) 近1月动量(±5)
  if (ret1m !== null) {
    if (ret1m >= 8) { signals.push({ name: "1月动量", verdict: "看多", detail: `近 21 交易日 +${ret1m.toFixed(1)}%` }); score += 5; }
    else if (ret1m <= -8) { signals.push({ name: "1月动量", verdict: "看空", detail: `近 21 交易日 ${ret1m.toFixed(1)}%` }); score -= 5; }
  }
  // 10) 量价配合(±5):量比≥1.5(基期=前20根均量,与 backend 一致)
  if (volumes.length >= 21 && closes.length >= 2) {
    const baseVol = volumes.slice(-21, -1).reduce((s, x) => s + x, 0) / 20;
    if (baseVol > 0) {
      const vr = volumes[volumes.length - 1] / baseVol;
      if (vr >= 1.5) {
        if (closes[closes.length - 1] >= closes[closes.length - 2]) { signals.push({ name: "量价", verdict: "看多", detail: `量比 ${vr.toFixed(1)} 放量上涨` }); score += 5; }
        else { signals.push({ name: "量价", verdict: "看空", detail: `量比 ${vr.toFixed(1)} 放量下跌` }); score -= 5; }
      }
    }
  }

  score = Math.max(-100, Math.min(100, score));
  const verdict = score >= 50 ? "强烈看多" : score >= 20 ? "看多" : score > -20 ? "中性" : score > -50 ? "看空" : "强烈看空";
  const bull = signals.filter((s) => s.verdict === "看多" || s.verdict === "超卖").length;
  const bear = signals.filter((s) => s.verdict === "看空" || s.verdict === "超买").length;
  const summary = `综合技术面【${verdict}】(评分 ${score},v2 十因子)。看多 ${bull} 项、看空 ${bear} 项。仅供信息参考,非投资建议。`;

  return {
    price, score, verdict, summary, signals,
    indicators: {
      sma20, sma50, sma200, rsi14, macd: macdV, macd_signal: macdS, bb_upper: bbUp, bb_lower: bbLo,
      return_1m_pct: ret1m, return_3m_pct: pctReturn(closes, 63),
      high_52w: hi52, low_52w: lo52,
      // 展示型扩展指标(不参与评分)
      atr14: atr(highs, lows, closes, 14),
      kdj_k: kdjV.k, kdj_d: kdjV.d, kdj_j: kdjV.j,
      vol_ratio: volumeRatio(volumes, 20),
    },
  };
}
