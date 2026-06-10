"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { type Quote } from "@/lib/datasource";
import { marketOf, nameOf } from "@/lib/markets";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";

// 纯展示组件:报价一律由父级统一拉取下发(单一数据源,卡片间/看板间不会出现
// 各自拉取导致的数值漂移)。技术分析/缠论放在个股详情页。
export default function QuoteCard({
  symbol,
  quote = null,
  error = "",
  loading = false,
}: {
  symbol: string;
  quote?: Quote | null;
  error?: string;
  loading?: boolean;
}) {
  const q = quote;
  const isCrypto = marketOf(symbol) === "CRYPTO";
  const dir = q && q.changePct != null ? (q.changePct >= 0 ? "up" : "down") : "muted";
  const [starred, setStarred] = useState(false);
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
        <div className="sym">{nameOf(symbol)}</div>
        <div className="src">{symbol}</div>
        {q ? (
          <>
            <div className={`price ${dir}`}>{q.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
            <div className={dir}>
              {q.changePct != null ? `${q.changePct >= 0 ? "+" : ""}${q.changePct.toFixed(2)}%` : "—"}
              {q.changePct != null && <span className="muted" style={{ fontSize: 11 }}>{isCrypto ? " 24h" : " 当日"}</span>}
              <span className="muted"> {q.currency}</span>
            </div>
            <div className="src" style={{ marginTop: 8 }}>来源 {q.source} · 点击看分析 →</div>
          </>
        ) : error ? (
          <div className="err" style={{ fontSize: 12 }}>{error}</div>
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
