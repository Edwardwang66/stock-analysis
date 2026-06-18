# 盈余质量与财务造假/暴雷规避 — 长期持有的下行保护

> 主题:把"盈余质量/红旗"指标当作**长期组合的剔除规则**(避免 -90% 暴雷),而非选股 alpha。
> 货币:净·扣成本。所有指标可从 SEC EDGAR XBRL 三表免费、PIT 计算。
> 日期:2026-06-18。可信度分级:**A**=同行评审/原始论文/监管原文;**B**=从业者一手研究/质量二手;**C**=百科/博客/营销页(仅作公式核对)。
> 凡无法核实之处标注 **[未核实]**。

---

## 1) TL;DR

- **这一类指标的正确用途是"剔除/降权",不是"选股"。** 应计异象的多空 alpha 在 2003 年后基本被套利掉(见 §3);但"高应计 / 高 M-Score / 低 F-Score / 低 Z-Score"作为**负面筛(避免持有最差的 5-10% 公司)**仍有经济意义,因为暴雷是**左尾、非对称**事件——剔除一个 -90% 的标的对长期复利的贡献远大于多抓一个 +20%。
- **五个工具,分工不同:**
  - **Sloan 应计(1996)**:盈余质量。高应计=盈余更多来自非现金估计=未来盈余/回报更低、更易反转。**A级**证据,但 alpha 已衰减。
  - **Beneish M-Score(1999)**:8 变量盈余操纵概率模型,阈值 **−1.78**。识别 Enron 的著名案例。作为**剔除**用途仍是"最经济可行"的 fraud 模型(2022,**A**)。
  - **Piotroski F-Score(2000)**:9 项二元财务健康打分(0-9)。**质量/财务体质过滤**,剔除低分(0-3)。
  - **Montier C-Score(2008)**:6 项"做账"红旗(0-6),≈M-Score 的简化版,**从业者(B)**。
  - **Altman Z-Score(1968)**:破产风险判别(<1.81 危险区)。**直接的暴雷/破产保护。**
- **诚实警告:** 全部都有**假阳性**(误杀好公司)和**失效场景**(行业不适用、轻资产、银行/金融、负权益、并购噪声)。它们是概率红旗,**不能证实造假**。应作为"需人工复核 / 降权 / 排除"的触发器,不是自动卖出信号。
- **落地:** 三表 → us-gaap XBRL 标签 → 计算 5 个分数 → 形成一个 PIT 的"红旗向量",对组合做硬剔除(Z<1.81 或 M>−1.78)+ 软降权(应计分位、F<3)。需做**前视/幸存者偏差**审计:用 filing 日期而非财年末做 PIT 对齐。

---

## 2) 各指标完整公式 + 阈值

### 2.1 Sloan 应计异象(Accruals)

**核心思想(Sloan 1996, *The Accounting Review*):** 盈余 = 现金部分 + 应计部分。应计部分**持续性更低**,但市场"盯住"报告盈余、未区分两者的持续性,于是**高应计公司未来盈余易反转、未来回报偏低**。原始多空对冲(做多低应计/做空高应计)约 **~10–12%/年**(1962–1991 样本)。**[A级]**

**资产负债表法应计(原始定义,Sloan 1996):**

```
Accruals = (ΔCA − ΔCash) − (ΔCL − ΔSTD − ΔTaxPayable) − Depreciation
其中 ΔCA=流动资产变动, ΔCL=流动负债变动, ΔSTD=流动负债中短期债务变动
Accruals_scaled = Accruals / Average Total Assets
```

**现金流量表法应计(更稳健,Hribar & Collins 2002 推荐,避免并购/汇率污染):**

```
Accruals = Net Income − Cash Flow from Operations (CFO)
Accruals_scaled = (NI − CFO) / Average Total Assets
```
> 现金流量表法更优,因为资产负债表差分会把并购、剥离、外币折算误记为应计。**[A级:Hribar & Collins 2002]**

**用作剔除规则:** 不取多空,只**剔除/降权应计最高的十分位(decile 10)**。高 |应计| 也用作 §2.4 C-Score 和 §2.2 M-Score 的输入。

