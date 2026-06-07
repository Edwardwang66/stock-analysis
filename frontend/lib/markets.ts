// 各市场标签与默认标的(用于看板分区/热力图)。
export const MARKETS = [
  { key: "ALL", label: "全部" },
  { key: "US", label: "美股" },
  { key: "HK", label: "港股" },
  { key: "CN", label: "A股" },
  { key: "CRYPTO", label: "加密" },
] as const;

// 港股代码用 4 位(Yahoo 用 0700.HK)
export const DEFAULT_SYMBOLS: Record<string, string[]> = {
  US: ["US:AAPL", "US:MSFT", "US:NVDA", "US:TSLA", "US:GOOGL", "US:AMZN", "US:META"],
  HK: ["HK:0700", "HK:9988", "HK:3690", "HK:0939", "HK:1810"],
  CN: ["CN:600519", "CN:000001", "CN:600036", "CN:601318", "CN:300750"],
  CRYPTO: ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT", "CRYPTO:BNBUSDT", "CRYPTO:XRPUSDT"],
};

export function symbolsForTab(tab: string): string[] {
  if (tab === "ALL") return Object.values(DEFAULT_SYMBOLS).flat();
  return DEFAULT_SYMBOLS[tab] ?? [];
}

// 本地常用标的(含中文名)—— 无后端时的离线联想 + 名称展示
export interface SymInfo { symbol: string; name: string; market: string }
export const LOCAL_SYMBOLS: SymInfo[] = [
  { symbol: "US:AAPL", name: "苹果 Apple", market: "US" },
  { symbol: "US:MSFT", name: "微软 Microsoft", market: "US" },
  { symbol: "US:NVDA", name: "英伟达 Nvidia", market: "US" },
  { symbol: "US:TSLA", name: "特斯拉 Tesla", market: "US" },
  { symbol: "US:GOOGL", name: "谷歌 Google", market: "US" },
  { symbol: "US:AMZN", name: "亚马逊 Amazon", market: "US" },
  { symbol: "US:META", name: "Meta 脸书", market: "US" },
  { symbol: "US:NFLX", name: "奈飞 Netflix", market: "US" },
  { symbol: "US:AMD", name: "AMD", market: "US" },
  { symbol: "US:BABA", name: "阿里巴巴 Alibaba", market: "US" },
  { symbol: "HK:0700", name: "腾讯控股 Tencent", market: "HK" },
  { symbol: "HK:9988", name: "阿里巴巴 Alibaba", market: "HK" },
  { symbol: "HK:3690", name: "美团 Meituan", market: "HK" },
  { symbol: "HK:0939", name: "建设银行", market: "HK" },
  { symbol: "HK:1810", name: "小米集团 Xiaomi", market: "HK" },
  { symbol: "HK:9618", name: "京东 JD", market: "HK" },
  { symbol: "HK:0941", name: "中国移动", market: "HK" },
  { symbol: "HK:1299", name: "友邦保险 AIA", market: "HK" },
  { symbol: "CN:600519", name: "贵州茅台", market: "CN" },
  { symbol: "CN:000001", name: "平安银行", market: "CN" },
  { symbol: "CN:600036", name: "招商银行", market: "CN" },
  { symbol: "CN:601318", name: "中国平安", market: "CN" },
  { symbol: "CN:300750", name: "宁德时代", market: "CN" },
  { symbol: "CN:000858", name: "五粮液", market: "CN" },
  { symbol: "CN:002594", name: "比亚迪", market: "CN" },
  { symbol: "CN:600276", name: "恒瑞医药", market: "CN" },
  { symbol: "CRYPTO:BTCUSDT", name: "比特币 Bitcoin", market: "CRYPTO" },
  { symbol: "CRYPTO:ETHUSDT", name: "以太坊 Ethereum", market: "CRYPTO" },
  { symbol: "CRYPTO:SOLUSDT", name: "Solana", market: "CRYPTO" },
  { symbol: "CRYPTO:BNBUSDT", name: "BNB", market: "CRYPTO" },
  { symbol: "CRYPTO:XRPUSDT", name: "瑞波 XRP", market: "CRYPTO" },
  { symbol: "CRYPTO:DOGEUSDT", name: "狗狗币 Dogecoin", market: "CRYPTO" },
];

export const NAMES: Record<string, string> = Object.fromEntries(
  LOCAL_SYMBOLS.map((s) => [s.symbol, s.name.split(" ")[0]])
);

export function nameOf(symbol: string): string {
  return NAMES[symbol] || symbol.split(":")[1] || symbol;
}
