# 股东回报因子:股息、回购、总股东收益 — 长期投资深度研究

> 目的:为成熟量化/投研系统的**长期(年度)价值替代因子**评估"股东回报"族(股息率、股息增长、回购收益、总股东收益/净派现收益),并给出可落地的 PIT 实现。
> 方法:fan-out 检索(Boudoukh 学派 / OSAM / Faber / 回购质量 / EDGAR XBRL)→ 一手来源核验 → 合成。
> 日期:2026-06-18。所有关键数字标注**来源 URL + 可信度(高/中/低)**。无法核实的标**"未核实"**。
> 立场:**净·扣成本是唯一货币。** 股东回报不是"派得多就好",而是"用便宜的钱买回便宜的股、且不被股权激励稀释抵消"。高息是陷阱,伪回购是会计幻觉;两者都要在因子里显式扣掉。
> 防伪标注:本报告涉及的所有长期回测均为**公开发表的样本内/作者自报**结果,按 §7 与 McLean-Pontiff 规则**至少打 4-6 折**后再用于预期。前视与幸存者偏差风险见 §7。

---

## 1) TL;DR

1. **"总股东收益"(股息 + 净回购)比单纯股息率是更稳健的价值/派现度量。** Boudoukh-Michaely-Richardson-Roberts(JF 2007)的核心实证:当用 **payout yield(股息+回购)** 与 **net payout yield(股息+回购−增发)** 替代股息率时,无论时序还是横截面的可预测性都"统计与经济上显著",而 1980s 后"股息预测力衰退"被大幅高估——因为公司把派现从股息转移到了回购。`high−low net payout yield` 是一个**被定价的因子**。[高｜onlinelibrary.wiley.com/10.1111/j.1540-6261.2007.01226.x;nber.org/.../w10651]

2. **股息率单独用会踩"高息陷阱"。** Ned Davis / Hartford 口径:**最高股息率五分位 1973–2024 年化跑输 S&P 500 约 1%**;而"股息增长者(dividend growers/initiators)"1973–2024 年化 **10.24%** vs 不派息者 **~负到个位数**,且波动更低。高息常常是分母(股价)崩塌的结果,不是质量信号。→ **股息率必须与"可持续性/增长"联用,不能单买高息。**[高(行业研究,口径自报)｜hartfordfunds.com/.../the-power-of-dividends.html]

3. **回购收益(buyback yield)要用"净"口径,否则被股权激励(SBC)做成伪回购。** 一家公司花市值 4% 回购、同时因 SBC 稀释 2%,真实净回购收益只有 2%;有研究称**约 36.9% 的回购只是冲销股权激励造成的稀释**(未独立核验,标行业来源)。**正确口径 = 用股本变动(期初/期末稀释后加权股数)算,而非读"回购金额"行。**[中｜tikr.com/blog/how-to-tell-if-stock-buybacks-are-actually-good;corpgov.law.harvard.edu 2019/10/30]

4. **回购在高估值时摧毁价值——这是诚实的反方。** Buffett(2012 致股东信):"价值在以高于内在价值的价格回购时被摧毁。" 实证:**62% 的公司若按季均额回购会比择时回购更好**(公司择时差);GE 2007 高位 123 亿回购、2009 低位增发即反例。→ **回购收益必须与"是否便宜"(估值)交互,高 buyback yield 叠加高估值不是利好。**[高｜corpgov.law.harvard.edu 2020/10/22;Buffett 2012 letter]

5. **OSAM / Faber 的"shareholder yield"是价值的稳健替代,但预期要打折。** OSAM:高 shareholder yield 组合**年化跑赢 All Stocks ~3.5%**;股息单独 1928–2009 跑赢 ~1.18%/年,加上净回购再增 ~1.92%/年。Faber 把 **净债务偿还** 也加进来(SY = 股息 + 净回购 + 净还债)。这些是**作者自报、样本内**口径。[中(自报)｜quant-investing.com;mebfaber.com Shareholder-Yield.pdf]

6. **数据完全可由 SEC EDGAR XBRL 免费、PIT 地取得。** 现金流量表:`PaymentsForRepurchaseOfCommonStock`、`PaymentsOfDividendsCommonStock`、`ProceedsFromIssuanceOfCommonStock`;股本:`WeightedAverageNumberOfDilutedSharesOutstanding` / `CommonStockSharesOutstanding`。用 `data.sec.gov/api/xbrl/companyconcept/...` 拉历史,按**财报可得日(filed date)而非财报期末**对齐,避免前视。[高｜sec.gov/.../edgar-application-programming-interfaces]

