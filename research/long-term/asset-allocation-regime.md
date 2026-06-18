# 资产配置与市场状态(Regime)框架 — 长期投资深度研究

> 目的:为成熟量化/投研系统的**长期配置层**铺方法论 —— 把"市场状态(regime)"用于调整长期股票仓位/因子暴露,判断**哪些做法在样本外真有效、哪些是过拟合**。
> 方法:fan-out 检索(风险平价/All Weather、Permanent Portfolio、Faber GTAA/Trinity、波动目标、时序趋势、regime 检测)→ 关键数字标**一手/二手来源 URL + 可信度(高/中/低)**→ 落地到本仓 `feed/market/state.json`。
> 日期:2026-06-18。立场:**净·扣成本是唯一货币;诚实可证伪;标前视/幸存者偏差。多数稳健做法是简单规则(趋势开关 + 波动目标);复杂 regime 模型样本外脆弱。**
> 重要免责:本文为方法论调研,**非投资建议**。所有"历史回测"数字均隐含**幸存者偏差 + 当代 ETF 回填(backfill)前视**风险,见 §3 与 §7。

---

## 1) TL;DR(执行摘要)

1. **没有一个配置框架"防一切"。** 风险平价 / All Weather / Permanent Portfolio 的共同卖点是"对冲掉 60/40 的股债同跌",但 **2022 同时被证伪**:通胀冲击下股债相关性从长期 ~ −0.2 翻正到 +0.5~+0.65,所有靠"股债负相关"分散的组合一起回撤。这不是 bug,是模型对**通胀 regime 的结构性暴露**。[高]

2. **2022 的真账本(净·近似)**:All Weather ≈ **−22%**(其历史最差)[中];Permanent Portfolio 最大回撤 ≈ **−19%**(2022-10,股/债/金三杀)[中];60/40 ≈ −16%。**唯一在 2022 赚钱的"配置工具"是时序趋势(CTA)**:SG Trend Index **+27.3%**、SG CTA Index **+20.1%**,均为 2000 年以来最佳。[高]

3. **趋势/动量叠加配置是降回撤里证据最强的一类,但有诚实折扣。** Faber GTAA(资产价 vs 10 月均线开关)样本外(2006–2012)把**最大回撤砍 ~80%、波动降到 ~7.3%**[中,作者自报];但**真实 ETF(GTAA)已清盘**,且简单 200 日均线在**横盘市被 whipsaw 反复打脸**(历史上仅 ~28% 的交易盈利,靠少数大趋势赚钱)。[中]

4. **波动目标(vol targeting)是"几乎免费的午餐"中证据较硬的一个**:Moreira-Muir(2017)对市场组合产生 ~4.9% alpha、Sharpe 提升 ~25%,并降低平衡/风险平价组合的最大回撤。**但有重大方法论争议**:其缩放因子用了**事后(ex-post)信息 → 前视偏差**;可实现版本(只用滞后已实现波动)效果打折但仍正。[高]

5. **复杂 regime 检测(HMM/Markov-switching)样本外脆弱。** 失败模式公认:状态数过多→追噪声、结构断裂(2022 这种新 regime 未见过)→失效、回测前视污染、高斯假设在崩盘尾部失真。**学界与实务共识:简单规则(趋势开关 + 波动阈值)的稳健性 ≥ 复杂隐状态模型。** [高]

6. **对本系统的落地结论(诚实)**:本仓 `feed/market/state.json` 已有一个**正确方向、克制**的 regime(SPY>200dma + 20 日年化波动阈值 + 广度 + 拥挤代理)。建议**不上 HMM**;把 regime 用作**仓位/杠杆与因子腿权重的"软开关 + 波动目标"**,而非择时进出;所有规则**月频、滞后、扣成本验证**,并做 PBO/Deflated Sharpe 检验试验次数。把"regime 调仓"当**风险管理**(降回撤、控尾部)而非**alpha 来源**。

---

## 2) 各配置框架原理 + 权重规则

### 2.1 风险平价(Risk Parity)/ Bridgewater All Weather

