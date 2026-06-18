# 长周期动量与趋势跟踪 — 作为长期投资的收益引擎与回撤护栏

> 目的:为本系统的**长期投资**方向落地"动量(横截面 12-1)+ 趋势跟踪(时序动量 / 移动均线择时)"。
> 方法:fan-out 检索 → 每个分支抓一手或近一手来源 → 关键数字标 **URL + 可信度(高/中/低)** → 合成可落地做法。
> 日期:2026-06-18。立场延续房子风格:**诚实可证伪、净·扣成本是唯一货币、显式标注前视/幸存者偏差**;优先 2023-2026 与免费/PIT 数据。
> 适用范围:**月度(及以上)再平衡、长持有期**。短周期反转/微观结构不在本文范围(见 `research/quant-factor-deep-research.md` §2.1)。
>
> ⚠️ 数据可信度口径:本文多数论文 PDF 在本环境不可直接抓取(403/二进制),数字来自论文摘要页、Quantpedia、AQR/作者博客、第三方复现页等**近一手**来源,已逐条标注;凡本文未能在原始 PDF 核对的精确数字,标"**未核实(二手)**",落地前应回到原文表格核对。

---

## 1) TL;DR(执行摘要)

1. **横截面动量(12-1)与时序动量(趋势)是两类可分离的信号,长期投资应两者都要、且互补。** 横截面=同时点给资产排序做多空/多头超配;时序=用资产自身过去 ~12 月收益决定持有/离场。二者正相关但不等价,叠加价值后形成"价值+动量+趋势"三引擎。[高｜MOP 2012;AMP 2013]

2. **横截面动量的长期溢价真实且大,但伴随罕见、可部分预测的"崩盘"。** Jegadeesh-Titman(1993)原始 ~1%/月级别;但 WML 在 **2009 年 3 月起的反弹中单段巨亏(论文记为 panic-state 崩盘,2009 年 3-5 月量级 -40%~-70% 区间)**,且 1932 年同类巨亏。崩盘集中在"熊市后 + 高波动 + 市场反弹"时。[高｜Daniel-Moskowitz 2016 JFE;NBER w20439]

3. **崩盘是可治理的,不是否定动量。** Daniel-Moskowitz 的**动态动量**(按预测均值/方差对 WML 加减杠杆)把无条件 Sharpe **约翻倍**;实务里更简单的护栏=波动率目标化 + 熊市/高波动降腿 + 用 **52 周高点接近度**替代裸过去收益(George-Hwang,崩盘更轻、利润不反转)。[高｜DM 2016;中｜52wk]

4. **时序动量(趋势跟踪)本身就是回撤护栏,且有"危机 alpha"。** Moskowitz-Ooi-Pedersen(2012):58 个期货**全部**呈正时序动量、52 个 5% 显著,12 月回看/1 月持有最优,**分散组合 Sharpe ~1.3(1965-2009,毛额)**,且在**股票最差的月份表现最好**(凸性/危机 alpha)。[高｜MOP 2012 JFE;Quantpedia]

5. **移动均线择时(Faber GTAA)把股票最大回撤从 ~45-50% 压到个位数,代价是跑输牛市尾段 + 换手/whipsaw。** 规则极简:月末看是否在 **10 月(~200 日)SMA 之上**,在上则持有、在下则移仓现金/债。这是"长期股票仓位的回撤护栏"最便宜的落地。[高｜Faber 2007/2013]

6. **Antonacci 双动量(GEM)= 绝对动量(择时护栏)+ 相对动量(美 vs 非美选强)**:作者 1974-2013 回测 **CAGR ~17.4% vs S&P500 ~12.3%,最大回撤不到买入持有的一半**;独立复现(1970-2025,SPY/VXUS/IEF/BIL)**CAGR ~14.8% / MaxDD ~-20.5% vs S&P 11.2% / -50.1%**。年 ~1.5 次交易,成本极低。但**样本短、月度切换、对参数敏感**。[中｜Antonacci 博客;中｜Grzegorz Link 复现]

