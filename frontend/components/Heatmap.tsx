"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { type Quote } from "@/lib/datasource";
import { cnLimitTag, marketOf, nameOf } from "@/lib/markets";
import { useLang } from "@/lib/names";
import { useNightQuotes } from "@/lib/nightquotes";
import { getRsRanks, type RsTable } from "@/lib/feed";
import { marketStatus } from "@/lib/marketstatus";

// 纯展示组件:与行情卡片共用同一份 quotes(父级单一数据源),保证看板各区数值一致。
interface Tile { symbol: string; pct: number | null; price: number | null }

// 涨跌幅 -> 颜色(绿涨红跌,强度随幅度)
function color(pct: number | null): string {
  if (pct == null) return "#2a2e39";
  const x = Math.max(-5, Math.min(5, pct)) / 5; // [-1,1]
  if (x >= 0) return `rgba(38,166,154,${0.25 + 0.6 * x})`;
  return `rgba(239,83,80,${0.25 + 0.6 * -x})`;
}

let _rsCache: RsTable | null = null;
function Tiles({ symbols, quotes, mode }: { symbols: string[]; quotes: Record<string, Quote | null>; mode: "pct" | "rs" }) {
  const lang = useLang();
  const night = useNightQuotes();
  const [rsT, setRsT] = useState<RsTable | null>(_rsCache);
  useEffect(() => {
    if (mode === "rs" && !_rsCache) getRsRanks().then((d) => { _rsCache = d; setRsT(d); }).catch(() => {});
  }, [mode]);
  const tiles = useMemo<(Tile & { night?: boolean })[]>(
    () => symbols.map((s) => {
      // 🌙 闭市 + 有 HIP-3 映射 → 用永续 24h 上色(瓦片角标区分口径)
      const nq = night.map[s];
      if (nq && nq.chg24h != null && !marketStatus(marketOf(s)).open) {
        return { symbol: s, pct: nq.chg24h * 100, price: nq.mark, night: true };
      }
      return { symbol: s, pct: quotes[s]?.changePct ?? null, price: quotes[s]?.price ?? null };
    }).sort((a, b) => (b.pct ?? -99) - (a.pct ?? -99)),
    [quotes, symbols, night],
  );
  return (
    <div className="heatmap">
      {tiles.map((t) => (
        <Link key={t.symbol} href={`/symbol/?s=${encodeURIComponent(t.symbol)}`}>
          <div
            className="tile"
            style={{ background: mode === "rs"
              ? (() => { const v = rsT?.ranks?.[t.symbol.replace(/^US:/, "")]?.rs; return v == null ? "#2a2e39" : v >= 50 ? `rgba(38,166,154,${0.2 + (v - 50) / 49 * 0.65})` : `rgba(239,83,80,${0.2 + (50 - v) / 49 * 0.65})`; })()
              : color(t.pct),
              ...(cnLimitTag(t.symbol, t.pct) ? { border: "1.5px solid #f7b500", boxShadow: "0 0 6px rgba(247,181,0,.4)" } : {}) }}
            title={`${nameOf(t.symbol, lang)} ${t.price ?? "—"} · ${t.pct == null ? "—" : `${t.pct >= 0 ? "+" : ""}${t.pct.toFixed(2)}%`}${t.night ? "(🌙夜盘24h)" : marketOf(t.symbol) === "CRYPTO" ? "(24h)" : "(当日)"}`}
          >
            <div className="tile-name">{t.night ? "🌙" : ""}{nameOf(t.symbol, lang)}</div>
            <div className="tile-pct">{mode === "rs"
              ? (() => { const v = rsT?.ranks?.[t.symbol.replace(/^US:/, "")]?.rs; return v == null ? "—" : `RS ${v}`; })()
              : t.pct == null ? "—" : `${t.pct >= 0 ? "+" : ""}${t.pct.toFixed(2)}%`}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function Heatmap({
  symbols,
  quotes,
  loading = false,
  sections = null,
}: {
  symbols: string[];
  quotes: Record<string, Quote | null>;
  loading?: boolean;
  /** 分区渲染(如「全部」视图按市场拆分,避免 24h 与当日涨跌混排) */
  sections?: { label: string; symbols: string[] }[] | null;
}) {
  const [mode, setMode] = useState<"pct" | "rs">("pct");
  if (loading || (!symbols.length && !sections?.length)) return <div className="loading">热力图加载中…</div>;
  const chips = (
    <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
      {(["pct", "rs"] as const).map((k) => (
        <button key={k} className="linklike" style={{ fontSize: 12,
          color: mode === k ? "var(--accent)" : "var(--muted)", textDecoration: mode === k ? "underline" : "none" }}
          onClick={() => setMode(k)}>{k === "pct" ? "涨跌" : "RS 强弱"}</button>
      ))}
    </div>
  );

  if (sections?.length) {
    return (
      <div>
        {chips}
        {sections.map((sec) => (
          <div key={sec.label} style={{ marginBottom: 10 }}>
            <div className="src" style={{ margin: "0 0 5px" }}>{sec.label}</div>
            <Tiles symbols={sec.symbols} quotes={quotes} mode={mode} />
          </div>
        ))}
      </div>
    );
  }
  return <div>{chips}<Tiles symbols={symbols} quotes={quotes} mode={mode} /></div>;
}
