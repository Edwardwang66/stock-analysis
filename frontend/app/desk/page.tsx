"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, HAS_BACKEND, type Quote } from "@/lib/datasource";
import {
  getAnalysisMd, getChanStats, getCryptoState, getEventHeat, getFundHoldings, getOvernight, getPreipoHistory, getIndex, getIntradayLive, getMarketHistory, getNotesIndex, getRepoWatchlist, getRsHistory, getRsRanks, getScores, getScreener, getScreenerHistory,
  type CryptoState, type EventHeatDoc, type FeedIndex, type OvernightDoc, type FundHoldings, type IntradayDoc, type MarketSnapshot, type NotesIndex, type RsTable, type ScoreTable, type ScreenerList,
} from "@/lib/feed";
import { cnLimitTag, nameOf } from "@/lib/markets";
import { inWatchlist, toggleWatchlist } from "@/lib/watchlist";
import { sectorLabel, useLang } from "@/lib/names";
import { sectorOf } from "@/lib/sectors";
import TzSelect from "@/components/TzSelect";
import LangSelect from "@/components/LangSelect";
import LiveClock from "@/components/LiveClock";
import RrgChart, { type RrgItem } from "@/components/RrgChart";
import { agoShort, fmtTime, useNow, useTz } from "@/lib/timefmt";
import { useNightQuotes } from "@/lib/nightquotes";
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
  const night = useNightQuotes();
  const [wl, setWl] = useState<string[]>([]);
  const [localWl, setLocalWl] = useState<Set<string>>(new Set());
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
  const [evFilter, setEvFilter] = useState<"全部" | "异动" | "新高" | "新低">("全部");
  // OpenClaw 三报告状态(盘前/盘中滚动/收盘前;5 分钟轮询)
  const [mdPre, setMdPre] = useState<string | null>(null);
  const [mdIntra, setMdIntra] = useState<string | null>(null);
  const [mdClose, setMdClose] = useState<string | null>(null);
  const [heat, setHeat] = useState<EventHeatDoc | null>(null);
  useEffect(() => { const t = setTimeout(() => getEventHeat().then(setHeat).catch(() => {}), 1500); return () => clearTimeout(t); }, []);
  const [chanA, setChanA] = useState<{ symbol: string; kind: string; price: number }[]>([]);
  useEffect(() => { const t = setTimeout(() => getChanStats().then((d) => setChanA(d?.active ?? [])).catch(() => {}), 1800); return () => clearTimeout(t); }, []);
  const [hl, setHl] = useState<CryptoState | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => getCryptoState().then((d) => { if (alive) setHl(d); }).catch(() => {});
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 120_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);
  const [pipo, setPipo] = useState<{ at: string; marks: Record<string, number> }[]>([]);
  useEffect(() => { const t = setTimeout(() => getPreipoHistory().then((h) => setPipo(h ?? [])).catch(() => {}), 2800); return () => clearTimeout(t); }, []);
  const [ovn, setOvn] = useState<OvernightDoc | null>(null);
  useEffect(() => { const t = setTimeout(() => getOvernight().then(setOvn).catch(() => {}), 1200); return () => clearTimeout(t); }, []);
  const [rsHist, setRsHist] = useState<{ date: string; rs: Record<string, number> }[]>([]);
  useEffect(() => { const t = setTimeout(() => getRsHistory().then((h) => setRsHist(h ?? [])).catch(() => {}), 2200); return () => clearTimeout(t); }, []);
  const [scrHist, setScrHist] = useState<{ date: string; items: { symbol: string }[] }[]>([]);
  useEffect(() => { const t = setTimeout(() => getScreenerHistory().then((h) => setScrHist((h ?? []) as any)).catch(() => {}), 2500); return () => clearTimeout(t); }, []);


  useEffect(() => {
    let alive = true;
    const d = new Date().toISOString().slice(0, 10);
    const load = () => {
      getAnalysisMd("premarket", d).then((t) => { if (alive) setMdPre(t); });
      getAnalysisMd("intraday", d).then((t) => { if (alive) setMdIntra(t); });
      getAnalysisMd("close", d).then((t) => { if (alive) setMdClose(t); });
    };
    const t0 = setTimeout(load, 2000);
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 300_000);
    return () => { alive = false; clearTimeout(t0); window.clearInterval(id); };
  }, []);
  useEffect(() => {
    let alive = true;
    const load = () => getIntradayLive().then((d) => { if (alive) setLiveDoc(d); }).catch(() => {});
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 60_000);
    return () => { alive = false; window.clearInterval(id); };
  }, []);
  // 过滤与排序(localStorage 记忆,刷新不丢)
  const [pools, setPools] = useState<Set<PoolKey>>(new Set());   // 空 = 全部
  const [sector, setSector] = useState("全部");
  const [sort, setSort] = useState<SortKey>("tag");
  useEffect(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem("desk:filters") || "{}");
      if (Array.isArray(saved.pools)) setPools(new Set(saved.pools));
      if (typeof saved.sector === "string") setSector(saved.sector);
      if (typeof saved.sort === "string") setSort(saved.sort);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => {
    try {
      window.localStorage.setItem("desk:filters", JSON.stringify({ pools: Array.from(pools), sector, sort }));
    } catch { /* ignore */ }
  }, [pools, sector, sort]);
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

  useEffect(() => {
    const sync = () => setLocalWl(new Set(rows.filter((r) => inWatchlist(r.symbol)).map((r) => r.symbol)));
    sync();
    window.addEventListener("watchlist-changed", sync);
    return () => window.removeEventListener("watchlist-changed", sync);
  }, [rows]);

  // 📌 今日要点(纯前端聚合现有 feed)
  const briefing = useMemo(() => {
    const out: { icon: string; text: string; href?: string }[] = [];
    // 1) 宏观:期货 + 亚洲最大异动
    if (ovn?.futures && ovn.date === today()) {
      const f = Object.values(ovn.futures).map((x) => `${x.name.replace("期货", "")} ${x.pct >= 0 ? "+" : ""}${x.pct}%`).join(" / ");
      const asia = Object.values(ovn.asia ?? {}).sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))[0];
      out.push({ icon: "🌐", text: `期货 ${f}${asia ? ` · 亚洲最大异动 ${asia.name} ${asia.pct >= 0 ? "+" : ""}${asia.pct}%` : ""}` });
    }
    // 2) 夜盘预警:perp_movers ∩ 自选池
    const wlCodes = new Set(wl.filter((x) => x.startsWith("US:")).map((x) => x.slice(3)).concat(wl.includes("KR:000660") ? ["SKHX"] : []));
    const pm = (ovn?.perp_movers ?? []).filter((x) => wlCodes.has(x.symbol)).slice(0, 4);
    if (pm.length) {
      out.push({ icon: "🌙", text: `自选夜盘异动:${pm.map((x) => `${nameOf(x.symbol === "SKHX" ? "KR:000660" : `US:${x.symbol}`, lang)} ${x.chg24h >= 0 ? "+" : ""}${x.chg24h}%`).join(" · ")}` });
    }
    // 2.5) 盘中自选大动(任意市场 |当日|≥4%)
    const big = rows.filter((r) => r.tags.includes("watch"))
      .map((r) => ({ r, pc: quotes[r.symbol]?.changePct }))
      .filter((x): x is { r: typeof rows[number]; pc: number } => x.pc != null && Math.abs(x.pc) >= 4)
      .sort((a, b) => Math.abs(b.pc) - Math.abs(a.pc))
      .slice(0, 4);
    if (big.length) {
      out.push({ icon: "⚡", text: `自选大动:${big.map((x) => `${nameOf(x.r.symbol, lang)} ${x.pc >= 0 ? "+" : ""}${x.pc.toFixed(1)}%`).join(" · ")}` });
    }
    // 3) 缠论信号 ∩ 自选池
    const K: Record<string, string> = { "1B": "一买", "2B": "二买", "3B": "三买", "1S": "一卖", "2S": "二卖", "3S": "三卖" };
    const ca = chanA.filter((a) => wlCodes.has(a.symbol)).slice(0, 5);
    if (ca.length) {
      out.push({ icon: "☯", text: `自选缠论信号:${ca.map((a) => `${nameOf(`US:${a.symbol}`, lang)} ${K[a.kind] ?? a.kind}`).join(" · ")}`, href: "/tracker/" });
    }
    // 4) 选股名单变动(今日 vs 上一交易日)
    if (scrHist.length >= 2) {
      const cur = new Set(scrHist[scrHist.length - 1].items.map((x) => x.symbol));
      const prev = new Set(scrHist[scrHist.length - 2].items.map((x) => x.symbol));
      const added = [...cur].filter((x) => !prev.has(x));
      const dropped = [...prev].filter((x) => !cur.has(x));
      if (added.length || dropped.length) {
        out.push({ icon: "📈", text: `≥80 名单:新进 ${added.length} 只${added.length ? `(${added.slice(0, 3).map((x) => nameOf(x, lang)).join("/")}${added.length > 3 ? "…" : ""})` : ""} · 掉出 ${dropped.length} 只`, href: "/screener/" });
      }
    }
    // 4.5) 领涨且动量加速(RS≥85 且 r63-r126≥25pp)
    if (rs?.ranks) {
      const acc = Object.entries(rs.ranks)
        .filter(([, v]) => (v.rs ?? 0) >= 85 && v.r63 != null && v.r126 != null && v.r63 - v.r126 >= 25)
        .sort((a, b) => (b[1].r63! - b[1].r126!) - (a[1].r63! - a[1].r126!))
        .slice(0, 4);
      if (acc.length) {
        out.push({ icon: "🚀", text: `领涨且加速:${acc.map(([k, v]) => `${nameOf(`US:${k}`, lang)}(RS${v.rs}·+${(v.r63! - v.r126!).toFixed(0)}pp)`).join(" · ")}` });
      }
    }
    // 5) 高波动 top
    const h0 = heat?.items?.[0];
    if (h0) out.push({ icon: "🔥", text: `本周最躁动:${nameOf(h0.symbol, lang)}(${h0.total} 次事件${h0.lows > h0.highs ? ",偏新低" : h0.highs > h0.lows ? ",偏新高" : ""})` });
    // 6) Winter 盘前观点(报告已投时抽首两行)
    if (mdPre) {
      const lines = mdPre.split("\n").map((x) => x.replace(/^#+\s*/, "").trim()).filter((x) => x && !x.startsWith("---"));
      const gist = lines.slice(0, 2).join(" / ").slice(0, 120);
      if (gist) out.push({ icon: "🌅", text: `Winter 盘前:${gist}…`, href: "/reports/" });
    }
    // 7) OpenClaw 节拍
    out.push({ icon: "🤖", text: `报告:盘前 ${mdPre ? "✅" : "⏳"} · 盘中滚动 ${mdIntra ? "✅" : "⏳"} · 收盘前 ${mdClose ? "✅" : "⏳"}`, href: "/reports/" });
    return out;
  }, [ovn, wl, rows, quotes, chanA, scrHist, heat, rs, mdPre, mdIntra, mdClose, lang]);

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

  // 轮动象限数据:池内美股(rs-ranks 覆盖)
  const rrgItems = useMemo<RrgItem[]>(() => {
    if (!rs?.ranks) return [];
    const out: RrgItem[] = [];
    for (const r of rows) {
      if (!r.symbol.startsWith("US:")) continue;
      const v = rs.ranks[r.symbol.slice(3)];
      if (!v || v.rs == null || v.r63 == null) continue;
      const color = r.tags.includes("watch") ? "#f7b500" : r.tags.includes("salp") ? "#26c6da" : (r.score ?? 0) >= 80 ? "#26a69a" : "#787b86";
      out.push({ symbol: r.symbol, name: nameOf(r.symbol, lang), rs: v.rs, r63: v.r63, r126: v.r126 ?? null, color });
    }
    return out;
  }, [rows, rs, lang]);

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
        <Link href="/reports/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>📜 报告</Link>
        <Link href="/alerts/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>⏰</Link>
        <Link href="/tracker/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🎯 追踪</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🛰️ 情报</Link>
        <LangSelect />
        <LiveClock />
        <TzSelect />
      </div>

      {loading ? <div className="loading">加载中…</div> : (
        <>
          {/* 📌 今日要点(聚合卡) */}
          {briefing.length > 0 && (
            <div className="section" style={{ marginTop: 4, borderColor: "var(--accent)" }}>
              <h2>📌 今日要点
                <button className="linklike" style={{ marginLeft: 10, fontSize: 12 }}
                  onClick={() => {
                    const txt = `【${today()} 看板要点】\n` + briefing.map((b) => `${b.icon} ${b.text}`).join("\n");
                    navigator.clipboard?.writeText(txt).then(() => alert("已复制,可直接粘贴分享")).catch(() => {});
                  }}>📋 复制</button>
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {briefing.map((b, i) => (
                  <div key={i} style={{ fontSize: 13, lineHeight: 1.6 }}>
                    <span style={{ marginRight: 6 }}>{b.icon}</span>
                    {b.text}
                    {b.href && <Link href={b.href} style={{ marginLeft: 8, color: "var(--accent)", fontSize: 12 }}>→</Link>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 行业风向(池内各行业平均涨跌 · ≥3 只才计) */}
          {(() => {
            const agg = new Map<string, { sum: number; n: number }>();
            for (const r of rows) {
              const pc = quotes[r.symbol]?.changePct;
              if (pc == null || r.sector === "其他") continue;
              const g = agg.get(r.sector) ?? { sum: 0, n: 0 };
              g.sum += pc; g.n++;
              agg.set(r.sector, g);
            }
            const arr = Array.from(agg.entries())
              .filter(([, g]) => g.n >= 3)
              .map(([sec, g]) => ({ sec, avg: g.sum / g.n, n: g.n }))
              .sort((a, b) => b.avg - a.avg);
            if (arr.length < 4) return null;
            const mx = Math.max(...arr.map((x) => Math.abs(x.avg)), 0.5);
            return (
              <div className="src" style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "0 2px 8px", fontSize: 11, alignItems: "center" }}>
                <span>行业风向:</span>
                {arr.slice(0, 5).map((x) => (
                  <span key={x.sec} title={`${x.n} 只均值`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    {sectorLabel(x.sec, lang)}
                    <span style={{ display: "inline-block", width: Math.max(6, Math.abs(x.avg) / mx * 36), height: 6,
                      background: x.avg >= 0 ? UP : DOWN, borderRadius: 3 }} />
                    <span className={x.avg >= 0 ? "up" : "down"}>{x.avg >= 0 ? "+" : ""}{x.avg.toFixed(1)}%</span>
                  </span>
                ))}
                {arr.length > 5 && <span>…</span>}
                {arr.slice(-2).filter((x) => !arr.slice(0, 5).includes(x)).map((x) => (
                  <span key={x.sec} title={`${x.n} 只均值`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    {sectorLabel(x.sec, lang)}
                    <span style={{ display: "inline-block", width: Math.max(6, Math.abs(x.avg) / mx * 36), height: 6,
                      background: x.avg >= 0 ? UP : DOWN, borderRadius: 3 }} />
                    <span className={x.avg >= 0 ? "up" : "down"}>{x.avg >= 0 ? "+" : ""}{x.avg.toFixed(1)}%</span>
                  </span>
                ))}
              </div>
            );
          })()}

          {/* 评分结构(70-100 五桶) */}
          {(() => {
            const scoresArr = rows.map((r) => r.score).filter((x): x is number => x != null && x >= 70);
            if (scoresArr.length < 10) return null;
            const b = [0, 0, 0, 0, 0]; // 70-75/75-80/80-85/85-90/90+
            for (const v of scoresArr) b[v >= 90 ? 4 : v >= 85 ? 3 : v >= 80 ? 2 : v >= 75 ? 1 : 0]++;
            const mx = Math.max(...b);
            const lbl = ["70+", "75+", "80+", "85+", "90+"];
            return (
              <div className="src" style={{ display: "flex", gap: 10, alignItems: "flex-end", margin: "0 2px 6px", fontSize: 11 }}>
                <span>评分结构:</span>
                {b.map((c, i) => (
                  <span key={i} style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                    <span style={{ display: "block", width: 22, height: 4 + (c / (mx || 1)) * 22,
                      background: i >= 2 ? "#26a69a" : "#787b86", borderRadius: 2, opacity: 0.5 + (i * 0.12) }} />
                    <span>{lbl[i]}·{c}</span>
                  </span>
                ))}
              </div>
            );
          })()}

          {/* 池内宽度分布条(全部行情就位后显示) */}
          {(() => {
            const pcs = rows.map((r) => quotes[r.symbol]?.changePct).filter((x): x is number => x != null);
            if (pcs.length < 30) return null;
            const buckets = [-3, -1, 0, 1, 3];
            const cnt = [0, 0, 0, 0, 0, 0];
            for (const p2 of pcs) {
              let i = buckets.findIndex((b) => p2 < b);
              if (i === -1) i = 5;
              cnt[i]++;
            }
            const colors = ["#b71c1c", "#ef5350", "#f1979b", "#9bd4b1", "#26a69a", "#0b8043"];
            const labels = ["<-3%", "-3~-1", "-1~0", "0~1", "1~3", ">3%"];
            const total = pcs.length;
            const up = pcs.filter((x) => x > 0).length;
            return (
              <div style={{ margin: "2px 2px 10px" }}>
                <div style={{ display: "flex", height: 10, borderRadius: 6, overflow: "hidden", border: "1px solid var(--border)" }}
                  title={cnt.map((c, i) => `${labels[i]}: ${c} 只`).join(" · ")}>
                  {cnt.map((c, i) => c > 0 && <div key={i} style={{ width: `${(c / total) * 100}%`, background: colors[i] }} />)}
                </div>
                <div className="src" style={{ fontSize: 11, marginTop: 3 }}>
                  池内宽度:涨 <span className="up">{up}</span> / 跌 <span className="down">{total - up - pcs.filter((x) => x === 0).length}</span>
                  · 中位 {(pcs.sort((a, b) => a - b)[Math.floor(pcs.length / 2)] ?? 0).toFixed(2)}% · {total} 只已报价
                </div>
              </div>
            );
          })()}

          {/* 盘中机器流(交易时段才有;Winter 5 分钟循环 → live 分支) */}
          {live && (
            <div className="section" style={{ marginTop: 4, borderColor: "var(--accent)" }}>
              <h2>⚡ 盘中流(机器报告 · {fmtTime(live.at, tzKey)}({agoShort(live.at, nowTick)}) · 池 {live.quoted}/{live.pool_size})
                {live.producer && (
                  <span className="badge" style={{ marginLeft: 8, fontSize: 11,
                    color: live.producer === "winter-loop" ? "#26c6da" : "#f7b500",
                    borderColor: live.producer === "winter-loop" ? "#26c6da" : "#f7b500" }}>
                    {live.producer === "winter-loop" ? "Winter 在岗" : live.producer === "watchdog" ? "三级兜底" : "备胎顶班"}
                  </span>
                )}
                <span className="src" style={{ marginLeft: 10 }}>
                  涨 <span className="up">{live.summary.up}</span> / 跌 <span className="down">{live.summary.down}</span>
                  {live.summary.median_pct != null && <> · 中位 {live.summary.median_pct >= 0 ? "+" : ""}{live.summary.median_pct.toFixed(2)}%</>}
                </span>
              </h2>
              {live.events.length ? (
                <>
                <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                  {(["全部", "异动", "新高", "新低"] as const).map((k) => (
                    <button key={k} className="linklike" style={{ fontSize: 12,
                      color: evFilter === k ? "var(--accent)" : "var(--muted)",
                      textDecoration: evFilter === k ? "underline" : "none" }}
                      onClick={() => setEvFilter(k)}>
                      {k}{k !== "全部" && `(${live.events.filter((e) => e.type === k).length})`}
                    </button>
                  ))}
                </div>
                <div className="signal-list">
                  {live.events.filter((e) => evFilter === "全部" || e.type === evFilter).slice(0, 12).map((e, i) => (
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
                </>
              ) : <p className="src">本轮无触发事件(异动≥0.8%/5分钟、当日新高新低)。</p>}
            </div>
          )}

          {/* OpenClaw 三报告状态(盘前 → 盘中滚动 → 收盘前) */}
          <div className="section" style={{ marginTop: 4 }}>
            <h2>🤖 OpenClaw 当日节拍
              <span className="src" style={{ marginLeft: 10 }}>
                盘前 {mdPre ? "✅" : "⏳"} · 盘中滚动 {mdIntra ? `✅(${mdIntra.split("\n").filter(Boolean).length} 行)` : "⏳"} · 收盘前 {mdClose ? "✅" : "⏳"}
              </span>
              <Link href="/reports/" className="src" style={{ marginLeft: 10, color: "var(--accent)" }}>报告中心 →</Link>
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

          {/* 24/7 夜盘代理 + 加密情绪(Hyperliquid,Cycle7/8) */}
          {hl?.equity_perps?.stocks && hl.equity_perps.stocks.length > 0 && (
            <div className="section" style={{ marginTop: 4 }}>
              <h2>🌙 24/7 夜盘代理
                <span className="src" style={{ marginLeft: 10 }}>
                  Hyperliquid 永续 · 全天候定价 · 实证 corr 0.965/方向命中 96%(Cycle8)· {agoShort(hl.updated_at ?? "", nowTick)}
                </span>
              </h2>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                {(hl.equity_perps.commodities ?? []).filter((x) => ["CL", "SILVER", "GOLD"].includes(x.symbol)).map((x) => (
                  <span key={x.symbol} className="badge" style={{ fontSize: 12, padding: "5px 10px",
                    color: (x.chg24h ?? 0) >= 0 ? UP : DOWN }}>
                    {x.symbol === "CL" ? "原油" : x.symbol === "SILVER" ? "白银" : "黄金"} {fmt(x.mark)} {x.chg24h != null ? `${(x.chg24h * 100).toFixed(2)}%` : ""}
                  </span>
                ))}
                {(hl.equity_perps.indices ?? []).filter((x) => ["SP500", "USTECH", "MAG7"].includes(x.symbol)).map((x) => (
                  <span key={x.symbol} className="badge" style={{ fontSize: 12, padding: "5px 10px",
                    color: (x.chg24h ?? 0) >= 0 ? UP : DOWN }}>
                    {x.symbol === "SP500" ? "标普永续" : x.symbol === "USTECH" ? "纳指永续" : "MAG7"} {fmt(x.mark)} {x.chg24h != null ? `${(x.chg24h * 100).toFixed(2)}%` : ""}
                  </span>
                ))}
              </div>
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead><tr><th>美股永续</th><th>24/7 价</th><th>24h</th><th>vs 正股</th><th>资金费率(年化)</th><th>24h 量</th></tr></thead>
                  <tbody>
                    {hl.equity_perps.stocks.slice(0, 10).map((x) => {
                      const local = x.symbol === "SKHX" ? "KR:000660" : `US:${x.symbol}`;
                      const label = x.symbol === "SKHX" ? nameOf("KR:000660", lang) : x.symbol === "SPCX" ? "SPCX合成" : x.symbol === "DRAM" ? "DRAM指数" : x.symbol === "EWY" ? "韩国ETF EWY" : nameOf(`US:${x.symbol}`, lang);
                      return (
                        <tr key={x.symbol}>
                          <td>{x.symbol === "SPCX" ? <span>{label}</span> :
                            <Link href={`/symbol/?s=${encodeURIComponent(local)}`} style={{ color: "var(--accent)" }}>{label}</Link>}
                            <span className="src" style={{ marginLeft: 6 }}>{x.symbol}</span></td>
                          <td>{fmt(x.mark)}</td>
                          <td className={(x.chg24h ?? 0) >= 0 ? "up" : "down"}>{x.chg24h != null ? `${(x.chg24h * 100).toFixed(2)}%` : "—"}</td>
                          {(() => {
                            const q = quotes[local];
                            const gap = q?.price ? (x.mark / q.price - 1) * 100 : null;
                            return <td className={gap == null ? "muted" : gap >= 0 ? "up" : "down"}
                              title="永续价 vs 正股最新价;闭市时=隐含跳空,盘中≈0 为正常">
                              {gap == null ? "—" : `${gap >= 0 ? "+" : ""}${gap.toFixed(2)}%`}</td>;
                          })()}
                          <td className={(x.funding_apr ?? 0) >= 0 ? "up" : "down"}>{x.funding_apr != null ? `${(x.funding_apr * 100).toFixed(1)}%` : "—"}</td>
                          <td className="src">{x.vol24h_usd ? `$${(x.vol24h_usd / 1e6).toFixed(0)}M` : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {!!hl.equity_perps?.private?.length && (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0 2px", alignItems: "center" }}>
                  <span className="src" style={{ fontWeight: 600 }}>🔮 Pre-IPO 永续:</span>
                  {hl.equity_perps.private.map((x) => (
                    <span key={x.symbol} className="badge" title={`24h量 $${((x.vol24h_usd ?? 0) / 1e6).toFixed(1)}M · 资金费率(年化) ${x.funding_apr != null ? (x.funding_apr * 100).toFixed(0) + "%" : "—"}`}
                      style={{ fontSize: 12, padding: "5px 10px", color: (x.chg24h ?? 0) >= 0 ? UP : DOWN }}>
                      {x.symbol === "SPACEX" ? "SpaceX" : x.symbol === "ANTHROPIC" ? "Anthropic" : x.symbol === "OPENAI" ? "OpenAI" : x.symbol}
                      {" "}${fmt(x.mark)} {x.chg24h != null ? `${x.chg24h >= 0 ? "+" : ""}${(x.chg24h * 100).toFixed(1)}%` : ""}
                      {(() => {
                        const vals = pipo.map((pt) => pt.marks?.[x.symbol]).filter((v): v is number => v != null).slice(-30);
                        if (vals.length < 4) return null;
                        const w = 40, h2 = 12, mn = Math.min(...vals), mx = Math.max(...vals);
                        const ptsStr = vals.map((v, i) => `${((i / (vals.length - 1)) * w).toFixed(1)},${(h2 - ((v - mn) / (mx - mn || 1)) * h2).toFixed(1)}`).join(" ");
                        return (
                          <svg width={w} height={h2} style={{ marginLeft: 5, opacity: 0.85, verticalAlign: "middle" }} aria-hidden>
                            <polyline points={ptsStr} fill="none" stroke={vals[vals.length - 1] >= vals[0] ? UP : DOWN} strokeWidth="1.3" />
                          </svg>
                        );
                      })()}
                      {x.funding_apr != null && x.funding_apr > 0.3 && <span style={{ color: "#f7b500" }}> 🔥{(x.funding_apr * 100).toFixed(0)}%</span>}
                    </span>
                  ))}
                  <span className="src">(链上合约对私有公司的 24/7 定价;🔥=资金费率&gt;30%=多头狂热)</span>
                </div>
              )}
              {hl.crypto && (
                <p className="src" style={{ marginTop: 8 }}>
                  ₿ 加密情绪:BTC 费率 {((hl.crypto.btc?.funding_apr ?? 0) * 100).toFixed(1)}% · ETH {((hl.crypto.eth?.funding_apr ?? 0) * 100).toFixed(1)}%
                  · 正费率占比 {((hl.crypto.pct_positive_funding ?? 0) * 100).toFixed(0)}% · 总持仓 ${((hl.crypto.total_oi_usd ?? 0) / 1e9).toFixed(1)}B
                  {hl.crypto.crowding_flag && <span style={{ color: "#f7b500" }}> · ⚠ 拥挤</span>}
                  {!!hl.crypto.funding_extremes?.length && (
                    <> · 极端费率:{hl.crypto.funding_extremes.slice(0, 3).map((c) => `${c.coin} ${((c.funding_apr ?? 0) * 100).toFixed(0)}%`).join(" / ")}</>
                  )}
                  {hl.venues?.n_dislocated != null && <> · 跨所错位 {hl.venues.n_dislocated} 个</>}
                </p>
              )}
              <p className="src" style={{ marginTop: 4 }}>
                美股闭市时这里仍在跳动(链上永续 24/7);开盘后以正股实价为准。资金费率正=多头付费(看多拥挤),负=空头付费。非投资建议。
              </p>
            </div>
          )}

          {/* 🌗 夜盘→开盘修复表(美股开盘后显示;Cycle8 结论的每日活体验证) */}
          {!night.usClosed && ovn?.date === today() && !!ovn?.perp_movers?.length && (() => {
            const rows2 = (ovn.perp_movers ?? [])
              .filter((x) => x.kind === "stock" && Math.abs(x.chg24h) >= 4)
              .map((x) => {
                const local = x.symbol === "SKHX" ? "KR:000660" : `US:${x.symbol}`;
                const q = quotes[local];
                const open_ = q?.changePct ?? null;
                const repair = open_ != null && x.chg24h !== 0 ? Math.max(0, Math.min(2, 1 - open_ / x.chg24h)) : null;
                return { sym: x.symbol, local, nightPct: x.chg24h, openPct: open_, repair };
              })
              .filter((r) => r.openPct != null);
            if (!rows2.length) return null;
            return (
              <div className="section" style={{ marginTop: 4 }}>
                <h2>🌗 夜盘→开盘修复
                  <span className="src" style={{ marginLeft: 10 }}>
                    永续夜盘预警 vs 开盘实况 · 修复率高=恐慌未兑现(Cycle8:开盘价吸收隔夜信息)
                  </span>
                </h2>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {rows2.map((r) => (
                    <Link key={r.sym} href={`/symbol/?s=${encodeURIComponent(r.local)}`} className="badge"
                      style={{ fontSize: 12, padding: "5px 10px" }}>
                      {nameOf(r.local, lang)}
                      <span className="down"> 夜{r.nightPct.toFixed(1)}%</span>
                      <span className={r.openPct! >= 0 ? "up" : "down"}> → 开{r.openPct! >= 0 ? "+" : ""}{r.openPct!.toFixed(1)}%</span>
                      {r.repair != null && r.nightPct < 0 && (
                        <span style={{ marginLeft: 4, color: r.repair >= 0.7 ? "#26a69a" : r.repair >= 0.3 ? "#f7b500" : "#ef5350" }}>
                          修复{(r.repair * 100).toFixed(0)}%
                        </span>
                      )}
                    </Link>
                  ))}
                </div>
              </div>
            );
          })()}

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
                    {nameOf(h.symbol, lang)} ×{h.total}
                    {h.highs > 0 && <span style={{ color: UP }}> ↑{h.highs}</span>}
                    {h.lows > 0 && <span style={{ color: DOWN }}> ↓{h.lows}</span>}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* 轮动象限(RRG 近似,RS×63日动量) */}
          {rrgItems.length >= 8 && (
            <div className="section" style={{ marginTop: 4 }}>
              <details>
                <summary style={{ cursor: "pointer" }}>
                  <span style={{ fontSize: 15, fontWeight: 600 }}>📡 轮动象限</span>
                  <span className="src" style={{ marginLeft: 10 }}>
                    池内美股 {rrgItems.length} 只 · x=RS分位 y=63日动量 · ⭐金 🦅青 80+绿 · 点击进个股
                  </span>
                </summary>
                <RrgChart items={rrgItems} />
              </details>
            </div>
          )}

          {/* 缠论进行中信号(chan-stats 周更) */}
          {chanA.length > 0 && (
            <p className="src" style={{ margin: "4px 2px 8px" }}>
              ☯ 缠论进行中:{chanA.slice(0, 14).map((a, i) => (
                <span key={i}>{i > 0 && " · "}
                  <Link href={`/symbol/?s=${encodeURIComponent("US:" + a.symbol)}`}
                    style={{ color: a.kind.endsWith("B") ? UP : DOWN }}>
                    {a.symbol} {({ "1B": "一买", "2B": "二买", "3B": "三买", "1S": "一卖", "2S": "二卖", "3S": "三卖" } as Record<string, string>)[a.kind] ?? a.kind}
                  </Link>
                </span>
              ))}
              <Link href="/tracker/" style={{ marginLeft: 8, color: "var(--accent)" }}>胜率表 →</Link>
            </p>
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
              <button className={sort === "tag" ? "active" : ""} onClick={() => setSort("tag")}>{lang === "en" ? "Default" : "默认"}</button>
              <button className={sort === "pctDesc" ? "active" : ""} onClick={() => setSort("pctDesc")}>{lang === "en" ? "Gain↓" : "涨幅↓"}</button>
              <button className={sort === "pctAsc" ? "active" : ""} onClick={() => setSort("pctAsc")}>{lang === "en" ? "Loss↑" : "跌幅↑"}</button>
              <button className={sort === "scoreDesc" ? "active" : ""} onClick={() => setSort("scoreDesc")}>{lang === "en" ? "Score↓" : "评分↓"}</button>
              <button className={sort === "rsDesc" ? "active" : ""} onClick={() => setSort("rsDesc")}>RS↓</button>
            </div>
            <span className="src">{view.length} 只</span>
            <button className="btn subtle" style={{ padding: "6px 12px", fontSize: 12 }}
              onClick={() => {
                const head = ["symbol", "name", "tags", "sector", "score", "rs", "price", "change_pct", "ai"];
                const lines = [head.join(",")];
                for (const r of view) {
                  const q = quotes[r.symbol];
                  const k = rs?.ranks?.[r.symbol.replace(/^US:/, "")];
                  const n = noteMap.get(r.symbol);
                  lines.push([r.symbol, JSON.stringify(nameOf(r.symbol, lang)), r.tags.join("|"), JSON.stringify(r.sector),
                    r.score ?? "", k?.rs ?? "", q?.price ?? "", q?.changePct?.toFixed(2) ?? "", n?.stance ?? ""].join(","));
                }
                const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = `desk-${today()}.csv`;
                a.click();
                URL.revokeObjectURL(a.href);
              }}>⬇ CSV</button>
          </div>

          <div className="section" style={{ overflowX: "auto", marginTop: 8 }}>
            <table>
              <thead><tr>
                <th>{lang === "en" ? "Symbol" : "标的"}</th><th>{lang === "en" ? "Tags" : "标签"}</th>
                <th>{lang === "en" ? "Sector" : "行业"}</th><th>{lang === "en" ? "Score" : "评分"}</th>
                <th>RS</th><th>{lang === "en" ? "Price" : "现价"}</th><th>{lang === "en" ? "Day" : "当日"}</th>
                {night.usClosed && Object.keys(night.map).length > 0 && <th>🌙 {lang === "en" ? "Night" : "夜盘"}</th>}
                <th>AI</th></tr></thead>
              <tbody>
                {view.map((r) => {
                  const q = quotes[r.symbol];
                  const pc = q?.changePct ?? null;
                  return (
                    <tr key={r.symbol}>
                      <td>
                        <button className="linklike" title={localWl.has(r.symbol) ? "移出本地自选" : "加入本地自选"}
                          style={{ marginRight: 4, color: localWl.has(r.symbol) ? "#f7b500" : MUT, fontSize: 13 }}
                          onClick={() => { toggleWatchlist(r.symbol); }}>
                          {localWl.has(r.symbol) ? "★" : "☆"}
                        </button>
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
                        const code = r.symbol.replace(/^US:/, "");
                        const v = rs?.ranks?.[code]?.rs;
                        if (v == null) return <span className="muted">—</span>;
                        const c = v >= 80 ? UP : v >= 50 ? "var(--text)" : DOWN;
                        const old7 = rsHist.length > 1 ? rsHist[Math.max(0, rsHist.length - 8)]?.rs?.[code] : undefined;
                        const delta = old7 != null ? v - old7 : null;
                        return (
                          <strong style={{ color: c }} title={delta != null ? `7日前 RS ${old7} → 今 ${v}` : undefined}>
                            {v}
                            {delta != null && Math.abs(delta) >= 5 && (
                              <span style={{ fontSize: 10, color: delta > 0 ? UP : DOWN }}>{delta > 0 ? "↗" : "↘"}</span>
                            )}
                          </strong>
                        );
                      })()}</td>
                      <td>{fmt(q?.price)}</td>
                      <td className={pc == null ? "muted" : pc >= 0 ? "up" : "down"}>
                        {pc == null ? "…" : `${pc >= 0 ? "+" : ""}${pc.toFixed(2)}%`}
                        {(() => { const lt = cnLimitTag(r.symbol, pc); return lt ? <span style={{ marginLeft: 4, fontSize: 10, color: "#f7b500" }}>{lt}</span> : null; })()}
                      </td>
                      {night.usClosed && Object.keys(night.map).length > 0 && (() => {
                        const nq = night.map[r.symbol];
                        if (!nq) return <td className="muted">—</td>;
                        const gap = q?.price ? (nq.mark / q.price - 1) * 100 : null;
                        return (
                          <td title={`Hyperliquid ${nq.hlSymbol} · 24h ${nq.chg24h != null ? (nq.chg24h * 100).toFixed(2) + "%" : "—"} · 费率 ${nq.fundingApr != null ? (nq.fundingApr * 100).toFixed(0) + "%" : "—"}`}>
                            <span>{fmt(nq.mark)}</span>
                            {gap != null && Math.abs(gap) >= 0.3 && (
                              <span className={gap >= 0 ? "up" : "down"} style={{ marginLeft: 4, fontSize: 12 }}>
                                {gap >= 0 ? "+" : ""}{gap.toFixed(1)}%
                              </span>
                            )}
                          </td>
                        );
                      })()}
                      <td>{noteCell(r.symbol)}</td>
                    </tr>
                  );
                })}
                {!view.length && <tr><td colSpan={9} className="src">当前过滤条件下没有标的。</td></tr>}
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
