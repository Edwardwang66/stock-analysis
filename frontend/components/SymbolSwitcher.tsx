"use client";
// 个股页内标的切换器(交互参考 Hyperliquid 市场切换):
// 点击标题弹出 搜索 + 自选 + 热门 下拉,选中原地换标的 —— 不用回首页重搜。
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { searchSymbols } from "@/lib/search";
import { getWatchlist } from "@/lib/watchlist";
import { getCachedQuotesSync, getQuotes, type Quote } from "@/lib/datasource";
import { LOCAL_SYMBOLS, nameOf, type SymInfo } from "@/lib/markets";
import { useLang } from "@/lib/names";

const MK: Record<string, string> = {
  US: "美股", HK: "港股", CN: "A股", CRYPTO: "加密", IDX: "指数",
  JP: "日股", KR: "韩股", DE: "德股", GB: "英股",
};

interface Row extends SymInfo { group: string }

export default function SymbolSwitcher({ symbol }: { symbol: string }) {
  const lang = useLang();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SymInfo[]>([]);
  const [hi, setHi] = useState(0);
  const [watch, setWatch] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const boxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 打开时:聚焦搜索框,读自选,拉一轮列表行情(缓存秒出)
  useEffect(() => {
    if (!open) return;
    const wl = getWatchlist();
    setWatch(wl);
    const syms = [...new Set([...wl, ...LOCAL_SYMBOLS.slice(0, 12).map((s) => s.symbol)])];
    setQuotes(getCachedQuotesSync(syms));
    getQuotes(syms, (qt) => setQuotes((m) => ({ ...m, [qt.symbol]: qt }))).catch(() => {});
    setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  // 防抖搜索
  useEffect(() => {
    if (!q.trim()) { setResults([]); setHi(0); return; }
    const t = setTimeout(async () => {
      const r = await searchSymbols(q);
      setResults(r); setHi(0);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  // 点击外部 / Esc 关闭
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  // 无搜索词时的默认列表:自选在前,热门补后(去重、排除当前标的)
  const rows = useMemo<Row[]>(() => {
    if (q.trim()) return results.map((r) => ({ ...r, group: "搜索" }));
    const seen = new Set<string>([symbol]);
    const out: Row[] = [];
    for (const s of watch) {
      if (seen.has(s)) continue;
      seen.add(s);
      out.push({ symbol: s, name: nameOf(s, lang), market: s.split(":")[0], group: "自选" });
    }
    for (const s of LOCAL_SYMBOLS) {
      if (out.length >= 16) break;
      if (seen.has(s.symbol)) continue;
      seen.add(s.symbol);
      out.push({ ...s, group: "热门" });
    }
    return out;
  }, [q, results, watch, symbol, lang]);

  function goto(sym: string) {
    setOpen(false); setQ("");
    router.push(`/symbol/?s=${encodeURIComponent(sym)}`);
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") { setOpen(false); return; }
    if (!rows.length) {
      if (e.key === "Enter" && q.trim()) goto(q.trim().toUpperCase());
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, rows.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); goto(rows[hi]?.symbol || q.trim().toUpperCase()); }
  }

  return (
    <div className="symswitch" ref={boxRef}>
      <h1 className="symswitch-h1">
        <button className="symswitch-title" onClick={() => setOpen((v) => !v)}
          title="切换标的(搜索 / 自选 / 热门)" aria-expanded={open}>
          {nameOf(symbol, lang)} <span className="caret">{open ? "▴" : "▾"}</span>
        </button>
      </h1>
      {open && (
        <div className="symswitch-drop">
          <input
            ref={inputRef} value={q}
            onChange={(e) => setQ(e.target.value)} onKeyDown={onKey}
            placeholder="搜索:苹果 / AAPL / 茅台 / 0700 / BTC …"
            autoComplete="off"
          />
          <div className="symswitch-list">
            {rows.map((r, i) => {
              const qt = quotes[r.symbol];
              const pct = qt?.changePct;
              const showGroup = i === 0 || rows[i - 1].group !== r.group;
              return (
                <div key={r.symbol}>
                  {showGroup && <div className="symswitch-group">{r.group}</div>}
                  <div className={`symswitch-row ${i === hi ? "hi" : ""}`}
                    onMouseEnter={() => setHi(i)}
                    onMouseDown={(e) => { e.preventDefault(); goto(r.symbol); }}>
                    <span className="nm">{r.name}</span>
                    <span className="cd">{MK[r.market] || r.market} · {r.symbol}</span>
                    {pct != null && (
                      <span className={`pc ${pct >= 0 ? "up" : "down"}`}>{pct >= 0 ? "+" : ""}{pct.toFixed(2)}%</span>
                    )}
                  </div>
                </div>
              );
            })}
            {!rows.length && <div className="symswitch-group">{q.trim() ? "无匹配,回车直接打开输入的代码" : "暂无自选"}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
