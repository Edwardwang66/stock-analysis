// 筹码分布(成本分布)—— 对标富途「筹码分布 / 获利比例 / 支撑位·压力位」。
//
// 方法论:券商筹码分布基于真实持仓换手「移动」筹码;免费行情无持仓数据,
// 这里用历史日 K 估算 *成交量在价格上的堆积*:
//   · 每根 K 线把成交量在 [low, high] 区间内均匀摊到价格桶
//   · 时间衰减(越近权重越高),近似换手对筹码的稀释
//   · 获利比例 = 当前价之下(成本低于现价)的筹码占比
//   · 支撑位 = 现价之下最大的筹码峰;压力位 = 现价之上最大的筹码峰
// 为估算参考,非真实持仓成本。

import type { Bar } from "./datasource";

export interface ChipLevel { price: number; volume: number; profit: boolean }
export interface ChipDist {
  levels: ChipLevel[];          // 价格从低到高的筹码柱
  price: number;                // 现价
  profitRatio: number;          // 获利比例 0..1
  avgCost: number;              // 平均成本
  support: number | null;       // 支撑位(下方筹码峰)
  resistance: number | null;    // 压力位(上方筹码峰)
  conc90: { low: number; high: number }; // 90% 成本集中区间
  note: string;
}

export function computeChips(bars: Bar[], price: number, nBins = 60, halfLife = 60): ChipDist | null {
  const data = bars.filter((b) => b.high > 0 && b.low > 0 && b.volume > 0);
  if (data.length < 10 || !(price > 0)) return null;

  const lo = Math.min(...data.map((b) => b.low));
  const hi = Math.max(...data.map((b) => b.high));
  if (!(hi > lo)) return null;
  const step = (hi - lo) / nBins;
  const bins = new Array(nBins).fill(0);

  // 时间衰减:最近一根权重 1,越往前按半衰期衰减
  const decay = Math.pow(0.5, 1 / Math.max(1, halfLife));
  const n = data.length;
  for (let i = 0; i < n; i++) {
    const b = data[i];
    const w = Math.pow(decay, n - 1 - i);
    const vol = b.volume * w;
    const a = Math.max(0, Math.floor((b.low - lo) / step));
    const z = Math.min(nBins - 1, Math.floor((b.high - lo) / step));
    const span = z - a + 1;
    const per = vol / span;
    for (let k = a; k <= z; k++) bins[k] += per;
  }

  const total = bins.reduce((s, v) => s + v, 0) || 1;
  const levels: ChipLevel[] = bins.map((v, i) => {
    const p = lo + (i + 0.5) * step;
    return { price: p, volume: v, profit: p <= price };
  });

  const profitRatio = levels.filter((l) => l.profit).reduce((s, l) => s + l.volume, 0) / total;
  const avgCost = levels.reduce((s, l) => s + l.price * l.volume, 0) / total;

  // 支撑/压力:现价上下各自的最大筹码峰
  let support: number | null = null, resistance: number | null = null, sV = 0, rV = 0;
  for (const l of levels) {
    if (l.price < price && l.volume > sV) { sV = l.volume; support = l.price; }
    if (l.price > price && l.volume > rV) { rV = l.volume; resistance = l.price; }
  }

  // 90% 成本集中区间(去掉两端各 5% 筹码)
  const sortedByPrice = [...levels].sort((a, b) => a.price - b.price);
  const lowCut = total * 0.05, highCut = total * 0.95;
  let acc = 0, cLow = sortedByPrice[0].price, cHigh = sortedByPrice[sortedByPrice.length - 1].price;
  for (const l of sortedByPrice) {
    const before = acc; acc += l.volume;
    if (before < lowCut && acc >= lowCut) cLow = l.price;
    if (before < highCut && acc >= highCut) { cHigh = l.price; break; }
  }

  const note =
    profitRatio >= 0.7 ? "高获利盘,上方抛压偏重,留意获利了结。"
      : profitRatio <= 0.2 ? "深度套牢盘,上方套牢需化解,反弹易遇压。"
        : "获利与套牢盘相对均衡。";

  return { levels, price, profitRatio, avgCost, support, resistance, conc90: { low: cLow, high: cHigh }, note };
}
