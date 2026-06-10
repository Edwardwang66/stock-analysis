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
/** 是否配置了后端(决定股票是否走公共代理;供 UI 提示用)。 */
export const HAS_BACKEND = Boolean(API_BASE);
const QUOTE_CACHE_MS = 30_000;          // 股票:盘中报价新鲜期
const CRYPTO_CACHE_MS = 8_000;          // 加密:直连免费,可以更"实时"
function quoteTtl(symbol: string): number {
  return symbol.startsWith("CRYPTO:") ? CRYPTO_CACHE_MS : QUOTE_CACHE_MS;
}
const quoteCache = new Map<string, { quote: Quote; expires: number }>();
const quoteInflight = new Map<string, Promise<Quote>>();

// ---- localStorage 持久缓存:刷新/重开页面先用上次数据渲染(秒开),再后台更新 ----
// v3:清洗 v2 时代被 5d-窗口 bug 污染的涨跌幅缓存
const LS_QUOTES = "ds:q:v3";
const LS_BARS_PREFIX = "ds:b:v2:";
const LS_BARS_INDEX = "ds:bidx:v2";
const QUOTE_STALE_MAX_MS = 10 * 60_000;   // 超过 10 分钟的旧报价不再用于首屏
const BARS_STALE_MAX_MS = 24 * 3600_000;  // K线断网降级上限
const MAX_BAR_SERIES = 30;

function lsRead<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try { const s = localStorage.getItem(key); return s ? (JSON.parse(s) as T) : null; } catch { return null; }
}
function lsWrite(key: string, v: unknown): void {
  if (typeof window === "undefined") return;
  try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* 配额满等忽略 */ }
}

type StoredQuotes = Record<string, { q: Quote; at: number }>;
let storedQuotes: StoredQuotes | null = null;
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function getStoredQuotes(): StoredQuotes {
  if (storedQuotes === null) storedQuotes = lsRead<StoredQuotes>(LS_QUOTES) ?? {};
  return storedQuotes;
}
function persistQuotes(quotes: Quote[]): void {
  if (!quotes.length) return;
  const store = getStoredQuotes();
  const now = Date.now();
  for (const q of quotes) store[q.symbol] = { q, at: now };
  // 清掉太老的,防 localStorage 膨胀
  for (const k of Object.keys(store)) if (now - store[k].at > BARS_STALE_MAX_MS) delete store[k];
  if (flushTimer) clearTimeout(flushTimer);
  flushTimer = setTimeout(() => lsWrite(LS_QUOTES, store), 300);
}

/** 同步取"上次会话留下的报价"用于首屏即时渲染;不发网络请求。 */
export function getCachedQuotesSync(symbols: string[]): Record<string, Quote> {
  const out: Record<string, Quote> = {};
  const now = Date.now();
  const store = getStoredQuotes();
  for (const raw of symbols) {
    const s = raw.trim().toUpperCase();
    const mem = quoteCache.get(s);
    if (mem && mem.expires > now) { out[s] = mem.quote; continue; }
    const item = store[s];
    if (item && now - item.at <= QUOTE_STALE_MAX_MS) out[s] = item.q;
  }
  return out;
}

// K线 localStorage:新鲜期内直接复用(切 range/interval 来回、刷新页面都秒回)
function barsFreshMs(interval: string): number {
  return ["1m", "5m", "15m", "30m", "1h"].includes(interval) ? 60_000 : 300_000;
}
function barsKey(symbol: string, range: string, interval: string): string {
  return `${LS_BARS_PREFIX}${symbol}:${range}:${interval}`;
}
function readBarsCache(key: string): { bars: Bar[]; at: number } | null {
  return lsRead<{ bars: Bar[]; at: number }>(key);
}
function writeBarsCache(key: string, bars: Bar[]): void {
  lsWrite(key, { bars, at: Date.now() });
  const idx = lsRead<Record<string, number>>(LS_BARS_INDEX) ?? {};
  idx[key] = Date.now();
  const keys = Object.keys(idx);
  if (keys.length > MAX_BAR_SERIES) {
    keys.sort((a, b) => idx[a] - idx[b]);
    for (const k of keys.slice(0, keys.length - MAX_BAR_SERIES)) {
      try { localStorage.removeItem(k); } catch { /* ignore */ }
      delete idx[k];
    }
  }
  lsWrite(LS_BARS_INDEX, idx);
}

