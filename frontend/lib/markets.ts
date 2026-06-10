// 各市场标签与默认标的(用于看板分区/热力图)。
import { displayName, getLang, type Lang } from "./names";
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
  { key: "GB", label: "英股" },
] as const;

// 港股代码用 4 位(Yahoo 用 0700.HK);日 .T / 韩 .KS / 德 .DE
// 每市场代表性标的(2026-06-10 Edward 要求扩容;名称见 lib/names.ts 双语库)
export const DEFAULT_SYMBOLS: Record<string, string[]> = {
  US: ["US:AAPL", "US:MSFT", "US:NVDA", "US:GOOGL", "US:AMZN", "US:META", "US:TSLA", "US:AVGO", "US:BRK-B", "US:JPM", "US:V", "US:MA", "US:WMT", "US:LLY", "US:UNH", "US:XOM", "US:CVX", "US:JNJ", "US:PG", "US:KO", "US:PEP", "US:ORCL", "US:CRM", "US:ADBE", "US:NFLX", "US:AMD", "US:INTC", "US:MU", "US:QCOM", "US:TXN", "US:CSCO", "US:IBM", "US:GE", "US:CAT", "US:BA", "US:GS", "US:MS", "US:BAC", "US:WFC", "US:C", "US:DIS", "US:NKE", "US:MCD", "US:SBUX", "US:PFE", "US:MRK", "US:ABBV", "US:TMO", "US:COST", "US:HD"],
  CN: ["CN:600519", "CN:000858", "CN:601318", "CN:600036", "CN:601398", "CN:601939", "CN:601288", "CN:600276", "CN:300750", "CN:002594", "CN:601012", "CN:600900", "CN:601888", "CN:600309", "CN:600887", "CN:000333", "CN:000651", "CN:002475", "CN:300059", "CN:600030", "CN:601628", "CN:601088", "CN:600028", "CN:601857", "CN:601668", "CN:600048", "CN:000002", "CN:600585", "CN:002415", "CN:002230", "CN:688981", "CN:688041", "CN:603501", "CN:603986", "CN:600941", "CN:601728", "CN:688111", "CN:603259", "CN:300760", "CN:300015", "CN:000725", "CN:601166", "CN:600000", "CN:601658", "CN:603288", "CN:600690", "CN:000568", "CN:600809", "CN:000001"],
  HK: ["HK:0700", "HK:9988", "HK:3690", "HK:1810", "HK:9618", "HK:9999", "HK:9888", "HK:1024", "HK:2015", "HK:9868", "HK:1211", "HK:0175", "HK:2333", "HK:0941", "HK:0939", "HK:1398", "HK:3988", "HK:0005", "HK:1299", "HK:2318", "HK:2628", "HK:0388", "HK:0011", "HK:2382", "HK:0981", "HK:1347", "HK:0992", "HK:0285", "HK:2018", "HK:0027", "HK:1928", "HK:0066", "HK:0001", "HK:0016", "HK:1109", "HK:0960", "HK:0883", "HK:0857", "HK:0386", "HK:1088", "HK:1093", "HK:1177", "HK:2269", "HK:2359", "HK:6160", "HK:1801", "HK:0291", "HK:2020", "HK:2331", "HK:6862"],
  CRYPTO: ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT", "CRYPTO:BNBUSDT", "CRYPTO:XRPUSDT", "CRYPTO:DOGEUSDT", "CRYPTO:ADAUSDT", "CRYPTO:AVAXUSDT", "CRYPTO:LINKUSDT", "CRYPTO:DOTUSDT", "CRYPTO:LTCUSDT", "CRYPTO:BCHUSDT", "CRYPTO:UNIUSDT", "CRYPTO:ATOMUSDT", "CRYPTO:NEARUSDT", "CRYPTO:APTUSDT", "CRYPTO:ARBUSDT", "CRYPTO:OPUSDT", "CRYPTO:FILUSDT", "CRYPTO:TRXUSDT", "CRYPTO:ETCUSDT", "CRYPTO:XLMUSDT", "CRYPTO:ICPUSDT", "CRYPTO:SUIUSDT", "CRYPTO:PEPEUSDT"],
  JP: ["JP:7203", "JP:6758", "JP:9984", "JP:8306", "JP:6861", "JP:9983", "JP:8035", "JP:6954", "JP:6501", "JP:7974", "JP:4063", "JP:6098", "JP:8316", "JP:8411", "JP:7267", "JP:7201", "JP:6902", "JP:4502", "JP:6273", "JP:6920"],
  KR: ["KR:005930", "KR:000660", "KR:373220", "KR:207940", "KR:005380", "KR:000270", "KR:035420", "KR:035720", "KR:051910", "KR:006400", "KR:005490", "KR:105560", "KR:055550", "KR:012330", "KR:066570"],
  DE: ["DE:SAP", "DE:SIE", "DE:VOW3", "DE:BMW", "DE:MBG", "DE:ALV", "DE:DTE", "DE:BAS", "DE:BAYN", "DE:ADS", "DE:AIR", "DE:IFX", "DE:MUV2", "DE:RWE", "DE:DBK"],
  GB: ["GB:SHEL", "GB:HSBA", "GB:AZN", "GB:ULVR", "GB:RR", "GB:BP", "GB:GSK", "GB:RIO", "GB:GLEN", "GB:BARC", "GB:LLOY", "GB:VOD", "GB:BT-A", "GB:TSCO", "GB:REL"],
};

export function symbolsForTab(tab: string): string[] {
  if (tab === "ALL") return Object.values(DEFAULT_SYMBOLS).flat();
  return DEFAULT_SYMBOLS[tab] ?? [];
}

export const MARKET_LABEL: Record<string, string> = {
  US: "美股", CN: "A股", HK: "港股", CRYPTO: "加密",
  JP: "日股", KR: "韩股", DE: "德股", GB: "英股", IDX: "指数",
};

// 「全部」视图分组顺序(美股/A股优先)
export const GROUP_ORDER = ["US", "CN", "HK", "CRYPTO", "JP", "KR", "DE", "GB"];

// 指数概览(IDX: 前缀 → Yahoo 代码原样直传,如 ^GSPC / 000001.SS)
export const INDEX_SYMBOLS: string[] = [
  "IDX:^GSPC", "IDX:^IXIC", "IDX:^DJI", "IDX:000001.SS", "IDX:^HSI",
  "IDX:^N225", "IDX:^KS11", "IDX:^GDAXI", "IDX:^FTSE",
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
  { symbol: "IDX:^FTSE", name: "富时100 FTSE", market: "IDX" },
  { symbol: "GB:SHEL", name: "壳牌 Shell", market: "GB" },
  { symbol: "GB:HSBA", name: "汇丰控股 HSBC", market: "GB" },
  { symbol: "GB:AZN", name: "阿斯利康(伦敦) AstraZeneca", market: "GB" },
  { symbol: "GB:ULVR", name: "联合利华 Unilever", market: "GB" },
  { symbol: "GB:RR", name: "罗尔斯罗伊斯 RollsRoyce", market: "GB" },
  { symbol: "GB:BP", name: "英国石油 BP", market: "GB" },
];

export const NAMES: Record<string, string> = Object.fromEntries(
  LOCAL_SYMBOLS.map((s) => [s.symbol, s.name.split(" ")[0]])
);

export function nameOf(symbol: string, lang?: Lang): string {
  return displayName(symbol, lang ?? getLang(), NAMES[symbol] || null);
}
