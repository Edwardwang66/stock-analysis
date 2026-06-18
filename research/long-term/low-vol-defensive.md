# 低波动 / 防御异象与长期复利 — 深度研究

> 目的:为**长期 buy-and-hold / 复利**评估低波动(Low-Vol)与防御类异象的真实价值。
> 方法:fan-out 检索一手文献 + 行业研究 → 关键数字标来源 URL 与可信度(高/中/低)→ 落地到本系统(已有 `lowvol` 因子)。
> 立场(房子风格):**净·扣成本是唯一货币**;诚实可证伪;标注前视/幸存者偏差;无法核实标"未核实"。优先 2023-2026 与免费/PIT 数据。
> 日期:2026-06-18。
> 范围硬约束:只写本文件,不改其他文件,不跑 git。

---

## 1) TL;DR

1. **低波/低beta 异象是金融学中最稳健、最违反 CAPM 的事实之一**:低风险股票的风险调整后收益(常常连绝对收益也)高于高风险股票。源头可追溯到 Black(1972)、Haugen-Heins(1975),现代证据 Ang-Hodrick-Xing-Zhang(2006)、Frazzini-Pedersen BAB(2014)、Baker-Bradley-Wurgler(2011)。[高]

2. **BAB(Betting-Against-Beta)美股长期 Sharpe ≈ 0.78(1926–2012/03)**,约为价值的 2 倍、动量的 1.4 倍;在 19 个国际股市、4 个资产类别中同向。**但**这是一个**做多低beta加杠杆 + 做空高beta去杠杆**的多空、需杠杆的市场中性因子,不等于一个无杠杆 buy-and-hold 组合的收益。[高]

3. **对长期 buy-and-hold,价值不在"更高 Sharpe 的多空因子",而在"更高几何收益/更低回撤 → 更好复利"**:做多腿(long-only 低波组合)在多数样本里以更低波动取得接近或略高于市值指数的算术收益,但**更高的几何收益**(波动拖累更小)和**显著更低的回撤**。这正是复利友好型特征。[中-高]

4. **发表后衰减 + 拥挤 + 估值变贵是真实风险**。低波 ETF 资产从 2010 年 <500 亿美元涨到 2024 年约 4000 亿(未独立核实精确数,量级可信);USMV/SPLV 类策略估值一度从历史折价收敛到与大盘持平(2025/06 Invesco SPLV 的 P/E ≈ 22.3 ≈ S&P500)。**买贵的防御 = 透支未来超额**。[中]

5. **空头腿(做空高beta/高波)在扣成本后基本被吃光**:2025 Soebhag-Baltussen-van Vliet 拆解显示 long leg 净 alpha ~2.70%/年,short leg 仅 ~0.52% 净(借券费+价差)。**对只做多的长期投资者,这反而是好消息——价值集中在做多腿。** [中]

6. **低波在两类环境系统性跑输:利率上行期(债券代理属性,负久期暴露)与价值/周期轮动期(高beta cyclical 领涨)**。2017–2019 轮动、2020 复苏、2022 加息都让低波难看。诚实结论:低波是**风格**而非**全天候**,需与价值/质量/动量组合或择时估值。[高]

7. **质量(Quality/QMJ)与低波高度重叠**:安全性(低beta、低波、低杠杆)是 QMJ 四要素之一。Fama-French(2015)五因子主张 profitability+investment 能"解释掉"低波。务实结论:**低波的可持续部分很可能就是质量在起作用**;单独追低波而忽略质量,易买到"便宜的垃圾低波"(低波但盈利差的债务沉重公司)。[高]

8. **最小方差(Min-Var)组合 vs 简单低波排序**:Min-Var 理论上更优(用整个协方差矩阵),但**对协方差估计误差极敏感、换手高、集中度高、需约束/收缩**;简单按个股波动率排序的低波组合**更稳健、更透明、换手更低、更可证伪**。对本系统(免费数据、防过拟合纪律),**优先简单排序 + 收缩协方差仅作对照**。[中-高]

