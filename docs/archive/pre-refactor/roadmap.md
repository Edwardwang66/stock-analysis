# 实施路线图与 MVP 范围
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [accepted migration program](../../superpowers/specs/2026-07-16-stock-analysis-refactor-design.md); historical prose below is preserved, and moved local link targets are redirected to their current repository locations.

> 配套:[`architecture.md`](../../architecture.md) · [`../research/ai-agents-skills-market-scan.md`](../../../research/ai-agents-skills-market-scan.md)

本平台采用「**先窄后宽、先免费源后付费源、先看板后 AI**」的演进策略。

---

## 阶段总览

| 阶段 | 目标 | 市场范围 | AI 程度 | 产出 |
|------|------|---------|---------|------|
| **P0 研究 + 架构**(当前) | 选型与设计定稿 | 全部(纸面) | — | 本仓库文档 |
| **P1 MVP 看板** | 跑通"数据→展示"主链路 | 美股 + 加密 | 无/极轻 | 可运行最小看板 |
| **P2 多市场 + 基本面** | 接入 A股/港股、财务数据 | 四市场 | 轻 | 个股基本面页 |
| **P3 AI 助手** | 自然语言查询 + 个股分析 | 四市场 | 中 | Claude+MCP 对话 |
| **P4 进阶分析** | 舆情/研报/筛选/回测 | 四市场 | 高 | 多 Agent 研报 |

---

## P1 — MVP 看板(优先做)

**为什么从美股 + 加密起步**:数据源最丰富、免费、无重分发以外的强合规门槛,链路最短。

- [ ] 后端:FastAPI 骨架 + `DataProvider` 抽象 + 1~2 个适配器(yfinance、Binance/CoinGecko)。
- [ ] 统一数据模型:`Symbol / Quote / Bar / NewsItem`。
- [ ] 缓存:Redis 报价缓存 + TimescaleDB 落历史 K线。
- [ ] 前端:Next.js + Lightweight Charts;市场总览 + 个股 K线页。
- [ ] WebSocket 行情推送(加密用 Binance WS,美股用轮询/快照)。
- [ ] Docker Compose 一键起。

**验收**:输入 `AAPL` / `BTCUSDT`,看到实时报价 + 历史 K线 + 涨跌热力图。

---

## P2 — 多市场 + 基本面

- [ ] 接入 A股(AkShare 免费 / Tushare 积分)、港股(yfinance/AkShare/Futu)。
- [ ] `MarketCalendar`:各市场交易时段/节假日。
- [ ] 基本面适配器:财报三表、估值指标(FMP/AlphaVantage/AkShare)。
- [ ] 个股页加入基本面卡片 + 财务图表。
- [ ] 多源降级与监控(命中率、限频告警)。

---

## P3 — AI 助手(Claude + MCP)

- [ ] AI 服务层:Orchestrator(Claude `claude-opus-4-8`)。
- [ ] 工具暴露:行情/基本面/新闻 作为本地工具或接入现成 MCP(financial-datasets、Alpha Vantage、CoinGecko)。
- [ ] 前端 AI 对话框(SSE 流式)+ 引用溯源。
- [ ] 强约束:数值必走工具、输出标注"非投资建议"。

**验收**:"对比 AAPL 和 MSFT 近三年营收与估值",AI 调工具取真实数据并图文作答。

---

## P4 — 进阶分析

- [ ] 新闻舆情:聚合新闻 + FinBERT 情绪打分 + 情绪时间线。
- [ ] RAG:财报/新闻原文入 pgvector,问答带引用。
- [ ] 多 Agent 研报:借鉴 TradingAgents/AI-Hedge-Fund 的"分析师辩论"结构。
- [ ] 选股筛选器(技术/基本面/情绪多因子)。
- [ ] (可选)量化回测:VectorBT/Backtrader;组合优化:PyPortfolioOpt。

---

## 横切事项(各阶段持续)

- **合规**:免费源不重分发;商用前采购授权;全站"非投资建议"声明。
- **成本**:免费源 + 缓存优先;监控 AI 调用 token 成本。
- **测试/CI**:GitHub Actions lint + 单测;适配器需 mock 外部源。
- **安全**:API Key 走环境变量;用户鉴权 JWT;限流防滥用。
