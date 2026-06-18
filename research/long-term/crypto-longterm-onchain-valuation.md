# 加密资产的长期估值与链上指标 — 深度研究报告

> 目的:为"长期持有/定投/再平衡"的加密配置层,评估链上估值指标(MVRV、NUPL、SOPR、Reserve Risk、Puell、Mayer、200WMA、S2F、SSR、净流)作为周期顶底信号的**真实证据强度与失效模式**,并给出可落地、防过拟合、免费数据优先的做法。
> 方法:fan-out 检索一手来源(Glassnode/CoinMetrics 官方文档、JF/RFS 学术论文、批判文章)→ 关键定义与公式核到原始页 → 关键结论标 URL + 可信度。
> 日期:2026-06-18。立场遵循房子风格:**诚实可证伪、净·扣成本、标注前视/过拟合**。
> 核心立场:**链上"周期指标"样本极小(n=3–4 个完整周期)、口径多、极易事后拟合;它们能讲一个自洽的"贵/便宜"故事,但不构成可独立交易的择时信号。最多用于长期定投/再平衡的温和倾斜(tilt),且必须扣成本、扣前视后才采信。**

---

## 1. TL;DR

1. **链上估值指标的"历史精度"几乎全是样本内叙事。** MVRV-Z、NUPL、Reserve Risk、Puell、200WMA 都被宣传为"每个周期顶底误差两周内命中"——但这些阈值(红区/绿区)是**在已知顶底之后画上去的**,n=3–4 个周期,自由度几乎为 0。所谓"历史命中率 100%"是 **in-sample 拟合**,不是样本外预测力。可信度:高(方法学事实)。

2. **Stock-to-Flow(S2F)已被作者本人在 2021 年实质证伪,且统计基础是协整谬误。** PlanB 的 floor model 预测 2021/11 ≈ \$98k、12 月 ≈ \$135k,实际 12 月收 ≈ \$47k,误差过半;统计上 S2F 与价格都是非平稳序列,OLS 残差强自相关,Engle-Granger 协整检验前提不满足 → **典型 spurious regression**。S2F **不应进入任何生产信号**。可信度:高 [CoinDesk 2020; Burger/Amdax; PlanB 公开声明]。

3. **学术上加密横截面只需三因子:市场 + 规模 + 动量(Liu-Tsyvinski-Wu, JF 2022)。** 10 个特征构造的多空策略,其超额收益**全部被三因子模型吸收**。时序上"动量 + 投资者注意力"可预测收益;收益暴露于**网络因子(采用度)**而非生产因子(挖矿成本)——这直接削弱"挖矿成本/S2F"叙事。可信度:高 [JF 2022; RFS 2021]。

4. **减半(halving)叙事统计不稳健。** 仅 3 个完整周期(2012/2016/2020,2024 为第 4 次)。回报幅度逐周期衰减:≈ +8,200% → +3,000% → +690%,2024 后周期为历来最弱;窗口选择(30 天 vs 365 天)能讲完全不同的故事。**n 太小,不能据此择时。** 可信度:高(对"小样本"这一判断);对"减半有因果"则可信度低。

5. **可落地结论:把链上指标当"估值温度计 + 再平衡触发器",不当"买卖择时器"。** 用 MVRV-Z / Mayer 这类**极少数、口径透明、可免费复现**的指标,对长期定投做**有界倾斜**(例如深度低估时小幅加码再平衡),而非全仓进出。

6. **免费且可程序化的链上源是 CoinMetrics Community API**(无需 key,CC BY-NC,`api.coinmetrics.io/v4`,含 `CapRealUSD`/`CapMVRVCur`)。Glassnode 免费层仅网页、24h 分辨率、**API 需付费 Pro**。blockchain.com / Hyperliquid 提供互补的免费原始数据。可信度:高 [CoinMetrics 官方文档]。

---

## 2. 各链上指标:定义 + 公式

> 约定:Market Cap = 流通供给 × 现价;Realized Cap = 按"每个 UTXO/币上次链上移动当日收盘价"计价的总和(用"成本基础"近似)。下列公式以 Glassnode/CoinMetrics 官方口径为准。