- **核心思想**:不按"资金"分散,按"风险贡献"分散 —— 让每类资产对组合波动的边际贡献相等。因为债券波动远低于股票,需**加杠杆**把债券风险拉到与股票相当。[高｜原理普遍共识]
- **All Weather 的"四季"框架**:把宏观拆成两轴 ——(增长↑/↓)×(通胀↑/↓),四象限各配能在该环境跑赢的资产(增长↑:股/商品;增长↓:名义债;通胀↑:通胀挂钩债/商品/金;通胀↓:股/名义债),目标"任何宏观季节都不大输"。[高｜Bridgewater 公开框架]
- **对利率/通胀的暴露(关键!)**:风险平价**结构性超配债券**(因为要把低波动债券加杠杆补到等风险),因此**对实际利率上行 + 通胀冲击高度敏感**。2x 名义杠杆意味着对冲失效时 2x 损失。[高]
- **典型 All Weather 静态权重(Dalio 在 Tony Robbins《Money》公开的简化版,非基金实盘)**:30% 美股 / 40% 长期美债 / 15% 中期美债 / 7.5% 黄金 / 7.5% 大宗商品。**注意:这是简化教学版,不是 Bridgewater 旗舰基金的实际持仓(后者用衍生品 + 杠杆 + 全球敞口)。** [中｜二手]

### 2.2 Permanent Portfolio(Harry Browne)

- **核心思想**:不预测,用"四等分"覆盖四种经济状态 —— 繁荣(股)、通胀(金)、通缩(长债)、衰退/紧缩(现金)。每年(或偏离阈值)再平衡回 25/25/25/25。[高｜Browne 原始设计]
- **权重规则**:25% 美股(VTI)/ 25% 长期美债(TLT)/ 25% 现金或短债(SHY)/ 25% 黄金(GLD)。无杠杆、无择时、机械再平衡。[高]
- **特征**:历史 CAGR ~8.5%(1968–2026.3)、年化波动仅 ~7.3%,波动不到标普一半,GFC 回撤约为标普 1/3。[中｜PortfoliosLab/OptimizedPortfolio 等二手回测,含 ETF 回填前视]

### 2.3 Faber GTAA(Global Tactical Asset Allocation)/ 时序趋势叠加

- **核心信号**:每个资产类在**月末**看价格是否 > **10 月(≈200 日)简单均线**。在线上则持有,跌破则换成现金/T-bills。**纯时序趋势开关,逐资产独立**。[高｜Faber 2007 SSRN id=962461]
- **GTAA(5)经典 5 资产**:美股 / 外股 / 美国 10 年债 / 大宗商品(GSCI)/ 房地产(REITs),等权 20% × 趋势开关。GTAA(13)扩到 13 个更细资产类。[高]
- **作用**:不提高收益,而是**靠趋势开关把单个资产类的深度回撤截断** → "股票般收益 + 债券般波动/回撤"。[中｜作者自报]

### 2.4 Meb Faber Trinity(三位一体)

- **三要素**:① 全球分散(全球市场组合 GMP 简化为 ~10 资产类);② 价值 + 动量**因子倾斜**(美股加价值/动量、海外加价值);③ **趋势跟随**叠加。[高｜Faber 2016 + AAII]
- **权重规则**:整体**对半分**——50% 静态 buy & hold(全球分散 + 因子倾斜),50% **动态趋势/动量**腿(Global Asset Allocation Plus 资产按动量排序取上半,且仅当价 > 10 月均线才持有,否则转现金/T-bills)。[高]
- **定位**:把 §2.1–2.3 的优点拼起来 —— 分散 + 因子溢价 + 趋势降回撤,是"长期配置 + 择时叠加"的范式样板。

### 2.5 时序动量 / 双动量(配套基准)

- **时序趋势(time-series momentum)**:Moskowitz-Ooi-Pedersen(2012)在 58 个期货上全部呈正可预测性,是 CTA"危机 alpha"的学术地基(详见本仓 `research/quant-factor-deep-research.md §1.1`)。[高]
- **双动量 GEM(Antonacci)**:相对动量(美股 vs 外股)+ 绝对动量(vs T-bill 的趋势开关),择优持有。[高｜原始] **诚实折扣**:公开化(2014)后**样本外略输 SPY**、强牛市/急反弹被 whipsaw,被 ThinkNewfound 列为"脆弱性案例研究"(信号对回看窗口、再平衡时点敏感)。[中]

