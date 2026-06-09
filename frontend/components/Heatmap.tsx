"use client";
import Link from "next/link";
import { useMemo } from "react";
import { type Quote } from "@/lib/datasource";
import { marketOf, nameOf } from "@/lib/markets";

// 纯展示组件:与行情卡片共用同一份 quotes(父级单一数据源),保证看板各区数值一致。
interface Tile { symbol: string; pct: number | null; price: number | null }

// 涨跌幅 -> 颜色(绿涨红跌,强度随幅度)
function color(pct: number | null): string {
  if (pct == null) return "#2a2e39";
  const x = Math.max(-5, Math.min(5, pct)) / 5; // [-1,1]
  if (x >= 0) return `rgba(38,166,154,${0.25 + 0.6 * x})`;
  return `rgba(239,83,80,${0.25 + 0.6 * -x})`;
}

export default function Heatmap({
  symbols,
  quotes,
  loading = false,
}: {
  symbols: string[];
  quotes: Record<string, Quote | null>;
  loading?: boolean;
}) {
  const tiles = useMemo<Tile[]>(
    () => symbols.map((s) => ({
      symbol: s,
      pct: quotes[s]?.changePct ?? null,
      price: quotes[s]?.price ?? null,
    })).sort((a, b) => (b.pct ?? -99) - (a.pct ?? -99)),
    [quotes, symbols],
  );

  if (!tiles.length || loading) return <div className="loading">热力图加载中…</div>;

  return (
    <div className="heatmap">
      {tiles.map((t) => (
        <Link key={t.symbol} href={`/symbol/?s=${encodeURIComponent(t.symbol)}`}>
          <div
            className="tile"
            style={{ background: color(t.pct) }}
            title={`${nameOf(t.symbol)} ${t.price ?? "—"} · ${t.pct == null ? "—" : `${t.pct >= 0 ? "+" : ""}${t.pct.toFixed(2)}%`}${marketOf(t.symbol) === "CRYPTO" ? "(24h)" : "(当日)"}`}
          >
            <div className="tile-name">{nameOf(t.symbol)}</div>
            <div className="tile-pct">{t.pct == null ? "—" : `${t.pct >= 0 ? "+" : ""}${t.pct.toFixed(2)}%`}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
