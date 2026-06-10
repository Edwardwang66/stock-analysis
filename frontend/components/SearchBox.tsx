"use client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { searchSymbols } from "@/lib/search";
import type { SymInfo } from "@/lib/markets";

const MK: Record<string, string> = {
  US: "美股", HK: "港股", CN: "A股", CRYPTO: "加密", IDX: "指数",
  JP: "日股", KR: "韩股", DE: "德股", GB: "英股",
};

export default function SearchBox() {
  const [q, setQ] = useState("");
  const [list, setList] = useState<SymInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // 防抖搜索
  useEffect(() => {
    if (!q.trim()) { setList([]); return; }
    const t = setTimeout(async () => {
      const r = await searchSymbols(q);
      setList(r); setOpen(true); setHi(0);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  // 点击外部关闭
  useEffect(() => {
    const h = (e: MouseEvent) => { if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  // 全局快捷键 “/” 聚焦搜索(输入框内不拦截)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (e.key === "/" && tag !== "INPUT" && tag !== "TEXTAREA") {
        e.preventDefault();
        boxRef.current?.querySelector("input")?.focus();
      }
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, []);

  function goto(sym: string) {
    setOpen(false); setQ("");
    router.push(`/symbol/?s=${encodeURIComponent(sym)}`);
  }

  function onKey(e: React.KeyboardEvent) {
    if (!open || !list.length) {
      if (e.key === "Enter" && q.trim()) goto(q.trim().toUpperCase());
      return;
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((h) => Math.min(h + 1, list.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); goto(list[hi]?.symbol || q.trim().toUpperCase()); }
    else if (e.key === "Escape") setOpen(false);
  }

  return (
    <div className="searchbox" ref={boxRef}>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => list.length && setOpen(true)}
        onKeyDown={onKey}
        placeholder="搜索:苹果 / AAPL / 茅台 / 0700 / BTC …(按 / 聚焦)"
        autoComplete="off"
      />
      {open && list.length > 0 && (
        <div className="suggest">
          {list.map((s, i) => (
            <div
              key={s.symbol}
              className={`suggest-item ${i === hi ? "hi" : ""}`}
              onMouseEnter={() => setHi(i)}
              onMouseDown={(e) => { e.preventDefault(); goto(s.symbol); }}
            >
              <span className="s-name">{s.name}</span>
              <span className="s-meta">{MK[s.market] || s.market} · {s.symbol}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
