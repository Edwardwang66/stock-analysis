"use client";
import { useEffect, useState } from "react";
import { getFundamentals, type Fundamentals } from "@/lib/fundamentals";

const UP = "#26a69a", DOWN = "#ef5350";

function money(v: number | null, unit: string): string {
  if (v == null) return "—";
  if (unit === "USD/shares") return `$${v.toFixed(2)}`;
  const a = Math.abs(v), s = v < 0 ? "-" : "";
  if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(2)}M`;
  return `${s}$${a.toFixed(0)}`;
}

export default function Fundamentals({ symbol }: { symbol: string }) {
  const [market, code] = symbol.split(":");
  const [data, setData] = useState<Fundamentals | null>(null);
  const [state, setState] = useState<"load" | "ok" | "none">("load");

  useEffect(() => {
    if (market !== "US") { setState("none"); return; }
    let alive = true;
    setState("load");
    getFundamentals(code)
      .then((d) => { if (alive) { setData(d); setState(d ? "ok" : "none"); } })
      .catch(() => alive && setState("none"));
    return () => { alive = false; };
  }, [symbol, market, code]);

  if (market !== "US" || state === "none") return null;

  return (
    <div className="section">
      <h2>基本面财报 <span className="badge" style={{ marginLeft: 8, fontSize: 11, borderColor: UP, color: UP }}>SEC 官方</span></h2>
      {state === "load" ? <div className="loading">从 SEC EDGAR 拉取财报中…</div> : data && (
        <>
          <table>
            <thead>
              <tr><th>科目</th><th>最近年度</th><th>同比 YoY</th><th>期间</th></tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.key}>
                  <th>{r.label}</th>
                  <td>{money(r.value, r.unit)}</td>
                  <td style={{ color: r.yoyPct == null ? "var(--muted)" : r.yoyPct >= 0 ? UP : DOWN }}>
                    {r.yoyPct == null ? "—" : `${r.yoyPct >= 0 ? "+" : ""}${r.yoyPct.toFixed(1)}%`}
                  </td>
                  <td className="muted">{r.fy || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="src" style={{ marginTop: 8 }}>
            数据源:SEC EDGAR XBRL(美国证监会官方申报,companyconcept 端点,无 key)。
            年度口径取最近完整财年(10-K);仅美国注册公司有 XBRL 申报。仅供信息参考,非投资建议。
          </p>
        </>
      )}
    </div>
  );
}
