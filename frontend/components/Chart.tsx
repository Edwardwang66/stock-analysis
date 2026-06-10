"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, LineStyle, CrosshairMode, PriceScaleMode, type IChartApi } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";
import { sma } from "@/lib/indicators";
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
  return d.getUTCHours() || d.getUTCMinutes() ? `${base} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}` : base;
}

export default function Chart({
  bars,
  compare = null,
}: {
  bars: Bar[];
  /** 对比叠加:右轴切百分比模式,两边都按首值归一(TradingView 同款体验) */
  compare?: { name: string; bars: Bar[] } | null;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showChan, setShowChan] = useState(false);

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

    if (showChan) {
      const chan = computeChan(bars);
      const endpoints = new Set<number>();
      chan.strokes.forEach((s) => { endpoints.add(s.from.time); endpoints.add(s.to.time); });
      const bspTimes = new Set(chan.points.map((p) => p.time));
      const fractalMarkers = chan.fractals.filter((f) => endpoints.has(f.time) && !bspTimes.has(f.time)).map((f) => ({
        time: f.time, position: f.type === "top" ? "aboveBar" : "belowBar",
        color: f.type === "top" ? "#ef5350" : "#26a69a", shape: f.type === "top" ? "arrowDown" : "arrowUp",
      }));
      const bspMarkers = chan.points.map((p) => {
        const buy = p.kind.endsWith("B");
        return { time: p.time, position: buy ? "belowBar" : "aboveBar", color: buy ? "#26a69a" : "#ef5350", shape: buy ? "arrowUp" : "arrowDown", text: p.kind };
      });
      candles.setMarkers([...fractalMarkers, ...bspMarkers].sort((a, b) => (a.time as number) - (b.time as number)) as any);
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
  }, [bars, showChan, compare]);

  return (
    <>
      <div className="ranges" style={{ justifyContent: "flex-end" }}>
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
      </div>
    </>
  );
}
