// 纯 TS 技术指标(与 backend/app/analysis/indicators.py 逻辑一致)。
export type Maybe = number | null;

export function sma(v: number[], p: number): Maybe[] {
  const out: Maybe[] = Array(v.length).fill(null);
  if (p <= 0) return out;
  let run = 0;
  for (let i = 0; i < v.length; i++) {
    run += v[i];
    if (i >= p) run -= v[i - p];
    if (i >= p - 1) out[i] = run / p;
  }
  return out;
}

export function ema(v: number[], p: number): Maybe[] {
  const out: Maybe[] = Array(v.length).fill(null);
  if (p <= 0 || v.length < p) return out;
  const k = 2 / (p + 1);
  let prev = v.slice(0, p).reduce((a, b) => a + b, 0) / p;
  out[p - 1] = prev;
  for (let i = p; i < v.length; i++) {
    prev = v[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function rsi(v: number[], p = 14): Maybe[] {
  const out: Maybe[] = Array(v.length).fill(null);
  if (v.length <= p) return out;
  let g = 0, l = 0;
  for (let i = 1; i <= p; i++) {
    const d = v[i] - v[i - 1];
    g += Math.max(d, 0);
    l += Math.max(-d, 0);
  }
  let ag = g / p, al = l / p;
  out[p] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  for (let i = p + 1; i < v.length; i++) {
    const d = v[i] - v[i - 1];
    ag = (ag * (p - 1) + Math.max(d, 0)) / p;
    al = (al * (p - 1) + Math.max(-d, 0)) / p;
    out[i] = al === 0 ? 100 : 100 - 100 / (1 + ag / al);
  }
  return out;
}

export function macd(v: number[], fast = 12, slow = 26, signal = 9) {
  const ef = ema(v, fast), es = ema(v, slow);
  const line: Maybe[] = ef.map((a, i) => (a !== null && es[i] !== null ? a - (es[i] as number) : null));
  const idx: number[] = [];
  line.forEach((x, i) => x !== null && idx.push(i));
  const sig: Maybe[] = Array(v.length).fill(null);
  if (idx.length >= signal) {
    const seq = idx.map((i) => line[i] as number);
    const es2 = ema(seq, signal);
    idx.forEach((i, j) => (sig[i] = es2[j]));
  }
  const hist: Maybe[] = line.map((x, i) => (x !== null && sig[i] !== null ? x - (sig[i] as number) : null));
  return { line, sig, hist };
}

export function bollinger(v: number[], p = 20, mult = 2) {
  const mid = sma(v, p);
  const up: Maybe[] = Array(v.length).fill(null);
  const lo: Maybe[] = Array(v.length).fill(null);
  for (let i = p - 1; i < v.length; i++) {
    const m = mid[i];
    if (m === null) continue;
    const w = v.slice(i - p + 1, i + 1);
    const sd = Math.sqrt(w.reduce((a, x) => a + (x - m) ** 2, 0) / p);
    up[i] = m + mult * sd;
    lo[i] = m - mult * sd;
  }
  return { mid, up, lo };
}

export function last(a: Maybe[]): Maybe {
  for (let i = a.length - 1; i >= 0; i--) if (a[i] !== null) return a[i];
  return null;
}

export function pctReturn(v: number[], lb: number): Maybe {
  if (v.length <= lb || v[v.length - 1 - lb] === 0) return null;
  return (v[v.length - 1] / v[v.length - 1 - lb] - 1) * 100;
}

/** ATR(p):平均真实波幅(Wilder 平滑)。bars 需含 high/low/close。 */
export function atr(highs: number[], lows: number[], closes: number[], p = 14): Maybe {
  const n = closes.length;
  if (n <= p) return null;
  const trs: number[] = [];
  for (let i = 1; i < n; i++) {
    trs.push(Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1]),
    ));
  }
  let a = trs.slice(0, p).reduce((s, x) => s + x, 0) / p;
  for (let i = p; i < trs.length; i++) a = (a * (p - 1) + trs[i]) / p;
  return a;
}

/** KDJ(9,3,3):返回最新 K/D/J。 */
export function kdj(highs: number[], lows: number[], closes: number[], p = 9): { k: Maybe; d: Maybe; j: Maybe } {
  const n = closes.length;
  if (n < p) return { k: null, d: null, j: null };
  let k = 50, d = 50;
  for (let i = p - 1; i < n; i++) {
    const hh = Math.max(...highs.slice(i - p + 1, i + 1));
    const ll = Math.min(...lows.slice(i - p + 1, i + 1));
    const rsv = hh === ll ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
    k = (2 / 3) * k + (1 / 3) * rsv;
    d = (2 / 3) * d + (1 / 3) * k;
  }
  return { k, d, j: 3 * k - 2 * d };
}

/** 量比:最新一根成交量 / 近 p 根均量(>1 放量,<1 缩量)。 */
export function volumeRatio(volumes: number[], p = 20): Maybe {
  if (volumes.length < p + 1) return null;
  const recent = volumes[volumes.length - 1];
  const base = volumes.slice(-p - 1, -1).reduce((s, x) => s + x, 0) / p;
  return base > 0 ? recent / base : null;
}

// ---- TD9 神奇九转(仅 Setup 段,东方财富口径;见 routines/methodology.md)----
export interface TdMark {
  idx: number;                 // bar 下标
  count: number;               // 1..9
  side: "buy" | "sell";        // buy=下跌九转(将反弹) sell=上涨九转(将衰竭)
  perfected: boolean;          // 完美 9
  runMax: number;              // 本段最终数到几(渲染时只显示 runMax>=6 的段)
}

