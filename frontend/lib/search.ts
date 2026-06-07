// 标的联想搜索:有后端走后端(/api/v1/search,覆盖海量),
// 无后端时本地常用表 + Yahoo 搜索(经 CORS 代理,尽力而为)。
import { LOCAL_SYMBOLS, type SymInfo } from "./markets";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";
const cors = (u: string) => `https://corsproxy.io/?url=${encodeURIComponent(u)}`;

function mapYahoo(sym: string): string | null {
  if (sym.endsWith(".HK")) return `HK:${sym.slice(0, -3)}`;
  if (sym.endsWith(".SS") || sym.endsWith(".SZ")) return `CN:${sym.slice(0, -3)}`;
  if (!sym.includes(".") && !sym.includes("-") && !sym.includes("=")) return `US:${sym}`;
  return null;
}

export async function searchSymbols(q: string): Promise<SymInfo[]> {
  const ql = q.trim().toLowerCase();
  if (!ql) return [];

  if (API_BASE) {
    try {
      const r = await fetch(`${API_BASE}/api/v1/search?q=${encodeURIComponent(q)}`);
      if (r.ok) return await r.json();
    } catch { /* 回退本地 */ }
  }

  // 本地常用表
  const local = LOCAL_SYMBOLS.filter(
    (s) => s.symbol.toLowerCase().includes(ql) || s.name.toLowerCase().includes(ql)
  );
  // Yahoo 搜索(尽力而为)
  let yahoo: SymInfo[] = [];
  try {
    const u = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=8&newsCount=0`;
    const r = await fetch(cors(u));
    const d = await r.json();
    yahoo = (d.quotes || [])
      .map((it: any): SymInfo | null => {
        const m = mapYahoo(it.symbol || "");
        return m ? { symbol: m, name: it.shortname || it.longname || it.symbol, market: m.split(":")[0] } : null;
      })
      .filter(Boolean) as SymInfo[];
  } catch { /* 忽略 */ }

  const seen = new Set<string>();
  const out: SymInfo[] = [];
  for (const s of [...local, ...yahoo]) {
    if (!seen.has(s.symbol)) { seen.add(s.symbol); out.push(s); }
  }
  return out.slice(0, 10);
}