### 2.1 Realized Cap(已实现市值)
- **定义**:对所有币,按其**最后一次链上移动当日的 USD 价格**计价并求和。代表全网"链上成本基础"的聚合。CoinMetrics 2018 年首创该指标。[高｜CoinMetrics docs: gitbook-docs.coinmetrics.io/.../market-capitalization]
- **作用**:比 Market Cap 更"慢"、更稳;过滤掉久未移动的币的现价波动,近似"投入资本"。

### 2.2 MVRV 与 MVRV-Z
- **MVRV ratio** = `Market Cap / Realized Cap`。>1 全网平均浮盈,<1 全网平均浮亏。
- **MVRV-Z Score** = `(Market Cap − Realized Cap) / StdDev(Market Cap)`。分子是市值对已实现值的偏离,分母用市值的**历史标准差**归一化。由 `Awe_andWonder` 于 2018/10 提出。[高｜Glassnode docs: docs.glassnode.com/.../mvrv/mvrv-z-score]
- **解读**:Z 高(历史红区)≈ 顶;Z 低/负(绿区)≈ 底。**注意**:`StdDev(Market Cap)` 用全历史滚动,本身随牛市膨胀 → Z 的"红区阈值"会漂移(见 §4)。

### 2.3 NUPL(净未实现盈亏)
- **公式** = `(Market Cap − Realized Cap) / Market Cap`(= 1 − 1/MVRV)。即"若今天全卖,全网净浮盈占市值比例"。[高｜Glassnode docs: docs.glassnode.com/.../nupl]
- **变体**:STH-NUPL(UTXO < 155 天,短期持有者)、LTH-NUPL(≥ 155 天,长期持有者)。接近 1 历史上对应全局顶部。**本质与 MVRV 同源**(都基于 Market−Realized 差),不是独立信号。

### 2.4 SOPR(已花费产出盈亏比)
- **公式** = `卖出时 USD 值 / 创建时 USD 值`(已花费产出口径)。>1 平均盈利了结,<1 平均亏损了结,=1 盈亏平衡。[高｜Glassnode docs: docs.glassnode.com/.../sopr]
- **aSOPR**:剔除存活 < 1 小时的 UTXO,去噪,牛熊 regime 读数更干净。
- **作用**:更偏"行为/已实现",可与 MVRV(未实现)互补;但日频噪声大,仅适合做 regime 而非择时。

### 2.5 Reserve Risk
- **公式** = `Price / HODL Bank`,HODL Bank = 累计机会成本(由 VOCD 衍生)。VOCD = Bitcoin Days Destroyed × spot price;常用 30 日中位数 MVOCD 去噪。[高｜Glassnode docs: docs.glassnode.com/.../coin-days-destroyed/reserve-risk]
- **解读**:低 Reserve Risk = 长期持有者信念强但价格低 → 历史上的高风险回报吸引区(底部);高 = 顶部。**口径复杂、参数多(30 日中位数等)→ 过拟合面更大**。

### 2.6 Puell Multiple(矿工侧)
- **公式** = `当日发行(USD) / 365 日发行(USD)均值`。低值 = 挖矿不经济 → 矿工投降,常见底部信号;高值 = 矿工超额收入,常见顶部。[中-高｜themarketsunplugged / coinmarketcap cycle indicators]
- **注**:减半瞬间发行量阶跃减半 → Puell 分子结构性跳变,需注意口径断点。

### 2.7 Mayer Multiple 与 200 周均线(纯价格)
- **Mayer Multiple** = `Price / 200日MA`。>1 在 200DMA 上方,<1 在下方;历史大底常见 < 0.8,极端 < 0.6。[中｜newhedge / btcframe 2025]
- **200 周均线(200WMA)**:200 个周线收盘均值;2015/2018/2022 三次熊底价格都在 200WMA 附近获支撑。[中｜bitcoinmagazine / phemex]
- **优点**:**纯价格、零链上依赖、可在任何 OHLC 上免费复现**,是性价比最高的"长期估值温度计"。**缺点**:仍是 n=3 的样本内观察。

