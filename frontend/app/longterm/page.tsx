"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getLongScore, getMacro, getLongValidation, type LongScore, type LongRow, type MacroDial, type LongValidation } from "@/lib/feed";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";
const num = (x?: number | null, d = 2) => (x == null ? "—" : x.toFixed(d));
const pct = (x?: number | null, d = 1) => (x == null ? "—" : `${(x * 100).toFixed(d)}%`);
const FACTOR_CN: Record<string, string> = {
  gross_profitability: "毛利率", cash_op_to_assets: "现金经营", roic: "ROIC", roe: "ROE",
  net_margin: "净利率", accruals_to_assets: "应计(负)", piotroski_f: "F分",
  earnings_yield: "E/P", ebit_ev: "EBIT/EV", fcf_ev: "FCF/EV", book_to_price: "B/P",
  shareholder_yield: "股东收益",
};
const REGIME: Record<string, { c: string; t: string }> = {
  risk_on: { c: UP, t: "风险偏好" }, neutral: { c: WARN, t: "中性" },
  risk_off: { c: DOWN, t: "避险" }, unknown: { c: MUT, t: "未知" },
};

// 把分数映射成颜色(z 分数:正绿负红)
const zc = (z?: number | null) => (z == null ? MUT : z > 0.3 ? UP : z < -0.3 ? DOWN : MUT);