7. **本系统落地建议:** 把"股东回报"建成 **一个复合因子 + 三个质量闸门**:(a) 净股东收益 = (股息+净回购)/市值;(b) 闸门:净回购 vs 总回购的差(伪回购惩罚)、派现可持续性(FCF 覆盖、负债)、估值交互(贵则回购降权)。**先在自由现金流口径上构建,杜绝"读回购行就当净回购"的常见错误。**

---

## 2) 各收益度量定义 + 公式

记 `MktCap` = 期末普通股市值(或股价×稀释股数);所有流量取**过去 12 个月(TTM)**或最近完整财年。

| 度量 | 公式 | 含义 / 注意 |
|---|---|---|
| **股息率 Dividend Yield (DY)** | `普通股现金股息 / MktCap` | 只算普通股、剔除特别股息(避免一次性扭曲)。会踩高息陷阱。 |
| **股息增长 Dividend Growth** | `DPS_t / DPS_{t-k} − 1`(常 3–5 年 CAGR) | 信号在"连续增长/启动派息",非高水平。质量代理。 |
| **总回购收益 Gross Buyback Yield** | `回购支出 / MktCap` 或 `1 − 股数_t/股数_{t-1}`(仅减少) | **会被 SBC 注水。不要单用。** |
| **净回购收益 Net Buyback Yield (NBY)** | `(回购 − 增发) / MktCap`;或股本口径 `(稀释股数_{t-1} − 稀释股数_t)/稀释股数_{t-1}` | **首选口径。** 股本法天然包含 SBC 行权增发。 |
| **总股东收益 / 派现收益 Payout Yield** | `(股息 + 回购) / MktCap` | Boudoukh 的 payout(未减增发)。 |
| **净派现收益 Net Payout Yield (NPY)** | `(股息 + 回购 − 增发) / MktCap` | **Boudoukh 核心被定价因子。** = DY + NBY。 |
| **股东收益 Shareholder Yield (SY, Faber)** | `股息 + 净回购 + 净债务偿还` ÷ MktCap | Faber 扩展:把"还债"也视为对股东(企业价值口径)的回报。 |
| **总股东回报 Total Shareholder Return (TSR)** | `(价格涨幅 + 已派股息再投资)` | 注意:TSR 是**结果/绩效度量**,不是事前因子,勿与上面混用。 |

**口径要点(可证伪):**
- **优先股本法算净回购**:`NBY = (D_shares_{t-1} − D_shares_t)/D_shares_{t-1}`,D_shares = 稀释后加权股数。它一步把 SBC 行权、增发、ATM、可转债转股都吃进去,比"回购行−增发行"更难造假。[中｜wallstreetprep.com/knowledge/buyback-yield]
- **现金流法做交叉验证**:`NBY ≈ (回购支出 − 普通股发行所得)/MktCap`。两法背离 = 红旗(大量非现金 SBC 或并购对价发股)。
- **NPY = DY + NBY** 是 §3 证据最强的复合度量;本系统主因子建议用它。

---

## 3) 长期净收益证据(标来源可信度)

> 提醒:以下均为**公开发表/作者自报**,样本内或发表前口径。按 McLean-Pontiff(2016)"发表后衰减 ~58%、样本外低 ~26%"规则,落地预期至少打 4-6 折(见前序报告 §1.5)。[高｜ssrn 2156623]

### 3.1 Boudoukh et al. (JF 2007) — 学术基石(可信度:高)
- 标题:*On the Importance of Measuring Payout Yield: Implications for Empirical Asset Pricing*,Journal of Finance 62(2): 877–915。
- 核心结论(直接来自 Wiley/NBER 摘要):用 **payout yield 与 net payout yield** 替代 dividend yield 后,**时序可预测性在短、长 horizon 均统计与经济显著**;两者对**横截面预期收益的信息超过股息率**;**`high−low payout yield` 是被定价的因子**。
- 机制:股息−价格比的过程在样本期剧变,但**总派现比几乎没变**——"股息预测力衰退"被高估,因为派现迁移到了回购。
- 一手:[onlinelibrary.wiley.com/doi/full/10.1111/j.1540-6261.2007.01226.x] / 工作论文 [nber.org/system/files/working_papers/w12847/w12847.pdf]。可信度:**高(顶刊、原文摘要)**。