9. **落地建议**:本系统 `backtest/factors_xs.py` 已有 `lowvol` 因子(63 日年化波动,sign=-1)。建议(a)新增 **beta 度量**与 **BAB 风格的 beta 中性**作为研究对照;(b)把低波**与质量正交**,避免买垃圾低波;(c)把低波定位为**long-only 防御腿 + 复利引擎**,而非多空 alpha;(d)用 walkforward + PBO + Deflated Sharpe + 估值监控(spread valuation)防过拟合与拥挤。

---

## 2) 定义 + 公式(波动率 / beta 度量)

### 2.1 三种"低风险"度量(常被混用,务必区分)

| 度量 | 定义 | 备注 |
|---|---|---|
| **总波动率** σ | 个股(超额)日/月收益的标准差,常年化 √252 | 本系统 `lowvol` 用的就是这个(63 日,年化) |
| **特质波动率** IVOL | 对 FF3/FF5 回归后**残差**的标准差 | Ang-Hodrick-Xing-Zhang(2006)用此;剔除系统性暴露 |
| **市场 beta** β | `β_i = ρ_{i,m} · σ_i / σ_m`(相关 × 波动比) | BAB 用此;低beta ≠ 低总波动(相关性不同) |

> 三者经验上高度相关但**不等价**:一只高波动但与市场低相关的股票可能 beta 不高。学术"低波异象"在 σ、IVOL、β 三种切法下都成立(稳健性证据),但**做空腿在排除微盘/penny/1月效应后才稳**(AHXZ)。[高｜AHXZ 2006]

### 2.2 总波动率因子(本系统现状)

```
rets_t = ln(P_t / P_{t-1})              # 过去 63 日对数日收益
σ_ann  = std(rets, ddof=1) × √252       # 年化波动
factor_value(lowvol) = σ_ann
合成方向 FACTOR_SIGN["lowvol"] = -1     # 取负:低波得高分
```

(来源:`backtest/factors_xs.py` L11/L18/L32-37;已核实存在于本仓库。)

### 2.3 BAB(Betting-Against-Beta)构造 — Frazzini-Pedersen(2014)

**Beta 估计(收缩到 1):**
```
β̂_TS_i = ρ̂ · (σ̂_i / σ̂_m)
   σ̂   : 用 1 年滚动日收益估波动(论文用 1y 日数据)
   ρ̂   : 用 5 年滚动(重叠 3 日对数收益)估相关,降噪
收缩:  β̂_i = 0.6 · β̂_TS_i + 0.4 · 1.0     # 向 1 收缩(Vasicek/Frazzini-Pedersen 式)
```

**组合构造(beta 中性多空):**
```
1. 按 β̂ 横截面排序,分高低两组(以中位数为界)。
2. 组内按 "rank 加权":离中位数越远权重越大(z = rank − mean_rank)。
   w_L = k · (z_L)^+   (低beta,做多)
   w_H = k · (z_H)^+   (高beta,做空)，Σ|w|=1
3. 加/去杠杆到 beta=1:
   做多腿乘 1/β_L(<1 → 加杠杆),做空腿乘 1/β_H(>1 → 去杠杆)
4. r_BAB = (1/β_L)·(r_L − r_f) − (1/β_H)·(r_H − r_f)   # 事前 beta≈0
```

**理论机制:杠杆与保证金约束(leverage aversion / funding liquidity)。** 受杠杆限制的投资者(共同基金、散户)为追求高收益**超配高beta**,推高其价格、压低其预期收益 → 低beta 被低估。BAB 通过**替投资者加杠杆买低beta**收割这块溢价。funding 流动性紧张时 BAB 回撤(机制可证伪点)。[高｜Frazzini-Pedersen, JFE 2014]