export default function LongTermDashboard() {
  const [ls, setLs] = useState<LongScore | null>(null);
  const [macro, setMacro] = useState<MacroDial | null>(null);
  const [val, setVal] = useState<LongValidation | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const d = await getLongScore();
    if (!d) { setErr("无法加载 feed/longterm/longscore.json(远端与捆绑快照均失败)。"); return; }
    setLs(d); setErr(null);
    setMacro(await getMacro());
    setVal(await getLongValidation());
  }
  useEffect(() => { load(); const t = setInterval(load, 5 * 60 * 1000); return () => clearInterval(t); }, []);

  const rows = ls?.rows || [];
  const scored = rows.filter((r) => r.long_score != null && !r.exclude);
  const excluded = rows.filter((r) => r.exclude);
  const flagged = rows.filter((r) => !r.exclude && (r.flags?.length || 0) > 0);
  const rg = REGIME[macro?.regime || "unknown"] || REGIME.unknown;

  return (
    <div className="container">
      <div className="header" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <Link href="/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>← 返回</Link>
        <Link href="/intel/" className="btn" style={{ background: "transparent", border: "1px solid var(--border)", color: MUT }}>🛰️ 情报</Link>
        <h1 style={{ margin: 0 }}>🏛️ 长期投资腿(LIS)</h1>
      </div>

      <p style={{ color: MUT, fontSize: 13, lineHeight: 1.6 }}>
        基于 <b>EDGAR PIT 基本面</b> 的质量+价值多因子合成(LongScore)。持有期数月至数年,
        与中频做多做空互补。<b>这是候选清单,非下单信号,非投资建议</b>——上线前须过 7 关验证
        (PIT / Deflated Sharpe / CSCV-PBO / t&gt;3 / 2022 holdout / 正交增量 / 净·扣成本)。
        方法论见 <Link href="https://github.com/edwardwang66/stock-analysis/blob/main/docs/long-term-investment-system.md" style={{ color: UP }}>设计文档</Link>。
      </p>

      {err && <div style={{ color: DOWN, padding: 12, border: `1px solid ${DOWN}`, borderRadius: 8 }}>{err}</div>}

      {/* 验证裁决(诚实优先,放最前)*/}
      {val && (() => {
        const ic = val.summary.ic_long, iv = val.summary.ic_value;
        const sig = ic.t != null && Math.abs(ic.t) >= 2;
        const col = sig ? UP : WARN;
        return (
          <div style={{ border: `1px solid ${col}`, borderRadius: 10, padding: 14, margin: "12px 0", background: "rgba(247,181,0,0.06)" }}>
            <b>🔬 验证裁决(L-5,{val.n_periods} 期 {val.periods[0]?.as_of}…{val.periods[val.periods.length - 1]?.as_of})</b>
            <div style={{ display: "flex", gap: 18, marginTop: 8, flexWrap: "wrap", fontSize: 13 }}>
              <div>LongScore IC <b style={{ color: (ic.mean || 0) > 0 ? UP : DOWN }}>{num(ic.mean, 3)}</b> (t={num(ic.t, 2)}, 命中 {pct(ic.hit, 0)})</div>
              {val.summary.ic_long_orth?.mean != null && (
                <div title="对价格动量+规模正交化后的增量 IC">⊥动量/规模 <b style={{ color: MUT }}>{num(val.summary.ic_long_orth.mean, 3)}</b> (t={num(val.summary.ic_long_orth.t, 2)})</div>
              )}
              <div>质量 IC <b>{num(val.summary.ic_quality.mean, 3)}</b></div>
              <div>价值 IC <b style={{ color: (iv.mean || 0) < 0 ? DOWN : MUT }}>{num(iv.mean, 3)}</b></div>
              <div>Q5−Q1 <b style={{ color: (val.summary.qspread_long.mean || 0) < 0 ? DOWN : UP }}>{num(val.summary.qspread_long.mean, 3)}</b></div>
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: sig ? UP : WARN, fontWeight: 600 }}>
              {sig
                ? "IC t≥2,但仍须经正交化 + 净·扣成本检验(幸存者偏差/小样本未除)。"
                : "未达统计显著(|t|<2)+ 幸存者偏差 + 小样本 → 不宣称 alpha,仅候选展示。"}
              {(iv.mean || 0) < 0 && " 价值腿在该成长型 universe 中 IC 为负(反而拖累)。"}
            </div>
            <div style={{ marginTop: 4, fontSize: 11, color: MUT }}>
              下一步:消幸存者偏差(PIT 成分史)· 对 HML/RMW/UMD 正交化 · 净·扣成本组合回测(2022 入 holdout)。
            </div>
          </div>
        );
      })()}

      {/* 宏观风险拨盘 */}
      {macro && (
        <div style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 14, margin: "12px 0" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <b>🌡️ 宏观风险拨盘</b>
            <span style={{ color: rg.c, fontWeight: 700 }}>{rg.t}</span>
            <span style={{ fontSize: 22, fontWeight: 800, color: rg.c }}>{num(macro.risk_dial, 2)}</span>
            <span style={{ color: MUT, fontSize: 12 }}>(1=risk-on · 数据 {macro.asof_data || "—"} · FRED keyless)</span>
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
            {Object.entries(macro.components).map(([k, c]) => (
              <div key={k} style={{ fontSize: 12 }}>
                <span style={{ color: MUT }}>{({ credit: "信用利差", curve: "期限利差", fci: "金融条件", labor: "劳动(Sahm)" }[k]) || k}</span>{" "}
                <b style={{ color: c.score > 0.6 ? UP : c.score < 0.35 ? DOWN : WARN }}>{num(c.score, 2)}</b>{" "}
                <span style={{ color: MUT }}>(={num(c.value, 2)}, w{c.w})</span>
              </div>
            ))}
          </div>
          <div style={{ color: MUT, fontSize: 11, marginTop: 6 }}>温和拨盘,非择时;喂 L-4 总敞口软开关。</div>
        </div>
      )}

      {/* 概览 */}
      {ls && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", margin: "8px 0", fontSize: 13 }}>
          <div>PIT 截止 <b>{ls.as_of}</b></div>
          <div>universe <b>{ls.universe_size}</b></div>
          <div>有分 <b style={{ color: UP }}>{ls.n_scored}</b></div>
          <div>剔除 <b style={{ color: DOWN }}>{ls.n_excluded}</b></div>
          <div>价值腿 <b>{ls.with_value ? "已启用" : "未启用"}</b></div>
        </div>
      )}

      {/* 排行表 */}
      <h3 style={{ marginTop: 16 }}>📊 LongScore 排行(点行看因子分解)</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: MUT, textAlign: "right", borderBottom: "1px solid var(--border)" }}>
              <th style={{ textAlign: "left", padding: "6px 8px" }}>#</th>
              <th style={{ textAlign: "left" }}>代码</th>
              <th>LongScore</th><th>质量</th><th>价值</th><th>因子数</th><th>标记</th>
            </tr>
          </thead>
          <tbody>
            {scored.map((r) => (
              <RowView key={r.ticker} r={r} open={open === r.ticker} onClick={() => setOpen(open === r.ticker ? null : r.ticker)} />
            ))}
          </tbody>
        </table>
      </div>

      {/* 软标记 */}
      {flagged.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3>⚠️ 软标记(保留,供复核)</h3>
          {flagged.map((r) => (
            <div key={r.ticker} style={{ fontSize: 12, color: MUT, padding: "2px 0" }}>
              <b style={{ color: "var(--text)" }}>{r.ticker}</b> — {(r.flags || []).join("; ")}
            </div>
          ))}
        </div>
      )}

      {/* 硬剔除 */}
      {excluded.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3>🚫 剔除闸拦下(下行保护)</h3>
          {excluded.map((r) => (
            <div key={r.ticker} style={{ fontSize: 12, color: DOWN, padding: "2px 0" }}>
              <b>{r.ticker}</b> — {(r.reasons || []).join("; ")}
            </div>
          ))}
        </div>
      )}

      <p style={{ color: MUT, fontSize: 11, marginTop: 24, lineHeight: 1.6 }}>
        数据:SEC EDGAR XBRL(基本面,filed≤as_of PIT)+ Yahoo(价格)+ FRED(宏观)。均为免费源,仅供研究/自用,
        <b>非投资建议</b>。LongScore = 各 bucket 横截面 rank-z 等权(integrated)。剔除闸 = Altman Z'' / Beneish M(双确认)/ Piotroski F。
      </p>
    </div>
  );
}