### 2.8 Stock-to-Flow(S2F)— 仅作批判对象
- **公式** = `Stock / Flow`(存量/年增发),PlanB 用 `ln(price) = a + b·ln(S2F)` 回归。**不纳入生产信号**(见 §3.5)。

### 2.9 Stablecoin Supply Ratio(SSR)与交易所净流
- **SSR** = `BTC Market Cap / 稳定币总 Market Cap`。低 SSR = 场外稳定币"弹药"相对充足(潜在买压);高 SSR = 弹药薄。[高｜CryptoQuant / Glassnode docs]
- **交易所净流(exchange netflow)** = 流入 − 流出交易所的币量。持续净流出常被解读为"搬去冷钱包/长期持有"(供给收紧),净流入为潜在抛压。**口径强依赖交易所地址标注质量**,免费层覆盖差、噪声大。

---

## 3. 长期信号:证据强度与失效模式(标可信度)

### 3.1 MVRV-Z / NUPL 作为顶底信号
- **宣称**:MVRV-Z 自 2011 起"每个周期顶底误差两周内命中";Z<0(尤其 <−1)历史上先于每轮大涨;NUPL→1 对应全局顶。[中｜axeladlerjr / spotedcrypto / bitcoinmagazinepro]
- **真实强度**:**这些是描述性、样本内的**。阈值在事后画定,只有 3–4 个顶、3–4 个底可"验证"。**没有公开的、预注册的、扣成本的样本外检验**支持其择时 alpha。可信度:对"描述贵/便宜"=中;对"可交易择时"=**低**。
- **失效**:Z 的分母 `StdDev(Market Cap)` 随历史膨胀 → 每轮牛市顶部 Z 峰值**单调下移**(2013 ≫ 2017 > 2021),意味着"固定红区阈值"会越来越早误报或漏报;机构化(ETF)后周期形态可能进一步改变。可信度:高。

### 3.2 SOPR / Reserve Risk
- SOPR=1 作为"支撑/阻力"在牛/熊有方向性差异(牛市回踩 1 获支撑),是合理的**行为 regime 描述**,但日频噪声大、无稳健择时证据。可信度:中(描述)/低(择时)。
- Reserve Risk 底部识别"事后看很准",但参数多(MVOCD 窗口)、口径不透明,过拟合风险高于 MVRV。可信度:低-中。

### 3.3 Puell / Mayer / 200WMA
- 三者在 **2015/2018/2022 三次熊底**都"落在便宜区",一致性好;Mayer<0.8、价格触 200WMA、Puell 低位常**共振**于大底。[中｜coinmarketcap cycle indicators]
- **但**:三点共振 = 3 个样本点,且这些指标**高度相关**(都随价格深跌而触发),不是独立证据。"四条件共振=每次都在底部"属典型小样本叙事。可信度:对"共振时确实便宜"=中;对"可据此抄底择时"=低。

### 3.4 学术因子证据(可信度最高的一块)
- **Liu-Tsyvinski-Wu, JF 2022 "Common Risk Factors in Cryptocurrency"**:**市场 + 规模 + 动量**三因子吸收 10 个特征多空策略的超额收益。[高｜onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119;NBER w25882;Yale econ]
- **Liu-Tsyvinski, RFS 2021 "Risks and Returns of Cryptocurrency"**:强时序动量;**投资者注意力**(如 Google 搜索)预测未来收益;收益暴露于**网络/采用因子**,**不暴露于生产因子(挖矿成本)** → 直接反驳"挖矿成本/S2F 决定价值"。[高｜academic.oup.com/rfs/article-abstract/34/6/2689]
- **落地含义**:长期层真正有学术背书的不是"链上估值择时",而是**动量 + 规模 + 注意力**这类截面/时序因子。链上估值指标至多作为**情境(regime)变量**。

