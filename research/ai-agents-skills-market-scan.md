# 市场调研:股票 / 经济 / 市场 相关 AI Agent 与 AI Skills 全景

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

> 调研时间:2026-06 · 方法:多路并行网络检索 + 对抗式核验(deep-research 流程)。
> 目的:为搭建**多市场股票数据看板平台**(美股/港股/A股/加密,Next.js + Python)提供选型依据。
> ⚠️ 星标数、价格为检索时近似值,会变动;商用前请到官网二次确认。标注"未核实"的条目谨慎采信。

## 目录
1. [商业化 AI 股票分析平台 / SaaS](#1-商业化-ai-股票分析平台--saas)
2. [开源金融 LLM / Agent 框架](#2-开源金融-llm--agent-框架)
3. [AI Skills / Plugins / MCP Servers(可接入 Claude/GPT)](#3-ai-skills--plugins--mcp-servers)
4. [按能力维度的工具盘点](#4-按能力维度的工具盘点)
5. [数据源 API 对比(免费/付费/合规)](#5-数据源-api-对比)
6. [对本平台的选型结论](#6-对本平台的选型结论)

---

## 1. 商业化 AI 股票分析平台 / SaaS

### 1.1 海外(Western)

| 产品 | 做什么 | 市场 | AI 能力 | 价格 | 来源 |
|------|--------|------|---------|------|------|
| **Fiscal.ai**(原 FinChat/Fey) | 对话式投研,覆盖 10万+ 全球上市公司财报/KPI/分析师预期/仪表盘 | 美股/全球 | 对话、摘要、筛选、仪表盘;另售 API & MCP | 免费层;Pro ≈ $39/月(年付) | [wallstreetzen](https://www.wallstreetzen.com/blog/finchat-io-fiscal-ai-review/) |
| **Public.com "Alpha"** | 券商内置 AI 投研助手(原 GPT-4) | 美股(~9000 只) | 自然语言、实时筛选、财报电话会摘要、新闻 | 免费(随账户) | [public.com/ai-agents](https://public.com/ai-agents) |
| **Bloomberg Terminal AI / BloombergGPT** | 500亿参数金融模型 + 终端 AI 功能 | 机构 | 财报会摘要、Document Insights 问答、跨文档检索、新闻摘要、AskBloomberg | 含于终端订阅(~$2万/年/席) | [bloomberg press](https://www.bloomberg.com/company/press/bloomberg-launches-ai-powered-earnings-call-summaries/) |
| **Perplexity Finance** | Perplexity 金融垂类 + 研究终端 | 美股 + 加密 | 对话研究、实时指数/期货、热力图、Earnings Hub 实时转录 | 免费(高级随 Pro) | [perplexity.ai/finance](https://www.perplexity.ai/finance) |
| **AlphaSense** | 企业市场情报/搜索,5亿+ 文档(filings/transcripts/研报) | 机构/全球 | 生成式搜索、摘要、Smart Synthesis | 企业报价 | [alpha-sense.com](https://www.alpha-sense.com/) |
| **Danelfin** | 每只股票 AI Score(1-10),用 1万+ 因子(技术/基本面/情绪) | 美股 | 评分/筛选(非聊天) | 付费订阅(有限免费) | [danelfin.com](https://danelfin.com/) |
| **Tickeron** | AI 图形态识别 + 交易信号 | 美股/加密/外汇 | 形态识别、AI robots/信号 | 付费分层 | [tickeron](https://tickeron.com/) |
| **Boosted.ai** | 面向机构的无代码 AI/ML 组合管理,旗舰助手 "Alfa" | 机构 | 智能体研究助手、ML 组合工具 | 企业报价 | [via alpha-sense](https://www.alpha-sense.com/compare/alphasense-vs-boosted-ai/) |
| **Kavout** | AI 引擎 "Kai" → Kai Score(1-9);筛选/告警/API | 美股/ETF + 加密 | 评分、筛选、告警、API | 分层 | [kavout.com](https://www.kavout.com/) |
| **Trade Ideas (Holly)** | AI 扫描/告警,隔夜模拟选股 | 美股 | 扫描、信号、模拟选股 | 付费(Standard/Premium) | [officechai](https://officechai.com/learn/ai-tools-for-stock-analysis/) |
| **Composer** | 无代码:自然语言 → 回测 → 自动交易 | 美股 + 加密 | 策略生成、回测、自动化 | ≈ $24/月(年付) | [composer.trade/ai](https://www.composer.trade/ai) |

> 核验提示:Danelfin "+376%" 等业绩为**自报、未经独立审计**;多家(Tickeron/Kavout/Trade Ideas/AlphaSense/Boosted)精确价格为分层或报价制,未逐一核到官网定价页。检索中**未能确认存在名为 "Magnificent" 的金融 AI 产品**。

### 1.2 中国(A股/港股,中文)

| 产品 | 做什么 | 市场 | AI 能力 | 价格 | 来源 |
|------|--------|------|---------|------|------|
| **东方财富「妙想」金融大模型** | 自研金融大模型,强在投研;AI研究员生成行业研报 | A股/基金 | 对话、深度搜索、多源交叉验证、研报生成 | 2025 C端对全体用户免费;B端"妙想投研助理"另算 | [ai.eastmoney.com](https://ai.eastmoney.com/) |
| **同花顺「问财」/ HithinkGPT(iFinD)** | 自研 LLM,首个过网信办备案的金融对话模型;2025 升级为自主规划 Agent | A股 | 自然语言选股("问财")、对话、智能体研究 | 免费增值(付费转化 ~5.3%,ARPU ~¥1572/年) | [aibase](https://top.aibase.com/tool/tonghuashunwencaidamoxinghithinkgpt) |
| **富途牛牛 (Futu/Moomoo) AI** | AI 选股 + 港美股热点图谱;跨境多币种 | 港股+美股 | AI 筛选、热点/情绪图谱 | 含于 App(AI 单独价格未核) | [sina](https://finance.sina.com.cn/stock/aigcy/2025-10-11/doc-inftnynp0459764.shtml) |
| **老虎证券 (Tiger) AI** | 中文服务 + 美股工具 + 碎股 | 美股+港股 | 集成 AI 工具(深度未充分披露) | 含于 App | [sina](https://finance.sina.com.cn/roll/2025-12-18/doc-inhcfvmc8320245.shtml) |
| **雪球 (Xueqiu)** | 社交投资生态,组合跟投/一键跟单 | A股/港股/美股 | AI 集成较轻,偏社区/情绪 | 免费 + 付费内容 | [sina](https://finance.sina.com.cn/stock/aigcy/2025-10-11/doc-inftnynp0459764.shtml) |
| **通达信 (TongDaXin)** | 专业技术分析平台 | A股 | AI 集成偏弱(传统图表为主) | 免费 + 付费 L2 | [sina](https://finance.sina.com.cn/stock/aigcy/2025-10-11/doc-inftnynp0459764.shtml) |

### 1.3 加密 AI 工具
2025–26 多数"加密 AI 分析"是上面平台的多资产能力(Tickeron/Kavout/Composer/Perplexity),而非独立龙头;加密原生 AI 交易 bot 多见于聚合榜单([koinly](https://koinly.io/blog/ai-trading-apps/)),未独立核实出单一主导产品。

---

## 2. 开源金融 LLM / Agent 框架

> 星标为 2026-06 近似;部分来源对 Qlib 星数有冲突(见注)。

### 多智能体交易/投研框架
- **TradingAgents**(Tauric Research)— **~83k★** · Apache-2.0。模拟真实交易公司:基本面/情绪/技术分析师 + 交易员 + 风控团队**辩论**决策。支持 OpenAI/Anthropic/Gemini/Grok/DeepSeek/Qwen/Ollama 等;数据用 Yahoo/Alpha Vantage/新闻/StockTwits/Reddit。论文 arXiv 2412.20138。[GitHub](https://github.com/TauricResearch/TradingAgents)
- **AI Hedge Fund**(virattt/ai-hedge-fund)— **~60k★** · MIT。教育性 PoC,~19 个 Agent,含投资人人格(巴菲特/芒格/格雷厄姆/Ackman/木头姐/Burry/Damodaran)+ 估值/情绪/基本面/技术 + 风控 + 组合经理,含回测。LLM:OpenAI/Anthropic/Groq/DeepSeek/Ollama;数据:Financial Datasets API。**非实盘**。[GitHub](https://github.com/virattt/ai-hedge-fund)
- **FinRobot**(AI4Finance)— **~7k★** · Apache-2.0。金融应用智能体平台:自动股票研报、金融分析、投资策略工作流(Financial CoT)。数据:FMP/Finnhub/SEC/yfinance/FinNLP。[GitHub](https://github.com/AI4Finance-Foundation/FinRobot)
- **FinMem**(pipiku915/FinMem-LLM-StockTrading)— 研究级,分层记忆 + 角色画像 + 决策模块,强调可解释记忆。arXiv 2311.13743。星数/许可未核实。[GitHub](https://github.com/pipiku915/FinMem-LLM-StockTrading)

### 金融 LLM
- **FinGPT**(AI4Finance)— **~20k★** · MIT。轻量 LoRA 微调(每次更新 <$300),基座 Llama-2/Falcon/ChatGLM2/Qwen 等;强在情绪分析。论文 arXiv 2306.06031。[GitHub](https://github.com/AI4Finance-Foundation/FinGPT)

### 量化平台 / 强化学习
- **Qlib**(Microsoft)— **~44k★**(部分二手文章称 6k+,以仓库页为准,标注冲突)· MIT。AI 量化全流程:数据/训练/回测/生产;支持监督学习、市场动态建模、RL(PPO/OPDS);集成 RD-Agent(LLM 自动因子挖掘)。[GitHub](https://github.com/microsoft/qlib)
- **FinRL**(AI4Finance)— **~15k★** · MIT。首个金融深度强化学习框架,"train-test-trade" 管线;A2C/DDPG/PPO/SAC/TD3。[GitHub](https://github.com/AI4Finance-Foundation/FinRL)

### 数据平台(面向 AI Agent)
- **OpenBB**(OpenBB-finance/OpenBB)— **~69k★** · 平台 AGPLv3(旧 CLI MIT)。"面向分析师/quant/AI agent 的金融数据平台",整合公开/授权/自有数据,提供 Python/Excel/REST/**MCP server**(另有 `agents-for-openbb`)。本身不是 LLM,而是 Agent 的数据/工具层。[GitHub](https://github.com/OpenBB-finance/OpenBB)

### 轻量 / 单 Agent
- **StockBot on Groq**(bklieger-groq)— **~1.5k★**。对话返回 TradingView 实时图表/财务/新闻/筛选;LLM:Llama 3 70B on Groq(TS/Vercel AI SDK)。[GitHub](https://github.com/bklieger-groq/stockbot-on-groq)
- **gpt-investor**(mshumer)— **~2.3k★** · MIT。拉取数据/新闻/评级、情绪分析、排序公司;现版用 Claude 3 Opus/Haiku。[GitHub](https://github.com/mshumer/gpt-investor)
- 其他:**StockAgent**(MingyuJ666)模拟环境 LLM 交易;清单 **awesome-ai-in-finance**、**awesome-quant** 适合继续发掘。

> 核验:FinMem/FinAgent 星数与许可未核;未发现独立高星的 LangChain/LlamaIndex 原生金融 Agent 旗舰(多以组件形式存在于上述项目)。

---

## 3. AI Skills / Plugins / MCP Servers

### 金融数据 MCP server(可直接接 Claude / Claude Code)
| MCP | 提供能力 | 接入 | 免费层 | 来源 |
|-----|---------|------|--------|------|
| **Financial Datasets MCP**(官方) | 三大报表、当前/历史价、公司新闻、加密价(~10 工具) | 远程 HTTP + OAuth/API Key | 100 req/天;付费 ~$49/月 | [GitHub](https://github.com/financial-datasets/mcp-server) |
| **Alpha Vantage MCP**(官方) | 股/ETF/基金/外汇/加密/商品/经济/基本面/技术指标;渐进式工具发现 | 远程 URL | 25 calls/天;付费 ~$29.99/月+ | [GitHub](https://github.com/alphavantage/alpha_vantage_mcp) |
| **Polygon.io MCP**(官方) | 股/期权/外汇/加密 实时+历史、tick、WebSocket | uvx 安装 | 5 req/分,2 年历史;实时付费 | [GitHub](https://github.com/polygon-io/mcp_polygon) |
| **CoinGecko MCP**(官方) | 200+ 链、800万+ token 价格/市值/交易所/NFT/DeFi/链上 | 远程,免密测试 | 公共免费测试;生产需 Key | [docs](https://docs.coingecko.com/docs/mcp-server) |
| **yfinance / Yahoo MCP**(社区,多个) | 历史价/公司信息/报表/期权/新闻/筛选 | 本地 | 全免费(Yahoo,无 Key,**不稳定**) | [Alex2Yang97](https://github.com/Alex2Yang97/yahoo-finance-mcp) · [hachecito ~30工具](https://github.com/hachecito/yfinance-market-mcp) |
| **EODHD / FMP / Alpaca / QuantConnect MCP** | 全球行情/基本面/回测/交易 | 各异 | EODHD 20/天;FMP 250/天 | [roundup](https://dev.to/kevin_menesesgonzlez/the-7-best-mcp-servers-for-stock-market-data-2026-389l) |

### Claude Skills / Anthropic 官方
- **Anthropic 金融服务 Skills(官方)**— 6 个金融 Skill:可比公司分析(估值倍数)、DCF 模型、尽调数据包、公司 teaser/画像、财报分析(季度 transcript)、首次覆盖研报。Skill = 文件夹(指令+脚本+资源),通用于 Claude.ai/Claude Code/API,可作为 Cowork/Code 插件或托管 Agent。[GitHub](https://github.com/anthropics/financial-services) · [news](https://www.anthropic.com/news/advancing-claude-for-financial-services)
- **Anthropic Skills 仓库(通用)**— 含数据分析类 Skill,可用于金融工作流。[GitHub](https://github.com/anthropics/skills)
- **Claude Marketplace** — Claude agents/plugins 分发(含金融);托管 Agent 公测,可响应 SEC filing webhook、长时运行。[claude.com/platform/marketplace](https://claude.com/platform/marketplace)
- **Claude for Financial Services 数据连接器** — 接 Databricks/Snowflake/LSEG 等(企业付费)。[anthropic](https://www.anthropic.com/news/claude-for-financial-services)

### ChatGPT 侧
- OpenAI **已下线 Plugins 平台(2024)**,能力并入**自定义 GPTs(GPT Store)**与内置工具。金融类 GPT:股票分析 GPT、**Wolfram GPT**(金融计算)、**AskYourPDF**(解析 filings);需 Plus。[来源](https://promptengineering.org/the-proliferation-of-finance-and-investing-chatgpt-plugins/)

### MCP / Skill 市场
- 官方索引 **modelcontextprotocol/servers**(Linux Foundation);注册站 mcpservers.org、PulseMCP、Glama、mcp.so、LobeHub 等。

---

## 4. 按能力维度的工具盘点

| 能力 | 代表工具 | 一句话 |
|------|---------|--------|
| **技术分析(指标)** | **TA-Lib**(150+ 指标/60+ K线形态,C 高速)· **pandas-ta**(150+,pandas) | 看板指标计算首选 [ta-lib](https://ta-lib.org/) |
| **图形态识别(AI)** | **PatternPy**(头肩/双顶底)· **YOLOv8 形态检测**(CV 识图) | 图像/规则两路 [hf](https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8) |
| **基本面/财报解读** | LLM+RAG over filings(GPT-4/Claude,~85% 命中需复核)· **Brightwave** · **AlphaSense** | 解析 10-K/10-Q [arxiv](https://arxiv.org/html/2407.17866v1) |
| **新闻/社媒情绪** | **FinBERT**(ProsusAI,行业基线,开源)· LLM 情绪打分 · FinBERT-LSTM 混合 | 情绪首选 [finBERT](https://github.com/ProsusAI/finBERT) |
| **财报电话会摘要** | **Aiera**(Claude 3.5 Sonnet 生产最佳)· **AlphaSense Smart Summaries** · **Hudson Labs** · **FactSet** | 实时转录+摘要 [zenml](https://www.zenml.io/llmops-database/building-and-evaluating-a-financial-earnings-call-summarization-system) |
| **量化回测** | **VectorBT**(向量化超快)· **Backtrader**(事件驱动,贴近实盘)· **Zipline-reloaded** · **Qlib** | 研究用 VectorBT,实盘路径 Backtrader |
| **组合优化** | **PyPortfolioOpt**(均值方差/BL/HRP)· **Riskfolio-Lib**(CVXPY,24 风险度量)· **skfolio** | [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) |
| **AI 选股筛选** | **Danelfin**(可解释 AI Score)· **Zen Ratings** · **Tickeron** · **Kavout/Toggle/AltIndex** | 业绩宣称需谨慎 |
| **宏观经济** | **FRED API**(84万+ 时序)· **fredapi** · **fedfred**(异步) | 宏观最成熟开放接口 [fred](https://fred.stlouisfed.org/docs/api/fred/) |

> 核验:AI 宏观 nowcasting 缺成熟开箱产品,多为 DIY(FRED + 自训模型);各厂"跑赢 93% 基金经理"等宣称为营销口径,不可作可靠依据。TA-Lib 安装较繁琐,Zipline 需用 zipline-reloaded(Py3.10+)。

---

## 5. 数据源 API 对比

> 已经专项核验(2026-06)。价格/额度变动频繁,商用前到官网定价页二次确认。

### ⚠️ 两个重要变更(2025)
- **Polygon.io → 已更名 "Massive"(massive.com,2025-10-30)**。旧 URL/Key 仍可用并重定向;定价见 [massive.com/pricing](https://massive.com/pricing)。
- **IEX Cloud 已彻底关停(2024-08-31)**,不可用。[来源](https://iexcloud.org/)

### 美股 / 全球股票
| 源 | 免费层 | 付费起步 | 覆盖 | 关键限制 / 合规 |
|----|--------|---------|------|---------|
| **yfinance**(Yahoo,非官方) | 全免费,无 Key | — | 美/港(.HK)/A股(.SS/.SZ)/全球 | 非官方、**易封**;Yahoo ToS **仅个人非商用**,**重分发风险最高** |
| **Alpha Vantage** | **25 req/天**(极低) | ~$49.99/月(75/分,15分延迟);$99.99 实时 | 美/全球/外汇/加密/基本面/技术 | 免费额度太低,仅 demo |
| **Polygon / Massive** | 5 req/分,15分延迟,2年史 | ~$29(Starter)→$99→$199→$399 | 美股/期权/指数/外汇/加密(**无港/A**) | 实时在高档;20年 tick |
| **Finnhub** | **60 req/分**(此处最慷慨) | ~$49.99→$129.99→$199.99 | 美股实时;全球基本面/估值/外汇/加密/新闻/情绪 | **重分发权仅 Startup/Enterprise** 档 |
| **Financial Modeling Prep (FMP)** | ~250/天,30天 500MB | ~$22→$99+ | 美/全球、强基本面、SEC EDGAR、加密/外汇 | **展示/重分发需单独 Licensing 协议** |
| **Twelve Data** | 8 credits/分,800/天(**仅内部非展示**) | $79(Grow)→$229→$999 | 美实时+全球 EOD,扩至 70-84 市场 | Basic 不可对外展示 |
| **financialdatasets.ai** | — | PAYG;Developer **$200/月**;Pro **$2000/月**(含重分发授权) | 美股报表/价/filings/新闻/内部+机构;Pro 含加密 | 为 AI/LLM 设计,有 MCP;AI-Hedge-Fund 默认源 |
| **Tiingo** | 有限(EOD,低频) | ~$10(Power)/~$30 商用 | 美股/ETF/基金 EOD+盘中、加密、外汇、**新闻** | 免费非商用;精确限额未核 |

> 注:financialdatasets 的 **MCP** 标称"免费 100 req/天、付费 ~$49/月",而其 **API 定价**为 Developer $200/Pro $2000——两口径不同,以官网为准。

### A股 / 港股
| 源 | 免费层 | 覆盖 | 关键限制 / 合规 |
|----|--------|------|---------|
| **AkShare** | 开源免费,**无需 Key** | A股/港/美/期货/基金/债/宏观/加密(聚合公开源) | 本质是**爬虫**,上游改版即失效,高频被封 IP(尤其 eastmoney),**无正式授权,重分发法律灰色**;适合原型非生产 SLA |
| **Tushare Pro** | 注册免费(**积分制**) | A股(SH/SZ)/指数/基本面,部分港/美 | 120分→50/分(仅日线);500+分→500/分;实时另收;2025-08 曾停服约 1 周 |
| **Baostock** | 免费,无注册 | A股历史(日/周/分钟)+财务 | **无实时**,社区维护,稳定性一般 |
| **东方财富 (Eastmoney)** | 无官方公开免费 API | A股/港/美 | 多用**非官方端点**(AkShare 即爬此),易封、ToS 灰色;官方授权为机构定制,传 2026-03 推标准化授权服务 |
| **Futu OpenAPI**(富途/moomoo) | 免费 SDK,需账户 + FutuOpenD 网关 | **港/美/A** + 期权期货 + 交易 | 行情权限看账户地区/行情卡(部分需购卡);快照限 60 req/30s |

### 加密
| 源 | 免费层 | 覆盖 | 备注 |
|----|--------|------|------|
| **Binance API** | 免费;公共行情**免 Key**(权重限频) | 现货/合约行情、订单簿、成交;REST+**WS** | 单交易所;实时 WS 强 |
| **CoinGecko** | 公共 ~5-15/分;Demo 30/分、1万 credits/月(**需署名**) | 1.7万+币/1700+所/260+链,价/市值/历史 | 有官方 MCP;Pro ~$129/月起 |
| **CoinMarketCap** | Basic ~30/分、1万 credits/月(仅最新快照) | 跨所聚合行情 | 历史/深数据付费 |
| **Coinbase** | 免费;公共行情免 Key | Coinbase 行情;REST+WS | 单交易所 |

### 新闻 / 宏观
| 源 | 免费层 | 备注 |
|----|--------|------|
| **FRED**(美联储 St.Louis) | 免费,Key 即用 | 84万+ 宏观时序;`fredapi`/`fedfred`(异步) |
| **Finnhub News** | 随 Finnhub 免费层(公司+大盘新闻) | 情绪/社媒在付费;重分发需 Startup/Enterprise |
| **Tiingo News** | 付费/附加 | 商用需商用授权 |
| **NewsAPI.org** | Developer **仅本地/开发用,非商用**,~100/天,延迟 | 商用 ~$449/月起 |

### 🔑 合规要点(反复出现的"重分发陷阱")
对**对外/商用**看板,几乎所有免费源都**禁止重分发**:yfinance/Yahoo(仅个人)、FMP(需展示授权协议)、Twelve Data(Basic 不可展示)、Finnhub(重分发仅 Startup/Enterprise)、NewsAPI(免费非商用)、AkShare/eastmoney(爬取无授权)。**正式商用必须预算正规付费授权档。**

---

## 6. 对本平台的选型结论

结合"**数据看板 · 四市场 · Next.js+Python · 成本可控**":

1. **数据源(免费起步,多源降级)**
   - 美股/港股看板:**yfinance**(免费,仅自用)→ **Finnhub**(60/分)→ 商用切 **Polygon/付费源**。
   - A股:**AkShare**(免费)/ **Tushare**(积分);港股可叠加 **Futu OpenAPI**。
   - 加密:**Binance**(实时 WS)+ **CoinGecko**(市值/MCP)。
   - 宏观:**FRED**。
   - ⚠️ 免费源普遍**禁止商业重分发**,正式商用须采购授权。

2. **AI 层(复用 > 自研)**
   - 编排/推理用 **Claude(claude-opus-4-8)**;情绪分类用开源 **FinBERT**(便宜、可批量)。
   - 工具直接接现成 **MCP**:`financial-datasets`、`Alpha Vantage`、`CoinGecko`,减少自研。
   - 进阶研报:借鉴 **TradingAgents / AI-Hedge-Fund** 的多 Agent 辩论结构;可参考 **Anthropic 金融 Skills**(DCF/可比/财报分析)。

3. **分析能力库**:指标 **pandas-ta/TA-Lib**;回测 **VectorBT/Backtrader**;组合 **PyPortfolioOpt**;RAG 用 **pgvector**。

4. **可借鉴的产品形态**:对话式投研(Fiscal.ai/Perplexity Finance)、可解释评分(Danelfin/Kavout)、自然语言选股(同花顺问财)、研报自动生成(东方财富妙想/FinRobot)。

> 详细架构落地见 [`../docs/architecture.md`](../docs/architecture.md),实施顺序见 [`../docs/roadmap.md`](../docs/roadmap.md)。
