# 06 · QuantDinger 调研

> 调研日期 2026-06-19 · 诚实纪律:每条关键结论标 一手来源 + 可信度(高/中/低);star 高 ≠ 能赚;无法核实标「未核实」。

## 一、仓库事实(确认难度:中——名称同名分叉多,主仓需甄别)

- **主仓库**:`https://github.com/brokermr810/QuantDinger`(可信度:高)。榜单拼写「QuantDinger」准确,无拼写出入。
- **存在多个同名/镜像/fork**,易混淆:`MantisWare/quantdinger`、`jouer50/quantdinger`、SourceForge 镜像 `quantdinger.mirror`。这些应视为镜像/分叉,**非原始上游**(可信度:中)。研判时务必锁定 `brokermr810` 为上游。
- **Star 数**:OSS Insight 计 **6,384 stars / 1,388 forks**(2026-06,可信度:高);GitHub 仓库页抓取显示 8.3k stars / 1.8k forks(可信度:中,可能含缓存/四舍五入差异)。**榜单「~6.2k」基本准确**;真实区间约 6.4k–8.3k,以 OSS Insight 6.4k 为保守基准。
- **License**:后端 **Apache-2.0**;**前端为 source-available**,非自由软件——「个人/合规非商业免费,商业部署需授权」(可信度:高)。这点常被忽略,**不是纯开源**。
- **语言**:Python 99.4%;后端 Flask/Gunicorn,前端 Vue.js(可信度:高)。
- **项目语言/出身**:**英文为主**,README 以英文营销文案撰写,**附中文译本** `docs/README_CN.md`。作者疑似中文背景但项目对外定位国际化(可信度:中)。
- **活跃度**:最新 v4.0.1 发布 2026-06-18(调研前一天);约 400 commits(可信度:高)。提交活跃但**历史短**。
- **作者画像**:`brokermr810` 为**新账号**(User ID 2.2 亿级,2025+ 注册),148 followers,仅 4 个仓库且全部围绕 QuantDinger,**疑似为产品发布/营销专设账号**(可信度:中)。无长期开发者履历背书。
- **Star 增长是否自然**:未能从 OSS Insight 取得逐日增长曲线,**「未核实」**。结合「新营销账号 + 高 fork 比(fork/star≈0.22 偏高)+ 强 CTA 求 star」,**需对 star 真实性持保留**(可信度:低,提示而非定论)。

## 二、架构

整体定位:**自托管(self-hosted)、local-first 的 AI 量化基础设施**,用 Docker Compose(PostgreSQL 16 + Redis 7)部署。

- **数据层**:Postgres 存策略/订单/审计日志,Redis 做缓存与 worker 协调。行情源 Yahoo Finance、Finnhub、Twelve Data、CCXT(可信度:高)。
- **因子/信号**:行情先过 indicator/signal 层再进策略引擎。**注意:无独立的因子研究/特征工程框架**,偏技术指标与情绪分析,非基本面多因子(可信度:中)。
- **策略运行时(两种)**:
  - `IndicatorStrategy`——DataFrame 向量化、出 buy/sell 信号、带图表,偏研究/可视化原型。
  - `ScriptStrategy`——事件驱动 `on_init()/on_bar()` + `ctx.buy()/ctx.sell()`,偏有状态实盘逻辑。
- **回测**:服务端回测,出回撤、成交日志等(可信度:高)。**未见样本外/walk-forward、滑点冲击建模细节**。
- **实盘执行**:后台 worker 按 venue adapter 分发订单(CCXT 加密 / IBKR / MT5 / Alpaca),含重试与健康检查。**研究与实盘代码路径隔离**,需显式 promote 才上实盘资金(设计上是加分项)。
- **多 Agent 部分**:核心是 **Agent Gateway (`/api/agent/v1`) + `quantdinger-mcp`(PyPI,MCP server)**,把平台能力包成 MCP 工具(约 26 个 scoped tools)供 **Cursor / Claude Code / Codex** 调用做回测、workspace 管理、分析。**安全默认**:agent token 默认 paper-only,实盘需 token `paper_only=false` 且服务端 `AGENT_LIVE_TRADING_ENABLED=true`,且 append-only 审计。**这是「让外部 AI agent 操作平台」,而非内置一支自研多 agent 投研团队**(可信度:高)。
- **「多 agent 研究」实质**:文档主要是 **multi-LLM 协同/ensemble + 置信度校准 + NL→指标/策略 代码生成**,并非独立的、有分工角色的研究 agent 团队(对比 TradingAgents 那类)。**营销叙述 > 已证实的 agent 协作深度**(可信度:中)。
- **LLM**:provider 可配——OpenAI、Claude、Gemini、DeepSeek、Grok、OpenRouter、AtlasCloud,支持本地 LLM,按查询切换或 ensemble 投票(可信度:高)。无强绑定单一模型。
- **覆盖市场**:加密(10+ 交易所)、美股/ETF(IBKR/Alpaca)、外汇(MT5/OANDA);官网另称支持 SSE/SZSE/HKEX 及期货(CME/COMEX/CBOT)——但 **A股(沪深)支持在 README_CN 中并无具体数据源与落地说明**,疑为官网营销侧的宽泛列举(可信度:中,A股支持「未核实/存疑」)。

