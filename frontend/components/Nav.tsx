"use client";
// 🧭 全站统一导航:每页同一组入口,当前页高亮。
// 快捷键 g+字母 由 components/HotKeys.tsx 直接读取本表,保证按键与导航永远一致。
import Link from "next/link";
import { usePathname } from "next/navigation";

export interface NavItem { href: string; icon: string; label: string; key: string }

export const NAV_ITEMS: NavItem[] = [
  { href: "/",           icon: "🏠", label: "首页",   key: "h" },
  { href: "/desk/",      icon: "📋", label: "总览",   key: "d" },
  { href: "/screener/",  icon: "📈", label: "选股",   key: "s" },
  { href: "/tracker/",   icon: "🎯", label: "追踪",   key: "t" },
  { href: "/intel/",     icon: "🛰️", label: "情报",   key: "i" },
  { href: "/reports/",   icon: "📜", label: "报告",   key: "r" },
  { href: "/portfolio/", icon: "💼", label: "持仓",   key: "p" },
  { href: "/alerts/",    icon: "⏰", label: "告警",   key: "a" },
  { href: "/sources/",   icon: "🔌", label: "数据源", key: "o" },
  { href: "/help/",      icon: "❓", label: "帮助",   key: "?" },
];

/** 把 usePathname() 归一成带尾斜杠的站内路径(App Router 已去掉 basePath;此处再兜底一次)。 */
function normalizePath(path: string | null): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  let p = path || "/";
  if (base && p.startsWith(base)) p = p.slice(base.length);
  if (!p.startsWith("/")) p = `/${p}`;
  if (!p.endsWith("/")) p = `${p}/`;
  return p;
}

export default function Nav() {
  const current = normalizePath(usePathname());
  return (
    <nav className="nav" aria-label="站内导航">
      {NAV_ITEMS.map((it) => {
        const active = it.href === "/" ? current === "/" : current.startsWith(it.href);
        return (
          <Link
            key={it.href}
            href={it.href}
            className={active ? "active" : undefined}
            aria-current={active ? "page" : undefined}
            title={`${it.label} · 快捷键 g ${it.key}`}
          >
            <span className="nav-icon" aria-hidden="true">{it.icon}</span>
            <span className="nav-label">{it.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