---

## 3) 长期净收益 / 回撤证据(含来源可信度与偏差标注)

> ⚠️ **全表共同偏差**:① 多数二手回测用**当代 ETF 回填**早期年份(基金不存在,数据是指数代理)→ 隐含**前视/幸存者偏差**;② 黄金 1971 后才自由浮动、长债 40 年大牛市(1981–2021)给债重组合"虚高顺风";③ "净"多数**未扣**再平衡成本/税。当作量级参考,不是可复制净值。

| 框架 | 长期 CAGR | 年化波动 | 最大回撤 | **2022(关键压力测试)** | 来源 / 可信度 |
|---|---|---|---|---|---|
| 60/40 | ~8% | ~10% | GFC ~−30% | **≈ −16%** | 通识 / 中 |
| All Weather(简化版) | ~7–8% | ~7–8% | 历史浅 | **≈ −22%(历史最差)** | 二手 / 中 |
| Permanent Portfolio | **~8.5%**(1968–2026.3) | **~7.3%** | **−18.99%(2022-10)** | 股债金三杀,历史罕见 | PortfoliosLab / 中 |
| Faber GTAA | ≈股票级 | **~7.3%**(OOS 06–12) | **OOS 砍 ~80% → ~−9.4%** | 趋势开关降回撤(月频滞后) | Faber SSRN / 中(作者自报) |
| 时序趋势 / CTA | 周期性 | ~10–15% | 长平台期 | **SG Trend +27.3% / SG CTA +20.1%(2000 来最佳)** | SocGen / **高** |
| 波动目标(市场) | — | 目标恒定 | 降回撤 | 减仓于高波动期 | Moreira-Muir / 高(有前视争议) |

**要点解读:**

- **2022 是全场唯一同步压力测试**:把"靠股债负相关分散"的三个框架(60/40、All Weather、Permanent)一起打回原形;**唯一对冲住的是时序趋势**(做空债券 + 做多美元/能源的趋势)。这定义了"regime 工具"的真正价值边界 —— **趋势是状态切换里最稳的那个,因为它不假设相关性结构。** [高]
- **Permanent Portfolio 2022 −19%**:平时"金对冲通胀"的逻辑在 2022 也短暂失效(金随实际利率上行回落),说明**任何静态四象限对"快速加息 + 通胀"这个组合 regime 都无解**。[中]
- **Faber OOS 砍回撤 80%** 是该领域引用最多的正面证据,但**真实 GTAA ETF 已清盘**,提示**纸面回测 ≠ 可投净值**(费用、税、跟踪误差、行为)。[中]
- **波动目标证据较硬**:Moreira-Muir 市场组合 alpha ~4.9% / Sharpe +25%,且**降低平衡与风险平价组合的最大回撤**;**但**有论文证实其缩放因子含**事后信息(look-ahead)**,可实现版(仅滞后波动)效果缩水但仍正。[高]

---

## 4) Regime 检测方法与脆弱性

### 4.1 方法谱系(从简单到复杂)

| 方法 | 输入 | 输出 | 透明度 | 样本外稳健性 |
|---|---|---|---|---|
| **200 日均线开关** | 价格 vs SMA200 | 牛/熊二态 | 极高 | 中(横盘 whipsaw) |
| **波动阈值** | 已实现波动 vs 分位 | 低/高波动 | 极高 | 中-高 |
| **趋势 + 波动联合(本仓)** | 二者 + 广度 + 相关 | risk_on/neutral/off | 高 | 中-高 |
| **宏观规则** | CPI/利差/失业趋势 | 通胀/增长象限 | 中 | 中(滞后、修正) |
| **HMM / Markov-switching** | 收益序列 | 隐状态 + 概率 | 低 | **低(脆)** |
| **聚类 / Jump model / ML** | 多特征 | 状态标签 | 低 | **低-中** |

### 4.2 简单规则的真实代价(诚实)

