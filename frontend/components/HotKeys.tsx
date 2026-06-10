"use client";
// ⌨️ 全站快捷键:g+键 跳页(g d 总览 / g h 首页 / g r 报告 / g t 追踪 / g s 选股 / g a 告警 / g ? 帮助)。
// 输入框聚焦时不触发;800ms 内按第二键生效。
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

const MAP: Record<string, string> = {
  h: "/", d: "/desk/", r: "/reports/", t: "/tracker/", s: "/screener/",
  a: "/alerts/", i: "/intel/", p: "/portfolio/", "?": "/help/", "/": "/help/",
};

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
