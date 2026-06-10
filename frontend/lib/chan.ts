// 简化版缠论(Chan Theory)结构识别 —— 纯规则、非 LLM。
// 灵感来自「观潮 TideView」(guanchaotv.com,闭源商业产品)的缠论自动标注能力;
// 此处为独立实现的简化版:包含处理 -> 分型 -> 笔 -> 中枢。教学/参考用,非精确缠论。
import type { Bar } from "./datasource";
import { macd } from "./indicators";

export interface Fractal { time: number; price: number; type: "top" | "bottom"; idx: number }
export interface Stroke { from: Fractal; to: Fractal; dir: "up" | "down"; area: number }
export interface Pivot { zg: number; zd: number; startTime: number; endTime: number }
export interface BSPoint { time: number; price: number; kind: "1B" | "2B" | "3B" | "1S" | "2S" | "3S"; detail: string }
/** 背驰度(原文 24 课口径,methodology §4):A、C 同向笔对比,B 段 |DIF| 须回拉。 */
export interface Divergence {
  side: "top" | "bottom";        // 顶背驰 / 底背驰
  degree: number;                // 1 − 面积(C)/面积(A),≥0.3 显著
  priceExtended: boolean;        // C 创新高/新低
  difPull: boolean;              // B 段 min|DIF| < 0.25 × A∪C 峰值(回拉确认)
  difPeakShrink: boolean;        // C 段 |DIF| 峰值 < A 段(动能衰竭)
  significant: boolean;          // 全条件成立且 degree ≥ 0.3
  text: string;
}
export interface ChanResult {
  fractals: Fractal[]; strokes: Stroke[]; pivots: Pivot[]; points: BSPoint[];
  divergence: Divergence | null; note: string;
}

interface MK { time: number; high: number; low: number; idx: number } // 合并后K线

// 1) 包含关系处理
function mergeInclusion(bars: Bar[]): MK[] {
  const out: MK[] = [];
  for (let i = 0; i < bars.length; i++) {
    const b = bars[i];
    if (out.length < 1) { out.push({ time: b.time, high: b.high, low: b.low, idx: i }); continue; }
    const prev = out[out.length - 1];
    const contains = (prev.high >= b.high && prev.low <= b.low) || (b.high >= prev.high && b.low <= prev.low);
    if (contains) {
      // 方向:看前一根合并线相对更前的趋势
      const up = out.length >= 2 ? prev.high > out[out.length - 2].high : b.high > prev.high;
      if (up) { prev.high = Math.max(prev.high, b.high); prev.low = Math.max(prev.low, b.low); }
      else { prev.high = Math.min(prev.high, b.high); prev.low = Math.min(prev.low, b.low); }
      prev.time = b.time; prev.idx = i;
    } else {
      out.push({ time: b.time, high: b.high, low: b.low, idx: i });
    }
  }
  return out;
}

// 2) 分型
function fractals(mk: MK[]): Fractal[] {
  const fs: Fractal[] = [];
  for (let i = 1; i < mk.length - 1; i++) {
    const a = mk[i - 1], b = mk[i], c = mk[i + 1];
    if (b.high > a.high && b.high > c.high) fs.push({ time: b.time, price: b.high, type: "top", idx: b.idx });
    else if (b.low < a.low && b.low < c.low) fs.push({ time: b.time, price: b.low, type: "bottom", idx: b.idx });
  }
  return fs;
}

// 3) 笔:相邻分型必须类型相反且间隔足够(简化:合并K线序号差 >= 2)
function strokes(fs: Fractal[], mk: MK[]): Stroke[] {
  const pos = new Map(mk.map((m, i) => [m.idx, i]));
  const valid: Fractal[] = [];
  for (const f of fs) {
    if (!valid.length) { valid.push(f); continue; }
    const last = valid[valid.length - 1];
    if (f.type === last.type) {
      // 同类型取更极端者
      if ((f.type === "top" && f.price > last.price) || (f.type === "bottom" && f.price < last.price)) valid[valid.length - 1] = f;
    } else {
      const gap = Math.abs((pos.get(f.idx) ?? 0) - (pos.get(last.idx) ?? 0));
      if (gap >= 2) valid.push(f);
      else if ((f.type === "top" && f.price > last.price) || (f.type === "bottom" && f.price < last.price)) valid[valid.length - 1] = f;
    }
  }
  const st: Stroke[] = [];
  for (let i = 1; i < valid.length; i++) {
    st.push({ from: valid[i - 1], to: valid[i], dir: valid[i].price > valid[i - 1].price ? "up" : "down", area: 0 });
  }
  return st;
}

