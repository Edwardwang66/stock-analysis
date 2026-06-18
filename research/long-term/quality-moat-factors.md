# 质量因子与经济护城河的量化 — 长期投资深度调研

> 目的:为本系统的**长期腿(持有期数月至数年)**评估"质量/护城河"作为一类可落地、净·扣成本仍有效的因子。
> 方法:fan-out 检索(Novy-Marx 毛利润率 / FF5 RMW / Ball 等现金利润 / QMJ / Morningstar 护城河 / ROIC 持续性 / 净成本与拥挤 / 因子相关性)→ 一手 PDF 核验 → 合成。
> 日期:2026-06-18。每条关键结论标注**来源 URL + 可信度(高/中/低)**;无法核实者标"未核实"。
> 立场承袭房子风格:**诚实可证伪;净·扣成本是唯一货币;标注样本内/前视/幸存者偏差;免费/PIT 数据优先。**

---

## 1) TL;DR(执行摘要)

1. **质量是少数"低换手 → 扣成本后仍活着"的因子。** Novy-Marx-Velikov《Taxonomy of Anomalies and Their Trading Costs》:单边月换手 < 50% 的异象多数在扣成本后仍有显著净 spread;质量信号"移动足够慢,可承载大量资金而不受高昂交易成本之苦",1990-2012 报告 Sharpe≈1.2(样本内,需打折)。这对我们这条数月-数年持有的长期腿是**结构性优势**——交易成本不是质量的主要敌人。[高]

2. **毛利润率(Novy-Marx 2013)是奠基证据:GP/资产 = (REVT − COGS) / AT,预测力"与账面市值比大致相当"。** 利润-减-不利润 spread 对 FF3 的月度 alpha = **0.52%,t = 4.49**(1963-2010,样本内)。关键洞见:用利润表**最顶端**的毛利,而非被会计裁量、融资、税收污染的净利润。[高]

3. **"哪个利润度量最好"已有迭代答案:现金型利润 > 含应计利润。** Ball-Gerakos-Linnainmaa-Nikolaev(JFE 2016):**现金型经营利润(cash-based operating profitability)吞并应计异象**,预测力优于含应计的毛利/经营利润,且可外推至 10 年。落地启示:若只能选一个利润分子,优先**经营利润 − 应计**。[高]

4. **Fama-French 2015 五因子把利润率制度化为 RMW。** 经营利润 OP = (营收 − COGS − SG&A − 利息费用) / 账面权益;RMW = 高 OP 组合 − 低 OP 组合。把质量纳入主流资产定价框架。[高]

5. **QMJ(Asness-Frazzini-Pedersen)是质量的"四维合成"标准件:盈利+成长+安全+派息**,各维内多变量先转 z-score 再等权合成,Quality = z(Profitability+Growth+Safety+Payout),做多最高 30%、做空最低 30%;全球 **24 国**显著的风险调整收益。这是本系统直接可抄的合成架构。[高]

6. **护城河可量化代理 = 高且稳定的 ROIC − WACC 利差 + 利差的持续时长。** Morningstar 明言"经济利润的**幅度远不如持续时长**重要":宽护城河≈≥20 年超额回报、窄护城河≈≥15 年;利差越薄越需要对持续性有把握。可代理化为:ROIC−WACC 利差、ROIC 波动率(越低越好)、毛利率稳定性、市占。[高]

7. **ROIC 会向资本成本均值回归,但顶部有"黏性"。** Mauboussin/Credit Suisse:中位大盘公司 ROIC>WACC 约维持 ~7 年(竞争优势期 CAP);但起点最高五分位的公司,10 年后仍留在前两分位的概率 ~64%。→ 质量不是永动机,是**衰减曲线**:必须把"ROIC 水平"和"ROIC 稳定性/趋势"分开建因子。[中-高]

8. **质量与价值、动量呈低/负相关,是天然分散器;与低波正相关(同源防御性)。** 质量与价值/小盘相关性低甚至负,使其在多因子配置中价值很高;但质量与最低波动正相关(预期内,质量有防御性偏向)。组合层面:质量+价值是经典互补(贵的好公司 vs 便宜的烂公司),不要把质量和低波当成两个独立赌注。[中-高]