### 3.2 Net Payout Yield 复现(Quantpedia,可信度:中)
- 定义沿用 Boudoukh:`(股息 + 回购 − 普通股增发)/ 年末市值`,**用现金流口径的回购**(非库存股变动)。
- 自报回测:**1984–2003**,NYSE/AMEX/NASDAQ 全体(~1000 标的),**年度 6 月底再平衡**,long-only **年化 22.13%**(月度几何 1.68%),最大回撤 **−52.5%**;未给夏普。
- 来源:[quantpedia.com/strategies/net-payout-yield-effect]。可信度:**中(第三方复现、自报、未扣实盘成本、long-only 高回撤)**。

### 3.3 OSAM / O'Shaughnessy — shareholder yield 作为价值替代(可信度:中,自报)
- 定义:**SY = 股息率(过去 12 月,剔特别股息) + 净回购率(今 vs 一年前稀释股数变动)**。
- 自报:高 SY 组合**跑赢 All Stocks 约 3.5%/年**;1928–2009 高股息单独跑赢 CRSP 大盘 **~1.18%/年**,**加上净回购再 +1.92%/年**。
- 机制论点:回购是"便宜时管理层用真金白银说股票被低估"的信号 → 兼具价值与质量。
- 来源:[osam.com/Commentary/the-factor-archives-shareholder-yield](2026-06 抓取返回 500,内容据搜索摘要);白皮书 [osam.com/pdfs/research/OSAM_Shareholder_Yield_Whitepaper.pdf]。可信度:**中(资管自报、含构建自由度、样本内)**。

### 3.4 Mebane Faber — shareholder yield(可信度:中,自报)
- 定义扩展:**SY = 股息 + 净回购 + 净债务偿还**(企业价值视角)。
- 第三方(Validea)实现自报:**1998–2024 价格年化 8.2% vs S&P 500 6.1%**;另一组合自 2009 用"季度再平衡 + 10 股"录得 2299.6% 总回报(**极小组合、择优口径,容量与过拟合风险高,谨慎**)。
- 重要限定:**美国公司回购占盈利比例高于海外**,故 SY 在海外的增益小于美国。
- 来源:[mebfaber.com/.../Shareholder-Yield.pdf](PDF 二进制未能解析正文,数字据 Validea 摘要);[validea.com/meb-faber]。可信度:**中(自报、第三方实现、小组合)**。

### 3.5 股息增长 vs 高息(可信度:高,行业研究口径)
- Hartford/Ned Davis(1973–2024):**$100 投于"股息增长者"→ ~$15,874;不增长者 → $2,983;不派息者 → $899;削减/取消者 → $63。** 增长者**总回报更高、波动更低**。
- 高息陷阱:**最高股息率五分位年化跑输 S&P 500 ~1%**。
- 来源:[hartfordfunds.com/insights/market-perspectives/equity/the-power-of-dividends.html]。可信度:**高(广被引用,但为资管口径、含再平衡与生存者处理细节未全披露)**。

---

## 4) 伪回购 / 陷阱识别

**4.1 伪回购(buyback to offset SBC dilution)**
- 现象:回购 $500M、同期 SBC 发股 $600M → 标题"大手笔回购",股数反增。约 **36.9% 的回购仅冲销股权激励稀释**(**未核实**,行业引用)。[中｜corpgov.law.harvard.edu 2019/10/30;tikr.com]
- 识别(可落地):
  - **红旗1 — 总回购 ≫ 净回购**:`gross_BY − net_BY` 大 → 大量增发抵消。阈值示例:差值 > 总回购的 50%。
  - **红旗2 — SBC/营收 或 SBC/FCF 高**:从现金流量表 `ShareBasedCompensation` 取。科技/成长股尤甚。
  - **红旗3 — 稀释股数不降反升**:`WeightedAverageNumberOfDilutedSharesOutstanding` 同比上行,即使现金流有回购行。
- **因子处理**:主因子一律用**股本法净回购**;另设惩罚项 `−w·(gross_BY − net_BY)`,把"花钱回购但股数没降"显式扣分。

**4.2 高息陷阱(yield trap)**
- 高 DY 常源于股价崩塌或不可持续派息。识别:
  - **派息率 > 100%**(股息 > 盈利/FCF)、**负 FCF 覆盖**、**高净负债/EBITDA**、**近 12 月股价大跌驱动的 DY 抬升**。
  - 价值面叠加:DY 高但毛利/ROIC 差 = 价值陷阱。