// 多个公共 CORS 代理,依次回退以提升美股(Yahoo)稳定性。
// 2026-06 实测:allorigins 最稳;corsproxy.io 已改为落地页不可用,放最后兜底。
const CORS_PROXIES: ((u: string) => string)[] = [
  (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
  (u) => `https://api.codetabs.com/v1/proxy/?quest=${u}`,
  (u) => `https://thingproxy.freeboard.io/fetch/${u}`,
  (u) => `https://corsproxy.io/?url=${encodeURIComponent(u)}`,
];

// 带超时的 fetch:公共代理常卡 10-20s,8s 未返回即放弃换下一个,避免整页无限转。
export async function fetchT(url: string, ms = 8000): Promise<Response> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

// 通用:经公共 CORS 代理取纯文本(XML/RSS 等非 JSON 源)。
export async function fetchTextViaProxy(url: string): Promise<string> {
  let lastErr: any;
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetchT(proxy(url));
      if (!r.ok) { lastErr = new Error(`proxy HTTP ${r.status}`); continue; }
      const t = await r.text();
      if (t && t.length > 50) return t;
      lastErr = new Error("empty body");
    } catch (e) { lastErr = e; }
  }
  throw new Error(`代理全部失败:${lastErr?.message || lastErr}`);
}

// 通用:经公共 CORS 代理取 JSON(给无 CORS 的源用,如 Yahoo search / SEC ticker 映射)。
export async function fetchViaProxy(url: string): Promise<any> {
  let lastErr: any;
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetchT(proxy(url));
      if (!r.ok) { lastErr = new Error(`proxy HTTP ${r.status}`); continue; }
      const j = await r.json();
      if (j) return j;
    } catch (e) { lastErr = e; }
  }
  throw new Error(`代理全部失败:${lastErr?.message || lastErr}`);
}

// 健壮的后端 JSON 请求:容忍 Render 免费实例冷启动(首请求可能 30-50s,或先回 502 错误页)。
// 检查 r.ok + JSON 可解析;失败按延迟重试(等后端唤醒);超时给足 60s。
// 返回 null 表示后端确实拿不到 —— 调用方应回退到浏览器直连路径。
async function backendJson(path: string, retries = 2): Promise<any | null> {
  for (let i = 0; i <= retries; i++) {
    try {
      const r = await fetchT(`${API_BASE}${path}`, 60000);
      if (r.ok) {
        const text = await r.text();
        try { return JSON.parse(text); } catch { /* 非 JSON(冷启动错误页),重试 */ }
      }
    } catch { /* 网络/超时,重试 */ }
    if (i < retries) await new Promise((res) => setTimeout(res, 3000)); // 等冷启动唤醒
  }
  return null;
}

/** 后端健康状态(未配置后端返回 null;配置了但拿不到返回 {ok:false})。 */
export async function getBackendHealth(): Promise<any | null> {
  if (!API_BASE) return null;
  const h = await backendJson("/api/v1/health", 0);
  return h ?? { ok: false };
}

// ---- 盘中机器快照(live 分支)作为免代理报价缓存 ----
// Winter 循环/Actions 每 5 分钟产出全池快照;6 分钟内视为可用。模块级 60s 记忆防重复拉取。
interface LiveSnap { data: Record<string, { price: number; pct: number | null; high: number | null; low: number | null }>; ageMin: number }
let liveSnapCache: { snap: LiveSnap | null; at: number } | null = null;
let liveSnapInflight: Promise<LiveSnap | null> | null = null;

