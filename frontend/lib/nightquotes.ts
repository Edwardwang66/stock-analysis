"use client";
// 🌙 HIP-3 夜盘报价层:美股非交易时段,用 Hyperliquid 永续(24/7)补全全站看板。
// 实证背书(Cycle8 研究):合成美股永续 vs 正股 corr 0.965、方向命中 96%、SP500→SPY 0.981。
// 口径:chg24h 为 24 小时滚动涨跌(非「相对昨收」);「隐含跳空」= mark/正股最新价 − 1。
// 映射原则:个股可直接映射(US:XXX / SK海力士);指数点位口径不同,只在专门 UI 展示,不冒充正股价。
import { useEffect, useState } from "react";
import { getCryptoState, type CryptoState, type HlAsset } from "./feed";
import { marketStatus } from "./marketstatus";

export interface NightQuote {
  mark: number; chg24h: number | null; fundingApr: number | null;
  volUsd: number | null; hlSymbol: string;
}
export interface NightBoard {
  /** 本站 symbol → 夜盘永续(仅个股/可直映射 ETF) */
  map: Record<string, NightQuote>;
  /** 指数永续(SP500/USTECH/MAG7 等,独立口径) */
  indices: HlAsset[];
  updatedAt: string | null;
  /** 美股当前是否处于非交易时段(夜盘层是否激活) */
  usClosed: boolean;
}

const EMPTY: NightBoard = { map: {}, indices: [], updatedAt: null, usClosed: false };

// HL 符号 → 本站 symbol;null = 不映射(口径不同或合成无对应)
function localOf(hlSym: string): string | null {
  if (hlSym === "SKHX") return "KR:000660";
  if (hlSym === "SPCX" || hlSym === "DRAM") return null; // 合成/指数,无正股对应
  return `US:${hlSym}`;
}

// 模块级共享缓存(全站所有组件共用一次取数;3 分钟刷新,单飞防并发)
let _cache: { data: CryptoState | null; ts: number } = { data: null, ts: 0 };
let _inflight: Promise<CryptoState | null> | null = null;
const TTL = 180_000;

async function fetchShared(): Promise<CryptoState | null> {
  if (Date.now() - _cache.ts < TTL && _cache.data) return _cache.data;
  if (!_inflight) {
    _inflight = getCryptoState()
      .then((d) => { _cache = { data: d, ts: Date.now() }; return d; })
      .finally(() => { _inflight = null; });
  }
  return _inflight;
}

function build(d: CryptoState | null): Omit<NightBoard, "usClosed"> {
  if (!d?.equity_perps) return { map: {}, indices: [], updatedAt: d?.updated_at ?? null };
  const map: Record<string, NightQuote> = {};
  for (const x of d.equity_perps.stocks ?? []) {
    const local = localOf(x.symbol);
    if (!local || x.mark == null) continue;
    map[local] = { mark: x.mark, chg24h: x.chg24h ?? null, fundingApr: x.funding_apr ?? null,
                   volUsd: x.vol24h_usd ?? null, hlSymbol: x.symbol };
  }
  return { map, indices: d.equity_perps.indices ?? [], updatedAt: d.updated_at ?? null };
}

/** 全站夜盘 hook:美股闭市时 map 才有意义;开市时各处应展示正股实价。 */
export function useNightQuotes(): NightBoard {
  const [board, setBoard] = useState<NightBoard>(EMPTY);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      const usClosed = !marketStatus("US").open;
      const d = await fetchShared();
      if (alive) setBoard({ ...build(d), usClosed });
    };
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 60_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);
  return board;
}