- **200 日均线 whipsaw**:横盘市每月买进、次月卖出,反复触发交易成本 + 税;历史统计**仅 ~28% 的择时交易盈利**,整体靠少数大趋势(熊市规避)赚钱。**无熊市的年份,大概率跑输 buy & hold。** [中]
- **缓解**:① 加缓冲带(价需突破均线 ±X% 才翻转)/ ② 用月末而非每日(Faber 原法)/ ③ 3–5 日确认。文献称这些**显著降 whipsaw 且不损原统计**。[中] **代价**:都是新参数 → 过拟合风险,须按试验次数惩罚。

### 4.3 复杂 regime 模型为什么样本外脆弱(核心警告)

- **Markov-switching 起点**:Hamilton(1989)给了 regime-dependent 动态的范式;HMM 提供隐状态 + 滤波/似然推断。理论优雅。[高]
- **公认失败模式**(直接证伪"上 HMM 更好"):
  1. **结构断裂**:模型只见过历史 regime,**2022 这种"加息 + 通胀 + 股债同跌"的新组合未在训练集 → 样本外失效**。[高]
  2. **状态数过拟合**:状态太多 → 追噪声;太少 → 混淆不同 regime。**没有客观的"对"状态数。** [高]
  3. **前视污染**:全样本 EM 拟合后再"回看"标注 regime → 回测虚高;实盘只能用滤波(filtered)而非平滑(smoothed)状态,效果大降。[高]
  4. **分布误设**:高斯 HMM 假设每态正态,**崩盘尾部恰恰非正态** → 在最该用的时候最不准。[高]
  5. **滞后**:隐状态切换确认时,行情大半已走完(与简单趋势开关同病,但更不透明)。
- **结论(可证伪)**:**复杂 regime 模型的样本外 IR 提升,绝大多数在严格 OOS + 前视隔离 + Deflated Sharpe 后消失。** 这与本仓 `quant-factor-deep-research.md` 的防过拟合纪律一致(Purged K-Fold + Embargo + CPCV + t>3)。**不上 HMM 是基于证据的选择,不是偷懒。**

---

## 5) 数据与可得性(免费 / PIT 优先)

| 需求 | 免费源 | PIT 风险 | 备注 |
|---|---|---|---|
| 美股指数/ETF 日线(SPY/QQQ/TLT/GLD/GSG/VNQ) | Stooq、Yahoo(本仓已用)、yfinance | 价格本身低风险;**成分/分红回填**有 | 配置层只需类资产代理,数据负担轻 |
| 类资产代理(国际股/债/商品/REIT/金) | ETF:VEA/IEF/TLT/DBC/VNQ/GLD | ETF 上市前需指数回填 → **早期年份前视** | 标注"回填段不可投" |
| 已实现波动 | 从日线自算(本仓已算 20 日年化) | 无(滞后即可) | 波动目标核心输入 |
| 广度 / 截面相关(拥挤代理) | 从 universe 日线自算(本仓已算) | 无 | risk_off 早警 |
| 宏观 regime(CPI/利差/失业) | FRED(免费)、本仓未接 | **数据修正(vintage)→ 须用 ALFRED real-time vintage 防前视** | 宏观滞后且常被修正,谨慎当 regime |
| 股债相关性 regime | SPY vs IEF/TLT 滚动相关自算 | 无 | 2022 类风险的直接监测器 |

- **关键 PIT 提醒**:**宏观数据(CPI、GDP、失业)有发布滞后 + 后续大幅修正**;用"当下看到的最终值"做回测 = 前视。若要上宏观 regime,必须用 **FRED/ALFRED 的 real-time vintage(ALFRED)**。本仓现有 regime **只用价格/波动/相关 → 无修正前视**,这是优点,建议保留。[高]
- **免费可得性结论**:**纯价格/波动/相关的 regime 完全免费且 PIT 干净;宏观象限 regime 数据更难做对,收益不确定 → 暂不优先。**

---

## 6) 落地到本系统(配置 / 择时规则 / 脚本 / 验证)

> 本仓现状:`scripts/run_routine.py::market_state()` 已产出 `feed/market/state.json`:
> `regime`(risk_on/neutral/risk_off)、`spy_above_200dma`、`spy_vol_20d_annual`、`breadth_pct_above_50dma`、`crowding_proxy`(平均两两相关)、`crowding_alert`、`residual_dispersion`。
> 现有判据:`risk_on` = SPY>200dma **且** 20 日年化波动 <0.18;`risk_off` = 跌破 200dma **或** 波动 >0.28;否则 neutral。
> **评价:方向正确、克制、PIT 干净、无 LLM、无未来函数 —— 是"简单规则"范式的好起点。下面是增量,不是推倒。**

