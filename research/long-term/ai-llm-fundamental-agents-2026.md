# 2025–2026 面向基本面/长期投资的 LLM Agent 系统盘点 — 深度研究报告

> 目的:为成熟量化/投研系统(已有 OpenClaw 外部 agent 编队 + LLM 假设工厂)盘点 2025–2026 最新的、面向**基本面/长期投资**的 LLM Agent 进展,并给出**本系统如何安全用 LLM**的可落地边界。
> 方法:多角度 fan-out 检索(框架进展 / 学术评测 / 泄漏证据 / 工程范式 / 厂商用例)→ 关键结论标一手来源 URL + 可信度(高/中/低)→ 区分真证据 vs 营销。
> 日期:2026-06-18。
> 立场(房子风格):**LLM 在非结构化文本的抽取/总结上有真价值;在数值预测/选股上证据薄弱且极易被预训练记忆污染。** 因此本系统的设计原则是:**LLM 只做抽取 + 假设生成,绝不直接决策;一切量化效力由门控验证证明,而非由 LLM 自称。**

---

## 1. TL;DR

1. **最危险的混淆:亮眼回测 = 真 alpha。** "Profit Mirage"(2510.07920, 2025-10)在**同等市场环境**下对比 LLM 交易 agent 的历史期(2021)与未来期(2024):Sharpe 衰减 51–62%、总收益衰减 50–72%,五个被测框架(FinMem/FinAgent/QuantAgent/FinCON/TradingAgents)**全部**显著退化。结论:大量"LLM 选股成功"来自预训练里见过结果+事后解释,而非因果推理。[高]

2. **"记忆即泄漏"已被多篇 2025 论文坐实。** Lopez-Lira 等《The Memorization Problem》(2504.14765)显示 LLM 能**逐字复现**历史宏观/股价数值;Gao-Jiang-Yan《A Test of Lookahead Bias》(2512.23847)提出可操作的 **LAP(Lookahead Propensity)** 检测,发现小盘股"预测力"很大程度是泄漏。**凡是测试窗落在模型知识截止之前的 LLM 选股结果,默认不可信。** [高]

3. **唯一相对可信的"数值"正面证据也有保留。** Kim-Martin-Nikolaev《Financial Statement Analysis with LLMs》(2407.17866, Chicago Booth)用**匿名化标准化报表**让 GPT-4 预测盈利方向,CoT 准确率 60.4% vs 分析师 52.7%,并称"不来自训练记忆"。但 v3 已被作者**撤回**(2025-02,原因未公开),需谨慎。即便成立,60% 方向准确率 ≠ 可盈利 alpha(见 §3)。[中]

4. **真正成熟、可直接用的是"文本→结构化"能力,不是预测。** FinanceBench(2311.11944):GPT-4-Turbo+检索在财报 QA 上**错答/拒答 81%**,闭卷仅 11%,即便 Oracle 上下文也只有 85%。这说明:RAG-over-filings 能大幅改善但远未"可信自动化",必须**强制引用 + 数值核验**。[高]

5. **厂商侧 2025–2026 是"工作流自动化"年,不是"自动选股"年。** Anthropic《Claude for Financial Services》(2025-07-15)、OpenAI×PwC(2025-05),卖点是**审计追踪 + 跨源验证 + 抽取/建模提速**(AIG 称数据准确率 75%→90%、复核提速 5x),没有任何"模型直接产 alpha"的承诺。这与本系统方向一致。[高]

6. **本系统落地结论:LLM = 抽取器 + 假设生成器 + RAG 检索器,三者全部进入门控验证管线。** LLM 产出永远是"待证伪的候选",由确定性代码做数值核对、由 Purged-CV/Deflated-Sharpe/样本外做效力证明。**LLM 不进入下单路径、不给方向票、不调仓位。**

---

## 2. 最新框架/项目盘点(2025–2026,带链接可信度)

