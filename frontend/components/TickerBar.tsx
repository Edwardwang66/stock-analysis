"use client";
// 全站常驻自选行情条(交互参考 Hyperliquid 顶部 favorites bar):
// 自选标的实时价一条横排,任何页面可见,点击直达个股页。
// 加密走 Binance WebSocket 实时推送;股票随统一缓存层轮询。自选为空时退化显示主要指数。
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { getCachedQuotesSync, getQuotes, type Quote } from "@/lib/datasource";
import { subscribeCryptoLive } from "@/lib/livePrice";
import { getWatchlist } from "@/lib/watchlist";
import { INDEX_SYMBOLS, nameOf } from "@/lib/markets";
import { useLang } from "@/lib/names";

const FALLBACK = [...INDEX_SYMBOLS.slice(0, 5), "CRYPTO:BTCUSDT"];
const MAX_ITEMS = 30;

export default function TickerBar() {
  const lang = useLang();
  const [symbols, setSymbols] = useState<string[]>([]);
  const [isFallback, setIsFallback] = useState(false);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const flashRef = useRef<Record<string, { dir: "up" | "down"; at: number }>>({});
  const prevPrice = useRef<Record<string, number>>({});

  // 自选列表(挂载后读取,跟随 watchlist-changed 实时同步)
  useEffect(() => {
    const sync = () => {
      const wl = getWatchlist();
      setIsFallback(!wl.length);
      setSymbols(wl.length ? wl.slice(0, MAX_ITEMS) : FALLBACK);
    };
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, []);

  // 行情:缓存秒出 → 15s 轮询;加密叠加 WebSocket 实时跳动
  useEffect(() => {
    if (!symbols.length) return;
    let alive = true;
    const apply = (q: Quote) => {
      if (!alive) return;
      const prev = prevPrice.current[q.symbol];
      if (prev != null && q.price !== prev) {
        flashRef.current[q.symbol] = { dir: q.price > prev ? "up" : "down", at: Date.now() };
      }
      prevPrice.current[q.symbol] = q.price;
      setQuotes((m) => ({ ...m, [q.symbol]: q }));
    };
    setQuotes(getCachedQuotesSync(symbols));
    const load = () => { if (!document.hidden) getQuotes(symbols, apply).catch(() => {}); };
    load();
    const id = window.setInterval(load, 15_000);
    const unsub = subscribeCryptoLive(symbols, apply);
    return () => { alive = false; window.clearInterval(id); unsub(); };
  }, [symbols]);

  if (!symbols.length) return null;
  return (
    <nav className="tickerbar" aria-label="自选行情条">
      <span className="tb-label" title={isFallback ? "把标的加入自选(个股页 ☆)后,这里会常驻显示你的自选" : "自选标的实时行情,点击直达个股页"}>
        {isFallback ? "指数" : "★ 自选"}
      </span>
      <div className="tb-scroll">
        {symbols.map((s) => {
          const q = quotes[s];
          const pct = q?.changePct;
          const dir = pct == null ? "" : pct >= 0 ? "up" : "down";
          const fl = flashRef.current[s];
          const flashing = fl && Date.now() - fl.at < 900;
          return (
            <Link key={s} href={`/symbol/?s=${encodeURIComponent(s)}`} className="tb-item" title={s}>
              <span className="tb-name">{nameOf(s, lang)}</span>
              {q ? (
                <span key={fl?.at ?? 0} className={flashing ? (fl.dir === "up" ? "flash-up" : "flash-down") : ""}>
                  <span className="tb-price">{q.price.toLocaleString(undefined, { maximumFractionDigits: q.price < 10 ? 4 : 2 })}</span>
                  {pct != null && <span className={`tb-pct ${dir}`}> {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%</span>}
                </span>
              ) : (
                <span className="tb-price muted">…</span>
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
