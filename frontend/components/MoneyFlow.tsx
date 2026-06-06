"use client";
import { useEffect, useMemo, useState } from "react";
import { getIntraday, parseSymbol, type Bar } from "@/lib/datasource";
import { getCryptoFlow, getOrderBook, type OrderBook } from "@/lib/crypto";
import { computeMoneyFlow, fmtAmount, type MoneyFlow } from "@/lib/moneyflow";

// 周期:对标富途「分时 / 日 / 周 / 月」(免费股票源用分钟K近似)
const PERIODS = [
  { k: "分时", interval: "5m", range: "1d" },
  { k: "5日", interval: "15m", range: "5d" },
  { k: "近月", interval: "1h", range: "1mo" },
];

const UP = "#26a69a", DOWN = "#ef5350";
const IN_C = ["#0f6b5f", "#1f9e8c", "#3fbfa9", "#7fd9c9"];
const OUT_C = ["#b32d2a", "#e0463f", "#ef6f68", "#f6a39d"];

function polar(cx: number, cy: number, r: number, ang: number) {
  const a = (ang - 90) * (Math.PI / 180);
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}
function arc(cx: number, cy: number, r: number, rIn: number, a0: number, a1: number) {
  const [x0, y0] = polar(cx, cy, r, a1);
  const [x1, y1] = polar(cx, cy, r, a0);
  const [x2, y2] = polar(cx, cy, rIn, a0);
  const [x3, y3] = polar(cx, cy, rIn, a1);
  const big = a1 - a0 > 180 ? 1 : 0;
  return `M${x0} ${y0} A${r} ${r} 0 ${big} 0 ${x1} ${y1} L${x2} ${y2} A${rIn} ${rIn} 0 ${big} 1 ${x3} ${y3} Z`;
}

function Donut({ mf }: { mf: MoneyFlow }) {
  const segs: { v: number; c: string }[] = [];
  mf.buckets.forEach((b, i) => b.inflow > 0 && segs.push({ v: b.inflow, c: IN_C[i] }));
  [...mf.buckets].reverse().forEach((b, i) => b.outflow > 0 && segs.push({ v: b.outflow, c: OUT_C[3 - i] }));
  const tot = segs.reduce((s, x) => s + x.v, 0) || 1;
  let ang = 0;
  const cx = 90, cy = 90, r = 80, rIn = 56;
  const netIn = mf.net >= 0;
  return (
    <svg viewBox="0 0 180 180" width="180" height="180">
      {segs.map((s, i) => {
        const a0 = ang, a1 = ang + (s.v / tot) * 360; ang = a1;
        return <path key={i} d={arc(cx, cy, r, rIn, a0, a1 - 0.6)} fill={s.c} />;
      })}
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="12" fill="#787b86">{netIn ? "净流入" : "净流出"}</text>
      <text x={cx} y={cy + 16} textAnchor="middle" fontSize="18" fontWeight="700" fill={netIn ? UP : DOWN}>
        {fmtAmount(Math.abs(mf.net))}
      </text>
    </svg>
  );
}

function Bars({ mf }: { mf: MoneyFlow }) {
  const max = Math.max(1, ...mf.buckets.flatMap((b) => [b.inflow, b.outflow]));
  return (
    <div style={{ flex: 1, minWidth: 220 }}>
      {mf.buckets.map((b) => (
        <div key={b.name} style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0", fontSize: 12 }}>
          <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
            <div style={{ height: 14, width: `${(b.outflow / max) * 100}%`, background: DOWN, borderRadius: "3px 0 0 3px" }} />
          </div>
          <div style={{ width: 56, textAlign: "center", color: "#d1d4dc" }}>{b.name}</div>
          <div style={{ flex: 1 }}>
            <div style={{ height: 14, width: `${(b.inflow / max) * 100}%`, background: UP, borderRadius: "0 3px 3px 0" }} />
          </div>
        </div>
      ))}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#787b86", marginTop: 4 }}>
        <span style={{ color: DOWN }}>← 流出 {fmtAmount(mf.outflow)}</span>
        <span style={{ color: UP }}>流入 {fmtAmount(mf.inflow)} →</span>
      </div>
    </div>
  );
}

function FlowLine({ mf }: { mf: MoneyFlow }) {
  const w = 640, h = 150, pad = 6;
  const pts = mf.series;
  if (pts.length < 2) return null;
  const vals = pts.flatMap((p) => [p.cumAll, p.cumMain]).concat(0);
  const min = Math.min(...vals), max = Math.max(...vals);
  const sx = (i: number) => pad + (i / (pts.length - 1)) * (w - 2 * pad);
  const sy = (v: number) => pad + (1 - (v - min) / (max - min || 1)) * (h - 2 * pad);
  const path = (key: "cumAll" | "cumMain") => pts.map((p, i) => `${i ? "L" : "M"}${sx(i).toFixed(1)} ${sy(p[key]).toFixed(1)}`).join(" ");
  const zeroY = sy(0);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" style={{ marginTop: 8 }}>
      <line x1={pad} y1={zeroY} x2={w - pad} y2={zeroY} stroke="#2a2e39" strokeDasharray="3 3" />
      <path d={path("cumAll")} fill="none" stroke="#9aa0aa" strokeWidth={1.4} />
      <path d={path("cumMain")} fill="none" stroke="#f7b500" strokeWidth={1.8} />
    </svg>
  );
}