> 说明:下表区分"**框架成熟度**"(工程是否能跑、是否活跃)与"**alpha 证据**"(是否有可信样本外收益)。绝大多数项目前者尚可、后者**无或被泄漏污染**。

### 2.1 多 agent 投研/交易框架

| 项目 | 最新进展 | 做什么 | alpha 证据 | 可信度 |
|---|---|---|---|---|
| **TradingAgents** (TauricResearch) | arxiv 2412.20138 v7(2025-06);repo 称 v0.2.0(2026-02)多模型支持 GPT-5.x/Gemini 3.x/Claude 4.x — **repo 版本号未核实** | 模拟交易公司:基本面/情绪/新闻/技术分析师 + 研究员 + 交易员 + 风控,辩论式决策 | 被 Profit Mirage 列为**泄漏退化最重之一**(总收益衰减 50%) | 框架:中｜alpha:低(已被证泄漏) |
| **FinCon** (NeurIPS 2024, 2407.06567) | 经理-分析师层级 + 概念化口头强化(verbal RL) | 多 agent 决策,带"信念"更新 | Profit Mirage 中 **Sharpe 衰减 62%(最重)** | 框架:中｜alpha:低 |
| **FinAgent** | 首个多模态(新闻+价量+K 线图) | 多模态交易 agent | 同上,退化 | 框架:中｜alpha:低 |
| **FinRobot** (AI4Finance) | 平台版 2405.14767;**股票研究/估值版 2411.08804** | 见 §2.3,Data/Concept/Thesis-CoT 产研报 | **不声称 alpha**,只评报告质量(分析师评分 9–10/10) | 框架:中-高｜定位:报告生成(诚实) |
| **GuruAgents** (2510.01664, 2025-10) | 用 prompt 编码 Buffett/Graham/Piotroski 等 5 位大师 | NASDAQ-100,季度再平衡,测试窗 Q4'23–Q2'25(**刻意在知识截止之后**) | Buffett agent 称 42.2% CAGR、Piotroski 30.9% | 方法:中(注意了泄漏)｜结果:**未独立核验**,单一短窗易过拟合 |
| **QuantaAlpha** (2602.07085) / **多 agent 投资团队**(2602.23330) / **FinWorld**(2508.02292) | 2026 新一批:演化式 alpha 挖掘、细粒度交易任务分工、端到端开源平台 | LLM 驱动因子/策略生成与编排 | 多为 in-sample 或短窗,**alpha 未核实** | 框架:中｜alpha:未核实 |

### 2.2 FinGPT / FinRobot / FinRL 进展(AI4Finance 生态)

- **FinGPT → FinRobot**:FinGPT 是单模型微调路线;FinRobot(2405.14767)是其多 agent 平台化继任,四层架构(AI Agents / Financial LLM Algorithms / LLMOps+DataOps / 多源基座)。[中｜arxiv.org/html/2405.14767v2]
- **FinRL / FinRL Contests 2025**(2504.02281;open-finance-lab.github.io/FinRL_Contest_2025):2025 赛事四任务,核心新增 **FinRL-DeepSeek** —— 用 DeepSeek-V3 从新闻/SEC filings 抽取**风险与情绪信号**,注入 RL agent;另有加密 AlphaSeek、Open FinLLM Leaderboard(ReFT/DRR)。**关键观察:这正是"LLM 做信号抽取 → 交给非 LLM 决策器"的范式,与本系统门控思路同构。** [中-高]
- **诚实评估**:FinRL 系列的价值在于**把 LLM 限制在"文本→特征"角色**,决策仍由 RL/规则承担。这是比"LLM 直接决策"更稳健的工程选择;但 RL 本身在金融上样本外稳定性差(状态非平稳),不要把它当万灵药。[中]

### 2.3 LLM 做 analyst-style 估值/研报

