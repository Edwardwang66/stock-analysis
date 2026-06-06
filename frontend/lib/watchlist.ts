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
