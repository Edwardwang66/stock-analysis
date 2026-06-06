// 免费数据源登记表(2026-06 实测)。status: 已接入 / 可接入(已验证可用,待接) / 不可用。
export interface DataSource {
  name: string; provides: string; market: string;
  cors: "✅" | "❌" | "—"; key: "无" | "免费key" | "—";
  status: "已接入" | "可接入" | "不可用"; note: string;
}

export const SOURCES: DataSource[] = [
  // —— 已接入 ——
  { name: "Binance (data-api.binance.vision)", provides: "暗号 行情 / K线 / 逐笔 / 盘口", market: "加密", cors: "✅", key: "无", status: "已接入", note: "真实逐笔(aggTrades)+ 盘口(depth)→ 真·主力资金/买卖盘" },
  { name: "Yahoo Finance chart", provides: "美/港/A股 行情 + K线(含分钟)", market: "美·港·A", cors: "❌", key: "无", status: "已接入", note: "无 CORS,经公共代理(allorigins 优先)" },
  { name: "SEC EDGAR XBRL", provides: "美股基本面财报(营收/净利/资产…)", market: "美股", cors: "✅", key: "无", status: "已接入", note: "美国证监会官方;companyconcept 端点" },
  { name: "Frankfurter (ECB)", provides: "外汇汇率", market: "外汇", cors: "✅", key: "无", status: "已接入", note: "欧洲央行参考汇率;回退 open.er-api" },
  { name: "OKX", provides: "暗号 跨所报价", market: "加密", cors: "✅", key: "无", status: "已接入", note: "跨交易所校验" },
  { name: "Coinbase", provides: "暗号 跨所报价", market: "加密", cors: "✅", key: "无", status: "已接入", note: "v2/prices spot" },
  { name: "CoinPaprika", provides: "暗号 报价 / 市值", market: "加密", cors: "✅", key: "无", status: "已接入", note: "含市值/供应量" },
  { name: "open.er-api", provides: "外汇汇率(备用)", market: "外汇", cors: "✅", key: "无", status: "已接入", note: "Frankfurter 失败时回退" },

  // —— 可接入(已验证,后续接) ——
  { name: "CoinGecko", provides: "暗号 价格/市值/历史/全局", market: "加密", cors: "✅", key: "无", status: "可接入", note: "限频 ~10-30/分;含 /global、/trending" },
  { name: "Yahoo search", provides: "代码联想 / 搜索", market: "全市场", cors: "❌", key: "无", status: "可接入", note: "经代理;做搜索框自动补全" },
  { name: "Yahoo spark", provides: "多标的迷你走势", market: "美·港·A", cors: "❌", key: "无", status: "可接入", note: "轻量批量 sparkline" },
  { name: "Kraken", provides: "暗号 行情 / OHLC", market: "加密", cors: "❌", key: "无", status: "可接入", note: "服务端可用;浏览器需代理" },
  { name: "AlphaVantage", provides: "美股/外汇/基本面", market: "美·外汇", cors: "✅", key: "免费key", status: "可接入", note: "免费 25/日;demo key 仅 IBM 等" },
  { name: "Finnhub", provides: "美股 实时/基本面/新闻", market: "美股", cors: "✅", key: "免费key", status: "可接入", note: "免费 60/分,CORS OK" },

  // —— 服务端可用(浏览器受限) ——
  { name: "Sina hq.sinajs.cn", provides: "A/港/美股 实时(GBK)", market: "A·港·美", cors: "❌", key: "无", status: "可接入", note: "需 Referer + GBK 解码,仅后端" },
  { name: "Tencent qt.gtimg.cn", provides: "A股 实时 + 5档盘口", market: "A股", cors: "❌", key: "无", status: "可接入", note: "含买卖5档,仅后端;GBK" },

  // —— 不可用 ——
  { name: "Eastmoney push2", provides: "A股 实时 + 真·资金流", market: "A股", cors: "❌", key: "无", status: "不可用", note: "本环境 502/网络策略拦截;境内部署可用" },
  { name: "corsproxy.io", provides: "CORS 代理", market: "—", cors: "—", key: "无", status: "不可用", note: "已改为落地页,失效;改用 allorigins/codetabs" },
  { name: "Stooq CSV", provides: "全球 EOD", market: "全市场", cors: "❌", key: "无", status: "不可用", note: "加了 JS 反爬挑战页" },
  { name: "CoinCap", provides: "暗号 行情", market: "加密", cors: "—", key: "—", status: "不可用", note: "改为反爬/需 key" },
  { name: "api.binance.com (本体)", provides: "暗号 行情", market: "加密", cors: "✅", key: "无", status: "不可用", note: "451 地域封;用 data-api.binance.vision" },
];
