# 国际与新兴市场分散(长期) — 深度研究

> 目的:为**长期 buy-and-hold / 多市场配置**评估国际与新兴市场(EM)分散的真实价值。系统覆盖美/港/A/加密。
> 方法:fan-out 检索一手文献 + 机构研究 → 关键数字标来源 URL 与可信度(高/中/低)→ 落地到本系统(多市场配置 / 脚本 / 验证)。
> 立场(房子风格):**净·扣成本是唯一货币**;诚实可证伪;标注前视/幸存者偏差;无法核实标"未核实"。优先 2023-2026 与免费/PIT 数据。
> 日期:2026-06-18。
> 范围硬约束:只写本文件,不改其他文件,不跑 git,不 commit/push。

---

## 1) TL;DR

1. **国际分散降低单国尾部风险,但几何收益提升有限,且在危机中相关性上升而"在最需要时失灵"。** 这是诚实的双面结论:分散是"免费午餐"主要体现在**降低单国崩盘/失落十年的灾难性风险**,而非系统性提高复合收益。[高]

2. **本土偏好(home bias)有真实代价,但"最优国内权重"远高于市值权重。** Anarkulova-Cederburg-O'Doherty(2023/2025)用 39 个发达国家、约 2500 国-年的 block bootstrap 发现**对多数发达国家投资者,约 33-35% 国内 + 65-67% 国际**是退休财富/破产风险意义上的最优;Vanguard(2024)给出**约 30%(美国投资者视角下的"非美"配置上限附近)**的实务建议区间。**注意:这两个数字方向一致(国际分散有益)但口径不同**,后者是减少波动的边际收益递减点,前者是终身财富分布最优。[中-高]

3. **危机相关性上升是稳健的统计事实:相关性在熊市/极端下行升高,但在牛市不升高。** Longin-Solnik、Ang-Bekaert、Butler-Joaquin 等显示极端下行的实际相关性显著高于正态预测,等权国内+国际组合在极端下行月份的实际收益比正态预测**平均低 >2%/月**。**含义:把国际分散当"危机对冲"会失望;它的价值在长期(经济增长差异主导)而非短期 panic。** [高]

4. **EM 长期预期收益高,但伴随高波动与治理/货币风险。** 截至 2024Q4,Research Affiliates 对 EM 股票的长期预期约 **7% 名义 / ~4.7% 实际**,远高于美国(因 EM CAPE ~美国一半);但实现路径波动大、回撤深、汇率与政策风险高。**高预期收益是对承担这些风险的补偿,不是无风险套利。** [中]

5. **CAPE(Shiller PE)对**国家**层面长期回报有真实但**有限且不稳定**的预测力。** Keimling/StarCapital:CAPE 解释发达市场后续 10-15 年实际回报的约 **48%(R²)**,但**逐国差异巨大**(日本 ~90%、英国 ~86%、美国自 1970 ~82%、加拿大 ~1%)。低 CAPE(<15)历史上几乎总跟随更高后续回报(除丹麦)。**务实:CAPE 适合做**长期、跨国相对**的方向性倾斜,不适合精确择时或单点预测。** [中-高]

6. **货币对冲:股票端长期影响小且双向,债券端应对冲。** Vanguard:对**股票**,对冲减波动的效果**边际且不稳定**(有时反而增波动),长期投资者**可不对冲或部分对冲**,因非本币暴露有时降低组合尾部风险;对**国际债券**,不对冲会把波动推到"股票级",**应对冲**。对冲有持续成本与现金流风险。[高]

7. **价值/动量/质量在国际与 EM 总体稳健,但有重要例外。** AQR "Value and Momentum Everywhere"(Asness-Moskowitz-Pedersen 2013)在 8 个市场/资产类一致;价值+动量负相关,组合后 Sharpe 大幅提升;EM 因子常更强(流动性更差)。**但中国 A 股是显著例外:经典价格动量在 A 股**多数研究中弱或反转**,价值与规模需特殊构造(Liu-Stambaugh-Yuan CH-3/CH-4,剔除最小 30% 壳价值股、用 E/P、加 turnover 情绪因子)。** [高]

