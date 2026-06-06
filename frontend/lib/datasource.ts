// 客户端数据源(可在 GitHub Pages 静态站点中直接运行,无需后端、无需 API key)。
//
// 优先级:若配置了 NEXT_PUBLIC_API_BASE(指向 FastAPI 后端)则走后端;
// 否则浏览器直连已验证可用的公开 API:
//   暗号 -> data-api.binance.vision(无地域限制、CORS OK)
//   美股 -> Yahoo Finance chart 经 corsproxy.io(浏览器跨域)
//
// ⚠️ 免费源仅供演示/自用;商用对外须换授权源(见 docs/compliance.md)。

export interface Bar { time: number; open: number; high: number; low: number; close: number; volume: number }
export interface Quote {
  symbol: string; price: number; change: number | null; changePct: number | null;
  high: number | null; low: number | null; currency: string; source: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

// 多个公共 CORS 代理,依次回退以提升美股(Yahoo)稳定性。
// 2026-06 实测:allorigins 最稳;corsproxy.io 已改为落地页不可用,放最后兜底。
const CORS_PROXIES: ((u: string) => string)[] = [
  (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
  (u) => `https://api.codetabs.com/v1/proxy/?quest=${u}`,
  (u) => `https://thingproxy.freeboard.io/fetch/${u}`,
  (u) => `https://corsproxy.io/?url=${encodeURIComponent(u)}`,
];

// 通用:经公共 CORS 代理取 JSON(给无 CORS 的源用,如 Yahoo search / SEC ticker 映射)。
export async function fetchViaProxy(url: string): Promise<any> {
  let lastErr: any;
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetch(proxy(url));
      if (!r.ok) { lastErr = new Error(`proxy HTTP ${r.status}`); continue; }
      const j = await r.json();
      if (j) return j;
    } catch (e) { lastErr = e; }
  }
  throw new Error(`代理全部失败:${lastErr?.message || lastErr}`);
}

export function parseSymbol(s: string): { market: string; code: string } {
  const [market, code] = s.split(":");
  return { market: (market || "").toUpperCase(), code: (code || "").toUpperCase() };
}

