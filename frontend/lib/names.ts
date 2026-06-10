"use client";
// 双语股票名称库 + 语言切换(2026-06-10,Edward 要求)。
// - NAME_DB: symbol → [中文名, 英文名]。覆盖每市场代表票 + 云端自选池全量 + 指数/加密。
// - 解析顺序:NAME_DB[lang] → feed 提供的名称(多为 Yahoo 英文)→ 裸代码。
// - 不确定的标的宁缺毋错(fallback 显示代码),欢迎随时补充。
import { useEffect, useState } from "react";

export type Lang = "zh" | "en";
const LS_LANG = "ui:lang";
const EVT = "ui:langchange";

export function getLang(): Lang {
  if (typeof window === "undefined") return "zh";
  return (window.localStorage.getItem(LS_LANG) as Lang) || "zh";
}
export function setLang(l: Lang): void {
  window.localStorage.setItem(LS_LANG, l);
  window.dispatchEvent(new CustomEvent(EVT));
}
/** 响应式语言(SSR 安全:首帧 zh,挂载后取真值并监听切换)。 */
export function useLang(): Lang {
  const [l, setL] = useState<Lang>("zh");
  useEffect(() => {
    setL(getLang());
    const h = () => setL(getLang());
    window.addEventListener(EVT, h);
    return () => window.removeEventListener(EVT, h);
  }, []);
  return l;
}

type Pair = readonly [string, string]; // [zh, en]