7. **扣成本后动量仍活,但容量与构建口径决定生死。** Frazzini-Israel-Moskowitz 用近万亿美元真实成交:size/value/momentum 扣实测成本后**仍稳健、可规模化**(成本仅为学术估计的 <1/10),短期反转最受成本限制;**降换手设计能显著提净收益与容量**。反方:Patton-Weller 等用真实基金发现"纸面 alpha 与净 alpha 差距巨大"。[高｜FIM 2018;中｜Patton-Weller]

8. **价值与动量负相关(~-0.5),50/50 组合 Sharpe 高于任一单腿。** 这是"价值+动量"标配的根因;再叠加趋势作护栏,得到长期、低相关、回撤可控的多引擎。**落地建议:月度再平衡、12-1 横截面动量(跳过最近 1 月)+ 时序趋势离场护栏 + 价值/质量叠加 + 波动率目标。** [高｜AMP 2013 JF]

---

## 2) 横截面动量 vs 时序动量 — 定义与公式

### 2.1 横截面动量(cross-sectional / relative momentum)
- **定义**:在再平衡日 d,对全宇宙按"过去 J 月、跳过最近 1 月的累计收益"排序,做多 top 分位、做空(或仅超配)bottom 分位。"相对"——只看谁比谁强。
- **公式(12-1,本系统已实现口径)**:
  ```
  mom_12_1(i) = P[i-21] / P[i-252] - 1        # 过去 252 交易日收益,跳过最近 21 日(避开 1 月反转)
  signal      = cross_sectional_zscore(mom_12_1)   # 同时点截面标准化,越大越超配
  ```
  与 `backtest/factors_xs.py` 的 `mom_12_1` 完全一致(已落地)。跳过最近 1 月是因为 **1 月短期反转**(Jegadeesh 1990)会侵蚀动量。[高｜JT 1993]
- **变体与改进口径(对长持有期都相关)**:
  - **52 周高点接近度**(George-Hwang 2004)`hi52 = P[i] / max(P[i-252:i])`,本系统已有(`factors_xs.py`),实证崩盘更轻、利润长期不反转——长持有期尤其偏好"不反转"的信号。[高]
  - **残差/特质动量**(Blitz-Huij-Martens):先用 FF 因子回归剥掉市场/规模/价值暴露,用**残差收益**排序 → Sharpe 更高、换手更可控、对崩盘更稳。长持有适合。[中｜未核实(二手)]
  - **路径质量 / "frog-in-the-pan"**(Da-Gurun-Warachka):同样的累计动量,**连续小涨**(信息离散)比**几次大跳**(信息集中)漂移更久 → 可作动量腿的质量过滤。[中]
  - **行业/截面中性化**:对行业去均值后再排名,避免动量退化成"押单一热门行业"(2009 崩盘部分即行业押注被反转)。[中]
- **形成/持有期权衡**:形成期越长越偏"趋势/价值化"、越短越偏反转;长持有投资优选 **12-1 形成 + 月度再平衡(隐含 1 月持有滚动)**,避免 3-6 月短形成期的高换手与反转污染。[高｜JT 1993]

### 2.2 时序动量(time-series / absolute momentum / trend)
- **定义**:用资产**自身**过去收益的**符号**决定持有方向/是否离场——与别的资产无关。"绝对"——只看自己涨没涨。
- **公式(MOP 2012 口径)**:
  ```
  sign_i   = sign( past_12m_excess_return_i )         # 正→做多,负→做空/离场
  weight_i = sign_i * (target_vol / sigma_i)          # 波动率目标化:按自身波动反比定仓
  ```
  波动率目标化(把每个腿缩放到同一事前波动)是 TSMOM 出"危机 alpha"和稳定 Sharpe 的关键工程细节。[高｜MOP 2012]
- **移动均线等价物(Faber)**:`hold if P[t] > SMA_10month(P)  else cash`。月末判定,10 月 SMA ≈ 200 日。是 TSMOM 的"长多 + 离场"简化版。[高｜Faber 2007]

