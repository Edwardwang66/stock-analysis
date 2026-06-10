// 行业标签(静态映射,覆盖云端池;screener 临时进榜的未映射标的归"其他")。
// 改这里即可调整;后续可换成 Actions 自动从 Yahoo quoteSummary 抓取。
export const SECTORS: Record<string, string> = {
  // 指数/ETF
  "US:QQQ": "ETF/指数", "US:SQQQ": "ETF/指数", "US:SPY": "ETF/指数", "US:DJD": "ETF/指数",
  "US:TSLL": "ETF/指数", "HK:7226": "ETF/指数", "IDX:^DJI": "ETF/指数", "IDX:^HSI": "ETF/指数",
  "IDX:000001.SS": "ETF/指数",
  // 半导体/硬件
  "US:NVDA": "半导体", "US:AMD": "半导体", "US:AVGO": "半导体", "US:INTC": "半导体",
  "CN:688795": "半导体", "US:SNDK": "存储/硬件", "US:SMCI": "AI算力", "US:CSCO": "网络设备",
  "US:LITE": "光模块", "US:HOLOW": "光学/全息",
  // AI 算力/数据中心(SA LP 主题)
  "US:CRWV": "AI算力", "US:CORZ": "AI算力", "US:IREN": "AI算力", "US:APLD": "AI算力",
  "US:BE": "电力/能源", "US:MVST": "电池/储能", "CN:300750": "电池/储能",
  // 互联网/软件
  "US:MSFT": "软件", "US:NOW": "软件", "US:PLTR": "软件/AI", "US:APP": "软件/广告",
  "US:GOOG": "互联网", "US:GOOGL": "互联网", "US:META": "互联网", "US:AMZN": "互联网",
  "US:BABA": "互联网", "US:PDD": "互联网", "US:BILI": "互联网", "HK:0700": "互联网",
  "HK:9988": "互联网", "HK:3690": "互联网", "US:INFY": "软件外包",
  // 加密相关
  "US:COIN": "加密相关", "US:MSTR": "加密相关", "US:CRCL": "加密相关",
  // 量子/前沿
  "US:QUBT": "量子计算", "US:RGTI": "量子计算", "US:IONQ": "量子计算",
  "US:RR": "机器人", "US:PDYN": "机器人",
  // 航空航天/出行
  "US:RKLB": "航天", "US:BA": "航空制造", "US:EVTL": "eVTOL", "US:LILMF": "eVTOL",
  "US:RCAT": "无人机", "US:RVSN": "铁路AI", "US:TSLA": "汽车/出行", "US:NIO": "汽车/出行",
  "US:UBER": "汽车/出行",
  // 医疗
  "US:LLY": "医疗/制药", "US:AZN": "医疗/制药", "US:ILMN": "医疗/基因", "US:TEM": "医疗AI",
  "US:EBS": "医疗/生物", "US:CTKB": "医疗/仪器", "US:OSCR": "医疗/保险", "US:CI": "医疗/保险",
  "US:HUM": "医疗/保险", "HK:2359": "医疗/CXO", "HK:2269": "医疗/CXO", "CN:603259": "医疗/CXO",
  // 消费/传媒
  "US:AAPL": "消费电子", "US:SBUX": "消费", "CN:600519": "消费/白酒", "US:DIS": "传媒",
  "US:NFLX": "传媒/流媒体", "US:ROKU": "传媒/流媒体",
  // 金融
  "US:BRK-B": "金融", "US:FUTU": "金融科技", "US:APCX": "金融科技",
  // 能源/材料/其他
  "US:MARPS": "能源", "US:IMPP": "能源/油运", "US:NESR": "能源/油服", "US:USAU": "黄金矿业",
  "US:SVRN": "航运", "US:MMATQ": "材料", "US:BSIN": "工业", "US:EQT": "电力/能源",
  "US:TSEM": "半导体", "US:COHR": "光模块", "US:KRC": "地产", "US:SEI": "电力/能源",
  "US:RIOT": "加密相关", "US:HUT": "加密相关", "US:CLSK": "加密相关", "US:BITF": "加密相关",
  "US:BTDR": "加密相关", "US:WYFI": "AI算力", "US:PSIX": "电力/能源", "US:LBRT": "能源/油服",
  "US:PUMP": "能源/油服", "US:BW": "工业",
};

export function sectorOf(symbol: string): string {
  return SECTORS[symbol] ?? "其他";
}
