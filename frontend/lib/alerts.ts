// 价格提醒(纯前端:localStorage 存储,首页 30s 刷新循环顺带检查,零后端成本)。
// 一次性触发:命中后标记 triggered,不重复打扰;可手动删除/重设。

export interface PriceAlert {
  id: string;
  symbol: string;
  dir: "above" | "below";   // 价格 ≥ / ≤ 目标时触发
  target: number;
  createdAt: number;
  triggeredAt: number | null;
  triggeredPrice?: number;
}

const KEY = "alerts:v1";

function read(): PriceAlert[] {
  if (typeof window === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function write(list: PriceAlert[]): void {
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* ignore */ }
  window.dispatchEvent(new Event("alerts-changed"));
}

export function getAlerts(symbol?: string): PriceAlert[] {
  const all = read();
  return symbol ? all.filter((a) => a.symbol === symbol) : all;
}

export function addAlert(symbol: string, target: number, currentPrice: number | null): PriceAlert {
  const dir: "above" | "below" =
    currentPrice != null && target < currentPrice ? "below" : "above";
  const a: PriceAlert = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    symbol: symbol.toUpperCase(), dir, target,
    createdAt: Date.now(), triggeredAt: null,
  };
  write([...read(), a]);
  return a;
}

export function removeAlert(id: string): void {
  write(read().filter((a) => a.id !== id));
}

/** 改目标价(图上拖拽提醒线用):重新判定方向,并复位触发状态。 */
export function updateAlertTarget(id: string, target: number, currentPrice: number | null): void {
  write(read().map((a) => (a.id === id
    ? {
        ...a, target,
        dir: (currentPrice != null && target < currentPrice ? "below" : "above") as PriceAlert["dir"],
        triggeredAt: null, triggeredPrice: undefined,
      }
    : a)));
}

export function clearTriggered(): void {
  write(read().filter((a) => !a.triggeredAt));
}

/** 用最新报价检查所有未触发提醒;返回本轮新触发的。 */
export function checkAlerts(prices: Record<string, number | null | undefined>): PriceAlert[] {
  const list = read();
  const fired: PriceAlert[] = [];
  for (const a of list) {
    if (a.triggeredAt) continue;
    const p = prices[a.symbol];
    if (p == null) continue;
    if ((a.dir === "above" && p >= a.target) || (a.dir === "below" && p <= a.target)) {
      a.triggeredAt = Date.now();
      a.triggeredPrice = p;
      fired.push(a);
    }
  }
  if (fired.length) write(list);
  return fired;
}

/** 浏览器通知(用户允许时);失败静默,页内横幅兜底。 */
export function notify(fired: PriceAlert[], nameOf: (s: string) => string): void {
  if (!fired.length || typeof Notification === "undefined") return;
  const send = () => fired.forEach((a) => {
    try {
      new Notification(`${nameOf(a.symbol)} ${a.dir === "above" ? "≥" : "≤"} ${a.target}`, {
        body: `当前 ${a.triggeredPrice} · ${a.symbol}`,
      });
    } catch { /* ignore */ }
  });
  if (Notification.permission === "granted") send();
  else if (Notification.permission !== "denied") {
    Notification.requestPermission().then((p) => { if (p === "granted") send(); }).catch(() => {});
  }
}
