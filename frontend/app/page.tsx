"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import QuoteCard from "@/components/QuoteCard";
import Heatmap from "@/components/Heatmap";
import SearchBox from "@/components/SearchBox";
import { MARKETS, symbolsForTab } from "@/lib/markets";
import { getWatchlist } from "@/lib/watchlist";

export default function Home() {
  const [tab, setTab] = useState("ALL");
  const [watch, setWatch] = useState<string[]>([]);

  useEffect(() => {
    const sync = () => setWatch(getWatchlist());
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, []);

  const symbols = symbolsForTab(tab);

  return (
    <div className="container">
      <div className="header">
        <h1>📈 多市场股票数据看板</h1>
        <span className="tag">美股 · 港股 · A股 · 加密 · 实时行情 · 主力资金 · 非 LLM 技术分析</span>
        <Link href="/sources/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)", marginLeft: "auto" }}>🔌 数据源</Link>
      </div>

      <div className="search"><SearchBox /></div>

      {watch.length > 0 && (
        <>
          <h2 className="block-title">⭐ 我的自选</h2>
          <div className="grid">{watch.map((s) => <QuoteCard key={s} symbol={s} />)}</div>
        </>
      )}

      <div className="tabs">
        {MARKETS.map((m) => (
          <button key={m.key} className={m.key === tab ? "active" : ""} onClick={() => setTab(m.key)}>{m.label}</button>
        ))}
      </div>

      <h2 className="block-title">涨跌热力图</h2>
      <Heatmap symbols={symbols} />

      <h2 className="block-title">行情卡片</h2>
      <div className="grid">{symbols.map((s) => <QuoteCard key={s} symbol={s} />)}</div>

      <div className="disclaimer">
        数据来源:暗号 = Binance(data-api.binance.vision)· 美/港/A股 = Yahoo Finance(经公共 CORS 代理,自动多代理回退)。
        免费源仅供演示/自用,商用对外须更换授权数据源。
        本页所有分析为<strong>规则化技术指标 + 简化缠论(非投资建议 / Not financial advice)</strong>。
        缠论结构识别灵感来自 <a href="https://guanchaotv.com/" target="_blank" rel="noreferrer">观潮 TideView</a>(独立简化实现,非其代码)。
      </div>
    </div>
  );
}