> ⚠️ 注意:上面的收缩系数 0.6/0.4 与窗口长度是论文常见复述值;**精确实现细节(对数收益重叠天数、年化口径)以原文附录为准**——我从二手摘要核到 0.6×β+0.4×1 的收缩形式与"1y 波动 / 5y 相关"窗口,但**未逐字核验原文公式编号**,标**部分未核实**。

### 2.4 Baker-Bradley-Wurgler(2011)"基准即套利限制"

**核心解释(为什么异象不被套掉):** 多数机构被赋予"跑赢固定基准(如 S&P500)"的任务。要超配低beta/低波的 alpha 股,组合 beta 会掉到 1 以下 → 相对基准的**跟踪误差**变大、且在牛市跑输 → 经理不敢做。同理也没人去做空高beta/高波(低 alpha)股。**基准约束 + 杠杆约束**共同让低波异象长期存活。这是"为何免费午餐没被吃掉"的最有说服力解释之一。[高｜Baker-Bradley-Wurgler, FAJ 2011, v67 n1]

---

## 3) 长期净收益 / 回撤证据(标来源可信度)

### 3.1 多空因子层面(学术,毛收益或风险调整)

| 证据 | 数字 | 样本 | 可信度 |
|---|---|---|---|
| BAB 美股 Sharpe | **≈ 0.78**(1926–2012/03);早期版本 0.75(到 2009) | 美股全样本 | 高｜Frazzini-Pedersen JFE 2014 |
| BAB 跨 4 个 20 年子区间 | **每个子区间均显著为正** | 1926–2012 | 高｜同上 |
| BAB 国际 | 19 个股市同向;跨规模/IVOL 十分位稳健 | 19 国 | 高｜同上 |
| BAB 跨资产 | 股指/国债/外汇/商品均正,年化 Sharpe 0.22–0.51 | 多资产 | 高｜同上 |
| 低波非系统性风险补偿 | 低波组合超额"不能视作系统性风险补偿"→ 倾向**错误定价**解释 | 1966–2011,46 年 | 高｜AQR/Li-Sullivan-Garcia-Feijóo, FAJ 2016 |
| IVOL 异象 | 高 IVOL → 低未来收益,全球同向,排除微盘/penny/1月后仍稳 | 多国 | 高｜AHXZ 2006 |

### 3.2 Long-only / 可投资层面(对 buy-and-hold 更相关)

| 证据 | 数字 | 样本 | 可信度 |
|---|---|---|---|
| 拆解 long vs short(净 alpha) | **long leg 净 alpha ~2.70%/年**;short leg 仅 ~0.52% 净(扣借券+价差) | 近期 | 中｜Soebhag-Baltussen-van Vliet 2025(经 evidenceinvestor 转述,**原文未逐字核**) |
| 标准低波 vs 增强(+value+mom) | 标准:10.8% 收益 / 0.51 Sharpe / **-50.4% MDD**;增强:13.6% / 0.75 / **-37.2% MDD** | 1990–2023 | 中｜同上转述 |
| 近 10 年低波**跑输**大盘 | S&P500:14.3%/年、Sharpe 0.82;低波版:9.5%/年、Sharpe 0.63 | 2015/05–2024/10 | 中｜evidenceinvestor 转述 |

**对复利的解读(关键):**
- 几何收益 `g ≈ μ − σ²/2`。低波组合 σ 低 → **波动拖累小** → 同等算术收益下几何更高;更低 MDD → 复利路径不被深坑打断(从 -50% 爬回需 +100%,从 -37% 爬回只需 +59%)。**这正是低波对长期 buy-and-hold 的真实卖点**——不是更高 Sharpe 的多空,而是**更平滑的复利路径**。[逻辑推导,数字示意]
- **但**近 10 年 long-only 低波**绝对收益跑输**大盘(上表),说明:在大盘由高beta科技股驱动的牛市里,买低波的代价是少赚。诚实结论:**低波改善的是"风险调整后"与"回撤",不保证"绝对跑赢"**。

---

## 4) 拥挤与估值风险

