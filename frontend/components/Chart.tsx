"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, type IChartApi } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";

export default function Chart({ bars }: { bars: Bar[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      height: 380,
      layout: { background: { type: ColorType.Solid, color: "#131722" }, textColor: "#d1d4dc" },
      grid: { vertLines: { color: "#2a2e39" }, horzLines: { color: "#2a2e39" } },
      timeScale: { timeVisible: false, borderColor: "#2a2e39" },
      rightPriceScale: { borderColor: "#2a2e39" },
      autoSize: true,
    });
    chartRef.current = chart;
    const series = chart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });
    series.setData(bars.map((b) => ({ time: b.time as any, open: b.open, high: b.high, low: b.low, close: b.close })));
    chart.timeScale().fitContent();
    return () => { chart.remove(); chartRef.current = null; };
  }, [bars]);

  return <div ref={ref} style={{ width: "100%" }} />;
}