### 6.1 配置层规则(建议,均月频 + 滞后 + 扣成本)

1. **把 regime 当"软开关 + 波动目标",不当"全进全出"。**
   - 长期股票/因子腿目标权重 `w_target`,实际权重 `w = w_target × leverage(regime) × vol_scale`。
   - `leverage(regime)`:risk_on=1.0、neutral=0.7、risk_off=0.4(连续优于二元;避免 0/1 whipsaw)。
   - `vol_scale = clip(target_vol / realized_vol_20d, 0.3, 1.0)`,`target_vol≈0.15`。**只缩不放(上限 1.0)→ 不加杠杆,纯降尾部**;用**滞后**已实现波动(避免 Moreira-Muir 前视争议)。

2. **趋势开关用缓冲带 + 月末**(降 whipsaw):仅当 SPY 跌破 200dma **超过 −2%** 才置 risk_off,回升 **+2%** 才解除;判定用**月末**值。所有缓冲参数登记为"试验",纳入 PBO 惩罚。

3. **拥挤/相关 regime 作独立早警(2022 类风险)**:新增 `stock_bond_corr_60d`(SPY vs IEF 60 日滚动相关)。**当它翻正(>0)且 risk_off → 触发"分散失效"告警**,提示削减债性对冲依赖、加趋势/现金腿。这直接监测 2022 的失效机制。

4. **因子腿随 regime 调权(克制)**:risk_off 时**降动量/小盘、升质量/低波**(动量在 regime 切换的崩溃即"momentum crash");但**仅做温和倾斜(±20%)**,不做开关,因为因子-regime 关系样本外也脆。

### 6.2 脚本落地(增量,**本次不写代码,仅给规格**)

- 扩展 `scripts/run_routine.py::market_state()`:增 `stock_bond_corr_60d`、`vol_scale`(=clip 计算值)、`suggested_leverage`(由 regime 映射)。全部从已加载的 SPY/IEF/universe 日线自算,**无新数据依赖、无新 key**。
- 新建 `backtest/study_allocation_regime.py`(对标已有 `experiment_regime.py` / `study_*.py` 风格):
  - 资产宇宙:SPY/IEF(或 TLT)/GLD/DBC/VNQ 类代理。
  - 对比四套:① 静态 60/40;② Permanent 25×4;③ GTAA 趋势开关;④ regime 软开关 + 波动目标(本仓法)。
  - 输出**净·扣成本**(含再平衡换手成本)CAGR / 波动 / MaxDD / Sharpe / 2022 分年,**月频、滞后一期、非重叠**。
- 把结果写入 `feed/reports/`(沿用 `report.schema.json`),`/intel` 看板可消费。

### 6.3 验证纪律(与本仓既有标准对齐)

- **真 holdout**:配置规则参数(波动目标、缓冲带 %、杠杆映射)在**早段拟合、晚段(含 2022)holdout 终检**,2022 必须在 OOS。
- **PBO / Deflated Sharpe**:登记所有试过的阈值/窗口数 N,按 N 通缩 Sharpe(复用 `backtest/study_pbo.py` 思路);**regime 调仓若 Deflated Sharpe 不显著正,则只当风险管理(降回撤)用,不宣称 alpha。**
- **成本现实主义**:月频再平衡换手 × 成本必须扣;趋势开关额外算 whipsaw 次数 × 成本。
- **诚实输出口径**:报告里把"降回撤"和"提收益"**分开记账**;明确标注哪些数字含 ETF 回填/幸存者偏差。

---

## 7) 风险与反方(adversarial)