// 买卖点 + 背驰(简化):基于 MACD 能量(hist 面积)与中枢。
function buySellPoints(bars: Bar[], st: Stroke[], pivots: Pivot[]): BSPoint[] {
  const pts: BSPoint[] = [];
  if (st.length < 3) return pts;

  // 背驰 -> 第一类买卖点:同向相邻两笔,价格创新高/低但能量(面积)减弱
  const downs = st.filter((s) => s.dir === "down");
  const ups = st.filter((s) => s.dir === "up");
  const lastDown = downs[downs.length - 1], prevDown = downs[downs.length - 2];
  if (lastDown && prevDown && lastDown.to.price < prevDown.to.price && Math.abs(lastDown.area) < Math.abs(prevDown.area)) {
    pts.push({ time: lastDown.to.time, price: lastDown.to.price, kind: "1B", detail: "底背驰:创新低但 MACD 能量减弱" });
  }
  const lastUp = ups[ups.length - 1], prevUp = ups[ups.length - 2];
  if (lastUp && prevUp && lastUp.to.price > prevUp.to.price && Math.abs(lastUp.area) < Math.abs(prevUp.area)) {
    pts.push({ time: lastUp.to.time, price: lastUp.to.price, kind: "1S", detail: "顶背驰:创新高但 MACD 能量减弱" });
  }

  // 第三类买卖点:突破中枢后回踩不破 ZG(买)/反抽不破 ZD(卖)
  const piv = pivots[pivots.length - 1];
  if (piv) {
    for (const s of st) {
      if (s.to.time <= piv.endTime) continue;
      if (s.dir === "down" && s.to.type === "bottom" && s.to.price > piv.zg) {
        pts.push({ time: s.to.time, price: s.to.price, kind: "3B", detail: `回踩不破中枢上沿 ZG ${piv.zg.toFixed(2)}` });
        break;
      }
      if (s.dir === "up" && s.to.type === "top" && s.to.price < piv.zd) {
        pts.push({ time: s.to.time, price: s.to.price, kind: "3S", detail: `反抽不破中枢下沿 ZD ${piv.zd.toFixed(2)}` });
        break;
      }
    }
  }

  // 第二类买卖点:1B 后首个更高的底(买)/ 1S 后首个更低的顶(卖)
  const oneB = pts.find((p) => p.kind === "1B");
  if (oneB) {
    const after = st.find((s) => s.dir === "down" && s.to.type === "bottom" && s.to.time > oneB.time && s.to.price > oneB.price);
    if (after) pts.push({ time: after.to.time, price: after.to.price, kind: "2B", detail: "1B 后回调不破前低" });
  }
  const oneS = pts.find((p) => p.kind === "1S");
  if (oneS) {
    const after = st.find((s) => s.dir === "up" && s.to.type === "top" && s.to.time > oneS.time && s.to.price < oneS.price);
    if (after) pts.push({ time: after.to.time, price: after.to.price, kind: "2S", detail: "1S 后反弹不破前高" });
  }

  // 去重 + 按时间排序
  const seen = new Set<string>();
  return pts
    .filter((p) => { const k = p.time + p.kind; if (seen.has(k)) return false; seen.add(k); return true; })
    .sort((a, b) => a.time - b.time);
}

