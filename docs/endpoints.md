# 接入端点总览(Endpoints Reference)

> 本文件给**其他任务/Agent**速查:本平台**用到的所有端点** —— 分两层:
> 1. **上游免费数据源端点**(第三方,前端/后端直接调用)
> 2. **本平台对外 API 端点**(FastAPI 后端 `/api/v1/*`)
>
> 实测时间 2026-06。来源真实性、CORS/key、替代源详见 [`working-apis.md`](working-apis.md)。
> ⚠️ 上游均为**免费源,仅供演示/自用**,非投资建议;商用须换授权源(见 [`compliance.md`](compliance.md))。

---

## 一、上游免费数据源端点(第三方)

CORS 列:✅=浏览器可直连;❌=需经 CORS 代理或后端。Key 列:调用是否需密钥。

### 1. 暗号 Binance 公开镜像 — `https://data-api.binance.vision`
无 key、CORS ✅。**本仓库唯一能拿到真实逐笔+盘口的市场。**

| 方法 | 端点 | 返回 | 用在 |
|---|---|---|---|
| GET | `/api/v3/ticker/24hr?symbol={CODE}` | 24h 行情(最新价/涨跌/高低) | `lib/datasource.ts` `binanceQuote` / 后端 `providers/binance.py` |
| GET | `/api/v3/ticker/price?symbol={CODE}` | 最新价 | `lib/multiprice.ts`(跨所聚合) |
| GET | `/api/v3/klines?symbol={CODE}&interval={I}&limit={N}` | OHLCV 数组 | `lib/datasource.ts` `binanceOHLCV` / 后端 |
| GET | `/api/v3/aggTrades?symbol={CODE}&limit={N≤1000}` | **真实逐笔**(含 `m`=isBuyerMaker) | `lib/crypto.ts` `getCryptoFlow` → **真·主力资金** |
| GET | `/api/v3/depth?symbol={CODE}&limit={N}` | **真实盘口**(bids/asks) | `lib/crypto.ts` `getOrderBook` → **真·买卖盘** |

- `{CODE}` 例:`BTCUSDT`。`{I}` 例:`1m/5m/15m/30m/1h/1d/1w`。
- `aggTrades` 方向:`m=false`→主动买入(流入)、`m=true`→主动卖出(流出)。
- ⚠️ `api.binance.com` 本体 **451 地域封**,务必用 `data-api.binance.vision`。

### 2. 美/港/A 股 Yahoo Finance — `https://query1.finance.yahoo.com`
无 key、CORS ❌(浏览器需代理;后端直连)。

| 方法 | 端点 | 返回 | 用在 |
|---|---|---|---|
| GET | `/v8/finance/chart/{YCODE}?range={R}&interval={I}` | meta 报价 + timestamp/indicators(K线) | `lib/datasource.ts` `yahooChart` / 后端 `providers/yahoo.py` |

- `{YCODE}`:美股 `AAPL`;港股 `0700.HK`;A股 沪 `600519.SS` / 深 `000001.SZ`。
- `{R}`:`1d/5d/1mo/3mo/6mo/1y/2y/5y`;`{I}`:`1m/5m/15m/30m/60m/1d/1wk`(分钟线有跨度上限,见 datasource 内 `Y_INTRADAY_MAX`)。
- 同源**可用但未接**:`/v8/finance/spark`(批量迷你走势)、`/v1/finance/search?q=`(代码搜索)。
- ⚠️ `v7/finance/quote`、`v10/.../quoteSummary` 现 **401 需 crumb**,勿用。

### 3. 美股基本面 SEC EDGAR — `https://data.sec.gov` / `https://www.sec.gov`
无 key。官方权威财报。

| 方法 | 端点 | CORS | 返回 | 用在 |
|---|---|---|---|---|
| GET | `data.sec.gov/api/xbrl/companyconcept/CIK{10位}/us-gaap/{TAG}.json` | ✅ | 单一科目历年值 | `lib/fundamentals.ts` `concept` |
| GET | `www.sec.gov/files/company_tickers.json` | ❌ | ticker→CIK 全量映射 | `lib/fundamentals.ts`(经代理懒加载;常用 ticker 已内置种子表) |

- `{TAG}` 例:`Revenues` / `RevenueFromContractWithCustomerExcludingAssessedTax` / `NetIncomeLoss` / `Assets` / `Liabilities` / `StockholdersEquity` / `EarningsPerShareDiluted`(unit `USD/shares`)。
- 年度口径:流量科目 `frame=CY2024`,资产负债表时点 `frame=CY2024Q4I`。
- ⚠️ SEC 要求带描述性 `User-Agent`(含联系方式);仅美国注册公司有 XBRL。

