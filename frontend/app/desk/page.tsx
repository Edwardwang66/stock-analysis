"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, HAS_BACKEND, type Quote } from "@/lib/datasource";
import {
  getFundHoldings, getIndex, getMarketHistory, getNotesIndex, getRepoWatchlist, getScreener,
  type FeedIndex, type FundHoldings, type MarketSnapshot, type NotesIndex, type ScreenerList,
} from "@/lib/feed";
import { nameOf } from "@/lib/markets";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";
const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n as number) ? "—" : (n as number).toLocaleString(undefined, { maximumFractionDigits: d });
const today = () => new Date().toISOString().slice(0, 10);

function ago(iso?: string | null): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (!isFinite(ms)) return "—";
  const h = ms / 3600_000;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} 分钟前`;
  if (h < 48) return `${h.toFixed(1)} 小时前`;
  return `${(h / 24).toFixed(1)} 天前`;
}

function Dot({ ok }: { ok: boolean | null }) {
  const c = ok == null ? MUT : ok ? UP : DOWN;
  return <span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 99, background: c, marginRight: 6 }} />;
}

export default function DeskPage() {
  const [wl, setWl] = useState<string[]>([]);
  const [scr, setScr] = useState<ScreenerList | null>(null);
  const [fund, setFund] = useState<FundHoldings | null>(null);
  const [notes, setNotes] = useState<NotesIndex | null>(null);
  const [idx, setIdx] = useState<FeedIndex | null>(null);
  const [mh, setMh] = useState<MarketSnapshot[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [w, s, f, n, i, m] = await Promise.all([
        getRepoWatchlist(), getScreener(), getFundHoldings("situational-awareness"),
        getNotesIndex(), getIndex(), getMarketHistory(),
      ]);
      if (!alive) return;
      setWl(w?.symbols ?? []); setScr(s); setFund(f); setNotes(n); setIdx(i); setMh(m ?? []);
      setLoading(false);
      // 实时估值:自选池 + 看多全名单 + 基金前10(统一数据层,分块并发)
      const syms = Array.from(new Set([
        ...(w?.symbols ?? []),
        ...((s?.items ?? []).map((x) => `US:${x.symbol}`)),
        ...((f?.positions ?? []).slice(0, 10).map((p) => p.ticker).filter((t) => t.includes(":"))),
      ]));
      if (syms.length) {
        getQuotes(syms, (q) => { if (alive) setQuotes((prev) => ({ ...prev, [q.symbol]: q })); }).catch(() => {});
      }
    })();
    return () => { alive = false; };
  }, []);

  const noteMap = useMemo(() => {
    const m = new Map<string, { date: string; stance: string }>();
    for (const n of notes?.symbols ?? []) m.set(n.symbol, { date: n.date, stance: n.stance });
    return m;
  }, [notes]);

  const noteCell = (sym: string) => {
    const n = noteMap.get(sym);
    if (!n) return <span className="down">❌ 无</span>;
    const fresh = n.date === today() || n.date === scr?.date;
    return <span className={fresh ? "up" : "muted"}>{fresh ? "✅" : "🕓"} {n.date} · {n.stance}</span>;
  };

  const qCell = (sym: string) => {
    const q = quotes[sym];
    if (!q) return <span className="muted">…</span>;
    return (
      <>
        {fmt(q.price)} <span className={q.changePct != null && q.changePct >= 0 ? "up" : "down"}>
          {q.changePct != null ? `${q.changePct >= 0 ? "+" : ""}${q.changePct.toFixed(2)}%` : "—"}
        </span>
      </>
    );
  };

  // 链路面板数据
  const lastSnap = mh.length ? mh[mh.length - 1] : null;
  const notesFreshToday = (notes?.symbols ?? []).filter((n) => n.date === today() || n.date === scr?.date).length;
  const pipelines = [
    { name: "行情报价(加密)", mode: "🔴 实时", detail: "Binance WebSocket ~1s 推送 + 8s 缓存", ok: true },
    { name: "行情报价(股票)", mode: "🟡 准实时", detail: HAS_BACKEND ? "后端缓存 30s + 5-10s 轮询" : "公共代理 + 30s 缓存 + 5-10s 轮询(免费源有交易所级延迟)", ok: true },
    { name: "盘前/盘后(美股)", mode: "🟡 准实时", detail: "Yahoo 扩展时段,30s 轮询", ok: true },
    { name: "指数 / 恐惧贪婪", mode: "🟡 准实时", detail: "60s / 10min 轮询", ok: true },
    { name: "每日选股 screener", mode: "🔁 Routine", detail: `Actions 每交易日 22:30 UTC · 最新 ${scr?.date ?? "—"}`, ok: scr ? scr.date >= new Date(Date.now() - 4 * 86400_000).toISOString().slice(0, 10) : null },
    { name: "AI 解读 stock-notes", mode: "🔁 Routine", detail: `OpenClaw 每交易日 16:30(LA)· 更新 ${ago(notes?.updated_at)} · 今日已覆盖 ${notesFreshToday} 只`, ok: notes ? Date.now() - new Date(notes.updated_at).getTime() < 36 * 3600_000 : null },
    { name: "市场快照历史", mode: "🔁 Routine", detail: `Actions 每交易日×2 · 最新 ${lastSnap?.date ?? "—"}`, ok: lastSnap ? Date.now() - new Date(lastSnap.at).getTime() < 3 * 86400_000 : null },
    { name: "SA LP 13F 持仓", mode: "🔁 Routine", detail: `SEC 周检(一/四)· 当前期 ${fund?.asof ?? "—"}(13F 固有 ≤45 天延迟)`, ok: Boolean(fund) },
    { name: "日报 Issue", mode: "🔁 Routine", detail: "Actions 每交易日 23:30 UTC → GitHub Issue(邮件)", ok: true },
    { name: "量化情报 feed", mode: "🔁 Routine", detail: `alpha-routine + OpenClaw 投递 · ${idx?.freshness?.stale ? "陈旧 ⚠" : "新鲜"}`, ok: idx ? !idx.freshness?.stale : null },
  ];

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>← 返回</Link>
        <h1>📋 总览</h1>
        <span className="tag">链路状态 · 自选池 · 看多全名单 · SA LP 持仓 · AI 覆盖,一屏看完</span>
        <a href="https://github.com/Edwardwang66/stock-analysis/issues?q=is%3Aissue+label%3Adaily-digest" target="_blank" rel="noreferrer"
          className="btn" style={{ marginLeft: "auto", background: "transparent", border: "1px solid var(--border)", color: MUT }}>📬 历史日报</a>
        <Link href="/tracker/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🎯 追踪</Link>
      </div>

      {loading ? <div className="loading">加载中…</div> : (
        <>
          {/* ① 数据链路 */}
          <div className="section">
            <h2>① 数据链路(哪些实时 · 哪些靠 Routine)</h2>
            <table>
              <thead><tr><th>链路</th><th>模式</th><th>说明 / 新鲜度</th></tr></thead>
              <tbody>
                {pipelines.map((p) => (
                  <tr key={p.name}>
                    <td><Dot ok={p.ok} />{p.name}</td>
                    <td>{p.mode}</td>
                    <td className="src">{p.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ② 云端自选池 */}
          <div className="section">
            <h2>② 云端自选池(OpenClaw 每日必析)<span className="src" style={{ marginLeft: 8 }}>改 feed/watchlist.json 即增删</span></h2>
            <table>
              <thead><tr><th>标的</th><th>现价 / 当日</th><th>AI 解读</th></tr></thead>
              <tbody>
                {wl.map((s) => (
                  <tr key={s}>
                    <td><Link href={`/symbol/?s=${encodeURIComponent(s)}`} style={{ color: "var(--accent)" }}>{nameOf(s)}</Link> <span className="src">{s}</span></td>
                    <td>{qCell(s)}</td>
                    <td>{noteCell(s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ③ 今日看多全名单 */}
          <div className="section">
            <h2>③ 今日看多 ≥{scr?.threshold ?? 50}(全部 {scr?.count ?? 0} 只 · {scr?.date ?? "—"})
              <Link href="/tracker/" className="src" style={{ marginLeft: 10, color: "var(--accent)" }}>→ 历史持仓与胜率</Link>
            </h2>
            {!scr?.items?.length ? <p className="src">暂无清单(休市或任务未跑)。</p> : (
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead><tr><th>#</th><th>代码</th><th>名称</th><th>评分</th><th>现价 / 当日</th><th>AI 解读</th></tr></thead>
                  <tbody>
                    {scr.items.slice().sort((a, b) => b.score - a.score).map((r, i) => (
                      <tr key={r.symbol}>
                        <td className="muted">{i + 1}</td>
                        <td><Link href={`/symbol/?s=US:${r.symbol}`} style={{ color: "var(--accent)" }}>{r.symbol}</Link></td>
                        <td>{r.name}</td>
                        <td><strong>{r.score}</strong></td>
                        <td>{qCell(`US:${r.symbol}`)}</td>
                        <td>{noteCell(`US:${r.symbol}`)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ④ SA LP 持仓 */}
          <div className="section">
            <h2>④ 🦅 Situational Awareness LP(13F · {fund?.asof ?? "—"})
              <Link href="/intel/" className="src" style={{ marginLeft: 10, color: "var(--accent)" }}>→ 完整持仓与情报</Link>
            </h2>
            {!fund ? <p className="src">暂无数据。</p> : (
              <table>
                <thead><tr><th>#</th><th>标的</th><th>类型</th><th>仓位占比</th><th>现价 / 当日</th><th>AI 解读</th></tr></thead>
                <tbody>
                  {fund.positions.slice(0, 10).map((p, i) => {
                    const tot = fund.summary?.total_value || 1;
                    return (
                      <tr key={p.ticker + i}>
                        <td className="muted">{i + 1}</td>
                        <td>{p.ticker.includes(":")
                          ? <Link href={`/symbol/?s=${encodeURIComponent(p.ticker)}`} style={{ color: "var(--accent)" }}>{p.ticker.replace(/^US:/, "")}</Link>
                          : p.ticker} <span className="src">{p.name}</span></td>
                        <td><span className="badge" style={p.type.includes("Put") ? { borderColor: DOWN, color: DOWN } : undefined}>{p.type}</span></td>
                        <td>{((p.value / tot) * 100).toFixed(1)}%</td>
                        <td>{p.ticker.includes(":") ? qCell(p.ticker) : "—"}</td>
                        <td>{p.ticker.includes(":") ? noteCell(p.ticker) : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          <div className="disclaimer">
            ✅=当日已有 AI 解读 · 🕓=旧解读 · ❌=缺(日报会点名)。AI 解读由 OpenClaw 按
            routines/openclaw-daily-tasks.md 每交易日投递;汇总报告随日报 Issue 邮件送达。
            全部信息参考,<strong>非投资建议</strong>。
          </div>
        </>
      )}
    </div>
  );
}