1. **资金涌入 → 估值抬升 → 未来超额被透支。** 低波 ETF 资产规模据转述从 2010 <500 亿增至 2024 ~4000 亿美元(量级可信,精确数**未独立核实**)。结果:防御股的"便宜"消失。**2025/06 Invesco SPLV 的 P/E ≈ 22.3,与 S&P500 持平** → 历史上驱动低波超额的估值折价被抹平。[中｜evidenceinvestor 转述]

2. **可证伪的拥挤监控指标 = "factor valuation spread"。** AQR/Robeco 系做法:看低波组合相对高波组合的估值利差(P/B、P/E、EBIT/EV)。利差处于历史**便宜端**时低波前瞻收益好,处于**贵端**时差。转述数据:低波约 **62% 时间**处于折价(此时年化超额 ~+2%),**38% 时间**处于溢价(此时跑输 ~-1.4%)。→ **不是"永远持有低波",而是"在低波便宜时超配"**。[中｜转述,机制方向可信]

3. **发表后衰减(post-publication decay)。** McLean-Pontiff 框架:异象发表后平均衰减约 1/3–1/2(本仓库 `quant-factor-deep-research.md` 已记录此机制)。低波被广泛产品化(2011 FAJ + 大量 ETF)后,**应对其历史 Sharpe 打折**再用。[高｜McLean-Pontiff 机制]

4. **拥挤的尾部风险:同向去杠杆。** 低波/BAB 在 funding 紧张、风格急转时可能同步回撤(2016 美国"低波闪崩"、2020/11 疫苗 value 反弹日)。拥挤放大了这种"踩踏"。[中]

> 房子立场:**把低波当 beta 折价收割,但用估值利差当闸门**;任何"低波永远赢"的叙事都按发表后衰减 + 当前估值打折,标可证伪门槛。

---

## 5) 数据与可得性(免费 / PIT 优先)

| 数据 | 用途 | 可得性 | 备注 |
|---|---|---|---|
| **Kenneth French Data Library** | FF3/FF5/动量因子月度;算 IVOL 需残差回归 | **免费** | 学术基准;PIT 友好(月末口径) |
| **AQR Datasets — Betting Against Beta (Equity Factors, Monthly)** | BAB 因子月度,美股+23 国,持续更新 | **免费**(注册下载) | 直接对照 BAB;**注意 AQR 自家口径,非完全可复现微观构造** |
| **AQR — Quality Minus Junk (Factors, Monthly)** | 质量因子(含 safety 子项)用于正交化 | **免费** | 检验低波 vs 质量重叠 |
| 本系统日线 adj close(已有) | 算 σ(63d 已实现)、beta(需市场指数) | **已有** | `backtest/factors_xs.py` |
| 市场指数日收益(SPY/标普) | 估 beta、做 beta 中性 | **免费/已有** | beta = ρ·σ_i/σ_m |
| 个股估值(P/B、P/E、EBIT/EV) | 算 low-vol valuation spread(拥挤闸门) | **半免费**(需基本面源) | 免费源覆盖与 PIT 重述是难点,标**部分可得** |

**前视/幸存者偏差红旗:**
- **beta/σ 用未来数据**:必须严格滞后(t 时点只用 ≤t 的收益)。本系统 `factor_values(adj, i)` 用切片到 i,方向正确,但要确保 universe 也是 **PIT 成分**(仓库已有 `pit_membership.py`/`pit_sp500.json`)。
- **退市/幸存者**:低波研究尤其怕——很多高波动股是**已退市的输家**;若 universe 只含今天还活着的票,会**高估低波的相对优势**。务必用 PIT 成分 + 含退市的收益。[高｜方法论红旗]
- **微盘/penny 主导**:BAB 的高 Sharpe 部分来自微/纳米盘超配(见 §7 反方);用前必须做流动性/规模过滤,并扣真实成本。

---

## 6) 落地到本系统(因子 / 脚本 / 验证)

> 仅为研究建议,本文件**不改任何代码**。下述为可落地清单。

