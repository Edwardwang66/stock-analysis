"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, type Quote } from "@/lib/datasource";
import { getScreenerHistory, type TrackedDay } from "@/lib/feed";

const LIVE_DAYS = 8;    // 对最近 N 个交易日的选股拉实时价
const LIVE_MAX = 80;    // 实时报价标的上限(控代理压力)

const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n as number) ? "—" : (n as number).toLocaleString(undefined, { maximumFractionDigits: d });

export default function TrackerPage() {
  const [hist, setHist] = useState<TrackedDay[]>([]);
  const [live, setLive] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  useEffect(() => {
    let alive = true;
    getScreenerHistory().then((h) => {
      if (!alive) return;
      const days = (h ?? []).slice().sort((a, b) => b.date.localeCompare(a.date));
      setHist(days);
      setLoading(false);
      const syms = Array.from(new Set(
        days.slice(0, LIVE_DAYS).flatMap((d) => d.items.map((x) => x.symbol)),
      )).slice(0, LIVE_MAX);
      if (syms.length) {
        getQuotes(syms, (q) => { if (alive) setLive((prev) => ({ ...prev, [q.symbol]: q })); })
          .then(() => { if (alive) setUpdatedAt(new Date()); }).catch(() => {});
      }
    });
    return () => { alive = false; };
  }, []);

  // 每个交易日的统计:命中率(现价>选中价)+ 平均收益
  const dayStats = useMemo(() => hist.map((d) => {
    const rows = d.items.map((it) => {
      const q = live[it.symbol];
      const ret = q?.price != null && it.pick_price ? (q.price / it.pick_price - 1) * 100 : null;
      return { ...it, price: q?.price ?? null, ret };
    });
    const withRet = rows.filter((r) => r.ret != null) as (typeof rows[number] & { ret: number })[];
    const wins = withRet.filter((r) => r.ret > 0).length;
    const avg = withRet.length ? withRet.reduce((s, r) => s + r.ret, 0) / withRet.length : null;
    return { ...d, rows, wins, n: withRet.length, avg };
  }), [hist, live]);

  const overall = useMemo(() => {
    const all = dayStats.flatMap((d) => d.rows.filter((r) => r.ret != null) as { ret: number }[]);
    if (!all.length) return null;
    const wins = all.filter((r) => r.ret > 0).length;
    return { n: all.length, wins, avg: all.reduce((s, r) => s + r.ret, 0) / all.length };
  }, [dayStats]);

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>🎯 选股追踪</h1>
        <span className="tag">每日 ≥50 分选股自动入库 · 实时验证「第二天涨没涨」</span>
        {updatedAt && <span className="src" style={{ marginLeft: "auto" }}>实时价 {updatedAt.toLocaleTimeString()}</span>}
      </div>

      {overall && (
        <div className="toolbar">
          <div className="stat">
            <span>样本 {overall.n} 笔</span>
            <span className="up">胜率 {(overall.wins / overall.n * 100).toFixed(0)}%</span>
            <span className={overall.avg >= 0 ? "up" : "down"}>平均 {overall.avg >= 0 ? "+" : ""}{overall.avg.toFixed(2)}%</span>
            <span className="src">(自选中收盘价至今,近 {LIVE_DAYS} 个交易日实时计算)</span>
          </div>
        </div>
      )}

      {loading ? <div className="loading">加载中…</div> : !dayStats.length ? (
        <div className="hint">
          还没有追踪数据。daily-digest 工作流每个交易日美股收盘后把当日 ≥50 分选股入库,
          次日起这里自动显示每只的实时表现。也可在 GitHub Actions 手动触发 <code>Daily digest</code>。
        </div>
      ) : dayStats.map((d, di) => (
        <div className="section" key={d.date}>
          <h2>
            {d.date}{di === 0 && <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>最新</span>}
            {d.n > 0 && (
              <span className="src" style={{ marginLeft: 10 }}>
                命中 {d.wins}/{d.n} · 平均 <span className={d.avg! >= 0 ? "up" : "down"}>{d.avg! >= 0 ? "+" : ""}{d.avg!.toFixed(2)}%</span>
              </span>
            )}
          </h2>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr><th>#</th><th>代码</th><th>名称</th><th>评分</th><th>选中价</th><th>现价</th><th>收益</th></tr></thead>
              <tbody>
                {d.rows.slice().sort((a, b) => (b.ret ?? -999) - (a.ret ?? -999)).map((r, i) => (
                  <tr key={r.symbol}>
                    <td className="muted">{i + 1}</td>
                    <td><Link href={`/symbol/?s=${encodeURIComponent(r.symbol)}`} style={{ color: "var(--accent)" }}>{r.symbol.replace(/^US:/, "")}</Link></td>
                    <td>{r.name ?? ""}</td>
                    <td>{r.score ?? "—"}</td>
                    <td>{fmt(r.pick_price)}</td>
                    <td>{fmt(r.price)}</td>
                    <td className={r.ret == null ? "muted" : r.ret >= 0 ? "up" : "down"}>
                      {r.ret == null ? "—" : `${r.ret >= 0 ? "+" : ""}${r.ret.toFixed(2)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <div className="disclaimer">
        「选中价」= 入选当日收盘价;收益按实时价计算,未含交易成本。
        评分为规则化技术指标,<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。
      </div>
    </div>
  );
}