1. **"四象限/全天候防一切"是营销叙事。** 2022 证明:**同时通胀↑ + 增长↓ + 加息**这个 regime 让多数静态分散框架一起失效。任何宣称"任何环境都稳"的配置,**问它 2022 怎么过的**。[高]
2. **回测净值普遍虚高**:ETF 回填 + 40 年债牛顺风 + 不扣成本/税。**未来债券不会再有 1981–2021 的单边顺风** → 历史 Permanent/All Weather 的"低波动高收益"含一次性红利,**未核实**其前瞻可复制性。
3. **趋势/择时的反方**:① 横盘市 whipsaw(~28% 交易盈利);② 公开化后衰减(GEM 2014 后略输 SPY);③ 真实产品清盘(GTAA ETF);④ 行为成本(连续小亏后难坚持)。**趋势的价值高度集中在少数危机年(2008、2022),平时是拖累。**
4. **波动目标前视陷阱**:Moreira-Muir 经典结果含事后缩放。**落地必须只用滞后波动**,否则回测里的 alpha 是看穿未来。[高]
5. **regime 调仓 = 多一层过拟合面**:每加一个状态/阈值/缓冲都是新自由度。**复杂 regime 模型(HMM/ML)样本外脆**已是共识。**反方的反方**:简单趋势+波动开关的稳健性也只是"中",别把它当圣杯;它主要买的是**尾部保险**,长期可能略损 CAGR。
6. **宏观 regime 的 PIT 陷阱**:CPI/GDP 被大幅修正;不用 real-time vintage 就是前视。**这是"宏观 regime 看起来有效"的最大幻觉来源。** [高]
7. **相关性不是常数**:所有风险平价的"等风险贡献"权重依赖协方差矩阵估计;**2022 证明相关性会 regime 切换**,事前协方差严重低估同跌风险。

---

## 8) 参考来源(URL + 可信度)

**风险平价 / All Weather / 2022 失效**
- [高] CAIA — *Is 2022 All Bad Weather For Risk Parity?* https://caia.org/blog/2022/12/05/2022-all-bad-weather-risk-parity
- [中] Markov Processes Intl — *Risk Parity Not Performing? Blame The Weather.* https://www.markovprocesses.com/blog/risk-parity-not-performing-blame-the-weather/
- [中] EBC — *Ray Dalio Strategy Explained: All Weather, Risk Parity* https://www.ebc.com/forex/ray-dalio-strategy-explained-all-weather-risk-parity
- [中] Sophie-AI — *The All Weather Strategy in a New Economic Climate* https://www.sophie-ai-finance.com/articles/all-weather-strategy-new-economic-climate
- [中] 8figures — *All Weather Portfolio: 22% Drawdown vs S&P 500's 55%* https://8figures.com/blog/portfolio-allocations/all-weather-portfolios-building-resilient-investment-strategies-for-every-market-climate

**股债相关性 regime / 通胀**
- [高] AQR — *A Changing Stock-Bond Correlation* https://www.aqr.com/Insights/Research/Journal-Article/A-Changing-Stock-Bond-Correlation
- [高] Omnigence — *Stock Bond Correlations — Inflation Regime* https://omnigenceam.com/insights/stock-bond-correlations-inflation-regime
- [高] Financial Analysts Journal — *Empirical Evidence on the Stock–Bond Correlation* https://www.tandfonline.com/doi/full/10.1080/0015198X.2024.2317333
- [中] Vanguard — *Understanding the dynamics of stock bond correlations* https://www.nl.vanguard/professional/vanguard-365/understanding-stock-bond-correlations

**Permanent Portfolio(Harry Browne)**
- [中] PortfoliosLab — Harry Browne Permanent Portfolio https://portfolioslab.com/portfolio/harry-browne-permanent
- [中] OptimizedPortfolio — *Permanent Portfolio Review (2026)* https://www.optimizedportfolio.com/permanent-portfolio/
- [中] QuantifiedStrategies — Harry Browne's Permanent Portfolio https://www.quantifiedstrategies.com/harry-brownes-permanent-portfolio/
- [中] PortfolioCharts — Permanent Portfolio https://portfoliocharts.com/portfolios/permanent-portfolio/

**Faber GTAA / Trinity / 时序趋势**
- [高] Faber (2007 SSRN id=962461) — *A Quantitative Approach to Tactical Asset Allocation* https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf
- [高] Faber — Timing Model 数据页 https://mebfaber.com/timing-model/
- [高] Faber — *The Trinity Portfolio* https://mebfaber.com/2015/11/04/the-trinity-portfolio/
- [中] AAII — *The Trinity Portfolio: Combining Diversification, Tilts and Trend-Following* https://www.aaii.com/journal/article/the-trinity-portfolio-combining-diversification-tilts-and-trend-following
- [中] PortfolioDB — GTAA(13) by Meb Faber https://portfoliodb.co/portfolios/global-tactical-asset-allocation-13-gtaa-13-meb-faber