### 2.3 二者关系与收益分解
- 数学上可分离、经验上正相关但**不冗余**:MOP 显示时序动量在控制横截面动量后仍有显著 alpha。CTA 趋势择时(时序)与多空选股(横截面)互补。[高｜MOP 2012]
- **收益来源分解(Lo-MacKinlay / JT 三项)**:横截面动量利润 = (1) 个股收益的**正自相关**(真趋势)+ (2) 资产间**负交叉自相关**(领先-滞后)+ (3) 期望收益的**横截面分散**。其中只有 (1) 是"动量"本义,(2)(3) 部分是补偿/结构性。30 年综述把这套分解再确认。→ 落地含义:**别把全部动量收益当 alpha**,有一块是横截面收益分散(更像风险补偿),扣成本后才见真。[高｜JT 2023 综述]
- **时序 ⊃ 横截面的一部分**:一个截面多空组合可分解为"时序自身趋势 + 相对其他资产的趋势";MOP 证明时序腿单独显著 → 趋势是更"原子"的信号。长期投资里**时序做护栏(择时)、横截面做选强(超配)**是自然分工。[高]
- 本系统 `factors.py`(时序择时)与 `factors_xs.py`(横截面排序)已经分家,正对应这条结论。

---

## 3) 长期净收益 / 回撤 / 崩盘证据(含可信度)

### 3.1 横截面动量长期溢价
| 项 | 数字 | 来源 | 可信度 |
|---|---|---|---|
| JT(1993)12 月形成/3 月持有 | ~1%/月级别正收益,所有 3/6/9/12 月组合显著 | sciencedirect 30-years-review | 高(综述)/原数字**未核实(二手)** |
| 30 年后再确认 | Jegadeesh-Titman 2023 综述:动量存在性进一步被强化;讨论了正自相关、负交叉相关、期望收益分散三类来源 | link.springer 10.1007/s11408-022-00417-8 | 高 |
| UMD/WML 因子可得性 | Ken French 库公开 UMD(月/日);AQR 提供因子 premia 数据 | mba.tuck.dartmouth.edu French Data | 高 |

### 3.2 动量崩盘(momentum crash)
- **核心事实**:动量平均收益高,但有**罕见、持续、可部分预测**的崩盘。崩盘发生在 **"panic 状态":市场大跌之后 + 市场波动高 + 与市场反弹同期**。机制=过去的输家组合在 panic 后带有"期权式"凸性,反弹时暴涨,空头腿被打爆。[高｜Daniel-Moskowitz 2016 JFE "Momentum Crashes"]
- **2009 崩盘**:WML 在 **2009 年 3 月起的反弹中单段巨亏**(NBER w20439 / ScienceDirect 摘要确认为 panic-state 崩盘;不同口径量级在 **-40%~-70%/数月**区间,精确月度值**未核实(二手)**——落地前回原文表 1/图)。同类巨亏见 **1932 年夏**。[高(存在性)/中(精确量级)]
- **治理**:Daniel-Moskowitz 的**动态动量**(按预测的 WML 均值与方差对组合加减杠杆,使无条件 Sharpe 最大化)**约翻倍 alpha 与 Sharpe**,且不被其他因子解释。[高｜NBER w20439]
- **更简版护栏**(实务可落地,不需预测模型):
  1. **波动率目标化**:WML 自身波动可预测且与均值预测相互独立 → 缩放到常数事前波动即削掉大半崩盘尾部。[高]
  2. **熊市/高波动降腿**:市场在长期均线之下 + 已实现波动高 → 调低动量腿暴露。
  3. **52 周高点接近度**替代裸过去收益:崩盘更浅、利润不反转。[中｜George-Hwang 2004]
- **崩盘可预测性的具体特征(可直接做闸门)**:
  - **熊市状态**:市场过去 ~2 年累计收益为负(`bear = cum_return_24m < 0`)→ 动量崩盘概率显著上升。
  - **高波动**:市场已实现波动处于高分位 → 输家组合凸性最大、空头腿最危险。
  - **反弹同期**:崩盘与市场急涨同月发生(空头被轧)。
  → 工程化:`mom_health = 1 - 1{bear} * 1{vol_high}`,熊市高波动时把动量腿(尤其空头/低分位)暴露压低甚至清零。这是 DM 动态动量的"穷人版"。[高｜DM 2016]
- **"做空腿"是崩盘主因**:崩盘几乎全来自**输家组合(空头)**在反弹中暴涨,而非赢家腿。→ 长期投资若只做**多头超配(不做空)**,本身就规避了大部分动量崩盘尾部——这对免费数据/无券源的散户系统是关键利好。[高(性质)｜DM 2016]

