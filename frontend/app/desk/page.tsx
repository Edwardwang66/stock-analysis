"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, HAS_BACKEND, type Quote } from "@/lib/datasource";
import {
  getFundHoldings, getIndex, getMarketHistory, getNotesIndex, getRepoWatchlist, getScores, getScreener,
  type FeedIndex, type FundHoldings, type MarketSnapshot, type NotesIndex, type ScoreTable, type ScreenerList,
} from "@/lib/feed";
import { nameOf } from "@/lib/markets";
import { sectorOf } from "@/lib/sectors";

const UP = "#26a69a", DOWN = "#ef5350", MUT = "#787b86";
const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n as number) ? "—" : (n as number).toLocaleString(undefined, { maximumFractionDigits: d });
const today = () => new Date().toISOString().slice(0, 10);

type PoolKey = "watch" | "salp" | "s90" | "s80" | "s70";
type SortKey = "pctDesc" | "pctAsc" | "scoreDesc" | "tag";

interface Row {
  symbol: string;
  tags: PoolKey[];
  score: number | null;
  sector: string;
  isPut?: boolean;
}

const POOL_LABEL: Record<PoolKey, string> = {
  watch: "⭐ 自选", salp: "🦅 SA LP", s90: "📈 90+", s80: "📈 80+", s70: "📈 70+",
};
const TAG_STYLE: Record<PoolKey, { color: string }> = {
  watch: { color: "#f7b500" }, salp: { color: "#26c6da" },
  s90: { color: "#69f0ae" }, s80: { color: UP }, s70: { color: "#9ccc65" },
};

