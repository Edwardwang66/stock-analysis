"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import QuoteCard from "@/components/QuoteCard";
import Heatmap from "@/components/Heatmap";
import SearchBox from "@/components/SearchBox";
import { getCachedQuotesSync, getQuotes, type Quote } from "@/lib/datasource";
import { MARKETS, symbolsForTab } from "@/lib/markets";
import { getWatchlist } from "@/lib/watchlist";

type SortMode = "default" | "gainers" | "losers";

export default function Home() {
  const [tab, setTab] = useState("CRYPTO");
  const [watch, setWatch] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote | null>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingQuotes, setLoadingQuotes] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshId, setRefreshId] = useState(0);
  const [sortMode, setSortMode] = useState<SortMode>("default");

  useEffect(() => {
    const sync = () => setWatch(getWatchlist());
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, []);

  const baseSymbols = useMemo(() => symbolsForTab(tab), [tab]);
  const allVisibleSymbols = useMemo(
    () => Array.from(new Set([...watch, ...baseSymbols])),
    [baseSymbols, watch],
  );

  useEffect(() => {
    if (!allVisibleSymbols.length) return;
    let alive = true;
    // 先用上次会话的缓存即时渲染(秒开),再后台拉新
    const cached = getCachedQuotesSync(allVisibleSymbols);
    if (Object.keys(cached).length) setQuotes((prev) => ({ ...cached, ...prev }));
    setLoadingQuotes(true);
    setErrors({});
    (async () => {
      try {
        const next = await getQuotes(allVisibleSymbols);
        if (!alive) return;
        setQuotes((prev) => ({ ...prev, ...next }));
        setErrors(Object.fromEntries(
          allVisibleSymbols.filter((s) => !next[s] && !cached[s]).map((s) => [s, "暂时无数据"]),
        ));
        setLastUpdated(new Date());
      } finally {
        if (alive) setLoadingQuotes(false);
      }
    })();
    return () => { alive = false; };
  }, [allVisibleSymbols, refreshId]);

  // 30s 自动刷新;页面隐藏时暂停,回到前台立即补一次
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) setRefreshId((x) => x + 1);
    }, 30_000);
    const onVis = () => { if (!document.hidden) setRefreshId((x) => x + 1); };
    document.addEventListener("visibilitychange", onVis);
    return () => { window.clearInterval(id); document.removeEventListener("visibilitychange", onVis); };
  }, []);

  const symbols = useMemo(() => {
    const arr = [...baseSymbols];
    if (sortMode === "gainers") {
      return arr.sort((a, b) => (quotes[b]?.changePct ?? -Infinity) - (quotes[a]?.changePct ?? -Infinity));
    }
    if (sortMode === "losers") {
      return arr.sort((a, b) => (quotes[a]?.changePct ?? Infinity) - (quotes[b]?.changePct ?? Infinity));
    }
    return arr;
  }, [baseSymbols, quotes, sortMode]);

  const marketStats = useMemo(() => {
    const rows = symbols.map((s) => quotes[s]).filter((x): x is Quote => Boolean(x));
    const gainers = rows.filter((x) => (x.changePct ?? 0) > 0).length;
    const losers = rows.filter((x) => (x.changePct ?? 0) < 0).length;
    const avg = rows.length ? rows.reduce((sum, x) => sum + (x.changePct ?? 0), 0) / rows.length : null;
    return { loaded: rows.length, total: symbols.length, gainers, losers, avg };
  }, [quotes, symbols]);

  return (
    <div className="container">
      <div className="header">
        <h1>📈 多市场股票数据看板</h1>
        <span className="tag">美股 · 港股 · A股 · 加密 · 实时行情 · 主力资金 · 非 LLM 技术分析</span>
        <Link href="/screener/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)", marginLeft: "auto" }}>📈 每日选股</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>🛰️ 情报看板</Link>
        <Link href="/sources/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>🔌 数据源</Link>
      </div>

      <div className="search"><SearchBox /></div>

      {tab !== "CRYPTO" && (
        <div className="hint">
          ⚠️ 美股 / 港股 / A股 当前经<strong>公共代理</strong>获取,代理不稳时可能较慢或失败(点「刷新行情」重试)。
          加密为直连,秒开。部署后端并设 <code>API_BASE</code> 后,股票也将免代理秒开。
        </div>
      )}

      <div className="toolbar">
        <div className="stat">
          <span>已加载 {marketStats.loaded}/{marketStats.total}</span>
          <span className="up">涨 {marketStats.gainers}</span>
          <span className="down">跌 {marketStats.losers}</span>
          <span>均值 {marketStats.avg == null ? "—" : `${marketStats.avg >= 0 ? "+" : ""}${marketStats.avg.toFixed(2)}%`}</span>
        </div>
        <div className="segmented">
          <button className={sortMode === "default" ? "active" : ""} onClick={() => setSortMode("default")}>默认</button>
          <button className={sortMode === "gainers" ? "active" : ""} onClick={() => setSortMode("gainers")}>强势</button>
          <button className={sortMode === "losers" ? "active" : ""} onClick={() => setSortMode("losers")}>弱势</button>
        </div>
        <button className="btn subtle" onClick={() => setRefreshId((x) => x + 1)} disabled={loadingQuotes}>
          {loadingQuotes ? "刷新中" : "刷新行情"}
        </button>
        {lastUpdated && <span className="src">更新 {lastUpdated.toLocaleTimeString()}</span>}
      </div>

      {watch.length > 0 && (
        <>
          <h2 className="block-title">⭐ 我的自选</h2>
          <div className="grid">{watch.map((s) => (
            <QuoteCard key={s} symbol={s} quote={quotes[s] ?? null} error={errors[s]} loading={loadingQuotes} />
          ))}</div>
        </>
      )}

      <div className="tabs">
        {MARKETS.map((m) => (
          <button key={m.key} className={m.key === tab ? "active" : ""} onClick={() => setTab(m.key)}>{m.label}</button>
        ))}
      </div>

      <h2 className="block-title">涨跌热力图</h2>
      <Heatmap symbols={symbols} quotes={quotes} loading={loadingQuotes && marketStats.loaded === 0} />

      <h2 className="block-title">行情卡片</h2>
      <div className="grid">{symbols.map((s) => (
        <QuoteCard key={s} symbol={s} quote={quotes[s] ?? null} error={errors[s]} loading={loadingQuotes} />
      ))}</div>

      <div className="disclaimer">
        数据来源:暗号 = Binance(data-api.binance.vision)· 美/港/A股 = Yahoo Finance(经公共 CORS 代理,自动多代理回退)。
        免费源仅供演示/自用,商用对外须更换授权数据源。
        本页所有分析为<strong>规则化技术指标 + 简化缠论(非投资建议 / Not financial advice)</strong>。
        缠论结构识别灵感来自 <a href="https://guanchaotv.com/" target="_blank" rel="noreferrer">观潮 TideView</a>(独立简化实现,非其代码)。
      </div>
    </div>
  );
}
