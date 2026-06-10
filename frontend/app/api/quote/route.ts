// Vercel Edge Function:自有报价代理(替代不可靠的公共 CORS 代理)。
// GET /api/quote?symbols=US:AAPL,HK:0700,IDX:^GSPC
// 边缘缓存 s-maxage=10 + SWR 30:同一标的的并发用户共享一次上游请求。
export const runtime = "edge";

const UA = { "User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-edge/1.0)" };

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

async function one(symbol: string): Promise<any> {
  const [market, ...rest] = symbol.split(":");
  const code = rest.join(":");
  try {
    if (market === "CRYPTO") {
      const r = await fetch(`https://data-api.binance.vision/api/v3/ticker/24hr?symbol=${code}`, { headers: UA });
      const d = await r.json();
      return {
        symbol, price: +d.lastPrice, change: +d.priceChange, change_pct: +d.priceChangePercent,
        high: +d.highPrice, low: +d.lowPrice, currency: "USDT", source: "Binance·edge",
      };
    }
    const yc = yahooCode(market, code);
    if (!yc) return { symbol, error: `unsupported market ${market}` };
    const r = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(yc)}?range=1d&interval=1d`,
      { headers: UA },
    );
    const m = (await r.json())?.chart?.result?.[0]?.meta;
    if (!m || m.regularMarketPrice == null) return { symbol, error: "no data" };
    const prev = m.regularMarketPreviousClose ?? m.chartPreviousClose ?? m.previousClose;
    const change = prev != null ? m.regularMarketPrice - prev : null;
    return {
      symbol, price: m.regularMarketPrice, change,
      change_pct: change != null && prev ? (change / prev) * 100 : null,
      high: m.regularMarketDayHigh ?? null, low: m.regularMarketDayLow ?? null,
      currency: m.currency ?? "", source: "Yahoo·edge",
    };
  } catch (e: any) {
    return { symbol, error: String(e?.message ?? e) };
  }
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const symbols = (url.searchParams.get("symbols") ?? "")
    .split(",").map((s) => s.trim().toUpperCase()).filter((s) => s.includes(":")).slice(0, 60);
  if (!symbols.length) {
    return new Response(JSON.stringify({ error: "symbols required" }), { status: 400 });
  }
  const rows = await Promise.all(symbols.map(one));
  return new Response(JSON.stringify(rows), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "public, s-maxage=10, stale-while-revalidate=30",
    },
  });
}