### 6.1 现状
- `backtest/factors_xs.py`:已有 `lowvol`(63 日年化波动,`FACTOR_SIGN=-1`),与 `mom_12_1 / reversal / hi52` 同框架,走 z-score / rank-IC / decile spread。
- `backtest/costs.py`:已有 half-spread + sqrt 冲击成本 + 换手成本 + 容量上限 → **扣成本评估到位**。
- 验证设施:`walkforward.py`、`study_pbo.py`(CSCV-PBO)、`validation.py`、`xs_backtest.py`。

### 6.2 建议新增/研究项(按优先级)

1. **加 beta 度量做对照(低成本高价值)。**
   在 `factor_values` 同框架下新增 `beta`(需传入市场收益序列):
   `β = corr(r_i, r_m) · std(r_i)/std(r_m)`,可加 0.6/0.4 收缩。
   做两组对照:`lowvol`(总波动)vs `lowbeta`(beta)。检验哪个 rank-IC 更稳、扣成本后更好。

2. **低波 × 质量正交(避免"便宜的垃圾低波")。**
   用 QMJ/盈利指标对 `lowvol` 做横截面正交(回归取残差),或在合成时**先质量门槛后低波排序**。目标:剔除"低波但高杠杆/亏损"的债券代理型陷阱。这直接回应 §7 的 FF5 批评。

3. **long-only 防御腿(复利定位),而非多空。**
   对 buy-and-hold:构造 **long-only 低波 + 质量**组合,目标函数看**几何收益 / MaxDD / Calmar**,而非多空 Sharpe。空头腿扣成本后贡献低(§3.2),长期投资者不必做空。

4. **拥挤/估值闸门(可证伪)。**
   计算 low-vol valuation spread(低波组合 vs 高波组合的 P/E 或 EBIT/EV 中位数比),作为**择时权重**:利差贵端时降低低波暴露。需接基本面数据(标**部分可得**)。

5. **Min-Var 仅作对照,不作主线。**
   可加一个 Ledoit-Wolf 收缩协方差的 GMV 组合做 benchmark,但因换手/集中/估计误差,**主线用简单排序**。对比换手与扣成本净值,用证据说话。

### 6.3 验证纪律(房子硬规矩)
- **walkforward + 严格滞后**,universe 用 PIT 成分(`pit_membership.py`),收益含退市。
- **CSCV-PBO**(`study_pbo.py`)+ **Deflated Sharpe**(按试验次数通缩)+ **t>3.0**。低波因子简单、试验少,反而是 deflation 的"良民"——但**只要你试了多个窗口(21/63/126/252)就要计入 N**。
- **扣成本是唯一货币**:用 `costs.py` 全程扣 half-spread + 冲击;报告**净**几何收益、净 Sharpe、MaxDD、换手、容量。
- **分区间稳健性**:必须单独看**加息期(2022)/价值轮动期(2016-H2、2020Q4-2021)**的表现,诚实展示跑输,而非只报全样本均值。

---

## 7) 风险与反方(诚实可证伪)

1. **BAB 的高 Sharpe 被批"靠微/纳米盘 + 非标准构造"。** Novy-Marx & Velikov,*"Betting against betting against beta"*(JFE 2022,**摘要核实,原文 403 未取全文**):BAB 的 rank-weighting 实际近似**等权**,巨幅超配微/纳米盘,扣真实交易成本与做空成本后**收益大幅缩水**;用规模上限或市值加权重构后 alpha 弱化很多。→ **对实盘(尤其有容量要求),BAB 的纸面 Sharpe 不可照搬。** [高｜S0304405X21002051,摘要]

2. **Fama-French(2015)五因子:低波"被解释掉"。** profitability(RMW)+ investment(CMA)能吸收大部分低波/低beta 溢价 → 低波**可能不是独立因子**,只是质量/盈利的影子。务实含义:**单押低波 = 押一个可能冗余的因子**;与质量同测才知增量。[高]