- **因子处理**:DY 与**股息可持续性闸门**(FCF 覆盖 ≥1.2、派息率 ≤ 阈值)联用;或直接用"**股息增长/启动**"信号替代"高水平股息"。

**4.3 高估值回购(value-destroying buyback)**
- 高 buyback yield 若发生在**高估值**(高 P/B、P/FCF、低 earnings yield)上,是摧毁价值。
- **因子处理**:`net_payout_yield × cheapness`(与估值因子交互);或在贵的分位里给回购收益降权。**单独追高回购收益 = 危险**。[高｜corpgov.law.harvard.edu 2020/10/22]

**4.4 一次性/会计噪声**
- 特别股息、并购对价发股、ATM 增发、可转债转股都会污染流量。**剔特别股息、用股本法吸收非现金发股、用 TTM 平滑季度跳变。**

---

## 5) 数据与可得性(EDGAR XBRL 字段)

**5.1 免费 PIT 来源:SEC EDGAR XBRL API**(无需 key,需 User-Agent,≤10 req/s)
- 端点(CIK 补零到 10 位):
  - `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/<TAG>.json` — 单公司单概念历史序列。
  - `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` — 单公司全部已标注事实。
  - `https://data.sec.gov/api/xbrl/frames/us-gaap/<TAG>/USD/CY2024Q4I.json` — 横截面("所有公司某期某概念"),适合批量截面构建。
- 硬性要求:**`User-Agent: Name email` 头**(缺失返 403);**≤10 请求/秒**(超限 429/封 IP)。无每日上限。
- 来源:[sec.gov/search-filings/edgar-application-programming-interfaces]。可信度:**高(SEC 官方)**。

**5.2 关键 us-gaap 标签**

| 用途 | 主标签 | 备用 / 备注 |
|---|---|---|
| 回购支出(现金流融资) | `PaymentsForRepurchaseOfCommonStock` | `PaymentsForRepurchaseOfEquity`(含优先股)、`PaymentsForRepurchaseOfCommonStockForEmployeeTaxes`(剔除) |
| 普通股现金股息 | `PaymentsOfDividendsCommonStock` | `PaymentsOfDividends`(含优先,需拆)、`Dividends` |
| 普通股增发所得 | `ProceedsFromIssuanceOfCommonStock` | `ProceedsFromIssuanceOfSharesUnderIncentiveAndShareBasedCompensationPlansIncludingStockOptions` |
| 股权激励费用(伪回购探测) | `ShareBasedCompensation` | — |
| 稀释加权股数(净回购股本法) | `WeightedAverageNumberOfDilutedSharesOutstanding` | `WeightedAverageNumberOfSharesOutstandingBasic` |
| 期末在外股数 | `CommonStockSharesOutstanding` | 封面 `dei:EntityCommonStockSharesOutstanding`(更接近 PIT) |
| 每股股息 | `CommonStockDividendsPerShareDeclared` | 算股息增长用 |

来源(标签语义):[xbrl.us/data-rule/guid-cashflows/];[sec.gov XBRL API]。可信度:**高(标签定义)/ 中(各公司标注一致性参差,需清洗)**。

**5.3 PIT / 前视纪律(硬要求)**
- **用 filing 日(`filed`)而非财报期末对齐**:companyfacts 每个 fact 含 `end`(期末)与 `filed`(报送日);因子在 `filed + 缓冲(如 1–2 交易日)`后才可用,否则前视。
- **TTM 滚动**用最近 4 个季度且 `filed` 已到。**重述**(后续修订同一期)只能用首次报送值做 PIT,不能用最终修订值回填。
- **市值用因子日当天**价格 × 当时最近已报股数,不能用未来股数。
- **特别股息/并购发股**单独标记剔除。

**5.4 覆盖与局限**
- XBRL 结构化标注主要覆盖 **~2009 年后**;更早需解析正文或用其他源,长样本回测有**起点偏差**。
- 标签使用不统一(自定义扩展、维度成员拆分)→ 需建标签优先级链 + 人工抽检。
- ADR/外国私募发行人(20-F/40-F)标注稀疏;非美覆盖差。

---

## 6) 落地到本系统(因子 / 脚本 / 验证)

