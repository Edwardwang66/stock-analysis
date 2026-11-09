"use client";
// ⌨️ 全站快捷键:g+键 跳页(映射表即 components/Nav.tsx 的 NAV_ITEMS:g h 首页 / g d 总览 / g s 选股 / g t 追踪 /
// g i 情报 / g r 报告 / g p 持仓 / g a 告警 / g o 数据源 / g ? 帮助;g / 也是帮助)。
// 输入框聚焦时不触发;800ms 内按第二键生效。
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { NAV_ITEMS } from "@/components/Nav";

const MAP: Record<string, string> = Object.fromEntries(NAV_ITEMS.map((it) => [it.key, it.href]));
MAP["/"] = "/help/";

export default function HotKeys() {
  const router = useRouter();
  const armed = useRef<number>(0);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const now = Date.now();
      if (e.key.toLowerCase() === "g") { armed.current = now; return; }
      if (now - armed.current < 800) {
        const to = MAP[e.key.toLowerCase()];
        if (to) { e.preventDefault(); router.push(to); }
        armed.current = 0;
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [router]);
  return null;
}
