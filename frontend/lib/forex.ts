// 外汇汇率 —— Frankfurter(ECB 官方,无 key、CORS *),失败回退 open.er-api。
export interface Forex { base: string; date: string; rates: Record<string, number>; source: string }

const SYMBOLS = ["CNY", "HKD", "EUR", "JPY", "GBP", "AUD"];

export async function getForex(base = "USD"): Promise<Forex> {
  try {
    const r = await fetch(`https://api.frankfurter.dev/v1/latest?base=${base}&symbols=${SYMBOLS.join(",")}`);
    const d = await r.json();
    if (d?.rates) return { base: d.base, date: d.date, rates: d.rates, source: "Frankfurter / ECB" };
  } catch { /* fall through */ }
  const r = await fetch(`https://open.er-api.com/v6/latest/${base}`);
  const d = await r.json();
  const rates: Record<string, number> = {};
  SYMBOLS.forEach((s) => { if (d.rates?.[s] != null) rates[s] = d.rates[s]; });
  return { base, date: d.time_last_update_utc?.slice(0, 16) || "", rates, source: "open.er-api" };
}
