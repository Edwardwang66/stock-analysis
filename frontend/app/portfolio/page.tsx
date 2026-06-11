"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getQuotes, type Quote } from "@/lib/datasource";
import { getForex, type Forex } from "@/lib/forex";
import { nameOf } from "@/lib/markets";
import { addHolding, getHoldings, removeHolding, type Holding } from "@/lib/portfolio";
import { agoShort, fmtTime, useNow, useTz } from "@/lib/timefmt";
import LiveClock from "@/components/LiveClock";
import LangSelect from "@/components/LangSelect";
import { useLang } from "@/lib/names";
import { useNightQuotes } from "@/lib/nightquotes";
import { NAME_DB } from "@/lib/names";
import { marketStatus } from "@/lib/marketstatus";

const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !isFinite(n) ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: d });

export default function PortfolioPage() {
  const lang = useLang();
  const night = useNightQuotes();
  const [list, setList] = useState<Holding[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [sym, setSym] = useState("");
  const [qty, setQty] = useState("");
  const [cost, setCost] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const tzKey = useTz();
  const nowTick = useNow(1000);
  const [fx, setFx] = useState<Forex | null>(null);
  const [toUSD, setToUSD] = useState(false);

  useEffect(() => { getForex("USD").then(setFx).catch(() => {}); }, []);

  // 货币 → USD 系数(fx.rates 为 USD→C;USDT 视为 ≈USD)
  const usdRate = (cur: string): number | null => {
    if (cur === "USD" || cur === "USDT") return 1;
    const r = fx?.rates?.[cur];
    return r ? 1 / r : null;
  };

  useEffect(() => {
    const sync = () => setList(getHoldings());
    sync();
    window.addEventListener("portfolio-changed", sync);
    return () => window.removeEventListener("portfolio-changed", sync);
  }, []);

  // 实时估值:统一数据层,30s 跟首页同节奏
  useEffect(() => {
    const syms = Array.from(new Set(list.map((h) => h.symbol)));
    if (!syms.length) return;
    let alive = true;
    const load = () => getQuotes(syms, (q) => {
      if (alive) setQuotes((prev) => ({ ...prev, [q.symbol]: q }));
    }).then(() => { if (alive) setUpdatedAt(new Date()); }).catch(() => {});
    load();
    const id = window.setInterval(() => { if (!document.hidden) load(); }, 30_000);
    return () => { alive = false; window.clearInterval(id); };
  }, [list]);

  const rows = useMemo(() => list.map((h) => {
    const q = quotes[h.symbol];
    const price = q?.price ?? null;
    const mv = price != null ? price * h.qty : null;
    const costTotal = h.cost * h.qty;
    const pnl = mv != null ? mv - costTotal : null;
    const pnlPct = pnl != null && costTotal !== 0 ? (pnl / costTotal) * 100 : null;
    return { ...h, q, price, mv, costTotal, pnl, pnlPct, currency: q?.currency || "" };
  }), [list, quotes]);

  // 按币种分桶合计(避免 USD/HKD/CNY/USDT 直接相加的错误口径)
  const totals = useMemo(() => {
    const m = new Map<string, { mv: number; cost: number; pnl: number }>();
    for (const r of rows) {
      if (r.mv == null || !r.currency) continue;
      const t = m.get(r.currency) ?? { mv: 0, cost: 0, pnl: 0 };
      t.mv += r.mv; t.cost += r.costTotal; t.pnl += r.pnl ?? 0;
      m.set(r.currency, t);
    }
    return Array.from(m.entries());
  }, [rows]);

  const add = () => {
    const q = Number(qty), c = Number(cost);
    if (!sym.includes(":") || !(q > 0) || !(c >= 0)) return;
    addHolding(sym, q, c);
    setSym(""); setQty(""); setCost("");
  };

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <Link href="/desk/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>📋</Link>
        <h1>💼 模拟持仓</h1>
        <LangSelect />
        <span className="tag">本地存储 · 实时估值与首页同源 · 非真实账户</span>
        <span style={{ marginLeft: "auto" }}><LiveClock /></span>
        {updatedAt && <span className="src">估值更新 {fmtTime(updatedAt, tzKey)}({agoShort(updatedAt, nowTick)})</span>}
      </div>

      <div className="section">
        <h2>添加持仓</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input list="pf-syms" placeholder="标的(如 US:AAPL)" value={sym}
            onChange={(e) => setSym(e.target.value.trim().toUpperCase())}
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: "9px 12px", width: 200 }} />
          <datalist id="pf-syms">
            {Object.entries(NAME_DB).map(([sym2, [zh, en]]) => (
              <option key={sym2} value={sym2}>{zh === en ? zh : `${zh} ${en}`}</option>
            ))}
          </datalist>
          <input type="number" inputMode="decimal" placeholder="数量" value={qty} onChange={(e) => setQty(e.target.value)}
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: "9px 12px", width: 120 }} />
          <input type="number" inputMode="decimal" placeholder="成本价" value={cost} onChange={(e) => setCost(e.target.value)}
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: "9px 12px", width: 120 }} />
          <button className="btn" onClick={add} disabled={!sym.includes(":") || !(Number(qty) > 0)}>添加</button>
        </div>
      </div>

      {rows.length > 0 ? (
        <>
          {/* 持仓占比横条(按市值,跨币种未折算仅示意) */}
          {(() => {
            const withMv = rows.filter((r) => r.mv != null && r.mv > 0);
            if (withMv.length < 2) return null;
            const total = withMv.reduce((s2, r) => s2 + (r.mv as number), 0);
            const palette = ["#4c8dff", "#26a69a", "#f7b500", "#ab47bc", "#26c6da", "#ef5350", "#9ccc65", "#ff8a65", "#7986cb", "#787b86"];
            const sorted = [...withMv].sort((a, b) => (b.mv as number) - (a.mv as number));
            return (
              <div className="section" style={{ marginBottom: 12 }}>
                <h2>占比<span className="src" style={{ marginLeft: 8 }}>按市值 · 跨币种未折算</span></h2>
                <div style={{ display: "flex", height: 14, borderRadius: 7, overflow: "hidden", border: "1px solid var(--border)" }}>
                  {sorted.map((r, i) => (
                    <div key={r.id} title={`${nameOf(r.symbol, lang)} ${((r.mv as number) / total * 100).toFixed(1)}%`}
                      style={{ width: `${(r.mv as number) / total * 100}%`, background: palette[i % palette.length] }} />
                  ))}
                </div>
                <div className="src" style={{ fontSize: 11, marginTop: 5, display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {sorted.slice(0, 8).map((r, i) => (
                    <span key={r.id}><span style={{ color: palette[i % palette.length] }}>■</span> {nameOf(r.symbol, lang)} {((r.mv as number) / total * 100).toFixed(0)}%</span>
                  ))}
                </div>
              </div>
            );
          })()}
          <div className="section" style={{ overflowX: "auto" }}>
            <h2>持仓明细</h2>
            <table>
              <thead>
                <tr><th>标的</th><th>数量</th><th>成本价</th><th>现价</th><th>市值</th><th>盈亏</th><th>盈亏%</th><th>币种</th><th></th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td><Link href={`/symbol/?s=${encodeURIComponent(r.symbol)}`} style={{ color: "var(--accent)" }}>{nameOf(r.symbol, lang)}</Link> <span className="src">{r.symbol}</span></td>
                    <td>{fmt(r.qty, 6)}</td>
                    <td>{fmt(r.cost)}</td>
                    <td>{fmt(r.price)}</td>
                    <td>{fmt(r.mv)}
                      {(() => {
                        const nq = night.map[r.symbol];
                        if (!nq || marketStatus(r.symbol.split(":")[0]).open || r.qty == null) return null;
                        const nmv = nq.mark * r.qty;
                        const d = r.mv ? (nmv / r.mv - 1) * 100 : null;
                        return (
                          <div className="src" style={{ fontSize: 11 }}>
                            🌙 {fmt(nmv)}{d != null && Math.abs(d) >= 0.3 && (
                              <span className={d >= 0 ? "up" : "down"}> {d >= 0 ? "+" : ""}{d.toFixed(1)}%</span>
                            )}
                          </div>
                        );
                      })()}
                    </td>
                    <td className={r.pnl == null ? "muted" : r.pnl >= 0 ? "up" : "down"}>{r.pnl == null ? "—" : `${r.pnl >= 0 ? "+" : ""}${fmt(r.pnl)}`}</td>
                    <td className={r.pnlPct == null ? "muted" : r.pnlPct >= 0 ? "up" : "down"}>{r.pnlPct == null ? "—" : `${r.pnlPct >= 0 ? "+" : ""}${r.pnlPct.toFixed(2)}%`}</td>
                    <td className="muted">{r.currency || "—"}</td>
                    <td><button className="linklike" style={{ color: "var(--down)" }} onClick={() => removeHolding(r.id)}>删除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="section">
            <h2>合计(按币种)
              <label style={{ marginLeft: 12, fontSize: 12, color: "var(--muted)", fontWeight: 400, cursor: "pointer" }}>
                <input type="checkbox" checked={toUSD} onChange={(e) => setToUSD(e.target.checked)} disabled={!fx} style={{ marginRight: 4 }} />
                折算 USD{!fx && "(汇率加载中)"}
              </label>
            </h2>
            <table>
              <thead><tr><th>币种</th><th>总市值</th><th>总成本</th><th>总盈亏</th><th>收益率</th></tr></thead>
              <tbody>
                {totals.map(([cur, t]) => (
                  <tr key={cur}>
                    <td>{cur}</td>
                    <td>{fmt(t.mv)}</td>
                    <td>{fmt(t.cost)}</td>
                    <td className={t.pnl >= 0 ? "up" : "down"}>{t.pnl >= 0 ? "+" : ""}{fmt(t.pnl)}</td>
                    <td className={t.pnl >= 0 ? "up" : "down"}>{t.cost ? `${t.pnl >= 0 ? "+" : ""}${((t.pnl / t.cost) * 100).toFixed(2)}%` : "—"}</td>
                  </tr>
                ))}
                {toUSD && fx && (() => {
                  let mv = 0, cost = 0, skipped: string[] = [];
                  for (const [cur, t] of totals) {
                    const r = usdRate(cur);
                    if (r == null) { skipped.push(cur); continue; }
                    mv += t.mv * r; cost += t.cost * r;
                  }
                  const pnl = mv - cost;
                  return (
                    <tr style={{ borderTop: "2px solid var(--border)" }}>
                      <td><strong>≈ USD 合计</strong>{skipped.length > 0 && <span className="src">(未含 {skipped.join("/")})</span>}</td>
                      <td><strong>{fmt(mv)}</strong></td>
                      <td>{fmt(cost)}</td>
                      <td className={pnl >= 0 ? "up" : "down"}><strong>{pnl >= 0 ? "+" : ""}{fmt(pnl)}</strong></td>
                      <td className={pnl >= 0 ? "up" : "down"}>{cost ? `${pnl >= 0 ? "+" : ""}${((pnl / cost) * 100).toFixed(2)}%` : "—"}</td>
                    </tr>
                  );
                })()}
              </tbody>
            </table>
            <p className="src" style={{ marginTop: 8 }}>
              {toUSD && fx
                ? `折算口径:${fx.source} ${fx.date} 中间价;USDT 视为 ≈1 USD。仅供参考。`
                : "默认不跨币种合并(避免汇率口径误导);勾选「折算 USD」按 ECB 中间价估算。"}
            </p>
          </div>
        </>
      ) : (
        <div className="hint">还没有持仓。在上方添加(支持美股/港股/A股/加密/指数,数量可小数)。数据只存在你的浏览器里。</div>
      )}

      <div className="disclaimer">模拟持仓仅供学习与跟踪,**非真实账户、非投资建议**(Not financial advice)。</div>
    </div>
  );
}