---

## 2) 各质量度量定义 + 一手公式

> 约定:Compustat 年度字段 REVT(总营收)、COGS(销货成本)、XSGA(SG&A)、XINT(利息)、AT(总资产)、NI(净利)、CEQ/BE(账面权益)、SALE(营收)。所有"差"均为横截面 z-score 后合成。

### 2.1 毛利润率 Gross Profitability(Novy-Marx 2013)
- **公式:GP/A = (REVT − COGS) / AT**。即"毛利 / 总资产"。[高｜Novy-Marx JFE 2013 PDF]
- 理由:毛利位于利润表**最顶端**,尚未被 SG&A、研发、折旧政策、利息、税收等下游会计裁量污染;越往下越"干净度"越低。净利润对横截面收益的预测反而弱。[高]
- 注意:分母用**总资产**(非账面权益),所以它对资本结构中性,更像"资产生产率"。

### 2.2 经营利润率 Operating Profitability / RMW(Fama-French 2015)
- **OP = (REVT − COGS − XSGA − XINT) / BE**(营收 − 销货成本 − SG&A − 利息费用,再除以账面权益)。[高｜FF 2015 five-factor PDF;多源交叉确认]
- RMW = robust(高 OP)− weak(低 OP)组合收益。FF5 = 市场+SMB+HML+RMW+CMA。
- 与 GP/A 区别:RMW 减掉了 SG&A 和利息、分母用权益;两者高度相关但不等价。

### 2.3 现金型经营利润率 Cash-based Operating Profitability(Ball et al. 2016)
- 思路:经营利润 **减去应计项(accruals)**,只留现金部分。直觉:应计是"软"的、易被操纵且会反转;现金利润"硬"。
- 结论:现金型经营利润**吞并(subsumes)应计异象**,且单独加入它对 Sharpe 的提升,大于同时加入"应计因子+含应计利润因子"。预测力可延伸至 ~10 年——非常契合长期腿。[高｜Ball-Gerakos-Linnainmaa-Nikolaev JFE 2016]
- 落地:分子用"经营利润 − Δ净营运资本相关应计",分母可用资产或权益。

### 2.4 QMJ 四维(Asness-Frazzini-Pedersen, RAS 2019 / SSRN 2312432)
所有变量每月转 **z-score = (rᵢ − μ_r)/σ_r**(先排名再标准化),四维各自合成后再 z,等权相加:[高｜AFP QMJ;CRAN `qmj` 包文档交叉确认]

- **Profitability = z( zGPOA + zROE + zROA + zCFOA + zGMAR + zACC )**
  - GPOA=毛利/资产;ROE=NI/权益;ROA=NI/资产;CFOA=经营现金流/资产;GMAR=毛利/营收(毛利率);ACC=低应计(应计取负号,越低越"质")。
- **Growth = z( zΔgpoa + zΔroe + zΔroa + zΔcfoa + zΔgmar + zΔacc )**,每项为**过去 5 年**该利润度量的变化(分子变化 / 滞后分母)。
- **Safety = z( zBAB + zIVOL + zLEV + zO + zZ + zEVOL )**
  - BAB=低 beta;IVOL=低特异波动;LEV=低杠杆;O=Ohlson O-score(低破产概率);Z=Altman Z(高,稳健);EVOL=低盈利波动(ROE 的 5 年标准差)。
- **Payout = z( zEISS + zDISS + zNPOP )**
  - EISS=负的净股权发行(回购为正、增发为负);DISS=负的净债务发行;NPOP=净派出 / 利润。直觉:不稀释股东、把现金还给股东的公司更"质"。
- **Quality = z( Profitability + Growth + Safety + Payout )**。
- **QMJ 因子**:在大盘内/小盘内各取最高 30% 做多、最低 30% 做空。全球 24 国显著的风险调整收益;高质量股票价格略高但"惊人地温和",故有高风险调整收益(行为/错误定价解释)。[高]

