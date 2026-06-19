# 01 · TradingAgents(Tauric Research)调研

> 调研日期:2026-06-19 · 调研纪律:每条关键结论标**一手来源 + 可信度**;区分「真证据」与「营销叙事」;star 多 ≠ 能赚钱;无法核实标「未核实」。

## 一句话定位
学术界曝光度最高的「多 agent LLM 模拟交易公司」开源框架(架构编排值得借鉴,**业绩证据极弱**):公开实测只有 3 只票、3 个月、未扣成本的自报回测,且已被第三方论文证明业绩主要来自 LLM 训练集泄漏——属于**强营销叙事 + 弱因果证据**,严禁照搬其「让 LLM 直接下决策」的范式。

---

## 1. 仓库事实

| 项目 | 内容 | 来源 / 可信度 |
|---|---|---|
| 真实仓库 URL | `https://github.com/TauricResearch/TradingAgents` | [GitHub](https://github.com/TauricResearch/TradingAgents) · 高 |
| 作者/组织 | Tauric Research(论文作者:Yijia Xiao, Edward Sun, Di Luo, Wei Wang;含 UCLA/MIT 背景) | [arXiv 2412.20138](https://arxiv.org/abs/2412.20138) · 高 |
| **Star 数核实** | GitHub 页面显示 **~87.4k stars / 16.9k forks**。**榜单标 ~78k 偏低**(榜单可能为旧快照);两者均为「热度」指标,**与盈利能力无关**。GitHub API 二次核验本次被限流,未拿到精确数字 → 量级核实为「高」,精确值「中」 | [GitHub](https://github.com/TauricResearch/TradingAgents) · 中-高 |
| License | **Apache-2.0**(商用友好) | [GitHub](https://github.com/TauricResearch/TradingAgents) · 高 |
| 活跃度 | 活跃维护:v0.2.5 于 **2026-05-11** 发布,主分支约 229 commits;近期加多 LLM 供应商、Docker、checkpoint 续跑、决策日志 | [Releases](https://github.com/TauricResearch/TradingAgents/releases) · 高 |
| 语言 | Python 99.9%,编排基于 **LangGraph** | [GitHub](https://github.com/TauricResearch/TradingAgents) · 高 |

---

## 2. 架构(这是它最有价值的部分)

模拟「真实交易公司」的分工流水线,LangGraph 编排,可配置辩论轮数:

1. **分析师团队(Analyst Team)** — 4 类并行:基本面(财报)、情绪(社媒)、新闻、技术面(MACD/RSI 等指标)。
2. **研究员团队(Researcher Team)** — **Bull vs Bear 结构化辩论**,对分析师结论做多空对抗审查,平衡收益与风险。
3. **交易员(Trader Agent)** — 汇总上游报告,决定方向、时机与仓位。
4. **风控 + 组合经理(Risk Mgmt / Portfolio Manager)** — 最终审批,通过后下单到**模拟交易所(paper trading,非真盘)**。

- **LLM**:论文版用「深思模型」(o1-preview,给分析/研究/交易)+「快思模型」(gpt-4o / gpt-4o-mini,给摘要/取数)的**双速分层**。仓库现支持 OpenAI/Gemini/Claude/Grok/DeepSeek/Qwen/GLM/MiniMax/Ollama/Azure/Bedrock 等多供应商。
- **数据源**:Yahoo Finance、Alpha Vantage、StockTwits、Reddit、新闻头条、宏观指标。
- **回测**:仓库含 backtester(声称有日期保真、跨标的 alpha 对标)。
- 来源:[README](https://github.com/TauricResearch/TradingAgents/blob/main/README.md) / [arXiv html v3](https://arxiv.org/html/2412.20138v3) · 高。

---

## 3. 业绩与可信度(关键:证据弱)

**有学术论文**:arXiv 2412.20138,2024-12-28 首发,迭代至 v7(2025-06-03)。[arXiv](https://arxiv.org/abs/2412.20138) · 高。

**论文自报回测(营销叙事,非可信业绩)**:
- 样本极小:仅 **AAPL / GOOGL / AMZN 三只票**,区间 **2024-01-01 ~ 2024-03-29(约 3 个月)**。
- 自报数字:CR 23–27%、**Sharpe 5.6–8.2**、MDD <2.2%,声称碾压 Buy-&-Hold/MACD/KDJ&RSI/SMA 等基线。
- 来源:[arXiv html v3](https://arxiv.org/html/2412.20138v3) · 高(数字本身),但**作为业绩证据可信度低**。

**为什么这些数字不可信(真证据)**:
- **未扣交易成本**:论文未提手续费/滑点纳入,Sharpe 8 在扣成本/高换手下基本不可复制。可信度 中(基于论文未披露)。
- **样本外性存疑 + 已被独立证伪**:第三方论文 **「Profit Mirage」(arXiv 2510.07920)** 直接评测 TradingAgents,发现把测试期从 LLM 知识窗内(2021)移到发布后(2024 Q3–Q4)时,**Sharpe 衰减 55.68%、总收益衰减 50.18%**;并量化其对真实输入不敏感(预测一致性 0.69、输入依赖分仅 0.38)——即业绩很大程度来自 **LLM 记忆训练集中的事后价格解释**,而非因果推理(「模型没学会价格为何动,只记住了它已经动过」)。[arXiv 2510.07920](https://arxiv.org/abs/2510.07920) / [html](https://arxiv.org/html/2510.07920v1) · 高。
- 多篇综述将其与 FinMem/FinAgent/QuantAgent/FinCON 并列,普遍发现**泛化/前向测试时业绩显著掉落**。[The New Quant 综述](https://arxiv.org/pdf/2510.05533) · 中。

**已知失败模式**:① 前视/数据泄漏(新闻时间戳=发布时间≠可执行时间);② LLM 记忆训练集(post-hoc 价格解释);③ 过度自信(对输入扰动近乎无反应);④ 小样本 + 短窗 + 牛市区间挑选;⑤ 非确定性(温度/模型选择致结果不可复现,仓库自己声明「回测不保证复现」)。

**官方免责**:README 明确「仅供研究,非投资建议,回测不保证匹配任何已公布数字」——这点诚实,值得肯定。[README](https://github.com/TauricResearch/TradingAgents/blob/main/README.md) · 高。

---

## 4. 对我们系统的取舍

### 可借鉴(架构/工程模式,非结论)
- **角色分工流水线**:分析师→研究员→交易员→风控的分层编排,与我们 **OpenClaw 外部 agent 编队** 同构,可作为编排参考。
- **Bull/Bear 结构化对抗辩论**:强制多空双向举证,天然抗确认偏误——可移植为我们**假设工厂**的「红队/蓝队」审计环节(产出可审计论点,而非直接决策)。
- **双速 LLM 分层**(深思做推理 / 快思做取数摘要)= 成本/延迟优化,直接可用。
- **LangGraph 模块化编排 + checkpoint 续跑 + 决策日志(带结果回溯反思)**:工程上成熟,值得参考其状态机/可恢复设计。
- **多供应商 LLM 抽象层 + Docker**:降耦合,工程卫生好。

### 必须避免(踩雷点)
- **让 LLM 直接产出买卖决策/下单** ← 本框架核心范式,正是 Profit Mirage 证伪的泄漏/过度自信重灾区。我们的纪律应坚守:**LLM 只产可审计的公式因子、不做决策**,决策交给缠论/统计套利等可证伪引擎。
- **不要把它的自报 Sharpe/收益当 benchmark**:未扣成本、3 票 3 月、样本外掉一半。
- **避免无 point-in-time 隔离的 LLM 取数**:新闻/社媒时间戳必须按可执行时点对齐,否则继承其前视偏差。
- **避免非确定性进入交易路径**:温度致结果不可复现,与「诚实可证伪」相悖。

---

## 附:来源清单
- 仓库:https://github.com/TauricResearch/TradingAgents · https://github.com/TauricResearch/TradingAgents/blob/main/README.md · https://github.com/TauricResearch/TradingAgents/releases
- 原论文:https://arxiv.org/abs/2412.20138 · https://arxiv.org/html/2412.20138v3
- 独立证伪(泄漏):https://arxiv.org/abs/2510.07920 · https://arxiv.org/html/2510.07920v1
- 综述背景:https://arxiv.org/pdf/2510.05533

**未核实项**:GitHub API 精确 star/commit 数(本次限流,仅以页面显示量级 ~87.4k 为准);论文是否在某些版本补充扣成本结果(已查 v3 未见,其他版本未逐一核实)。