### 3.5 Stock-to-Flow 的证伪(最确定的失效案例)
- **预测失败**:2021/12 floor 预测 \$135k,实际收 ≈ \$47k;PlanB 一度自称模型 "invalidated"。[高｜medium/nicolakharvey 综述;PlanB 公开]
- **统计谬误**:S2F 与价格均非平稳,直接 OLS → 残差强自相关、系数虚高(spurious regression);Engle-Granger 协整检验前提不满足,不能用于宣称协整;模型忽略需求侧、近乎循环论证(用 stock 预测含 stock 的市值)。[高｜CoinDesk 2020-06-30;Burger/Amdax Part II;Felipe Threadreader 统计批判]
- **结论**:S2F **永久排除**于生产信号;仅作"如何被叙事+曲线拟合误导"的教学案例。

### 3.6 减半周期叙事
- 完整周期 n=3(2012/2016/2020),2024 为第 4 次但后续偏弱。回报衰减 ≈ 8,200%→3,000%→690%;2024 后为历来最弱(可能因现货 ETF、机构化、宏观流动性主导)。[中-高｜fractalcycles;hyrotrader]
- 多篇学术(MDPI/ScienceDirect 2023-2026)讨论减半与超级周期,但**效应强烈依赖测量窗口与控制变量**,无稳健因果。可信度:对"小样本不可据此择时"=高;对"减半→涨"=低。

---

## 4. 小样本 / 过拟合警示(本节是全报告的"红线")

1. **样本量 = 周期数,不是天数。** 链上周期指标的有效自由度 ≈ 完整牛熊周期数 = **3–4**,不是 4000+ 天。任何"日频回测 Sharpe"都把高度自相关的同一周期重复计数,**严重高估**显著性。[高｜方法学;arxiv 2209.05559 论 crypto 回测过拟合]
2. **指标花园(garden of forking paths)。** 同一原始数据可切出几十个指标 × 几十种平滑 × 几十个窗口 → 必然"发现"某个在单一 regime 有效的信号。[高｜cryptoadventure 框架]
3. **阈值事后画定。** 红/绿区是在已知顶底后标注的;这是 look-ahead,不是预测。
4. **指标间强共线。** MVRV、NUPL、Reserve Risk、SOPR 同根(Market vs Realized / 成本基础),"多指标共振"不是独立证据,而是同一信息的重复。
5. **非平稳 + 协整谬误**(S2F 是教科书案例):非平稳序列回归易得虚假显著。[高]
6. **regime 漂移**:杠杆扩张期有效的指标,在流动性收缩/机构化期失效;ETF(2024)后结构变化明显。[高]
7. **防过拟合纪律(若坚持检验)**:Purged K-Fold + Embargo + CPCV;按试验次数做 Deflated Sharpe;**多重检验门槛 t>3**(非 2);记录所有回测次数。链上"周期指标"几乎都过不了 t>3。[高｜对齐本系统 quant-factor 报告]
8. **诚实底线**:对周期顶底,**我们不声称可预测**;只声称"能描述当前相对贵/便宜",并据此做**有界、温和**的再平衡倾斜。

---

## 5. 数据与可得性(免费链上源优先)

| 源 | 关键指标 | 程序化访问 | 免费? | 备注 / 可信度 |
|---|---|---|---|---|
| **CoinMetrics Community API** | `CapRealUSD`(已实现市值)、`CapMVRVCur`(MVRV)、`CapMrktCurUSD`(市值)、活跃供给、价格 | `https://api.coinmetrics.io/v4`,**无需 key** | 是,**CC BY-NC 4.0**,限速 10 req/6s/IP | **首选免费可复现源**;MVRV/Realized Cap 可直接取或自算。[高｜gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data] |
| **Glassnode 免费层** | MVRV-Z、NUPL、SOPR、Reserve Risk、SSR 等图表 | **API 仅付费 Pro**;免费仅网页、24h 分辨率 | 网页免费,API 否 | 适合人工核对/取阈值参考,不适合自动 feed。[高｜docs.glassnode.com/basic-api/api;studio.glassnode.com/pricing] |
| **blockchain.com Charts/API** | 发行量、难度、交易数、矿工收入(→ 自算 Puell) | REST/CSV,免费 | 是 | 原始链上聚合,可自建 Puell/issuance。[中] |
| **Hyperliquid** | 永续 funding、OI、清算、basis(衍生品情绪) | 公开 API,免费 | 是 | 本系统已接入;补充"杠杆/情绪" regime,与链上估值互补。[中-高,本系统已用] |
| **价格 OHLC(Binance 等)** | 200WMA、Mayer Multiple | 已接入 | 是 | **纯价格指标零额外依赖**,优先实现。[高] |