### 2.5 ROIC / ROE(护城河核心)
- **ROIC = NOPAT / 投入资本**;NOPAT = EBIT×(1−税率);投入资本 = 有息债务 + 权益 − 现金(常见定义之一,口径需固定)。
- **经济利润 / 超额回报 = ROIC − WACC**。这是 Morningstar 护城河和 DCF 的核心。[高]
- **ROE = NI / 账面权益**(可用 DuPont 拆:净利率 × 资产周转 × 杠杆;护城河更看重前两项,杠杆驱动的高 ROE 是"假质量")。

### 2.6 度量之间的关系(一张速查)
| 度量 | 分子 | 分母 | 主要敌人/优点 | 出处 |
|---|---|---|---|---|
| GP/A(毛利率) | 营收−COGS | 总资产 | 最"干净"、资本结构中性;但忽略 SG&A 效率 | Novy-Marx 2013 |
| OP/BE(RMW) | 营收−COGS−SG&A−利息 | 账面权益 | 更全面;受权益口径与杠杆影响 | FF 2015 |
| 现金利润 | 经营利润−应计 | 资产/权益 | 抗应计操纵、长期预测最强;需现金流量表 | Ball et al. 2016 |
| ROIC | NOPAT | 投入资本 | 护城河核心;口径分歧大,易被会计扭曲 | Mauboussin/Morningstar |

**一致结论:越靠近现金、越靠近利润表顶端、越不依赖杠杆,质量信号越稳。** 这是从 2013(毛利)→2015(RMW)→2016(现金利润)的研究迭代主线。[高]

---

## 3) 长期净收益证据(标注可信度)

| 证据 | 数字 | 样本/口径 | 可信度 | 备注 |
|---|---|---|---|---|
| 毛利润率 spread vs FF3 alpha | **0.52%/月,t=4.49** | 1963-2010,美股,样本内 | 高 | Novy-Marx 2013 奠基 |
| 高-低 GP 组合月度 spread | ~0.30-0.40%/月(≈3.6-4.8%/年) | 同上 | 中-高 | WebFetch 摘要,数量级一致 |
| 质量(资产回报/经营现金流排序) Sharpe | **≈1.2** | 1990-2012,样本内 | 中-高 | Novy-Marx-Velikov 报告;**样本内须打折** |
| QMJ 风险调整收益 | "significant",24 国 | 全球,样本内 | 高 | 具体 alpha/t 见原文,此处定性 |
| 质量溢价(某质量指数口径) | **4.7%/年,σ=9.9,Sharpe 0.47** | 1964-2023 | 中 | T. Rowe Price 二手,口径非学术 QMJ |
| 现金型经营利润 | 吞并应计异象,提升 Sharpe,预测延伸 10 年 | 1963-2014 区间 | 高 | Ball et al. 2016 |

**净·扣成本(本系统唯一货币)关键结论:**
- Novy-Marx-Velikov:**单边月换手 < 50% 的异象,设计上做成本缓释(buy/hold spread)后多数仍有显著净 spread**;高换手策略很少能存活。质量属低换手 → **扣成本后存活概率高**。[高｜SSRN 2535173]
- Detzel-Novy-Marx-Velikov(2023):**用净成本因子做模型选择**,会偏向低换手因子;含**现金利润**的 FF5 变体在净成本下平方 Sharpe 最高。→ 我们若做净·扣成本模型比较,质量/现金利润很可能胜出。[高]
- 后发布衰减:文献普遍 ~50% 异象 alpha 在发布后衰减;但**低换手、有经济直觉的质量因子衰减较慢**(对比高换手反转因子)。仍需对样本内 Sharpe 打 30-50% 折扣。[中]

**幸存者/前视/样本内告警:**
- 上述多数 Sharpe/alpha 为**样本内、毛收益**;落地必扣成本、扣借券费(做空腿)、做 Deflated Sharpe 与 CSCV-PBO。
- Compustat 历史含幸存者与前视(财报"重述后"数值、未对齐 PIT)——见 §5。

