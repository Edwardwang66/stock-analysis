// 暗号(Binance 公开镜像)真实逐笔 + 盘口 —— 无 key、CORS OK。
//   · aggTrades:真实逐笔成交,带 isBuyerMaker(主动买/卖方向)→ 真·主力资金
//   · depth:真实买卖盘口(委买/委卖)→ 真·买卖盘比
// 这是免费源里少数能拿到「真实逐笔/盘口」的市场,股票侧无此数据(需券商 LV2)。

import { flowFromTrades, type MoneyFlow } from "./moneyflow";

const BINANCE = "https://data-api.binance.vision";

export interface OrderBook {
  bids: [number, number][];   // [价, 量]
  asks: [number, number][];
  bidVol: number;             // 委买总量
  askVol: number;             // 委卖总量
  bidPct: number;             // 买盘占比 0..1(对标富途「买盘 xx%」)
  spread: number;             // 买一卖一价差
}

export async function getOrderBook(code: string, limit = 20): Promise<OrderBook> {
  const r = await fetch(`${BINANCE}/api/v3/depth?symbol=${code}&limit=${limit}`);
  const d = await r.json();
  const bids: [number, number][] = (d.bids || []).map((x: string[]) => [+x[0], +x[1]]);
  const asks: [number, number][] = (d.asks || []).map((x: string[]) => [+x[0], +x[1]]);
  const bidVol = bids.reduce((s, b) => s + b[1], 0);
  const askVol = asks.reduce((s, a) => s + a[1], 0);
  const spread = asks.length && bids.length ? asks[0][0] - bids[0][0] : 0;
  return { bids, asks, bidVol, askVol, bidPct: bidVol / (bidVol + askVol || 1), spread };
}

// 真实主力资金:取最近 N 笔聚合逐笔,按成交额分档(特大/大/中/小),
// isBuyerMaker=false→主动买入(流入)、true→主动卖出(流出)。
export async function getCryptoFlow(code: string, limit = 1000): Promise<MoneyFlow> {
  const r = await fetch(`${BINANCE}/api/v3/aggTrades?symbol=${code}&limit=${limit}`);
  const d: any[] = await r.json();
  const trades = d.map((t) => ({
    amt: +t.p * +t.q,          // 成交额(计价币)
    buy: t.m === false,        // m=isBuyerMaker;false=买方为吃单方=主动买
    time: Math.floor(t.T / 1000),
  }));
  return flowFromTrades(trades, true);
}