export function tdSetup(highs: number[], lows: number[], closes: number[]): TdMark[] {
  const n = closes.length;
  const out: TdMark[] = [];
  let buyRun: TdMark[] = [];
  let sellRun: TdMark[] = [];
  const flush = (run: TdMark[]) => {
    const max = run.length ? run[run.length - 1].count : 0;
    for (const m of run) { m.runMax = max; out.push(m); }
  };
  for (let i = 4; i < n; i++) {
    // 买入计数:close < close[i-4](连续;相等即断,口径见 methodology)
    if (closes[i] < closes[i - 4]) {
      const count = (buyRun.length ? buyRun[buyRun.length - 1].count : 0) + 1;
      let perfected = false;
      if (count === 9) {
        const ref = Math.min(lows[i - 2], lows[i - 3]);     // 第7、6根
        perfected = lows[i] <= ref || lows[i - 1] <= ref;   // 第9或第8根
      }
      buyRun.push({ idx: i, count, side: "buy", perfected, runMax: 0 });
      if (count === 9) { flush(buyRun); buyRun = []; }      // 数满 9 重新数
    } else { flush(buyRun); buyRun = []; }
    if (closes[i] > closes[i - 4]) {
      const count = (sellRun.length ? sellRun[sellRun.length - 1].count : 0) + 1;
      let perfected = false;
      if (count === 9) {
        const ref = Math.max(highs[i - 2], highs[i - 3]);
        perfected = highs[i] >= ref || highs[i - 1] >= ref;
      }
      sellRun.push({ idx: i, count, side: "sell", perfected, runMax: 0 });
      if (count === 9) { flush(sellRun); sellRun = []; }
    } else { flush(sellRun); sellRun = []; }
  }
  flush(buyRun); flush(sellRun);
  out.sort((a, b) => a.idx - b.idx);
  return out;
}

// ---- SuperTrend(10,3;TradingView 同款,ATR 用 Wilder RMA,final band 棘轮)----
export function superTrend(
  highs: number[], lows: number[], closes: number[], p = 10, mult = 3,
): { st: Maybe[]; dir: number[] } {
  const n = closes.length;
  const st: Maybe[] = Array(n).fill(null);
  const dir: number[] = Array(n).fill(1);
  if (n <= p) return { st, dir };
  // Wilder RMA ATR
  const atrArr: Maybe[] = Array(n).fill(null);
  let a = 0;
  for (let i = 1; i < n; i++) {
    const tr = Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1]));
    if (i <= p) { a += tr; if (i === p) { a /= p; atrArr[i] = a; } }
    else { a = (a * (p - 1) + tr) / p; atrArr[i] = a; }
  }
  let fu = 0, fl = 0, started = false;
  for (let i = 0; i < n; i++) {
    const av = atrArr[i];
    if (av == null) continue;
    const mid = (highs[i] + lows[i]) / 2;
    const bu = mid + mult * av;
    const bl = mid - mult * av;
    if (!started) { fu = bu; fl = bl; dir[i] = -1; st[i] = fu; started = true; continue; }
    const pc = closes[i - 1];
    fu = (bu < fu || pc > fu) ? bu : fu;   // 下行趋势中上轨只降不升
    fl = (bl > fl || pc < fl) ? bl : fl;   // 上行趋势中下轨只升不降
    dir[i] = dir[i - 1];
    if (dir[i] === -1 && closes[i] > fu) dir[i] = 1;
    else if (dir[i] === 1 && closes[i] < fl) dir[i] = -1;
    st[i] = dir[i] === 1 ? fl : fu;        // 上行画下轨(绿),下行画上轨(红)
  }
  return { st, dir };
}

// ---- Pivot Points(经典;用上一完整周期的 H/L/C)----
export interface PivotLevels { P: number; R1: number; S1: number; R2: number; S2: number }
export function pivotPoints(H: number, L: number, C: number): PivotLevels {
  const P = (H + L + C) / 3, R = H - L;
  return { P, R1: 2 * P - L, S1: 2 * P - H, R2: P + R, S2: P - R };
}

/** 从日线 bars 取「上一完整 ISO 周」的 H/L/C(不足两周返回 null)。 */
export function prevWeekHLC(bars: { time: number; high: number; low: number; close: number }[]):
  { H: number; L: number; C: number } | null {
  if (bars.length < 10) return null;
  const wk = (t: number) => {
    const d = new Date(t * 1000);
    // ISO 周标识:周一为界
    const day = (d.getUTCDay() + 6) % 7;
    const monday = new Date(d); monday.setUTCDate(d.getUTCDate() - day);
    return `${monday.getUTCFullYear()}-${monday.getUTCMonth()}-${monday.getUTCDate()}`;
  };
  const groups = new Map<string, { H: number; L: number; C: number }>();
  const order: string[] = [];
  for (const b of bars) {
    const k = wk(b.time);
    const g = groups.get(k);
    if (!g) { groups.set(k, { H: b.high, L: b.low, C: b.close }); order.push(k); }
    else { g.H = Math.max(g.H, b.high); g.L = Math.min(g.L, b.low); g.C = b.close; }
  }
  if (order.length < 2) return null;
  return groups.get(order[order.length - 2]) ?? null;
}