function RowView({ r, open, onClick }: { r: LongRow; open: boolean; onClick: () => void }) {
  const q = r.buckets?.quality, v = r.buckets?.value;
  return (
    <>
      <tr onClick={onClick} style={{ cursor: "pointer", textAlign: "right", borderBottom: "1px solid var(--border)" }}>
        <td style={{ textAlign: "left", padding: "6px 8px", color: MUT }}>{r.rank}</td>
        <td style={{ textAlign: "left" }}><b>{r.ticker}</b></td>
        <td style={{ fontWeight: 700, color: (r.long_score || 0) > 0 ? UP : DOWN }}>{num(r.long_score, 3)}</td>
        <td style={{ color: zc(q) }}>{q == null ? "—" : num(q, 2)}</td>
        <td style={{ color: zc(v) }}>{v == null ? "—" : num(v, 2)}</td>
        <td style={{ color: MUT }}>{r.n_factors ?? "—"}</td>
        <td>{(r.flags?.length || 0) > 0 ? "⚠️" : ""}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={7} style={{ background: "var(--card,rgba(120,120,120,0.06))", padding: 12 }}>
            <div style={{ display: "flex", gap: 18, flexWrap: "wrap", fontSize: 12 }}>
              {Object.entries(r.z || {}).filter(([, z]) => z != null).map(([k, z]) => (
                <div key={k}>
                  <span style={{ color: MUT }}>{FACTOR_CN[k] || k}</span>{" "}
                  <b style={{ color: zc(z) }}>{num(z, 2)}</b>
                </div>
              ))}
            </div>
            {r.valuation && (
              <div style={{ marginTop: 8, fontSize: 12, color: MUT }}>
                市值 ${num((r.valuation.market_cap || 0) / 1e9, 0)}B · EV ${num((r.valuation.enterprise_value || 0) / 1e9, 0)}B
                {r.valuation.earnings_yield != null && <> · E/P {pct(r.valuation.earnings_yield)}</>}
                {r.valuation.shareholder_yield != null && <> · 股东收益 {pct(r.valuation.shareholder_yield)}</>}
                {r.shares_src && <> · 股数源 {r.shares_src}</>}
              </div>
            )}
            {r.scores && (
              <div style={{ marginTop: 6, fontSize: 12, color: MUT }}>
                Altman Z'' {num(r.scores.altman_z2 as number, 2)} ({r.scores.altman_zone as string}) ·
                Piotroski F {r.scores.piotroski_f as number} ·
                Beneish M {num(r.scores.beneish_m as number, 2)}
              </div>
            )}
            {(r.flags?.length || 0) > 0 && (
              <div style={{ marginTop: 6, fontSize: 12, color: WARN }}>{(r.flags || []).join("; ")}</div>
            )}
            <div style={{ marginTop: 6, fontSize: 11, color: MUT }}>财年末 {r.period_end || "—"}</div>
          </td>
        </tr>
      )}
    </>
  );
}