function ago(iso?: string | null): string {
  if (!iso) return "—";
  const h = (Date.now() - new Date(iso).getTime()) / 3600_000;
  if (!isFinite(h)) return "—";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} 分钟前`;
  if (h < 48) return `${h.toFixed(1)} 小时前`;
  return `${(h / 24).toFixed(1)} 天前`;
}

export default function DeskPage() {
  const [wl, setWl] = useState<string[]>([]);
  const [scr, setScr] = useState<ScreenerList | null>(null);
  const [scores, setScores] = useState<ScoreTable | null>(null);
  const [fund, setFund] = useState<FundHoldings | null>(null);
  const [notes, setNotes] = useState<NotesIndex | null>(null);
  const [idx, setIdx] = useState<FeedIndex | null>(null);
  const [mh, setMh] = useState<MarketSnapshot[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  // 过滤与排序
  const [pools, setPools] = useState<Set<PoolKey>>(new Set());   // 空 = 全部
  const [sector, setSector] = useState("全部");
  const [sort, setSort] = useState<SortKey>("tag");

  useEffect(() => {
    let alive = true;
    (async () => {
      const [w, s, sc, f, n, i, m] = await Promise.all([
        getRepoWatchlist(), getScreener(), getScores(), getFundHoldings("situational-awareness"),
        getNotesIndex(), getIndex(), getMarketHistory(),
      ]);
      if (!alive) return;
      setWl(w?.symbols ?? []); setScr(s); setScores(sc); setFund(f); setNotes(n); setIdx(i); setMh(m ?? []);
      setLoading(false);
    })();
    return () => { alive = false; };
  }, []);

  // 主表:三池合并 + 标签
  const rows = useMemo<Row[]>(() => {
    const map = new Map<string, Row>();
    const ensure = (sym: string): Row => {
      let r = map.get(sym);
      if (!r) { r = { symbol: sym, tags: [], score: null, sector: sectorOf(sym) }; map.set(sym, r); }
      return r;
    };
    for (const s of wl) ensure(s).tags.push("watch");
    const salpSet = (fund?.positions ?? []).slice(0, 12).filter((p) => p.ticker.includes(":"));
    for (const p of salpSet) {
      const r = ensure(p.ticker);
      r.tags.push("salp");
      if (p.type.includes("Put")) r.isPut = true;
    }
    // 分数:优先全宇宙 scores.json(任意档),否则用 latest.json(≥80)
    const scoreOf = (code: string): number | null =>
      scores?.scores?.[code] ?? scr?.items?.find((x) => x.symbol === code)?.score ?? null;
    const universe = scores?.scores ? Object.keys(scores.scores) : (scr?.items ?? []).map((x) => x.symbol);
    for (const code of universe) {
      const sc = scoreOf(code);
      if (sc == null || sc < 70) continue;          // 70 分以下不进看板
      const r = ensure(`US:${code}`);
      r.score = sc;
      if (sc >= 90) r.tags.push("s90");
      else if (sc >= 80) r.tags.push("s80");
      else r.tags.push("s70");
    }
    // 自选/SALP 里的标的若有分数也补上
    for (const r of map.values()) {
      if (r.score == null && r.symbol.startsWith("US:")) {
        const sc = scoreOf(r.symbol.slice(3));
        if (sc != null) r.score = sc;
      }
    }
    return Array.from(map.values());
  }, [wl, fund, scr, scores]);

  // 实时报价(统一数据层,分块并发渐进上屏)
  useEffect(() => {
    if (!rows.length) return;
    let alive = true;
    const syms = rows.map((r) => r.symbol);
    getQuotes(syms, (q) => { if (alive) setQuotes((prev) => ({ ...prev, [q.symbol]: q })); }).catch(() => {});
    const id = window.setInterval(() => {
      if (!document.hidden) getQuotes(syms, (q) => { if (alive) setQuotes((prev) => ({ ...prev, [q.symbol]: q })); }).catch(() => {});
    }, 30_000);
    return () => { alive = false; window.clearInterval(id); };
  }, [rows]);

  const noteMap = useMemo(() => {
    const m = new Map<string, { date: string; stance: string }>();
    for (const n of notes?.symbols ?? []) m.set(n.symbol, { date: n.date, stance: n.stance });
    return m;
  }, [notes]);

  const sectors = useMemo(
    () => ["全部", ...Array.from(new Set(rows.map((r) => r.sector))).sort()],
    [rows],
  );

  const view = useMemo(() => {
    let v = rows;
    if (pools.size) v = v.filter((r) => r.tags.some((t) => pools.has(t)));
    if (sector !== "全部") v = v.filter((r) => r.sector === sector);
    const pct = (r: Row) => quotes[r.symbol]?.changePct ?? null;
    const arr = [...v];
    if (sort === "pctDesc") arr.sort((a, b) => (pct(b) ?? -999) - (pct(a) ?? -999));
    else if (sort === "pctAsc") arr.sort((a, b) => (pct(a) ?? 999) - (pct(b) ?? 999));
    else if (sort === "scoreDesc") arr.sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
    else arr.sort((a, b) => {
      const w = (r: Row) => (r.tags.includes("watch") ? 0 : r.tags.includes("salp") ? 1 : 2);
      return w(a) - w(b) || (b.score ?? -1) - (a.score ?? -1) || a.symbol.localeCompare(b.symbol);
    });
    return arr;
  }, [rows, pools, sector, sort, quotes]);

  const togglePool = (k: PoolKey) => setPools((prev) => {
    const n = new Set(prev);
    if (n.has(k)) n.delete(k); else n.add(k);
    return n;
  });

  const noteCell = (sym: string) => {
    const n = noteMap.get(sym);
    if (!n) return <span className="down">❌</span>;
    const fresh = n.date === today() || n.date === scr?.date;
    return <span className={fresh ? "up" : "muted"} title={n.date}>{fresh ? "✅" : "🕓"} {n.stance}</span>;
  };

  const lastSnap = mh.length ? mh[mh.length - 1] : null;
  const notesFresh = (notes?.symbols ?? []).filter((n) => n.date === today() || n.date === scr?.date).length;

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>← 返回</Link>
        <h1>📋 总览</h1>
        <span className="tag">全池标签视图 · {rows.length} 只 · 选股日 {scr?.date ?? "—"}(阈值 ≥{scr?.threshold ?? 80})</span>
        <a href="https://github.com/Edwardwang66/stock-analysis/issues?q=is%3Aissue+label%3Adaily-digest" target="_blank" rel="noreferrer"
          className="btn" style={{ marginLeft: "auto", background: "transparent", border: "1px solid var(--border)", color: MUT }}>📬 日报</a>
        <Link href="/tracker/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🎯 追踪</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🛰️ 情报</Link>
      </div>

      {loading ? <div className="loading">加载中…</div> : (
        <>
          {/* 过滤 + 排序工具条 */}
          <div className="toolbar" style={{ marginTop: 4 }}>
            <div className="segmented">
              {(Object.keys(POOL_LABEL) as PoolKey[]).map((k) => (
                <button key={k} className={pools.has(k) ? "active" : ""} onClick={() => togglePool(k)}
                  title="可多选叠加;全不选 = 显示全部">{POOL_LABEL[k]}</button>
              ))}
            </div>
            <select value={sector} onChange={(e) => setSector(e.target.value)}
              style={{ background: "var(--panel)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px", fontSize: 12 }}>
              {sectors.map((s) => <option key={s} value={s}>{s === "全部" ? "行业:全部" : s}</option>)}
            </select>
            <div className="segmented">
              <button className={sort === "tag" ? "active" : ""} onClick={() => setSort("tag")}>默认</button>
              <button className={sort === "pctDesc" ? "active" : ""} onClick={() => setSort("pctDesc")}>涨幅↓</button>
              <button className={sort === "pctAsc" ? "active" : ""} onClick={() => setSort("pctAsc")}>跌幅↑</button>
              <button className={sort === "scoreDesc" ? "active" : ""} onClick={() => setSort("scoreDesc")}>评分↓</button>
            </div>
            <span className="src">{view.length} 只</span>
          </div>

          <div className="section" style={{ overflowX: "auto", marginTop: 8 }}>
            <table>
              <thead><tr><th>标的</th><th>标签</th><th>行业</th><th>评分</th><th>现价</th><th>当日</th><th>AI</th></tr></thead>
              <tbody>
                {view.map((r) => {
                  const q = quotes[r.symbol];
                  const pc = q?.changePct ?? null;
                  return (
                    <tr key={r.symbol}>
                      <td>
                        <Link href={`/symbol/?s=${encodeURIComponent(r.symbol)}`} style={{ color: "var(--accent)" }}>{nameOf(r.symbol)}</Link>
                        <span className="src" style={{ marginLeft: 6 }}>{r.symbol.replace(/^US:/, "")}</span>
                      </td>
                      <td>
                        {r.tags.map((t) => (
                          <span key={t} className="badge" style={{ marginRight: 4, fontSize: 10, color: TAG_STYLE[t].color, borderColor: TAG_STYLE[t].color }}>
                            {POOL_LABEL[t]}
                          </span>
                        ))}
                        {r.isPut && <span className="badge" style={{ fontSize: 10, color: DOWN, borderColor: DOWN }}>Put空头</span>}
                      </td>
                      <td className="src">{r.sector}</td>
                      <td>{r.score != null ? <strong>{r.score}</strong> : "—"}</td>
                      <td>{fmt(q?.price)}</td>
                      <td className={pc == null ? "muted" : pc >= 0 ? "up" : "down"}>
                        {pc == null ? "…" : `${pc >= 0 ? "+" : ""}${pc.toFixed(2)}%`}
                      </td>
                      <td>{noteCell(r.symbol)}</td>
                    </tr>
                  );
                })}
                {!view.length && <tr><td colSpan={7} className="src">当前过滤条件下没有标的。</td></tr>}
              </tbody>
            </table>
          </div>

          {/* 数据链路(折叠,保持单页不臃肿) */}
          <details className="section" style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontSize: 14 }}>
              ⚙️ 数据链路状态(实时 vs Routine)· AI 今日覆盖 {notesFresh} 只 · 快照 {lastSnap?.date ?? "—"} · feed {idx?.freshness?.stale ? "陈旧 ⚠" : "新鲜 ✓"}
            </summary>
            <table style={{ marginTop: 10 }}>
              <tbody>
                <tr><td>🔴 实时</td><td className="src">加密 WebSocket ~1s · 股票 {HAS_BACKEND ? "后端缓存" : "代理"} 5-10s 轮询 · 盘前盘后 30s · 指数/FNG 60s/10min</td></tr>
                <tr><td>🔁 Routine</td><td className="src">盘中5分钟机器报告(Winter 循环,Actions 备胎)· screener 22:30 UTC · AI 解读 {ago(notes?.updated_at)} · 快照×2/日 · 13F 周检 · 日报 23:30 UTC</td></tr>
              </tbody>
            </table>
          </details>

          <div className="disclaimer">
            标签:⭐ 自选池(feed/watchlist.json,{wl.length} 只)· 🦅 SA LP 13F 前 12 · 📈 评分档(v2 十因子,70 分起入板)。
            行业为静态映射(lib/sectors.ts,可改)。✅=当日 AI 解读 🕓=旧 ❌=缺。仅供信息参考,<strong>非投资建议</strong>。
          </div>
        </>
      )}
    </div>
  );
}
