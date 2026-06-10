"use client";
// 📡 信号雷达:个股页顶部一行看全方法论结论(九转/RS/52周/SuperTrend/缠论/Squeeze/AVWAP/夜盘)。
// 全部复用既有指标库,与图上开关同口径;多空计票给总倾向。非投资建议。
import { useEffect, useMemo, useState } from "react";
import type { Bar } from "@/lib/datasource";
import { anchoredVwap, superTrend, tdSetup, ttmSqueeze } from "@/lib/indicators";
import { computeChan } from "@/lib/chan";
import { getRsRanks, type RsTable } from "@/lib/feed";
import { useNightQuotes } from "@/lib/nightquotes";
import { marketStatus } from "@/lib/marketstatus";

const UP = "#26a69a", DOWN = "#ef5350", WARN = "#f7b500", MUT = "#787b86";

interface Chip { label: string; tone: "up" | "down" | "warn" | "mut"; title: string; vote: -1 | 0 | 1 }

export default function SignalRadar({ symbol, bars }: { symbol: string; bars: Bar[] }) {
  const [rs, setRs] = useState<RsTable | null>(null);
  useEffect(() => { getRsRanks().then(setRs).catch(() => {}); }, []);
  const night = useNightQuotes();

  const chips = useMemo<Chip[]>(() => {
    if (bars.length < 30) return [];
    const highs = bars.map((b) => b.high), lows = bars.map((b) => b.low), closes = bars.map((b) => b.close);
    const price = closes[closes.length - 1];
    const out: Chip[] = [];

    // 1) TD9 九转(最后一段 ≥4 才报)
    const td = tdSetup(highs, lows, closes);
    const lastTd = td.length ? td[td.length - 1] : null;
    if (lastTd && lastTd.idx >= bars.length - 3 && lastTd.count >= 4) {
      const exhaust = lastTd.count >= 7;
      out.push({
        label: `九转 ${lastTd.side === "buy" ? "下跌" : "上涨"}${lastTd.count}${lastTd.perfected ? "✓" : ""}`,
        tone: exhaust ? "warn" : "mut",
        title: lastTd.side === "buy" ? "连续低收计数,7+ 关注止跌反弹" : "连续高收计数,7+ 防短线衰竭",
        vote: exhaust ? (lastTd.side === "buy" ? 1 : -1) : 0,
      });
    }
    // 2) RS + 52周(美股)
    const code = symbol.startsWith("US:") ? symbol.slice(3) : null;
    const rk = code ? rs?.ranks?.[code] : null;
    if (rk?.rs != null) {
      out.push({ label: `RS ${rk.rs}`, tone: rk.rs >= 80 ? "up" : rk.rs < 40 ? "down" : "mut",
                 title: "全宇宙相对强度分位(1-99,IBD 加权动量)", vote: rk.rs >= 80 ? 1 : rk.rs < 40 ? -1 : 0 });
      if (rk.w52dd != null) {
        out.push({ label: `距52周高 ${rk.w52dd >= 0 ? "新高" : `${rk.w52dd}%`}`,
                   tone: rk.w52dd >= -3 ? "up" : rk.w52dd <= -30 ? "down" : "mut",
                   title: "George-Hwang:接近 52 周高点 = 动量偏强", vote: rk.w52dd >= -3 ? 1 : 0 });
      }
    }
    // 3) SuperTrend
    const { dir } = superTrend(highs, lows, closes);
    const d = dir[dir.length - 1];
    let flip = 0;
    for (let i = dir.length - 1; i > 0 && dir[i] === d; i--) flip = dir.length - i;
    out.push({ label: `ST ${d > 0 ? "多头" : "空头"}·${flip}根`, tone: d > 0 ? "up" : "down",
               title: `SuperTrend(10,3) 当前${d > 0 ? "上行" : "下行"},${flip} 根前翻转`, vote: d > 0 ? 1 : -1 });
    // 4) 缠论
    const chan = computeChan(bars);
    const lastStroke = chan.strokes[chan.strokes.length - 1];
    if (lastStroke) {
      const lastPt = chan.points[chan.points.length - 1];
      const recentPt = lastPt && (() => {
        const idx = bars.findIndex((b) => b.time === lastPt.time);
        return idx >= bars.length - 5 ? lastPt : null;
      })();
      const dv = chan.divergence;
      const lbl = recentPt ? `缠 ${recentPt.kind}` :
        dv && dv.significant ? `缠 ${dv.side === "top" ? "顶背驰" : "底背驰"}${(dv.degree * 100).toFixed(0)}%` :
        `缠 ${lastStroke.dir === "up" ? "上行笔" : "下行笔"}`;
      const bull = recentPt ? recentPt.kind.endsWith("B") : dv?.significant ? dv.side === "bottom" : lastStroke.dir === "up";
      out.push({ label: lbl, tone: bull ? "up" : "down", title: chan.note.slice(0, 80),
                 vote: recentPt || dv?.significant ? (bull ? 1 : -1) : 0 });
    }
    // 5) Squeeze
    const sq = ttmSqueeze(highs, lows, closes);
    const n1 = bars.length - 1;
    if (sq.on[n1]) out.push({ label: "Squeeze 挤压中", tone: "warn", title: "布林收进 Keltner = 波动蓄势,关注释放方向", vote: 0 });
    else if (sq.fired.slice(-3).some(Boolean)) {
      const up2 = (sq.mom[n1] ?? 0) >= 0;
      out.push({ label: `SQZ 释放${up2 ? "↑" : "↓"}`, tone: up2 ? "up" : "down", title: "挤压解除,动量方向首选", vote: up2 ? 1 : -1 });
    }
    // 6) AVWAP(52周低锚)
    const lb = Math.min(bars.length, 252);
    const seg = bars.slice(-lb);
    let loI = 0;
    seg.forEach((b, i) => { if (b.low < seg[loI].low) loI = i; });
    const av = anchoredVwap(bars, bars.length - lb + loI);
    const a = av[av.length - 1];
    if (a != null) {
      out.push({ label: `AVWAP${price >= a ? "上" : "下"}`, tone: price >= a ? "up" : "down",
                 title: `52周低点锚定成本线 ${a.toFixed(2)}:价在线上=底部以来买家整体盈利`, vote: price >= a ? 1 : -1 });
    }
    // 7) 夜盘(闭市)
    const nq = night.map[symbol];
    if (nq && nq.chg24h != null && !marketStatus(symbol.split(":")[0]).open) {
      out.push({ label: `🌙 ${nq.chg24h >= 0 ? "+" : ""}${(nq.chg24h * 100).toFixed(1)}%`,
                 tone: nq.chg24h >= 0 ? "up" : "down",
                 title: `HIP-3 永续 24h(夜盘代理,corr 0.965)`, vote: 0 });
    }
    return out;
  }, [bars, rs, night, symbol]);

  if (!chips.length) return null;
  const bulls = chips.filter((c) => c.vote > 0).length;
  const bears = chips.filter((c) => c.vote < 0).length;
  const TONE: Record<Chip["tone"], string> = { up: UP, down: DOWN, warn: WARN, mut: MUT };

  return (
    <div className="section" style={{ padding: "10px 14px", marginBottom: 10 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 13, fontWeight: 700 }}>📡 信号雷达</span>
        <span className="badge" style={{ fontSize: 11, color: bulls > bears ? UP : bears > bulls ? DOWN : WARN }}
          title="计票口径:仅强信号投票(RS≥80/≤40、九转7+、ST方向、缠论买卖点或显著背驰、SQZ释放、AVWAP上下)">
          多 {bulls} : 空 {bears}
        </span>
        {chips.map((c, i) => (
          <span key={i} className="badge" title={c.title}
            style={{ fontSize: 11, color: TONE[c.tone], borderColor: TONE[c.tone] }}>
            {c.label}
          </span>
        ))}
        <span className="src" style={{ fontSize: 10 }}>与图上开关同口径 · hover 看说明 · 非投资建议</span>
      </div>
    </div>
  );
}
