// 简化版缠论(Chan Theory)结构识别 —— 纯规则、非 LLM。
// 灵感来自「观潮 TideView」(guanchaotv.com,闭源商业产品)的缠论自动标注能力;
// 此处为独立实现的简化版:包含处理 -> 分型 -> 笔 -> 中枢。教学/参考用,非精确缠论。
import type { Bar } from "./datasource";

export interface Fractal { time: number; price: number; type: "top" | "bottom"; idx: number }
export interface Stroke { from: Fractal; to: Fractal; dir: "up" | "down" }
export interface Pivot { zg: number; zd: number; startTime: number; endTime: number }
export interface ChanResult { fractals: Fractal[]; strokes: Stroke[]; pivots: Pivot[]; note: string }

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
    st.push({ from: valid[i - 1], to: valid[i], dir: valid[i].price > valid[i - 1].price ? "up" : "down" });
  }
  return st;
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
  if (bars.length < 8) return { fractals: [], strokes: [], pivots: [], note: "数据不足,无法识别缠论结构" };
  const mk = mergeInclusion(bars);
  const fs = fractals(mk);
  const st = strokes(fs, mk);
  const ps = pivots(st);
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
  note += " 简化缠论,仅供参考,非投资建议。";
  return { fractals: fs, strokes: st, pivots: ps, note };
}