- **FinRobot 估值版**(2411.08804):Data-CoT(聚合 SEC/电话会/财报算 revenue growth、EBITDA、margin)→ Concept-CoT(模拟分析师推理,出营收预测、ROIC/WACC)→ Thesis-CoT(合成研报 + DCF + 买卖评级)。**评测只测报告质量**:7 位投行分析师打分 accuracy 9–10、logic 9–9.5、storytelling 7–10;GPT-4 评分与人类一致。**无任何样本外 alpha 主张。** [中-高｜定位诚实]
- **含义**:这类工作的真价值是**研报草稿/结构化推理脚手架**,把分析师从"找数+排版"里解放(行业普遍称 40–50% 产能提升,**该数字为厂商/咨询口径,未核实**)。但"评级"是 LLM 的口头输出,**不构成可回测信号**,必须落到可审计公式因子后才进入验证。

### 2.4 厂商企业级用例(Anthropic / OpenAI)

- **Claude for Financial Services**(Anthropic,2025-07-15):连接器含 **FactSet、S&P Global、Daloopa、Morningstar、PitchBook、Databricks、Snowflake、Palantir、Box**;用例为尽调/市场研究、竞品对标、带审计追踪的财务建模、投资备忘录/路演稿生成、组合监控。**卖点是跨源验证 + 每条主张链接原始来源**;AIG 称数据准确率 75%→90%、复核提速 5x+;FundamentalLabs 称 Opus 4 在复杂 Excel 任务 83% 准确。[高(为官方一手),但准确率为客户/自报口径，**未独立核验**｜anthropic.com/news/claude-for-financial-services]
- **后续**:Anthropic《Advancing/Agents for Financial Services》(2026,具体日期未核实)推出更多代理(对账、估值复核、earnings 研究、报表审计),`/earnings` 一键生成研究 note。[中｜anthropic.com/news/finance-agents]
- **OpenAI × PwC**(2025-05-06):预测、报告、treasury、税务、会计工作流的 agent;OpenAI 财务部门当"customer zero"。[中]
- **诚实评估**:两家旗舰金融产品的定位**全部是工作流自动化与抽取/核验**,无"自动产生投资收益"的承诺。这是行业最诚实的信号:**当前可货币化的是文本处理与流程提速,不是预测。**

---

## 3. 学术评测:真 alpha 还是泄漏?

> 核心问题:LLM 选股的"超额收益"是真的样本外能力,还是预训练记忆 + 事后解释的泄漏?**2025 年的证据强烈倾向后者。**

### 3.1 泄漏的直接证据(高可信度)

1. **Profit Mirage**(2510.07920,华南理工 + ByteDance,2025-10):
   - 设计巧妙——历史期(2021 Q2-Q3)vs 未来期(2024 Q3-Q4)**市场收益几乎相同**(+13.79% vs +13.35%),排除"市场更难"借口。
   - 结果:5 个 SOTA agent **全部**退化,Sharpe 衰减 51–62%、总收益衰减 50–72%。
   - 机制原话:*"the model does not learn why prices move; it learns that they already moved."*
   - 补救:FactFin 用**反事实扰动**逼模型学因果(Strategy Code Gen + RAG + MCTS + 反事实模拟器)。[高]

2. **The Memorization Problem**(2504.14765,Lopez-Lira/Tang/Zhu):LLM 能**逐字复现**训练期内的历史宏观指标与股价;预训练截止前的"预测"本质是检索。结论:**对 pre-cutoff 数据的经济预测应保持怀疑。** [高]

3. **A Test of Lookahead Bias**(2512.23847,Gao-Jiang-Yan,2025-12):
   - 提出 **LAP**(基于成员推断的"prompt 是否被训练过"代理:取最难预测 20% token 的平均概率)。
   - 在预测回归里加 `LLM预测 × LAP` 交互项,**正显著 = 记忆而非推理**。
   - 发现:小盘股的"预测力"很大程度是泄漏;corp capex 任务约 19% 来自泄漏放大。
   - 用 Llama-2 做样本外验证:**过截止日后交互效应消失**(强证据)。
   - **给从业者的建议**:不必弃用 LLM,但**对每个应用先跑 LAP 诊断**再下结论。[高]
   - **本系统直接可用**:把 LAP 类诊断纳入"LLM 衍生信号"的准入检查(见 §6)。

