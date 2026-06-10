// 个股新闻(Yahoo Finance RSS,免费无 key;经公共代理取 XML,失败静默)。
import { fetchTextViaProxy, parseSymbol } from "./datasource";

export interface NewsItem { title: string; link: string; pubDate: string | null; ts: number }

// 各市场 → Yahoo RSS 代码
function rssCode(symbol: string): string | null {
  const { market, code } = parseSymbol(symbol);
  if (market === "US") return code;
  if (market === "HK") return `${code.padStart(4, "0")}.HK`;
  if (market === "CN") return code.startsWith("6") ? `${code}.SS` : `${code}.SZ`;
  if (market === "IDX") return code;
  if (market === "CRYPTO") {
    // BTCUSDT → BTC-USD(Yahoo 加密代码)
    const base = code.replace(/(USDT|USD|BUSD)$/, "");
    return base ? `${base}-USD` : null;
  }
  return null;
}

const CACHE = new Map<string, { items: NewsItem[]; at: number }>();
const TTL = 10 * 60_000;

export async function getNews(symbol: string, limit = 6): Promise<NewsItem[]> {
  const code = rssCode(symbol);
  if (!code) return [];
  const hit = CACHE.get(code);
  if (hit && Date.now() - hit.at < TTL) return hit.items.slice(0, limit);

  const url = `https://feeds.finance.yahoo.com/rss/2.0/headline?s=${encodeURIComponent(code)}&region=US&lang=en-US`;
  const xml = await fetchTextViaProxy(url);
  const doc = new DOMParser().parseFromString(xml, "text/xml");
  const items: NewsItem[] = Array.from(doc.querySelectorAll("item")).map((it) => {
    const pub = it.querySelector("pubDate")?.textContent ?? null;
    return {
      title: it.querySelector("title")?.textContent?.trim() ?? "",
      link: it.querySelector("link")?.textContent?.trim() ?? "",
      pubDate: pub,
      ts: pub ? Date.parse(pub) || 0 : 0,
    };
  }).filter((x) => x.title && x.link);
  items.sort((a, b) => b.ts - a.ts);
  CACHE.set(code, { items, at: Date.now() });
  return items.slice(0, limit);
}

export function timeAgo(ts: number): string {
  if (!ts) return "";
  const m = Math.floor((Date.now() - ts) / 60000);
  if (m < 1) return "刚刚";
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  return `${Math.floor(h / 24)} 天前`;
}
