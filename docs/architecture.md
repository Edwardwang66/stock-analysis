# 平台技术架构设计 — 多市场股票数据看板

> 配套阅读:[`../research/ai-agents-skills-market-scan.md`](../research/ai-agents-skills-market-scan.md)(选型依据)、[`roadmap.md`](roadmap.md)(实施顺序)。
> 技术栈:**Next.js + Python(FastAPI)**;市场:美股 / 港股 / A股 / 加密货币。

---

## 1. 设计目标与原则

| 目标 | 说明 |
|------|------|
| **多市场统一** | 不同市场的数据源差异巨大,需在内部抽象成**统一数据模型**(Symbol、OHLCV、Fundamentals、News)。 |
| **数据源可插拔** | 任一数据源(yfinance/Tushare/Binance…)都封装为 `DataProvider` 适配器,可热切换、可降级。 |
| **AI 能力解耦** | AI 分析作为独立服务层,以 MCP / 工具调用方式访问数据,而非耦合进数据管线。 |
| **成本可控** | 免费源优先 + 缓存优先,付费源仅在必要处使用;严守各源**重分发与限频**约束。 |
| **可演进** | 先单体 + 模块化,再按负载拆分微服务;不过早过度设计。 |

---

## 2. 总体架构(分层)

```
┌──────────────────────────────────────────────────────────────┐
│  前端层  Next.js (App Router) + React + TypeScript              │
│  · 行情看板 / K线 / 热力图 / 个股页 / AI 对话框                  │
│  · TradingView Lightweight Charts · TanStack Query · shadcn/ui  │
└───────────────▲───────────────────────────▲──────────────────┘
                │ REST / WebSocket           │ SSE (AI 流式)
┌───────────────┴───────────────────────────┴──────────────────┐
│  API 网关层  FastAPI (Python)                                   │
│  · /api/quotes /api/fundamentals /api/news /api/ai/chat        │
│  · 鉴权(JWT) · 限流 · 请求聚合 · WebSocket 行情推送            │
└───────┬───────────────────┬────────────────────┬─────────────┘
        │                   │                    │
┌───────▼──────┐   ┌────────▼────────┐   ┌───────▼───────────────┐
│ 数据服务层    │   │ AI 服务层        │   │ 任务/调度层            │
│ DataProvider │   │ Agent Orchestr. │   │ Celery / APScheduler   │
│ 适配器 + 归一 │   │ Claude + MCP     │   │ · 定时拉取行情/财报    │
│ 化 + 缓存     │   │ Tools: 行情/财务 │   │ · 情绪分析批处理       │
└───────┬──────┘   │ /新闻/技术指标   │   │ · 数据落库             │
        │          └────────┬────────┘   └───────┬───────────────┘
        │                   │                    │
┌───────▼───────────────────▼────────────────────▼─────────────┐
│  存储层                                                         │
│  · PostgreSQL + TimescaleDB(时序行情/指标)                    │
│  · Redis(实时行情缓存 / 限流 / 会话)                          │
│  · 对象存储 S3(研报/PDF/财报原文)                             │
│  · (可选)向量库 pgvector / Qdrant(新闻&财报 RAG)            │
└───────────────────────────────────────────────────────────────┘
        ▲
┌───────┴───────────────────────────────────────────────────────┐
│  外部数据源(适配器封装)                                        │
│  美股: yfinance/AlphaVantage/Polygon/Finnhub/FMP               │
│  A股/港股: Tushare/AkShare/东方财富/Futu  ·  加密: Binance/CoinGecko │
│  宏观: FRED  ·  新闻: Finnhub/NewsAPI                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. 前端(Next.js)

- **框架**:Next.js(App Router)+ TypeScript + React Server Components。
- **图表**:[TradingView Lightweight Charts](https://www.tradingview.com/lightweight-charts/)(免费、轻量、K线/分时)。复杂指标叠加可用 `klinecharts`。
- **状态/数据**:TanStack Query(请求缓存 + 失效)、Zustand(轻量本地状态)。
- **UI**:Tailwind CSS + shadcn/ui;暗色为主(行情场景)。
- **实时**:WebSocket 订阅行情;AI 回答用 **SSE 流式**渲染。
- **核心页面**:
  1. **市场总览**:四市场切换、指数、涨跌幅热力图(Treemap)。
  2. **个股页**:K线 + 指标 + 基本面卡片 + 新闻流 + AI 分析按钮。
  3. **自选/看板**:用户自定义关注列表。
  4. **AI 助手**:自然语言提问("帮我对比 AAPL 和 MSFT 的估值")。

---

## 4. 后端(FastAPI)

- **为何 Python 后端**:金融数据生态(pandas、TA-Lib、yfinance、Tushare、Backtrader、FinBERT)几乎全在 Python;AI/量化能力天然契合。
- **职责**:对外 REST/WebSocket;对内编排数据服务层与 AI 服务层;鉴权、限流、聚合。
- **关键模块**:
  - `app/api/`:路由(quotes、fundamentals、news、screener、ai)。
  - `app/providers/`:数据源适配器(见 §5)。
  - `app/services/`:业务逻辑(行情聚合、指标计算、舆情)。
  - `app/ai/`:Agent 编排(见 §6)。
  - `app/jobs/`:定时任务。

---

## 5. 数据服务层 —— 统一数据模型 + 适配器

这是平台**最关键**的抽象。各市场数据源字段、频率、限频、合规差异巨大,必须归一化。

```python
# 统一接口(示意)
class DataProvider(Protocol):
    def get_quote(self, symbol: Symbol) -> Quote: ...
    def get_ohlcv(self, symbol: Symbol, interval: str, range: str) -> list[Bar]: ...
    def get_fundamentals(self, symbol: Symbol) -> Fundamentals | None: ...
    def get_news(self, symbol: Symbol) -> list[NewsItem]: ...

