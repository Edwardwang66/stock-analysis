"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, type Quote } from "@/lib/datasource";
import { getScreener, type ScreenerList } from "@/lib/feed";
import { getRsHistory, getRsRanks, type RsHistoryDay, type RsTable } from "@/lib/feed";
import { fmtDateTime, fmtTime, useTz } from "@/lib/timefmt";
import LangSelect from "@/components/LangSelect";
import { useLang } from "@/lib/names";

const IDX_LABEL: Record<string, string> = { SP500: "标普500", NDX100: "纳指100" };
type Filter = "ALL" | "SP500" | "NDX100";
const LIVE_MAX = 60; // 控制公共代理压力上限

export default function ScreenerPage() {
  const lang = useLang();
  const [rsT, setRsT] = useState<RsTable | null>(null);
  useEffect(() => { getRsRanks().then(setRsT).catch(() => {}); }, []);
  const [rsH, setRsH] = useState<RsHistoryDay[]>([]);
  useEffect(() => { getRsHistory().then((h) => setRsH(h ?? [])).catch(() => {}); }, []);
  const near52 = (() => {
    if (!rsT?.ranks) return [] as { sym: string; dd: number; rs: number | null }[];
    return Object.entries(rsT.ranks)
      .flatMap(([sym, v]) => (v.w52dd != null && v.w52dd >= -3 ? [{ sym, dd: v.w52dd, rs: v.rs }] : []))
      .sort((a, b) => b.dd - a.dd).slice(0, 24);
  })();
  const [data, setData] = useState<ScreenerList | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("ALL");
  // 与首页同一数据层取实时报价,覆盖清单生成时的冻结价(跨页一致)
  const [live, setLive] = useState<Record<string, Quote>>({});
  const [liveAt, setLiveAt] = useState<Date | null>(null);
  const tzKey = useTz();

  useEffect(() => {
    let alive = true;
    getScreener().then((d) => {
      if (!alive) return;
      setData(d); setLoading(false);
      const syms = (d?.items ?? []).slice(0, LIVE_MAX).map((x) => `US:${x.symbol}`);
      if (syms.length) {
        getQuotes(syms, (q) => {
          if (alive) setLive((prev) => ({ ...prev, [q.symbol.replace(/^US:/, "")]: q }));
        }).then(() => { if (alive) setLiveAt(new Date()); }).catch(() => {});
      }
    });
    return () => { alive = false; };
  }, []);

  type SK = "score" | "rs" | "w52" | "pct" | "rsi";
  const [sortK, setSortK] = useState<SK>("score");
  const [sortAsc, setSortAsc] = useState(false);
  const clickSort = (k: SK) => {
    if (sortK === k) setSortAsc((v) => !v);
    else { setSortK(k); setSortAsc(false); }
  };
  const items = useMemo(() => {
    const all = data?.items ?? [];
    const base = filter === "ALL" ? all : all.filter((x) => x.indices.includes(filter));
    const val = (x: typeof all[number]): number => {
      const k = rsT?.ranks?.[x.symbol];
      switch (sortK) {
        case "rs": return k?.rs ?? -1;
        case "w52": return k?.w52dd ?? -999;
        case "pct": return x.change_pct;
        case "rsi": return x.rsi14;
        default: return x.score;
      }
    };
    return [...base].sort((a, b) => (sortAsc ? val(a) - val(b) : val(b) - val(a)));
  }, [data, filter, sortK, sortAsc, rsT]);
  const arrow = (k: SK) => (sortK === k ? (sortAsc ? " ↑" : " ↓") : "");

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <Link href="/desk/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>📋</Link>
        <h1>📈 每日选股 · 技术评分 ≥ {data?.threshold ?? 50}</h1>
        <LangSelect />
        <span className="tag">标普500 + 纳指100 · 非 LLM 规则化评分</span>
      </div>

      {rsH.length >= 3 && (() => {
        const a0 = rsH[Math.max(0, rsH.length - 8)].rs, b0 = rsH[rsH.length - 1].rs;
        const moves = Object.keys(b0)
          .flatMap((k) => (a0[k] != null ? [{ sym: k, d: b0[k] - a0[k], rs: b0[k] }] : []))
          .filter((x) => Math.abs(x.d) >= 8)
          .sort((x, y) => y.d - x.d);
        if (!moves.length) return null;
        return (
          <div className="section" style={{ marginTop: 8 }}>
            <h2>🧲 RS 迁移榜<span className="src" style={{ marginLeft: 10 }}>{rsH.length} 天窗口 · 分位变化 ≥8(↗变强 ↘变弱)</span></h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {moves.slice(0, 10).map((x) => (
                <Link key={x.sym} href={`/symbol/?s=US:${x.sym}`} className="badge"
                  style={{ fontSize: 12, padding: "5px 10px", color: x.d > 0 ? "#26a69a" : "#ef5350" }}>
                  {x.sym} {x.d > 0 ? "↗" : "↘"}{Math.abs(x.d)} → RS{x.rs}
                </Link>
              ))}
              {moves.length > 10 && moves.slice(-4).map((x) => (
                <Link key={x.sym} href={`/symbol/?s=US:${x.sym}`} className="badge"
                  style={{ fontSize: 12, padding: "5px 10px", color: "#ef5350" }}>
                  {x.sym} ↘{Math.abs(x.d)} → RS{x.rs}
                </Link>
              ))}
            </div>
          </div>
        );
      })()}

      {near52.length > 0 && (
        <div className="section" style={{ marginTop: 8 }}>
          <h2>🏔 52周新高接近榜
            <span className="src" style={{ marginLeft: 10 }}>距 52 周高 ≤3%(George-Hwang 动量区)· 全宇宙扫描 · RS 同显</span>
          </h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {near52.map((x) => (
              <Link key={x.sym} href={`/symbol/?s=${encodeURIComponent("US:" + x.sym)}`} className="badge"
                style={{ fontSize: 12, padding: "5px 10px", color: x.dd >= 0 ? "#69f0ae" : "var(--text)" }}>
                {x.sym} {x.dd >= 0 ? "新高" : `${x.dd}%`}{x.rs != null && <span style={{ color: x.rs >= 80 ? "#26a69a" : "#787b86" }}> RS{x.rs}</span>}
              </Link>
            ))}
          </div>
        </div>
      )}

      {data?.date && (
        <div className="hint" style={{ background: "rgba(76,141,255,.08)", borderColor: "rgba(76,141,255,.35)" }}>
          🤖 当日 OpenClaw 汇总报告:
          <a href={`https://github.com/Edwardwang66/stock-analysis/blob/main/feed/screener/analysis-${data.date}.md`}
            target="_blank" rel="noreferrer" style={{ color: "var(--accent)", marginLeft: 6 }}>
            analysis-{data.date}.md →
          </a>
          <span className="src" style={{ marginLeft: 8 }}>(同步嵌入每日 Issue 日报;盘前/收盘前版本同目录)</span>
        </div>
      )}

      {loading ? <div className="loading">加载中…</div> : !data || !data.items.length ? (
        <div className="hint">暂无清单。每个交易日美股收盘后(约北京时间次日 06:30)自动生成;也可在 GitHub Actions 手动触发 <code>Daily screener</code>。</div>
      ) : (
        <>
          <div className="toolbar">
            <div className="stat">
              <span>美东交易日 {data.date}</span>
              <span>扫描 {data.scanned}/{data.universe_size}</span>
              <span className="up">命中 {data.count} 只(≥{data.threshold})</span>
              <span>{liveAt ? `实时价 ${fmtTime(liveAt, tzKey, true)}` : Object.keys(live).length ? "实时价更新中…" : "价格为生成时数据"}</span>
            </div>
            <div className="segmented">
              {(["ALL", "SP500", "NDX100"] as Filter[]).map((f) => (
                <button key={f} className={f === filter ? "active" : ""} onClick={() => setFilter(f)}>
                  {f === "ALL" ? "全部" : IDX_LABEL[f]}
                </button>
              ))}
            </div>
          </div>

          <div className="section" style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr><th>#</th><th>{lang === "en" ? "Code" : "代码"}</th><th>{lang === "en" ? "Name" : "名称"}</th>
                  <th style={{ cursor: "pointer" }} onClick={() => clickSort("score")}>{lang === "en" ? "Score" : "评分"}{arrow("score")}</th>
                  <th style={{ cursor: "pointer" }} onClick={() => clickSort("rs")}>RS{arrow("rs")}</th>
                  <th style={{ cursor: "pointer" }} onClick={() => clickSort("w52")}>{lang === "en" ? "vs 52wH" : "距52周高"}{arrow("w52")}</th>
                  <th>{lang === "en" ? "Verdict" : "结论"}</th><th>{lang === "en" ? "Price" : "价格"}</th>
                  <th style={{ cursor: "pointer" }} onClick={() => clickSort("pct")}>{lang === "en" ? "Chg%" : "涨跌%"}{arrow("pct")}</th>
                  <th style={{ cursor: "pointer" }} onClick={() => clickSort("rsi")}>RSI{arrow("rsi")}</th>
                  <th>{lang === "en" ? "Index" : "指数"}</th></tr>
              </thead>
              <tbody>
                {items.map((r, i) => {
                  const lq = live[r.symbol];
                  const price = lq?.price ?? r.price;
                  const pct = lq?.changePct ?? r.change_pct;
                  return (
                    <tr key={r.symbol}>
                      <td className="muted">{i + 1}</td>
                      <td><Link href={`/symbol/?s=US:${r.symbol}`} style={{ color: "var(--accent)" }}>{r.symbol}</Link></td>
                      <td>{r.name}</td>
                      <td><strong>{r.score}</strong></td>
                      {(() => {
                        const k = rsT?.ranks?.[r.symbol];
                        return (
                          <>
                            <td className={k?.rs != null && k.rs >= 80 ? "up" : undefined}>{k?.rs ?? "—"}</td>
                            <td className={k?.w52dd != null && k.w52dd >= -3 ? "up" : undefined}>
                              {k?.w52dd == null ? "—" : k.w52dd >= 0 ? "新高" : `${k.w52dd}%`}
                            </td>
                          </>
                        );
                      })()}
                      <td><span className="badge">{r.verdict}</span></td>
                      <td>{typeof price === "number" ? price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : price}{lq ? <span className="muted" style={{ fontSize: 10 }}> 实时</span> : null}</td>
                      <td className={pct >= 0 ? "up" : "down"}>{pct >= 0 ? "+" : ""}{pct.toFixed(2)}</td>
                      <td>{r.rsi14}</td>
                      <td className="muted" style={{ fontSize: 12 }}>{r.indices.map((x) => IDX_LABEL[x] || x).join("·")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="disclaimer">
        评分为<strong>规则化技术指标</strong>(均线/RSI/MACD/布林,范围 -100..100),<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。
        每日清单同时通过 GitHub Issue 推送(已指派给仓库所有者,GitHub 邮件通知)。数据源 Yahoo Finance · 生成 {data?.generated_at ? fmtDateTime(data.generated_at, tzKey) : "—"}。
      </div>
    </div>
  );
}