3. **利率上行 = 系统性逆风(债券代理)。** 低波组合**负久期暴露**:Morningstar/Acadian/Seeking Alpha 多方指出低波在加息期跑输,高波 cyclical 因经营/财务杠杆 + 增长能对冲加息。2022 是教科书案例。→ 低波**不是全天候**,对利率制度敏感。[高｜Morningstar / Acadian]

4. **价值/周期轮动期跑输。** 2017–2019、2020 复苏、2021 reflation,高beta/周期/小盘领涨时低波系统性落后。**"Low Volatility Is Not a Buy and Hold Strategy"**(Pacer ETFs 标题即观点)——业界都承认需轮动/择时,纯持有会经历长期相对回撤。[中｜Pacer ETFs(卖方,利益相关,标中)]

5. **拥挤 + 估值贵(§4)= 前瞻超额被透支。** 当前 SPLV 估值与大盘持平 → 历史折价驱动的超额不再免费。[中]

6. **数据陷阱放大历史优势。** 不含退市的 universe、未扣做空/借券成本、含微盘,都会**系统性高估**低波/BAB。任何复现若没处理这些,结论**不可信**。[高｜方法论]

7. **机制可被套利削弱。** Baker-Bradley-Wurgler 的"基准约束"解释意味着:**只要约束放松**(更多绝对收益/低波产品、机构 mandate 演化),异象就该衰减。低波产品爆发本身就是套利力量进场的信号 → 预期衰减。[高,逻辑]

**反方总结(房子口径):** 低波/防御**对长期复利仍有真实价值(更低回撤、更高几何路径)**,但(a)价值集中在 **long-only 做多腿 + 质量**,(b)多空 BAB 的纸面 Sharpe 实盘大打折扣,(c)需用**估值利差择时**应对拥挤,(d)必须容忍加息/价值轮动期的相对回撤。**它是复利友好的风格,不是 alpha 永动机。**

---

## 8) 参考来源(URL + 可信度)

> 可信度:高 = 一手学术/原始论文;中 = 行业研究/转述/卖方;低 = 二手未核。标注"未核实"= 未能取原文逐字核对。