4. **DatedGPT / 时间感知预训练**(2603.11838)、**时序污染检测**(2602.17234):2026 出现"从零训练 leak-free 时间戳语料模型"与污染检测工具,说明学界已把泄漏当**一类系统性方法论缺陷**对待,而非个案。[中｜较新,实现成熟度未核实]

### 3.2 唯一较强的正面信号及其保留(中可信度)

- **Kim-Martin-Nikolaev**(2407.17866):匿名化标准化报表 → GPT-4 CoT 预测盈利**方向** 60.4% vs 分析师 52.7%,且作者称做了多项检验论证"非记忆"(匿名化、剥离行业/叙事正是为降低泄漏)。**这是设计上最认真对待泄漏的一篇。** 但:
  - v3 被作者**撤回**(2025-02,原因未公开)——重大保留信号。[medianama / siliconangle 二手报道]
  - 即便 60.4% 成立,**方向准确率 ≠ 可盈利 alpha**:按本系统已有结论(`quant-factor-deep-research.md` §执行摘要),方向命中率 60% 对应的截面 IC 仍需配合广度才有 IR,且交易成本/容量会侵蚀;论文的高 Sharpe 策略未必经得起 Deflated Sharpe + 真实成本。[交叉印证:高]

### 3.3 评测层面的结论

- **数值预测/选股**:净证据**薄弱且易泄漏**。任何"LLM 直接选股跑赢"的结果,默认要求:(a) 测试窗严格在知识截止后;(b) 通过 LAP / 反事实诊断;(c) 真实成本 + Deflated Sharpe。三者缺一,按营销处理。
- **非结构化文本抽取/总结/QA**:有真价值但**远未可信自动化**(FinanceBench 81% 错答)。价值在"加速 + 候选生成",不在"免核验交付"。

---

## 4. 安全用法:抽取 / RAG / 门控

### 4.1 把 LLM 钉在"文本→结构化"这个它真擅长的格子里

- **真价值区**(2025 共识):
  - **KPI / 数值抽取**:从 10-K/10-Q/电话会抽 revenue、segment、guidance、margin、回购授权、债务到期表(可用 structured generation 强制 schema,见 blog.dottxt.ai 范式)。[中-高]
  - **事件/风险抽取**:管理层语气、风险因子变化、诉讼、关联交易;FinRL-DeepSeek 即此路线。
  - **总结/对齐**:跨季对比 MD&A 措辞变化(如"多元化越多写得越含糊"的 diversification score 类信号)。
  - **知识图谱**:FinReflectKG(2508.17906)等 schema-guided 抽取,把 filings 变结构化关系。
- **绝不让 LLM 干的**:直接给方向/仓位、直接产"数值预测"当因子、在无核验下把抽取数字写进可下单管线。

### 4.2 RAG-over-filings 工程范式(2025 实践)

1. **来源受控**:只检索一手 filings(EDGAR)、电话会原文、官方 PR;**禁止开放网络**进入估值数值链(防事后解释泄漏)。
2. **强制引用 + span 级证据**:每个抽取数字必须带原文 span(FinanceBench 设计即"evidence string"),无 span 不采信。
3. **数值二次核验**:LLM 抽出的数字交给**确定性代码**做勾稽(资产=负债+权益、分部加总=合计、同比口径一致),不过则丢弃或人工复核。
4. **闭卷→开卷的硬纪律**:闭卷问数字(11% 准确)证明模型在"编";因此**任何数值必须来自检索到的 span,而非模型内部记忆**。
5. **时间戳隔离**:检索语料按 as-of 日期切片,防止把未来文档喂给"历史时点"分析(point-in-time RAG)。