**ROIC 持续性 = 质量是"衰减曲线"而非常数(护城河量化的核心实证):**
- Mauboussin/Credit Suisse:**ROIC 在所有研究过的时段都向资本成本均值回归**,这与微观经济学一致;随机性在回归过程中作用很大。[中｜二手汇总]
- 但顶部有黏性:**起点最高五分位的公司,10 年后仍在前两分位的概率 ≈ 64%**;落入最低/次低分位的概率 ≈ 1/4。中位大盘公司维持 ROIC>WACC 约 **7 年**(竞争优势期 CAP);顶部公司可达 **15 年以上**。[中-高]
- Mauboussin 把"为何有些公司能抗回归"归因于**商业模式差异**(而非单纯成长或行业)。
- **落地含义:** 不能只买"当前高 ROIC",要建**水平 × 持续性 × 趋势**三层:① ROIC−WACC 当前水平 ② 过去 5-10 年利差为正的年份占比(持续性)③ ROIC 的 5 年斜率(改善 vs 恶化)。把"持续性"单列为一个子因子,正是 Morningstar"时长>幅度"的可计算翻译。

---

## 4) 护城河的可量化代理(Morningstar 方法论 → 可计算特征)

Morningstar 定义:经济护城河 = 让公司**长期维持超额利润**的结构性特征;超额利润 = ROIC > WACC。五大来源:无形资产、转换成本、网络效应、成本优势、有效规模。[高｜Morningstar Equity Research Methodology 2023]

**核心原则(直接抄进因子设计):**
- **"经济利润的幅度远不如持续时长重要。"** → 因子应奖励**持续性/稳定性**,而非单期高 ROIC。
- **利差越薄,越需要对持续性有信心**才给宽护城河。→ 因子里"ROIC−WACC 利差"应与"利差稳定性"交互。

**可量化代理(全部可用免费/PIT 数据近似):**

| 护城河信号 | 可计算代理 | 数据 |
|---|---|---|
| 高且稳定的超额回报 | 滚动 5-10 年 **ROIC − WACC > 0** 的年份占比;均值水平 | EDGAR XBRL + 自算 WACC |
| 低 ROIC 波动 | ROIC 的 5-10 年标准差(越低越好,取负) | EDGAR XBRL 时间序列 |
| 毛利率稳定 | 毛利率(GP/营收)的 5 年标准差(取负);均值水平 | REVT, COGS |
| 定价权/无形 | 高且稳定毛利率 + 高 SG&A 转化率(代理品牌/研发护城河) | REVT, COGS, XSGA |
| 市占/规模 | 行业内营收份额、营收规模分位(有效规模代理) | 同业 REVT 横截面 |
| 资本纪律 | 低净增发(EISS)、稳定/上升派息(NPOP);ROIC 不靠杠杆 | 现金流量表 XBRL |
| 反"假质量" | DuPont 拆解剔除高杠杆驱动的高 ROE | 资产/权益/NI |

**注意:** Morningstar 的最终评级含分析师定性判断,无法完全复制。我们只能复制其**量化骨架**(高且持续的 ROIC−WACC + 低波动),并诚实标注"这是护城河的代理,不是 Morningstar 评级本身"。[中]

---

## 5) 数据与可得性(免费 / PIT 优先)

**首选免费源:SEC EDGAR XBRL Company Facts / Frames API。**
- CompanyFacts:`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` —— 返回某公司全部历史 XBRL 事实,**免费、无需 API key**。[高｜SEC.gov EDGAR APIs]
- Frames(横截面):`https://data.sec.gov/api/xbrl/frames/us-gaap/{Concept}/USD/CY{YYYY}.json` —— 一次拿全市场某概念某年值。[高]
- 速率限制:**≤10 req/s/IP**;必须带 `User-Agent: 公司名 邮箱`。[高]

**关键 us-gaap XBRL 标签(质量因子原料):**

