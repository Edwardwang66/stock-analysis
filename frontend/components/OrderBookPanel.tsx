"use client";
// Hyperliquid 式盘口面板:订单簿(深度条) + 最近成交 tape。
// 仅加密标的渲染 —— Binance 公共 WebSocket 有真实 L2 与逐笔;
// 股票免费源无深度数据,宁缺毋假(不用 K 线估算冒充盘口)。
import { useEffect, useRef, useState } from "react";

interface Level { p: number; q: number }
interface Trade { p: number; q: number; t: number; buy: boolean; id: number }

const WS_BASE = "wss://data-stream.binance.vision";
const DEPTH_ROWS = 11;

function fmtP(p: number): string {
  return p.toLocaleString(undefined, { maximumFractionDigits: p < 1 ? 6 : p < 100 ? 4 : 2 });
}
function fmtQ(q: number): string {
  if (q >= 1000) return q.toFixed(0);
  if (q >= 1) return q.toFixed(3);
  return q.toFixed(5);
}

export default function OrderBookPanel({ symbol }: { symbol: string }) {
  const code = symbol.startsWith("CRYPTO:") ? symbol.split(":")[1].toLowerCase() : null;
  const [tab, setTab] = useState<"book" | "trades">("book");
  const [bids, setBids] = useState<Level[]>([]);
  const [asks, setAsks] = useState<Level[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    if (!code || typeof WebSocket === "undefined") return;
    setBids([]); setAsks([]); setTrades([]);
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const connect = () => {
      if (closed || document.hidden) return;
      ws = new WebSocket(`${WS_BASE}/stream?streams=${code}@depth20@1000ms/${code}@aggTrade`);
      ws.onmessage = (ev) => {
        try {
          const { stream, data } = JSON.parse(ev.data);
          if (typeof stream === "string" && stream.endsWith("@aggTrade")) {
            const t: Trade = { p: +data.p, q: +data.q, t: data.T, buy: !data.m, id: data.a };
            lastPrice.current = t.p;
            setTrades((prev) => [t, ...prev].slice(0, 40));
          } else if (data?.bids && data?.asks) {
            setBids((data.bids as string[][]).slice(0, DEPTH_ROWS).map(([p, q]) => ({ p: +p, q: +q })));
            setAsks((data.asks as string[][]).slice(0, DEPTH_ROWS).map(([p, q]) => ({ p: +p, q: +q })));
          }
        } catch { /* ignore malformed */ }
      };
      ws.onclose = () => { if (!closed) retry = setTimeout(connect, 3000); };
      ws.onerror = () => { try { ws?.close(); } catch { /* ignore */ } };
    };
    const onVis = () => {
      if (document.hidden) { try { ws?.close(); } catch { /* ignore */ } }
      else if (!ws || ws.readyState >= WebSocket.CLOSING) connect();
    };
    document.addEventListener("visibilitychange", onVis);
    connect();
    return () => {
      closed = true;
      document.removeEventListener("visibilitychange", onVis);
      if (retry) clearTimeout(retry);
      try { ws?.close(); } catch { /* ignore */ }
    };
  }, [code]);

  if (!code) return null;

  const bestBid = bids[0]?.p, bestAsk = asks[0]?.p;
  const spread = bestBid != null && bestAsk != null ? bestAsk - bestBid : null;
  // 深度条宽度:按本侧累计量占两侧最大累计量的比例
  const cum = (ls: Level[]) => { let s = 0; return ls.map((l) => ({ ...l, c: (s += l.q) })); };
  const cb = cum(bids), ca = cum(asks);
  const maxCum = Math.max(cb[cb.length - 1]?.c ?? 0, ca[ca.length - 1]?.c ?? 0) || 1;
  const bidSum = cb[cb.length - 1]?.c ?? 0, askSum = ca[ca.length - 1]?.c ?? 0;
  const bidRatio = bidSum + askSum > 0 ? (bidSum / (bidSum + askSum)) * 100 : 50;

  return (
    <div className="obpanel">
      <div className="ob-tabs">
        <button className={tab === "book" ? "active" : ""} onClick={() => setTab("book")}>盘口</button>
        <button className={tab === "trades" ? "active" : ""} onClick={() => setTab("trades")}>成交</button>
        <span className="src" title="Binance 公共 WebSocket,真实 L2 深度与逐笔成交">实时</span>
      </div>
      {tab === "book" ? (
        <>
          <div className="ob-ratio" title={`买盘占比 ${bidRatio.toFixed(0)}%(挂单量加总)`}>
            <span className="ob-ratio-bid" style={{ width: `${bidRatio}%` }} />
          </div>
          <div className="ob-list">
            {[...ca].reverse().map((l) => (
              <div key={`a${l.p}`} className="ob-row"
                style={{ background: `linear-gradient(to left, rgba(239,83,80,.14) ${(l.c / maxCum) * 100}%, transparent 0)` }}>
                <span className="down">{fmtP(l.p)}</span><span>{fmtQ(l.q)}</span>
              </div>
            ))}
            <div className="ob-spread" title="买一卖一价差">
              {spread != null ? <>价差 {fmtP(spread)}{bestBid ? ` (${((spread / bestBid) * 100).toFixed(3)}%)` : ""}</> : "连接中…"}
            </div>
            {cb.map((l) => (
              <div key={`b${l.p}`} className="ob-row"
                style={{ background: `linear-gradient(to left, rgba(38,166,154,.14) ${(l.c / maxCum) * 100}%, transparent 0)` }}>
                <span className="up">{fmtP(l.p)}</span><span>{fmtQ(l.q)}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="ob-list">
          <div className="ob-row ob-head"><span>价格</span><span>数量</span><span>时间</span></div>
          {trades.map((t) => (
            <div key={t.id} className="ob-row ob-trade">
              <span className={t.buy ? "up" : "down"}>{fmtP(t.p)}</span>
              <span>{fmtQ(t.q)}</span>
              <span className="muted">{new Date(t.t).toLocaleTimeString("zh-CN", { hour12: false })}</span>
            </div>
          ))}
          {!trades.length && <div className="ob-spread">等待成交…</div>}
        </div>
      )}
    </div>
  );
}
