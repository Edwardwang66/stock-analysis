"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getQuote, type Quote } from "@/lib/datasource";
import { nameOf } from "@/lib/markets";

// 卡片只取报价(轻量),避免每张卡都抓历史 K线 把公共代理打到限流。
// 技术分析/缠论放在个股详情页。
export default function QuoteCard({ symbol }: { symbol: string }) {
  const [q, setQ] = useState<Quote | null>(null);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const quote = await getQuote(symbol);
        if (alive) setQ(quote);
      } catch (e: any) {
        if (alive) setErr(e?.message || "加载失败");
      }
    })();
    return () => { alive = false; };
  }, [symbol]);

  const dir = q && q.changePct != null ? (q.changePct >= 0 ? "up" : "down") : "muted";
  return (
    <Link href={`/symbol/?s=${encodeURIComponent(symbol)}`}>
      <div className="card">
        <div className="sym">{nameOf(symbol)}</div>
        <div className="src">{symbol}</div>
        {err ? <div className="err" style={{ fontSize: 12 }}>{err}</div> : q ? (
          <>
            <div className={`price ${dir}`}>{q.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
            <div className={dir}>
              {q.changePct != null ? `${q.changePct >= 0 ? "+" : ""}${q.changePct.toFixed(2)}%` : "—"}
              <span className="muted"> {q.currency}</span>
            </div>
            <div className="src" style={{ marginTop: 8 }}>来源 {q.source} · 点击看分析 →</div>
          </>
        ) : <div className="loading">加载中…</div>}
      </div>
    </Link>
  );
}
