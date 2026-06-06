# 多市场股票数据看板平台 (Multi-Market Stock Data Dashboard)

> 一个聚合 **美股 / 港股 / A股 / 加密货币** 行情、基本面、新闻舆情与 AI 分析的数据看板平台。
> 技术栈:**Next.js (前端) + Python / FastAPI (后端 · 数据 · AI)**。

当前阶段:**研究 + 架构设计**(尚未进入正式编码)。

## 📁 仓库结构

```
.
├── README.md                          # 本文件:项目总览
├── research/
│   └── ai-agents-skills-market-scan.md  # 市场调研:股票/经济/市场相关 AI Agent 与 Skills 全景
└── docs/
    ├── architecture.md                # 平台技术架构设计
    └── roadmap.md                     # 分阶段路线图与 MVP 范围
```

## 🎯 项目定位

**数据看板(Data Dashboard)**——以"看得清、查得到、问得懂"为核心:

1. **行情看板**:多市场实时/历史行情、K线、指标、热力图。
2. **基本面**:财务报表、估值、财报解读。
3. **新闻舆情**:聚合新闻 + AI 情绪分析。
4. **AI 助手**:自然语言查询、个股分析、研报生成(基于 Claude / 开源金融模型)。

## 🌍 覆盖市场

| 市场 | 代表数据源 | 备注 |
|------|-----------|------|
| 美股 US | yfinance / Finnhub / Polygon(现 Massive) / FMP / Alpha Vantage | 数据源最丰富 |
| 港股 HK | yfinance / Futu OpenAPI / AkShare | 部分源覆盖 |
| A股 CN | Tushare / AkShare / 东方财富 | 注意合规与重分发限制 |
| 加密 Crypto | Binance / CoinGecko / CoinMarketCap | 7×24 行情 |

## 📚 文档导航

- 想了解**市面上有哪些 AI 股票工具/Agent/Skills** → [`research/ai-agents-skills-market-scan.md`](research/ai-agents-skills-market-scan.md)
- 想了解**平台怎么搭** → [`docs/architecture.md`](docs/architecture.md)
- 想了解**先做什么、后做什么** → [`docs/roadmap.md`](docs/roadmap.md)

## ⚖️ 合规提示

- 多数免费行情源(如 yfinance/Yahoo)**禁止商业化重分发**,生产环境需采购正规授权数据。
- A股数据源(Tushare 等)有积分/权限与再分发限制。
- 平台所有 AI 输出均为**信息参考,非投资建议**(not financial advice)。