### 3.3 时序动量(趋势)长期净收益
| 项 | 数字 | 来源 | 可信度 |
|---|---|---|---|
| MOP 全样本 | 58 个期货**全部**正时序动量,**52 个 5% 显著**;12 月回看/1 月持有最优;趋势持续 ~1 年后部分反转 | MOP 2012 JFE;ssrn 2089463 | 高 |
| 分散组合表现 | 估计年化 ~20.7%(FF alpha 口径)、**Sharpe ~1.31**、波动 ~15.7%、MaxDD ~-33.9%(1965-2009,**毛额**) | Quantpedia "Time Series Momentum Effect" | 中(二手汇总) |
| 危机 alpha | 分散 TSMOM 在**极端市场表现最好**、对标准因子暴露很小 → 与股票低/负相关 | MOP 2012;alphaarchitect TSMOM | 高(性质)/中(幅度) |
| 百年证据 | AQR "A Century of Evidence on Trend-Following":~110 年趋势毛/净后正 Sharpe,危机期凸性(PDF 本环境未抓到,数字**未核实**) | AQR Century of Evidence | 中-低 |

---

## 4) 趋势作为"回撤护栏"的证据

### 4.1 Faber GTAA(移动均线择时)
- **规则**:月末,对每个资产类别判断是否在 **10 月(≈200 日)SMA 之上**;在上→持有,在下→移仓现金/短债。资产宇宙:美股、外股、债、商品、REITs(GTAA5)。[高｜Faber 2007/2013 "A Quantitative Approach to Tactical Asset Allocation"]
- **效果(论文叙述,精确表格 PDF 本环境未抓到)**:择时把波动与最大回撤压到**个位数**,作者/二手反复引用**最大回撤从 ~46% 降到 <10%**,实现"股票级收益、债券级波动与回撤"。[高(结论)/数字**未核实(二手)**｜mebfaber.com SSRN-id962461]
- **代价(诚实)**:(a)牛市尾段跑输买入持有;(b)**whipsaw**——震荡市频繁穿越均线、来回交易扣成本;(c)信号月度滞后,深 V 急跌中先吃一段亏再离场。这是"护栏"的保费,不是免费午餐。

### 4.2 移动均线择时的"参数稳健性"与 whipsaw 量化
- **稳健性**:Faber 反复强调择时结论对均线长度**不敏感**(150/200/250 日大同小异)、对再平衡日(月末 vs 月中)不敏感 → 不是挑参数挑出来的。这降低过拟合担忧。[高(叙述)/数字未核实(二手)]
- **whipsaw 量化(落地必看)**:震荡市里价格反复穿越均线 → 频繁"卖在底、买在顶"的小亏累积。缓解:(a)**双均线缓冲带**(跌破 200 日 ×0.98 才离场、升破 ×1.02 才回场);(b)**分档离场**(穿越按比例减仓而非全清);(c)月度判定而非日度(系统天然月频 → whipsaw 已较少)。**护栏的净价值 = 削掉的尾部 − whipsaw 保费 − 牛市尾段机会成本**,必须在 `costs.py` 扣成本后算净。[中]
- **离场去哪**:移仓**中短债(IEF/AGG)**而非现金,历史上股跌时债涨(负相关)→ 护栏期还能小赚;但 2022 股债双杀年这条失效 → 护栏不是万能,极端通胀冲击下股债同跌。[中]

### 4.3 时序动量的凸性(crisis alpha)
- TSMOM 收益形状像**做多跨式(long straddle)**:大涨大跌都赚,温和震荡亏(时间价值)。这正是它在 2008、长期股票熊市里抗跌的原因——**与股票的尾部负相关比平均相关更值钱**。[高｜MOP 2012]
- 现代反方:AQR "You Can't Always Trend When You Want"(2019)解释 2010 年代趋势收益偏弱**主因是市场波动幅度偏小**(不是分散度或择时能力退化)→ 趋势的护栏价值依赖"有大趋势可跟",温和年份会拖累。[高｜AQR JPM 2019]

