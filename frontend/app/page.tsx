"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import QuoteCard from "@/components/QuoteCard";

const DEFAULTS = [
  "US:AAPL", "US:MSFT", "US:NVDA", "US:TSLA", "US:GOOGL", "US:AMZN",
  "CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT", "CRYPTO:BNBUSDT",
];

export default function Home() {
  const [q, setQ] = useState("");
  const router = useRouter();

  function go(e: React.FormEvent) {
    e.preventDefault();
    const s = q.trim().toUpperCase();
    if (s) router.push(`/symbol/?s=${encodeURIComponent(s)}`);
  }

  return (
    <div className="container">
      <div className="header">
        <h1>📈 多市场股票数据看板</h1>
        <span className="tag">美股 + 加密 · 实时行情 · 非 LLM 技术分析 (MVP)</span>
      </div>

      <form className="search" onSubmit={go}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="输入代码,如 US:AAPL 或 CRYPTO:BTCUSDT"
        />
        <button type="submit">查看</button>
      </form>

      <div className="grid">
        {DEFAULTS.map((s) => <QuoteCard key={s} symbol={s} />)}
      </div>

      <div className="disclaimer">
        数据来源:暗号 = Binance(data-api.binance.vision)· 美股 = Yahoo Finance(经 corsproxy.io)。
        免费源仅供演示/自用,商用对外须更换授权数据源。
        本页所有分析为<strong>规则化技术指标(非投资建议 / Not financial advice)</strong>。
      </div>
    </div>
  );
}