### 4. 外汇 — Frankfurter(主)/ open.er-api(备)
无 key、CORS ✅。

| 方法 | 端点 | 返回 | 用在 |
|---|---|---|---|
| GET | `https://api.frankfurter.dev/v1/latest?base={B}&symbols={LIST}` | ECB 参考汇率 | `lib/forex.ts` `getForex`(主) |
| GET | `https://open.er-api.com/v6/latest/{B}` | 汇率(备用回退) | `lib/forex.ts`(Frankfurter 失败时) |

### 5. 暗号跨所校验(多源并发)
无 key、CORS ✅。`lib/multiprice.ts` `getCrossExchange`。

| 交易所 | 端点 | 取值 |
|---|---|---|
| OKX | `https://www.okx.com/api/v5/market/ticker?instId={BASE}-USDT` | `.data[0].last` |
| Coinbase | `https://api.coinbase.com/v2/prices/{BASE}-USD/spot` | `.data.amount` |
| CoinPaprika | `https://api.coinpaprika.com/v1/tickers/{ID}` | `.quotes.USD.price`(`{ID}` 如 `btc-bitcoin`) |
| Binance | `…/api/v3/ticker/price?symbol={CODE}`（见 §1） | `.price` |

### 6. CORS 代理(给无 CORS 的上游用,按序回退)
`lib/datasource.ts` `CORS_PROXIES` / `fetchViaProxy`。

| 优先级 | 代理 | 状态 |
|---|---|---|
| 1 | `https://api.allorigins.win/raw?url={URL编码}` | ✅ 最稳 |
| 2 | `https://api.codetabs.com/v1/proxy/?quest={URL}` | ✅ 备用 |
| 3 | `https://thingproxy.freeboard.io/fetch/{URL}` | 时好时坏 |
| 4 | `https://corsproxy.io/?url={URL编码}` | ❌ 已失效(落地页),仅兜底 |

---

## 二、本平台对外 API 端点(FastAPI 后端)

基址 `http://<host>/api/v1`。仅 `GET`,CORS 全开。前端设环境变量 `NEXT_PUBLIC_API_BASE` 即从浏览器直连切到走后端(更稳、免公共代理)。源码 `backend/app/main.py`。

| 方法 | 端点 | 参数 | 说明 |
|---|---|---|---|
| GET | `/api/v1/health` | — | 健康检查 `{ok:true}` |
| GET | `/api/v1/quotes` | `symbols`(逗号分隔,如 `US:AAPL,CRYPTO:BTCUSDT`) | 批量实时报价 |
| GET | `/api/v1/ohlcv` | `symbol`,`interval=1d`,`range=1y` | K线/历史 |
| GET | `/api/v1/analysis` | `symbol`,`interval`,`range` | 规则化技术分析(非 LLM):评分/信号/摘要 |
| GET | `/api/v1/moneyflow` | `symbol`,`interval=5m`,`range=1d` | 资金流向/主力资金(估算):特大/大/中/小档 + 主力净额 + 累计序列 |
| GET | `/api/v1/chips` | `symbol`,`interval=1d`,`range=1y` | 筹码分布(估算):获利比例/平均成本/支撑位/压力位 |
| GET | `/api/v1/chan` | `symbol`,`interval`,`range` | 简化版缠论:分型/笔/中枢/买卖点 |

- `symbol` 格式 `MARKET:CODE`,`MARKET ∈ US/HK/CN/CRYPTO`。
- 完整 OpenAPI schema 见 [`data-model-api.md`](data-model-api.md)。
- ⚠️ 后端目前仅 Yahoo + Binance 两个 provider;SEC/外汇/跨所聚合**只在前端**接入(后端 parity 待补)。

---

## 三、状态速览

- **已接入(8 源)**:Binance(行情/K线/逐笔/盘口)、Yahoo chart、SEC EDGAR、Frankfurter、open.er-api、OKX、Coinbase、CoinPaprika。
- **已验证可用·待接**:CoinGecko、Yahoo search/spark、Kraken、Finnhub(免费key)、AlphaVantage(免费key)。
- **仅后端可用**:Sina `hq.sinajs.cn`、Tencent `qt.gtimg.cn`(A股5档盘口;需 GBK/Referer)。
- **不可用**:东方财富 push2(本环境网络拦截,**境内部署可接 A 股真·资金流**)、corsproxy.io、Stooq、CoinCap。

> 交互版登记表 + 实时演示:前端 **`/sources`** 页(`frontend/app/sources/page.tsx`)。
