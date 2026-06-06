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
