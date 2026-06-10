"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { type Quote } from "@/lib/datasource";
import { marketOf, nameOf } from "@/lib/markets";
import { useLang } from "@/lib/names";
import { useNightQuotes } from "@/lib/nightquotes";
import { marketStatus } from "@/lib/marketstatus";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";

// 纯展示组件:报价一律由父级统一拉取下发(单一数据源,卡片间/看板间不会出现
// 各自拉取导致的数值漂移)。技术分析/缠论放在个股详情页。
export default function QuoteCard({
  symbol,
  quote = null,
  error = "",
  loading = false,
  onRetry,
  tag,
}: {
  symbol: string;
  quote?: Quote | null;
  error?: string;
  loading?: boolean;
  onRetry?: () => void;
  tag?: string;
}) {
  const lang = useLang();
  const night = useNightQuotes();
  const q = quote;
  const isCrypto = marketOf(symbol) === "CRYPTO";
  const dir = q && q.changePct != null ? (q.changePct >= 0 ? "up" : "down") : "muted";
  const [starred, setStarred] = useState(false);
  // 价格跳动闪烁:比上一次渲染高→绿闪,低→红闪
  const prevPrice = useRef<number | null>(null);
  const [flash, setFlash] = useState("");
  useEffect(() => {
    const p = q?.price ?? null;
    if (p != null && prevPrice.current != null && p !== prevPrice.current) {
      setFlash(p > prevPrice.current ? "flash-up" : "flash-down");
      const t = setTimeout(() => setFlash(""), 700);
      prevPrice.current = p;
      return () => clearTimeout(t);
    }
    prevPrice.current = p;
  }, [q?.price]);
  useEffect(() => {
    const sync = () => setStarred(inWatchlist(symbol));
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, [symbol]);
  return (
    <Link href={`/symbol/?s=${encodeURIComponent(symbol)}`}>
      <div className="card">
        <button
          className={`star ${starred ? "on" : ""}`}
          title={starred ? "移出自选" : "加入自选"}
          aria-label={starred ? "移出自选" : "加入自选"}
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleWatchlist(symbol); }}
        >{starred ? "★" : "☆"}</button>
        <div className="sym">{nameOf(symbol, lang)}{tag && <span className="badge" style={{ marginLeft: 6, fontSize: 10, padding: "1px 6px" }}>{tag}</span>}</div>
        <div className="src">{symbol}</div>
        {q ? (
          <>
            <div className={`price ${dir} ${flash}`}>{q.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
            <div className={dir}>
              {q.change != null && `${q.change >= 0 ? "+" : ""}${q.change.toLocaleString(undefined, { maximumFractionDigits: 2 })} `}
              {q.changePct != null ? `${q.changePct >= 0 ? "+" : ""}${q.changePct.toFixed(2)}%` : "—"}
              {q.changePct != null && <span className="muted" style={{ fontSize: 11 }}>{isCrypto ? " 24h" : " 当日"}</span>}
              <span className="muted"> {q.currency}</span>
            </div>
            {(q.high != null || q.low != null) && (
              <div className="src" style={{ marginTop: 4 }}>
                最高 {q.high?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"} · 最低 {q.low?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "—"}
              </div>
            )}
            {(() => {
              const nq = night.map[symbol] && !marketStatus(marketOf(symbol)).open ? night.map[symbol] : null;
              if (!nq) return null;
              const gap = q.price ? (nq.mark / q.price - 1) * 100 : null;
              return (
                <div className="src" style={{ marginTop: 4 }}>
                  🌙 夜盘 <span style={{ color: "var(--text)" }}>{nq.mark.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  {nq.chg24h != null && <span className={nq.chg24h >= 0 ? "up" : "down"}> {nq.chg24h >= 0 ? "+" : ""}{(nq.chg24h * 100).toFixed(2)}%<span className="muted" style={{ fontSize: 10 }}>24h</span></span>}
                  {gap != null && Math.abs(gap) >= 0.3 && <span className={gap >= 0 ? "up" : "down"}> · 隐含{gap >= 0 ? "高开" : "低开"} {Math.abs(gap).toFixed(1)}%</span>}
                </div>
              );
            })()}
            <div className="src" style={{ marginTop: 6 }}>来源 {q.source} · 点击看分析 →</div>
          </>
        ) : error ? (
          <div className="err" style={{ fontSize: 12 }}>
            {error}
            {onRetry && (
              <button className="retry" onClick={(e) => { e.preventDefault(); e.stopPropagation(); onRetry(); }}>重试</button>
            )}
          </div>
        ) : loading ? (
          <div aria-busy="true">
            <div className="skeleton" style={{ width: "60%", height: 26, marginTop: 6 }} />
            <div className="skeleton" style={{ width: "40%", height: 14, marginTop: 8 }} />
            <div className="skeleton" style={{ width: "75%", height: 10, marginTop: 12 }} />
          </div>
        ) : (
          <div className="src" style={{ marginTop: 8 }}>等待数据…</div>
        )}
      </div>
    </Link>
  );
}