**6.1 因子定义(建议主因子 = Net Payout Yield + 质量闸门)**
```
# 概念(伪代码,均为 PIT,TTM)
DY   = ttm(PaymentsOfDividendsCommonStock_excl_special) / mktcap
NBY_cf = (ttm(PaymentsForRepurchaseOfCommonStock)
          - ttm(ProceedsFromIssuanceOfCommonStock)) / mktcap
NBY_sh = (diluted_shares[t-4q] - diluted_shares[t]) / diluted_shares[t-4q]   # 首选
NBY  = NBY_sh                       # 股本法为主,NBY_cf 做交叉验证
NPY  = DY + NBY                     # 主因子(Boudoukh net payout yield)

# 伪回购惩罚
gross_BY = ttm(PaymentsForRepurchaseOfCommonStock) / mktcap
fake_pen = max(0, gross_BY - max(NBY,0))      # 花钱回购但股数没降
sbc_ratio = ttm(ShareBasedCompensation) / ttm(FCF)

# 可持续性闸门(股息)
cover = ttm(FCF) / ttm(dividends+buybacks)    # >=1.2 视为可持续
payout_ratio = ttm(dividends) / ttm(net_income)

# 估值交互(避免高估值回购)
ey = ttm(FCF) / ev                            # cheapness
score = z(NPY) - w1*z(fake_pen) - w2*z(sbc_ratio) \
        + w3*z(NPY)*z(ey) - w4*trap_flag
```
- **`trap_flag`**:`payout_ratio>1 或 cover<1 或 net_debt/EBITDA 高 或 近12月价格暴跌驱动DY`。
- 权重 `w*` 由验证集定,**不在全样本调参**(防过拟合)。

**6.2 脚本(放到现有 `scripts/`,沿用本系统 feed/PIT 治理)**
- `fetch_edgar_payout.py`:遍历 universe 的 CIK,拉 7 个标签的 companyconcept,落地 `(cik, end, filed, tag, val)` 长表;带 User-Agent、≤10 req/s 限流、429 退避、本地缓存。
- `build_payout_factors.py`:按 `filed` 对齐做 PIT TTM,算 DY/NBY/NPY/gross_BY/fake_pen/cover;输出截面因子表。
- `validate_payout.py`:见 6.3。
- 复用现有看板/feed 把 NPY 截面分位与红旗股推送。

**6.3 验证(沿用房子防过拟合纪律)**
- **分层回测**:NPY 十分位,看单调性 + 多空价差,**扣换手成本后**评估(派现因子换手低,成本友好,是其优点)。
- **去重/正交化**:NPY 与现有 Value(HML/EY)高度相关 → 报告**对 Value 正交化后的增量 IC**(Boudoukh 的卖点正是"超过 DY 的信息",要复现这一增量)。
- **Purged K-Fold + Embargo / CPCV**,**Deflated Sharpe**(记录试验次数 N),新因子门槛 **t>3.0**。
- **子样本稳健性**:1973–2000 / 2000–2010 / 2010–2026 分段;回购占比上升使近 20 年 NBY 权重更大,检查时变。
- **前视审计**:随机抽 30 个 `(cik, factor_date)` 人工核对所用 fact 的 `filed ≤ factor_date`。
- **伪回购单测**:对已知大 SBC 公司(大型科技股)断言 `NBY_sh < gross_BY`,否则口径错。

**6.4 与本系统中频 stat-arb 的关系**
- 这是**年度 horizon** 因子,换手低、容量大,**与中频信号互补**,适合作为多空组合的"慢腿"或风险约束(避免做空高净派现、便宜的公司)。

---

## 7) 风险与反方

1. **回购在高估值摧毁价值。** 高 buyback yield 非无条件利好;**62% 公司择时差**,按季均额更优。→ 必须与 cheapness 交互。[高｜corpgov.law.harvard.edu 2020/10/22]
2. **数据起点 / 生存者偏差。** XBRL ~2009 后才全;长回测要么截短、要么混源 → 起点偏差。退市/被并购公司若从 universe 删除则高估收益。**回测须含已退市标的。**(前视/幸存者风险:**已标注,需在实现中处理**)
3. **发表后衰减与拥挤。** Shareholder yield 已被 ETF 化(如 SYLD/CSD 等)与广泛宣传;McLean-Pontiff 规则下增量 alpha 应大幅打折,且可能拥挤。[高｜ssrn 2156623]
4. **自报回测的构建自由度。** OSAM/Faber 数字含再平衡频率、组合规模(10 股)、剔除规则等自由度,**非扣成本净值、非严格样本外**。可信度标"中"。
5. **税制 / 政策变化。** 2023 起美国 **1% 回购消费税** 改变回购−股息相对吸引力;SBC 与回购税互动改变"伪回购"经济性。[中｜matthewssouth.com/stock-based-compensation]
6. **标签不一致 / 重述。** us-gaap 标注参差、公司用自定义扩展、财报重述 → 净回购口径噪声大,需清洗与 PIT 重述处理。
7. **行业偏置。** 高派现集中在成熟/现金牛行业(公用、金融、能源),NPY 因子可能变成行业押注 → 建议**行业中性化**后再评估。
8. **反方观点(诚实):** 部分研究认为回购长期**不必然**摧毁价值(Harvard corpgov 2020/10/22 标题即"Do buybacks really destroy long-term value?"持质疑),证据双向,勿把"回购=坏"绝对化;关键是**估值条件下的**好坏。

