# 07 · 榜单第 7 名(TS / 「Open」+ O 图标)调研

> 调研日期:2026-06-19 · 调研对象:榜单第 7 名,标注 ~4.2k stars / TypeScript / 覆盖股票·商品·外汇·加密 / 名称以「Open」开头 / 图标为字母 O
> 诚实纪律:每条关键结论标【来源 + 可信度】;张冠李戴风险已显式说明;无法核实处标「未核实」。

---

## 一、仓库定位(含候选与确认难度)

榜单线索(TS、「Open」开头、O 图标、覆盖股票/商品/外汇/加密)与 **OpenBB 主仓不符**——OpenBB 主仓是 Python,不是 TS。榜单大概率张冠李戴或把 OpenBB 当成"心理锚点"误标。逐一核对候选后,最匹配的是 **OpenAlice**。

| 候选 | 仓库 | Star | 语言 | 资产覆盖 | 与线索匹配度 |
|---|---|---|---|---|---|
| **OpenAlice(最可能)** | `TraderAlice/OpenAlice` | **5.4k** | **TypeScript 82%**(+Python 15%) | 股票/加密/商品/外汇/宏观 ✅ | **高**:Open 开头、O 图标、四类资产精确命中 |
| OpenBB(被误标的锚点) | `OpenBB-finance/OpenBB` | 69.4k | **Python 100%** | 全资产类 | 低:语言/star 全不符,几乎确定不是它 |
| NoFx | `NoFxAiOS/nofx` | 12.5k | **Go 68%** | 美股/商品/外汇/加密 | 低:语言是 Go、非 Open 开头 |

**最可能者:`TraderAlice/OpenAlice`**
- URL:https://github.com/TraderAlice/OpenAlice 【来源:GitHub 仓库页;可信度:高】
- 作者/组织:**TraderAlice**(同名官网 traderalice.com) 【来源:GitHub + traderalice.com;可信度:高】
- Star:**5.4k**(榜单标 ~4.2k——差值与"榜单为早期快照、项目仍在涨"一致,非矛盾) 【来源:GitHub 仓库页 + trendshift.io/repositories/22556;可信度:中-高】
- License:**AGPL-3.0** 【来源:GitHub;可信度:高】
- 语言:**TypeScript 82.4% / Python 15.3%**——TS 主体成立 ✅ 【来源:GitHub 语言条;可信度:高】
- 标语:"Your one-person Wall Street. An AI trading agent covering equities, crypto, commodities, forex, and macro." 【来源:README;可信度:高】

**确认难度:中。** 仓库本身高可信(真实代码、1300+ commit、32 release、monorepo)。残余不确定性仅在"榜单原始条目→具体仓库"的映射:榜单未给 URL,我是按线索反推。star 数 4.2k vs 5.4k 的差异未能用榜单原始快照精确核对——**标:映射关系「中度确认」,star 时点差异「未核实」**。

> ⚠️ **张冠李戴风险(必须明说)**:此领域近期涌现一批「Open*」/「*Claw」TS-AI 交易仓(OpenAlice、OpenFinClaw、TradeClaw、StockKit 等),营销文案高度雷同、作者多为新账号。OpenAlice 代码实体可验证、相对扎实,但整个赛道有"刷榜/AI 生成 README"嫌疑,引用其 star/trending 数据时应保留折扣。

---

## 二、架构与定位

**定位**:**自托管的"单人华尔街"AI 交易 Agent**——不是纯数据终端,而是「研究 → 建仓 → 持仓管理 → 离场」全生命周期的**可实盘 Agent**(强调跑在用户本机,因涉及私钥与真金白银)。 【来源:README;可信度:高】

**双进程 monorepo(pnpm + Turborepo)** 【来源:README/docs;可信度:高】
- **Alice 进程**:Agent 运行时 + 研究域(行情/分析/新闻)+ 工作区启动器 + Web UI / Inbox / MCP Server。
- **UTA 服务(Unified Trading Account)**:券商连接、交易状态机、**Guard 守卫流水线**、FX、快照。**刻意与券商凭证隔离**,Alice 仅通过 HTTP SDK 访问——类比"硬件钱包"分层。