落地数据原则:
- **MVRV / Realized Cap / MVRV-Z → 走 CoinMetrics Community**(可程序化、可复现、免费)。
- **Mayer / 200WMA / Puell → 自算**(价格 + blockchain.com 发行量),不依赖付费链上。
- **NUPL/SOPR/Reserve Risk → 仅人工参考**(免费层无 API),不进自动信号。
- **SSR / 交易所净流 → 暂缓**(免费可得性差、地址标注噪声大),标记为"未核实可程序化免费源"。

---

## 6. 落地到本系统(长期加密配置 / 再平衡 / feed / 验证)

### 6.1 配置哲学(扣成本、扣前视后的温和倾斜)
- **基线 = 规则化定投 + 周期再平衡**(DCA + rebalance),不做全仓择时。
- **链上估值仅做有界 tilt**:定义一个 0–1 的"估值温度" `valuation_score`(由 MVRV-Z 与 Mayer 合成,见下),把目标加密权重在 `[w_min, w_max]` 之间线性微调,**单次调整幅度设硬上限**(如 ±20% 相对基线),避免事后拟合的阈值主导仓位。

### 6.2 合成"估值温度"(只用少数透明指标)
- 取两个**口径透明、可免费复现、相对独立**的指标:
  - `mvrv_z`(CoinMetrics:`CapMrktCurUSD`、`CapRealUSD` + 滚动 StdDev 自算)
  - `mayer`(价格 / 200DMA;另存 `price/200WMA`)
- 归一为分位(用**扩张窗口 expanding rank**,避免用未来分布 → 防前视):
  - `temp = 0.5*pct_rank(mvrv_z) + 0.5*pct_rank(mayer)`,`temp∈[0,1]`,高=贵。
- 再平衡倾斜:`target_w = w_base * (1 + k*(0.5 - temp))`,`k` 小(如 0.4),并 clip 到 `[w_min, w_max]`。**深度低估(temp 低)→ 略加码;过热(temp 高)→ 略减码。**

### 6.3 feed 端点(对齐现有 `feed/crypto/`)
- 新增(只读、日频)`feed/crypto/onchain-valuation.json`,字段建议:
  ```json
  {
    "asset": "BTC",
    "asof": "2026-06-18",
    "market_cap_usd": null,
    "realized_cap_usd": null,
    "mvrv": null,
    "mvrv_z": null,
    "mayer_multiple": null,
    "price_over_200wma": null,
    "puell_multiple": null,
    "valuation_temp": null,
    "valuation_temp_pctile_window": "expanding",
    "source": "coinmetrics-community + ohlc",
    "caveat": "small-sample (n=3-4 cycles); descriptive only, not a timing signal"
  }
  ```
- 数据管线:`scripts/` 下加 `fetch_coinmetrics_community.py`(无 key,限速 10 req/6s),拉 `CapMrktCurUSD/CapRealUSD/CapMVRVCur`;Puell 用 blockchain.com 发行量自算;Mayer/200WMA 用现有 OHLC。
- 看板:把 `valuation_temp` 作为**情境带(regime band)**展示,**显式标注"描述性、非择时、小样本"**,与现有 funding/OI/清算面板并列。

