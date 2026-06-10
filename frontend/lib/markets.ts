// 各市场标签与默认标的(用于看板分区/热力图)。
// 排序即产品重心:美股 + A股 为主,其余次之(日/韩/德为 2026-06 新增覆盖)。
export const MARKETS = [
  { key: "ALL", label: "全部" },
  { key: "US", label: "美股" },
  { key: "CN", label: "A股" },
  { key: "HK", label: "港股" },
  { key: "CRYPTO", label: "加密" },
  { key: "JP", label: "日股" },
  { key: "KR", label: "韩股" },
  { key: "DE", label: "德股" },
] as const;

// 港股代码用 4 位(Yahoo 用 0700.HK);日 .T / 韩 .KS / 德 .DE
export const DEFAULT_SYMBOLS: Record<string, string[]> = {
  US: ["US:AAPL", "US:MSFT", "US:NVDA", "US:TSLA", "US:GOOGL", "US:AMZN", "US:META"],
  CN: ["CN:600519", "CN:000001", "CN:600036", "CN:601318", "CN:300750"],
  HK: ["HK:0700", "HK:9988", "HK:3690", "HK:0939", "HK:1810"],
  CRYPTO: ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT", "CRYPTO:BNBUSDT", "CRYPTO:XRPUSDT"],
  JP: ["JP:7203", "JP:6758", "JP:9984"],
  KR: ["KR:005930", "KR:000660", "KR:373220"],
  DE: ["DE:SAP", "DE:SIE", "DE:VOW3"],
};

export function symbolsForTab(tab: string): string[] {
  if (tab === "ALL") return Object.values(DEFAULT_SYMBOLS).flat();
  return DEFAULT_SYMBOLS[tab] ?? [];
}

export const MARKET_LABEL: Record<string, string> = {
  US: "美股", CN: "A股", HK: "港股", CRYPTO: "加密",
  JP: "日股", KR: "韩股", DE: "德股", IDX: "指数",
};

// 「全部」视图分组顺序(美股/A股优先)
export const GROUP_ORDER = ["US", "CN", "HK", "CRYPTO", "JP", "KR", "DE"];

// 指数概览(IDX: 前缀 → Yahoo 代码原样直传,如 ^GSPC / 000001.SS)
export const INDEX_SYMBOLS: string[] = [
  "IDX:^GSPC", "IDX:^IXIC", "IDX:^DJI", "IDX:000001.SS", "IDX:^HSI",
  "IDX:^N225", "IDX:^KS11", "IDX:^GDAXI",
];

/** 从 "US:AAPL" 取市场前缀。 */
export function marketOf(symbol: string): string {
  return (symbol.split(":")[0] || "").toUpperCase();
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
  { symbol: "IDX:^GSPC", name: "标普500 S&P500", market: "IDX" },
  { symbol: "IDX:^IXIC", name: "纳斯达克 NASDAQ", market: "IDX" },
  { symbol: "IDX:^DJI", name: "道琼斯 DowJones", market: "IDX" },
  { symbol: "IDX:^HSI", name: "恒生指数 HSI", market: "IDX" },
  { symbol: "IDX:000001.SS", name: "上证指数 SSE", market: "IDX" },
  { symbol: "IDX:^N225", name: "日经225 Nikkei", market: "IDX" },
  { symbol: "IDX:^KS11", name: "韩国KOSPI", market: "IDX" },
  { symbol: "IDX:^GDAXI", name: "德国DAX", market: "IDX" },
  { symbol: "JP:7203", name: "丰田汽车 Toyota", market: "JP" },
  { symbol: "JP:6758", name: "索尼 Sony", market: "JP" },
  { symbol: "JP:9984", name: "软银集团 SoftBank", market: "JP" },
  { symbol: "JP:8306", name: "三菱UFJ MUFG", market: "JP" },
  { symbol: "JP:6861", name: "基恩士 Keyence", market: "JP" },
  { symbol: "KR:005930", name: "三星电子 Samsung", market: "KR" },
  { symbol: "KR:000660", name: "SK海力士 SKHynix", market: "KR" },
  { symbol: "KR:373220", name: "LG新能源 LGES", market: "KR" },
  { symbol: "KR:035420", name: "NAVER", market: "KR" },
  { symbol: "DE:SAP", name: "思爱普 SAP", market: "DE" },
  { symbol: "DE:SIE", name: "西门子 Siemens", market: "DE" },
  { symbol: "DE:VOW3", name: "大众汽车 Volkswagen", market: "DE" },
  { symbol: "DE:BMW", name: "宝马 BMW", market: "DE" },
  { symbol: "DE:ALV", name: "安联 Allianz", market: "DE" },
];

export const NAMES: Record<string, string> = Object.fromEntries(
  LOCAL_SYMBOLS.map((s) => [s.symbol, s.name.split(" ")[0]])
);

export function nameOf(symbol: string): string {
  return NAMES[symbol] || symbol.split(":")[1] || symbol;
}