// 背驰度(methodology §4,原文 24 课):A、C 同向两笔,B 为其间反向笔。
// degree = 1 − |面积C|/|面积A|;确认:C 创新高/低 且 B 段 |DIF| 回拉 且 C 段 |DIF| 峰值缩。
function computeDivergence(
  st: Stroke[], dif: (number | null)[], idxByTime: Map<number, number>,
): Divergence | null {
  if (st.length < 3) return null;
  const C = st[st.length - 1];
  // 找上一笔同向的 A(中间隔着反向 B)
  let A: Stroke | null = null, B: Stroke | null = null;
  for (let i = st.length - 2; i >= 1; i--) {
    if (st[i].dir !== C.dir) { B = st[i]; continue; }
    A = st[i]; break;
  }
  if (!A || !B || Math.abs(A.area) < 1e-9) return null;

  const side: "top" | "bottom" = C.dir === "up" ? "top" : "bottom";
  const priceExtended = C.dir === "up" ? C.to.price > A.to.price : C.to.price < A.to.price;
  const degree = 1 - Math.abs(C.area) / Math.abs(A.area);

  const absDif = (s: Stroke, fn: (vals: number[]) => number): number => {
    const a = idxByTime.get(s.from.time) ?? 0, b = idxByTime.get(s.to.time) ?? 0;
    const vals: number[] = [];
    for (let i = Math.min(a, b); i <= Math.max(a, b); i++) {
      const d = dif[i];
      if (d != null) vals.push(Math.abs(d));
    }
    return vals.length ? fn(vals) : 0;
  };
  const peakA = absDif(A, (v) => Math.max(...v));
  const peakC = absDif(C, (v) => Math.max(...v));
  const minB = absDif(B, (v) => Math.min(...v));
  const peak = Math.max(peakA, peakC);
  const difPull = peak > 0 && minB < 0.25 * peak;
  const difPeakShrink = peakC < peakA;
  const significant = degree >= 0.3 && priceExtended && difPull && difPeakShrink;

  const label = side === "top" ? "顶背驰" : "底背驰";
  let text: string;
  if (significant) {
    text = `${label}显著(背驰度 ${(degree * 100).toFixed(0)}%):进入背驰段,关注其后次级别回试。`;
  } else if (degree > 0 && priceExtended) {
    const miss = [!difPull && "B段DIF未回拉", !difPeakShrink && "DIF峰值未缩", degree < 0.3 && "面积缩幅不足"].filter(Boolean).join("、");
    text = `${label}迹象(背驰度 ${(degree * 100).toFixed(0)}%,未确认:${miss})。`;
  } else {
    text = `当前${C.dir === "up" ? "上涨" : "下跌"}笔动能${degree <= 0 ? "未衰竭" : "衰竭中"},无背驰。`;
  }
  return { side, degree: Math.round(degree * 1000) / 1000, priceExtended, difPull, difPeakShrink, significant, text };
}

// 4) 中枢:连续 3 笔的重叠区间
function pivots(st: Stroke[]): Pivot[] {
  const ps: Pivot[] = [];
  for (let i = 0; i + 2 < st.length; i++) {
    const segs = [st[i], st[i + 1], st[i + 2]].map((s) => ({
      hi: Math.max(s.from.price, s.to.price), lo: Math.min(s.from.price, s.to.price),
    }));
    const zd = Math.max(...segs.map((s) => s.lo));
    const zg = Math.min(...segs.map((s) => s.hi));
    if (zg > zd) ps.push({ zg, zd, startTime: st[i].from.time, endTime: st[i + 2].to.time });
  }
  // 合并相邻重叠中枢,只保留代表性的(简化:取最近 1-2 个)
  return ps.slice(-2);
}

export function computeChan(bars: Bar[]): ChanResult {
  if (bars.length < 8) return { fractals: [], strokes: [], pivots: [], points: [], divergence: null, note: "数据不足,无法识别缠论结构" };
  const mk = mergeInclusion(bars);
  const fs = fractals(mk);
  const st = strokes(fs, mk);

  // 计算每笔的 MACD 能量面积(原文口径:上涨段只累计红柱、下跌段只累计绿柱,按笔端点截取)
  const closes = bars.map((b) => b.close);
  const { hist, line: dif } = macd(closes);
  const idxByTime = new Map(bars.map((b, i) => [b.time, i]));
  for (const s of st) {
    const a = idxByTime.get(s.from.time) ?? 0, b = idxByTime.get(s.to.time) ?? 0;
    let sum = 0;
    for (let i = Math.min(a, b); i <= Math.max(a, b); i++) {
      const h = hist[i];
      if (h == null) continue;
      if (s.dir === "up" && h > 0) sum += h;        // 红柱
      else if (s.dir === "down" && h < 0) sum += h; // 绿柱
    }
    s.area = sum;
  }

  // 背驰度(笔对笔,带 B 段 |DIF| 回拉验证)
  const divergence = computeDivergence(st, dif, idxByTime);

  const ps = pivots(st);
  const points = buySellPoints(bars, st, ps);
  const lastStroke = st[st.length - 1];
  const lastPivot = ps[ps.length - 1];
  const price = bars[bars.length - 1].close;
  let note = "";
  if (lastStroke) note += `当前为${lastStroke.dir === "up" ? "向上" : "向下"}笔。`;
  if (lastPivot) {
    const loc = price > lastPivot.zg ? "中枢上方(强势)" : price < lastPivot.zd ? "中枢下方(弱势)" : "中枢震荡区内";
    note += `最近中枢 [${lastPivot.zd.toFixed(2)}, ${lastPivot.zg.toFixed(2)}],价格位于${loc}。`;
  } else {
    note += "暂未形成有效中枢。";
  }
  if (points.length) {
    const last = points[points.length - 1];
    note += `最近买卖点:${last.kind}(${last.detail})。`;
  }
  if (divergence) note += divergence.text;
  note += " 简化缠论,仅供参考,非投资建议。";
  return { fractals: fs, strokes: st, pivots: ps, points, divergence, note };
}
