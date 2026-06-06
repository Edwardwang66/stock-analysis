# 多市场股票数据看板平台 (Multi-Market Stock Data Dashboard)

> 一个聚合 **美股 / 港股 / A股 / 加密货币** 行情、基本面、新闻舆情与 AI 分析的数据看板平台。
> 技术栈:**Next.js (前端) + Python / FastAPI (后端 · 数据 · AI)**。

当前阶段:**P1 MVP 编码中** — 美股 + 加密的实时行情看板 + **非 LLM 技术分析**已可运行,静态前端可部署到 GitHub Pages。

新增 **富途式看板(Futu-style)** 模块:**资金流向 / 主力资金(估算)** 与 **筹码分布 / 获利比例 / 支撑位·压力位(估算)**,对标富途个股页的「资金流向 + 筹码分布」。
> ⚠️ 真实的「主力资金 / 特大·大·中·小单」基于 **Level-2 逐笔成交**;免费公开行情(Yahoo/Binance)不提供逐笔与买卖盘方向,本平台用 **分钟 K 线** 做透明代理估算(成交额分位数分档 + 收盘涨跌定方向,主力=特大+大),仅供趋势参考,**非真实逐笔、非投资建议**。要还原券商口径需接入富途 OpenAPI 等 LV2 源,见 [`docs/compliance.md`](docs/compliance.md)。

## 🚀 快速开始

```bash
# 前端(静态站点,零 key,浏览器直连公开 API)
cd frontend && npm install && npm run dev        # http://localhost:3000

# 后端(可选,更稳定 / 未来部署)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

**GitHub Pages 部署**:仓库 Settings → Pages → Source 选 **GitHub Actions**;推送后 `.github/workflows/deploy-pages.yml` 自动构建发布。站点地址:`https://edwardwang66.github.io/stock-analysis/`。

> 实测可用的数据 API 见 [`docs/working-apis.md`](docs/working-apis.md)。当前分析**全程非 LLM**(纯技术指标规则)。

## 📁 仓库结构

```
.
├── README.md                          # 本文件:项目总览
├── frontend/                          # Next.js 静态前端(GitHub Pages),非LLM分析(TS)
├── backend/                           # FastAPI 后端:行情适配器 + 非LLM分析(Python)
├── .github/workflows/deploy-pages.yml # 自动构建并发布前端到 GitHub Pages
├── research/
│   └── ai-agents-skills-market-scan.md  # 市场调研:股票/经济/市场相关 AI Agent 与 Skills 全景
└── docs/
    ├── architecture.md                # 平台技术架构设计
    ├── roadmap.md                     # 分阶段路线图与 MVP 范围
    ├── positioning.md                 # 差异化定位分析(vs 竞品)
    ├── cost-estimate.md               # 成本测算(数据源 + Claude API + 基建)
    ├── compliance.md                  # 合规 / 法律专项
    └── data-model-api.md              # 数据模型 / REST·WS API 契约
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
- 想了解**我们凭什么赢(竞品差异化)** → [`docs/positioning.md`](docs/positioning.md)
- 想了解**要花多少钱** → [`docs/cost-estimate.md`](docs/cost-estimate.md)
- 想了解**合规怎么办** → [`docs/compliance.md`](docs/compliance.md)
- 想了解**数据模型与 API 长什么样** → [`docs/data-model-api.md`](docs/data-model-api.md)
- 想了解**哪些数据 API 实测可用** → [`docs/working-apis.md`](docs/working-apis.md)
- 想跑**后端** → [`backend/README.md`](backend/README.md)

## ⚖️ 合规提示

- 多数免费行情源(如 yfinance/Yahoo)**禁止商业化重分发**,生产环境需采购正规授权数据。
- A股数据源(Tushare 等)有积分/权限与再分发限制。
- 平台所有 AI 输出均为**信息参考,非投资建议**(not financial advice)。