| 因子分子/分母 | 候选 us-gaap 标签(有同义,需做映射) |
|---|---|
| 营收 REVT | `Revenues` / `RevenueFromContractWithCustomerExcludingAssessedTax` |
| 销货成本 COGS | `CostOfRevenue` / `CostOfGoodsAndServicesSold` |
| 毛利 GP | `GrossProfit`(也可由营收−COGS自算,更稳) |
| SG&A | `SellingGeneralAndAdministrativeExpense` |
| 利息费用 | `InterestExpense` |
| 总资产 AT | `Assets` |
| 净利 NI | `NetIncomeLoss` |
| 权益 BE | `StockholdersEquity` |
| 经营现金流 | `NetCashProvidedByUsedInOperatingActivities` |
| 资本开支 | `PaymentsToAcquirePropertyPlantAndEquipment` |
| 股票回购/增发 | `PaymentsForRepurchaseOfCommonStock` / `ProceedsFromIssuanceOfCommonStock` |
| 派息 | `PaymentsOfDividendsCommonStock` |

**PIT(point-in-time)与陷阱 —— 必须治理:**
- **用 filing date(`filed`),不要用 period end date 对齐特征。** XBRL 每条 fact 带 `filed` 字段;只能用"截至当时已公开"的数值,避免前视。常见保守做法:财报期末 + 滞后(如季报+45天/年报+90天)或直接用 `filed` 日期。[高｜推断,XBRL 含 filed 字段属事实]
- **重述(restatement):** 重述时 filer 须同时提交修订后的 XBRL;同一期会出现多版数值。PIT 必须保留**首次申报版本**,否则混入未来信息(前视)。[中｜SEC 规则确认须同步修订;PIT 实操属推断]
- **幸存者偏差:** EDGAR 覆盖"曾经申报过的所有 filer,含退市/解散实体",所以**原料层无幸存者偏差**——但若用第三方现成股票池或只取"今天仍在交易"的票,会重新引入偏差。务必保留退市票直至退市日。[中-高]
- **XBRL 覆盖起点:** 美股 XBRL 强制约 2009 起;更早历史需别的源(Compustat 付费,或学术免费集)。
- **免费学术替代:** Jensen-Kelly-Pedersen《Global Factor Data》(JKP factors)提供已构建好的质量/利润因子收益与文档,可作**基准对照**(不是个股原料)。Fama-French/Ken French 数据库提供 RMW、CMA 现成因子收益(免费)。AQR 提供 QMJ 月度因子数据集(免费)。[高]

---

## 6) 落地到本系统(因子公式 / EDGAR 字段 / 脚本 / 验证)

### 6.1 建议的三个质量子因子(从简到全)
1. **`q_cash_prof`(首选,单因子)** = (经营利润 − 应计) / 资产,横截面 z。理由:Ball et al. 证据最强、扣成本友好、长期预测。
   - 经营利润 ≈ `Revenues − CostOfRevenue − SG&A`;应计 ≈ 经营利润 − `经营现金流`;故 ≈ `经营现金流 / Assets`(粗代理)。
2. **`q_gross_prof`** = (`Revenues` − `CostOfRevenue`) / `Assets`(Novy-Marx),做对照基准。
3. **`q_qmj`(全维)** = z(Prof + Growth + Safety + Payout),按 §2.4 公式。先实现 Prof+Safety 两维(数据最易),Growth/Payout 后补。

### 6.1b QMJ 子因子的一个最小可行版本(先做 Prof + Safety 两维)
```
# 每个交易日横截面内执行(only filed<=t 的数据)
Prof_raw  = z(GPOA) + z(ROA) + z(CFOA) + z(GMAR) + z(-ACC)
Safety_raw= z(-LEV) + z(-EVOL) + z(-beta) + z(-IVOL)   # 省略 O/Z 可后补
Quality   = z(z(Prof_raw) + z(Safety_raw))             # 两维等权,再 z 一次
# 信号 = Quality 的横截面排名;长腿=前30%,（可选）空腿=后30%
```
- 先省略 Growth(需 5 年历史)与 Payout(需现金流/融资活动逐项),数据到位后再补成完整四维。
- 关键:**每一步 z-score 都在"当日可见信息"的横截面上做**,不得用未来均值/方差。