### 4.4 双动量(GEM)= 护栏 + 选强 的合体
- **结构**:绝对动量(自身 12 月 > T-bill?否→去债)提供**回撤护栏**;相对动量(美股 vs 非美股谁强)提供**收益增强**。[高｜Antonacci 2014]
- **决策树(月末执行,可直接编码)**:
  ```
  if SP500_12m_return <= TBill_12m_return:        # 绝对动量:大盘没跑赢现金
      hold AGG / IEF                               #   → 去债(护栏触发)
  else:                                            # 大盘在涨
      if SP500_12m > exUS_12m: hold S&P500        #   相对动量:美 vs 非美选强
      else:                     hold exUS (ACWI ex-US)
  ```
  关键细节:**绝对动量用美股(而非当前持仓)做开关**是 Antonacci 的设计,避免在非美股上各自择时导致的额外 whipsaw。
- **数字**:
  - 作者 1974-2013:**CAGR ~17.4% vs S&P500 ~12.3%**,**最大回撤 < 买入持有的一半**;下跌年 GEM 均 +2.2% vs S&P -15.2%。[中｜einvestingforbeginners 引 Antonacci;原书表格**未核实**]
  - 独立复现(Grzegorz Link,1970-2025,SPY/VXUS/IEF/BIL):**CAGR ~14.8% / MaxDD ~-20.5%** vs S&P **11.2% / -50.1%**。[中｜grzegorz.link]
  - 年均 ~1.5 次交易 → 成本可忽略。[中]
- **反方**:样本短(单一长牛 + 美股领先期)、月末切换有**择时运气成分**、对回看窗口/资产代理敏感、2010 年代相对动量(美 vs 非美)长期偏向美股 = 事后看对但事前是单次大赌注。

---

## 5) 数据与可得性(免费 / PIT 优先)

| 需求 | 免费源 | 说明 | 可信度 |
|---|---|---|---|
| 横截面 12-1 / 52wk 高点 | **本系统已有**:`backtest/data.py`(Yahoo 日线)+ `factors_xs.py` | 纯价量,无未来函数;⚠️ Yahoo 非官方、仅研究用 | 高 |
| PIT 成分(防幸存者/前视) | `backtest/pit_membership.py` + `pit_sp500.json` | 系统已做 PIT 成员重建(README:2021 起回测缺失率 ~10%,虚增已量化) | 高 |
| UMD/WML 学术因子(对标基准) | Ken French Data Library(月/日 Mom);AQR Factor Premia | 用来校准"我们做的 UMD ≈ 学术 UMD";`getFamaFrenchFactors`(py)可拉 | 高 |
| 时序趋势(ETF 代理) | Yahoo 日线 SPY/VEU(or VXUS)/IEF/AGG/BIL/GLD | GEM/GTAA 全部可用免费 ETF 复现 | 高 |
| 期货级 TSMOM | 免费源弱(无连续期货合约/roll);可用 ETF/指数近似 | 真期货 TSMOM 需付费(roll-adjusted)数据 → 本系统先做 ETF 版 | 中 |
| 价值/质量叠加 | 需财报(SEC EDGAR 已接入,见 README/`scripts`) | `factors_xs.py` 注释已诚实标注当前数据集无财报 → 价值腿待接 EDGAR | 中 |

**幸存者/前视红线**:任何动量回测必须用 **PIT 成分**(系统已具备)+ **跳过最近 1 月** + **再平衡日只用 d 及之前数据**(`factor_values(adj, i)` 已是此口径)。退市股不可事后剔除,否则系统性高估动量。

**复现学术基准的最小数据链(免费可走通)**:
1. 拉 Ken French **UMD 月度** + 10 个动量分组 → 作为"地面真值"。
2. 用本系统 Yahoo 日线 + PIT 成分自建 12-1 多空 → 与 UMD 月度对相关(目标 >0.8)。
3. 偏差 = 构建口径差异(市值加权 vs 等权、跳月与否、行业中性)→ 逐项对齐,定位 bug。
4. ETF 趋势/GEM 用 SPY/VEU(or VXUS)/IEF/AGG/BIL/GLD,**全程免费、月频、无逐笔需求** → CI 里可定时跑(类比系统已有 `monthly-studies.yml`)。