---

### 2.2 Beneish M-Score(盈余操纵概率)

**来源:** Beneish, M. D. (1999), "The Detection of Earnings Manipulation," *Financial Analysts Journal* 55(5). 基于 1982–1992 的操纵 vs 非操纵公司 probit 模型。**[A级]**

**8 变量(全部 = 本期/上期之比,除 TATA):**

| 变量 | 名称 | 公式 |
|---|---|---|
| DSRI | Days Sales in Receivables Index | (Receivables_t / Sales_t) / (Receivables_{t-1} / Sales_{t-1}) |
| GMI | Gross Margin Index | [(Sales_{t-1}−COGS_{t-1})/Sales_{t-1}] / [(Sales_t−COGS_t)/Sales_t] |
| AQI | Asset Quality Index | [1−(CA_t+PPE_t+Securities_t)/TA_t] / [1−(CA_{t-1}+PPE_{t-1}+Securities_{t-1})/TA_{t-1}] |
| SGI | Sales Growth Index | Sales_t / Sales_{t-1} |
| DEPI | Depreciation Index | [Dep_{t-1}/(Dep_{t-1}+PPE_{t-1})] / [Dep_t/(Dep_t+PPE_t)] |
| SGAI | SG&A Index | (SGA_t/Sales_t) / (SGA_{t-1}/Sales_{t-1}) |
| LVGI | Leverage Index | [(CL_t+LTD_t)/TA_t] / [(CL_{t-1}+LTD_{t-1})/TA_{t-1}] |
| TATA | Total Accruals to Total Assets | (ΔWorkingCapital − ΔCash − Dep) / Total Assets;实务常用 (NI − CFO)/TA |

**8 变量 M-Score 公式:**

```
M = −4.84 + 0.920·DSRI + 0.528·GMI + 0.404·AQI + 0.892·SGI
        + 0.115·DEPI − 0.172·SGAI + 4.679·TATA − 0.327·LVGI
```

**阈值:**
- **M > −1.78 → 可能为操纵者(红旗)。** M < −1.78 → 不太可能。**[C级核对:Wikipedia / DayTrading;A级原文一致]**
- 注:有些实现用更保守的 **−2.22**(发现概率最高的截点)。**[未核实是否为 Beneish 原文阈值;Wikipedia 仅列 −1.78]**
- 还有一个 **5 变量简化版**(去掉数据要求高的 SGAI/DEPI/LVGI),常用于数据缺失时。**[B级]**

**直观:** DSRI↑(应收涨太快=可能压货/虚增收入)、TATA↑(应计占比高=盈余更"软")、SGI↑(高增长公司更有操纵动机)是权重最大的红旗。

**著名案例:** 1998 年 Cornell 学生用 M-Score 把 **Enron** 判为盈余操纵者,当时华尔街仍在"买入"评级。**[C级:Wikipedia;广为引用]**

---

### 2.3 Piotroski F-Score(财务体质质量过滤)

**来源:** Piotroski, J. (2000), "Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers," *Journal of Accounting Research* 38. 在**高 B/M(价值股)**里,买高 F-Score、避低 F-Score。**[A级]**

**9 项二元(满足=1,共 0–9):**

*盈利性(4):*
1. ROA > 0(本期净利为正)→ 1
2. CFO > 0(经营现金流为正)→ 1
3. ΔROA > 0(ROA 同比改善)→ 1
4. CFO/TA > ROA(应计质量:经营现金流强于会计利润)→ 1 ← **盈余质量项**

*杠杆/流动性/融资(3):*
5. ΔLong-term Leverage < 0(长期负债率下降)→ 1
6. ΔCurrent Ratio > 0(流动比率改善)→ 1
7. 未增发新股(无稀释)→ 1

*经营效率(2):*
8. ΔGross Margin > 0(毛利率改善)→ 1
9. ΔAsset Turnover > 0(资产周转率改善)→ 1

