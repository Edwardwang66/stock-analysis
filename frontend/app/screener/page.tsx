"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, type Quote } from "@/lib/datasource";
import { getScreener, type ScreenerList } from "@/lib/feed";
import { getRsRanks, type RsTable } from "@/lib/feed";
import { fmtDateTime, fmtTime, useTz } from "@/lib/timefmt";
import LangSelect from "@/components/LangSelect";

const IDX_LABEL: Record<string, string> = { SP500: "标普500", NDX100: "纳指100" };
type Filter = "ALL" | "SP500" | "NDX100";
const LIVE_MAX = 60; // 控制公共代理压力上限

export default function ScreenerPage() {
  const [rsT, setRsT] = useState<RsTable | null>(null);
  useEffect(() => { getRsRanks().then(setRsT).catch(() => {}); }, []);
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

  const items = useMemo(() => {
    const all = data?.items ?? [];
    return filter === "ALL" ? all : all.filter((x) => x.indices.includes(filter));
  }, [data, filter]);

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>📈 每日选股 · 技术评分 ≥ {data?.threshold ?? 50}</h1>
        <LangSelect />
        <span className="tag">标普500 + 纳指100 · 非 LLM 规则化评分</span>
      </div>

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
                <tr><th>#</th><th>代码</th><th>名称</th><th>评分</th><th>RS</th><th>距52周高</th><th>结论</th><th>价格</th><th>涨跌%</th><th>RSI</th><th>指数</th></tr>
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