export const NAME_DB: Record<string, Pair> = {
  // ── 美股:大盘代表 ──
  "US:AAPL": ["苹果", "Apple"], "US:MSFT": ["微软", "Microsoft"], "US:NVDA": ["英伟达", "NVIDIA"],
  "US:GOOGL": ["谷歌A", "Alphabet A"], "US:GOOG": ["谷歌C", "Alphabet C"], "US:AMZN": ["亚马逊", "Amazon"],
  "US:META": ["Meta", "Meta"], "US:TSLA": ["特斯拉", "Tesla"], "US:AVGO": ["博通", "Broadcom"],
  "US:BRK-B": ["伯克希尔B", "Berkshire B"], "US:JPM": ["摩根大通", "JPMorgan"], "US:V": ["Visa", "Visa"],
  "US:MA": ["万事达", "Mastercard"], "US:WMT": ["沃尔玛", "Walmart"], "US:LLY": ["礼来", "Eli Lilly"],
  "US:UNH": ["联合健康", "UnitedHealth"], "US:XOM": ["埃克森美孚", "ExxonMobil"], "US:CVX": ["雪佛龙", "Chevron"],
  "US:JNJ": ["强生", "J&J"], "US:PG": ["宝洁", "P&G"], "US:KO": ["可口可乐", "Coca-Cola"],
  "US:PEP": ["百事", "PepsiCo"], "US:ORCL": ["甲骨文", "Oracle"], "US:CRM": ["赛富时", "Salesforce"],
  "US:ADBE": ["Adobe", "Adobe"], "US:NFLX": ["奈飞", "Netflix"], "US:AMD": ["AMD", "AMD"],
  "US:INTC": ["英特尔", "Intel"], "US:MU": ["美光", "Micron"], "US:QCOM": ["高通", "Qualcomm"],
  "US:TXN": ["德州仪器", "Texas Instruments"], "US:CSCO": ["思科", "Cisco"], "US:IBM": ["IBM", "IBM"],
  "US:GE": ["通用电气", "GE Aerospace"], "US:CAT": ["卡特彼勒", "Caterpillar"], "US:BA": ["波音", "Boeing"],
  "US:GS": ["高盛", "Goldman Sachs"], "US:MS": ["摩根士丹利", "Morgan Stanley"], "US:BAC": ["美国银行", "BofA"],
  "US:WFC": ["富国银行", "Wells Fargo"], "US:C": ["花旗", "Citigroup"], "US:DIS": ["迪士尼", "Disney"],
  "US:NKE": ["耐克", "Nike"], "US:MCD": ["麦当劳", "McDonald's"], "US:SBUX": ["星巴克", "Starbucks"],
  "US:T": ["AT&T", "AT&T"], "US:VZ": ["威瑞森", "Verizon"], "US:PFE": ["辉瑞", "Pfizer"],
  "US:MRK": ["默沙东", "Merck"], "US:ABBV": ["艾伯维", "AbbVie"], "US:TMO": ["赛默飞", "Thermo Fisher"],
  "US:COST": ["开市客", "Costco"], "US:HD": ["家得宝", "Home Depot"],
  // ── 美股:自选池/SA LP/题材 ──
  "US:PLTR": ["Palantir", "Palantir"], "US:APP": ["AppLovin", "AppLovin"], "US:NOW": ["ServiceNow", "ServiceNow"],
  "US:SMCI": ["超微电脑", "Supermicro"], "US:COIN": ["Coinbase", "Coinbase"], "US:MSTR": ["Strategy", "Strategy"],
  "US:CRCL": ["Circle", "Circle"], "US:TEM": ["Tempus AI", "Tempus AI"], "US:ILMN": ["因美纳", "Illumina"],
  "US:RR": ["Richtech机器人", "Richtech Robotics"], "US:QUBT": ["量子计算公司", "Quantum Computing"],
  "US:RGTI": ["Rigetti", "Rigetti"], "US:IONQ": ["IonQ", "IonQ"], "US:RKLB": ["火箭实验室", "Rocket Lab"],
  "US:LILMF": ["Lilium", "Lilium"], "US:PDYN": ["Palladyne AI", "Palladyne AI"],
  "US:EVTL": ["Vertical航空", "Vertical Aerospace"], "US:RCAT": ["Red Cat", "Red Cat"],
  "US:RVSN": ["Rail Vision", "Rail Vision"], "US:HOLOW": ["微云全息权证", "MicroCloud Wt"],
  "US:EBS": ["Emergent生物", "Emergent BioSolutions"], "US:CTKB": ["Cytek生物", "Cytek"],
  "US:MVST": ["微宏动力", "Microvast"], "US:TSLL": ["特斯拉2x多", "TSLL 2x Tesla"],
  "US:DJD": ["道指红利ETF", "DJD Dow Div ETF"], "US:QQQ": ["纳指100ETF", "QQQ Nasdaq100"],
  "US:SQQQ": ["纳指3x空", "SQQQ 3x Short"], "US:SPY": ["标普500ETF", "SPY S&P500"],
  "US:PDD": ["拼多多", "PDD"], "US:BABA": ["阿里巴巴", "Alibaba"], "US:BILI": ["哔哩哔哩", "Bilibili"],
  "US:NIO": ["蔚来", "NIO"], "US:FUTU": ["富途控股", "Futu"], "US:ROKU": ["Roku", "Roku"],
  "US:UBER": ["优步", "Uber"], "US:OSCR": ["Oscar健康", "Oscar Health"], "US:CI": ["信诺", "Cigna"],
  "US:HUM": ["哈门那", "Humana"], "US:AZN": ["阿斯利康ADR", "AstraZeneca ADR"],
  "US:BE": ["Bloom能源", "Bloom Energy"], "US:CRWV": ["CoreWeave", "CoreWeave"],
  "US:LITE": ["Lumentum", "Lumentum"], "US:CORZ": ["Core Scientific", "Core Scientific"],
  "US:IREN": ["IREN", "IREN"], "US:APLD": ["Applied Digital", "Applied Digital"],
  "US:SNDK": ["闪迪", "Sandisk"], "US:INFY": ["印孚瑟斯", "Infosys"],
  "US:MARPS": ["Marine石油信托", "Marine Petroleum Tr"], "US:IMPP": ["Imperial石油", "Imperial Petroleum"],
  "US:MMATQ": ["Meta Materials", "Meta Materials"], "US:NESR": ["NESR能源服务", "NESR"],
  "US:USAU": ["美国黄金", "U.S. Gold"], "US:APCX": ["AppTech支付", "AppTech"],
  // ── 美股:screener 常客(半导体设备/硬件/金融/医疗等) ──
  "US:ASML": ["阿斯麦", "ASML"], "US:KLAC": ["科磊", "KLA"], "US:AMAT": ["应用材料", "Applied Materials"],
  "US:LRCX": ["拉姆研究", "Lam Research"], "US:WDC": ["西部数据", "Western Digital"],
  "US:STX": ["希捷", "Seagate"], "US:MRVL": ["迈威尔", "Marvell"], "US:TER": ["泰瑞达", "Teradyne"],
  "US:ARM": ["Arm", "Arm"], "US:COHR": ["高意", "Coherent"], "US:CIEN": ["Ciena", "Ciena"],
  "US:FDX": ["联邦快递", "FedEx"], "US:LIN": ["林德", "Linde"], "US:GM": ["通用汽车", "GM"],
  "US:CSX": ["CSX铁路", "CSX"], "US:PLD": ["普洛斯", "Prologis"], "US:DELL": ["戴尔", "Dell"],
  "US:HPE": ["慧与", "HPE"], "US:NTAP": ["NetApp", "NetApp"], "US:BIIB": ["渤健", "Biogen"],
  "US:EW": ["爱德华兹", "Edwards Life"], "US:MET": ["大都会人寿", "MetLife"], "US:HLT": ["希尔顿", "Hilton"],
  "US:MAR": ["万豪", "Marriott"], "US:MGM": ["美高梅", "MGM"], "US:DECK": ["Deckers", "Deckers"],
  "US:EQR": ["EQR公寓", "Equity Residential"], "US:ESS": ["Essex地产", "Essex"],
  "US:EXR": ["Extra Space仓储", "Extra Space"], "US:GL": ["Globe Life", "Globe Life"],
  "US:JCI": ["江森自控", "Johnson Controls"], "US:STT": ["道富", "State Street"],
  "US:BNY": ["纽约梅隆", "BNY"], "US:CHRW": ["罗宾逊物流", "C.H. Robinson"],
  // ── A股:代表50 ──
  "CN:600519": ["贵州茅台", "Kweichow Moutai"], "CN:000858": ["五粮液", "Wuliangye"],
  "CN:601318": ["中国平安", "Ping An"], "CN:600036": ["招商银行", "CM Bank"],
  "CN:601398": ["工商银行", "ICBC"], "CN:601939": ["建设银行", "CCB"], "CN:601288": ["农业银行", "ABC"],
  "CN:600276": ["恒瑞医药", "Hengrui Pharma"], "CN:300750": ["宁德时代", "CATL"],
  "CN:002594": ["比亚迪", "BYD"], "CN:601012": ["隆基绿能", "LONGi"], "CN:600900": ["长江电力", "Yangtze Power"],
  "CN:601888": ["中国中免", "China Duty Free"], "CN:600309": ["万华化学", "Wanhua Chem"],
  "CN:600887": ["伊利股份", "Yili"], "CN:000333": ["美的集团", "Midea"], "CN:000651": ["格力电器", "Gree"],
  "CN:002475": ["立讯精密", "Luxshare"], "CN:300059": ["东方财富", "East Money"],
  "CN:600030": ["中信证券", "CITIC Sec"], "CN:601628": ["中国人寿", "China Life"],
  "CN:601088": ["中国神华", "Shenhua"], "CN:600028": ["中国石化", "Sinopec"],
  "CN:601857": ["中国石油", "PetroChina"], "CN:601668": ["中国建筑", "CSCEC"],
  "CN:600048": ["保利发展", "Poly Dev"], "CN:000002": ["万科A", "Vanke"],
  "CN:600585": ["海螺水泥", "Conch Cement"], "CN:002415": ["海康威视", "Hikvision"],
  "CN:002230": ["科大讯飞", "iFlytek"], "CN:688981": ["中芯国际", "SMIC"],
  "CN:688041": ["海光信息", "Hygon"], "CN:603501": ["韦尔股份", "Will Semi"],
  "CN:603986": ["兆易创新", "GigaDevice"], "CN:600941": ["中国移动", "China Mobile"],
  "CN:601728": ["中国电信", "China Telecom"], "CN:688111": ["金山办公", "Kingsoft Office"],
  "CN:603259": ["药明康德", "WuXi AppTec"], "CN:300760": ["迈瑞医疗", "Mindray"],
  "CN:300015": ["爱尔眼科", "Aier Eye"], "CN:000725": ["京东方A", "BOE"],
  "CN:601166": ["兴业银行", "Industrial Bank"], "CN:600000": ["浦发银行", "SPDB"],
  "CN:601658": ["邮储银行", "PSBC"], "CN:603288": ["海天味业", "Haitian"],
  "CN:600690": ["海尔智家", "Haier"], "CN:000568": ["泸州老窖", "Luzhou Laojiao"],
  "CN:600809": ["山西汾酒", "Fenjiu"], "CN:000001": ["平安银行", "Ping An Bank"],
  "CN:688795": ["688795", "688795"],
  // ── 港股:代表50 ──
  "HK:0700": ["腾讯控股", "Tencent"], "HK:9988": ["阿里巴巴-W", "Alibaba-W"],
  "HK:3690": ["美团-W", "Meituan-W"], "HK:1810": ["小米集团-W", "Xiaomi-W"],
  "HK:9618": ["京东集团-SW", "JD-SW"], "HK:9999": ["网易-S", "NetEase-S"],
  "HK:9888": ["百度集团-SW", "Baidu-SW"], "HK:1024": ["快手-W", "Kuaishou-W"],
  "HK:2015": ["理想汽车-W", "Li Auto-W"], "HK:9868": ["小鹏汽车-W", "XPeng-W"],
  "HK:1211": ["比亚迪股份", "BYD Co"], "HK:0175": ["吉利汽车", "Geely"],
  "HK:2333": ["长城汽车", "Great Wall"], "HK:0941": ["中国移动", "China Mobile"],
  "HK:0939": ["建设银行", "CCB"], "HK:1398": ["工商银行", "ICBC"], "HK:3988": ["中国银行", "BOC"],
  "HK:0005": ["汇丰控股", "HSBC"], "HK:1299": ["友邦保险", "AIA"], "HK:2318": ["中国平安", "Ping An"],
  "HK:2628": ["中国人寿", "China Life"], "HK:0388": ["香港交易所", "HKEX"],
  "HK:0011": ["恒生银行", "Hang Seng Bank"], "HK:2382": ["舜宇光学", "Sunny Optical"],
  "HK:0981": ["中芯国际", "SMIC"], "HK:1347": ["华虹半导体", "Hua Hong"],
  "HK:0992": ["联想集团", "Lenovo"], "HK:0285": ["比亚迪电子", "BYD Electronic"],
  "HK:2018": ["瑞声科技", "AAC Tech"], "HK:0027": ["银河娱乐", "Galaxy Ent"],
  "HK:1928": ["金沙中国", "Sands China"], "HK:0066": ["港铁公司", "MTR"],
  "HK:0001": ["长和", "CK Hutchison"], "HK:0016": ["新鸿基地产", "SHK Properties"],
  "HK:1109": ["华润置地", "CR Land"], "HK:0960": ["龙湖集团", "Longfor"],
  "HK:0883": ["中国海洋石油", "CNOOC"], "HK:0857": ["中国石油股份", "PetroChina H"],
  "HK:0386": ["中国石化股份", "Sinopec H"], "HK:1088": ["中国神华H", "Shenhua H"],
  "HK:1093": ["石药集团", "CSPC Pharma"], "HK:1177": ["中国生物制药", "Sino Biopharm"],
  "HK:2269": ["药明生物", "WuXi Bio"], "HK:2359": ["药明康德H", "WuXi AppTec H"],
  "HK:6160": ["百济神州", "BeiGene"], "HK:1801": ["信达生物", "Innovent"],
  "HK:0291": ["华润啤酒", "CR Beer"], "HK:2020": ["安踏体育", "ANTA"],
  "HK:2331": ["李宁", "Li Ning"], "HK:6862": ["海底捞", "Haidilao"],
  "HK:7226": ["南方恒科2x多", "CSOP HSTECH 2x"],
  // ── 加密:代表25 ──
  "CRYPTO:BTCUSDT": ["比特币", "Bitcoin"], "CRYPTO:ETHUSDT": ["以太坊", "Ethereum"],
  "CRYPTO:SOLUSDT": ["Solana", "Solana"], "CRYPTO:BNBUSDT": ["BNB", "BNB"],
  "CRYPTO:XRPUSDT": ["瑞波", "XRP"], "CRYPTO:DOGEUSDT": ["狗狗币", "Dogecoin"],
  "CRYPTO:ADAUSDT": ["Cardano", "Cardano"], "CRYPTO:AVAXUSDT": ["Avalanche", "Avalanche"],
  "CRYPTO:LINKUSDT": ["Chainlink", "Chainlink"], "CRYPTO:DOTUSDT": ["波卡", "Polkadot"],
  "CRYPTO:LTCUSDT": ["莱特币", "Litecoin"], "CRYPTO:BCHUSDT": ["比特币现金", "Bitcoin Cash"],
  "CRYPTO:UNIUSDT": ["Uniswap", "Uniswap"], "CRYPTO:ATOMUSDT": ["Cosmos", "Cosmos"],
  "CRYPTO:NEARUSDT": ["NEAR", "NEAR"], "CRYPTO:APTUSDT": ["Aptos", "Aptos"],
  "CRYPTO:ARBUSDT": ["Arbitrum", "Arbitrum"], "CRYPTO:OPUSDT": ["Optimism", "Optimism"],
  "CRYPTO:FILUSDT": ["Filecoin", "Filecoin"], "CRYPTO:TRXUSDT": ["波场", "TRON"],
  "CRYPTO:ETCUSDT": ["以太经典", "Ethereum Classic"], "CRYPTO:XLMUSDT": ["恒星币", "Stellar"],
  "CRYPTO:ICPUSDT": ["ICP", "ICP"], "CRYPTO:SUIUSDT": ["Sui", "Sui"], "CRYPTO:PEPEUSDT": ["PEPE", "PEPE"],
  // ── 日股:代表20 ──
  "JP:7203": ["丰田汽车", "Toyota"], "JP:6758": ["索尼集团", "Sony"], "JP:9984": ["软银集团", "SoftBank G"],
  "JP:8306": ["三菱UFJ", "MUFG"], "JP:6861": ["基恩士", "Keyence"], "JP:9983": ["迅销/优衣库", "Fast Retailing"],
  "JP:8035": ["东京电子", "Tokyo Electron"], "JP:6954": ["发那科", "Fanuc"], "JP:6501": ["日立", "Hitachi"],
  "JP:7974": ["任天堂", "Nintendo"], "JP:4063": ["信越化学", "Shin-Etsu"], "JP:6098": ["Recruit", "Recruit"],
  "JP:8316": ["三井住友FG", "SMFG"], "JP:8411": ["瑞穗FG", "Mizuho"], "JP:7267": ["本田", "Honda"],
  "JP:7201": ["日产", "Nissan"], "JP:6902": ["电装", "Denso"], "JP:4502": ["武田药品", "Takeda"],
  "JP:6273": ["SMC", "SMC"], "JP:6920": ["Lasertec", "Lasertec"],
  // ── 韩股:代表15 ──
  "KR:005930": ["三星电子", "Samsung Elec"], "KR:000660": ["SK海力士", "SK hynix"],
  "KR:373220": ["LG新能源", "LG Energy"], "KR:207940": ["三星生物", "Samsung Bio"],
  "KR:005380": ["现代汽车", "Hyundai Motor"], "KR:000270": ["起亚", "Kia"],
  "KR:035420": ["NAVER", "NAVER"], "KR:035720": ["Kakao", "Kakao"],
  "KR:051910": ["LG化学", "LG Chem"], "KR:006400": ["三星SDI", "Samsung SDI"],
  "KR:005490": ["POSCO控股", "POSCO"], "KR:105560": ["KB金融", "KB Financial"],
  "KR:055550": ["新韩金融", "Shinhan"], "KR:012330": ["现代摩比斯", "Hyundai Mobis"],
  "KR:066570": ["LG电子", "LG Elec"],
  // ── 德股:代表15 ──
  "DE:SAP": ["思爱普", "SAP"], "DE:SIE": ["西门子", "Siemens"], "DE:VOW3": ["大众汽车", "Volkswagen"],
  "DE:BMW": ["宝马", "BMW"], "DE:MBG": ["梅赛德斯-奔驰", "Mercedes-Benz"], "DE:ALV": ["安联", "Allianz"],
  "DE:DTE": ["德国电信", "Deutsche Telekom"], "DE:BAS": ["巴斯夫", "BASF"], "DE:BAYN": ["拜耳", "Bayer"],
  "DE:ADS": ["阿迪达斯", "adidas"], "DE:AIR": ["空客", "Airbus"], "DE:IFX": ["英飞凌", "Infineon"],
  "DE:MUV2": ["慕尼黑再保险", "Munich Re"], "DE:RWE": ["莱茵集团", "RWE"], "DE:DBK": ["德意志银行", "Deutsche Bank"],
  // ── 英股:代表15 ──
  "GB:SHEL": ["壳牌", "Shell"], "GB:HSBA": ["汇丰控股", "HSBC"], "GB:AZN": ["阿斯利康", "AstraZeneca"],
  "GB:ULVR": ["联合利华", "Unilever"], "GB:RR": ["罗尔斯罗伊斯", "Rolls-Royce"], "GB:BP": ["英国石油", "BP"],
  "GB:GSK": ["葛兰素史克", "GSK"], "GB:RIO": ["力拓", "Rio Tinto"], "GB:GLEN": ["嘉能可", "Glencore"],
  "GB:BARC": ["巴克莱", "Barclays"], "GB:LLOY": ["劳埃德银行", "Lloyds"], "GB:VOD": ["沃达丰", "Vodafone"],
  "GB:BT-A": ["英国电信", "BT Group"], "GB:TSCO": ["乐购", "Tesco"], "GB:REL": ["RELX", "RELX"],
  // ── 指数 ──
  "IDX:^GSPC": ["标普500", "S&P 500"], "IDX:^IXIC": ["纳斯达克", "NASDAQ"], "IDX:^DJI": ["道琼斯", "Dow Jones"],
  "IDX:000001.SS": ["上证指数", "SSE Composite"], "IDX:^HSI": ["恒生指数", "Hang Seng"],
  "IDX:^N225": ["日经225", "Nikkei 225"], "IDX:^KS11": ["韩国KOSPI", "KOSPI"],
  "IDX:^GDAXI": ["德国DAX", "DAX"], "IDX:^FTSE": ["富时100", "FTSE 100"],
};

