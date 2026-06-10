"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, HAS_BACKEND, type Quote } from "@/lib/datasource";
import {
  getAnalysisMd, getEventHeat, getFundHoldings, getOvernight, getIndex, getIntradayLive, getMarketHistory, getNotesIndex, getRepoWatchlist, getRsRanks, getScores, getScreener,
  type EventHeatDoc, type FeedIndex, type OvernightDoc, type FundHoldings, type IntradayDoc, type MarketSnapshot, type NotesIndex, type RsTable, type ScoreTable, type ScreenerList,
} from "@/lib/feed";
import { nameOf } from "@/lib/markets";
import { sectorLabel, useLang } from "@/lib/names";
import { sectorOf } from "@/lib/sectors";
import TzSelect from "@/components/TzSelect";
import LangSelect from "@/components/LangSelect";
import LiveClock from "@/components/LiveClock";
import { agoShort, fmtTime, useNow, useTz } from "@/lib/timefmt";
// 行业:自选池静态精标 > 标普500 GICS(scores.json) > 其他

const UP = "#26a69a", DOWN = "#ef5350", MUT = "#787b86";
const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n as number) ? "—" : (n as number).toLocaleString(undefined, { maximumFractionDigits: d });
const today = () => new Date().toISOString().slice(0, 10);