8. **中国 A 股可投资但有摩擦。** Stock Connect 提供外资准入;MSCI 自 2018 部分纳入。A 股**高散户、高换手、强情绪、监管/政策风险大**;直接套用美式因子会错。免费数据上 **AkShare** 是 A 股最佳免费源(质量优于 yfinance,后者对中国大陆已限流/停服)。[中-高]

9. **落地建议**:本系统应(a)把**多市场配置**作为一等公民(美/港/A 分桶 + 全球市值/GDP 锚 + 国内权重上限);(b)EM/A 股**单独因子构造**(CH-3/CH-4 风格,慎用价格动量);(c)用 **AkShare(A 股)+ stooq/yfinance(全球)** 拼免费 PIT 数据;(d)CAPE 仅作**长期方向性倾斜**,加 walkforward/PBO 防过拟合;(e)风险预算上对 EM 设波动/回撤上限,汇率默认股票不对冲、债券对冲。

---

## 2) 分散收益 / 相关性证据

### 2.1 国际分散降的是什么风险?

- **理论(经典)**:相对投资者实际持有,进一步国际分散可在**几乎不影响预期收益**的前提下**显著降低风险**(因加入低相关资产)。这是 Vanguard 等反复重申的"分散是接近免费午餐"。[中｜Vanguard,机构研究]
- **现实修正**:几何收益的提升**有限**——长期看各发达市场实际股票收益趋同,国际化主要**降低单国"失落十年"/崩盘的灾难尾部**(日本 1990s、俄罗斯 1998、希腊 2010s、单国监管冲击)。把"不会全军覆没"当作主要收益,而非"复合收益更高"。[中-高]
- **可证伪点**:若某单一市场(如美国)未来 10 年继续大幅跑赢,国际分散在**事后**看是拖累——这正是它作为保险的本质(为没发生的灾难付费)。不要因近 15 年美国独强就否定分散的**事前**价值。[高]

### 2.2 危机中相关性上升("最需要时失灵")