### 6.4 验证(诚实、可证伪)
- **不**对 MVRV-Z 阈值做"优化回测"(必过拟合)。改做:
  1. **预注册** `valuation_temp` 公式与 tilt 规则(冻结参数),仅做**前瞻 paper-trade**(walk-forward,扩张窗口分位),记录净·扣成本(含再平衡换手成本)收益与最大回撤。
  2. **基准对照**:tilt 组合 vs 纯定投 vs 纯持有;只有在**扣成本后** Sharpe/回撤显著改善才采信。
  3. **稳健性**:跨资产(BTC/ETH)、跨参数(k、window、权重)做敏感性;若结论对参数极敏感 → 视为过拟合,降级为"仅展示"。
  4. 用本系统已有的 **Deflated Sharpe / t>3 / PIT** 纪律统一裁决。

### 6.5 不做清单
- 不上 S2F(已证伪)。
- 不做基于减半倒计时的择时(n 太小)。
- 不把 NUPL/SOPR/Reserve Risk 进自动仓位(免费层无 API + 与 MVRV 共线)。
- 不声称"抄底/逃顶"能力,只声称"温度计 + 有界再平衡"。

---

## 7. 风险与反方

- **反方 1:"链上数据是真相,顶底识别确实很准。"** 部分正确——它**描述**贵/便宜很有信息量;但"准"基于 n=3–4 的事后阈值,无预注册样本外证据。我们采纳其**描述价值**,拒绝其**择时声明**。
- **反方 2:"机构化/ETF 让链上指标失效。"** 合理担忧:2024 后周期最弱、Z 峰值持续下移,确支持"指标会漂移"。对策:用**扩张窗口分位**(自适应)而非固定阈值,并接受信号强度衰减。
- **反方 3:"动量/规模因子已被 JF 证实,为何还碰链上?"** 因子是**收益驱动**;链上估值是**情境/风险变量**(贵时降杠杆)。二者互补,链上仅作 tilt,不喧宾夺主。
- **反方 4:"温和 tilt 收益太小,不值得做。"** 可能。所以**验证门槛设为扣成本后显著改善**;若达不到,诚实地把它降级为纯展示型情境带——这本身就是有价值的研究结论。
- **自身风险:再平衡换手成本**会吃掉 tilt 的边际收益;**前视风险**藏在分位计算里(必须用 expanding、PIT);**交易所/标注数据质量**影响净流类指标(故不纳入)。

---

## 8. 参考来源(URL + 可信度)

**学术(高)**
- Liu, Tsyvinski, Wu — *Common Risk Factors in Cryptocurrency*, Journal of Finance 77(2), 2022, pp.1133-1177(市场+规模+动量三因子)。https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119 ; NBER w25882 https://www.nber.org/papers/w25882 ; Yale https://economics.yale.edu/research/common-risk-factors-cryptocurrency 〔高〕
- Liu, Tsyvinski — *Risks and Returns of Cryptocurrency*, Review of Financial Studies 34(6), 2021(时序动量、投资者注意力、网络因子≠生产因子)。https://academic.oup.com/rfs/article-abstract/34/6/2689/5912024 ; SSRN 3226952 〔高〕
- *Using on-chain data to predict Bitcoin cycles*, ScienceDirect 2026(链上择时,正文 403 未取全文,仅标题/摘要)。https://www.sciencedirect.com/science/article/pii/S0275531926002138 〔中,正文未核实〕
- *Deep RL for Crypto Trading: addressing backtest overfitting*, arXiv 2209.05559(crypto 回测假阳性/过拟合)。https://arxiv.org/abs/2209.05559 〔中-高〕

**指标官方定义(高)**
- Glassnode Docs — MVRV-Z Score(公式、StdDev 归一、Awe_andWonder 2018)。https://docs.glassnode.com/further-information/metric-guides/mvrv/mvrv-z-score 〔高〕
- Glassnode Docs — NUPL(=(MCap−RCap)/MCap;STH/LTH 155 天)。https://docs.glassnode.com/guides-and-tutorials/metric-guides/unrealized-profit-loss/nupl-net-unrealized-profit-loss 〔高〕
- Glassnode Docs — SOPR / aSOPR。https://docs.glassnode.com/guides-and-tutorials/metric-guides/sopr/sopr-spent-output-profit-ratio 〔高〕
- Glassnode Docs — Reserve Risk(Price/HODL Bank;VOCD/MVOCD)。https://docs.glassnode.com/guides-and-tutorials/metric-guides/coin-days-destroyed/reserve-risk 〔高〕
- Glassnode Docs — SSR(BTC MCap / 稳定币 MCap)。https://docs.glassnode.com/guides-and-tutorials/metric-guides/stablecoin/ssr-stablecoin-supply-ratio 〔高〕
- CryptoQuant User Guide — SSR / aSOPR / 稳定币流。https://userguide.cryptoquant.com/cryptoquant-metrics/stablecoin/stablecoin-supply-ratio 〔高〕