**容量与扣成本来源**:`backtest/costs.py` 的 half-spread(默认 5bp)+ 平方根冲击(Y≈0.5)+ 容量地板(≤5% ADV)直接复用;月度动量换手低(GEM 年 ~1.5 次;个股横截面月频带状再平衡换手可控),成本敏感度远低于短周期反转。

---

## 6) 落地到本系统(信号公式 / 再平衡频率 / 脚本 / 验证)

### 6.1 三引擎信号(月度)
1. **横截面动量腿(已存在)**:`mom_12_1` + `hi52`(George-Hwang),截面 z-score 合成,top 分位超配。**崩盘护栏**:乘以一个 0~1 的"动量健康系数" = f(市场是否在 200 日均线上, 已实现波动分位),熊市高波动时压低动量腿。
2. **时序趋势护栏腿(新增,ETF 版)**:对组合或大盘代理(SPY)做 Faber 规则——`SPY < SMA_200` → 把整体股票暴露按比例降到现金/IEF。等价于在组合层加"绝对动量开关"。
3. **价值/质量叠加(待接 EDGAR)**:与动量负相关(~-0.5),50/50 提 Sharpe。先用 EDGAR 的 E/P、毛利率等做粗价值腿,与动量等权合成。

**合成公式(建议)**:
```
score = w_mom * z(mom_12_1, hi52)  +  w_val * z(value, quality)
exposure = score_topslice * trend_gate(SPY vs SMA200) * (target_vol / realized_vol)
# trend_gate ∈ {0..1};vol-target 控总波动;月度 rebalance
```

**两种落地配方(按数据/复杂度分档)**:
| 配方 | 数据需求 | 信号 | 适合 |
|---|---|---|---|
| **A. ETF 双动量(GEM/GTAA 版)** | 仅 SPY/VEU/IEF/BIL/GLD 免费日线(系统已有) | 绝对动量护栏 + 美 vs 非美相对动量,月末切换 | **先做**——最便宜、可信度最高、年 ~1.5 次交易 |
| **B. 个股横截面动量 + 组合趋势护栏** | PIT 成分(已有)+ 全宇宙日线(已有)+(可选)EDGAR 价值腿 | `mom_12_1`+`hi52` 截面排序做多头超配,乘 `mom_health` 与 `trend_gate` | 系统核心引擎,需 PBO/DSR 终检 |

- **只做多头**:免费数据无券源,**做多头超配版**(top 分位超配、不做空 bottom)即规避大部分崩盘尾部(§3.2)+ 无借券成本 → 与房子"容量受限冷门层"主张一致。
- **权重起点**:`w_mom : w_val ≈ 50:50`(AMP 负相关分散的经典配比),`target_vol` 取组合年化 ~10-12%,`trend_gate` 用 200 日 SMA 缓冲带(0.98/1.02)。所有这些都是**待标定参数,计入试验计数 N**。

### 6.2 再平衡频率与换手
- **月度再平衡**(长持有期标准):横截面动量在月频上 alpha/换手比最好;GEM/GTAA 本就是月末判定。
- **降换手**:沿用本系统已有的 **Garleanu-Pedersen aim 组合**思路(`backtest/statarb.py` 已实现 aim/控换手)迁到月频动量;**带状再平衡**(只在排名跨越缓冲区时换)削 whipsaw。
- **成本扣减**:复用 `backtest/costs.py`(half-spread + 平方根冲击 + 容量地板 ≤5% ADV)。**净·扣成本是唯一计价货币**——毛 Sharpe 不进结论。

### 6.3 建议脚本(新增,不在本次改动范围)
- `backtest/study_momentum_lt.py`:月度 12-1 + hi52 横截面回测,接 PIT 成分,输出净·扣成本曲线 + 分层单调性 + Rank-IC。
- `backtest/study_trend_gate.py`:Faber/GEM ETF 版(SPY/VEU/IEF/BIL),对比"裸买入持有 vs 趋势护栏"的 CAGR/MaxDD/Sharpe/whipsaw 次数。
- 复用现有 `study_pbo.py`(CSCV-PBO)与 Deflated Sharpe:动量+趋势的参数(回看月数、缓冲带宽、vol target)都要进**试验计数 N**,门槛 **t>3**。

