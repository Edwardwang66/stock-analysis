// Vercel Edge Function:K线代理。GET /api/ohlcv?symbol=US:AAPL&range=1y&interval=1d
// 边缘缓存:日/周线 60s,分钟线 30s。
export const runtime = "edge";

const UA = { "User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-edge/1.0)" };
const RANGES = new Set(["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"]);
const INTERVALS: Record<string, string> = {
  "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d", "1wk": "1wk",
};

function yahooCode(market: string, code: string): string | null {
  switch (market) {
    case "US": case "IDX": return code;
    case "HK": return `${code.padStart(4, "0")}.HK`;
    case "CN": return code.startsWith("6") ? `${code}.SS` : `${code}.SZ`;
    case "JP": return `${code}.T`;
    case "KR": return `${code}.KS`;
    case "DE": return `${code}.DE`;
    case "GB": return `${code}.L`;
    default: return null;
  }
}

export async function GET(req: Request) {
  const u = new URL(req.url);
  const symbol = (u.searchParams.get("symbol") ?? "").toUpperCase();
  const range = RANGES.has(u.searchParams.get("range") ?? "") ? u.searchParams.get("range")! : "1y";
  const interval = INTERVALS[u.searchParams.get("interval") ?? ""] ? (u.searchParams.get("interval") as string) : "1d";
  const [market, ...rest] = symbol.split(":");
  const code = rest.join(":");

  try {
    if (market === "CRYPTO") {
      const bi = interval === "1wk" ? "1w" : interval === "1h" ? "1h" : interval;
      const limit = ["1m", "5m", "15m", "30m", "1h"].includes(interval) ? 500
        : ({ "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1000 } as any)[range] ?? 365;
      const r = await fetch(`https://data-api.binance.vision/api/v3/klines?symbol=${code}&interval=${bi}&limit=${limit}`, { headers: UA });
      const d: any[] = await r.json();
      const bars = d.map((k) => ({ time: Math.floor(k[0] / 1000), open: +k[1], high: +k[2], low: +k[3], close: +k[4], volume: +k[5] }));
      return ok(bars, 30);
    }
    const yc = yahooCode(market, code);
    if (!yc) return new Response(JSON.stringify({ error: `unsupported market ${market}` }), { status: 400 });
    const r = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yc)}?range=${range}&interval=${INTERVALS[interval]}`,
      { headers: UA },
    );
    const res = (await r.json())?.chart?.result?.[0];
    if (!res) return new Response(JSON.stringify({ error: "no data" }), { status: 404 });
    const ts: number[] = res.timestamp ?? [];
    const q = res.indicators.quote[0];
    const bars: any[] = [];
    for (let i = 0; i < ts.length; i++) {
      if ([q.open[i], q.high[i], q.low[i], q.close[i]].some((x: any) => x == null)) continue;
      bars.push({ time: ts[i], open: q.open[i], high: q.high[i], low: q.low[i], close: q.close[i], volume: q.volume?.[i] ?? 0 });
    }
    return ok(bars, ["1d", "1wk"].includes(interval) ? 60 : 30);
  } catch (e: any) {
    return new Response(JSON.stringify({ error: String(e?.message ?? e) }), { status: 502 });
  }
}

function ok(bars: any[], maxage: number) {
  return new Response(JSON.stringify({ bars }), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": `public, s-maxage=${maxage}, stale-while-revalidate=${maxage * 3}`,
    },
  });
}
