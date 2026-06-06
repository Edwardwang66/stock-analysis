# 多市场股票数据看板平台 (Multi-Market Stock Data Dashboard)

> 一个聚合 **美股 / 港股 / A股 / 加密货币** 行情、基本面、新闻舆情与 AI 分析的数据看板平台。
> 技术栈:**Next.js (前端) + Python / FastAPI (后端 · 数据 · AI)**。

当前阶段:**P1 MVP 编码中** — 美股 + 加密的实时行情看板 + **非 LLM 技术分析**已可运行,静态前端可部署到 GitHub Pages。

新增 **富途式看板(Futu-style)** 模块:**资金流向 / 主力资金**、**筹码分布 / 获利比例 / 支撑位·压力位**、**买卖盘口**、**基本面财报**,对标富途个股页。

---

## 🛰️ 自我优化的做多做空情报闭环(新)

按设计文档《美股中频混合量化系统 v1.0》落成的**持续运转回路**:做多做空引擎(流 B 残差统计套利)+
每小时/每日 routine + LLM 假设工厂 + OpenClaw 外部 agent + 情报看板。总览见
[`docs/self-improving-alpha-loop.md`](docs/self-improving-alpha-loop.md)。

- **优化后的做多做空逻辑** [`backtest/statarb.py`](backtest/statarb.py):残差→OU s-score→滞回→**协整断裂熔断**→
  Garleanu-Pedersen aim 组合(控换手)→分层限额+**容量地板**→**净·扣成本** + Deflated Sharpe。
  诚实结论:免费数据上净 alpha ≈0/为负 —— 实证「真 alpha 在容量受限冷门层」。见 [`backtest/README_statarb.md`](backtest/README_statarb.md)。
- **routine(不断 post 报告)** [`routines/daily-alpha-routine.md`](routines/daily-alpha-routine.md) +
  [`scripts/run_routine.py`](scripts/run_routine.py) + 定时工作流 `alpha-routine.yml`。
- **静态网页不断接受** [`frontend/lib/feed.ts`](frontend/lib/feed.ts):GitHub raw 实时 + 捆绑快照兜底,**无需重建 Pages**。
- **OpenClaw 完整方案** [`docs/openclaw-integration.md`](docs/openclaw-integration.md):agent 名册 + 三投递通道 +
  HMAC 签名 + CI 安全闸门(`scripts/validate_feed.py`)。
- **情报看板 `/intel`**:何时获得多少信息 / 怎么帮助到系统 / 仓库是否最新(站内 🛰️ 情报看板入口)。

**主力资金的数据真实性(重要)**:
- **暗号**:接入 Binance **真实逐笔(aggTrades)+ 真实盘口(depth)**,按成交额分档 + 主动买卖方向算 → **真·主力资金 / 真·买卖盘**(免费源里少数能拿到逐笔的市场)。
- **股票**:免费行情无逐笔/盘口,用 **分钟 K 线** 做透明代理估算(成交额分位数分档 + 收盘涨跌定方向,主力=特大+大),UI 标注「K线估算」,仅供趋势参考。要还原券商口径需券商 LV2 / 富途 OpenAPI,A 股可在境内部署接东方财富资金流。

**新接入的免费数据源(2026-06 实测,零/免费 key)**:Binance(逐笔+盘口)、SEC EDGAR(美股官方财报)、Frankfurter/ECB(外汇)、OKX/Coinbase/CoinPaprika(跨所校验)、open.er-api。站内 **`/sources`** 页有实时演示 + 完整登记表(详见 [`docs/working-apis.md`](docs/working-apis.md))。
> ⚠️ 均为免费源,仅供演示/自用,**非投资建议**;商用对外须换授权源(见 [`docs/compliance.md`](docs/compliance.md))。
> 修复:公共代理 `corsproxy.io` 已失效,改为 `allorigins` 优先(影响全部美/港/A 股浏览器直连)。

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
├── frontend/                          # Next.js 静态前端(GitHub Pages):看板 + /intel 情报看板
├── backend/                           # FastAPI 后端:行情适配器 + 非LLM分析(Python)
├── backtest/                          # 因子研究 + 回测;statarb.py = 流 B 做多做空引擎
├── feed/                              # 情报馈送(JSON 单一真相源):routine + OpenClaw 写,看板读
├── scripts/                           # run_routine / openclaw_client / validate_feed / feed_lib
├── routines/                          # Claude 可执行 routine playbook
├── .github/workflows/                 # deploy-pages + alpha-routine(定时) + feed-validate(投递闸门)
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
- 想速查**所有接入的端点(上游源 + 本平台 API)** → [`docs/endpoints.md`](docs/endpoints.md)
- 想跑**后端** → [`backend/README.md`](backend/README.md)
- 想**部署后端**(摆脱公共代理限流) → [`docs/deploy-backend.md`](docs/deploy-backend.md)

## ⚖️ 合规提示

- 多数免费行情源(如 yfinance/Yahoo)**禁止商业化重分发**,生产环境需采购正规授权数据。
- A股数据源(Tushare 等)有积分/权限与再分发限制。
- 平台所有 AI 输出均为**信息参考,非投资建议**(not financial advice)。