### 6.4 预期收益打折(诚实定价)
- 学术 12-1 多空 ~1%/月**毛**;落地要连扣三道折:**(a) 发表后衰减 ~×0.4-0.6**(McLean-Pontiff)、**(b) 只做多头**(放弃空头腿收益,但也放弃其崩盘风险)、**(c) 净·扣成本 + 容量地板**。叠加后**长期投资的现实预期 = 个位数年化超额、且有多年痛苦期**,不是回测里的两位数。任何"动量年化 15%+"在我们口径下默认是样本内/前视,先证伪。[高｜McLean-Pontiff;FIM 2018]
- **趋势护栏的价值是"非对称"的**:多数年份它小幅拖累(whipsaw + 牛市尾段),少数危机年份它救命 → 用 **CAGR 看它像负贡献,用 MaxDD/最差年/Sortino 看它才值钱**。评估护栏必须用回撤类指标,不能只看均值。[高]

### 6.5 验证清单(防过拟合,house 纪律)
- [ ] PIT 成分 + 跳过最近 1 月 + d 及之前数据(无前视/幸存者)。
- [ ] **净·扣成本**(spread + impact + 容量地板)后才报收益;报告换手率。
- [ ] **Deflated Sharpe**(按 N 通缩)+ **CSCV-PBO**(`study_pbo.py`);所有回看/缓冲/vol-target 组合计入 N。
- [ ] 真 holdout 终检(系统 C1 已有框架);崩盘期(2009-03、2020-03)单独看护栏是否起作用。
- [ ] 与 Ken French UMD 对标:我们的 UMD 与学术 UMD 月度相关应 >0.8,否则构建有 bug。

---

## 7) 风险与反方

1. **动量崩盘是真实尾部风险**:裸 12-1 在熊市反弹中可单段 -40%~-70%。不带护栏(vol-target / 熊市降腿 / 52wk)的动量不可长期裸持。[高｜DM 2016]
2. **alpha 衰减 + 发表后拥挤**:公开因子样本外/发表后大幅缩水(McLean-Pontiff:发表后 ~-58%,见 `quant-factor-deep-research.md` §1.5)→ 动量预期应打 4-6 折。
3. **趋势依赖"有大趋势"**:温和波动的十年(2010s)趋势收益偏薄;护栏价值会闲置甚至拖累。[高｜AQR 2019]
4. **GEM/GTAA 样本短 + 单一制度**:回测窗多落在美股长牛 + 美股领先期,月末择时含运气;参数敏感、易过拟合。复现数字(CAGR 14.8-17.4%)**不可外推**。[中]
5. **whipsaw 与成本**:移动均线择时在震荡市频繁假信号;免费日线 + 月度判定能减,但扣成本后护栏的净收益贡献会缩水。
6. **真实净 alpha < 纸面**:Patton-Weller、López de Prado 体系都警告纸面与实盘差距;FIM(2018)乐观结论来自单一大型机构的优化执行,小资金/差执行未必复制。[高/中]
7. **数据源风险**:Yahoo 非官方接口、商用需换授权;期货级 TSMOM 免费数据不足,ETF 代理无法完全复刻 MOP 的 58 资产分散与凸性。
8. **护栏在"股债双杀"年失效**:趋势离场常移仓债;2022 通胀冲击下股债同跌 → 护栏的"离场资产"本身也亏。极端宏观风险下需现金/商品/趋势 CTA 才真分散。[中]
9. **月末择时的"日历运气"**:GEM/GTAA 全在月末判定,换到周中或不同月末样本会改变结果(择时点敏感)→ 应做**多个再平衡偏移**的稳健性检验,别只信一个日历。[中]
10. **本文数字的二手性**:多篇关键论文 PDF 在本环境不可直接抓取,精确数字(2009 崩盘月度量级、Faber 46%→<10%、GEM 原书表格)均标"**未核实(二手)**"——落地决策前必须回原文表格核对,不可直接引用本文数字下注。

**反方的反方(为什么仍值得做)**:即便打了上述所有折扣,(a) 价值×动量负相关分散是**结构性**的(不依赖任一腿持续赢),(b) 趋势护栏的**尾部削减**在 2008/2020 反复兑现,(c) 月频换手让扣成本后仍有正净收益空间(FIM)。三者叠加的"长期、低相关、回撤可控"组合,比裸买入持有在**风险调整**与**最大回撤**上有 30 年级别证据支撑——前提是带护栏 + 防过拟合纪律。

