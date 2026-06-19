# 02 · TradingAgents-CN 调研

> 调研日期：2026-06-19 · 方法：WebSearch/WebFetch 核实 · 诚实纪律：每条关键结论标【来源 + 可信度】，区分证据与营销，star 高 ≠ 能赚，无法核实标「未核实」。

## 一、仓库事实

- **真实仓库**：`hsliuping/TradingAgents-CN` —— <https://github.com/hsliuping/TradingAgents-CN>。【官方仓库页｜高】
  - 搜索结果中存在大量同名 fork（`ysfli/`、`zilogo/`、`garyma-ai01/`、`tinkermend/`、`chengshuxiao/Fork-...`），**真正上游中文版是 `hsliuping`**，引用时勿指错。【高】
- **作者/维护者**：hsliuping（联系邮箱 hsliup@163.com，用于商业授权）。【README｜高】
- **Star 数**：仓库页显示约 **28.7k stars / 6.1k forks**（2026-06 抓取）。榜单标「~27k」**基本属实，略偏低不算夸大**。【GitHub 仓库页｜中-高，star 实时变动】
  - 注意：star 高来自「中文 + AI + 炒股」三热点叠加 + 公众号导流，**与盈利能力无任何因果关系**。【判断｜高】
- **License（关键坑）**：**混合授权，非纯开源**。
  - `app/`（FastAPI 后端）与 `frontend/`（Vue 前端）**为专有，商业使用必须单独授权**；其余文件 Apache-2.0。
  - README 明确：「❌ 商业使用：必须获得商业授权，未经授权禁止商业使用」；v2.0「暂时不进行开源」（称因盗版顾虑）。【README｜高】
  - → **不能直接把其 Web/后端代码并入商业系统**；只有非 app/frontend 的 Apache 部分可复用。
- **活跃度**：活跃。v1.0.1（2026-04-14）为当前稳定版；v1.0.0-preview（2025-10）做了 FastAPI/Vue3 重构；2025 年有 v0.1.x 系列。约 215 open issues，社区使用量大。【README/仓库页｜高】
- **与上游关系**：**TauricResearch/TradingAgents 的中文增强衍生版**（非简单 fork，含架构改造 + 上游吸收）。上游约 87.4k stars、Apache-2.0、多智能体角色（分析师/研究员/交易员/风控）。【两仓库页｜高】

## 二、中文 / A股增强点

- **中文/A股数据源**：Tushare、AkShare、BaoStock 三路适配 + 东方财富（Eastmoney）接口；带**降级链**容错，例如实时行情 `stock_bid_ask_em → stock_zh_a_spot → stock_zh_a_spot_em → stock_zh_a_hist`。【README｜高】
  - 数据层：**MongoDB + Redis 双库**做同步与缓存。【README｜中-高】
- **中文 LLM**：通义千问 Qwen、DeepSeek、Kimi（月之暗面）、GLM（智谱），并保留 OpenAI/Google AI 及聚合商 AiHubMix；号称支持 60+ 模型选择。【README/中文测评｜高】
  - 成本工程：**快/慢双模型分工**（如 gpt-4o-mini 做检索摘要、深模型做推理决策）+ 实时 Token 统计/成本估算。【中文测评｜中】
- **A股特有处理**：README 宣称「完整 A股支持」，并被二手来源描述为覆盖涨跌停/停牌/T+1/复权。
  - ⚠️ **但 README 未给出 T+1/涨跌停/停牌/复权的具体实现代码或说明**，属「声称」而非可见证据。要用需**自行读源码核实**，此处标【中-低，未在文档层证实】。

## 三、可信度

- **业绩**：**无任何真实样本外业绩**。上游 TradingAgents 明确「研究用途，回测结果不保证复现，勿作投资建议」；CN 版同样声明「仅用于研究和教育，不构成投资建议」，「不提供实盘交易指令」。【两仓库 README｜高】
  - → 任何「能赚钱」的印象均来自营销/二手文章，**无可核实的 OOS 收益、Sharpe、基准对比**。标【高｜确认为 demo/研究脚手架】。
- **已知问题/局限**（多为二手中文测评，标【中】）：
  - AkShare 在策略循环内**同步调用易触发反爬→IP 封禁**，社区共识是**只做盘后 ETL 落库**，实盘读本地库。【数据源测评｜高】
  - Tushare 积分制，高频/高级接口需积分或付费；**数据仅限个人研究，禁止商业重分发**。【Tushare 文档/测评｜高】
  - LLM 推理不确定性 + Token 成本，官方建议先沙箱/模拟。【中文测评｜中】
- **A股数据合规/重分发**：Tushare「个人研究、禁止商业重分发」；AkShare 抓取上游网站、稳定性依赖源站。**把这些数据经本项目对外分发/商用存在合规风险**，且与项目自身「商业需授权」叠加。【高】

## 四、可借鉴 / 须避免（对我们系统）

我方已覆盖美/港/A/加密，有 A股 AkShare/Tushare 接入计划、OpenClaw agent 编队、feed 闭环。

**可借鉴（模式层，非抄代码）**：
- **多源降级链**：A股行情/历史按「实时→快照→历史」多接口 fallback，提升取数韧性 —— 直接对标我们 AkShare/Tushare 接入计划。【高价值】
- **AkShare 仅做盘后 ETL 落库**（ClickHouse/TimescaleDB/Mongo），实盘只读本地库，避开反爬封 IP。**这条是工程红线，建议直接采纳**。
- **中文 LLM 快/慢双模型分工 + 实时 Token 计量**：检索摘要用便宜快模型，推理决策用深模型；成本可观测。契合我们 agent 编队的成本闭环。
- **Mongo + Redis 数据/缓存分层**作为 A股 feed 缓存参考。

**须避免**：
- ❌ **勿直接引入其 `app/` / `frontend/` 代码**（专有、商业需授权）—— 只可参考 Apache 部分的思路。
- ❌ **勿把项目「28.7k star」当质量/盈利背书**；无 OOS 业绩。
- ❌ **勿信文档层「完整 A股支持」的涨跌停/T+1 等表述**未经源码核实即复用 —— 我方应自建并单测这些 A股规则。
- ❌ **勿对外重分发 Tushare/AkShare 派生数据**（合规 + 许可双重风险）。

## 五、一句话定位

**TradingAgents-CN = 上游 TradingAgents 的中文/A股本地化研究脚手架**：中文 LLM 接入与多源 A股取数的工程模式（尤其降级链、盘后 ETL、快慢双模型）值得借鉴；但**核心后端/前端为商业受限非开源、零真实样本外业绩、A股规则实现未在文档层证实**——当「学习参照与工程套路库」用，不当「能赚钱的成品」用。

---
### 来源
- TradingAgents-CN 仓库/README：<https://github.com/hsliuping/TradingAgents-CN>（高）
- 上游 TradingAgents：<https://github.com/TauricResearch/TradingAgents>（高）
- 数据源合规（Tushare/AkShare）：<https://tushare.pro/document/1?doc_id=108>、<https://blog.infoway.io/tushare-akshare-infoway-api-comparison/>（高/中）
- 中文测评（成本/局限，二手）：<https://www.cnblogs.com/tlnshuju/p/19354275>、<https://cloud.tencent.com/developer/article/2638662>（中）
- Grokipedia 条目：<https://grokipedia.com/page/TradingAgents-CN>（**未核实**，抓取 403）