---

## 8) 参考来源(URL + 可信度)

**学术 / 一手**
- Boudoukh, Michaely, Richardson, Roberts, *On the Importance of Measuring Payout Yield*, JF 2007 — [onlinelibrary.wiley.com/doi/full/10.1111/j.1540-6261.2007.01226.x] / NBER WP [nber.org/system/files/working_papers/w12847/w12847.pdf] / SSRN [papers.ssrn.com/sol3/papers.cfm?abstract_id=480171]。**高**。
- McLean & Pontiff, *Does Academic Research Destroy Return Predictability?* — [papers.ssrn.com SSRN 2156623]。**高**(用于衰减打折)。
- Buffett 2012 Shareholder Letter(回购高于内在价值摧毁价值)— [berkshirehathaway.com/letters/2012ltr.pdf]。**高**(原始)。

**因子证据(资管自报,中)**
- O'Shaughnessy (OSAM), *The Factor Archives: Shareholder Yield* — [osam.com/Commentary/the-factor-archives-shareholder-yield](2026-06 抓取 HTTP 500,数字据搜索摘要)。**中**。
- OSAM Shareholder Yield Whitepaper(PDF)— [osam.com/pdfs/research/OSAM_Shareholder_Yield_Whitepaper.pdf]。**中**。
- Meb Faber, *Shareholder Yield* — [mebfaber.com/wp-content/uploads/2023/05/Shareholder-Yield.pdf](PDF 正文未解析);Validea 实现 [validea.com/meb-faber]。**中**。
- Net Payout Yield Effect 复现 — [quantpedia.com/strategies/net-payout-yield-effect]。**中**。

**股息增长 vs 高息(行业研究,高/中)**
- Hartford Funds / Ned Davis, *The Power of Dividends* — [hartfordfunds.com/insights/market-perspectives/equity/the-power-of-dividends.html]。**高**(口径自报)。
- Osterweis, *Focus on Dividend Growth, Not Dividend Yield* — [osterweis.com/insights/dividend-growth-2023]。**中**。

**回购质量 / 伪回购 / 价值摧毁(中/高)**
- Harvard Law CorpGov, *Do Share Buybacks Really Destroy Long-Term Value?* (2020) — [corpgov.law.harvard.edu/2020/10/22/...]。**高**。
- Harvard Law CorpGov, *Dilution, Disclosure, Equity Compensation, and Buybacks* (2019) — [corpgov.law.harvard.edu/2019/10/30/...]。**中**(36.9% 数字标**未核实**)。
- Buyback Yield 公式/口径 — [wallstreetprep.com/knowledge/buyback-yield];[gurufocus.com/term/buyback-yield]。**中**。
- 伪回购识别 — [tikr.com/blog/how-to-tell-if-stock-buybacks-are-actually-good]。**中**。
- 1% 回购消费税 × SBC — [matthewssouth.com/stock-based-compensation]。**中**。

**数据 / EDGAR(高)**
- SEC EDGAR APIs(companyconcept/companyfacts/frames、User-Agent、10 req/s)— [sec.gov/search-filings/edgar-application-programming-interfaces]。**高**。
- XBRL US 现金流量表标注指南 — [xbrl.us/data-rule/guid-cashflows/]。**高**(标签语义)。

---

> **诚实声明:** 本报告所有"年化/跑赢"数字均来自公开发表或资管自报,多为样本内、未扣实盘成本、含构建自由度;**净·扣成本的可交易 alpha 必然显著更低**。落地前必须在本系统内用退市样本、PIT `filed` 对齐、对 Value 正交化、Deflated Sharpe(t>3)与扣成本分层回测**独立复现**。标"中/未核实"的来源不得作为决策依据,需一手核验。