---

## 8) 参考来源(URL + 可信度)

**横截面动量 / 崩盘**
- Jegadeesh-Titman 30 年综述(2023):https://link.springer.com/article/10.1007/s11408-022-00417-8 — **高**(同 ScienceDirect https://www.sciencedirect.com/science/article/abs/pii/S0927538X23002731)
- Daniel-Moskowitz "Momentum Crashes"(2016 JFE / NBER w20439):https://www.nber.org/papers/w20439 ;PDF https://www.nber.org/system/files/working_papers/w20439/w20439.pdf ;mirror http://www.snifferquant.com/gyantal/Incode/papers/Momentum%20Crashes%20by%20Moskowitz,%202013.pdf — **高**(本环境 PDF 二进制未直接抓取,精确月度量级**未核实(二手)**)
- George-Hwang 52 周高点(2004):见 `quant-factor-deep-research.md` §2.2(bauer.uh.edu)— **中-高**

**时序动量 / 趋势**
- Moskowitz-Ooi-Pedersen "Time Series Momentum"(2012 JFE):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463 ;AQR https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum — **高**
- Quantpedia TSMOM 汇总(Sharpe~1.31 / MaxDD~-33.9% / 1965-2009):https://quantpedia.com/strategies/time-series-momentum-effect — **中**(二手)
- AQR "A Century of Evidence on Trend-Following":http://www.ecapital.ch/downloads/AQR_A%20Century_of_Evidence_on_Trend-Following.pdf — **中-低**(PDF 未抓取,数字**未核实**)
- AQR "You Can't Always Trend When You Want"(2019 JPM):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3487134 — **高**

**择时护栏 / 双动量**
- Faber "A Quantitative Approach to Tactical Asset Allocation"(2007/2013 update):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461 ;PDF https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf — **高**(结论)/ MaxDD 46%→<10% 等精确数字**未核实(二手)**
- Antonacci GEM 扩展回测(博客):https://www.optimalmomentum.com/extended-backtest-of-global-equities-momentum/(本环境 403);近一手汇总 https://einvestingforbeginners.com/global-equities-momentum-ansh/ — **中**
- GEM 独立复现(Grzegorz Link,1970-2025):https://grzegorz.link/momentum-enhanced — **中**
- InvestResolve "Global Equity Momentum: A Craftsman's Perspective":https://investresolve.com/inc/uploads/pdf/global-equity-momentum-a-craftsmans-perspective.pdf — **中**(稳健性/参数敏感性讨论,未抓取)

**价值×动量分散 / 成本**
- Asness-Moskowitz-Pedersen "Value and Momentum Everywhere"(2013 JF):https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere ;NYU https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf — **高**(负相关~-0.5、50/50 提 Sharpe)
- Frazzini-Israel-Moskowitz "Trading Costs of Asset Pricing Anomalies"(2018):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2294498 ;PDF https://pages.stern.nyu.edu/~afrazzin/pdf/Trading%20Cost%20of%20Asset%20Pricing%20Anomalies%20-%20Frazzini,%20Israel%20and%20Moskowitz.pdf — **高**
- Patton-Weller "What You See Is Not What You Get"(纸面 vs 净 alpha):https://public.econ.duke.edu/~ap172/Patton_Weller_MF_31oct17.pdf — **中**

**数据**
- Ken French Data Library(UMD 月/日,免费):https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html ;Mom 细节 https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor.html — **高**

---

> 一句话结论:**长期投资里,横截面动量提供收益、时序趋势提供回撤护栏,价值提供负相关分散——三者月度叠加 + 波动率目标 + 净·扣成本 + PIT 防偏,是有 30 年证据支撑的可落地配方;但动量崩盘、趋势靠"有大趋势"、GEM 样本短这三条反方决定了护栏与防过拟合纪律不可省。** 本系统已具备 PIT 成分、成本模型、aim 控换手、CSCV-PBO/Deflated Sharpe 与横截面动量因子,落地主要缺口是:ETF 版趋势护栏脚本、价值腿接 EDGAR、以及把所有参数计入 N 做一次诚实的净·扣成本终检。