### 4.3 门控验证(本系统的核心防线)

LLM 产出 → **公式化**(假设工厂只产可审计公式因子)→ 进入既有验证管线:
- Purged K-Fold + Embargo + CPCV;
- Deflated Sharpe(按试验次数 N 通缩);多重检验门槛 **t>3.0**;
- **样本必须在 LLM 知识截止之后**(否则跑 LAP/反事实诊断);
- 真实成本 + 容量约束。
**只有通过门控的因子才"上线",LLM 的自信程度对此零权重。**

---

## 5. 已知失败模式(2025–2026 实证)

| 失败模式 | 表现 | 一手证据 | 缓解 |
|---|---|---|---|
| **预训练记忆 = 前视偏差** | "预测"实为复现训练期已知结果/事后解释 | Profit Mirage 2510.07920;Memorization 2504.14765 | 测试窗在截止后;LAP 诊断;反事实扰动 |
| **幻觉数值** | 编造财报数字、勾稽不上 | FinanceBench 闭卷 11%;dottxt 警告"LLM 会发明信息" | 强制 span 引用 + 代码勾稽 |
| **检索仍错答** | 即便 RAG 仍 81% 错答/拒答 | FinanceBench 2311.11944 | Oracle/多跳检索 + 人工复核高风险问 |
| **过度自信** | 高置信但错;辩论式 agent 互相强化错误 | TradingAgents/FinCon 退化 | 置信度不进决策;门控只看样本外统计 |
| **短窗/单路径过拟合** | 单段牛市(如 NASDAQ Q4'23–Q2'25)CAGR 漂亮 | GuruAgents 42.2% CAGR(未核验,单窗) | 多窗 + CPCV + Deflated Sharpe |
| **survivorship / 口径** | 用现成成分股、未对齐会计口径 | 通用风险 | point-in-time 成分股 + 口径核验 |
| **合成/污染检测难** | 难判断某条 prompt 是否被训练过 | 2602.17234 时序污染检测 | 成员推断/LAP 类工具入准入 |
| **厂商自报准确率** | "75%→90%""83% Excel"为客户口径 | Anthropic 页面 | 内部独立基准复测 |

---

## 6. 落地到本系统(LLM 角色边界 / feed / 验证)

### 6.1 角色边界(硬约束)

- **LLM 允许的三个角色**:
  1. **抽取器**:filings/电话会/PR → 结构化 KPI + 事件(带 span,过代码勾稽)。
  2. **假设生成器**(对接现有"LLM 假设工厂"):把抽取/文本观察 → **可审计公式因子草案**(例:`Δguidance_tone × buyback_authorization_yield`),只产公式不产判断。
  3. **RAG 检索/总结器**:为人类/下游 agent 提供带引用的证据包。
- **LLM 禁止的角色**:给方向票、定仓位、产"数值预测因子"、在无核验下写数进可下单链、用自身置信度影响排序。

### 6.2 Feed(数据流)

```
EDGAR/电话会/官方PR (point-in-time, as-of 切片)
   │  禁开放网络进数值链
   ▼
LLM 抽取(强制 schema + span)──► 确定性勾稽核验 ──(失败)──► 丢弃/人工
   │ (通过)
   ▼
结构化 KPI/事件库(带 as-of 时间戳)
   │
   ├──► LLM 假设工厂 ──► 公式因子草案
   │                          │
   ▼                          ▼
特征库 ◄────────────── 门控验证管线
                       (Purged-CV/Embargo/CPCV,
                        Deflated Sharpe, t>3.0,
                        样本>知识截止 或 LAP 诊断,
                        真实成本+容量)
                              │ (通过)
                              ▼
                        上线因子(LLM 置信度=0 权重)
```

### 6.3 验证(在既有管线上加 3 个 LLM 专属门)