**S2F 批判(高)**
- CoinDesk(2020-06-30)— *Why the Stock-to-Flow Bitcoin Valuation Model Is Wrong*。https://www.coindesk.com/markets/2020/06/30/why-the-stock-to-flow-bitcoin-valuation-model-is-wrong 〔高〕
- Burger/Amdax(Medium)— *Reviewing "Modelling Bitcoin's Value with Scarcity" Part II: The hunt for cointegration*(协整/spurious regression)。https://medium.com/burgercrypto-com/reviewing-modelling-bitcoins-value-with-scarcity-part-ii-the-hunt-for-cointegration-66a8dcedd7ef 〔高〕
- 综述 — *Bitcoin … PlanB's S2F … Past Failures*(2021 预测失败、"invalidated")。https://medium.com/@nicolakharvey/...-1e1f192f8ce2 〔中,二手综述〕

**数据可得性(高)**
- CoinMetrics Community Data(`api.coinmetrics.io/v4`,无需 key,CC BY-NC,10 req/6s)。https://gitbook-docs.coinmetrics.io/packages/coin-metrics-community-data 〔高〕
- CoinMetrics — CapRealUSD / CapMVRVCur 定义。https://docs.coinmetrics.io/info/metrics/CapMVRVCur ; https://github.com/coinmetrics/docs-website/blob/master/asset-metrics/market/caprealusd.md 〔高〕
- Glassnode API 仅付费 Pro;免费层 24h 网页。https://docs.glassnode.com/basic-api/api ; https://studio.glassnode.com/pricing 〔高〕

**指标解读 / 周期(中,多为二手分析)**
- Puell / Mayer / 200WMA 解读。https://www.themarketsunplugged.com/sopr-bitcoin-profit-loss-guide/ ; https://newhedge.io/bitcoin/mayer-multiple ; https://bitcoinmagazine.com/markets/bitcoin-price-200-week-moving-average 〔中〕
- 减半小样本/衰减回报。https://fractalcycles.com/guides/bitcoin-halving-cycle ; https://www.hyrotrader.com/blog/bitcoin-cycles/ 〔中〕
- 减半学术讨论(窗口依赖)。https://www.mdpi.com/1911-8074/19/1/2 ; https://www.sciencedirect.com/science/article/pii/S2666188824000285 〔中,正文未逐一核实〕

**未核实标注**
- "MVRV-Z 误差两周内命中每个顶底"类宣称(axeladlerjr / spotedcrypto / bitcoinmagazinepro):**描述为样本内叙事,无预注册样本外检验**,可信度低,**未核实其择时 alpha**。
- 交易所净流 / SSR 的**免费可程序化源**与历史回测有效性:**未核实**(免费层覆盖差、地址标注噪声)。
- ScienceDirect《Using on-chain data to predict Bitcoin cycles》正文(403):**结论未核实**,仅引标题/摘要级信息。

---

> 一句话总结:**链上估值指标是优秀的"贵/便宜"温度计,但不是择时器;它们的"历史精度"几乎全是 n=3–4 的样本内叙事。S2F 已证伪、减半叙事统计不稳健;真正有学术背书的是市场+规模+动量三因子。落地做法 = 用少数口径透明、可免费复现(CoinMetrics Community + 纯价格)的指标,对长期定投做扣成本、防前视、预注册的有界再平衡倾斜,达不到扣成本后显著改善就诚实降级为纯展示。**