**用作过滤:** 强=8–9,弱=0–2(部分来源用 0–3)。**剔除规则用 F ≤ 2(或 ≤3)**,尤其在价值/低估区。**[C级核对:Wikipedia;A级原文一致]**

---

### 2.4 Montier C-Score(做账红旗,Cooking-the-books)

**来源:** Montier, J. (2008), "Cooking the Books, or, More Sailing Under the Black Flag," SG Global Strategy / *Mind Matters*(2008-06-30)。**[B级:从业者研报]**

**6 项红旗(命中=1,共 0–6,越高越差):**
1. 净利与经营现金流的差距**扩大**(NI 持续 > CFO)→ 1
2. **DSO(应收周转天数)上升** → 1(压货/虚增收入)
3. **DSI(存货周转天数)上升** → 1(滞销/存货堆积)
4. **其他流动资产/收入 上升** → 1(藏东西)
5. **折旧/毛 PPE 下降** → 1(拉长折旧年限做高利润)
6. **总资产高增长** → 1(连环并购掩盖)

**Montier 报告业绩(1993–2007):** 高 C-Score 股票美国跑输 ≈ **8%/年**、欧洲 ≈ **5%/年**。叠加 **市销率(P/S)>2** 的估值条件后,跑输放大到 **美国 ≈14%/年、欧洲 ≈17%/年**。**[B级:Montier 原研报 + quant-investing 转述]**

> C-Score 本质是 M-Score 的"无系数、计数版"——优点是直观、对数据缺失更鲁棒;缺点是无统计校准。

---

### 2.5 Altman Z-Score(破产/暴雷风险)

**来源:** Altman, E. (1968), *Journal of Finance*。多元判别分析,预测**制造业上市公司 2 年内破产**。**[A级]**

**原始(上市制造业)Z:**
```
Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
X1 = 营运资本 / 总资产         (Working Capital / TA)
X2 = 留存收益 / 总资产         (Retained Earnings / TA)
X3 = EBIT / 总资产
X4 = 股权市值 / 总负债账面值    (Market Cap / Total Liabilities)
X5 = 销售 / 总资产
```
**分区:** Z > 2.99 安全;1.81 ≤ Z ≤ 2.99 灰区;**Z < 1.81 危险(破产风险高)**。**[C级核对一致]**