/** 双语名称解析:库 → feed 名称兜底 → 裸代码。 */
export function displayName(symbol: string, lang: Lang, fallback?: string | null): string {
  const hit = NAME_DB[symbol];
  if (hit) return lang === "en" ? hit[1] : hit[0];
  if (fallback) return fallback;
  return symbol.split(":")[1] || symbol;
}

// 市场标签双语
const MKT_EN: Record<string, string> = {
  ALL: "All", US: "US", CN: "A-shares", HK: "HK", CRYPTO: "Crypto",
  JP: "Japan", KR: "Korea", DE: "Germany", GB: "UK", IDX: "Index",
};
const MKT_ZH: Record<string, string> = {
  ALL: "全部", US: "美股", CN: "A股", HK: "港股", CRYPTO: "加密",
  JP: "日股", KR: "韩股", DE: "德股", GB: "英股", IDX: "指数",
};
export function marketLabel(market: string, lang: Lang): string {
  return (lang === "en" ? MKT_EN : MKT_ZH)[market] || market;
}

// 行业标签双语(覆盖 sectors.ts 自定义词 + GICS 11)
const SECTOR_EN: Record<string, string> = {
  "ETF/指数": "ETF/Index", "半导体": "Semis", "存储": "Memory/Storage", "AI算力": "AI Compute",
  "网络设备": "Networking", "光模块": "Optics", "光学/全息": "Holography", "电力/能源": "Power/Energy",
  "电池/储能": "Battery/ESS", "软件": "Software", "软件/AI": "Software/AI", "软件/广告": "AdTech",
  "互联网": "Internet", "软件外包": "IT Services", "加密相关": "Crypto-linked", "量子计算": "Quantum",
  "机器人": "Robotics", "航天": "Space", "航空制造": "Aerospace", "eVTOL": "eVTOL",
  "无人机": "Drones", "铁路AI": "Rail AI", "汽车/出行": "Auto/Mobility", "医疗": "Healthcare",
  "医疗保险": "Health Insurance", "生物科技": "Biotech", "消费": "Consumer", "白酒": "Baijiu",
  "金融": "Financials", "能源": "Energy", "其他": "Other",
  "信息技术": "Info Tech", "通信服务": "Comm Services", "可选消费": "Consumer Disc",
  "日常消费": "Consumer Staples", "医疗保健": "Health Care", "工业": "Industrials",
  "材料": "Materials", "公用事业": "Utilities", "房地产": "Real Estate",
};
export function sectorLabel(zhName: string, lang: Lang): string {
  if (lang !== "en") return zhName;
  return SECTOR_EN[zhName] || zhName;
}
