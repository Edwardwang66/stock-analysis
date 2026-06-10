// 实时价推送层。
// 加密:Binance 公共行情 WebSocket(data-stream.binance.vision,无 key、浏览器可连),
//       miniTicker 每 ~1s 推一次 —— 真·实时跳动。
// 股票:免费源无 WS(且交易所行情本身延迟 15min 上下),由调用方用短轮询兜底。

import type { Quote } from "./datasource";

const WS_BASE = "wss://data-stream.binance.vision";

export type LiveHandler = (q: Quote) => void;

interface Sub { symbols: string[]; ws: WebSocket | null; handlers: Set<LiveHandler>; closed: boolean }

function toQuote(d: any): Quote | null {
  // miniTicker 字段:s=symbol c=close o=open24h h=high l=low
  const c = parseFloat(d?.c), o = parseFloat(d?.o);
  if (!isFinite(c)) return null;
  const change = isFinite(o) ? c - o : null;
  return {
    symbol: `CRYPTO:${d.s}`,
    price: c,
    change,
    changePct: change != null && o ? (change / o) * 100 : null,
    high: isFinite(parseFloat(d.h)) ? parseFloat(d.h) : null,
    low: isFinite(parseFloat(d.l)) ? parseFloat(d.l) : null,
    currency: "USDT",
    source: "Binance·实时",
  };
}

/**
 * 订阅一组加密标的的实时推送(非加密符号自动忽略)。
 * 返回退订函数。断线 3s 自动重连;页面隐藏时挂起(省电),恢复可见自动重连。
 */
export function subscribeCryptoLive(symbols: string[], onQuote: LiveHandler): () => void {
  const codes = symbols
    .filter((s) => s.toUpperCase().startsWith("CRYPTO:"))
    .map((s) => s.split(":")[1].toLowerCase());
  if (!codes.length || typeof WebSocket === "undefined") return () => {};

  const sub: Sub = { symbols: codes, ws: null, handlers: new Set([onQuote]), closed: false };
  let retry: ReturnType<typeof setTimeout> | null = null;

  const connect = () => {
    if (sub.closed || document.hidden) return;
    const streams = codes.map((c) => `${c}@miniTicker`).join("/");
    const url = codes.length === 1 ? `${WS_BASE}/ws/${streams}` : `${WS_BASE}/stream?streams=${streams}`;
    try {
      const ws = new WebSocket(url);
      sub.ws = ws;
      ws.onmessage = (ev) => {
        try {
          const j = JSON.parse(ev.data);
          const d = j?.data ?? j; // combined stream 包一层 {stream, data}
          const q = toQuote(d);
          if (q) sub.handlers.forEach((h) => h(q));
        } catch { /* ignore malformed */ }
      };
      ws.onclose = () => { if (!sub.closed) retry = setTimeout(connect, 3000); };
      ws.onerror = () => { try { ws.close(); } catch { /* ignore */ } };
    } catch { retry = setTimeout(connect, 3000); }
  };

  const onVis = () => {
    if (document.hidden) { try { sub.ws?.close(); } catch { /* ignore */ } }
    else if (!sub.ws || sub.ws.readyState >= WebSocket.CLOSING) connect();
  };
  document.addEventListener("visibilitychange", onVis);
  connect();

  return () => {
    sub.closed = true;
    document.removeEventListener("visibilitychange", onVis);
    if (retry) clearTimeout(retry);
    try { sub.ws?.close(); } catch { /* ignore */ }
  };
}