**变体(用于非制造业/私企/新兴市场——更适合通用组合):**
- **Z'(私企,用账面权益替代市值 X4):** `Z' = 0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5`;危险 < 1.23,安全 > 2.90。**[B级]**
- **Z''(非制造业/新兴市场,去掉 X5):** `Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4`;危险 < 1.10,安全 > 2.60。**[B级]** ← **建议跨行业组合默认用 Z''**,因为 X5(资产周转)行业差异巨大。

---

## 3) 证据:作为"剔除规则"的有效性(含可信度)

**(a) 应计异象的多空 alpha 已衰减——这正说明应"剔除"而非"做多空"。**
- Sloan(1996)原始 ~10–12%/年对冲收益,**持续约四十年至 ~2002**。**[A级]**
- **Green, Hand & Soliman(2011), "Going, Going, Gone? The Apparent Demise of the Accruals Anomaly," *Management Science*:** 美国应计异象在 2000 年代中后期"平均回报不再可靠为正",归因于**对冲基金 AUM 与极端应计股交易量上升**(套利)。**[A级]**
- **publication effect:** 论文发表 + 数据可得后,异象交易增加、收益衰减,在高换手机构/对冲基金中更明显。**[A级:综述证据]**
- **结论:** 不要把应计当 alpha 来榨;把它当**质量分层/剔除最差十分位**——左尾保护属性比 alpha 更持久。

**(b) M-Score 作为低成本 fraud 筛——2022 年再确认。**
- **Beneish & 合作者(2022, *The Accounting Review*):** M-Score 仍是"**最经济可行**"的 fraud 预测模型。示例:1 万家公司、~60 起真造假;新型 ML 模型抓 42 起(70%)但**误报 3,976 家(40% 的清白公司)**——"对多数决策者来说太多了"。M-Score 误报率低,实务上更可用。**[A级]**
- 原始样本内:识别 ~76% 操纵者,假阳性 ~17%(开发样本)。**[B/C级转述,需以原文为准;[未核实精确留出样本数字]]**

**(c) F-Score 的过滤价值。**
- Piotroski(2000)原文:在高 B/M 组内,**高 F-Score 组合的回报显著高于低 F-Score**,且多空价差可观(原文报约 23% 的两端价差,**[未核实精确数字]**)。**[A级:存在;数字待核]**
- 后续:F-Score 对**异象组合(价值/低应计)有增量过滤价值**,但在不同市场/时段有效性不一(如德国市场的 reality check)。**[A/B级]**

**(d) C-Score:** 仅 Montier 自研报业绩(§2.4),**无独立同行评审复制**。当作"M-Score 的直觉版红旗",可信度 **B**。

**(e) Z-Score:** 数十年广泛使用于信用/破产预测;作为**破产/退市左尾筛**有长期实证支撑(尤其 Z'' 跨行业版)。**[A级历史 + B级现代]**

**整体判断:** 作为**剔除规则**(避开最差分位)的证据,比作为**选股 alpha**的证据强得多且更持久。这与"下行保护"目标一致。

---

## 4) 假阳性 / 失效(诚实、可证伪)

**通用失效:**
- **不能证实造假**——只是概率红旗;合法的业务变化(高速扩张、商业模式转型、会计准则变更如 ASC 606/842、一次性项目)会触发假阳性。
- **行业不适用:** 银行/保险/REIT/资管(无 COGS、无常规存货、杠杆天然高)→ M/C/Z 全部失真。**金融股应单独建模或直接排除这些规则。**
- **轻资产/科技/生物:** 高增长 + 高无形 + 负留存收益 → SGI/AQI/X2 误报;Z-Score 对负留存收益公司系统性偏低。
- **负权益 / 巨亏:** Z、F 的多个比率分母/符号失稳。

**逐指标:**
- **M-Score:** 高增长公司(SGI、DSRI 高)天然 M 偏高 → **成长股假阳性**;并购年份 TATA/AQI 被污染;行业不可比(技术、地产波动大)。**[B级]**
- **C-Score:** 无统计校准;连环并购合法时第 6 项必触发;周期顶部存货上升非造假。
- **F-Score:** 周期股谷底改善 → 高 F 但前景差(反之亦然);成熟稳定公司"无改善"被扣分(惩罚优质慢公司);增发可能是良性融资却被扣分。
- **Z-Score:** 为 **1960s 制造业**校准;对现代轻资产、负权益、金融业失效;X4 用市值 → 与价格挂钩,会在已暴跌后才报警(滞后)。**Z'' 缓解但不消除。**
- **应计:** 现金流量表法依赖 CFO 质量;季节性营运资本波动制造噪声;**资产负债表法被并购/外币严重污染(故首选 NI−CFO 法)。**

**假阳性的代价:** 误杀好公司=机会成本(但**对"下行保护"目标可接受**:宁可错过也不暴雷)。假阴性(漏掉真暴雷)=灾难性。**因此把阈值调到"低假阴性",接受较高假阳性,再用人工复核挽回好公司。**

---

## 5) 数据与可得性(EDGAR 字段映射)

**数据源:** SEC EDGAR XBRL,免费、无 key、PIT 可得。
- CompanyFacts:`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`(零填充 10 位 CIK)
- CompanyConcept:`.../companyconcept/CIK##########/us-gaap/<Tag>.json`
- Frames(横截面):`.../frames/us-gaap/<Tag>/USD/CY2024Q4I.json`
- **限制:** ≤10 req/s,必须带 `User-Agent: Name email`。**[A级:SEC.gov API 文档]**
- **PIT 关键:** 每条 fact 带 `end`(财年末)与 **`filed`(报送日)**。**用 `filed` 做对齐**以避前视偏差;十分位/阈值的横截面也要用 filing 当时可得的数据。

**us-gaap 标签映射(主要项;实务需 fallback 列表,因公司用标签不一):**

