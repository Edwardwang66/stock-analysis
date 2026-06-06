"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Chart from "@/components/Chart";
import { getOHLCV, getQuote, type Bar, type Quote } from "@/lib/datasource";
import { analyze, type Analysis } from "@/lib/analysis";
import { nameOf } from "@/lib/markets";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";

const RANGES = ["3mo", "6mo", "1y", "2y", "5y"];

function fmt(n: number | null | undefined, d = 2): string {
  return n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: d });
}

function SymbolView() {
  const params = useSearchParams();
  const symbol = (params.get("s") || "US:AAPL").toUpperCase();
  const [range, setRange] = useState("1y");
  const [bars, setBars] = useState<Bar[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [an, setAn] = useState<Analysis | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [starred, setStarred] = useState(false);

  useEffect(() => { setStarred(inWatchlist(symbol)); }, [symbol]);

  useEffect(() => {
    let alive = true;
    setLoading(true); setErr("");
    (async () => {
      try {
        const [b, q] = await Promise.all([getOHLCV(symbol, range), getQuote(symbol)]);
        if (!alive) return;
        setBars(b); setQuote(q); setAn(analyze(b)); setLoading(false);
      } catch (e: any) {
        if (alive) { setErr(e?.message || "加载失败"); setLoading(false); }
      }
    })();
    return () => { alive = false; };
  }, [symbol, range]);

  const dir = quote && quote.changePct != null ? (quote.changePct >= 0 ? "up" : "down") : "muted";
  const ind = an?.indicators ?? {};

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>{nameOf(symbol)}</h1>
        <span className="muted">{symbol}</span>
        <button className="btn" style={{ background: starred ? "var(--accent)" : "transparent", border: "1px solid var(--border)" }}
          onClick={() => { toggleWatchlist(symbol); setStarred(inWatchlist(symbol)); }}>
          {starred ? "★ 已自选" : "☆ 加入自选"}
        </button>
        {quote && (
          <>
            <span className={`price ${dir}`} style={{ fontSize: 22 }}>{fmt(quote.price)}</span>
            <span className={dir}>{quote.changePct != null ? `${quote.changePct >= 0 ? "+" : ""}${quote.changePct.toFixed(2)}%` : ""}</span>
            <span className="muted">{quote.currency} · 来源 {quote.source}</span>
          </>
        )}
      </div>

      {err && <div className="err">加载失败:{err}(美股经公共 CORS 代理,偶发不稳定,可刷新重试或配置后端 NEXT_PUBLIC_API_BASE)</div>}

      <div className="section">
        <div className="ranges">
          {RANGES.map((r) => (
            <button key={r} className={r === range ? "active" : ""} onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>
        {loading ? <div className="loading">加载中…</div> : <Chart bars={bars} />}
      </div>

      {an && (
        <>
          <div className="section">
            <h2>技术分析结论(规则化,非 LLM)</h2>
            <p><span className="badge" style={{ fontSize: 14 }}>{an.verdict}</span> <span className="muted">评分 {an.score} / [-100, 100]</span></p>
            <p style={{ color: "var(--muted)", fontSize: 13 }}>{an.summary}</p>
            <div className="signal-list">
              {an.signals.map((s, i) => (
                <div className="signal" key={i}>
                  <span>{s.name}</span>
                  <span><span className="badge">{s.verdict}</span> <span className="muted" style={{ fontSize: 12 }}>{s.detail}</span></span>
                </div>
              ))}
            </div>
          </div>

          {ind.high_52w != null && ind.low_52w != null && quote?.price != null && (
            <div className="section">
              <h2>52 周区间位置</h2>
              <div className="range52">
                <div className="range52-fill" style={{
                  width: `${Math.max(0, Math.min(100, ((quote.price - ind.low_52w) / (ind.high_52w - ind.low_52w)) * 100))}%`,
                }} />
              </div>
              <div className="range52-labels">
                <span>低 {fmt(ind.low_52w)}</span>
                <span className="muted">当前 {fmt(quote.price)}</span>
                <span>高 {fmt(ind.high_52w)}</span>
              </div>
            </div>
          )}

          <div className="section">
            <h2>关键指标</h2>
            <table>
              <tbody>
                <tr><th>MA50</th><td>{fmt(ind.sma50)}</td><th>MA200</th><td>{fmt(ind.sma200)}</td></tr>
                <tr><th>RSI(14)</th><td>{fmt(ind.rsi14, 1)}</td><th>MACD</th><td>{fmt(ind.macd, 3)}</td></tr>
                <tr><th>布林上轨</th><td>{fmt(ind.bb_upper)}</td><th>布林下轨</th><td>{fmt(ind.bb_lower)}</td></tr>
                <tr><th>近1月%</th><td>{fmt(ind.return_1m_pct)}</td><th>近3月%</th><td>{fmt(ind.return_3m_pct)}</td></tr>
                <tr><th>52周高</th><td>{fmt(ind.high_52w)}</td><th>52周低</th><td>{fmt(ind.low_52w)}</td></tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="disclaimer">本页分析为规则化技术指标,<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。</div>
    </div>
  );
}

export default function SymbolPage() {
  return (
    <Suspense fallback={<div className="container"><div className="loading">加载中…</div></div>}>
      <SymbolView />
    </Suspense>
  );
}
