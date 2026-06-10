"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle, CrosshairMode, PriceScaleMode, type IChartApi, type IPriceLine } from "lightweight-charts";
import type { Bar } from "@/lib/datasource";
import { anchoredVwap, sma, superTrend, tdSetup, ttmSqueeze, vsaSignals } from "@/lib/indicators";
import { computeChan } from "@/lib/chan";
import { usePref } from "@/lib/prefs";

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

export interface MyLine {
  id: string;
  price: number;
  title: string;
  color: string;
  /** 可拖拽(提醒线):按住线上下移动,松手回调 onLineDrag */
  draggable?: boolean;
}

export default function Chart({
  bars,
  compare = null,
  levels = null,
  myLines = null,
  onLineDrag,
}: {
  bars: Bar[];
  /** 对比叠加:右轴切百分比模式,两边都按首值归一(TradingView 同款体验) */
  compare?: { name: string; bars: Bar[] } | null;
  /** 支撑压力水平线组(如 周Pivot),由「支撑压力」开关控制显示 */
  levels?: { price: number; label: string; color?: string }[] | null;
  /** "我的"信息上图(Hyperliquid 式):持仓成本线 / 价格提醒线,由「我的」开关控制 */
  myLines?: MyLine[] | null;
  onLineDrag?: (id: string, price: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // 指标开关持久化:刷新/下次访问保持上次组合(Hyperliquid 式偏好记忆)。
  // td=九转(默认开,方法论 #1) st=SuperTrend lv=支撑压力(周Pivot) av=锚定VWAP
  // sq=TTM Squeeze fib=自动斐波 ichi=Ichimoku简版 vsa=量价信号 chan=缠论结构
  const [flags, setFlags] = usePref("chart:overlays:v1", {
    chan: false, td: true, st: false, lv: false, av: false, sq: false, fib: false, ichi: false, vsa: false,
    mine: true, // "我的"持仓/提醒线默认开
  });
  const toggle = (k: keyof typeof flags) => setFlags((f) => ({ ...f, [k]: !f[k] }));
  const { chan: showChan, td: showTd, st: showSt, lv: showLv, av: showAv,
          sq: showSq, fib: showFib, ichi: showIchi, vsa: showVsa, mine: showMine } = flags;
  // 拖拽回调走 ref:父组件每次渲染都会换函数身份,不让它触发整图重建
  const dragCb = useRef(onLineDrag);
  dragCb.current = onLineDrag;

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

    // 自动斐波回撤:近 252 根 高→低 或 低→高(按时间后者为终点),0/23.6/38.2/50/61.8/78.6/100
    if (showFib && !compare && bars.length >= 30) {
      const lb = Math.min(bars.length, 252);
      const seg = bars.slice(-lb);
      let loI = 0, hiI = 0;
      seg.forEach((b, i) => { if (b.low < seg[loI].low) loI = i; if (b.high > seg[hiI].high) hiI = i; });
      const hi = seg[hiI].high, lo = seg[loI].low;
      const upMove = loI < hiI; // 低点在前 = 上行段回撤
      for (const r of [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]) {
        const price = upMove ? hi - (hi - lo) * r : lo + (hi - lo) * r;
        candles.createPriceLine({ price, color: r === 0.5 ? "#f7b500" : "rgba(120,123,134,0.55)",
          lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true,
          title: `Fib ${(r * 100).toFixed(1).replace(".0", "")}%` });
      }
    }

    // Ichimoku 简版:转换线(9)/基准线(26)/先行A/B(云,前移省略=同位画)
    if (showIchi && !compare && bars.length >= 60) {
      const hl = (p2: number, i: number) => {
        const a = bars.slice(Math.max(0, i - p2 + 1), i + 1);
        return (Math.max(...a.map((x) => x.high)) + Math.min(...a.map((x) => x.low))) / 2;
      };
      const tenkan = bars.map((_, i) => (i >= 8 ? hl(9, i) : null));
      const kijun = bars.map((_, i) => (i >= 25 ? hl(26, i) : null));
      const spanA = bars.map((_, i) => (tenkan[i] != null && kijun[i] != null ? ((tenkan[i] as number) + (kijun[i] as number)) / 2 : null));
      const spanB = bars.map((_, i) => (i >= 51 ? hl(52, i) : null));
      const mk = (data: (number | null)[], color: string, w: number, title: string) => {
        const ser = chart.addLineSeries({ color, lineWidth: w as any, priceLineVisible: false, lastValueVisible: false, title, crosshairMarkerVisible: false });
        ser.setData(bars.flatMap((b, i) => (data[i] != null ? [{ time: b.time as any, value: data[i] as number }] : [])));
      };
      mk(tenkan, "#26c6da", 1, "转换9");
      mk(kijun, "#ab47bc", 1, "基准26");
      mk(spanA, "rgba(38,166,154,0.5)", 1, "云A");
      mk(spanB, "rgba(239,83,80,0.5)", 1, "云B");
    }

    // VSA 量价四信号:高量滞涨⊗ / 无供应◦ / 承接▲ / 放量突破★
    if (showVsa && !compare && bars.length >= 30) {
      const marks = vsaSignals(bars.map((b) => b.open), bars.map((b) => b.high),
                               bars.map((b) => b.low), bars.map((b) => b.close), bars.map((b) => b.volume));
      const KIND: Record<string, { pos: string; color: string; shape: string; text: string }> = {
        churn: { pos: "aboveBar", color: "#f7b500", shape: "circle", text: "高量滞涨" },
        noSupply: { pos: "belowBar", color: "#4c8dff", shape: "circle", text: "无供应" },
        stopping: { pos: "belowBar", color: "#26a69a", shape: "arrowUp", text: "承接" },
        breakout: { pos: "aboveBar", color: "#69f0ae", shape: "arrowUp", text: "放量突破" },
      };
      const markers = marks.slice(-60).map((m) => {
        const k = KIND[m.kind];
        return { time: bars[m.idx].time as any, position: k.pos as any, color: k.color, shape: k.shape as any, text: k.text };
      });
      if (markers.length) {
        const host = chart.addLineSeries({ color: "rgba(0,0,0,0)", priceLineVisible: false,
          lastValueVisible: false, crosshairMarkerVisible: false });
        host.setData(bars.map((b) => ({ time: b.time as any, value: b.close })));
        host.setMarkers(markers);
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

    // "我的"信息上图(Hyperliquid 精髓:把你的状态画进市场):
    // 实线=持仓成本,虚线=价格提醒;提醒线支持按住拖拽改价,松手生效。
    const disposers: (() => void)[] = [];
    if (showMine && myLines?.length && !compare) {
      const lineMap = new Map<string, { line: IPriceLine; draggable: boolean }>();
      for (const ml of myLines) {
        const line = candles.createPriceLine({
          price: ml.price, color: ml.color, lineWidth: 1,
          lineStyle: ml.draggable ? LineStyle.Dashed : LineStyle.Solid,
          axisLabelVisible: true, title: ml.title,
        });
        lineMap.set(ml.id, { line, draggable: !!ml.draggable });
      }
      const el = ref.current;
      if (el && myLines.some((m) => m.draggable)) {
        let dragging: { id: string; line: IPriceLine } | null = null;
        const relY = (e: PointerEvent) => e.clientY - el.getBoundingClientRect().top;
        const findNear = (y: number): { id: string; line: IPriceLine } | null => {
          for (const [id, v] of lineMap) {
            if (!v.draggable) continue;
            const ly = candles.priceToCoordinate(v.line.options().price);
            if (ly != null && Math.abs(ly - y) <= 6) return { id, line: v.line };
          }
          return null;
        };
        const onDown = (e: PointerEvent) => {
          const hit = findNear(relY(e));
          if (!hit) return;
          dragging = hit;
          chart.applyOptions({ handleScroll: false, handleScale: false });
          e.preventDefault();
          e.stopPropagation(); // capture 阶段拦住,不让图表进入平移
        };
        const onHover = (e: PointerEvent) => {
          if (!dragging) el.style.cursor = findNear(relY(e)) ? "ns-resize" : "";
        };
        const onMove = (e: PointerEvent) => {
          if (!dragging) return;
          const p = candles.coordinateToPrice(relY(e));
          if (p != null && p > 0) dragging.line.applyOptions({ price: p });
        };
        const onUp = () => {
          if (!dragging) return;
          const { id, line } = dragging;
          dragging = null;
          chart.applyOptions({ handleScroll: true, handleScale: true });
          el.style.cursor = "";
          dragCb.current?.(id, line.options().price);
        };
        el.addEventListener("pointerdown", onDown, true);
        el.addEventListener("pointermove", onHover);
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        disposers.push(() => {
          el.removeEventListener("pointerdown", onDown, true);
          el.removeEventListener("pointermove", onHover);
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
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
    return () => { disposers.forEach((d) => d()); chart.remove(); chartRef.current = null; };
  }, [bars, flags, levels, compare, myLines]);

  return (
    <>
      <div className="ranges" style={{ justifyContent: "flex-end" }}>
        {myLines && myLines.length > 0 && (
          <button className={showMine ? "active" : ""} onClick={() => toggle("mine")}
            title="把我的持仓成本线 / 价格提醒线画在图上;提醒线(虚线)按住可上下拖拽改价">
            {showMine ? "✓ 💼 我的" : "💼 我的"}
          </button>
        )}
        <button className={showTd ? "active" : ""} onClick={() => toggle("td")}>
          {showTd ? "✓ 神奇九转" : "神奇九转"}
        </button>
        <button className={showSt ? "active" : ""} onClick={() => toggle("st")}>
          {showSt ? "✓ SuperTrend" : "SuperTrend"}
        </button>
        <button className={showAv ? "active" : ""} onClick={() => toggle("av")}>
          {showAv ? "✓ AVWAP" : "AVWAP"}
        </button>
        <button className={showSq ? "active" : ""} onClick={() => toggle("sq")}>
          {showSq ? "✓ Squeeze" : "Squeeze"}
        </button>
        <button className={showFib ? "active" : ""} onClick={() => toggle("fib")}>
          {showFib ? "✓ 斐波" : "斐波"}
        </button>
        <button className={showIchi ? "active" : ""} onClick={() => toggle("ichi")}>
          {showIchi ? "✓ 一目" : "一目"}
        </button>
        <button className={showVsa ? "active" : ""} onClick={() => toggle("vsa")}>
          {showVsa ? "✓ VSA" : "VSA"}
        </button>
        {levels && levels.length > 0 && (
          <button className={showLv ? "active" : ""} onClick={() => toggle("lv")}>
            {showLv ? "✓ 支撑压力" : "支撑压力"}
          </button>
        )}
        <button className={showChan ? "active" : ""} onClick={() => toggle("chan")}>
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
        {showMine && !compare && myLines && myLines.length > 0 && <> · 💼 我的:实线=持仓成本 · 虚线=价格提醒(按住线可拖拽改价)</>}
      </div>
    </>
  );
}