**一手学术(高):**
- Frazzini & Pedersen, *Betting Against Beta*, JFE 2014 — https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf (NBER WP: https://www.nber.org/system/files/working_papers/w16601/w16601.pdf) — BAB 定义、美股 Sharpe 0.78、杠杆约束机制。**[高;构造公式细节部分未逐字核]**
- Baker, Bradley & Wurgler, *Benchmarks as Limits to Arbitrage: Understanding the Low-Volatility Anomaly*, FAJ 2011, v67 n1 — https://rpc.cfainstitute.org/research/financial-analysts-journal/2011/benchmarks-as-limits-to-arbitrage-understanding-the-low-volatility-anomaly (SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1585031) — 基准约束解释。**[高]**
- Ang, Hodrick, Xing & Zhang, *High Idiosyncratic Volatility and Low Returns* (IVOL 异象) — https://business.columbia.edu/sites/default/files-efs/pubfiles/3361/ang_high_idiosyncratic_volatility.pdf — IVOL 全球稳健、排除微盘/penny/1月后仍存。**[高]**
- Asness, Frazzini & Pedersen, *Quality Minus Junk* — https://www.aqr.com/Insights/Research/Working-Paper/Quality-Minus-Junk (PDF: http://www.econ.yale.edu/~shiller/behfin/2013_04-10/asness-frazzini-pedersen.pdf) — 质量=盈利+成长+安全+派息;安全性(低beta/低波)是质量子项 → 低波与质量重叠。**[高]**
- Li, Sullivan & Garcia-Feijóo (AQR/FAJ 2016), *The Low-Volatility Anomaly: Market Evidence on Systemic Risk vs. Mispricing* — https://www.aqr.com/Insights/Research/Journal-Article/The-Low-Volatility-Anomaly-Market-Evidence-on-Systemic-Risk-vs-Mispricing — 1966–2011,倾向错误定价解释。**[高]**

**反方 / 批评(高,部分仅摘要):**
- Novy-Marx & Velikov, *Betting against betting against beta*, JFE 2022 — https://www.sciencedirect.com/science/article/abs/pii/S0304405X21002051 — 微/纳米盘超配、近似等权、扣成本后缩水。**[高;全文 403,仅摘要核实 → 标"全文未核实"]**
- Fama & French (2015) 五因子主张 profitability+investment 解释低波 — 经多处转述,**原文未在本轮取**。**[高机制,引用未逐字核]**

**行业 / 转述(中;含卖方利益相关):**
- The Evidence-Based Investor, *Deep Dive: Low-volatility investing* — https://www.evidenceinvestor.com/post/low-volatility-investing — 转述 Soebhag-Baltussen-van Vliet 2025(long 2.70% / short 0.52% 净)、近10年低波跑输(9.5% vs 14.3%)、SPLV P/E 22.3、估值利差 62%/38%。**[中;底层原文未逐字核]**
- Morningstar, *Low-Vol Strategies May Underperform When Rates Rise* — https://www.morningstar.com/stocks/low-vol-strategies-may-underperform-when-rates-rise — 加息逆风。**[中]**
- Acadian, *Low-Volatility Investing: Elephant in the Room* — https://www.acadian-asset.com/investment-insights/managing-risk/low-volatility-investing-welcoming-the-elephant-into-the-room — 利率/估值/拥挤。**[中,卖方]**
- Pacer ETFs, *Low Volatility Is Not a Buy and Hold Strategy* — https://www.paceretfs.com/resources/resource-library/low-volatility-is-not-a-buy-and-hold-strategy/ — 需择时。**[中,卖方,利益相关]**
- Robeco, *Low volatility anomaly* (glossary) — https://www.robeco.com/en-us/glossary/quantitative-investing/low-volatility-anomaly — 估值利差/拥挤方法论。**[中,卖方]**
- Quantpedia, *Low Volatility Factor Effect in Stocks* — https://quantpedia.com/strategies/low-volatility-factor-effect-in-stocks — 策略综述。**[中]**

**数据源(免费/PIT):**
- Kenneth French Data Library(FF3/FF5/Mom,免费,月度)— https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html **[高]**
- AQR — Betting Against Beta (Equity Factors, Monthly) — https://www.aqr.com/Insights/Datasets/Betting-Against-Beta-Equity-Factors-Monthly **[高;免费注册]**
- AQR — Quality Minus Junk (Factors, Monthly) — https://www.aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly **[高;免费]**

**本仓库交叉引用:**
- `backtest/factors_xs.py`(已有 `lowvol` 因子)、`backtest/costs.py`、`study_pbo.py`、`walkforward.py`、`pit_membership.py` — 已核实存在。
- `research/quant-factor-deep-research.md`(McLean-Pontiff 发表后衰减、Factor Zoo 中已列 Low-Vol/BAB Sharpe~0.75)。

---

### 核验状态摘要
- **已核实(高)**:BAB 美股 Sharpe 0.78(1926–2012/03)、跨子区间/国际/资产同向;BBW 基准约束解释;AHXZ IVOL 异象;QMJ 安全性子项;AQR 2016 错误定价倾向;本仓库 `lowvol` 因子存在。
- **部分未核实**:BAB 收缩系数 0.6/0.4 与窗口长度(摘要核到形式,未逐字核原文公式);Novy-Marx-Velikov 全文(403,仅摘要);Soebhag-Baltussen-van Vliet 2025 的 2.70%/0.52% 与各项数字(经 evidenceinvestor 转述,原文未取);低波 ETF 资产 500亿→4000亿(量级可信,精确数未独立核实);SPLV P/E 22.3(单一转述源)。
- **未核实**:Fama-French 2015 原文逐字;估值利差 62%/38% 的样本与方法细节。
