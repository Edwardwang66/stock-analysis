# 实测可用的数据 API(2026-06 验证)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [current architecture](../../current-architecture.md); historical prose below is preserved, and moved local link targets are redirected to their current repository locations.


> 实测自本仓库环境;标注**是否能在浏览器(静态站点)直接调用**(CORS)、是否需 key。
> 站内有交互版:前端 **`/sources`** 页(`frontend/app/sources/page.tsx`)带实时演示 + 登记表。
> ⚠️ 均为免费源,**仅供演示/自用**;商用对外须换授权源(见 [`compliance.md`](../../compliance.md))。

## ✅ 已接入(浏览器直连,零/免费 key)

| 用途 | API | 端点示例 | CORS | Key | 备注 |
|------|-----|---------|:---:|:---:|------|
| 暗号 行情/K线 | **Binance 镜像** | `data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d` | ✅ | 无 | 无地域封;`api.binance.com` 本体 451 |
| 暗号 **真·逐笔** | Binance | `/api/v3/aggTrades?symbol=BTCUSDT&limit=1000` | ✅ | 无 | 带 `isBuyerMaker` → **真·主力资金/主动买卖** |
| 暗号 **真·盘口** | Binance | `/api/v3/depth?symbol=BTCUSDT&limit=20` | ✅ | 无 | 委买/委卖 → **真·买卖盘比** |
| 美/港/A股 行情+K线(含分钟) | **Yahoo chart** | `query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1y&interval=1d` | ❌ | 无 | 无 CORS,经代理;支持 `0700.HK`/`600519.SS` |
| 美股 **基本面财报** | **SEC EDGAR XBRL** | `data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json` | ✅ | 无 | 官方;营收/净利/资产/EPS,含历年同比 |
| 外汇 | **Frankfurter(ECB)** | `api.frankfurter.dev/v1/latest?base=USD&symbols=CNY,EUR` | ✅ | 无 | 央行参考汇率;回退 `open.er-api.com` |
| 暗号 跨所校验 | **OKX / Coinbase / CoinPaprika** | `okx.com/api/v5/market/ticker?instId=BTC-USDT` 等 | ✅ | 无 | 多源并发,交叉验价 |

## 🟡 已验证可用 · 待接入

| 用途 | API | CORS | Key | 备注 |
|------|-----|:---:|:---:|------|
| 暗号 价格/市值/全局/趋势 | **CoinGecko** | ✅ | 无 | 限频 ~10-30/分;`/global`、`/coins/markets`、`/trending` |
| 代码搜索/联想 | **Yahoo search** | ❌ | 无 | `query2.finance.yahoo.com/v1/finance/search?q=apple`,经代理 |
| 多标的迷你走势 | **Yahoo spark** | ❌ | 无 | 批量 sparkline,经代理 |
| 暗号 OHLC/行情 | **Kraken** | ❌ | 无 | 服务端可用;浏览器需代理 |
| 美股 实时/基本面/新闻 | **Finnhub** | ✅ | 免费key | 免费 60/分,CORS OK |
| 美股/外汇/基本面 | **AlphaVantage** | ✅ | 免费key | 免费 25/日;`demo` key 仅限 IBM 等 |

## 🔻 仅服务端可用(浏览器受限)

| 用途 | API | 备注 |
|------|-----|------|
| A/港/美股 实时 | **Sina** `hq.sinajs.cn/list=sh600519` | 需 `Referer` + GBK 解码,仅后端;✅本环境可达 |
| A股 实时 + 5档盘口 | **Tencent** `qt.gtimg.cn/q=sh600519` | 含买卖5档,仅后端;GBK;✅本环境可达 |

## ❌ 当前不可用

| API | 状态 |
|-----|------|
| **东方财富** `push2.eastmoney.com`(含真·资金流) | 本环境 502 / 网络策略拦截;**境内部署可用**,届时可接 A 股真·主力资金 |
| **corsproxy.io** | 已改为落地页,代理失效 → 改用 `allorigins`/`codetabs` |
| **Stooq** CSV | JS 反爬挑战页 |
| **CoinCap** | 改为反爬/需 key |
| Yahoo `v7/quote`、`quoteSummary` | 401 需 crumb(改用 `chart`/`spark`) |

## 本项目如何使用

- **静态站点(GitHub Pages)**:`frontend/lib/datasource.ts` 默认浏览器直连;无 CORS 的源(Yahoo/SEC映射)经 `fetchViaProxy` 多代理回退(**allorigins 优先**)。
- 关键模块:`lib/crypto.ts`(暗号真逐笔+盘口)、`lib/moneyflow.ts`(主力资金)、`lib/chips.ts`(筹码)、`lib/fundamentals.ts`(SEC)、`lib/forex.ts`、`lib/multiprice.ts`(跨所聚合)、`lib/sources.ts`(登记表)。
- **后端(FastAPI)**:`backend/app/providers/` 服务端直连(免代理);前端设 `NEXT_PUBLIC_API_BASE` 即切换。

## 升级路径(更稳 / 可商用)

| 需求 | 建议 |
|------|------|
| 美股更稳/实时 | Finnhub(免费 60/分,CORS OK)或自建后端代理 Yahoo |
| A股真·主力资金 | 境内部署接 **东方财富 push2 fflow** / Tushare;或券商 LV2 |
| 真·主力逐笔(股票) | 富途 OpenAPI / 券商 Level-2(付费) |
| 商用可重分发 | Finnhub、Polygon、FMP、financialdatasets(授权协议) |