type PoolKey = "watch" | "salp" | "s90" | "s80" | "s70";
type SortKey = "pctDesc" | "pctAsc" | "scoreDesc" | "rsDesc" | "tag";

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
  const lang = useLang();
  const [wl, setWl] = useState<string[]>([]);
  const [scr, setScr] = useState<ScreenerList | null>(null);
  const [scores, setScores] = useState<ScoreTable | null>(null);
  const [rs, setRs] = useState<RsTable | null>(null);
  const [fund, setFund] = useState<FundHoldings | null>(null);
  const [notes, setNotes] = useState<NotesIndex | null>(null);
  const [idx, setIdx] = useState<FeedIndex | null>(null);
  const [mh, setMh] = useState<MarketSnapshot[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  // 盘中机器流(live 分支,60s 轮询;非交易时段自动为 null)
  const [live, setLiveDoc] = useState<IntradayDoc | null>(null);
  // OpenClaw 三报告状态(盘前/盘中滚动/收盘前;5 分钟轮询)
  const [mdPre, setMdPre] = useState<string | null>(null);
  const [mdIntra, setMdIntra] = useState<string | null>(null);
  const [mdClose, setMdClose] = useState<string | null>(null);
  const [heat, setHeat] = useState<EventHeatDoc | null>(null);
  useEffect(() => { getEventHeat().then(setHeat).catch(() => {}); }, []);
  const [ovn, setOvn] = useState<OvernightDoc | null>(null);
  useEffect(() => { getOvernight().then(setOvn).catch(() => {}); }, []);
  useEffect(() => {
    let alive = true;
    const d = new Date().toISOString().slice(0, 10);
    const load = () => {
      getAnalysisMd("premarket", d).then((t) => { if (alive) setMdPre(t); });
      getAnalysisMd("intraday", d).then((t) => { if (alive) setMdIntra(t); });
      getAnalysisMd("close", d).then((t) => { if (alive) setMdClose(t); });
    };
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 300_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);
  useEffect(() => {
    let alive = true;
    const load = () => getIntradayLive().then((d) => { if (alive) setLiveDoc(d); }).catch(() => {});
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 60_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);
  // 过滤与排序
  const [pools, setPools] = useState<Set<PoolKey>>(new Set());   // 空 = 全部
  const [sector, setSector] = useState("全部");
  const [sort, setSort] = useState<SortKey>("tag");
  const tzKey = useTz();
  const nowTick = useNow(1000);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [w, s, sc, f, n, i, m, rsT] = await Promise.all([
        getRepoWatchlist(), getScreener(), getScores(), getFundHoldings("situational-awareness"),
        getNotesIndex(), getIndex(), getMarketHistory(), getRsRanks(),
      ]);
      if (!alive) return;
      setWl(w?.symbols ?? []); setScr(s); setScores(sc); setFund(f); setNotes(n); setIdx(i); setMh(m ?? []); setRs(rsT);
      setLoading(false);
    })();
    return () => { alive = false; };
  }, []);

  // 主表:三池合并 + 标签
  const rows = useMemo<Row[]>(() => {
    const map = new Map<string, Row>();
    const ensure = (sym: string): Row => {
      let r = map.get(sym);
      if (!r) {
        const gics = sym.startsWith("US:") ? scores?.sectors?.[sym.slice(3)] : null;
        r = { symbol: sym, tags: [], score: null, sector: sectorOf(sym, gics) };
        map.set(sym, r);
      }
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
    else if (sort === "rsDesc") {
      const rsOf = (r: Row) => rs?.ranks?.[r.symbol.replace(/^US:/, "")]?.rs ?? -1;
      arr.sort((a, b) => rsOf(b) - rsOf(a));
    }
    else arr.sort((a, b) => {
      const w = (r: Row) => (r.tags.includes("watch") ? 0 : r.tags.includes("salp") ? 1 : 2);
      return w(a) - w(b) || (b.score ?? -1) - (a.score ?? -1) || a.symbol.localeCompare(b.symbol);
    });
    return arr;
  }, [rows, pools, sector, sort, quotes, rs]);

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
        <span className="tag">全池标签视图 · {rows.length} 只 · 选股日 {scr?.date ?? "—"}(美东 · 阈值 ≥{scr?.threshold ?? 80})</span>
        <a href="https://github.com/Edwardwang66/stock-analysis/issues?q=is%3Aissue+label%3Adaily-digest" target="_blank" rel="noreferrer"
          className="btn" style={{ marginLeft: "auto", background: "transparent", border: "1px solid var(--border)", color: MUT }}>📬 日报</a>
        <Link href="/tracker/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🎯 追踪</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🛰️ 情报</Link>
        <LangSelect />
        <LiveClock />
        <TzSelect />
      </div>

      {loading ? <div className="loading">加载中…</div> : (
        <>
          {/* 盘中机器流(交易时段才有;Winter 5 分钟循环 → live 分支) */}
          {live && (
            <div className="section" style={{ marginTop: 4, borderColor: "var(--accent)" }}>
              <h2>⚡ 盘中流(机器报告 · {fmtTime(live.at, tzKey)}({agoShort(live.at, nowTick)}) · 池 {live.quoted}/{live.pool_size})
                <span className="src" style={{ marginLeft: 10 }}>
                  涨 <span className="up">{live.summary.up}</span> / 跌 <span className="down">{live.summary.down}</span>
                  {live.summary.median_pct != null && <> · 中位 {live.summary.median_pct >= 0 ? "+" : ""}{live.summary.median_pct.toFixed(2)}%</>}
                </span>
              </h2>
              {live.events.length ? (
                <div className="signal-list">
                  {live.events.slice(0, 12).map((e, i) => (
                    <Link key={i} href={`/symbol/?s=${encodeURIComponent(e.symbol)}`} className="signal" style={{ alignItems: "baseline" }}>
                      <span>
                        <span className="badge" style={{ marginRight: 8, fontSize: 11,
                          color: e.type === "新低" ? DOWN : e.type === "新高" ? UP : "#f7b500",
                          borderColor: e.type === "新低" ? DOWN : e.type === "新高" ? UP : "#f7b500" }}>{e.type}</span>
                        {nameOf(e.symbol, lang)} <span className="src">{e.symbol.replace(/^US:/, "")}</span>
                      </span>
                      <span className="src">{e.detail} @ {fmt(e.price)}</span>
                    </Link>
                  ))}
                </div>
              ) : <p className="src">本轮无触发事件(异动≥0.8%/5分钟、当日新高新低)。</p>}
            </div>
          )}

          {/* OpenClaw 三报告状态(盘前 → 盘中滚动 → 收盘前) */}
          <div className="section" style={{ marginTop: 4 }}>
            <h2>🤖 OpenClaw 当日节拍
              <span className="src" style={{ marginLeft: 10 }}>
                盘前 {mdPre ? "✅" : "⏳"} · 盘中滚动 {mdIntra ? `✅(${mdIntra.split("\n").filter(Boolean).length} 行)` : "⏳"} · 收盘前 {mdClose ? "✅" : "⏳"}
              </span>
              <a href={`https://github.com/Edwardwang66/stock-analysis/tree/main/feed/screener`} target="_blank" rel="noreferrer"
                className="src" style={{ marginLeft: 10, color: "var(--accent)" }}>原文 →</a>
            </h2>
            {ovn?.futures && ovn.date === today() && (
              <p className="src" style={{ margin: "4px 0 8px" }}>
                盘前要素:{Object.values(ovn.futures).map((f) => `${f.name} ${f.pct >= 0 ? "+" : ""}${f.pct}%`).join(" · ")}
                {ovn.asia && <> ｜ 亚洲 {Object.values(ovn.asia).map((f) => `${f.name} ${f.pct >= 0 ? "+" : ""}${f.pct}%`).join(" · ")}</>}
                {ovn.crypto?.BTCUSDT && <> ｜ BTC {ovn.crypto.BTCUSDT.pct >= 0 ? "+" : ""}{ovn.crypto.BTCUSDT.pct.toFixed(1)}%</>}
              </p>
            )}
            {mdIntra && (
              <details>
                <summary style={{ cursor: "pointer", fontSize: 13 }} className="src">盘中事件解读滚动(最新在下,点开看全部)</summary>
                <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, lineHeight: 1.7, color: "var(--text)",
                              background: "var(--bg)", borderRadius: 8, padding: 12, marginTop: 8, maxHeight: 320, overflow: "auto" }}>
                  {mdIntra.trim()}
                </pre>
              </details>
            )}
            {mdPre && !mdIntra && (
              <details>
                <summary style={{ cursor: "pointer", fontSize: 13 }} className="src">盘前报告(点开)</summary>
                <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, lineHeight: 1.7, color: "var(--text)",
                              background: "var(--bg)", borderRadius: 8, padding: 12, marginTop: 8, maxHeight: 320, overflow: "auto" }}>
                  {mdPre.trim()}
                </pre>
              </details>
            )}
          </div>

          {/* 事件热度榜(Winter PG 近7天聚合;未投递时隐藏) */}
          {!!heat?.items?.length && (
            <div className="section" style={{ marginTop: 4 }}>
              <h2>🔥 高波动榜
                <span className="src" style={{ marginLeft: 10 }}>
                  近 {heat.window_days ?? 7} 天盘中事件(异动≥0.8%/新高/新低)次数 · Winter·Postgres
                </span>
              </h2>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {heat.items.slice(0, 20).map((h) => (
                  <Link key={h.symbol} href={`/symbol/?s=${encodeURIComponent(h.symbol)}`} className="badge"
                    title={`异动${h.moves} · 新高${h.highs} · 新低${h.lows}`}
                    style={{ fontSize: 12, padding: "5px 10px",
                             color: h.lows > h.highs ? DOWN : h.highs > h.lows ? UP : "var(--text)" }}>
                    {h.symbol.replace(/^US:/, "")} ×{h.total}
                    {h.highs > 0 && <span style={{ color: UP }}> ↑{h.highs}</span>}
                    {h.lows > 0 && <span style={{ color: DOWN }}> ↓{h.lows}</span>}
                  </Link>
                ))}
              </div>
            </div>
          )}

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
              {sectors.map((s) => <option key={s} value={s}>{s === "全部" ? (lang === "en" ? "Sector: All" : "行业:全部") : sectorLabel(s, lang)}</option>)}
            </select>
            <div className="segmented">
              <button className={sort === "tag" ? "active" : ""} onClick={() => setSort("tag")}>默认</button>
              <button className={sort === "pctDesc" ? "active" : ""} onClick={() => setSort("pctDesc")}>涨幅↓</button>
              <button className={sort === "pctAsc" ? "active" : ""} onClick={() => setSort("pctAsc")}>跌幅↑</button>
              <button className={sort === "scoreDesc" ? "active" : ""} onClick={() => setSort("scoreDesc")}>评分↓</button>
              <button className={sort === "rsDesc" ? "active" : ""} onClick={() => setSort("rsDesc")}>RS↓</button>
            </div>
            <span className="src">{view.length} 只</span>
          </div>

          <div className="section" style={{ overflowX: "auto", marginTop: 8 }}>
            <table>
              <thead><tr><th>标的</th><th>标签</th><th>行业</th><th>评分</th><th>RS</th><th>现价</th><th>当日</th><th>AI</th></tr></thead>
              <tbody>
                {view.map((r) => {
                  const q = quotes[r.symbol];
                  const pc = q?.changePct ?? null;
                  return (
                    <tr key={r.symbol}>
                      <td>
                        <Link href={`/symbol/?s=${encodeURIComponent(r.symbol)}`} style={{ color: "var(--accent)" }}>{nameOf(r.symbol, lang)}</Link>
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
                      <td>{(() => {
                        const v = rs?.ranks?.[r.symbol.replace(/^US:/, "")]?.rs;
                        if (v == null) return <span className="muted">—</span>;
                        const c = v >= 80 ? UP : v >= 50 ? "var(--text)" : DOWN;
                        return <strong style={{ color: c }}>{v}</strong>;
                      })()}</td>
                      <td>{fmt(q?.price)}</td>
                      <td className={pc == null ? "muted" : pc >= 0 ? "up" : "down"}>
                        {pc == null ? "…" : `${pc >= 0 ? "+" : ""}${pc.toFixed(2)}%`}
                      </td>
                      <td>{noteCell(r.symbol)}</td>
                    </tr>
                  );
                })}
                {!view.length && <tr><td colSpan={8} className="src">当前过滤条件下没有标的。</td></tr>}
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
