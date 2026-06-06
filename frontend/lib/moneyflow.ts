// 资金流向 / 主力资金(估算)—— 对标富途「资金流向」看板。
//
// ⚠️ 方法论与诚实声明:
//   富途等券商的「特大/大/中/小单」与「主力资金」基于 Level-2 *逐笔成交* 数据,
//   按每一笔成交金额分档、按主动买/卖盘方向(内外盘)累计。免费公开行情(Yahoo/Binance)
//   不提供逐笔与买卖盘方向,因此本模块用 **分钟 K 线** 做透明的代理估算:
//     · 单根 K 线的成交额  amt = 典型价(H+L+C)/3 × 成交量
//     · 方向:收盘 vs 上一根收盘(涨→流入 / 跌→流出),近似「内外盘」
//     · 按单根成交额的分位数分档:小单 < P55 < 中单 < P80 < 大单 < P95 < 特大单
//     · 主力资金 = 特大单 + 大单 的净额
//   这是趋势性参考,非真实主力逐笔。要还原券商口径需接入 LV2 逐笔(见 docs/compliance.md)。

import type { Bar } from "./datasource";

export type BucketName = "特大单" | "大单" | "中单" | "小单";
export interface FlowBucket { name: BucketName; inflow: number; outflow: number; net: number }
export interface FlowPoint { time: number; cumAll: number; cumMain: number }

export interface MoneyFlow {
  inflow: number;          // 总流入
  outflow: number;         // 总流出
  net: number;             // 净流入(>0 流入 / <0 流出)
  buckets: FlowBucket[];   // 特大/大/中/小
  mainInflow: number;      // 主力流入(特大+大)
  mainOutflow: number;
  mainNet: number;         // 主力净额 —— 「主力资金在哪里」的核心
  series: FlowPoint[];     // 累计净流入时间序列(整体 / 主力)
  bars: number;            // 参与计算的 K 线数
  note: string;
}

const EMPTY: MoneyFlow = {
  inflow: 0, outflow: 0, net: 0, mainInflow: 0, mainOutflow: 0, mainNet: 0,
  buckets: [
    { name: "特大单", inflow: 0, outflow: 0, net: 0 },
    { name: "大单", inflow: 0, outflow: 0, net: 0 },
    { name: "中单", inflow: 0, outflow: 0, net: 0 },
    { name: "小单", inflow: 0, outflow: 0, net: 0 },
  ],
  series: [], bars: 0, note: "数据不足,无法估算资金流向。",
};

function quantile(sorted: number[], p: number): number {
  if (!sorted.length) return 0;
  return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
}

export function computeMoneyFlow(bars: Bar[]): MoneyFlow {
  if (bars.length < 4) return EMPTY;

  // 单根成交额
  const amt = bars.map((b) => ((b.high + b.low + b.close) / 3) * (b.volume || 0));
  const sorted = amt.filter((x) => x > 0).sort((a, b) => a - b);
  // 分档阈值(按成交额分位数,自适应不同标的的量级)
  const tSmall = quantile(sorted, 0.55);
  const tMed = quantile(sorted, 0.8);
  const tLarge = quantile(sorted, 0.95);

  const buckets: Record<BucketName, FlowBucket> = {
    特大单: { name: "特大单", inflow: 0, outflow: 0, net: 0 },
    大单: { name: "大单", inflow: 0, outflow: 0, net: 0 },
    中单: { name: "中单", inflow: 0, outflow: 0, net: 0 },
    小单: { name: "小单", inflow: 0, outflow: 0, net: 0 },
  };

  const series: FlowPoint[] = [];
  let cumAll = 0, cumMain = 0;

  for (let i = 0; i < bars.length; i++) {
    const a = amt[i];
    if (a <= 0) { series.push({ time: bars[i].time, cumAll, cumMain }); continue; }
    // 方向:收盘 vs 上一根收盘(首根用 收盘 vs 开盘)
    const ref = i > 0 ? bars[i - 1].close : bars[i].open;
    const sign = bars[i].close > ref ? 1 : bars[i].close < ref ? -1 : 0;
    if (sign === 0) { series.push({ time: bars[i].time, cumAll, cumMain }); continue; }

    const bk = a > tLarge ? buckets.特大单 : a > tMed ? buckets.大单 : a > tSmall ? buckets.中单 : buckets.小单;
    if (sign > 0) bk.inflow += a; else bk.outflow += a;

    const signed = sign * a;
    cumAll += signed;
    if (bk === buckets.特大单 || bk === buckets.大单) cumMain += signed;
    series.push({ time: bars[i].time, cumAll, cumMain });
  }

  const list = [buckets.特大单, buckets.大单, buckets.中单, buckets.小单];
  list.forEach((b) => { b.net = b.inflow - b.outflow; });

  const inflow = list.reduce((s, b) => s + b.inflow, 0);
  const outflow = list.reduce((s, b) => s + b.outflow, 0);
  const mainInflow = buckets.特大单.inflow + buckets.大单.inflow;
  const mainOutflow = buckets.特大单.outflow + buckets.大单.outflow;
  const mainNet = mainInflow - mainOutflow;
  const net = inflow - outflow;

  const where =
    mainNet > 0
      ? `主力资金净流入,${buckets.特大单.net >= 0 ? "特大单" : "大单"}主导,资金在「进场」。`
      : mainNet < 0
        ? `主力资金净流出,${buckets.特大单.net <= 0 ? "特大单" : "大单"}主导,资金在「撤离」。`
        : "主力资金基本均衡。";

  return {
    inflow, outflow, net, buckets: list, mainInflow, mainOutflow, mainNet, series,
    bars: bars.length, note: where,
  };
}

// 金额格式化:对标富途,自动用「亿 / 万」缩放(保留货币无关的纯数值口径)。
export function fmtAmount(v: number): string {
  const a = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (a >= 1e8) return `${sign}${(a / 1e8).toFixed(2)}亿`;
  if (a >= 1e4) return `${sign}${(a / 1e4).toFixed(2)}万`;
  return `${sign}${a.toFixed(0)}`;
}