1. **截止日门**:任何含 LLM 衍生信号的因子,回测样本默认**严格在模型知识截止之后**;若必须用历史段,先跑 **LAP/反事实诊断**(参照 2512.23847 / FactFin),交互项显著则判定泄漏、拒绝。
2. **抽取核验门**:LLM 抽取数字 100% 过确定性勾稽 + 抽样人工复核;记录抽取错误率作为该数据源可信度权重。
3. **可证伪门**:LLM 的文本判断(如"护城河增强")**不得**直接成为信号;必须先 operationalize 成公式因子,再由门控证明,否则只作研究备注。

### 6.4 可直接借用的外部组件

- **FinRL-DeepSeek 范式**:LLM 抽风险/情绪 → 注入非 LLM 决策器(与本系统门控同构,可参考其信号注入实现)。[中]
- **FinReflectKG / structured-generation 抽取**:做 schema-guided filings 抽取的工程模板。[中]
- **LAP 诊断 / FactFin 反事实**:作为"LLM 信号准入"的标准检测件。[中-高]
- **Claude for Financial Services 连接器思路**:跨源验证 + 每条主张链接来源 = 本系统抽取层的产品化参照(自建时复刻"span 引用 + 多源勾稽")。[中]

---

## 7. 反方(诚实对冲,避免本报告自身过度自信)

1. **"泄漏论被夸大"**:Kim 等用匿名化报表后仍 60.4%,且做了非记忆检验;Profit Mirage 测的是**交易 agent**(嘈杂、含价量记忆),不直接否定"匿名报表盈利方向预测"。→ 回应:正因如此,本系统**允许**报表抽取 + 方向假设,但**仍要门控**;不因一篇撤回稿就全盘否定文本能力。

2. **"截止日后测试也会很快被污染"**:模型迭代快,今天的"样本外"几个月后就进了下一代训练集,LAP 也非完美。→ 回应:把"截止日 + LAP + 反事实"当**多重而非单一**防线;并定期用最新发布且无金融微调的开源模型做对照。

3. **"GuruAgents 这类正面结果可能是真的"**:它确实把测试窗放在截止后。→ 回应:单一短牛市窗 + 未独立复现 + 未做 Deflated Sharpe,**证据等级仅"未核实"**;欢迎复现,但在复现前不据此配置资本。

4. **"RL/多 agent 编排终会学到因果"**:FactFin 反事实、FinRL-DeepSeek 等在往这个方向走。→ 回应:方向正确,但金融状态非平稳使 RL 样本外稳定性存疑;在它跨多个独立 regime 证明前,仍按"未证实"对待。

5. **"过度保守会错过 LLM 红利"**:把 LLM 锁在抽取/假设会不会太窄?→ 回应:红利**当前确实主要在抽取/提速**(厂商产品、FinanceBench、FSA 论文一致指向);把决策权让给未证实的预测才是真正的风险。边界可随**通过门控的证据**逐步放宽,而非凭乐观放宽。

---

## 8. 参考来源(URL + 可信度)

> 可信度:高=同行评审/顶会/官方一手且方法稳健;中=arXiv 预印本/活跃开源/官方但口径自报;低=二手报道/营销/单窗未复现。

**泄漏与评测(核心证据,高优先级)**
1. Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents (2510.07920, 2025-10) — https://arxiv.org/abs/2510.07920 — **高**(设计严谨,等市场对照)
2. The Memorization Problem: Can We Trust LLMs' Economic Forecasts? (2504.14765, Lopez-Lira/Tang/Zhu) — https://arxiv.org/pdf/2504.14765 — **高**
3. A Test of Lookahead Bias in LLM Forecasts (LAP) (2512.23847, Gao/Jiang/Yan, 2025-12) — https://arxiv.org/html/2512.23847v1 — **高**
4. Financial Statement Analysis with LLMs (2407.17866, Kim/Martin/Nikolaev, Chicago Booth) — https://arxiv.org/abs/2407.17866v2 — **中**(正面证据但 v3 已撤回)
5. DatedGPT: Time-Aware Pretraining (2603.11838) — https://arxiv.org/pdf/2603.11838 — **中**(很新,实现未核实)
6. Interpretable Temporal Contamination Detection (2602.17234) — https://arxiv.org/pdf/2602.17234 — **中**

