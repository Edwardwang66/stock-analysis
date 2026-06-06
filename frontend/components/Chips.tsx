"use client";
import { useMemo } from "react";
import type { Bar } from "@/lib/datasource";
import { computeChips } from "@/lib/chips";

const UP = "#26a69a", DOWN = "#ef5350";

function fmt(n: number | null, d = 2) {
  return n == null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: d });
}

// 横向筹码柱:价格在纵轴,获利盘绿、套牢盘红(对标富途筹码分布)
export default function Chips({ bars, price }: { bars: Bar[]; price: number | null }) {
  const chips = useMemo(() => (price ? computeChips(bars, price) : null), [bars, price]);
  if (!chips || price == null) return null;

  const maxV = Math.max(...chips.levels.map((l) => l.volume)) || 1;
  const rows = [...chips.levels].reverse(); // 高价在上

  return (
    <div className="section">
      <h2>筹码分布（成本分布 · 估算）</h2>
      <table style={{ marginBottom: 12 }}>
        <tbody>
          <tr>
            <th>获利比例</th>
            <td style={{ color: chips.profitRatio >= 0.5 ? UP : DOWN, fontWeight: 600 }}>{(chips.profitRatio * 100).toFixed(2)}%</td>
            <th>平均成本</th>
            <td>{fmt(chips.avgCost)}</td>
          </tr>
          <tr>
            <th>支撑位</th>
            <td style={{ color: UP }}>{fmt(chips.support)}</td>
            <th>压力位</th>
            <td style={{ color: DOWN }}>{fmt(chips.resistance)}</td>
          </tr>
          <tr>
            <th>90%成本区间</th>
            <td colSpan={3}>{fmt(chips.conc90.low)} ~ {fmt(chips.conc90.high)}</td>
          </tr>
        </tbody>
      </table>

      <div style={{ display: "grid", gap: 1 }}>
        {rows.map((l, i) => {
          const here = Math.abs(l.price - price) <= (chips.levels[1].price - chips.levels[0].price) / 2;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, height: 9 }}>
              <span style={{ width: 56, textAlign: "right", color: here ? "#fff" : "#787b86" }}>
                {l.price.toFixed(2)}{here ? " ◄" : ""}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ height: 7, width: `${(l.volume / maxV) * 100}%`, background: l.profit ? UP : DOWN, opacity: 0.85, borderRadius: 2 }} />
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#787b86", marginTop: 8 }}>
        <span><span style={{ color: UP }}>■</span> 获利盘(成本&lt;现价)</span>
        <span><span style={{ color: DOWN }}>■</span> 套牢盘(成本&gt;现价)</span>
        <span>◄ 现价 {fmt(price)}</span>
      </div>
      <p className="src" style={{ marginTop: 8 }}>{chips.note} 估算自历史日 K 的量价堆积(时间衰减),非真实持仓成本,仅供参考。</p>
    </div>
  );
}