// 买卖盘口(暗号真实 depth,对标富途「买盘/卖盘 %」)
function OrderBookBar({ ob }: { ob: OrderBook }) {
  const bid = ob.bidPct * 100;
  return (
    <div style={{ marginTop: 14 }}>
      <div className="block-title" style={{ margin: "0 0 6px" }}>买卖盘(真实盘口)· 买一 {ob.bids[0]?.[0]} / 卖一 {ob.asks[0]?.[0]}</div>
      <div style={{ display: "flex", height: 16, borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${bid}%`, background: UP }} />
        <div style={{ width: `${100 - bid}%`, background: DOWN }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginTop: 4 }}>
        <span style={{ color: UP }}>买盘 {bid.toFixed(2)}%</span>
        <span style={{ color: DOWN }}>{(100 - bid).toFixed(2)}% 卖盘</span>
      </div>
    </div>
  );
}

export default function MoneyFlow({ symbol }: { symbol: string }) {
  const isCrypto = parseSymbol(symbol).market === "CRYPTO";
  const [period, setPeriod] = useState(PERIODS[0]);
  const [bars, setBars] = useState<Bar[]>([]);
  const [cryptoMf, setCryptoMf] = useState<MoneyFlow | null>(null);
  const [ob, setOb] = useState<OrderBook | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true); setErr("");
    const { code } = parseSymbol(symbol);
    const job = isCrypto
      ? Promise.all([getCryptoFlow(code), getOrderBook(code)]).then(([mf, o]) => { if (alive) { setCryptoMf(mf); setOb(o); } })
      : getIntraday(symbol, period.interval, period.range).then((b) => { if (alive) setBars(b); });
    job.then(() => alive && setLoading(false))
      .catch((e) => { if (alive) { setErr(e?.message || "加载失败"); setLoading(false); } });
    return () => { alive = false; };
  }, [symbol, period, isCrypto]);

  const mf = useMemo(() => (isCrypto ? cryptoMf : computeMoneyFlow(bars)), [isCrypto, cryptoMf, bars]);
  const mainIn = (mf?.mainNet ?? 0) >= 0;

  return (
    <div className="section">
      <h2>
        资金流向 · 主力资金
        {mf?.real
          ? <span className="badge" style={{ marginLeft: 8, fontSize: 11, borderColor: UP, color: UP }}>真实逐笔</span>
          : <span className="badge" style={{ marginLeft: 8, fontSize: 11 }}>K线估算</span>}
      </h2>

      {!isCrypto && (
        <div className="ranges">
          {PERIODS.map((p) => (
            <button key={p.k} className={p.k === period.k ? "active" : ""} onClick={() => setPeriod(p)}>{p.k}</button>
          ))}
        </div>
      )}

      {mf && mf.bars > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", margin: "4px 0 12px" }}>
          <span className="badge" style={{ fontSize: 13, borderColor: mainIn ? UP : DOWN, color: mainIn ? UP : DOWN }}>
            主力{mainIn ? "净流入" : "净流出"} {fmtAmount(Math.abs(mf.mainNet))}
          </span>
          <span className="muted" style={{ fontSize: 13 }}>{mf.note}</span>
        </div>
      )}

      {err && <div className="err">资金数据加载失败:{err}(分钟线/代理偶发不稳,可切换周期或刷新)</div>}
      {loading ? <div className="loading">资金流向计算中…</div> : !mf || mf.bars === 0 ? (
        <div className="muted">该周期暂无足够数据(休市或免费源限制)。</div>
      ) : (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
            <Donut mf={mf} />
            <Bars mf={mf} />
          </div>
          {ob && <OrderBookBar ob={ob} />}
          <div className="block-title" style={{ margin: "16px 0 4px" }}>
            累计净流入 · <span style={{ color: "#f7b500" }}>主力(特大+大)</span> vs <span style={{ color: "#9aa0aa" }}>整体</span>
          </div>
          <FlowLine mf={mf} />
        </>
      )}

      <p className="src" style={{ marginTop: 10 }}>
        {mf?.real
          ? "暗号:基于 Binance 真实逐笔成交(aggTrades)与盘口(depth),按成交额分档、主动买卖定方向,主力=特大+大 —— 真·主力资金。"
          : "股票:免费行情无逐笔/盘口,用分钟 K 线成交额分位数分档 + 收盘涨跌定方向做透明估算(主力=特大+大),仅供趋势参考。"}
        {" "}不构成投资建议。
      </p>
    </div>
  );
}