## 三、可信度

- **真实样本外业绩**:**无**。仓库/官网仅展示 demo 持仓(Grid ETH、DCA BTC),明确为示意,**无独立审计、无 track record**(可信度:高)。
- **平台自带免责**:明示「过往/回测/模拟结果不预示未来」,且「不提供投资建议,合规与风险自负」,贡献者免责交易亏损/服务中断/监管处罚(可信度:高)。
- **已知问题/红旗**:① 引导管理员**默认密码 `123456`**,README 自承生产不安全;② 前端非自由许可,商用需授权易踩坑;③ 作者为新营销账号、强 CTA 求 star,**star 高 ≠ 经得起实盘**;④ 历史短(~400 commits)。
- **A股数据合规**:README_CN **未给出任何 A股数据来源与合规说明**。若有人真用其接 A股,需自行解决行情数据牌照/合规——平台无背书(可信度:高,即「不支持或刻意回避」)。
- **总体**:工程完成度看似不低(可部署、有审计、研究/实盘隔离),但**「能赚钱」的证据为零**;属于**基础设施 + 营销**,而非已验证策略。

## 四、可借鉴(对我们已有「因子研究+回测+feed+多市场」系统)

1. **研究/实盘代码路径强隔离 + 显式 promote 机制**:值得借鉴的工程纪律,降低「研究误触实盘资金」风险。
2. **MCP / Agent Gateway 模式**:把回测、workspace、分析封装成 **scoped MCP 工具**,让 Claude Code/Cursor 等外部 agent 受控操作,**默认 paper-only + 双开关 + append-only 审计**——这套「最小权限 + 审计」是我们若要接入 AI agent 时可直接照搬的安全范式。
3. **两档策略运行时**(向量化研究态 `IndicatorStrategy` vs 事件驱动实盘态 `ScriptStrategy`)的分层抽象,对统一「研究→实盘」迁移有参考价值。
4. **multi-LLM ensemble + 置信度校准** 作为信号增强的工程封装(provider 可插拔),可作为我们 LLM 辅助层的接口设计参考。
5. **反面教训**:不要用「star/营销叙述」替代样本外验证;前端许可这类「source-available 伪开源」陷阱需在选型清单中明确标注。

## 五、一句话定位

> QuantDinger 是一套**英文为主、Apache 后端 + 限制性前端**的自托管 AI 量化**基础设施**(加密为主、美股/外汇次之、A股存疑),亮点在 **MCP/Agent Gateway 让外部 AI agent 受控操作交易栈**;但**「多 agent 研究」营销大于实证、零样本外业绩、作者系新营销账号**——可借鉴其工程范式(研究/实盘隔离、最小权限 MCP),**不可据 star 数推断盈利能力**。

---
### 来源
- 主仓库 README/元数据:`https://github.com/brokermr810/QuantDinger`(高)
- 中文 README:`https://github.com/brokermr810/QuantDinger/blob/main/docs/README_CN.md`(高)
- Star/活跃度核实:`https://ossinsight.io/analyze/brokermr810/QuantDinger`(6,384 stars,高)
- 作者画像:`https://github.com/brokermr810`(中)
- 官网(市场/LLM/定价,营销侧):`https://www.quantdinger.com/`(中)
- 同名分叉/镜像(混淆提示):`https://github.com/MantisWare/quantdinger`、`https://github.com/jouer50/quantdinger`、`https://sourceforge.net/projects/quantdinger.mirror/`(中)