### 6.2 护城河子因子(长期腿专属)
- **`moat_excess_roic`** = 近 5-10 年 (ROIC − WACC) 均值。WACC 可先用粗代理(无风险利率 + 行业 beta×ERP;债务成本用利息/有息债务)。
- **`moat_stability`** = − std(ROIC, 5-10y) 与 − std(毛利率, 5y) 的 z 合成。
- **复合护城河分** = z(`moat_excess_roic`) + z(`moat_stability`);可作为质量的"持续性增强"层。

### 6.3 数据脚本骨架(放 `scripts/`,本次不写文件)
```
# 伪代码 / 落地清单
1. universe: 从 EDGAR ticker→CIK 映射(company_tickers.json),含已退市票
2. pull: 对每个 CIK 调 companyfacts.json,带 UA,限速 <10/s,缓存到本地 parquet
3. PIT: 每条 fact 取 (concept, period_end, filed, value);
        按 filed 排序,构建 as-of 视图:某交易日只用 filed<=该日的最新值
        重述时保留首次 filed 版本(标 is_restatement)
4. factors: 在 as-of 视图上算 q_cash_prof / q_gross_prof / moat_*,横截面 z
5. align: 特征滞后到 filed + 1 个交易日,与价格/市值对齐
6. output: 写入 feed,接现有看板
```

### 6.4 验证纪律(承袭房子)
- **样本内 → 净·扣成本回测:** 月/季再平衡,扣双边成本 + 做空借券费;报告**净** decile spread 与 Rank-IC。
- **防过拟合:** Deflated Sharpe(按试验次数 N 通缩)、CSCV-PBO、单因子 **t > 3.0**(非 2.0)。
- **换手核查:** 质量应天然低换手(单边月 <50%),若回测出现高换手 → 多半是噪声/定义错误。
- **稳健性:** GP vs OP vs 现金利润三种定义都跑;若结论只在某一种成立则存疑。
- **基准对照:** 与 Ken French RMW、AQR QMJ、JKP 质量因子的收益做相关性/对齐检验,确认我们没有"重新发明且更差"。
- **相关性约束(见 §7):** 把质量与已有价值/低波因子做相关矩阵,避免重复下注。

---

## 7) 风险与反方观点

1. **样本内 / 毛收益虚高。** 几乎所有 Sharpe(1.2)、alpha(0.52%/月)都是样本内、毛收益。落地必扣成本 + Deflated Sharpe;经验折扣 30-50%。[高]
2. **后发布衰减 + 拥挤。** ~50% 异象 alpha 发布后消失;质量因子已被 ETF(如 MOAT、QUAL)规模化,部分溢价或被套利。质量比反转抗拥挤,但非免疫。[中]
3. **"质量"定义不收敛 = 研究者自由度。** GP / OP / 现金利润 / QMJ 四维 / ROIC 持续性,定义众多 → 易被 p-hacking。必须固定口径并多定义稳健性检验。[高]
4. **ROIC 均值回归是铁律。** 高 ROIC 大概率向 WACC 衰减;买"当前高 ROIC"未必买到"未来持续高 ROIC"。须建衰减曲线、区分水平 vs 持续性。[中-高]
5. **质量可能只是价值/低波的影子。** 质量与低波正相关;部分质量溢价可能被 BAB/低波解释。需做因子正交化、控制 BAB 后看残余 alpha。[中]
6. **行为解释 ≠ 风险补偿,可逆。** AFP 倾向"市场对质量定价不足"(行为),若市场学会定价,溢价可消失;Morningstar 护城河含主观成分,无法完全量化复制。[中]
7. **"假质量"陷阱。** 杠杆驱动的高 ROE、会计利润(高应计)驱动的高利润率会反转 → 现金利润 + DuPont 拆解 + 安全维(低杠杆)是必要防护。[高]
8. **PIT/前视风险在数据层。** 用 period-end 而非 filed 对齐、混入重述值,会系统性高估质量因子。这是最隐蔽、最致命的偏差。[高]

---

## 8) 参考来源(URL + 可信度)

