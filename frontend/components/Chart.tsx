"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, LineStyle, CrosshairMode, PriceScaleMode, type IChartApi } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";
import { anchoredVwap, sma, superTrend, tdSetup, ttmSqueeze } from "@/lib/indicators";
import { computeChan } from "@/lib/chan";

const MA = [
  { period: 20, color: "#4c8dff" },
  { period: 50, color: "#f7b500" },
  { period: 200, color: "#ab47bc" },
];

function fmtDate(t: number): string {
  const d = new Date(t * 1000);
  const p = (n: number) => String(n).padStart(2, "0");
  const base = `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
  return d.getUTCHours() || d.getUTCMinutes() ? `${base} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} UTC` : base;
}

export default function Chart({
  bars,
  compare = null,
  levels = null,
}: {
  bars: Bar[];
  /** 对比叠加:右轴切百分比模式,两边都按首值归一(TradingView 同款体验) */
  compare?: { name: string; bars: Bar[] } | null;
  /** 支撑压力水平线组(如 周Pivot),由「支撑压力」开关控制显示 */
  levels?: { price: number; label: string; color?: string }[] | null;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showChan, setShowChan] = useState(false);
  const [showTd, setShowTd] = useState(true); // 九转默认开(方法论 #1)
  const [showSt, setShowSt] = useState(false); // SuperTrend(方法论 #3)
  const [showLv, setShowLv] = useState(false); // 支撑压力(周 Pivot,方法论 #6)
  const [showAv, setShowAv] = useState(false); // 锚定VWAP(52周低/高双锚,方法论二期)
  const [showSq, setShowSq] = useState(false); // TTM Squeeze(挤压=蓄势,释放=变盘)

  useEffect(() => {
    if (!ref.current || !bars.length) return;
    const chart = createChart(ref.current, {
      height: 440,
      layout: { background: { type: ColorType.Solid, color: "#131722" }, textColor: "#d1d4dc" },
      grid: { vertLines: { color: "#2a2e39" }, horzLines: { color: "#2a2e39" } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#2a2e39" },
      rightPriceScale: { borderColor: "#2a2e39" },
      crosshair: { mode: CrosshairMode.Normal },
      autoSize: true,
    });
    chartRef.current = chart;

    const candles = chart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });
    candles.setData(bars.map((b) => ({ time: b.time as any, open: b.open, high: b.high, low: b.low, close: b.close })));

    const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol" });
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(bars.map((b) => ({
      time: b.time as any, value: b.volume,
      color: b.close >= b.open ? "rgba(38,166,154,.5)" : "rgba(239,83,80,.5)",
    })));

    // 对比模式:右轴切百分比(各序列按首个可见值归一),叠加对比线
    if (compare && compare.bars.length) {
      chart.priceScale("right").applyOptions({ mode: PriceScaleMode.Percentage });
      chart.addLineSeries({ color: "#26c6da", lineWidth: 2, priceLineVisible: false })
        .setData(compare.bars.map((b) => ({ time: b.time as any, value: b.close })));
    }

    const closes = bars.map((b) => b.close);
    if (!showChan && !compare) {
      for (const m of MA) {
        const s = sma(closes, m.period);
        const data = bars.map((b, i) => (s[i] != null ? { time: b.time as any, value: s[i] as number } : null)).filter(Boolean) as any[];
        if (data.length) chart.addLineSeries({ color: m.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false }).setData(data);
      }
    }

    // 锚定 VWAP:52周低点锚(青)+ 52周高点锚(紫);机构成本线
    if (showAv && !compare && bars.length >= 30) {
      const lookback = Math.min(bars.length, 252);
      const seg = bars.slice(-lookback);
      const off = bars.length - lookback;
      let loI = 0, hiI = 0;
      seg.forEach((b, i) => {
        if (b.low < seg[loI].low) loI = i;
        if (b.high > seg[hiI].high) hiI = i;
      });
      for (const [aIdx, color, label] of [[off + loI, "#26c6da", "AVWAP·低锚"], [off + hiI, "#ab47bc", "AVWAP·高锚"]] as const) {
        const av = anchoredVwap(bars, aIdx);
        const series = chart.addLineSeries({ color, lineWidth: 2, lineStyle: LineStyle.Solid,
          priceLineVisible: false, lastValueVisible: true, title: label, crosshairMarkerVisible: false });
        series.setData(bars.flatMap((b, i) => (av[i] != null ? [{ time: b.time as any, value: av[i] as number }] : [])));
      }
    }

    // TTM Squeeze:挤压期黄点(蓄势),释放根▲/▼(按动量方向)
    if (showSq && !compare && bars.length >= 25) {
      const sq = ttmSqueeze(bars.map((b) => b.high), bars.map((b) => b.low), bars.map((b) => b.close));
      const markers: any[] = [];
      bars.forEach((b, j) => {
        if (sq.fired[j]) {
          const up = (sq.mom[j] ?? 0) >= 0;
          markers.push({ time: b.time as any, position: up ? "belowBar" : "aboveBar",
                         color: up ? "#26a69a" : "#ef5350", shape: up ? "arrowUp" : "arrowDown", text: "SQZ释放" });
        } else if (sq.on[j]) {
          markers.push({ time: b.time as any, position: "belowBar", color: "#f7b500", shape: "circle", text: "" });
        }
      });
      if (markers.length) {
        // 注:series 不能 visible:false(markers 会被一并隐藏);用全透明线承载标记
        const host = chart.addLineSeries({ color: "rgba(0,0,0,0)",
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
        host.setData(bars.map((b) => ({ time: b.time as any, value: b.close })));
        host.setMarkers(markers.slice(-180));
      }
    }

    // SuperTrend(10,3):上行画绿线(下轨),下行画红线(上轨),翻转处断开
    if (showSt && !compare) {
      const { st, dir } = superTrend(bars.map((b) => b.high), bars.map((b) => b.low), bars.map((b) => b.close));
      const upData: any[] = [], downData: any[] = [];
      for (let i = 0; i < bars.length; i++) {
        if (st[i] == null) continue;
        (dir[i] === 1 ? upData : downData).push({ time: bars[i].time as any, value: st[i] as number });
      }
      if (upData.length) chart.addLineSeries({ color: "#26a69a", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }).setData(upData);
      if (downData.length) chart.addLineSeries({ color: "#ef5350", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }).setData(downData);
    }

    // 支撑压力水平线(周 Pivot 等)
    if (showLv && levels?.length && !compare) {
      for (const lv of levels) {
        candles.createPriceLine({
          price: lv.price, color: lv.color ?? "#9aa0aa", lineWidth: 1,
          lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: lv.label,
        });
      }
    }

    // 标记合并:TD9 与 缠论 可同开,统一 setMarkers 一次
    const allMarkers: any[] = [];

    if (showTd) {
      // TD9 神奇九转:只显示最终数到 ≥6 的段,且从 6 起标数字(9 高亮,完美 9 加 ✓)
      const tds = tdSetup(bars.map((b) => b.high), bars.map((b) => b.low), bars.map((b) => b.close));
      for (const m of tds) {
        if (m.runMax < 6 || m.count < 6) continue;
        const isNine = m.count === 9;
        allMarkers.push({
          time: bars[m.idx].time,
          position: m.side === "sell" ? "aboveBar" : "belowBar",
          color: m.side === "sell" ? (isNine ? "#ff8a80" : "#ef5350") : (isNine ? "#69f0ae" : "#26a69a"),
          shape: "circle",
          size: isNine ? 1 : 0,
          text: isNine ? (m.perfected ? "9✓" : "9") : String(m.count),
        });
      }
    }

    if (showChan) {
      const chan = computeChan(bars);
      const endpoints = new Set<number>();
      chan.strokes.forEach((s) => { endpoints.add(s.from.time); endpoints.add(s.to.time); });
      const bspTimes = new Set(chan.points.map((p) => p.time));
      chan.fractals.filter((f) => endpoints.has(f.time) && !bspTimes.has(f.time)).forEach((f) => allMarkers.push({
        time: f.time, position: f.type === "top" ? "aboveBar" : "belowBar",
        color: f.type === "top" ? "#ef5350" : "#26a69a", shape: f.type === "top" ? "arrowDown" : "arrowUp",
      }));
      chan.points.forEach((p) => {
        const buy = p.kind.endsWith("B");
        allMarkers.push({ time: p.time, position: buy ? "belowBar" : "aboveBar", color: buy ? "#26a69a" : "#ef5350", shape: buy ? "arrowUp" : "arrowDown", text: p.kind });
      });
      const pts: { time: any; value: number }[] = [];
      if (chan.strokes.length) {
        pts.push({ time: chan.strokes[0].from.time, value: chan.strokes[0].from.price });
        chan.strokes.forEach((s) => pts.push({ time: s.to.time, value: s.to.price }));
      }
      if (pts.length) chart.addLineSeries({ color: "#e0e3eb", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }).setData(pts);
      chan.pivots.forEach((p) => {
        candles.createPriceLine({ price: p.zg, color: "#f7b500", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "ZG" });
        candles.createPriceLine({ price: p.zd, color: "#f7b500", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "ZD" });
      });
    }

    if (allMarkers.length) {
      candles.setMarkers(allMarkers.sort((a, b) => (a.time as number) - (b.time as number)) as any);
    }

    // 十字光标 tooltip:日期 + OHLC + 涨跌% + 量
    const volByTime = new Map(bars.map((b) => [b.time, b.volume]));
    const renderLegend = (b: { time: number; open: number; high: number; low: number; close: number }) => {
      if (!legendRef.current) return;
      const chg = ((b.close - b.open) / b.open) * 100;
      const cls = b.close >= b.open ? "up" : "down";
      const v = volByTime.get(b.time) ?? 0;
      legendRef.current.innerHTML =
        `<b>${fmtDate(b.time)}</b> &nbsp; 开 ${b.open.toFixed(2)} 高 ${b.high.toFixed(2)} 低 ${b.low.toFixed(2)} ` +
        `<span class="${cls}">收 ${b.close.toFixed(2)} (${chg >= 0 ? "+" : ""}${chg.toFixed(2)}%)</span> ` +
        `&nbsp; 量 ${v >= 1e6 ? (v / 1e6).toFixed(2) + "M" : v.toFixed(0)}`;
    };
    const lastBar = bars[bars.length - 1];
    renderLegend(lastBar);
    chart.subscribeCrosshairMove((param) => {
      const d = param.time ? (param.seriesData.get(candles) as any) : null;
      if (d && d.open != null) renderLegend({ time: param.time as number, ...d });
      else renderLegend(lastBar);
    });

    chart.timeScale().fitContent();
    return () => { chart.remove(); chartRef.current = null; };
  }, [bars, showChan, showTd, showSt, showLv, showAv, showSq, levels, compare]);

  return (
    <>
      <div className="ranges" style={{ justifyContent: "flex-end" }}>
        <button className={showTd ? "active" : ""} onClick={() => setShowTd((v) => !v)}>
          {showTd ? "✓ 神奇九转" : "神奇九转"}
        </button>
        <button className={showSt ? "active" : ""} onClick={() => setShowSt((v) => !v)}>
          {showSt ? "✓ SuperTrend" : "SuperTrend"}
        </button>
        <button className={showAv ? "active" : ""} onClick={() => setShowAv((v) => !v)}>
          {showAv ? "✓ AVWAP" : "AVWAP"}
        </button>
        <button className={showSq ? "active" : ""} onClick={() => setShowSq((v) => !v)}>
          {showSq ? "✓ Squeeze" : "Squeeze"}
        </button>
        {levels && levels.length > 0 && (
          <button className={showLv ? "active" : ""} onClick={() => setShowLv((v) => !v)}>
            {showLv ? "✓ 支撑压力" : "支撑压力"}
          </button>
        )}
        <button className={showChan ? "active" : ""} onClick={() => setShowChan((v) => !v)}>
          {showChan ? "✓ 缠论结构" : "缠论结构"}
        </button>
      </div>
      <div style={{ position: "relative" }}>
        <div ref={legendRef} className="chart-legend" />
        <div ref={ref} style={{ width: "100%" }} />
      </div>
      <div className="src" style={{ marginTop: 6 }}>
        {compare
          ? <>对比模式:右轴为<strong>百分比</strong>(两者均按区间首值归一)· <span style={{ color: "#26c6da" }}>青线 = {compare.name}</span> · K线 = 本标的</>
          : showChan
          ? "缠论:白线=笔 · 黄虚线=中枢 · 标签 1/2/3B=买点 1/2/3S=卖点(含背驰,简化版,灵感来自观潮 TideView)"
          : <>均线:<span style={{ color: "#4c8dff" }}>MA20</span> · <span style={{ color: "#f7b500" }}>MA50</span> · <span style={{ color: "#ab47bc" }}>MA200</span> · 底部为成交量 · 鼠标移到图上看每日明细</>}
        {showTd && <> · 九转:<span className="up">绿数字=下跌段(超卖)</span> <span className="down">红数字=上涨段(衰竭)</span>,6 起显示、9✓=完美九转(预警非建议)</>}
      </div>
    </>
  );
}