**AI 能力(模式很有意思)** 【来源:README + docs;可信度:中-高】
- **不在进程内跑 LLM**:模型循环跑在原生 Agent CLI 内(`claude`/`codex`/`opencode`/`pi`/`shell`),多 provider(Anthropic/OpenAI/Google/DeepSeek/GLM/Kimi 等)经凭证保险库注入。
- **工作区即基底**:每个任务 = 一个目录 + git repo + 持久 PTY 会话 + 注入的 MCP 工具;cron 可派生 headless 工作区,经 Inbox 推送回报。
- **Trading-as-Git(TaG)**:暂存订单 → commit(带 message)→ push 执行;push 触发 guards、派发券商、快照账户、记 8 位 hash——把"AI 交易黑箱"变成可审计的版本历史。 【来源:README + traderalice.com/blog/trading-as-git-intro;可信度:中】

**数据/feed**:TraderHub 托管低频数据(宏观板、movers、财报历、Fed、航运指数、期限结构、板块轮动;FRED/EIA/BLS/FMP/FX);新闻为后台 RSS 采集 + 归档检索;默认零 API key,Hub 不可用时回退到用户自带 key。payload **显式打 staleness + 来源戳(hub/local)**。 【来源:README;可信度:中-高】

---

## 三、可信度

- **开源投研终端 vs 真交易**:**真交易**(接 CCXT/Alpaca/IBKR/Longbridge,有下单、guard、快照),不是只读终端。 【来源:README;可信度:高】
- **业绩主张**:**未发现任何收益/胜率主张**。文档反复强调实验性、"无正确性/可靠性/盈利性保证、不担责"。这与本系统"诚实可证伪、反炒作"取向高度一致。 【来源:README caution box;可信度:高】
  > "Do not use this software for live trading with real funds unless you fully understand and accept the risks involved. The authors provide no guarantees of correctness, reliability, or profitability…"
- **诚实工程信号**:数据 payload 带 staleness/来源戳;Hub 被定义为"便利层而非正确性依赖";券商凭证与 Agent 隔离。这些是正向可信信号。 【来源:README/docs;可信度:中-高】
- **折扣项**:作者为相对新账号、所属"Open*-AI-trading"赛道整体有刷榜嫌疑;trending/star 增长曲线**未核实**是否自然。实盘安全性、guard 实际有效性**未核实**(未读源码级验证)。

**净评:代码与文档层面可信度「中-高」,营销/star 真实性「中」,实盘安全性「未核实」。**

---

## 四、对我们系统(Next.js/TS 前端 + Python 后端 + feed)的可借鉴

1. **数据 payload 带「来源戳 + staleness」**(hub/local + 新鲜度):直接契合本系统"诚实可证伪"——前端看板每条指标都能显示"数据多旧、来自哪个源",可证伪、可降级。**强烈建议借鉴。**
2. **"便利层 vs 正确性依赖"二分**:把托管聚合数据明确标为便利层、可回退到自带 key 的源——避免单点 feed 成为隐性正确性依赖。适配本系统的 feed 层设计。
3. **凭证/执行与 Agent 隔离(UTA 模式)**:研究/AI 层 ⟷ 敏感凭证层经受限 HTTP SDK 通信。即便本系统暂不实盘,把"Python 后端持密钥、TS 前端/Agent 只经窄接口访问"做成硬边界,是好安全姿势。
4. **AI 助手"工作区即基底"**:任务 = 目录 + git + 持久会话 + MCP 工具注入;可审计、可重放。本系统 AI 助手若要"可解释/可回溯",这是比"无状态 chat"更强的模式。
5. **Trading-as-Git 的可审计 commit 历史**:即便只做投研建议,把"每条 AI 决策/调仓建议"落成带 message 的版本历史,天然支持事后复盘与证伪。
6. **前端 TS 栈参照**:OpenAlice 用 **React + Vite**,本系统用 **Next.js**——前端聚合/看板模式可借鉴,但其"原生 CLI vendor TUI、无协议 shim"路线与 Web 看板不同,**不直接套用**。MCP Server 暴露研究工具的做法可借鉴。
7. **Zod 校验贯穿数据边界**(README 提及):TS 侧对 feed/AI 输出做 schema 校验,与本系统前后端契约一致性诉求吻合。

---

## 一句话定位

**OpenAlice(`TraderAlice/OpenAlice`)= 自托管、反炒作、可审计(Trading-as-Git)的「单人华尔街」TS-AI 交易 Agent;最匹配榜单第 7 名,但榜单把它与 Python 的 OpenBB 混为一谈系张冠李戴;其「来源戳 + 凭证隔离 + 工作区即基底」三点最值得本系统借鉴,star/营销真实性需打折。**
