# 实测可用的数据 API(2026-06 验证)

> 实测自本仓库环境;每条标注**是否能在浏览器(静态站点)直接调用**(CORS)。
> ⚠️ 这些为免费源,**仅供演示/自用**;商用对外须换授权源(见 [`compliance.md`](compliance.md))。

## ✅ 可用

| 用途 | API | 端点示例 | 浏览器直连 | 备注 |
|------|-----|---------|:---:|------|
| 暗号 行情/24h | **Binance 公开镜像** | `https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT` | ✅ | **无地域限制、无 key**;比 `api.binance.com` 更适合(后者 451 地域封) |
| 暗号 K线 | Binance 镜像 | `.../api/v3/klines?symbol=BTCUSDT&interval=1d&limit=365` | ✅ | OHLCV 数组 |
| 暗号 价格/市值/历史 | **CoinGecko** | `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd` | ✅ | CORS OK;免费限频 ~10-30/分;需署名 |
| 美股/港/A 行情+K线 | **Yahoo Finance chart** | `https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1y&interval=1d` | ❌(需代理) | 服务端直连 OK;含 `meta.regularMarketPrice` + `timestamp/indicators` |
| 美股(浏览器) | Yahoo + **corsproxy.io** | `https://corsproxy.io/?url=<编码后的 Yahoo URL>` | ✅ | 静态站点用此叩 Yahoo;公共代理偶发不稳 |

**港股/A股**:Yahoo 同一端点支持后缀 `0700.HK` / `600519.SS` / `000001.SZ`(本仓库 `yahoo.py` 已实现映射,P2 接入)。

## ❌ 当前不可用 / 不推荐

| API | 状态 |
|-----|------|
| `api.binance.com`(本体) | **451 地域封锁**(用 `data-api.binance.vision` 替代) |
| **Stooq** CSV | 已加 JS 反爬挑战页,程序化不可用 |
| **CoinCap** | 请求失败(疑似改为需 key) |
| allorigins 代理 + Yahoo | 500(改用 corsproxy.io) |

## 本项目如何使用

- **静态站点(GitHub Pages)**:`frontend/lib/datasource.ts` 默认浏览器直连——暗号走 Binance 镜像、美股走 Yahoo+corsproxy,**零 key**。
- **后端(FastAPI)**:`backend/app/providers/` 服务端直连 Yahoo(免代理)+ Binance 镜像;前端设 `NEXT_PUBLIC_API_BASE` 即切换到后端(更稳、避开公共代理)。

## 升级路径(更稳/可商用)

| 需求 | 建议 |
|------|------|
| 美股更稳/实时 | **Finnhub**(免费 60/分,**浏览器 CORS OK**,需免费 key)或自建后端代理 Yahoo |
| 商用可重分发 | Finnhub Startup/Enterprise、Polygon(Massive)、FMP(授权协议)、financialdatasets Pro |
| A股 | AkShare(原型)/ Tushare(积分) |

> 价格/限额见 [`../research/ai-agents-skills-market-scan.md`](../research/ai-agents-skills-market-scan.md) §5。
