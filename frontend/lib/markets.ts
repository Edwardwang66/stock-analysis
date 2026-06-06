// 各市场标签与默认标的(用于看板分区/热力图)。
export const MARKETS = [
  { key: "ALL", label: "全部" },
  { key: "US", label: "美股" },
  { key: "HK", label: "港股" },
  { key: "CN", label: "A股" },
  { key: "CRYPTO", label: "加密" },
] as const;

export const DEFAULT_SYMBOLS: Record<string, string[]> = {
  US: ["US:AAPL", "US:MSFT", "US:NVDA", "US:TSLA", "US:GOOGL", "US:AMZN", "US:META"],
  HK: ["HK:00700", "HK:09988", "HK:03690", "HK:00939", "HK:01810"],
  CN: ["CN:600519", "CN:000001", "CN:600036", "CN:601318", "CN:300750"],
  CRYPTO: ["CRYPTO:BTCUSDT", "CRYPTO:ETHUSDT", "CRYPTO:SOLUSDT", "CRYPTO:BNBUSDT", "CRYPTO:XRPUSDT"],
};

export function symbolsForTab(tab: string): string[] {
  if (tab === "ALL") return Object.values(DEFAULT_SYMBOLS).flat();
  return DEFAULT_SYMBOLS[tab] ?? [];
}

// 常见标的中文名(展示用,缺省回退代码)
export const NAMES: Record<string, string> = {
  "US:AAPL": "苹果", "US:MSFT": "微软", "US:NVDA": "英伟达", "US:TSLA": "特斯拉",
  "US:GOOGL": "谷歌", "US:AMZN": "亚马逊", "US:META": "Meta",
  "HK:00700": "腾讯控股", "HK:09988": "阿里巴巴", "HK:03690": "美团", "HK:00939": "建设银行", "HK:01810": "小米集团",
  "CN:600519": "贵州茅台", "CN:000001": "平安银行", "CN:600036": "招商银行", "CN:601318": "中国平安", "CN:300750": "宁德时代",
  "CRYPTO:BTCUSDT": "比特币", "CRYPTO:ETHUSDT": "以太坊", "CRYPTO:SOLUSDT": "Solana", "CRYPTO:BNBUSDT": "BNB", "CRYPTO:XRPUSDT": "瑞波",
};

export function nameOf(symbol: string): string {
  return NAMES[symbol] || symbol.split(":")[1] || symbol;
}