| 现象 | 证据 | 来源 / 可信度 |
|---|---|---|
| 相关性随波动上升,熊市升、牛市不升 | Longin-Solnik(2001)、Ang-Bekaert(2002)极值相关性研究 | [高｜JF/RFS 经典] |
| 极端下行实际相关 >> 正态预测 | Butler-Joaquin(2002):等权国内+国际在极端下行月实际收益比正态预测平均低 **>2%/月** | [高｜J. Int'l Money & Finance] |
| 2008 全球近乎同步 | 高波动→相关性骤升,分散在短期 panic 中保护有限 | [中｜综述类] |
| 长期仍有效 | 长期(增长差异主导)分散的风险/收益对投资者仍有利 | [中｜AAII/综述] |

> **诚实结论**:国际分散**不是危机对冲**(危机时相关性收敛到接近 1)。它的价值在**长期、跨周期**——当各国经济增长路径分化时,分散捕捉"不把鸡蛋放在一个国家治理/货币/人口篮子里"的好处。把它定位为**结构性保险**,而非战术性避险。[高]

### 2.3 本土偏好(home bias)的代价与争议

- **代价**:加拿大投资者把约 50% 股票配本国(相对全球市值过配 ~18x),导致行业/个股高度集中、可分散的特质风险未分散。[中｜Vanguard Canada HOBI 2024]
- **最优国内权重(终身财富视角)**:Anarkulova-Cederburg-O'Doherty,39 国 ~2500 国-年 block bootstrap → **约 33-35% 国内 + ~65% 国际**对多数发达国家投资者最优(最大化退休财富/最小化破产)。[中-高｜SSRN 4590406]
- **最优国内权重(波动最小化视角)**:Vanguard(2024)实务建议**约 30% 国际**起步、再视成本/相关性/汇率调整;两者**方向一致但口径不同**,不应混用为同一数字。[中｜Vanguard]
- **争议**:home bias 有部分**理性成分**——本币负债匹配、税收、信息优势、对冲本国通胀/汇率。"全市值权重"是上限参照,**不是必须达到的目标**。[中]

---

## 3) CAPE 长期回报模型(来源可信度)

### 3.1 CAPE 的跨国预测力(Keimling / StarCapital)

| 度量 | 数字 | 来源 / 可信度 |
|---|---|---|
| CAPE 解释发达市场后续 10-15 年**实际**回报 | **R² ≈ 0.48**(整体) | [中-高｜Keimling SSRN 2736423,经 Monevator 转述] |
| 逐国 R² 离散度 | 日本 ~0.90、英国 ~0.86、美国(自 1970)~0.82、美国(自 1881)~0.46、**加拿大 ~0.01** | [中｜同上,二手转述] |
| 低 CAPE 规律 | CAPE<15 几乎总跟随更高后续回报(除丹麦) | [中｜同上] |
| 改进版(10y forward) | 某些研究 R² 升至 ~0.78(1983-2015) | [中｜二手] |

> **CAPE 原始论文**(Keimling, "Predicting Stock Market Returns Using the Shiller CAPE", SSRN 2736423)WebFetch 返回 403,以上为**经 Monevator/搜索摘要二手转述**,R² 量级可信但**精确数未独立核实**。[标注:部分未核实]

### 3.2 当前各国 CAPE(截至 2025-12-31,Siblis Research)

| 市场 | CAPE | 估值含义 |
|---|---|---|
| 美国 | **34.73** | 昂贵 → 低预期实际回报 |
| 印度 | 34.36 | 昂贵 |
| 日本 | 29.38 | 偏贵 |
| 加拿大 | 26.20 | 中等偏贵 |
| 德国 | 24.08 | 中等 |
| 西班牙 | 23.69 | 中等 |
| 意大利 | 20.72 | 中等偏低 |
| 英国 | 20.19 | 偏便宜 |
| **中国** | **17.71** | **最便宜之一** |

来源:Siblis Research CAPE by country(已 WebFetch 核实数值)。[高｜数据源] 注:Siblis 明确**警告不同国家 CAPE 不应直接横比**,应与该国自身历史均值比较(会计/行业结构/利率环境差异)。

### 3.3 Research Affiliates / StarCapital 长期回报模型

| 项 | 内容 | 来源 / 可信度 |
|---|---|---|
| RA Asset Allocation Interactive(AAI) | 10 年期 CME,覆盖 140+ 资产、多币种;方法=**当前股息收益 + EPS 增长 + 估值(多重)均值回归**(美/国际同一框架) | [中-高｜researchaffiliates.com] |
| EM 股票预期(2024Q4) | **~7% 名义 / ~4.7% 实际** | [中｜RA,经搜索摘要] |
| EM vs 美国 | EM CAPE ~美国一半 → EM 预期实际回报高出数个百分点 | [中｜RA] |
| 10 年回顾自评 | RA 2025/01 "AAI at 10 Years: The Good, the Not Too Bad, and the Ugly" 自评模型基本有用但非完美(WebFetch 仅取到标题,**具体命中率/R² 未核实**) | [低-中｜未核实细节] |
| StarCapital 模型 | 用 CAPE + P/B 对全球市场做 10-15 年回报与风险预测;Keimling 是核心研究者 | [中｜StarCapital/Keimling] |

> **可信度立场**:RA/StarCapital 的模型是**公开、可证伪、长期方向性**的——它们对"贵的市场未来回报低、便宜的市场高"这一**方向**的预测力强(R² ~0.4-0.5 量级),但**对精确点估计和短期(<7 年)几乎无预测力**。把它们当**长期相对配置罗盘**,不当短期信号。RA AAI 工具本身免费可查(interactive.researchaffiliates.com),适合 PIT 引用。[中-高]

---

## 4) 货币对冲 / 因子国际稳健性

### 4.1 货币对冲 vs 不对冲(长期)

| 资产 | 结论 | 数字/机制 | 来源 / 可信度 |
|---|---|---|---|
| **国际股票** | 长期对冲效果**边际且双向**;可不对冲或部分对冲 | 各地区对冲对波动影响小、有时反增波动;非本币暴露有时**降低**组合尾部(危机中避险货币升值) | [高｜Vanguard ISGPCH 2018] |
| **国际债券** | **应对冲** | 不对冲时债券波动会升到"股票级",淹没债券的分散价值 | [高｜Vanguard] |
| **成本** | 对冲有持续成本+现金流/再平衡风险 | 短期降波动须与"减少的收益+成本"权衡 | [高｜Vanguard / WisdomTree] |
| **AQR 优化视角** | 把货币拆成"最小化股票波动的对冲组合 + 价值/动量/carry 的 alpha 组合",可同时降风险+提收益,优于全对冲/全不对冲 | mean-variance 框架 | [中-高｜AQR working paper] |

> **本系统默认**:股票**不对冲**(简单、长期影响小、保留尾部对冲);债券若引入则**对冲**;货币因子(value/carry/momentum)作为**独立研究模块**,不混进股票配置。Vanguard ISGPCH PDF WebFetch 因二进制解码失败,以上结论来自 Vanguard 多篇研究的搜索摘要,**方向高可信,精确波动数未独立核实**。[部分未核实]

### 4.2 因子(价值/动量/质量)在国际与 EM 的稳健性

| 因子 | 国际/EM 证据 | 来源 / 可信度 |
|---|---|---|
| **价值 + 动量(联合)** | AQR "Value and Momentum Everywhere"(2013):美/英/欧/日个股 + 指数/债/汇/商品 8 类一致;价值与动量**负相关**,组合后 Sharpe 大幅提升;**强共同因子结构** | [高｜JF,Asness-Moskowitz-Pedersen] |
| 价值/动量在 EM | 常**更强**(流动性更差、定价更不效率) | [中｜AQR] |
| **规模/价值/盈利/投资(EM)** | Fama-French(1998):13 个主要市场中 12 个有显著价值溢价;规模是世界市场最强异象之一;盈利溢价在东欧/拉美显著、在亚洲不显著(Foye 2018) | [中-高｜FF / 学术] |
| **局部 vs 全球因子** | 局部(本地)因子表现优于美/全球因子 → EM 存在**市场分割**,需本地构造 | [中｜学术] |
| Dimensional 实务 | 小盘在发达非美与 EM 长期跑赢大盘;价值/盈利溢价跨市场存在但波动大、有长期落后期 | [中｜Dimensional insights] |

### 4.3 中国 A 股的因子表现(关键例外)

| 发现 | 细节 | 来源 / 可信度 |
|---|---|---|
| **经典价格动量弱/反转** | A 股高散户、高换手 → 多数研究找不到稳健价格动量,常见**短期反转**;动量仅在高价/受限于整手规则的股中出现(Du et al. 2023) | [高｜多篇学术] |
| **Liu-Stambaugh-Yuan CH-3** | 构造中国版规模+价值因子:**剔除最小 30% 股票**(其 ~30% 市值是"壳价值",83% 反向并购壳来自最小 30%);价值用 **E/P**(吸收 B/M);复刻 FF 在中国会留 **17%/年 alpha** → 必须本地化 | [高｜Wharton/SSRN 3108175] |
| **CH-4** | 加第四因子=**turnover(换手/情绪)**,解释 A 股换手与反转异象(散户主导市场特有) | [高｜同上] |
| 低波/质量 | 低波效应在中国存在(The Volatility Effect in China, JAM 2021);质量需本地验证 | [中｜JAM] |

> **务实**:对 A 股**不要直接套美式价格动量**;价值用 E/P、规模剔除壳股、加情绪/换手因子。这是 EM 因子"局部构造优于全球"的最典型案例。[高]

---

## 5) 数据与可得性(免费国际源)

| 源 | 覆盖 | 优点 | 坑 / 注意 | 可信度 |
|---|---|---|---|---|
| **AkShare**(`akshare`) | A 股/港股/中国债/基金/宏观 + 部分全球;1000+ 接口 | A 股最佳免费源,**质量优于 yfinance**;pip 装;社区活跃 | 接口随上游网页变动易碎;需 Python≥3.9;主要中国市场,全球覆盖弱 | [高｜github akfamily/akshare] |
| **yfinance** | 全球(美/欧/部分 EM) | 免费、易用、覆盖广 | **对中国大陆已限流/停服**;单请求也可能 "too many requests";调整后价口径需核对;非 PIT(可能回填修正) | [中｜社区共识] |
| **stooq** | 全球指数/股票/外汇/商品,日线 | 免费 CSV、可批量下国际指数;`pandas-datareader` 可接 | 个股覆盖参差;复权/口径需校验;限频 | [中｜社区] |
| RA AAI | 140+ 资产长期 CME | 免费查、长期方向性、可 PIT 引用预期 | 是**预期**非历史价;季度更新 | [中-高｜RA] |
| Siblis / StarCapital | 各国 CAPE | 免费查 CAPE by country | 横比需谨慎(见 §3.2) | [中｜数据源] |

**拼数据建议(免费 PIT 友好)**:
- A 股 / 港股 → **AkShare**(主)
- 美股 / 全球指数 → **stooq**(国际指数,稳)+ **yfinance**(个股,备,非大陆)
- 估值锚(CAPE)→ Siblis/StarCapital(季度快照,自建历史)
- 长期预期 → RA AAI(方向性输入,不当交易信号)

> **前视/PIT 警告**:yfinance/AkShare 多为**当前快照**,历史财务可能已回填修正(restatement),做因子回测须**用 PIT 财报日对齐**或显式标注"可能含前视"。复权价口径(分红/拆股)各源不一,跨源拼接前先对齐。[高]

---

## 6) 落地到本系统(多市场配置 / 脚本 / 验证)

系统已有 `backtest/factors_xs.py`(横截面因子)、`backtest/`、`scripts/`、`feed/`、`routines/`(已核实目录存在,未读具体实现)。建议(均为**研究对照**,不强行改现有文件):

### 6.1 多市场配置层(新研究模块)
- **分桶**:美 / 港 / A(/ 加密另算),各桶内跑本地因子,桶间按**市值或 GDP 锚 + 国内权重上限**配置。
- **国内权重锚**:以全球市值为参照,设**国内上限**(参照 ACO 的 ~35% 国内 / Vanguard ~30% 国际起点),作为**约束**而非点目标。
- **EM/A 风险预算**:对 EM/A 桶设**波动上限 + 回撤刹车**,反映高波动/治理风险。

### 6.2 因子构造(按市场差异化)
- A 股:实现 **CH-3/CH-4 风格**(剔除最小 30% 壳股、E/P 价值、turnover 情绪因子);**默认关闭价格动量**或改用反转。
- EM(非中国):价值/规模/盈利可复用全球框架,但**本地化排序**(局部因子优于全球)。
- 美/发达:沿用现有 `factors_xs.py`。

### 6.3 货币处理
- 股票桶**默认不对冲**(记录本币 vs 美元两套收益曲线对照);
- 若引入国际债券则**对冲**;
- 货币 value/carry/momentum 作为**独立 alpha 模块**,不混进股票配置。

### 6.4 估值倾斜(慎用)
- 用 **CAPE 跨国相对**做**长期、低频(年度)** 的桶间倾斜(便宜国家小幅超配),倾斜幅度上限严格(如 ±25% 相对市值);
- **不**用 CAPE 做短期择时(<7 年无预测力)。

### 6.5 验证纪律(防过拟合 / 防前视)
- **Walk-forward + Purged/Embargoed CV**;PBO(Probability of Backtest Overfitting);Deflated Sharpe。
- **样本外地理验证**:在美股调好的因子,**先在国际/EM 盲测**再上线(检验是否数据挖掘)。
- **PIT 对齐**:财报用 PIT 日;价格复权口径跨源校验。
- **成本现实化**:EM/A 桶用**更高交易成本 + 借券难/不可做空**假设;A 股 T+1、涨跌停、停牌须建模。
- **危机相关性压力测试**:对组合做"极端下行月相关性→1"的情景,验证国际分散的尾部保护被高估了多少(见 §2.2)。

---

## 7) 风险与反方

1. **国际分散事后可能长期拖累**:近 ~15 年美国独强,任何非美超配都跑输。分散是**事前**保险,**事后**可能"白付保费"——必须接受这是保险的本质,不能因近期失效就放弃。[高]
2. **危机相关性收敛**:把国际分散当短期避险会失望(§2.2)。真正的危机对冲是久期/现金/避险货币,不是更多国家股票。[高]
3. **EM 高预期收益 ≠ 高实现收益**:治理、汇率、资本管制、政策(如行业整顿)、退市/审计风险可吞掉估值折价。CAPE 便宜可能是**便宜有理**(价值陷阱国家级版本)。[中-高]
4. **CAPE 预测力不稳**:逐国 R² 从 0.90 到 0.01(§3.1);会计准则、行业结构、利率/流动性环境变化可让历史关系失效。**横比不同国家 CAPE 是误用**。[中-高]
5. **A 股因子陷阱**:直接套美式动量/价值会错;壳价值、散户情绪、T+1/涨跌停、停牌、PIT 财报缺失都是真实坑。[高]
6. **货币对冲的诱惑**:对股票长期对冲常无益且有成本;过度对冲反而剥离了尾部对冲。[中-高]
7. **免费数据的前视/口径风险**:yfinance/AkShare 回填修正、复权口径不一、限流;不做 PIT 对齐的国际回测结论不可信。[高]
8. **模型预期的过度自信**:RA/StarCapital 的 CME 是方向性长期输入,不是精确点估计;把 "EM 预期 7%" 当确定性会误配风险预算。[中]

---

## 8) 参考来源(URL + 可信度)

**分散 / 相关性 / home bias**
- Vanguard Canada, "Home Bias" (HOBI, 2024) — https://www.vanguard.ca/content/dam/intl/americas/canada/en/documents/HOBI_052024_V14_secure.pdf [中]
- Vanguard Mexico, "Global equity investing: benefits of diversification & sizing" — https://www.vanguardmexico.com/content/dam/intl/americas/documents/mexico/en/global-equity-investing-diversification-sizing.pdf [中]
- Anarkulova, Cederburg, O'Doherty, "Beyond the Status Quo: A Critical Assessment of Lifecycle Investment Advice" (SSRN 4590406) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4590406 [中-高]
- Butler & Joaquin, "Are gains from international diversification exaggerated? Downside risk in bear markets" (JIMF 2002) — https://www.sciencedirect.com/science/article/abs/pii/S0261560602000487 [高]
- "Impact of financial crises on international diversification" (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S1044028302000509 [高]
- AAII, "International Diversification: Why It Still Makes Sense" — https://www.aaii.com/journal/article/international-diversification-why-it-still-makes-sense [中]

**CAPE / 长期回报模型**
- Keimling, "Predicting Stock Market Returns Using the Shiller CAPE" (SSRN 2736423) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2736423 [中-高｜原文 403,数字经二手转述,部分未核实]
- Monevator, "CAPE ratio by country" (Keimling R² 转述) — https://monevator.com/cape-ratio-by-country/ [中]
- Siblis Research, "CAPE Ratios by Country 2026" (截至 2025-12-31 数值,已核实) — https://siblisresearch.com/data/cape-ratios-by-country/ [高｜数据]
- Research Affiliates, "Asset Allocation Interactive at 10 Years" (2025/01) — https://www.researchaffiliates.com/publications/articles/1069-asset-allocation-interactive-good-bad-ugly [中｜自评细节未核实]
- Research Affiliates, AAI 工具(免费,长期 CME) — https://interactive.researchaffiliates.com/asset-allocation [中-高]
- "On the predictive power of CAPE / Shiller's PE" (PMC) — https://pmc.ncbi.nlm.nih.gov/articles/PMC8308066/ [中]

**货币对冲**
- Vanguard, "The portfolio currency-hedging decision" (ISGPCH, 2018) — https://passiveinvestingaustralia.com/wp-content/uploads/downloads/ISGPCH.pdf [高｜PDF 解码失败,结论经摘要,精确数未核实]
- AQR, "Optimal Currency Hedging for International Equity Portfolios" — https://www.aqr.com/Insights/Research/Working-Paper/Optimal-Currency-Hedging-for-International-Equity-Portfolios [中-高]
- WisdomTree, "Don't Layer Currency Risk on Top of Equity" — https://www.wisdomtree.com/-/media/us-media-files/documents/resource-library/whitepaper/currency-hedging_wp.pdf [中]

**因子国际/EM 稳健性**
- Asness, Moskowitz, Pedersen, "Value and Momentum Everywhere" (JF 2013) — https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf [高]
- AQR, "Value and Momentum Everywhere" (数据集/文章) — https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere [高]
- "Size, value, profitability, investment: Evidence from emerging markets" (ScienceDirect) — https://www.sciencedirect.com/science/article/abs/pii/S1566014117303357 [中-高]
- Dimensional, "Perspective on Premiums" — https://www.dimensional.com/ie-en/insights/perspective-on-premiums [中]

**中国 A 股因子 / 可投资性**
- Liu, Stambaugh, Yuan, "Size and Value in China" (CH-3/CH-4) — https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf [高]
- 同上 SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3108175 [高]
- "Factor Investing in the China A-Share Market" (CAIA) — https://caia.org/sites/default/files/factor_investing_in_the_china_a-share_market.pdf [中｜PDF 解码失败,未核实正文]
- NBER w29453, "Momentum, Reversals, and Investor Clientele" — https://www.nber.org/system/files/working_papers/w29453/w29453.pdf [中-高]
- "The Volatility Effect in China" (JAM 2021) — https://link.springer.com/article/10.1057/s41260-021-00218-0 [中]
- MSCI China A Inclusion Index — https://www.msci.com/indexes/index/716566 [高｜指数方法]

**免费数据源**
- AkShare (github akfamily/akshare) — https://github.com/akfamily/akshare [高]
- AkShare awesome-data — https://github.com/akfamily/awesome-data [中]
- stooq(经 pandas-datareader / PyBroker) — https://www.pybroker.com/en/latest/notebooks/1.%20Getting%20Started%20with%20Data%20Sources.html [中]

---

### 核实状态汇总
- **已独立核实(WebFetch)**:Siblis 各国 CAPE 数值(2025-12-31);MSCI A Inclusion 年度业绩(2024 +19.67%, 2025 +31.42%);Keimling R² 量级(经 Monevator)。
- **经搜索摘要、方向高可信但精确数未独立核实**:RA EM 预期 ~7%/4.7%;Vanguard 货币对冲精确波动数;Keimling 原文逐国 R²(原文 403);CAIA A 股因子正文(PDF 解码失败)。已在正文逐处标注"未核实 / 部分未核实"。
- **未读本仓库实现细节**:仅核实 `backtest/`、`scripts/`、`feed/`、`routines/` 目录存在与 `factors_xs.py` 引用(来自 low-vol 研究文件交叉引用),§6 建议均为研究对照,未声称已实现。
