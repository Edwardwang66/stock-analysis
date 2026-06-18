# 价值投资框架的量化化与长期证据 — 深度研究报告

> 目的:为本系统的**长期(持有期数月至数年)做多**方向提供可证伪、可落地的价值因子方法论与最新净收益证据。
> 方法:5 角度并行检索(Graham / Magic Formula / F-Score / Acquirer's Multiple / intangibles-adjusted value)→ 一手来源 + 可信度标注 → 合成。
> 日期:2026-06-18。所有关键数字标注来源 URL 与可信度(高/中/低)。
> 立场(房子风格):**一切以净·扣成本收益为唯一货币;不接受"稳赚"叙事;明确标注样本内/前视/幸存者偏差;2010s 价值长期跑输是已被反复确认的事实,任何框架的历史 CAGR 都要先打这个折。**

---

## 1. TL;DR(可证伪要点)

1. **"价值长期年化 17-20%"几乎全部来自 1970-2007 的样本,且多为毛收益、不含成本/冲击/容量。** 多个独立回测显示:**2010-2023 Magic Formula 累计仅 +46% 而 S&P500 +354%**;若从 2014 起逐年比较,Magic Formula **没有一年跑赢 S&P500**(中-高可信度,多源一致)[reasonabledeviations; quant-investing]。→ 任何用 1970s-2000s 回测推销的价值策略,默认其近 10 年 alpha 已被套利/再定价吃掉,除非用 2010-2025 的扣成本数据重新证明。

2. **2007-2020 是价值的"历史性异常",2022 出现强反弹但未确立趋势反转。** AHKL(2020)记 HML 到 2020 年中 **回撤 ~54.8%、历时 13.5 年**;2022 年 Russell 1000 Value 跑赢 Growth **>20 个百分点**(中-高可信度)[AQR; Acadian; Russell via II]。→ 价值溢价"未死"但**时序极不稳定**,单押价值腿等于押再定价时点,必须与质量/动量分散。

3. **深度价值(纯便宜)在 Carlisle 的回测里优于"质量-价值"(Magic Formula):加入 ROIC 质量排名反而降低收益。** Acquirer's Multiple(EV/EBIT 最便宜十分位)1973-2017 ~**17.9%/年** vs 市场 ~10.5%;独立研究 1972-2017 三个市值域 AM 均略胜 MF(中可信度,作者自利益相关,需独立复现)[finbox; Greenbackd/Quantopian]。→ **"便宜"本身是主驱动,"质量"更多是降回撤/避坑而非加 alpha。**

4. **Piotroski F-Score 的价值不在选股而在"在便宜股里剔除价值陷阱"。** 原文 1976-1996 高低分价差 ~**23%/年**(高分组对低分组,样本内、小盘、高 B/M 子集)[Piotroski 2000];近期中国市场 2024 研究 High-Low 月度超额 ~**0.50-0.57%**(中可信度)[SSRN 5144971]。→ F-Score 是**条件过滤器**(在 value universe 内用),不是独立 alpha 源;脱离便宜股池单用 F-Score 收益弱。

5. **intangibles 是 2010s 价值失效的"会计真因"之一,扣无形资产修正 B/M 能显著缩短回撤。** AHKL 把 R&D/SG&A 资本化构造 iHML 后,价值回撤**从 13.5 年缩到 3.5 年、深度从 -54.8% 缩到 -43.0%**(中-高可信度,但方法对资本化假设敏感)[AHKL 2020; Iqbal-Rajgopal-Srivastava-Zhao, Mgmt Sci 2024]。→ 对软件/医药/品牌密集行业,**传统 B/M 系统性高估"贵",必须做 intangibles 调整或直接改用 EV/EBIT、FCF/EV 等不依赖账面净值的便宜度。**

6. **Fama-French 五因子里 HML 在加入 RMW(盈利)+CMA(投资)后"冗余"。** 这说明**裸价值因子的信息大部分可被质量/投资因子吸收**(高可信度)[FF 2015; CFA Institute 2022]。→ 本系统不应单独建"裸 HML"腿,应建**价值⊥质量**的复合腿(价值在质量上的正交残差),或直接用 Asness 式 QMJ + 价值组合。

7. **价值陷阱的量化签名是可识别的:F-Score 低(0-2)、应计高、净债务上升、ROIC 下行、股本稀释。** "便宜 + 基本面恶化"是亏损主源(中可信度)[Novy-Marx; Piotroski]。→ 在便宜度排序后,用 F-Score≥7、应计为负、债务/资产下降做**硬过滤**,而非把它们混入综合打分稀释。

8. **所有框架都要用 PIT + 防过拟合纪律重测:这些公开公式被全网回测过,极易过拟合到历史窗口。** 用 Deflated Sharpe / CSCV-PBO / t>3 复测,**默认历史毛收益要打 3-5 折**作为扣成本、扣再定价后的实盘预期(本系统纪律)。

---

## 2. 各框架定义 + 一手公式

### 2.1 Graham 防御型 / 企业型(Defensive / Enterprising)
来源:Graham《聪明的投资者》(1949/1973);AAII Graham 屏幕复刻 [aaii.com/stocks/screens/34, /35](中可信度)。

**防御型(Defensive)量化筛选**(逐条 PIT 可算):
- 规模充分(营收/市值下限,避免微盘);
- 财务稳健:流动比率 ≥ 2;长期债务 ≤ 净流动资产;
- 盈利稳定:过去 10 年每年正 EPS;
- 股息记录:连续 20 年派息(可放宽);
- 盈利增长:10 年 EPS 增长 ≥ 1/3(三年均值口径);
- 估值:**P/E ≤ 15**(取近 3 年平均 EPS);**P/B ≤ 1.5**;且 **P/E × P/B ≤ 22.5**(Graham number 隐含)。

**企业型(Enterprising)** 放宽质量、收紧便宜度:价格 ≤ **min(1.2 × 有形账面价值/股, P/E 10)**[netnethunter; netnetscanner](中可信度)。

**Net-Net / NCAV(最量化的一支)**:
- `NCAV = 流动资产 − 总负债`(忽略固定资产);
- 买入 `价格 < 2/3 × NCAV` 的股票;
- Graham 自述 30+ 只组合、持有 1-3 年再平衡,**年化 ~20%**(自述,样本内、深度小微盘、流动性极差,**幸存者/容量偏差严重** — 中-低可信度)[stablebread net-net]。

### 2.2 Greenblatt Magic Formula(质量-价值)
来源:Greenblatt《The Little Book That Beats the Market》;[reasonabledeviations 复盘](中可信度)。
- **便宜度(Earnings Yield)**:`EBIT / EV`,EV = 市值 + 净债务(+少数股东权益等);
- **质量(Return on Capital, ROC)**:`EBIT / (净营运资本 + 净固定资产)`(=有形投入资本回报,刻意不含商誉/无形);
- **方法**:对两个指标分别**排名**,排名相加,取综合排名最优的 20-30 只,等权,持有 1 年(税务优化逐月建仓);剔除金融/公用事业、极小市值。

### 2.3 Piotroski F-Score(9 项二元打分,0-9)
来源:Piotroski(2000)《Value Investing: Using Historical Financial Statement Information…》;[Wikipedia Piotroski F-score](高可信度,定义)。
**盈利性(4 分)**:① ROA>0;② 经营性现金流 CFO>0;③ ΔROA>0(同比);④ CFO/资产 > ROA(应计为负,现金质量优于账面)。
**杠杆/流动性/融资(3 分)**:⑤ 长期负债率同比下降;⑥ 流动比率同比上升;⑦ 当年未增发股本。
**经营效率(2 分)**:⑧ 毛利率同比上升;⑨ 资产周转率同比上升。
**用法**:Piotroski 在**高 B/M(便宜)子集**内,做多 F≥8、做空 F≤1。原文 1976-1996 该价差 ~**23%/年**(样本内、偏小盘)[Piotroski 2000](高可信度,原文;但样本内)。

### 2.4 Acquirer's Multiple(深度价值,Carlisle)
来源:Carlisle《Deep Value》《The Acquirer's Multiple》;[finbox; quant-investing](中可信度,作者利益相关)。
- **单一指标**:`Acquirer's Multiple = EV / 营业利润(operating earnings ≈ EBIT)`;取最便宜十分位;
- **刻意去掉质量腿**:Carlisle 实测加 ROIC 排名(即 Magic Formula 的质量项)**反而降低收益**,故纯便宜更优 [finbox/Quantopian]。

### 2.5 intangibles 调整后的价值(iHML)
来源:Arnott, Harvey, Kalesnik, Linnainmaa(2020)《Reports of Value's Death May Be Greatly Exaggerated》,Financial Analysts Journal;Iqbal-Rajgopal-Srivastava-Zhao《A Better Estimate of Internally Generated Intangible Capital》(Mgmt Sci 2024)[ssrn 3917998](中-高可信度)。
- **核心问题**:GAAP 把 R&D、广告、SG&A 中的品牌/组织资本**费用化**,导致软件/医药/消费龙头**账面净值被系统性低估**→ 传统 B/M 把它们误判为"贵"。
- **修正(知识资本 + 组织资本)**:
  - 知识资本 `KC_t = (1-δ_R)·KC_{t-1} + R&D_t`,常用 δ_R≈20%/年(行业相关);
  - 组织资本 `OC_t = (1-δ_O)·OC_{t-1} + θ·SG&A_t`,常用 θ≈20-30%、δ_O≈20%;
  - `调整后账面价值 = 报告账面价值 + KC + OC`;用 `i-book/market` 替代 `book/market` 构造 iHML。
- 资本化假设(摊销率/资本化比例)对结果**高度敏感**,这是该方法主要争议点。

---

## 3. 长期净收益 / 回撤证据(带来源可信度)

| 框架 | 样本/期间 | 收益(口径) | 回撤/失效证据 | 可信度 |
|---|---|---|---|---|
| Magic Formula | 1999-2010(原书+复刻) | ~26%/年(<2007) vs ~18% benchmark;毛收益 | 2007-2010 回撤 **57%**(SPY 55%);**beta-hedged specific return 转负**(纯 alpha 在金融危机亏钱) | 中-高 [reasonabledeviations] |
| Magic Formula | 2003-2015 | 11.4%/年(Sharpe 0.60)vs S&P 8.7%(0.54) | 优势主要来自 2003-2007 | 中 [reasonabledeviations] |
| Magic Formula | **2010-2023** | 累计 **+46%** vs S&P500 **+354%**;2014 起逐年无一年跑赢 | **决定性失效证据**:近十余年大幅跑输 | 中-高(多源一致)[Telford via reasonabledeviations; quant-investing] |
| Acquirer's Multiple | 1973-2017(美股) | 最便宜十分位 ~**17.9%/年** vs 市场 ~10.5% | 高波动、高回撤(Calmar/Sharpe 仍优于 MF) | 中(作者利益相关,需独立复现)[finbox; Greenbackd] |
| AM vs MF | 1972-2017,三市值域 | $50M:MF16.2/AM18.6;$200M:17.2/17.5;$1B:16.2/17.9 | AM 全胜但差距小;均为长样本毛收益 | 中 [finbox] |
| Piotroski F-Score | 1976-1996(原文) | 高低分价差 ~**23%/年**;在高 B/M 内 | 样本内、偏小盘、高 B/M;独立期外较弱 | 高(原文)但样本内 [Piotroski 2000] |
| Piotroski F-Score | 中国 2024 研究 | High-Low 月度超额 ~0.50-0.57%(EW/VW) | 与 B/M、短期反转结合后增强 | 中 [SSRN 5144971] |
| HML(裸价值) | 1926-2007 vs 2007-2020 | 历史 Sharpe~0.64(小盘价值溢价 0.60%/月、大盘 0.26%/月) | **2007-2020 回撤 ~54.8%、历时 13.5 年**(AHKL) | 高 [FF; AHKL 2020] |
| iHML(intangibles 调整) | 同期 | 显著优于裸 HML | 回撤缩至 **3.5 年 / -43.0%** | 中-高 [AHKL 2020] |
| 价值反弹 | 2022 | Russell 1000 Value 跑赢 Growth **>20pp** | 单年事件,未确立趋势反转 | 中-高 [Russell via II; Acadian] |

**关键失效叙事(必须内化)**:
- **2010s 是"对成长的单因子押注"**:FAANG 等巨头实际盈利高增长,价值跑输是普遍、跨地域、跨指标的(高可信度)[Acadian; GMO]。
- **Magic Formula 公式过于简单 → 易被套利**(假说,中可信度)[reasonabledeviations]。
- **裸 HML 被 RMW+CMA 吸收 → 冗余**(高可信度)[FF 2015]:价值的独立信息含量本就低于宣传。

---

## 4. 数据与可得性(免费源 / PIT)

| 需求 | 免费/低成本源 | PIT 注意 |
|---|---|---|
| 因子基准(HML/RMW/CMA/SMB/UMD) | **Kenneth French Data Library**(免费,月/日频) | 用于对标本系统价值腿是否真有增量 alpha |
| 美股基本面(EBIT/EV、ROIC、F-Score 项) | SEC EDGAR XBRL(`data.sec.gov`,免费,**财报披露日=PIT 时点**) | 必须用 `filed` 日期而非 `period` 日期对齐,杜绝前视 |
| 财务比率快照 | Financial Modeling Prep(免费档有限)、yfinance(无 PIT,慎用) | yfinance 给的是**最新重述值**,有重述/前视污染,只能做粗探 |
| 历史价格(分红调整) | Stooq、yfinance、Tiingo(免费档) | 分红/拆股调整需校验 |
| 退市/幸存者 | EDGAR + 交易所 delisting 公告;CRSP(付费) | **免费源普遍缺退市样本 → 历史回测系统性偏乐观** |
| intangibles(R&D/SG&A) | EDGAR XBRL `ResearchAndDevelopmentExpense`、`SellingGeneralAndAdministrativeExpense` | 自建 KC/OC 永续盘存,δ、θ 作为可调超参 |

**硬约束提醒**:免费源最大的坑是**幸存者偏差 + 缺乏 PIT 重述**。net-net/深度小盘策略的历史 20% 几乎无法在含退市、含流动性冲击、含税的实盘复现 — 默认大幅打折。

---

## 5. 落地到本系统(因子公式 / 数据端点 / 脚本 / 验证)

### 5.1 因子库(全部 PIT,用 EDGAR `filed` 日期对齐)
建议新增到价值长期腿(横截面排序,月度/季度再平衡):

1. **earnings_yield_ev** = `EBIT_ttm / EV`,EV = `marketcap + total_debt − cash`。EBIT 用 `OperatingIncomeLoss`(EDGAR XBRL)。
2. **acquirers_multiple** = `EV / EBIT_ttm`(取倒数即上条;保留两个口径便于对账)。
3. **fcf_yield** = `FCF_ttm / EV`,FCF = `CFO − CapEx`(对 intangibles 行业比 B/M 稳健,不依赖账面净值)。
4. **roic_tangible** = `EBIT / (净营运资本 + 净固定资产)`(Greenblatt 质量项,仅作过滤/正交,不进主排序)。
5. **f_score**(0-9):按 §2.3 九项二元逐项实现,全部用同比 PIT 财报。
6. **ihml_value**(进阶):`(报告账面 + KC + OC) / marketcap`,KC/OC 用 R&D、SG&A 永续盘存;δ_R=δ_O=20%、θ=0.25 作默认超参。

### 5.2 组合构造(基于证据的取舍)
- **主驱动用"便宜度"**:综合排序以 `earnings_yield_ev`(或 `fcf_yield`)为主,而非裸 B/M —— 因 B/M 在 intangibles 时代系统性失真(§1.5、§2.5)。
- **质量作过滤而非加权**:证据(Carlisle)显示把 ROIC 混入主排序会**降低收益**;故 `roic_tangible` 与 `f_score` 用作**硬门槛/价值陷阱过滤**(如 F≥7、应计为负、债务率下降、无大额增发),而非综合分。
- **正交化避免冗余**:价值腿对 RMW/CMA 回归取残差,确保增量 alpha 而非重复质量暴露(§1.6)。
- **与动量/质量分散**:价值与动量负相关,长期腿不要纯价值,保留价值⊥ + 趋势过滤(避免买在下跌中的便宜陷阱)。

### 5.3 脚本/端点落地草图(不在本任务实现,仅给规格)
- 拉取:`data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json`,字段取 `filed`(PIT)、`val`、`fy/fp`;tags:`OperatingIncomeLoss`、`Assets`、`Liabilities`、`AssetsCurrent`、`LiabilitiesCurrent`、`LongTermDebtNoncurrent`、`NetCashProvidedByUsedInOperatingActivities`、`ResearchAndDevelopmentExpense`、`SellingGeneralAndAdministrativeExpense`、`CommonStockSharesOutstanding`。
- 价格/市值:复用本系统现有价格管道(Stooq/yfinance);EV 用建仓日市值。
- 因子计算落到现有因子框架(参见 `research/quant-factor-deep-research.md` 的 IC/RankIC/分层评估流程)。

### 5.4 验证方法(套用本系统现有纪律)
- **PIT 对齐审计**:断言每个因子值的 `as_of` ≥ 对应财报 `filed` 日;随机抽样人工核对杜绝前视。
- **分层回测**:十分位 spread + **换手率 + 成本/冲击**;价值长期腿换手低是优势,但小盘深度价值冲击成本高,需建容量上限。
- **防过拟合**:Deflated Sharpe(按试验次数通缩)、CSCV-PBO、**t>3** 门槛;记录所有回测次数。
- **稳健子样本**:必须单独报告 **2010-2020 子窗**(价值最差期)和 **2021-2025 子窗**的扣成本表现 —— 若策略只在 1970-2007 有效,视为失效。
- **对标 French HML/RMW/CMA**:回归取 alpha,确认是真增量而非重复经典因子。
- **退市/幸存者修正**:显式纳入退市样本或对缺失打保守折扣。

---

## 6. 风险与反方观点

1. **价值溢价可能已结构性衰减**:McLean-Pontiff 类研究显示公开异象在发表后收益普遍下降;Magic Formula 这类"全网公式"被套利风险最高。本系统应预期**实盘 alpha << 历史毛收益**。
2. **裸价值因子冗余(FF 2015)**:若 RMW+CMA 已吸收 HML,单独价值腿增量有限 —— 反对"只做价值"。
3. **intangibles 调整是双刃**:iHML 改善回撤的结论**对 δ/θ/资本化假设敏感**,有研究者认为这接近"用未来知识倒推参数",存在数据窥探风险(中可信度,争议存在)。需用多组参数做稳健性,不可只报最优。
4. **深度价值的高波动/高回撤**:AM 收益高但回撤大、且 2007-2010 beta-hedged 转负 —— 在危机中价值腿与市场同跌,**分散作用在最需要时失效**。
5. **net-net/小盘的容量与幸存者陷阱**:Graham 自述 20% 几乎不可实盘复现 —— 流动性、税、退市偏差三重打击。
6. **2022 反弹 ≠ 趋势反转**:单年事件;利率/通胀环境一旦再转,价值可能重回跑输。不应据单年押注。
7. **F-Score 期外衰减**:原文 23%/年是样本内、小盘、高 B/M 三重条件;脱离该子集单用 F-Score,收益弱(中可信度)。

---

## 7. 参考来源清单(URL + 可信度)

**框架定义/复盘**
- Magic Formula 批判性复盘(含 2003-2015、2007-2010 回撤 57%、specific return 转负):https://reasonabledeviations.com/2020/06/08/greenblatt-magic-formula/ — 中-高
- Magic Formula 2000-2022 回测:https://www.quant-investing.com/blog/magic-formula-performance-backtest-2000-2022 — 中
- Magic Formula 投资策略方法/回测:https://www.quantifiedstrategies.com/the-magic-formula-strategy/ — 中
- Magic Formula(Wikipedia,定义):https://en.wikipedia.org/wiki/Magic_formula_investing — 中
- Acquirer's Multiple 回测(1973-2017 ~17.9%,vs MF):https://finbox.com/blog/what-is-the-acquirers-multiple-review-performance-backtest/ — 中
- AM 深度价值指标说明:https://www.quant-investing.com/blog/acquirers-multiple-deep-value-metric-explained — 中
- Quantopian AM vs Magic Formula 对比:https://greenbackd.com/2015/04/07/is-simpler-better-quantopian-tests-the-acquirers-multiple-and-joel-greenblatts-magic-formula/ — 中
- Piotroski F-Score 九项定义(Wikipedia):https://en.wikipedia.org/wiki/Piotroski_F-score — 高(定义)
- Piotroski F-Score 完整指南/回测:https://www.quant-investing.com/blog/piotroski-f-score-complete-guide — 中
- Piotroski F-Score 中国市场 2024(SSRN):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5144971 — 中
- F-Score 神经网络方法(ScienceDirect):https://www.sciencedirect.com/science/article/pii/S1544612319304660 — 中
- Graham 防御型屏幕(AAII,非公用):https://www.aaii.com/stocks/screens/34 — 中
- Graham 防御型屏幕(AAII,公用):https://www.aaii.com/stocks/screens/35 — 中
- Graham 企业型 / net-net 筛选:https://www.netnethunter.com/benjamin-graham-stock-screener/ — 中
- 防御型 vs 企业型说明:https://netnetscanner.com/resources/guides/defensive-vs-enterprising-graham — 中
- net-net / NCAV 估值方法:https://stablebread.com/net-net-stock-valuation/ — 中

**价值溢价宏观/失效与反弹**
- AQR《Is (Systematic) Value Investing Dead?》:https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead — 高
- AQR《Deep Value》(Asness-Liew-Pedersen-Thapar, SSRN):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3076181 — 高
- AQR《Building a Better Deep Value Portfolio》:https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/AQR-Building-a-Better-Deep-Value-Portfolio.pdf — 高
- Acadian《Growth Versus Value: End of an Era?》:https://www.acadian-asset.com/investment-insights/equities/growth-versus-value-end-of-an-era — 中-高
- GMO《Beyond the Factor》价值方法:https://www.gmo.com/americas/research-library/beyond-the-factor-gmos-approach-to-value-investing_whitepaper/ — 中-高
- J.P. Morgan 价值 vs 成长历史:https://am.jpmorgan.com/ch/en/asset-management/adv/insights/value-vs-growth-investing/ — 中
- Institutional Investor:Asness 为价值辩护:https://www.institutionalinvestor.com/article/b1qw90rfmpxmd0/Cliff-Asness-Has-Once-Again-Come-to-Value-s-Defense — 中

**intangibles / 因子结构**
- Arnott-Harvey-Kalesnik-Linnainmaa《Reports of Value's Death…》(FAJ 2020):https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1842704 — 中-高(WebFetch 被 403,数字取自检索摘要,**部分未独立核实**)
- Harvey 版 PDF(Duke):https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf — 中-高
- Iqbal-Rajgopal-Srivastava-Zhao《A Better Estimate of Internally Generated Intangible Capital》(Mgmt Sci 2024, SSRN):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3917998 — 中-高
- Sparkline Capital《Investing in the Intangible Economy》:https://www.sparklinecapital.com/post/investing-in-the-intangible-economy — 中
- Fama-French 五因子模型(HML 冗余讨论,CFA Institute):https://rpc.cfainstitute.org/blogs/enterprising-investor/2022/fama-and-french-the-five-factor-model-revisited — 高
- Novy-Marx《The Quality Dimension of Value Investing》(质量过滤价值陷阱):https://www.ivey.uwo.ca/media/3775548/novy-marx.pdf — 高

**数据源**
- Kenneth French Data Library(HML/RMW/CMA 等,免费):https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html — 高
- SEC EDGAR XBRL API(PIT 基本面,免费):https://www.sec.gov/edgar/sec-api-documentation — 高

---

**未核实/需独立复现清单**:
- AHKL iHML 具体数字(13.5y→3.5y、-54.8%→-43.0%)取自检索摘要,原文 WebFetch 403,**未独立核实**,落地前应取 Duke PDF 原文校对。
- Carlisle AM 的 17.9%/年与 AM>MF 结论来自作者利益相关方,**需用本系统 PIT 数据独立复现**。
- 所有历史 CAGR 均为毛收益、多含幸存者偏差;实盘扣成本预期应大幅下调。