| 概念 | 首选 us-gaap 标签 | Fallback / 备注 |
|---|---|---|
| 净利润 NI | `NetIncomeLoss` | `ProfitLoss` |
| 经营现金流 CFO | `NetCashProvidedByUsedInOperatingActivities` | `...ContinuingOperations` |
| 总资产 TA | `Assets` | — |
| 总负债 | `Liabilities` | `LiabilitiesAndStockholdersEquity` − Equity |
| 流动资产 CA | `AssetsCurrent` | — |
| 流动负债 CL | `LiabilitiesCurrent` | — |
| 现金 | `CashAndCashEquivalentsAtCarryingValue` | `CashCashEquivalentsRestricted...` |
| 应收 Receivables | `AccountsReceivableNetCurrent` | `ReceivablesNetCurrent` |
| 收入 Sales | `RevenueFromContractWithCustomerExcludingAssessedTax` | `Revenues`, `SalesRevenueNet` |
| COGS | `CostOfGoodsAndServicesSold` | `CostOfRevenue`, `CostOfGoodsSold` |
| 存货 | `InventoryNet` | — |
| PPE(净) | `PropertyPlantAndEquipmentNet` | 毛:`PropertyPlantAndEquipmentGross` |
| 折旧 Dep | `DepreciationDepletionAndAmortization` | `Depreciation`, `DepreciationAmortizationAndAccretionNet` |
| SG&A | `SellingGeneralAndAdministrativeExpense` | `GeneralAndAdministrativeExpense` |
| 长期债务 LTD | `LongTermDebtNoncurrent` | `LongTermDebt` |
| 留存收益 RE | `RetainedEarningsAccumulatedDeficit` | — |
| 营运资本 WC | `AssetsCurrent` − `LiabilitiesCurrent` | 计算项 |
| EBIT | `OperatingIncomeLoss` | NI + 利息 + 税 |
| 股权市值(X4) | 价格×股数 `EntityCommonStockSharesOutstanding` | 非 XBRL,需行情;否则用 Z''(免市值) |
| 增发(F#7) | `StockIssuedDuringPeriodSharesNewIssues` / Δ`CommonStockSharesOutstanding` | — |
| 短期债务(应计法) | `DebtCurrent` / `ShortTermBorrowings` | — |

> **标签缺失是常态**:同一概念跨公司/年份用不同标签,需 fallback 链 + 单位校验(USD vs shares)+ 维度(合并 vs 分部)去重。**[B级:实务经验]**
> **唯一非 EDGAR 输入** = X4 的股权市值(需价格)。若坚持纯 EDGAR/免费,**用 Z''(无 X4 市值版,但 X4 用账面权益)或直接以 Z' 私企版**绕开行情依赖。

---

## 6) 落地到本系统(剔除规则 / 脚本 / 验证)

**设计原则:这些是"剔除/降权门",不是 alpha 信号源。** 接在选股/打分之后,作为**最后一道下行保护过滤**。

**(a) 硬剔除(从可投域移除,不可豁免):**
- `Altman Z'' < 1.1`(非金融);或 `Z(原始) < 1.81`(制造业有市值时) → **排除**(破产/退市风险)。
- `M-Score > −1.78` **且** 应计在 top decile → **排除**(操纵 + 软盈余双确认,降假阳性)。
- 审计意见"持续经营存疑"(going concern,可从 8-K/10-K 文本解析) → **排除**。**[可选增强]**

**(b) 软降权(扣质量分,不直接剔除):**
- 应计十分位:decile 9–10 线性降权;decile 10 额外标红。
- `F-Score ≤ 2` → 重扣;`3–5` → 轻扣。
- `C-Score ≥ 4` → 标红需人工复核。
- M-Score 在 (−2.22, −1.78) 灰区 → 观察名单。

**(c) 金融/特殊行业护栏:** 银行/保险/REIT/资管(按 SIC 或 us-gaap 行业标签识别)**豁免 M/C/Z 规则**,改用专用杠杆/拨备指标或直接置于单独域。避免对无 COGS/无存货公司套用通用公式。

**(d) 双确认与人工复核队列:** 单一红旗→观察名单;**≥2 个独立红旗(如 M>−1.78 且 F≤3)→ 候选剔除 + 人工复核**。降低单指标假阳性误杀。

**(e) 脚本架构(伪代码,落到本系统 feed):**
```
edgar_fetch(cik)        -> companyfacts.json (缓存, UA, ≤10rps)
normalize_tags()        -> 统一标签 + fallback 链 + 单位/维度去重
build_pit_panel()       -> 按 filed 日对齐, 生成 t / t-1 PIT 快照
compute_scores():
    accruals = (NI - CFO) / avg(TA)          # Hribar-Collins 现金流法
    m_score  = beneish_8var(...)
    f_score  = piotroski_9(...)
    c_score  = montier_6(...)
    z        = altman_zdd(...)               # 默认 Z''
flag_vector()           -> {hard_exclude, soft_demote, review}
apply_to_universe()     -> 在组合构建前过滤/降权
```
- 输出进**看板**:每只持仓/候选的 5 维红旗 + 触发原因 + filing 链接(可证伪、可追溯)。
- 加 feed 告警:已持仓标的**新出现** Z 跌破阈值或 M 翻红 → 推送复核。

**(f) 验证(防过拟合 / 防前视):**
1. **PIT 审计:** 用 `filed` 日重建历史快照,确认任一历史日期的剔除决策只用当时可得数据。
2. **幸存者偏差:** 回测域必须含**已退市/破产**公司(EDGAR 保留退市前 filing);否则会高估规则有效性。
3. **事件研究:** 对历史已知暴雷(如会计造假被 SEC 处罚的样本,可从 SEC AAER 列表取)检验规则**是否在暴雷前 N 个季度翻红**(真阳性率);对清白龙头股检验**误杀率**(假阳性率)。
4. **净·扣成本:** 剔除规则降低换手即可,但要量化"被误杀好公司"的机会成本;报告**剔除前后组合的左尾(最大回撤、最差 5% 标的贡献)**而非只看均值。
5. **阈值不调参:** 沿用文献原始阈值(−1.78 / 1.81 / F≤2),**不在样本内优化**,避免过拟合(房子原则)。如需校准,用滚动样本外。

---

## 7) 风险与反方

- **数据质量风险:** XBRL 标签不一致、重述(restatement)、缺失 → 计算错误本身制造假阳/假阴。需严格单位/维度/fallback 处理与覆盖率监控。
- **滞后性:** 年报数据有报送滞后(财年末后数周到数月);最严重的快速暴雷(流动性危机、欺诈突然曝光)可能**早于下一期财报**,这些规则**抓不住**。Z-Score 的 X4 用市值时还会"在已跌后才报警"。
- **反方一:** 多数指标的**选股 alpha 已被套利/发表效应侵蚀**(§3a)。把它们当 alpha 会失望;只在"剔除/下行保护"框架下用才站得住。
- **反方二(假阳性 > 暴雷收益?):** 若假阳性误杀了大量优质成长股(M-Score 对高 SGI 偏严),长期可能**拖累收益超过它避免的暴雷**——必须用事件研究量化净效果,不能想当然。
- **反方三(已知即失效):** 造假者知道这些公式(尤其 M-Score 系数公开),可针对性地把指标做"漂亮"(规避 DSRI/TATA),使模型对**蓄意、精巧的欺诈**钝化。模型更擅长抓"粗糙/激进"的盈余管理。
- **反方四(行业/制度漂移):** Altman 1968、Beneish 1990s、Piotroski 1990s 的校准来自不同会计制度与经济结构;ASC 606/842、SaaS 递延收入、股权激励等使部分比率含义漂移。需定期重估、考虑只用方向(red flag)而非精确截点。
- **多重检验/组合相关:** 5 个指标高度相关(都吃应计/现金流口径),"≥2 红旗"未必是独立确认。需检查指标间相关性,避免伪双确认。

---

## 8) 参考来源(URL + 可信度)

**原始论文 / 学术(A):**
- Sloan, R. (1996), "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows About Future Earnings?" *The Accounting Review*. — 应计异象原始。**A**。综述/转述:Quantpedia <https://quantpedia.com/strategies/accrual-anomaly>(C 级转述)。
- Dechow, Khimich & Sloan, "The Accrual Anomaly," SSRN <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1793364> — 综述。**A/B**。
- Hribar & Collins (2002), "Errors in Estimating Accruals," *JAR* — 现金流法优于资产负债表法。**A**(本文按记忆引用,**[未核实精确卷期]**)。
- Green, Hand & Soliman (2011), "Going, Going, Gone? The Apparent Demise of the Accruals Anomaly," *Management Science* <https://pubsonline.informs.org/doi/10.1287/mnsc.1110.1320> — 应计 alpha 衰减/套利。**A**。
- Beneish, M. (1999), "The Detection of Earnings Manipulation," *Financial Analysts Journal* 55(5). — M-Score 原始。**A**(经多处一致转述)。
- Beneish 等 (2022), *The Accounting Review*,经 IU Kelley 转述:<https://blog.kelley.iu.edu/2022/02/17/kelley-professors-m-score-model-remains-most-viable-means-of-predicting-corporate-fraud/> — M-Score 仍最经济可行 vs ML。**A(原文)/B(转述)**。
- Piotroski, J. (2000), "Value Investing...," *Journal of Accounting Research* 38. — F-Score 原始。**A**。
- Altman, E. (1968), *Journal of Finance*. — Z-Score 原始。**A**。

**从业者一手(B):**
- Montier, J. (2008), "Cooking the Books..." SG/Mind Matters(PDF)<https://oldschoolvalue-files.s3.amazonaws.com/pdf/Montier_C_Score.pdf> — C-Score 原研报 + 业绩。**B**。
- Quant Investing — C-Score 转述/业绩 <https://www.quant-investing.com/blog/simple-ratios-help-you-identify-companies-that-cook-their-books-the-c-score>。**B/C**。
- Portfolio123 — M-Score 实务检验 <https://blog.portfolio123.com/detecting-financial-fraud-a-close-look-at-the-beneish-m-score/>。**B**。

**公式核对 / 二手(C):**
- Beneish M-score — Wikipedia <https://en.wikipedia.org/wiki/Beneish_M-score>(公式、−1.78、Enron 案例)。**C**。
- Piotroski F-score — Wikipedia <https://en.wikipedia.org/wiki/Piotroski_F-score>(9 准则)。**C**。
- Altman Z-score 公式/分区 — AccountingTools <https://www.accountingtools.com/articles/the-altman-z-score-formula.html>;WallStreetPrep <https://www.wallstreetprep.com/knowledge/altman-z-score/>。**C**。
- Beneish 公式细节 — DayTrading.com <https://www.daytrading.com/beneish-m-score>;StableBread <https://stablebread.com/beneish-m-score/>。**C**。

**数据/EDGAR(A 官方):**
- SEC EDGAR APIs(CompanyFacts/Concept/Frames,限速,UA 要求)<https://www.sec.gov/search-filings/edgar-application-programming-interfaces>。**A**。
- XBRL US — us-gaap 标签库 <https://xbrl.us/>;NetIncomeLoss 标签 <https://xbrl.us/home/tag/netincomeloss/>。**B**。
- EDGAR XBRL Python 教程 <https://tldrfiling.com/blog/sec-edgar-xbrl-api-python-tutorial>。**C**。

**待核实清单(诚实标注):**
- M-Score 第二阈值 **−2.22** 是否为 Beneish 原文 → **[未核实]**(Wikipedia 仅列 −1.78)。
- M-Score 留出样本"76% 识别 / 17% 假阳"的精确出处与样本 → **[未核实]**(二手转述)。
- Piotroski 原文高/低 F 两端价差精确数字(~23%?)→ **[未核实]**。
- Hribar & Collins (2002) 精确卷期页码 → **[未核实]**。
- 应计现金流量表法 vs 资产负债表法在**当前(2023–2026)** 美股的剔除规则有效性,缺独立最新复制 → **[未核实]**。
