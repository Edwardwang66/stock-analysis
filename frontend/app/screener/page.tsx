"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getScreener, type ScreenerList } from "@/lib/feed";

const IDX_LABEL: Record<string, string> = { SP500: "标普500", NDX100: "纳指100" };
type Filter = "ALL" | "SP500" | "NDX100";

export default function ScreenerPage() {
  const [data, setData] = useState<ScreenerList | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("ALL");

  useEffect(() => {
    let alive = true;
    getScreener().then((d) => { if (alive) { setData(d); setLoading(false); } });
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
        <span className="tag">标普500 + 纳指100 · 非 LLM 规则化评分</span>
      </div>

      {loading ? <div className="loading">加载中…</div> : !data || !data.items.length ? (
        <div className="hint">暂无清单。每个交易日美股收盘后(约北京时间次日 06:30)自动生成;也可在 GitHub Actions 手动触发 <code>Daily screener</code>。</div>
      ) : (
        <>
          <div className="toolbar">
            <div className="stat">
              <span>日期 {data.date}</span>
              <span>扫描 {data.scanned}/{data.universe_size}</span>
              <span className="up">命中 {data.count} 只(≥{data.threshold})</span>
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
                <tr><th>#</th><th>代码</th><th>名称</th><th>评分</th><th>结论</th><th>价格</th><th>涨跌%</th><th>RSI</th><th>指数</th></tr>
              </thead>
              <tbody>
                {items.map((r, i) => (
                  <tr key={r.symbol}>
                    <td className="muted">{i + 1}</td>
                    <td><Link href={`/symbol/?s=US:${r.symbol}`} style={{ color: "var(--accent)" }}>{r.symbol}</Link></td>
                    <td>{r.name}</td>
                    <td><strong>{r.score}</strong></td>
                    <td><span className="badge">{r.verdict}</span></td>
                    <td>{r.price}</td>
                    <td className={r.change_pct >= 0 ? "up" : "down"}>{r.change_pct >= 0 ? "+" : ""}{r.change_pct.toFixed(2)}</td>
                    <td>{r.rsi14}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{r.indices.map((x) => IDX_LABEL[x] || x).join("·")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="disclaimer">
        评分为<strong>规则化技术指标</strong>(均线/RSI/MACD/布林,范围 -100..100),<strong>仅供信息参考,不构成投资建议</strong>(Not financial advice)。
        每日清单同时通过 GitHub Issue 推送(已指派给仓库所有者,GitHub 邮件通知)。数据源 Yahoo Finance · 生成 {data?.generated_at?.slice(0, 16)?.replace("T", " ") ?? "—"}。
      </div>
    </div>
  );
}