// ---- Binance (crypto) ----
const BINANCE = "https://data-api.binance.vision";
const B_INTERVAL: Record<string, string> = {
  "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "1d": "1d", "1wk": "1w",
};
// 不同周期下取的根数(配合 range 控制时间跨度)
const B_LIMIT: Record<string, number> = { "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1000 };

async function binanceQuote(code: string): Promise<Quote> {
  const r = await fetch(`${BINANCE}/api/v3/ticker/24hr?symbol=${code}`);
  const d = await r.json();
  return {
    symbol: `CRYPTO:${code}`, price: +d.lastPrice, change: +d.priceChange, changePct: +d.priceChangePercent,
    high: +d.highPrice, low: +d.lowPrice, currency: "USDT", source: "Binance",
  };
}
async function binanceOHLCV(code: string, range: string, interval: string): Promise<Bar[]> {
  const bi = B_INTERVAL[interval] ?? "1d";
  const intraday = ["1m", "5m", "15m", "30m", "1h"].includes(interval);
  const limit = intraday ? 500 : B_LIMIT[range] ?? 365;
  const r = await fetch(`${BINANCE}/api/v3/klines?symbol=${code}&interval=${bi}&limit=${limit}`);
  const d: any[] = await r.json();
  return d.map((k) => ({ time: Math.floor(k[0] / 1000), open: +k[1], high: +k[2], low: +k[3], close: +k[4], volume: +k[5] }));
}

// ---- Yahoo (US/HK/CN) via CORS proxy ----
const Y_RANGE: Record<string, string> = {
  "1d": "1d", "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y",
};
function yahooCode(market: string, code: string): string {
  if (market === "US") return code;
  if (market === "HK") return `${code.padStart(4, "0")}.HK`;
  if (market === "CN") return code.startsWith("6") ? `${code}.SS` : `${code}.SZ`;
  return code;
}
const Y_INTERVAL: Record<string, string> = {
  "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d", "1wk": "1wk",
};
// Yahoo 对分钟线有跨度上限:1m≤7d、5m/15m/30m≤60d、60m≤730d
const Y_INTRADAY_MAX: Record<string, string> = { "1m": "5d", "5m": "1mo", "15m": "1mo", "30m": "3mo", "1h": "3mo" };
const _RANGE_DAYS: Record<string, number> = { "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825 };
async function yahooChart(ycode: string, range: string, interval: string): Promise<any> {
  // 分钟/小时线 Yahoo 限制跨度,range 上限收窄
  const cap = Y_INTRADAY_MAX[interval];
  const yr = cap
    ? ((_RANGE_DAYS[range] ?? 999) <= (_RANGE_DAYS[cap] ?? 0) ? (Y_RANGE[range] ?? cap) : cap)
    : (Y_RANGE[range] ?? "1y");
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ycode}?range=${yr}&interval=${Y_INTERVAL[interval] ?? "1d"}`;
  let lastErr: any;
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetch(proxy(url));
      if (!r.ok) { lastErr = new Error(`proxy HTTP ${r.status}`); continue; }
      const j = await r.json();
      const res = j?.chart?.result?.[0];
      if (res) return res;
      lastErr = new Error("no chart data");
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(`Yahoo 全部代理失败:${lastErr?.message || lastErr}`);
}
async function yahooQuote(market: string, code: string): Promise<Quote> {
  const res = await yahooChart(yahooCode(market, code), "5d", "1d");
  const m = res.meta;
  const prev = m.chartPreviousClose ?? m.previousClose;
  const change = m.regularMarketPrice != null && prev != null ? m.regularMarketPrice - prev : null;
  return {
    symbol: `${market}:${code}`, price: m.regularMarketPrice, change,
    changePct: change != null && prev ? (change / prev) * 100 : null,
    high: m.regularMarketDayHigh ?? null, low: m.regularMarketDayLow ?? null,
    currency: m.currency ?? "", source: "Yahoo",
  };
}
async function yahooOHLCV(market: string, code: string, range: string, interval: string): Promise<Bar[]> {
  const res = await yahooChart(yahooCode(market, code), range, interval);
  const ts: number[] = res.timestamp ?? [];
  const q = res.indicators.quote[0];
  const bars: Bar[] = [];
  for (let i = 0; i < ts.length; i++) {
    if ([q.open[i], q.high[i], q.low[i], q.close[i]].some((x) => x == null)) continue;
    bars.push({ time: ts[i], open: q.open[i], high: q.high[i], low: q.low[i], close: q.close[i], volume: q.volume?.[i] ?? 0 });
  }
  return bars;
}

// ---- 统一入口 ----
export async function getQuote(symbol: string): Promise<Quote> {
  if (API_BASE) {
    const r = await fetch(`${API_BASE}/api/v1/quotes?symbols=${encodeURIComponent(symbol)}`);
    const d = (await r.json())[0];
    return { symbol: d.symbol, price: d.price, change: d.change, changePct: d.change_pct, high: d.high, low: d.low, currency: d.currency, source: d.source };
  }
  const { market, code } = parseSymbol(symbol);
  return market === "CRYPTO" ? binanceQuote(code) : yahooQuote(market, code);
}

export async function getOHLCV(symbol: string, range = "1y", interval = "1d"): Promise<Bar[]> {
  if (API_BASE) {
    const r = await fetch(`${API_BASE}/api/v1/ohlcv?symbol=${encodeURIComponent(symbol)}&range=${range}&interval=${interval}`);
    const d = await r.json();
    return d.bars.map((b: any) => ({ time: Math.floor(new Date(b.ts).getTime() / 1000), open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume }));
  }
  const { market, code } = parseSymbol(symbol);
  return market === "CRYPTO" ? binanceOHLCV(code, range, interval) : yahooOHLCV(market, code, range, interval);
}

// 分钟级 K 线(资金流向 / 主力资金估算用)。interval ∈ 1m/5m/15m/30m/1h。
export async function getIntraday(symbol: string, interval = "5m", range = "1d"): Promise<Bar[]> {
  if (API_BASE) {
    const r = await fetch(`${API_BASE}/api/v1/ohlcv?symbol=${encodeURIComponent(symbol)}&range=${range}&interval=${interval}`);
    const d = await r.json();
    return d.bars.map((b: any) => ({ time: Math.floor(new Date(b.ts).getTime() / 1000), open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume }));
  }
  const { market, code } = parseSymbol(symbol);
  return market === "CRYPTO" ? binanceOHLCV(code, range, interval) : yahooOHLCV(market, code, range, interval);
}