**框架/项目盘点**
7. TradingAgents (2412.20138 v7, 2025-06) — https://arxiv.org/pdf/2412.20138 ; repo https://github.com/TauricResearch/TradingAgents — **中**(v0.2.0/2026-02 版本号未核实)
8. FinCon (NeurIPS 2024, 2407.06567) — https://arxiv.org/abs/2407.06567 — **中**
9. FinRobot 平台 (2405.14767) — https://arxiv.org/html/2405.14767v2 ; repo https://github.com/ai4finance-foundation/finrobot — **中**
10. FinRobot 股票研究/估值 (2411.08804) — https://arxiv.org/html/2411.08804v1 — **中-高**(定位诚实:只评报告质量)
11. GuruAgents (2510.01664, 2025-10) — https://arxiv.org/abs/2510.01664 — **方法中 / 结果未核实**
12. FinRL Contests 2025 (2504.02281) — https://arxiv.org/html/2504.02281v4 ; https://open-finance-lab.github.io/FinRL_Contest_2025/ — **中-高**(FinRL-DeepSeek 抽取范式)
13. QuantaAlpha (2602.07085) / 多 agent 投资团队 (2602.23330) / FinWorld (2508.02292) — arxiv 同号 — **中 / alpha 未核实**

**工程范式 / 抽取 / RAG / benchmark**
14. FinanceBench (2311.11944, Patronus) — https://arxiv.org/abs/2311.11944 ; https://github.com/patronus-ai/financebench — **高**(81% 错答关键数据)
15. FinReflectKG: Agentic Financial Knowledge Graphs (2508.17906) — https://arxiv.org/pdf/2508.17906 — **中**
16. Scalable LLM framework for SEC 10-K (2409.17581) — https://arxiv.org/html/2409.17581v1 — **中**
17. Extracting Financial Data from 10-K with LLMs (structured generation) — https://blog.dottxt.ai/extracting-financial-data.html — **中**(工程实践)
18. Evaluating LLMs in Financial NLP (2507.22936) — https://www.arxiv.org/pdf/2507.22936 — **中**

**厂商用例(官方一手,但部分准确率为自报)**
19. Claude for Financial Services (Anthropic, 2025-07-15) — https://www.anthropic.com/news/claude-for-financial-services — **高(一手)/ 准确率口径未核实**
20. Agents for Financial Services (Anthropic, 2026) — https://www.anthropic.com/news/finance-agents — **中**(日期未核实)
21. OpenAI × PwC finance agents (2025-05-06) — 见 mindstudio.ai 综述 https://www.mindstudio.ai/blog/ai-agents-for-finance-anthropic-openai-enterprise — **中(二手)**

**综述/背景**
22. The New Quant: Survey of LLMs in Financial Prediction & Trading (2510.05533) — https://arxiv.org/pdf/2510.05533 — **中**
23. LLMs in Equity Markets: applications, techniques, insights (Frontiers, 2025, 84 篇综述) — https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1608365/full — **中**
24. From Deep Learning to LLMs: Survey of AI in Quantitative Investment (2503.21422) — https://arxiv.org/pdf/2503.21422 — **中**

**本系统内部交叉印证**
25. `research/quant-factor-deep-research.md` — 方向命中率↔IC 数学关系、Deflated Sharpe、t>3.0 纪律 — **高(内部已核验)**

---

*报告内凡标"未核实"者表示未能从一手来源独立确认(版本号、客户自报准确率、单窗回测结果、二手报道日期)。决策时按相应可信度折扣处理。*
