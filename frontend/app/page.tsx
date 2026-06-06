"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import QuoteCard from "@/components/QuoteCard";
import Heatmap from "@/components/Heatmap";
import { MARKETS, symbolsForTab } from "@/lib/markets";
import { getWatchlist } from "@/lib/watchlist";

export default function Home() {
  const [q, setQ] = useState("");
  const [tab, setTab] = useState("ALL");
  const [watch, setWatch] = useState<string[]>([]);
  const router = useRouter();

  useEffect(() => {
    const sync = () => setWatch(getWatchlist());
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, []);

  function go(e: React.FormEvent) {
    e.preventDefault();
    const s = q.trim().toUpperCase();
    if (s) router.push(`/symbol/?s=${encodeURIComponent(s)}`);
  }

  const symbols = symbolsForTab(tab);

  return (
    <div className="container">
      <div className="header">
        <h1>📈 多市场股票数据看板</h1>
        <span className="tag">美股 · 港股 · A股 · 加密 · 实时行情 · 非 LLM 技术分析</span>
      </div>

      <form className="search" onSubmit={go}>
        <input value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="输入代码,如 US:AAPL / HK:00700 / CN:600519 / CRYPTO:BTCUSDT" />
        <button type="submit">查看</button>
      </form>

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
        本页所有分析为<strong>规则化技术指标(非投资建议 / Not financial advice)</strong>。
      </div>
    </div>
  );
}