**质量/利润率因子(一手):**
- Novy-Marx (2013) *The Other Side of Value: The Gross Profitability Premium*, JFE — https://oldschoolvalue-files.s3.amazonaws.com/pdf/Novy-Marx_Gross-Profitability-Anomaly_JFE_2013.pdf [高]
- NBER 版 *The Other Side of Value: Good Growth and the Gross Profitability Premium* — https://www.nber.org/papers/w15940 [高]
- Fama & French (2015) *A Five-Factor Asset Pricing Model* (RMW/OP 定义) — https://tevgeniou.github.io/EquityRiskFactors/bibliography/FiveFactor.pdf [高]
- Ball, Gerakos, Linnainmaa, Nikolaev (2016) *Accruals, Cash Flows, and Operating Profitability in the Cross Section of Stock Returns*, JFE — https://faculty.tuck.dartmouth.edu/images/uploads/faculty/joseph-gerakos/Ball,_Gerakos,_Linnainmaa,_et_al._2016.pdf [高]
- Asness, Frazzini, Pedersen *Quality Minus Junk* (AQR) — https://www.aqr.com/Insights/Research/Working-Paper/Quality-Minus-Junk [高]
- QMJ 工作论文 PDF(AQR) — https://images.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/Quality-Minus-Junk.pdf [高]
- QMJ SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2312432 [高]
- CRAN `qmj` 包文档(QMJ 公式实现,交叉确认变量) — https://cran.r-project.org/web/packages/qmj/vignettes/qmj.pdf [中]

**净成本 / 拥挤 / 衰减:**
- Novy-Marx & Velikov *A Taxonomy of Anomalies and Their Trading Costs*, RFS — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2535173 [高]
- Detzel, Novy-Marx, Velikov *Model Comparison with Transaction Costs* (2023) — https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4269265_code1536992.pdf?abstractid=3805379 [高]
- NBER (2025) *Profitability Retrospective: What Have We Learned?* — https://www.nber.org/system/files/working_papers/w33601/w33601.pdf [高｜内容未逐字核实(PDF 解析失败),仅引为存在性]
- T. Rowe Price (2024) *The quality factor: its impact, foundation, and evolution* — https://www.troweprice.com/institutional/se/en/insights/articles/2024/q2/the-quality-factor-its-impact-foundation-and-evolution.html [中]
- arXiv (2025) *Not All Factors Crowd Equally* — https://arxiv.org/pdf/2512.11913 [中]

**护城河 / ROIC 持续性:**
- Morningstar *Equity Research Methodology* (2023-06-14) — https://s205.q4cdn.com/437373358/files/doc_downloads/2025/07/Morningstar-Equity-Research-Methodology-2023-06-14.pdf [高]
- Morningstar *The Morningstar Economic Moat Rating* — https://www.morningstar.com/stocks/morningstar-economic-moat-rating-3 [中-高]
- Morgan Stanley/Counterpoint (Mauboussin) *Measuring the Moat* — https://www.morganstanley.com/im/publication/insights/articles/article_measuringthemoat.pdf [高]
- Mauboussin ROIC 持续性/CAP(二手汇总) — https://greenbackd.com/2010/04/21/roic-and-reversion-to-the-mean-part-1/ [中｜二手]

**相关性 / 分散:**
- MSCI *Quality Time — Understanding Factor Investing*(质量与价值/低波相关性) — https://www.msci.com/documents/10199/4c5bd381-5b29-453e-ad73-6df24290a172 [中-高]
- alphaarchitect *Combining Value and Profitability Factors to Improve Performance* — https://alphaarchitect.com/combining-value-and-profitability-factors-to-improve-performance/ [中]

**数据 / EDGAR:**
- SEC EDGAR APIs 官方 — https://www.sec.gov/search-filings/edgar-application-programming-interfaces [高]
- JKP *Global Factor Data Documentation*(Jensen-Kelly-Pedersen) — https://jkpfactors.s3.amazonaws.com/documents/Documentation.pdf [高]
- AQR QMJ Factors Monthly(免费数据集) — https://www.aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly [高]

---
*生成:2026-06-18。所有"高"可信度结论均来自一手论文/官方文档;"中"为二手或口径非学术;标"未核实/仅引为存在性"者表示一手 PDF 自动解析失败,数字未逐字确认。落地前务必以净·扣成本回测 + Deflated Sharpe + PBO 复核。*
