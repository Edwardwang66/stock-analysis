"use client";
import { useMemo } from "react";
import type { Bar } from "@/lib/datasource";
import { computeChan } from "@/lib/chan";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";
const KIND_LABEL: Record<string, string> = {
  "1B": "一买(底背驰)", "2B": "二买", "3B": "三买", "1S": "一卖(顶背驰)", "2S": "二卖", "3S": "三卖",
};

function fmtD(t: number): string {
  const d = new Date(t * 1000);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

/** 缠论面板:背驰度徽章 + 当前结构 + 买卖点历史表(含事后表现)。methodology §4 前端实装。 */
export default function ChanPanel({ bars }: { bars: Bar[] }) {
  const chan = useMemo(() => (bars.length >= 8 ? computeChan(bars) : null), [bars]);
  const rows = useMemo(() => {
    if (!chan) return [];
    const idxByTime = new Map(bars.map((b, i) => [b.time, i]));
    return chan.points.slice(-10).reverse().map((p) => {
      const i = idxByTime.get(p.time);
      const after = (n: number) =>
        i != null && i + n < bars.length ? (bars[i + n].close / p.price - 1) * 100 : null;
      return { ...p, r5: after(5), r20: after(20) };
    });
  }, [chan, bars]);

  if (!chan || !chan.strokes.length) return null;
  const dv = chan.divergence;
  const last = chan.strokes[chan.strokes.length - 1];
  const piv = chan.pivots[chan.pivots.length - 1];
  const price = bars[bars.length - 1]?.close;

  const cell = (v: number | null) =>
    v == null ? <td className="muted">—</td>
      : <td className={v >= 0 ? "up" : "down"}>{v >= 0 ? "+" : ""}{v.toFixed(1)}%</td>;

  return (
    <div className="section">
      <h2>
        ☯ 缠论结构
        <span className="badge" style={{ marginLeft: 8, fontSize: 11, color: last.dir === "up" ? UP : DOWN, borderColor: last.dir === "up" ? UP : DOWN }}>
          {last.dir === "up" ? "向上笔" : "向下笔"}
        </span>
        {piv && price != null && (
          <span className="badge" style={{ marginLeft: 6, fontSize: 11 }}>
            中枢 [{piv.zd.toFixed(2)}, {piv.zg.toFixed(2)}] · {price > piv.zg ? "上方(强)" : price < piv.zd ? "下方(弱)" : "区间内"}
          </span>
        )}
        {dv && dv.degree > 0 && dv.priceExtended && (
          <span className="badge" style={{
            marginLeft: 6, fontSize: 11,
            color: dv.significant ? (dv.side === "top" ? DOWN : UP) : WARN,
            borderColor: dv.significant ? (dv.side === "top" ? DOWN : UP) : WARN,
          }}>
            {dv.side === "top" ? "顶背驰" : "底背驰"}{dv.significant ? "✓" : "?"} 度 {(dv.degree * 100).toFixed(0)}%
          </span>
        )}
      </h2>
      <p className="src" style={{ marginTop: 0 }}>{chan.note}</p>
      {dv && dv.degree > 0 && dv.priceExtended && (
        <p className="src" style={{ color: MUT }}>
          确认三件套:创新{dv.side === "top" ? "高" : "低"} {dv.priceExtended ? "✓" : "✗"} ·
          B段DIF回拉 {dv.difPull ? "✓" : "✗"} · DIF峰值缩 {dv.difPeakShrink ? "✓" : "✗"}
          (口径:原文24课,面积=同色MACD柱按笔端点截取,度≥30%+三件套全✓才算显著)
        </p>
      )}
      {rows.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr><th>日期</th><th>买卖点</th><th>价格</th><th>+5根</th><th>+20根</th><th>依据</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.time}${r.kind}`}>
                  <td className="muted">{fmtD(r.time)}</td>
                  <td style={{ color: r.kind.endsWith("B") ? UP : DOWN }}>{KIND_LABEL[r.kind] ?? r.kind}</td>
                  <td>{r.price.toFixed(2)}</td>
                  {cell(r.r5)}
                  {cell(r.r20)}
                  <td className="src">{r.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="src" style={{ marginTop: 8 }}>
        买卖点为简化缠论自动识别(当前K线周期);「+5/+20根」为该点之后 N 根K线的收盘变动,用于自检信号质量。仅供参考,非投资建议。
      </p>
    </div>
  );
}
