// 标的联想搜索:双语库(中/英/代码三路匹配)优先 → 后端 → Yahoo 兜底。
// 输入「茅台」「moutai」「600519」「美团」「meituan」均可命中。
import { LOCAL_SYMBOLS, type SymInfo } from "./markets";
import { NAME_DB } from "./names";

// NAME_DB(~330 条双语)展开为可搜索表,与 LOCAL_SYMBOLS 合并去重
const DB_SYMBOLS: SymInfo[] = Object.entries(NAME_DB).map(([symbol, [zh, en]]) => ({
  symbol, name: `${zh} ${en}`, market: symbol.split(":")[0],
}));
const SEARCHABLE: SymInfo[] = (() => {
  const seen = new Set<string>();
  const out: SymInfo[] = [];
  for (const s of [...DB_SYMBOLS, ...LOCAL_SYMBOLS]) {
    if (!seen.has(s.symbol)) { seen.add(s.symbol); out.push(s); }
  }
  return out;
})();

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

  // 双语库 + 本地常用表(代码/中文/英文三路;前缀命中排前)
  const local = SEARCHABLE
    .filter((s) => s.symbol.toLowerCase().includes(ql) || s.name.toLowerCase().includes(ql))
    .sort((a, b) => {
      const ap = a.symbol.toLowerCase().split(":")[1]?.startsWith(ql) || a.name.toLowerCase().startsWith(ql) ? 0 : 1;
      const bp = b.symbol.toLowerCase().split(":")[1]?.startsWith(ql) || b.name.toLowerCase().startsWith(ql) ? 0 : 1;
      return ap - bp;
    })
    .slice(0, 8);
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