**时序趋势 / CTA(2022 危机 alpha)**
- [高] AlphaWeek — *2022 CTA Index Performance Review* https://www.alpha-week.com/2022-cta-index-performance-review
- [高] SocGen Prime Services — SG Trend / CTA Indices https://wholesale.banking.societegenerale.com/en/prime-services-indices/
- [中] Aspect Capital — *Living with Trend Following (SG CTA Index)* https://www.aspectcapital.com/insight/living-with-trend-following-sg-cta-index/

**波动目标 / 波动管理**
- [高] Moreira & Muir (2017) — *Volatility-Managed Portfolios* (NBER w22208) https://www.nber.org/system/files/working_papers/w22208/w22208.pdf
- [高] Moreira & Muir — Stern PDF https://www.stern.nyu.edu/sites/default/files/assets/documents/Volatility%20Managed%20Portfolios.pdf
- [高] FAJ — *Conditional Volatility Targeting*(含可实现版 + 前视批评) https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853
- [中] Man Group — *The Impact of Volatility Targeting* https://www.man.com/insights/the-impact-of-volatility-targeting

**Regime 检测 / HMM 脆弱性**
- [高] MDPI JRFM (2020) — *Regime-Switching Factor Investing with Hidden Markov Models* https://www.mdpi.com/1911-8074/13/12/311
- [高] arXiv (2024) — *Downside Risk Reduction Using Regime-Switching Signals: Statistical Jump Model* https://arxiv.org/pdf/2402.05272
- [中] QuantifiedStrategies — *HMM Market Regimes* https://www.quantifiedstrategies.com/hidden-markov-model-market-regimes-how-hmm-detects-market-regimes-in-trading-strategies/
- [中] QuantStart — *Market Regime Detection using HMM in QSTrader* https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/

**双动量 / 趋势脆弱性 / whipsaw**
- [中] ThinkNewfound — *Fragility Case Study: Dual Momentum GEM* https://blog.thinknewfound.com/2019/01/fragility-case-study-dual-momentum-gem/
- [中] A Wealth of Common Sense — *My Thoughts on Gary Antonacci's Dual Momentum* https://awealthofcommonsense.com/2015/07/my-thoughts-on-gary-antonaccis-dual-momentum/
- [中] Antonacci (Medium) — *Extended Backtest of GEM* https://medium.com/@garyantonacci_30463/extended-backtest-of-global-equities-momentum-dual-momentum-eb12902612e0
- [中] Alvarez Quant — *Reducing Whipsaws When Using 200-day MA* https://alvarezquanttrading.com/blog/reducing-whipsaws-when-using-200-day-moving-average-for-market-timing/
- [中] QuantifiedStrategies — *200 Day Moving Average Trading Strategy (Backtest)* https://www.quantifiedstrategies.com/200-day-moving-average-trading-strategy/

**本仓内部交叉引用**
- `research/quant-factor-deep-research.md`(时序动量 MOP 2012、防过拟合纪律、IR=IC√Breadth)
- `scripts/run_routine.py::market_state()`(现有 regime 实现)
- `backtest/experiment_regime.py`(SPY>200dma 择时闸门实验)
- `feed/market/state.json` / `feed/market/history.json`(regime 快照与历史)

---

> **一句话总结**:配置层最稳的"regime 工具"不是某个复杂隐状态模型,而是 **趋势开关 + 波动目标 + 相关性早警** 这三件简单、PIT 干净、可证伪的事;它们买的是**尾部保险(降回撤)**,不是 alpha;2022 是它们唯一真正证明价值的一年,也是所有静态分散框架被同时证伪的一年。本仓现有 `state.json` 已在正确轨道,增量是把它从"标签"升级为"软开关 + 波动目标 + 股债相关监测",并用真 holdout / Deflated Sharpe 钉住有效性,不上 HMM。
