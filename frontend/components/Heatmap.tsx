"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getQuote } from "@/lib/datasource";
import { nameOf } from "@/lib/markets";

interface Tile { symbol: string; pct: number | null; price: number | null }

// 涨跌幅 -> 颜色(绿涨红跌,强度随幅度)
function color(pct: number | null): string {
  if (pct == null) return "#2a2e39";
  const x = Math.max(-5, Math.min(5, pct)) / 5; // [-1,1]
  if (x >= 0) return `rgba(38,166,154,${0.25 + 0.6 * x})`;
  return `rgba(239,83,80,${0.25 + 0.6 * -x})`;
}

export default function Heatmap({ symbols }: { symbols: string[] }) {
  const [tiles, setTiles] = useState<Tile[]>([]);

  useEffect(() => {
    let alive = true;
    setTiles([]);
    (async () => {
      const out: Tile[] = [];
      await Promise.all(
        symbols.map(async (s) => {
          try {
            const q = await getQuote(s);
            out.push({ symbol: s, pct: q.changePct, price: q.price });
          } catch {
            out.push({ symbol: s, pct: null, price: null });
          }
        })
      );
      if (alive) setTiles(out.sort((a, b) => (b.pct ?? -99) - (a.pct ?? -99)));
    })();
    return () => { alive = false; };
  }, [symbols]);

  if (!tiles.length) return <div className="loading">热力图加载中…</div>;

  return (
    <div className="heatmap">
      {tiles.map((t) => (
        <Link key={t.symbol} href={`/symbol/?s=${encodeURIComponent(t.symbol)}`}>
          <div className="tile" style={{ background: color(t.pct) }}>
            <div className="tile-name">{nameOf(t.symbol)}</div>
            <div className="tile-pct">{t.pct == null ? "—" : `${t.pct >= 0 ? "+" : ""}${t.pct.toFixed(2)}%`}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
