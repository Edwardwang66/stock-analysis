"use client";
import { useEffect, useRef, useState } from "react";
import { createChart, ColorType, LineStyle, type IChartApi } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";
import { sma } from "@/lib/indicators";
import { computeChan } from "@/lib/chan";

const MA = [
  { period: 20, color: "#4c8dff" },
  { period: 50, color: "#f7b500" },
  { period: 200, color: "#ab47bc" },
];

export default function Chart({ bars }: { bars: Bar[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [showChan, setShowChan] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      height: 420,
      layout: { background: { type: ColorType.Solid, color: "#131722" }, textColor: "#d1d4dc" },
      grid: { vertLines: { color: "#2a2e39" }, horzLines: { color: "#2a2e39" } },
      timeScale: { timeVisible: false, borderColor: "#2a2e39" },
      rightPriceScale: { borderColor: "#2a2e39" },
      crosshair: { mode: 0 },
      autoSize: true,
    });
    chartRef.current = chart;

    // 蜡烛
    const candles = chart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });
    candles.setData(bars.map((b) => ({ time: b.time as any, open: b.open, high: b.high, low: b.low, close: b.close })));

    // 成交量(底部独立刻度)
    const vol = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol" });
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(bars.map((b) => ({
      time: b.time as any, value: b.volume,
      color: b.close >= b.open ? "rgba(38,166,154,.5)" : "rgba(239,83,80,.5)",
    })));

    // 多均线叠加
    const closes = bars.map((b) => b.close);
    if (!showChan) {
      for (const m of MA) {
        const s = sma(closes, m.period);
        const data = bars
          .map((b, i) => (s[i] != null ? { time: b.time as any, value: s[i] as number } : null))
          .filter(Boolean) as any[];
        if (data.length) {
          const line = chart.addLineSeries({ color: m.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
          line.setData(data);
        }
      }
    }

    // 缠论结构:笔(连线)+ 分型(标记)+ 中枢(价格区间线)
    if (showChan) {
      const chan = computeChan(bars);
      // 分型标记(笔端点)+ 买卖点标签
      const endpoints = new Set<number>();
      chan.strokes.forEach((s) => { endpoints.add(s.from.time); endpoints.add(s.to.time); });
      const bspTimes = new Set(chan.points.map((p) => p.time));
      const fractalMarkers = chan.fractals
        .filter((f) => endpoints.has(f.time) && !bspTimes.has(f.time))
        .map((f) => ({
          time: f.time, position: f.type === "top" ? "aboveBar" : "belowBar",
          color: f.type === "top" ? "#ef5350" : "#26a69a",
          shape: f.type === "top" ? "arrowDown" : "arrowUp",
        }));
      const bspMarkers = chan.points.map((p) => {
        const buy = p.kind.endsWith("B");
        return {
          time: p.time, position: buy ? "belowBar" : "aboveBar",
          color: buy ? "#26a69a" : "#ef5350",
          shape: buy ? "arrowUp" : "arrowDown", text: p.kind,
        };
      });
      candles.setMarkers(
        [...fractalMarkers, ...bspMarkers].sort((a, b) => (a.time as number) - (b.time as number)) as any
      );
      // 笔:连接端点的折线
      const pts: { time: any; value: number }[] = [];
      if (chan.strokes.length) {
        pts.push({ time: chan.strokes[0].from.time, value: chan.strokes[0].from.price });
        chan.strokes.forEach((s) => pts.push({ time: s.to.time, value: s.to.price }));
      }
      if (pts.length) {
        const stroke = chart.addLineSeries({ color: "#e0e3eb", lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
        stroke.setData(pts);
      }
      // 中枢:上下沿价格线
      chan.pivots.forEach((p) => {
        candles.createPriceLine({ price: p.zg, color: "#f7b500", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "中枢上沿 ZG" });
        candles.createPriceLine({ price: p.zd, color: "#f7b500", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "中枢下沿 ZD" });
      });
    }

    chart.timeScale().fitContent();
    return () => { chart.remove(); chartRef.current = null; };
  }, [bars, showChan]);

  return (
    <>
      <div className="ranges" style={{ justifyContent: "flex-end" }}>
        <button className={showChan ? "active" : ""} onClick={() => setShowChan((v) => !v)}>
          {showChan ? "✓ 缠论结构" : "缠论结构"}
        </button>
      </div>
      <div ref={ref} style={{ width: "100%" }} />
      <div className="src" style={{ marginTop: 6 }}>
        {showChan
          ? "缠论:白线=笔 · 黄虚线=中枢 · 标签 1/2/3B=买点 1/2/3S=卖点(含背驰,简化版,灵感来自观潮 TideView)"
          : "均线:"}
        {!showChan && <><span style={{ color: "#4c8dff" }}>MA20</span> · <span style={{ color: "#f7b500" }}>MA50</span> · <span style={{ color: "#ab47bc" }}>MA200</span> · 底部为成交量</>}
      </div>
    </>
  );
}
