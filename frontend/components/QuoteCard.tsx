"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getOHLCV, getQuote, type Quote } from "@/lib/datasource";
import { analyze } from "@/lib/analysis";
import { nameOf } from "@/lib/markets";

export default function QuoteCard({ symbol }: { symbol: string }) {
  const [q, setQ] = useState<Quote | null>(null);
  const [verdict, setVerdict] = useState<string>("");
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const quote = await getQuote(symbol);
        if (alive) setQ(quote);
        const bars = await getOHLCV(symbol, "1y");
        if (alive) setVerdict(analyze(bars).verdict);
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
            <div style={{ marginTop: 8 }}>
              {verdict ? <span className="badge">{verdict}</span> : <span className="src">分析中…</span>}
            </div>
            <div className="src" style={{ marginTop: 6 }}>来源 {q.source}</div>
          </>
        ) : <div className="loading">加载中…</div>}
      </div>
    </Link>
  );
}
