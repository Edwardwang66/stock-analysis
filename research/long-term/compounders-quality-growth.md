# 优质成长"复利机器"(compounders)的可量化化 — 长期投资深度调研

> 目的:把 Terry Smith/Fundsmith 式"质量-成长复利机器"框架翻译成**预先可观测、可回测、可落地**的量化打分,并诚实标注幸存者偏差与估值纪律的决定性作用。
> 方法:fan-out 检索(Fundsmith 标准 / ROIC×再投资复利数学 / Buffett's Alpha 一手 PDF / Nifty Fifty 估值教训 / QMJ 长期证据 / 价值陷阱 vs 复利机器 / 幸存者偏差)→ 一手来源核验(含 NBER w19681 PDF 文本逐字抽取)→ 合成。
> 日期:2026-06-18。每条关键结论标注**来源 URL + 可信度(高/中/低)**;无法核实者标"未核实"。
> 房子风格:**诚实可证伪;净·扣成本是唯一货币;标注样本内/前视/幸存者偏差;免费/PIT 数据优先。**

---

## 1) TL;DR(执行摘要)

1. **"复利机器"的核心数学只有一行:内生增长 g = ROIC × 再投资率。** 高 ROIC 本身不够,必须能**把高比例利润以同样高的回报再投出去**。一个 20% ROIC、100% 再投资的公司内生增长 20%;同样 20% ROIC 但只能再投 50% 的公司只增长 10%。再投资能力(reinvestment runway)是把"高质量"和"高复利"分开的关键变量。[高｜basehitinvesting/Saber Capital]

2. **复利机器对估值的容错远大于直觉,但不是无限。** 一个 20% 复利、起点 25 倍 P/E 的公司,即使 15 年后多重从 25 压到 10 倍,15 年 CAGR 仍 ~12.9%;而 10% 复利的公司即使维持 25 倍也只有 ~10.4%。结论:**业务质量(复利速度)比入场多重更重要,但"为质量付任意价"会被证伪**(见 Nifty Fifty)。[高｜basehitinvesting 工作示例]

3. **Fundsmith/Terry Smith 框架可量化为五条预先可观测规则:** 高且稳定 ROCE(≥15–20%)、高毛利率、低资本强度、高现金转换(FCF≈净利)、低杠杆(净现金或低 debt/EBITDA),外加**估值护栏**(用买入年 FCF yield 设上限)。"Buy good companies, don't overpay, do nothing."[中-高｜Fundsmith 官方因 403 未直接核实,经二手多源交叉]

4. **Buffett's Alpha(Frazzini-Kabiller-Pedersen, NBER 2013)是质量+复利叙事最强的一手证据,也是最强的"祛魅":** 1976–2011 Berkshire 夏普 0.76(市场 ~0.39),市场 beta 仅 0.7,但**当控制 BAB(低 beta)与 QMJ(质量)因子后,alpha 变得不显著**——即 Buffett 的超额回报"既非运气也非魔法",而是**便宜+安全+质量股票 × ~1.6:1 廉价杠杆(保险浮存,平均成本仅 2.2%,低于 T-bill)**。质量是真实溢价,但很大程度是**可复制的因子暴露**,不是不可名状的天才。[高｜NBER w19681 PDF 逐字核实]

5. **质量因子有强样本内长期证据:QMJ(Asness-Frazzini-Pedersen)在美国长样本月度风险调整 alpha ~64–105 bp(t 在 4.26–9.31),全球 24 国显著。** 这是把"compounder"制度化为因子的学术底座。但必须打"样本内 + AQR 自家因子"的折扣。[高｜QMJ 论文 / RAS 2019]

6. **幸存者偏差是这条赛道最大的诚实风险。** "复利机器"叙事极易**事后选样**:我们记得可口可乐、好市多,忘了同样曾被称为"一次决策"却腰斩的 Nifty Fifty 成员。用现存成分股回测可高估年化 1–4%、极端可达 23%。唯一解药:**预先规则 + 含退市/重述的 PIT 数据 + 横截面回测,而非挑几个赢家讲故事**。[高｜多源]

7. **Nifty Fifty 是"为质量付过高价"的经典教训,但 Siegel 的长程研究给了反直觉的细节:** 1972 年 Nifty Fifty P/E 41.9(S&P 18.9),1973–74 腰斩;但到 1998 年,整组**仅高估约 3.2%**,总回报 12.2–12.5% vs S&P 12.7%——高估值被更高的盈利增长几乎抵消。教训是**双向的**:既不能为质量付任意价,质量的高增长也确实能"挣回"相当一部分溢价。决定成败的是**估值纪律的程度**,不是"贵就不买"的口号。[高｜Siegel via AAII/MoneyWeek,二手]

8. **价值陷阱 vs 复利机器的可量化判别(GMO 框架):** 把回报拆成"估值变化 vs 基本面回报"。理想的便宜=估值压缩但基本面(ROIC、增长)稳定;价值陷阱=基本面回报为负、ROIC 相对市场下滑、杠杆上升。**ROIC 的趋势/稳定性,而非点时水平,是关键判别量。**[高｜GMO Quarterly]

---

## 2) compounder 量化代理 + 复利数学

### 2.1 一行核心数学:内生增长 = ROIC × 再投资率

> 直觉:公司今年留存并再投入的每一块钱,以 ROIC 的回报生出新盈利;增长率就是"投出去的比例 × 投出去的回报"。

- **g(内生增长) = ROIC × b**,其中 b = 再投资率 = 1 − 派息率(含回购口径)。[高｜basehitinvesting "Math of Compounding Part 4";Saber Capital Part 3/4]
- 更精确地,**用增量回报 RONIC**(return on *new* invested capital)而非平均 ROIC:`g = RONIC × b`。平均 ROIC 高但增量 RONIC 低的公司(老资产好、新机会差)会让人高估复利。[中-高｜Mauboussin & Callahan "ROIC and the Investment Process";Trevisiol/Medium 二手]
- 示例(已核实于一手工作表):

| 公司 | ROIC | 再投资率 | 内生增长 | 起点 EPS | 15 年后 EPS |
|---|---|---|---|---|---|
| A | 20% | 100% | 20% | $1.00 | $15.40 |
| B | 20% | 50% | 10% | $1.00 | $4.17 |

两者 ROIC 相同,但 A 因再投资跑道更长,15 年盈利积累相差 ~3.7×。[高｜basehitinvesting 示例]

### 2.2 复利机器对入场多重的容错(同一示例的回报表)

| 退出 P/E | A 的 15 年 CAGR | B 的 15 年 CAGR |
|---|---|---|
| 10x | 12.9% | 5.5% |
| 15x | 16.0% | 8.3% |
| 20x | 18.2% | 10.4% |

- 解读:**即便 A 经历多重从 25→10 的腰斩,仍 ~12.9%**,优于 B 在任何多重下的表现。"picking the right business is more important than picking the right multiple"。[高]
- **诚实反方:** 这个示例假设 A 能**真的**维持 20% ROIC 与 100% 再投资 15 年——这正是事后才知道的。竞争优势期(CAP)会衰减(见 §3.4)。容错大 ≠ 容错无限;为复利付的价越高,对"持续性"的隐含赌注越大。

### 2.3 Fundsmith/Terry Smith 框架 → 五条可观测规则 + 估值护栏

Fundsmith 公开口径(官网 403,经 thesisrationale / stockinvestoriq / investinassets 多源交叉,标"未直接核实"处见下):

| 维度 | Fundsmith 表述 | 可量化代理 | EDGAR/PIT 字段(见 §5) |
|---|---|---|---|
| 高且稳定回报 | 高 ROCE / ROOCE,不靠杠杆 | ROIC ≥ 15–20% **且** 5–10 年波动率低 | NOPAT / 投入资本 |
| 高毛利 | 定价权、护城河 | 毛利率高 **且** 稳定(标准差低) | (Revenues − COGS)/Revenues |
| 低资本强度 | 现金流可高比例再投/返还 | Capex/Revenue 低;资产周转适中 | PaymentsToAcquirePPE / Revenues |
| 高现金转换 | FCF 接近/超过净利 | FCF / NetIncome ≈ 1(多年均值) | (CFO − Capex)/NetIncome |
| 低杠杆/避周期/避被颠覆 | 净现金或低债;避银行/资源/重科技颠覆 | NetDebt/EBITDA 低;行业排除 | DebtCurrent+LongTermDebt − Cash |
| **估值护栏** | "don't overpay" | 买入年 FCF yield ≥ 阈值(护栏,非择时) | FCF / MarketCap |

- 性格:**集中(20–30 只)、超低换手(<5%/年)、避开银行/保险/资源/重资本**。这契合本系统长期腿的"低换手→扣成本后仍活"结构性优势(见姊妹文件 quality-moat-factors §1)。[中-高]
- **未直接核实:** Fundsmith 官网 factsheet 上的**组合级加权平均 ROCE / 毛利率 / 现金转换 / 买入年 FCF yield**(历史上常披露)本次因 403 未取到具体数值,只有阈值方向。建库时应人工补一次官网快照。[标:未核实-数值]

### 2.4 "用合理价买伟大公司" vs 价值陷阱(GMO 四步)

把任意便宜股的"便宜"拆解(GMO Quarterly,已核实):
1. **估值**:相对历史/同业真便宜吗(P/S、P/GP、P/B、P/经济账面 的混合)。
2. **回报分解**:underperformance 由"估值压缩"还是"基本面回报(增长+派息+净发行)为负"驱动?**理想便宜 = 估值压缩主导、基本面稳定。**
3. **质量趋势**:ROIC、盈利、杠杆、周期性的**变化方向**。质量下滑→更低估值是"应得的"。
4. **结构力**:行业是逆风还是顺风(IPO 趋势、投资率、地缘)。

- 复利机器信号:估值压缩 + ROIC 稳定/上升 + 正基本面回报 + 长再投资跑道。
- 价值陷阱信号:基本面回报为负 + ROIC 相对市场下滑 + 杠杆上升(如 debt/EBITDA >4x 创新高)+ 结构逆风。[高｜GMO]
- **判别量的核心是 ROIC 的趋势与稳定性,不是点时水平**(呼应 quality-moat-factors §2.5:把 ROIC 水平和 ROIC 稳定性/趋势分开建因子)。

---

## 3) 长期证据 vs 幸存者偏差(来源可信度)

### 3.1 质量因子的样本内长期证据(强)

- **QMJ(Asness-Frazzini-Pedersen, RAS 2019;SSRN 2312432):** 做多盈利+成长+安全+派息四维高分、做空低分。美国长样本月度风险调整 alpha **~64–105 bp,t 在 4.26–9.31**;全球广样本 ~71–99 bp,t≈4.05+;**24 国**显著。高质量股票价格略高但"惊人地温和",故有高风险调整收益(行为/错误定价解释)。[高｜QMJ PDF econ.yale.edu;link.springer RAS 2019]
- **折扣:** 样本内、AQR 自家因子、可能拥挤。把它当**先验证据**而非未来保证;落地用预先规则横截面回测自验(§6)。

### 3.2 Nifty Fifty:为质量付过高价的双向教训(中-高,二手)

- **1972:** Nifty Fifty P/E **41.9** vs S&P **18.9**;被宣传为"one-decision, buy and never sell"。1973–74 熊市("Black Bear")腰斩。[中-高｜RIA/AAII/Wikipedia 二手]
- **Siegel 长程(1972-12 → 1998-08):** 整组**仅高估约 3.2%**;不再平衡 12.2%、年再平衡 12.5%,S&P 12.7%。高 P/E 的"earnings yield 缺口"几乎被**更高的实际盈利增长**抵消。个股层面:1972 你本可为 Philip Morris 付 68.5×、可口可乐 82×、默克 76× 仍跑平 S&P,而当时实付仅 24× 左右。[中-高｜Siegel via AAII/MoneyWeek,**一手 Siegel 论文未直接核实**]
- **诚实双向解读:**
  - 反"为质量付任意价":1973–74 的腰斩是真实回撤,**估值过高会先让你承受巨大久期风险**(Nifty Fifty 是长久期资产,对利率/通胀极敏感)。
  - 反"贵就不买":26 年维度,优质高增长**确实挣回了**绝大部分溢价。**关键变量是持有期长度 + 估值过高的幅度**,不是简单的"贵/便宜"二分。
- **落地:** 估值护栏应是"上限/打折",不是"硬择时"——为质量付**合理溢价**可以,付**41.9× 的市场级泡沫**会被久期惩罚。

### 3.3 幸存者偏差 / 事后选样(本赛道最大诚实风险)

- **机制:** "复利机器"叙事天然只盯赢家(可口可乐、好市多、微软),退市/腰斩的"曾经的复利机器"被记忆抹去。用**当前成分股**回测系统性排除了曾经入选后失败的公司。[高｜luxalgo/QuantifiedStrategies/Wikipedia]
- **量级:** 排除退市股可高估年化 **1–4%**;某指数回测案例排除了 82.5% 曾入选公司,**高估 23.3%**。[高｜二手量化博客,数值为示例非普适常数,标"中"可信度的普适性]
- **叙事偏差:** 先发现 pattern、后编经济理由 = 大概率自欺。[高]
- **解药(本系统硬要求):**
  1. **预先可观测规则**(ROIC/再投资/毛利稳定/低杠杆/估值上限)在 t 时刻仅用 t 之前信息计算;
  2. **PIT 数据含退市与重述**(用 `filed` 而非 `end`,见 sec-edgar-xbrl-fundamentals §1);
  3. **横截面组合回测**(打分前 N 分位 vs 后 N 分位),而非挑 5 只赢家;
  4. **报告净·扣成本**与换手、容量。

### 3.4 质量不是永动机:ROIC 均值回归(中-高)

- 见姊妹文件 quality-moat-factors §7:ROIC 向 WACC 均值回归,中位公司超额回报 ~7 年(CAP);但顶部五分位有"黏性",10 年后仍在前两分位概率 ~64%。[中-高｜Mauboussin/Credit Suisse]
- 启示:复利机器打分要**同时含 ROIC 水平 + ROIC 趋势/稳定性 + 再投资跑道**;并对"为持续性付的溢价"做敏感性分析(若 CAP 只剩 7 年,当前价隐含的 IRR 是多少)。

---

## 4) Buffett's Alpha 分解(一手核实,NBER w19681)

> 来源:Frazzini, Kabiller, Pedersen, "Buffett's Alpha", NBER WP 19681 (2013);后发表于 Financial Analysts Journal 74(4), 2018。**以下数值由 PDF 文本逐字抽取核实(2026-06-18)。** [高]

**核心数字(1976-11 → 2011):**
- 夏普比率 **0.76**(>30 年历史的任何股票/共同基金中最高;市场 ~0.39)。[高｜逐字核实]
- 年化超额回报(over T-bill)**19.0%**;市场 6.1%。$1(1976-11)→ >$1500(2011 末)。[高]
- **市场 beta 仅 0.7**;信息比率 **0.66**;年化波动 24.9%(19.0/24.9 = 0.76)。[高]

**杠杆来源与成本:**
- 平均杠杆 **~1.6:1**。对市场加 1.6× 杠杆只能放大到 ~10% 超额回报,**远不及 Berkshire 的 19%**——杠杆能解释一部分,但不是全部。[高｜逐字核实]
- **保险浮存(float)= 负债的 ~36%,平均成本仅 2.2%,比平均 T-bill 低 >3 个百分点。** Berkshire 1989–2009 AAA 评级,2002 发行史上首个负息证券。**这是"独家、有期限的廉价杠杆"——别人无法复制的部分。**[高｜逐字核实]

**因子分解(本文的"祛魅"核心):**
- 控制 BAB(Betting-Against-Beta,低 beta)与 **QMJ(Quality-Minus-Junk)** 后,**Berkshire 对 CAPM 的显著 alpha 变得不显著**。Berkshire 显著正载于 BAB 与 QMJ。[高｜逐字核实]
- 风格画像:**safe(低 beta、低波)+ cheap(低 P/B 价值)+ quality(盈利、稳定、成长、高派出)**。
- **拆股票 vs 私有控股:公开股票(13F)表现最好 → 超额回报更多来自选股,而非对管理层的影响。**[高]

**对本系统的含义:**
- "compounder + 合理价 + 廉价稳定杠杆"的**因子化版本可大体复制**(BAB+QMJ+Value),这是好消息(可量化、可回测)。
- 但**廉价稳定杠杆(浮存)是 Berkshire 不可复制的护城河**;散户/基金没有 2.2% 永续杠杆。**复制 Buffett 的因子暴露 ≠ 复制 Buffett 的回报**——别把杠杆来源的稀缺性当成可外推的 alpha。[高,诚实警告]

---

## 5) 数据与可得性(EDGAR 字段)

> 底座沿用姊妹文件 sec-edgar-xbrl-fundamentals:免费、无 key、PIT 友好;用 `filed` 做时间轴避前视;含退市/重述去重。下表给 compounder 打分所需 us-gaap 标签(口径需固定;营收等做优先级回退)。

| 量 | 公式 | 主要 us-gaap 标签(回退顺序) | 备注 |
|---|---|---|---|
| 毛利率 | (Rev − COGS)/Rev | `RevenueFromContractWithCustomerExcludingAssessedTax` → `Revenues` → `SalesRevenueNet`;`CostOfRevenue` → `CostOfGoodsAndServicesSold` | 利润表最顶端,最"干净" |
| 营业利润率 | OperatingIncome/Rev | `OperatingIncomeLoss` | RMW 口径近似 |
| NOPAT | EBIT×(1−税率) | `OperatingIncomeLoss`;税率用 `IncomeTaxExpenseBenefit`/`IncomeLossBeforeIncomeTaxes` | ROIC 分子 |
| 投入资本 | 有息债 + 权益 − 现金 | `LongTermDebtNoncurrent`+`LongTermDebtCurrent`(或 `DebtCurrent`)+`StockholdersEquity`−`CashAndCashEquivalentsAtCarryingValue` | 口径固定后全样本统一 |
| ROIC | NOPAT/投入资本 | 上两行 | 水平 + 5–10y 波动率 + 趋势 |
| CFO | 经营现金流 | `NetCashProvidedByUsedInOperatingActivities` | 现金转换分子 |
| Capex | 资本开支 | `PaymentsToAcquirePropertyPlantAndEquipment` | 资本强度 |
| FCF | CFO − Capex | 上两行 | 现金转换、FCF yield |
| 现金转换 | FCF/NetIncome | `NetIncomeLoss` | 多年均值,过滤会计裁量 |
| 净债务 | 有息债 − 现金 | 见投入资本 | NetDebt/EBITDA 杠杆护栏 |
| 再投资率 b | 1 − (派息+回购净额)/NOPAT | `PaymentsOfDividends`、`PaymentsForRepurchaseOfCommonStock`、`ProceedsFromIssuanceOfCommonStock` | 内生增长 g 的乘子 |
| 市值(护栏) | 价格×股数 | `EntityCommonStockSharesOutstanding`×价格(价格非 EDGAR,需行情源) | FCF yield 估值护栏 |

**硬限制(沿用 EDGAR 文件):** 仅 XBRL filer(美股 ~15k、~10 年史);无国际、无 pre-2009;退市公司从 ticker 表消失 → **必须用 bulk 历史 + submissions 保留退市 CIK,否则引入幸存者偏差**。合规带 User-Agent、限速 ~10 req/s。[高｜见 sec-edgar-xbrl-fundamentals §1]

---

## 6) 落地到本系统(compounder 打分 / 估值护栏 / 脚本 / 验证)

### 6.1 Compounder 打分(预先可观测,横截面 z-score 合成)

> 沿用 QMJ 的合成范式(各分项先横截面 z 再等权;见 quality-moat-factors §2.4)。**所有量在 t 时刻仅用 `filed ≤ t` 的事实计算。**

```
CompounderScore = z(
    w1 · z(ROIC_level)              # NOPAT/投入资本,当期
  + w2 · z(−ROIC_volatility_5y)     # 稳定性:5y ROIC 标准差,取负
  + w3 · z(ROIC_trend_5y)           # 趋势:5y ROIC 斜率(防价值陷阱)
  + w4 · z(GrossMargin_level)
  + w5 · z(−GrossMargin_volatility) # 毛利率稳定 = 定价权代理
  + w6 · z(CashConversion_5y_avg)   # FCF/NetIncome 多年均值
  + w7 · z(−Capex_to_Rev)           # 低资本强度
  + w8 · z(ReinvestmentRunway)      # g = RONIC × b 的隐含值,或 b × ROIC
)
HardGates(必须通过,否则剔除):
  · NetDebt/EBITDA ≤ 阈值(如 2.5x;银行/保险/资源行业整组排除)
  · 多年 FCF > 0、现金转换均值 ≥ ~0.8
ValuationGuardrail(护栏,不是择时):
  · 仅在 买入年 FCF yield ≥ 下限(如 ≥ 行业中位 或 ≥ 绝对阈值)时纳入
  · 或:对 score 做"估值打折"= CompounderScore − λ·z(Valuation_richness)
```

- 默认等权(w=1)起步,**不要优化权重到样本内最优**(过拟合)。RONIC 优于平均 ROIC,但 RONIC 噪声大,建议双轨:平均 ROIC 进 gate,RONIC 进敏感性。
- **估值护栏的纪律决定成败**(Nifty Fifty 教训):护栏太松 → 为质量付泡沫价;太紧 → 永远买不到伟大公司。建议用"打折"而非"硬剔除",并对 λ 做敏感性。

### 6.2 脚本(stdlib 优先,接 EDGAR PIT 底座)

- `scripts/build_compounder_panel.py`:从 §5 字段构建**带 vintage(filed)的长表**,产出每个 `as_of` 日的横截面打分。复用 sec-edgar 构建器(sec-edgar-xbrl-fundamentals §1 建议的 stdlib 构建器)。
- `scripts/score_compounders.py`:横截面 z-score 合成 + hard gates + 估值护栏 → 输出分位组合。
- `backtest/`:接现有 backtest 框架,跑**含退市股**的分位组合回测,报净·扣成本、换手、容量、最大回撤。

### 6.3 验证(证伪优先)

1. **幸存者偏差自查:** 同一回测分别用"含退市 PIT 全集" vs "当前成分股",报告 alpha 差异(应非零;若为零说明数据没含退市,**回测无效**)。
2. **估值护栏消融:** 有/无护栏、不同 λ 的净回报与回撤——验证"估值纪律决定成败"是否在本数据成立。
3. **ROIC 趋势 vs 水平消融:** 只用水平 vs 水平+趋势+稳定性——验证价值陷阱过滤是否真有增量。
4. **CAP 衰减压力测试:** 假设 ROIC 在 7–10 年回归 WACC,反推当前组合隐含 IRR,对比买入价。
5. **净·扣成本 + 容量:** 换手应 <20%/年(契合质量低换手优势);报告冲击成本下的容量上限。
6. **与现有因子相关性:** compounder score 与 value/momentum/低波的相关(质量与价值低/负相关、与低波正相关,见 quality-moat-factors §1)——避免把质量和低波当两个独立赌注。

---

## 7) 风险与反方

1. **幸存者偏差(最大):** compounder 叙事 = 事后选样的重灾区。不用含退市 PIT 数据 + 预先规则 + 横截面回测,所有"复利机器跑赢"的结论都不可信。[高]
2. **样本内 / 因子拥挤:** QMJ 等证据多为样本内、AQR 自家因子;质量近十年部分时段(如成长泡沫)表现平淡。打折看待,实盘自验。[高]
3. **为质量付过高价(Nifty Fifty 久期风险):** 优质长久期资产对利率/通胀极敏感;41.9× 市场级泡沫会先让你腰斩,即使 26 年挣回。估值护栏不是可选项。[高]
4. **ROIC 均值回归 / CAP 高估:** 把当前高 ROIC 外推到永远 = 系统性高估内在价值。增量 RONIC < 平均 ROIC 时,复利数学会让人自欺。[中-高]
5. **Buffett 不可复制的部分:** 浮存(36% 负债 @2.2%、AAA、永续)是 Berkshire 独家;复制 BAB+QMJ 因子暴露 ≠ 复制 1.6× 廉价杠杆带来的回报放大。别把杠杆来源稀缺性当 alpha。[高]
6. **标签碎片化 / 覆盖:** EDGAR 营收等标签需优先级回退;无国际、无 pre-2009、外国发行人(20-F/IFRS)缺失 → 美股偏样。[高]
7. **现金转换/再投资口径敏感:** FCF、投入资本、再投资率定义不唯一;口径不固定会让横截面打分失真。固定口径并做敏感性。[中]
8. **"do nothing"与再平衡冲突:** 极低换手是质量的成本优势,但纯买入持有会让组合随时间偏离打分;需规则化的低频再平衡 + 护栏触发卖出(质量恶化/估值离谱)。[中]

---

## 8) 参考来源(URL + 可信度)

**一手 / 高可信:**
- Frazzini, Kabiller, Pedersen, *Buffett's Alpha*, NBER WP 19681 (2013) — PDF 逐字核实(夏普 0.76、beta 0.7、杠杆 1.6:1、浮存 36%@2.2%、BAB+QMJ 吞并 alpha)。https://www.nber.org/system/files/working_papers/w19681/w19681.pdf [高]
- 同上,Financial Analysts Journal 74(4) 2018(正式发表版,403 未直接核实正文)。https://www.tandfonline.com/doi/full/10.2469/faj.v74.n4.3 [高｜元数据]
- Asness, Frazzini, Pedersen, *Quality Minus Junk* (Yale 工作稿 PDF) — 质量四维 + alpha/t 区间。http://www.econ.yale.edu/~shiller/behfin/2013_04-10/asness-frazzini-pedersen.pdf [高]
- *Quality Minus Junk*, Review of Accounting Studies (2019) 正式版。https://link.springer.com/article/10.1007/s11142-018-9470-2 [高]
- GMO, *Bargain, Value Trap, or Something in Between?* (Quarterly Letter) — 便宜 vs 陷阱四步框架(已核实)。https://www.gmo.com/americas/research-library/bargain-value-trap-or-something-in-between_gmoquarterlyletter/ [高]
- NBIM, *The Quality Factor*(Discussion Note 3-15)。https://www.nbim.no/contentassets/0660d8c611f94980ab0d33930cb2534e/nbim_discussionnotes_3-15.pdf [高｜未直接核实正文]

**复利数学(中-高,二手但作者为从业者):**
- Saber Capital, *Importance of ROIC* Part 3 & 4(复利与再投资)。https://sabercapitalmgt.com/importance-of-roic-part-4-the-math-of-compounding/ [中-高]
- Base Hit Investing, *The Math of Compounding*(A vs B 工作示例,已核实数表)。https://basehitinvesting.substack.com/p/importance-of-roic-part-4-the-math-of-compounding [高｜示例数值核实]
- Mauboussin & Callahan, *ROIC and the Investment Process*(via therikinshah / Medium 摘要;一手 Counterpoint Global 报告未直接核实)。https://medium.com/@j.trevisiol/growth-roic-and-ronic-bc336746f2bb [中｜二手]

**Fundsmith / Terry Smith(中-高,官网 403,二手交叉):**
- Fundsmith 官网 factsheet(403,**组合级数值未核实**)。https://www.fundsmith.co.uk/factsheet/ [未核实-数值]
- thesisrationale, *Super Investors Series: Terry Smith*(ROCE≥15%、现金转换、低杠杆、"buy good / don't overpay / do nothing")。https://thesisrationale.substack.com/p/super-investors-series-terry-smith [中-高｜二手]
- stockinvestoriq, *Terry Smith / Fundsmith Strategy*(ROCE 15–20%、护城河、行业排除)。https://stockinvestoriq.com/terry-smith/ [中｜二手,403 未直接核实]
- investinassets, *How Terry Smith Beats the Market*。https://www.investinassets.net/p/how-terry-smith-beats-the-market [中｜二手]

**Nifty Fifty / 估值教训(中-高,二手;Siegel 一手未直接核实):**
- AAII, *Valuing Growth Stocks: Revisiting the Nifty Fifty*(Siegel 1972-1998 数据)。https://www.aaii.com/journal/article/valuing-growth-stocks-revisiting-the-nifty-fifty [中-高｜二手]
- MoneyWeek, *The 'nifty fifty' — when it makes sense to buy at the top*(Siegel breakeven P/E)。https://moneyweek.com/93195/when-it-makes-sense-to-buy-at-the-top-62310 [中｜二手]
- Real Investment Advice, *Are The Magnificent Seven In A Bubble? Ask The Nifty Fifty*(P/E 41.9 vs 18.9、Black Bear)。https://realinvestmentadvice.com/resources/blog/are-the-magnificent-seven-in-a-bubble-ask-the-nifty-fifty/ [中｜二手]
- Wikipedia, *Nifty Fifty*。https://en.wikipedia.org/wiki/Nifty_Fifty [中]

**价值陷阱 vs 复利机器:**
- Eagle Point Capital, *A Framework For Spotting Value Traps (The Anti-Compounders)*。https://eaglepointcapital.substack.com/p/spotting-value-traps-the-anti-compounders [中｜二手]
- Research Affiliates, *Active Value Investing: Avoiding Value Traps*(PDF)。https://www.researchaffiliates.com/content/dam/ra/publications/pdf/1013-avoiding-value-traps.pdf [中-高]

**幸存者偏差 / 回测陷阱:**
- Quantified Strategies, *Survivorship Bias in Trading*(1–4% 高估量级)。https://www.quantifiedstrategies.com/survivorship-bias-in-backtesting/ [中]
- LuxAlgo, *Survivorship Bias in Backtesting Explained*(82.5%/23.3% 案例)。https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/ [中｜案例数值非普适常数]
- Wikipedia, *Survivorship bias*。https://en.wikipedia.org/wiki/Survivorship_bias [中]

**本仓姊妹文件(交叉引用):**
- `research/long-term/quality-moat-factors.md`(QMJ 合成、ROIC 持续性、因子相关性)。
- `research/long-term/sec-edgar-xbrl-fundamentals.md`(PIT 底座、`filed` 时间轴、退市去偏)。
- `research/long-term/value-investing-frameworks.md`、`accruals-earnings-quality.md`(现金利润、应计)。

---

> **诚实结语:** 这条赛道最容易自欺的地方不是"质量是否长期跑赢"(样本内证据相当强),而是**我们是否在用预先规则诚实地回测,还是在事后挑可口可乐讲故事**。Buffett's Alpha 给出的最锋利结论是:伟大投资者的复利,很大程度上 = 可量化的便宜+安全+质量因子 × 独家廉价杠杆。前者本系统可复制并回测;后者(浮存)不可。把估值纪律当护栏、把幸存者偏差当默认敌人、把 ROIC 趋势而非水平当判别量——这三条决定本打分是真 alpha 还是又一个事后叙事。
