"use client";
// ⏰ 告警中心:价格提醒统一管理(纯前端 localStorage;闭市时夜盘永续价也参与触发)。
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { addAlert, clearTriggered, getAlerts, removeAlert, type PriceAlert } from "@/lib/alerts";
import { getQuotes, type Quote } from "@/lib/datasource";
import { nameOf } from "@/lib/markets";
import { useLang } from "@/lib/names";
import { useNightQuotes } from "@/lib/nightquotes";
import LangSelect from "@/components/LangSelect";

export default function AlertsPage() {
  const lang = useLang();
  const night = useNightQuotes();
  const [list, setList] = useState<PriceAlert[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote | null>>({});
  const [sym, setSym] = useState("");
  const [target, setTarget] = useState("");

  const refresh = () => setList(getAlerts());
  useEffect(() => {
    refresh();
    const h = () => refresh();
    window.addEventListener("alerts-changed", h);
    return () => window.removeEventListener("alerts-changed", h);
  }, []);

  useEffect(() => {
    const syms = Array.from(new Set(list.map((a) => a.symbol)));
    if (!syms.length) return;
    getQuotes(syms, (q) => setQuotes((prev) => ({ ...prev, [q.symbol]: q }))).catch(() => {});
  }, [list]);

  const active = useMemo(() => list.filter((a) => !a.triggeredAt), [list]);
  const fired = useMemo(() => list.filter((a) => a.triggeredAt).sort((a, b) => (b.triggeredAt ?? 0) - (a.triggeredAt ?? 0)), [list]);

  const add = () => {
    const s = sym.trim().toUpperCase();
    const t = Number(target);
    if (!s.includes(":") || !(t > 0)) return;
    addAlert(s, t, quotes[s]?.price ?? null);
    setSym(""); setTarget("");
  };

  const row = (a: PriceAlert) => {
    const q = quotes[a.symbol];
    const nq = night.map[a.symbol];
    const cur = q?.price ?? null;
    const dist = cur ? ((a.target / cur - 1) * 100) : null;
    return (
      <tr key={a.id}>
        <td><Link href={`/symbol/?s=${encodeURIComponent(a.symbol)}`} style={{ color: "var(--accent)" }}>{nameOf(a.symbol, lang)}</Link>
          <span className="src" style={{ marginLeft: 6 }}>{a.symbol}</span></td>
        <td>{a.dir === "above" ? "≥" : "≤"} {a.target}</td>
        <td>{cur != null ? cur.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}
          {nq && <span className="src" style={{ marginLeft: 6 }}>🌙 {nq.mark.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>}</td>
        <td className={dist == null ? "muted" : Math.abs(dist) < 2 ? "up" : undefined}>
          {dist == null ? "—" : `${dist >= 0 ? "+" : ""}${dist.toFixed(1)}%`}
        </td>
        <td className="muted" style={{ fontSize: 12 }}>
          {a.triggeredAt ? `已触发 @${a.triggeredPrice}(${new Date(a.triggeredAt).toLocaleString()})` : "监控中(含夜盘)"}
        </td>
        <td><button className="linklike" style={{ color: "var(--down)" }} onClick={() => removeAlert(a.id)}>删除</button></td>
      </tr>
    );
  };

  return (
    <div className="container">
      <div className="header">
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--muted)" }}>← 返回</Link>
        <h1>⏰ 告警中心</h1>
        <span className="tag">价格提醒 · 30s 轮询 · 闭市时夜盘永续价也触发 · 数据存本机</span>
        <span style={{ marginLeft: "auto" }} />
        <LangSelect />
      </div>

      <div className="section">
        <h2>新建提醒</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input value={sym} onChange={(e) => setSym(e.target.value)} placeholder="代码,如 US:MU"
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: "9px 12px", width: 160 }} />
          <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="目标价" inputMode="decimal"
            style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", borderRadius: 8, padding: "9px 12px", width: 120 }} />
          <button className="btn" onClick={add} disabled={!sym.includes(":") || !(Number(target) > 0)}>添加</button>
          <span className="src">方向自动:目标低于现价=跌破提醒,高于=突破提醒。</span>
        </div>
      </div>

      <div className="section" style={{ overflowX: "auto" }}>
        <h2>监控中({active.length})</h2>
        {active.length ? (
          <table>
            <thead><tr><th>标的</th><th>条件</th><th>现价</th><th>距目标</th><th>状态</th><th></th></tr></thead>
            <tbody>{active.map(row)}</tbody>
          </table>
        ) : <p className="src">暂无监控中的提醒。个股页与上方均可新建。</p>}
      </div>

      {fired.length > 0 && (
        <div className="section" style={{ overflowX: "auto" }}>
          <h2>已触发({fired.length})
            <button className="linklike" style={{ marginLeft: 10, fontSize: 12 }} onClick={() => clearTriggered()}>清空已触发</button>
          </h2>
          <table>
            <thead><tr><th>标的</th><th>条件</th><th>现价</th><th>距目标</th><th>状态</th><th></th></tr></thead>
            <tbody>{fired.map(row)}</tbody>
          </table>
        </div>
      )}

      <div className="disclaimer">提醒存于浏览器本机(localStorage),换设备不同步;页面开着才会轮询触发。非投资建议。</div>
    </div>
  );
}