async function getLiveSnapshot(): Promise<LiveSnap | null> {
  const now = Date.now();
  if (liveSnapCache && now - liveSnapCache.at < 60_000) return liveSnapCache.snap;
  if (liveSnapInflight) return liveSnapInflight;
  liveSnapInflight = (async () => {
    try {
      const r = await fetchT(`https://raw.githubusercontent.com/edwardwang66/stock-analysis/live/feed/intraday/latest.json?t=${now}`, 6000);
      if (!r.ok) return null;
      const j = await r.json();
      const ageMs = now - new Date(j.at).getTime();
      if (!isFinite(ageMs) || ageMs > 6 * 60_000) return null; // 过期快照不用(收盘后走常规路径)
      const snap: LiveSnap = { data: j.snapshot ?? {}, ageMin: Math.max(1, Math.round(ageMs / 60_000)) };
      return snap;
    } catch {
      return null;
    } finally {
      setTimeout(() => { liveSnapInflight = null; }, 0);
    }
  })();
  const snap = await liveSnapInflight;
  liveSnapCache = { snap, at: now };
  return snap;
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
  if (market === "US" || market === "IDX") return code; // IDX: Yahoo 代码原样直传(^GSPC / 000001.SS)
  if (market === "HK") return `${code.padStart(4, "0")}.HK`;
  if (market === "CN") return code.startsWith("6") ? `${code}.SS` : `${code}.SZ`;
  if (market === "JP") return `${code}.T`;    // 东证
  if (market === "KR") return `${code}.KS`;   // KOSPI(KOSDAQ 标的可直接写 KR:xxxxxx.KQ)
  if (market === "DE") return `${code}.DE`;   // XETRA
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
      const r = await fetchT(proxy(url));
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
  // ⚠️ range 必须 1d:chartPreviousClose 的语义是「请求窗口前一根的收盘」,
  // 用 5d 会算成对 5 天前的涨跌幅(曾导致 AAPL 显示 -7.82% 实为 -3.64%)。
  const res = await yahooChart(yahooCode(market, code), "1d", "1d");
  const m = res.meta;
  const prev = m.regularMarketPreviousClose ?? m.chartPreviousClose ?? m.previousClose;
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
async function fetchQuote(symbol: string): Promise<Quote> {
  // IDX(指数)后端 router 不识别,直接走浏览器 Yahoo 路径
  if (API_BASE && !symbol.startsWith("IDX:")) {
    const arr = await backendJson(`/api/v1/quotes?symbols=${encodeURIComponent(symbol)}`);
    const d = Array.isArray(arr) ? arr[0] : null;
    if (d && !d.error && d.price != null) {
      return { symbol: d.symbol, price: d.price, change: d.change, changePct: d.change_pct, high: d.high, low: d.low, currency: d.currency, source: d.source };
    }
    // 后端不可用/无数据 → 落浏览器直连
  }
  const { market, code } = parseSymbol(symbol);
  return market === "CRYPTO" ? binanceQuote(code) : yahooQuote(market, code);
}

/**
 * 批量取报价。onPartial:每拿到一个报价立刻回调(渐进式渲染,快源先上屏,
 * 不必等最慢的公共代理),最终仍 resolve 完整 map。
 */
export async function getQuotes(
  symbols: string[],
  onPartial?: (quote: Quote) => void,
): Promise<Record<string, Quote>> {
  const unique = Array.from(new Set(symbols.map((s) => s.trim().toUpperCase()).filter(Boolean)));
  const now = Date.now();
  const out: Record<string, Quote> = {};
  const missing: string[] = [];

  const persisted = getStoredQuotes();
  for (const symbol of unique) {
    const cached = quoteCache.get(symbol);
    if (cached && cached.expires > now) { out[symbol] = cached.quote; onPartial?.(cached.quote); continue; }
    // L2:上次会话 30s 内的报价同样视为新鲜(硬刷新后不重复拉)
    const p = persisted[symbol];
    if (p && now - p.at <= quoteTtl(symbol)) {
      out[symbol] = p.q;
      quoteCache.set(symbol, { quote: p.q, expires: p.at + quoteTtl(symbol) });
      onPartial?.(p.q);
      continue;
    }
    missing.push(symbol);
  }

  const backendable = missing.filter((s) => !s.startsWith("IDX:")); // 指数不发后端,避免整批 422
  if (API_BASE && backendable.length >= 1) {
    // 后端单次上限 50 个标的 → 分块并发,任何一块失败不影响其他块
    const chunks: string[][] = [];
    for (let i = 0; i < backendable.length; i += 50) chunks.push(backendable.slice(i, i + 50));
    const results = await Promise.all(
      chunks.map((c) => backendJson(`/api/v1/quotes?symbols=${encodeURIComponent(c.join(","))}`)),
    );
    for (const rows of results) {
      for (const d of Array.isArray(rows) ? rows : []) {
        if (d.error || d.price == null) continue;
        const quote = {
          symbol: d.symbol, price: d.price, change: d.change, changePct: d.change_pct,
          high: d.high, low: d.low, currency: d.currency, source: d.source,
        };
        quoteCache.set(quote.symbol, { quote, expires: now + quoteTtl(quote.symbol) });
        out[quote.symbol] = quote;
        onPartial?.(quote);
      }
    }
  }

  // 快路径②:盘中机器快照(live 分支,≤6 分钟新鲜)——免代理拿到池内股票报价。
  // 这是无后端模式的源头提速:Winter/Actions 每 5 分钟算好,前端一次 fetch 全拿。
  const stillMissing = missing.filter((s) => !out[s] && !s.startsWith("CRYPTO:"));
  if (stillMissing.length >= 3) {
    try {
      const snap = await getLiveSnapshot();
      if (snap) {
        for (const symbol of stillMissing) {
          const v = snap.data[symbol];
          if (!v || v.price == null) continue;
          const prev = v.pct != null ? v.price / (1 + v.pct / 100) : null;
          const quote: Quote = {
            symbol, price: v.price,
            change: prev != null ? v.price - prev : null, changePct: v.pct,
            high: v.high, low: v.low, currency: "", source: `快照(${snap.ageMin}分钟)`,
          };
          quoteCache.set(symbol, { quote, expires: Date.now() + 60_000 });
          out[symbol] = quote;
          onPartial?.(quote);
        }
      }
    } catch { /* 快照不可用则继续走代理 */ }
  }

  // 批量没拿到的(后端冷启动/出错)逐个回退:加密走直连必成,股票尝试代理
  await Promise.all(missing.filter((s) => !out[s]).map(async (symbol) => {
    let req = quoteInflight.get(symbol);
    if (!req) {
      req = fetchQuote(symbol).finally(() => quoteInflight.delete(symbol));
      quoteInflight.set(symbol, req);
    }
    try {
      const quote = await req;
      quoteCache.set(symbol, { quote, expires: Date.now() + quoteTtl(symbol) });
      out[symbol] = quote;
      onPartial?.(quote);
    } catch {
      // 网络全挂:有 10 分钟内的旧值就降级展示,好过空白
      const p = persisted[symbol];
      if (p && Date.now() - p.at <= QUOTE_STALE_MAX_MS) { out[symbol] = p.q; onPartial?.(p.q); }
    }
  }));
  persistQuotes(Object.values(out));
  return out;
}

export async function getQuote(symbol: string): Promise<Quote> {
  const normalized = symbol.trim().toUpperCase();
  const quotes = await getQuotes([normalized]);
  if (!quotes[normalized]) throw new Error(`无法获取 ${normalized} 行情`);
  return quotes[normalized];
}

function barsFromBackend(d: any): Bar[] | null {
  if (!d || !Array.isArray(d.bars)) return null;
  return d.bars.map((b: any) => ({ time: Math.floor(new Date(b.ts).getTime() / 1000), open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume }));
}

async function fetchBars(symbol: string, range: string, interval: string): Promise<Bar[]> {
  if (API_BASE && !symbol.startsWith("IDX:")) {
    const bars = barsFromBackend(await backendJson(`/api/v1/ohlcv?symbol=${encodeURIComponent(symbol)}&range=${range}&interval=${interval}`));
    if (bars) return bars;
    // 后端不可用 → 落浏览器直连
  }
  const { market, code } = parseSymbol(symbol);
  return market === "CRYPTO" ? binanceOHLCV(code, range, interval) : yahooOHLCV(market, code, range, interval);
}

// K线统一入口:新鲜期内 localStorage 直出(切周期/刷新秒回);
// 网络全挂时 24h 内旧数据降级,好过空图。
async function cachedBars(symbol: string, range: string, interval: string): Promise<Bar[]> {
  const key = barsKey(symbol, range, interval);
  const hit = readBarsCache(key);
  const now = Date.now();
  if (hit && now - hit.at <= barsFreshMs(interval) && hit.bars.length) return hit.bars;
  try {
    const bars = await fetchBars(symbol, range, interval);
    if (bars.length) writeBarsCache(key, bars);
    return bars;
  } catch (e) {
    if (hit && now - hit.at <= BARS_STALE_MAX_MS && hit.bars.length) return hit.bars;
    throw e;
  }
}

export async function getOHLCV(symbol: string, range = "1y", interval = "1d"): Promise<Bar[]> {
  return cachedBars(symbol.trim().toUpperCase(), range, interval);
}

// 分钟级 K 线(资金流向 / 主力资金估算用)。interval ∈ 1m/5m/15m/30m/1h。
export async function getIntraday(symbol: string, interval = "5m", range = "1d"): Promise<Bar[]> {
  return cachedBars(symbol.trim().toUpperCase(), range, interval);
}

// ---- 美股盘前/盘后(扩展时段)----
// Yahoo chart includePrePost=true:用扩展时段最后一根 1m bar 当前价。
// 盘前涨跌基准 = 昨收;盘后基准 = 当日常规收盘。免费源无「夜盘」(Blue Ocean 为付费通道)。
export interface ExtendedQuote {
  session: "盘前" | "盘后";
  price: number;
  change: number;
  changePct: number;
  at: number; // 秒级时间戳
}

export async function getExtendedQuote(symbol: string): Promise<ExtendedQuote | null> {
  const { market, code } = parseSymbol(symbol.trim().toUpperCase());
  if (market !== "US") return null; // 免费源仅美股有可靠扩展时段
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${code}?range=1d&interval=1m&includePrePost=true`;
  let res: any = null;
  for (const proxy of CORS_PROXIES) {
    try {
      const r = await fetchT(proxy(url));
      if (!r.ok) continue;
      const j = await r.json();
      res = j?.chart?.result?.[0];
      if (res) break;
    } catch { /* 换下一个代理 */ }
  }
  if (!res) return null;
  const m = res.meta ?? {};
  const ctp = m.currentTradingPeriod;
  const ts: number[] = res.timestamp ?? [];
  const closes: (number | null)[] = res.indicators?.quote?.[0]?.close ?? [];
  let i = ts.length - 1;
  while (i >= 0 && closes[i] == null) i--;
  if (i < 0 || !ctp?.regular) return null;
  const t = ts[i], price = closes[i] as number;
  let session: "盘前" | "盘后";
  let base: number | null;
  if (ctp.post && t >= ctp.post.start) {
    session = "盘后";
    base = m.regularMarketPrice ?? null;
  } else if (ctp.pre && t < ctp.regular.start) {
    session = "盘前";
    base = m.regularMarketPreviousClose ?? m.chartPreviousClose ?? m.previousClose ?? null;
  } else {
    return null; // 常规时段内无需扩展报价
  }
  if (base == null || !isFinite(base) || base === 0) return null;
  const change = price - base;
  return { session, price, change, changePct: (change / base) * 100, at: t };
}