# Symbol 统一编码:市场前缀 + 代码,如 US:AAPL / HK:00700 / CN:600519 / CRYPTO:BTCUSDT
```

- **路由策略(Provider Router)**:按 `Symbol.market` 选择默认源 + 备用源(降级)。
  - 美股 → Finnhub(60/分,最慷慨免费档)/yfinance(免费看板)→ Polygon/Massive(实时付费)。
  - A股 → AkShare(免费)/ Tushare(积分)→ 东方财富。
  - 港股 → yfinance / AkShare → Futu OpenAPI。
  - 加密 → Binance(行情)/ CoinGecko(市值)。
- **缓存策略**:Redis 短 TTL(实时报价秒级)+ TimescaleDB 落历史 K线;遵守各源限频。
- **合规**:免费源(yfinance 等)**仅自用/不可重分发**;生产商用须采购授权(详见研究报告合规小节)。

---

## 6. AI 服务层 —— Agent 编排 + MCP 工具

参考调研中 **TradingAgents / AI-Hedge-Fund** 的多智能体设计与 **Anthropic 金融 Skills**,采用「**编排器 + 工具(MCP)+ 专家 Agent**」模式:

```
用户提问
   │
   ▼
┌─────────────────────────────────────────────┐
│  Orchestrator (Claude, claude-opus-4-8)      │
│  规划 → 调用工具 → 综合 → 流式输出           │
└───────┬──────────┬──────────┬───────────────┘
        │          │          │
   ┌────▼───┐ ┌────▼────┐ ┌───▼─────┐
   │行情工具 │ │基本面/  │ │新闻舆情 │   (作为 MCP server / 本地工具暴露)
   │OHLCV   │ │财报工具 │ │FinBERT  │
   └────────┘ └─────────┘ └─────────┘
```

- **模型**:默认 **Claude(claude-opus-4-8)** 做编排与推理;情绪分类用开源 **FinBERT**(成本低、批量快)。
- **工具复用现成 MCP**:可直接接入 `financial-datasets MCP`、`Alpha Vantage MCP`、`CoinGecko MCP`(见研究报告),减少自研。
- **专家 Agent(可选进阶)**:技术面 / 基本面 / 舆情 / 风险,借鉴 TradingAgents 的"分析师辩论"结构生成研报。
- **RAG**:财报/新闻原文入向量库(pgvector),AI 回答带**引用溯源**。
- **强约束**:所有输出标注"非投资建议";数值类回答必须来自工具真实数据,禁止臆测。

---

## 7. 存储层

| 用途 | 选型 | 理由 |
|------|------|------|
| 时序行情/指标 | PostgreSQL + **TimescaleDB** | 时序压缩、连续聚合,SQL 友好 |
| 实时缓存/限流/会话 | **Redis** | 低延迟、TTL、计数器 |
| 财报/研报/PDF | **S3 兼容对象存储** | 原文留存,供 RAG/下载 |
| 新闻&财报向量 | **pgvector** 或 Qdrant | RAG 检索 |
| 用户/自选/配置 | PostgreSQL | 事务型 |

---

## 8. 部署与运维

- **容器化**:Docker Compose 起步(前端、API、worker、PG、Redis);后续可上 K8s。
- **环境**:`.env` 管理各数据源 API Key 与 Claude API Key;密钥不入库不入仓。
- **可观测**:结构化日志 + Prometheus/Grafana(数据源命中率、限频、AI 调用耗时与成本)。
- **CI**:GitHub Actions 跑 lint + 测试;前后端独立流水线。

---

## 9. 关键技术风险与对策

| 风险 | 对策 |
|------|------|
| 免费源(yfinance/Yahoo)不稳定、易封 | 多源降级 + 缓存 + 监控;商用切付费授权源 |
| 数据**重分发合规** | 仅做"展示/分析",不批量转售;采购授权 |
| AI **幻觉数值** | 数值强制走工具;回答带引用;关键结论交叉校验 |
| 实时行情成本高 | 看板用延迟/快照行情;实时仅付费用户/特定页面 |
| 多市场时区/交易日历 | 统一 `MarketCalendar` 抽象,按市场处理交易时段 |

---

## 10. 技术选型一览(摘要)

| 层 | 选型 |
|----|------|
| 前端 | Next.js · TypeScript · TradingView Lightweight Charts · TanStack Query · Tailwind/shadcn |
| 后端 | Python · FastAPI · Pydantic · WebSocket/SSE |
| 数据 | yfinance/AlphaVantage/Polygon/Finnhub/FMP · Tushare/AkShare/东方财富 · Binance/CoinGecko · FRED |
| 计算 | pandas · pandas-ta/TA-Lib · FinBERT · (进阶)VectorBT/Backtrader · PyPortfolioOpt |
| AI | Claude(claude-opus-4-8)· MCP 工具 · pgvector RAG |
| 存储 | PostgreSQL+TimescaleDB · Redis · S3 · pgvector |
| 运维 | Docker Compose · GitHub Actions · Prometheus/Grafana |
