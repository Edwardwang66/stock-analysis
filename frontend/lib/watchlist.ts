// 自选列表(localStorage 持久化,静态站点可用)。
const KEY = "watchlist";

export function getWatchlist(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function inWatchlist(symbol: string): boolean {
  return getWatchlist().includes(symbol);
}

export function toggleWatchlist(symbol: string): string[] {
  const list = getWatchlist();
  const next = list.includes(symbol) ? list.filter((s) => s !== symbol) : [...list, symbol];
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("watchlist-changed"));
  return next;
}

// ---- 备份/恢复(自选 + 价格提醒,跨设备迁移用;无账号体系下的轻方案) ----

export function exportUserData(): void {
  const data = {
    version: 2,
    exportedAt: new Date().toISOString(),
    watchlist: getWatchlist(),
    alerts: JSON.parse(localStorage.getItem("alerts:v1") || "[]"),
    portfolio: JSON.parse(localStorage.getItem("portfolio:v1") || "[]"),
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `stock-dashboard-backup-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/** 合并导入(并集,不覆盖现有);返回新增自选数,格式错误抛异常。 */
export function importUserData(text: string): number {
  const data = JSON.parse(text);
  if (!data || !Array.isArray(data.watchlist)) throw new Error("格式不对:缺 watchlist 数组");
  const cur = getWatchlist();
  const incoming = data.watchlist.filter((s: unknown): s is string => typeof s === "string" && /^[A-Z]+:.+$/.test(s as string));
  const merged = Array.from(new Set([...cur, ...incoming]));
  localStorage.setItem(KEY, JSON.stringify(merged));
  if (Array.isArray(data.alerts)) {
    const curAlerts = JSON.parse(localStorage.getItem("alerts:v1") || "[]");
    const ids = new Set(curAlerts.map((a: any) => a?.id));
    const add = data.alerts.filter((a: any) => a && a.id && a.symbol && !ids.has(a.id));
    localStorage.setItem("alerts:v1", JSON.stringify([...curAlerts, ...add]));
    window.dispatchEvent(new Event("alerts-changed"));
  }
  if (Array.isArray(data.portfolio)) {
    const curPf = JSON.parse(localStorage.getItem("portfolio:v1") || "[]");
    const ids = new Set(curPf.map((h: any) => h?.id));
    const add = data.portfolio.filter((h: any) => h && h.id && h.symbol && !ids.has(h.id));
    localStorage.setItem("portfolio:v1", JSON.stringify([...curPf, ...add]));
    window.dispatchEvent(new Event("portfolio-changed"));
  }
  window.dispatchEvent(new Event("watchlist-changed"));
  return merged.length - cur.length;
}
