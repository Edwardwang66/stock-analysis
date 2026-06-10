"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, type Quote } from "@/lib/datasource";
import { getScreenerHistory, type TrackedDay } from "@/lib/feed";
import TzSelect from "@/components/TzSelect";
import LiveClock from "@/components/LiveClock";
import { agoShort, fmtTime, useNow, useTz } from "@/lib/timefmt";

const AUTO_DAYS = 2;    // 最近 N 个交易日自动实时估值;更早的按需点击估值(控代理压力)

const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n as number) ? "—" : (n as number).toLocaleString(undefined, { maximumFractionDigits: d });

export default function TrackerPage() {
  const [hist, setHist] = useState<TrackedDay[]>([]);
  const [live, setLive] = useState<Record<string, Quote>>({});
  const [valuedDays, setValuedDays] = useState<Set<string>>(new Set());
  const [loadingDays, setLoadingDays] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const tzKey = useTz(); // 时区切换时间戳联动
  const nowTick = useNow(1000);

  const valueDay = (d: TrackedDay) => {
    setLoadingDays((prev) => new Set(prev).add(d.date));
    const syms = d.items.map((x) => x.symbol);
    getQuotes(syms, (q) => setLive((prev) => ({ ...prev, [q.symbol]: q })))
      .then(() => {
        setValuedDays((prev) => new Set(prev).add(d.date));
        setUpdatedAt(new Date());
      })
      .catch(() => {})
      .finally(() => setLoadingDays((prev) => { const n = new Set(prev); n.delete(d.date); return n; }));
  };

  useEffect(() => {
    let alive = true;
    getScreenerHistory().then((h) => {
      if (!alive) return;
      const days = (h ?? []).slice().sort((a, b) => b.date.localeCompare(a.date));
      setHist(days);
      setLoading(false);
      days.slice(0, AUTO_DAYS).forEach((d) => valueDay(d));
    });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 每个「当日持仓」的统计(只对已估值的天计算)
  const dayStats = useMemo(() => hist.map((d) => {
    const valued = valuedDays.has(d.date);
    const rows = d.items.map((it) => {
      const q = live[it.symbol];
      const ret = valued && q?.price != null && it.pick_price ? (q.price / it.pick_price - 1) * 100 : null;
      return { ...it, price: valued ? (q?.price ?? null) : null, ret };
    });
    const withRet = rows.filter((r) => r.ret != null) as (typeof rows[number] & { ret: number })[];
    const wins = withRet.filter((r) => r.ret > 0).length;
    const avg = withRet.length ? withRet.reduce((s, r) => s + r.ret, 0) / withRet.length : null;
    return { ...d, rows, wins, n: withRet.length, avg, valued };
  }), [hist, live, valuedDays]);

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
        <span className="tag">每日达标选股全量入库 = 当日持仓 · 逐日回看「选中后涨没涨」</span>
        <span style={{ marginLeft: "auto" }}><LiveClock /></span>
        <TzSelect />
        {updatedAt && <span className="src">估值 {fmtTime(updatedAt, tzKey)}({agoShort(updatedAt, nowTick)})</span>}
      </div>

      {overall && (
        <div className="toolbar">
          <div className="stat">
            <span>已估值样本 {overall.n} 笔</span>
            <span className="up">胜率 {(overall.wins / overall.n * 100).toFixed(0)}%</span>
            <span className={overall.avg >= 0 ? "up" : "down"}>平均 {overall.avg >= 0 ? "+" : ""}{overall.avg.toFixed(2)}%</span>
            <span className="src">(自选中收盘价至今;最近 {AUTO_DAYS} 天自动估值,更早的逐日点「估值」)</span>
          </div>
        </div>
      )}

      {loading ? <div className="loading">加载中…</div> : !dayStats.length ? (
        <div className="hint">
          还没有追踪数据。daily-digest 工作流每个交易日美股收盘后把当日达标(现行 ≥80 分)选股全量入库,
          次日起这里按「当日持仓」逐日显示表现。也可在 GitHub Actions 手动触发 <code>Daily digest</code>。
        </div>
      ) : dayStats.map((d, di) => (
        <div className="section" key={d.date}>
          <h2>
            {d.date} <span className="src">美东交易日 · 持仓 {d.items.length} 只</span>
            {di === 0 && <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>最新</span>}
            {d.valued && d.n > 0 && (
              <span className="src" style={{ marginLeft: 10 }}>
                命中 {d.wins}/{d.n} · 平均 <span className={d.avg! >= 0 ? "up" : "down"}>{d.avg! >= 0 ? "+" : ""}{d.avg!.toFixed(2)}%</span>
              </span>
            )}
            {!d.valued && (
              <button className="btn subtle" style={{ marginLeft: 10, padding: "3px 12px", fontSize: 12 }}
                disabled={loadingDays.has(d.date)} onClick={() => valueDay(d)}>
                {loadingDays.has(d.date) ? "估值中…" : "⚡ 实时估值"}
              </button>
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
                      {r.ret == null ? (d.valued ? "—" : "待估值") : `${r.ret >= 0 ? "+" : ""}${r.ret.toFixed(2)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <div className="disclaimer">
        「选中价」= 入选当日(美东交易日)收盘价;日期均为美东交易日;收益按实时价计算,未含交易成本。历史保留 60 个交易日,每日全量(≥阈值一只不落)。
        评分为规则化技术指标(v2 十因子),<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。
      </div>
    </div>
  );
}
