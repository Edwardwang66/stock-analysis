"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, type IChartApi } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";
import { sma } from "@/lib/indicators";

const MA = [
  { period: 20, color: "#4c8dff" },
  { period: 50, color: "#f7b500" },
  { period: 200, color: "#ab47bc" },
];

export default function Chart({ bars }: { bars: Bar[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

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

    chart.timeScale().fitContent();
    return () => { chart.remove(); chartRef.current = null; };
  }, [bars]);

  return (
    <>
      <div ref={ref} style={{ width: "100%" }} />
      <div className="src" style={{ marginTop: 6 }}>
        均线:<span style={{ color: "#4c8dff" }}>MA20</span> · <span style={{ color: "#f7b500" }}>MA50</span> · <span style={{ color: "#ab47bc" }}>MA200</span> · 底部为成交量
      </div>
    </>
  );
}
