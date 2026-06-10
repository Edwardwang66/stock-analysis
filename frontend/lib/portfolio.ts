// 模拟持仓(paper portfolio):localStorage 存储,行情走统一数据层实时估值。
// 无账号体系;与自选/提醒一起进 JSON 备份。

export interface Holding {
  id: string;
  symbol: string;   // "US:AAPL"
  qty: number;      // 数量(可小数,支持加密)
  cost: number;     // 单位成本价
  note?: string;
  createdAt: number;
}

const KEY = "portfolio:v1";

function read(): Holding[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function write(list: Holding[]): void {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* ignore */ }
  window.dispatchEvent(new Event("portfolio-changed"));
}

export function getHoldings(): Holding[] { return read(); }

export function addHolding(symbol: string, qty: number, cost: number, note = ""): Holding {
  const h: Holding = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    symbol: symbol.toUpperCase(), qty, cost, note, createdAt: Date.now(),
  };
  write([...read(), h]);
  return h;
}

export function removeHolding(id: string): void {
  write(read().filter((h) => h.id !== id));
}

export function updateHolding(id: string, patch: Partial<Pick<Holding, "qty" | "cost" | "note">>): void {
  write(read().map((h) => (h.id === id ? { ...h, ...patch } : h)));
}
