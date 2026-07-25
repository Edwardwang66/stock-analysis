# 量化因子设计与多周期价格预测 — 深度研究报告

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

> 目的:为"设计一个能同时用于美股与加密、覆盖次日/周/月/年多周期的可回测因子"做方法论铺垫。
> 方法:5 个角度并行检索(fan-out)→ 每角度 ~20 条可证伪结论 + 一手来源 → 关键结论独立核验 → 合成。
> 日期:2026-06-06。所有关键数字均标注来源 URL 与可信度(高/中/低)。
> 立场:**先把"85-90% 正确率"这个目标用证据钉死,再讲怎么设计真正有用的因子。**

---

## 执行摘要(TL;DR)

1. **"85-90% 方向正确率"在公开价量数据上不可能来自真实预测力——这是数学事实,不是经验之谈。**
   双变量正态下,方向命中率 ≈ `0.5 + arcsin(IC)/π`。代入实盘可达的因子 IC:

   | 因子 IC | 0.02 | 0.05 | 0.10 | 0.20(极罕见) |
   |---|---|---|---|---|
   | 方向命中率 | 50.6% | 51.6% | 53.2% | 56.4% |

   要达到 **85% 命中率需要 IC≈0.89、90% 需要 IC≈0.95**(本报告独立计算核验)。而股票截面单因子真实 IC 仅 0.02–0.05,组合后 0.05–0.15 已属顶级 [HLZ; ml4trading]。多个 ML 研究在指数上的样本外方向命中率稳定在 **52% 附近**,公认上限 55–57% [MDPI 2025]。
   → 凡见 85-90%,几乎必然来自:**改标签定义(止盈不止损)/ 极短持有期 / 样本内数据窥探 / 生存者偏差**,且都不等于可盈利。

2. **真正的护城河不是"单因子准"而是"广度 + 合成 + 防过拟合纪律"。** 主动管理基本定律 `IR ≈ IC × √Breadth`:把同等微弱技能(IC≈0.05)铺到几百个标的、几百个再平衡时点上,信息比才上得来 [Grinold-Kahn]。

3. **多周期要用不同信号源**:日内/次日靠微观结构(订单流失衡 OFI 同期 R²≈65%,但可交易的滞后 R² 仅 ~9%);周/月靠动量(12-1)、短期反转、财报漂移 PEAD;年度靠价值/质量/低波。同一信号画"IC-horizon 衰减曲线"即可判断它是瞬态还是持续。

4. **加密有股票没有的独家因子**:Hyperliquid 永续的资金费率(funding)、未平仓量(OI)、清算(liquidation)、基差(basis-carry),以及链上指标(SOPR/MVRV/交易所净流、稳定币 SSR)。学术上加密只需"市场+规模+动量"三因子,股票因子不能直接搬 [Liu-Tsyvinski-Wu, JF 2022]。

5. **外部预测可作因子**:预测市场(Polymarket/Kalshi)校准良好但有 longshot 偏差;分析师"修正(revisions)"比"水平"有预测力;预言机(Pyth)的置信区间可作不确定性因子。最佳用法是 **meta-labeling**(主模型给方向,次模型用外部预测定下注大小)[López de Prado]。

6. **防过拟合是硬纪律**:Purged K-Fold + Embargo + CPCV、Deflated Sharpe(按试验次数 N 通缩)、多重检验门槛 t>3.0(而非 2.0)、记录所有回测次数。Hou-Xue-Zhang 复现 447 个异象,施加 t>3 后 **85% 不显著**。

---

## §1 量化基金的因子研究工作流

### 1.1 横截面 vs 时序(两类可分离的信号源)
- **横截面(cross-sectional)**:同一时点给所有标的排序(谁更好),做多空。**时序(time-series)**:用资产自身历史预测自身未来(择时/趋势)。二者数学上可分离、正相关但不等价。[高｜AQR/MOP 2012: ssrn 2089463]
- Moskowitz-Ooi-Pedersen(JFE 2012)在 58 个期货上:**全部 58 个**对过去 ~12 月收益呈正可预测性,**52 个在 5% 显著**;最优 = 12 月回看/1 月持有;时序动量控制横截面动量后仍有显著 alpha。[高｜docs.lhpedersen.com/TimeSeriesMomentum.pdf]
- **落地含义**:CTA 趋势择时与股票多空选股互补,不是冗余。我们的因子应同时含一个横截面排序腿和一个时序趋势腿。

### 1.2 主动管理基本定律(为什么要做宽)
- `IR ≈ IC × √Breadth`:同等 IC 下,独立下注次数翻 4 倍 → IR 翻倍。这是量化做宽截面、高频再平衡的根本理由。[高｜Grinold-Kahn, tsgperformance.com]

### 1.3 经典因子库(Factor Zoo)及一手定义
| 因子 | 定义 | 关键数字/出处 | 可信度 |
|---|---|---|---|
| Value (HML) | 高账面市值比 − 低 | Fama-French 1992/93;价值溢价小盘 ~0.60%/月、大盘 ~0.26%/月,HML 长期 Sharpe~0.64 | 高 |
| Size (SMB) | 小市值 − 大市值 | FF 1993;Sharpe~0.14 | 高 |
| Momentum (UMD/WML) | 过去 3-12 月赢家 − 输家 | Jegadeesh-Titman 1993:12 月形成/3 月持有 ~1.31%/月;Carhart 1997 制度化 | 高 |
| Quality (QMJ) | 盈利+成长+安全+派息,做多最高30%/做空最低30% | Asness-Frazzini-Pedersen;全球 24 国显著 | 高 |
| Low-Vol / BAB | 做多低beta(加杠杆)−做空高beta | Frazzini-Pedersen 2014:美股 BAB 1926-2009 Sharpe~0.75 | 高 |
| Carry | 假设价格不变的预期收益,事前可观测 | Koijen-Moskowitz-Pedersen-Vrugt 2018:全资产类别有效 | 高 |
- **Value 与 Momentum 在所有资产类别中负相关**(Asness-Moskowitz-Pedersen 2013 "Value and Momentum Everywhere"),组合二者产生强分散收益 → 量化标配"价值+动量"双引擎。[高｜jofi.12021]

### 1.4 因子评估指标
- 核心:**IC**(预测与实际收益相关)、**Rank-IC**(Spearman 秩相关,抗离群、对应分层单调性,实务优先)、**ICIR**(IC均值/IC标准差,稳定性)。[高｜grokipedia/IC]
- **分层回测(decile spread)+ 换手率/成本**是落地过滤器:高 IC 但高换手的因子扣成本后可能为负。[高｜McLean-Pontiff]
- **Realized IC 幅度小且时序波动剧烈**,其逐期标准差常与均值同量级——任何"IC 平稳 0.3+"的图都应质疑为样本内/前视。[高｜arxiv 2010.08601]

### 1.5 Alpha 衰减与因子拥挤(给预期打折)
- McLean-Pontiff(2016)对 97 个学术预测变量:组合收益**样本外低 26%、发表后低 58%**(发表本身带来 ~32% 额外衰减,源于投资者学习与套利)。**公开因子的预期 alpha 应至少打 4-6 折。**[高｜ssrn 2156623]

### 1.6 防过拟合方法(López de Prado 体系)
- **Purged K-Fold**:从训练集剔除标签时间与测试集重叠的样本;**Embargo**:测试折之后再加缓冲期。标准 K-fold 在金融数据上因标签重叠泄漏而失效。[高｜AFML]
- **CPCV(组合purged CV)**:生成数千个 train/test 组合,得到夏普的**分布**而非单点,直接度量回测过拟合概率 PBO。[高｜garp.org 白皮书]
- **Deflated Sharpe Ratio**:按(试验次数 N、偏度、峰度)向下通缩夏普显著性门槛;不报告 N 的回测无法评估过拟合。配套 **MinBTL**(最小回测长度)。[高｜Bailey-LdP 2014]
- **多重检验**:Harvey-Liu-Zhu(2016)检验 300+ 因子,新因子门槛应 **t>3.0** 而非 2.0;提供 Bonferroni/Holm/BHY(控 FDR)。[高｜HLZ, duke.edu]
- **复制危机**:Hou-Xue-Zhang 复现 447 异象,剔除微盘+市值加权后 **64% 不显著**,t>3 后 **85% 不显著**。因子是否"真"高度依赖构建口径。[高｜nber w23394]

### 1.7 因子合成
- 线性仍是基准(IC 加权/等权/横截面回归)。
- **Gu-Kelly-Xiu(2020)"Empirical Asset Pricing via ML"**:94 特征+8 宏观,树模型与神经网络最优,月度样本外 R²≈0.33-0.40%(远高于 OLS),增益来自**非线性交互**;NN 多空十分位样本外年化 Sharpe ~1.35(市值加权)/~2.45(等权)。**等权远高于市值加权 → 大量 alpha 来自小盘/难交易股,落地被成本与容量侵蚀**(深度学习 alpha"纸面强、实盘弱"的核心原因)。[高｜dachxiu ML.pdf]

---

## §2 多周期各自有效的信号

### 2.1 日内/次日:市场微观结构
- **订单流失衡 OFI**(Cont-Kukanov-Stoikov):10 秒区间回归,OFI 解释中间价同期变动 **R²≈65%**;价格冲击与 OFI 线性、斜率与市场深度成反比。[高｜arxiv 1011.6402]
- **但"可交易"的部分远小**:滞后(真正可预测)项平均只解释收益变动 **~8.7%**、订单流 ~4.6%;用日级订单失衡预测**次日**收益只在少数股票上显著。这是"同期 R² 高、可预测 R² 低"的关键反证点。[高｜arxiv 2508.06788]
- **OBI(订单簿失衡)** 对秒级-数十秒方向强预测,但**数分钟内快速衰减**。[高｜arxiv 2112.13213]
- **VPIN**(Easley-LdP-O'Hara):订单流毒性 → 预示**波动率上升**(非方向),2010 闪崩前显著走高。[高｜ssrn 1695041]
- **隔夜 vs 日内**(Lou-Polk-Skouras, JFE 2019):同一策略利润往往**要么全在隔夜、要么全在日内**,两分量符号相反且持续多年。[高｜lse tugofwar]

### 2.2 周/月:横截面
- **1 周反转**(Lehmann 1990):~1.7%/周。**1 月反转**(Jegadeesh 1990):~2-2.5%/月 → 这是 12-1 动量要"跳过最近 1 月"的原因。[高]
- **12-1 横截面动量**:~0.9-1.3%/月。[高｜JT 1993]
- **PEAD(财报后漂移)**:按 SUE 分组零投资组合 ~8-9%/季;好/坏消息股 60 日内 ±2% 漂移;机制是季度盈余自相关而投资者反应不足。[高｜PEAD wiki]
- **52 周高点**(George-Hwang 2004):股价对 52 周高点的"接近度"预测力**优于并主导**过去收益,且利润长期**不反转**。[高｜bauer.uh.edu]
- **分析师修正 + 盈余惊喜**叠加:3 月累计漂移可达 ~4.5%。[中]

### 2.3 年度:长周期因子
- 价值/质量/低波在年度更稳定但 alpha 更薄、伴随长期跑输痛苦期(价值需 15 年+持有)。MSCI World Quality Sharpe~0.47 vs 母指数 0.31。低波 alpha 部分被 E/P、D/P 解释掉(是价值的伪装)。Fama-French 因子风险溢价**时间不稳定**。[中-高]

### 2.4 信噪比的周期规律
- 横截面因子有效 IC 多在 0.05-0.15,多因子混合 ~0.12(最高 ~0.18)。**短周期 IC 低/衰减快但 breadth 极大;长周期 IC 稳定但下注稀少**。同一信号画 IC-horizon 衰减曲线即可判别瞬态(反转/流动性)vs 持续(漂移/因子)。[中｜ml4trading]

---

## §3 加密专属数据与因子(Hyperliquid + 链上)

### 3.1 Hyperliquid 永续 API(可直接抓的硬字段)
- **`metaAndAssetCtxs`**(逐资产快照):`funding`、`openInterest`、`oraclePx`、`markPx`、`midPx`、`premium`、`prevDayPx`、`dayNtlVlm`、`impactPxs`。构建 OI/funding/basis 因子的核心。[高｜官方 perpetuals 文档]
- **`fundingHistory`**:`coin / fundingRate / premium / time`(premium 与 fundingRate 是独立字段,premium 可单独作因子)。[高]
- **`l2Book`**:每侧 ≤20 档,字段 `px/sz/n`(n=该价位订单数,可算平均单笔大小)。[高]
- **`candleSnapshot`**:`t/T/o/h/l/c/v/n`,**仅保留最近 5000 根** → 分钟级长回测须用 WebSocket 增量自存。[高]
- **`predictedFundings`、`allMids`**;实时因子流走 WebSocket `activeAssetCtx`,Info 端点 `POST https://api.hyperliquid.xyz/info`。[高]

### 3.2 资金费率机制(建模必须对齐的细节)
- 公式 `F = 溢价指数 P + clamp(利率 − P, −0.0005, +0.0005)`,利率固定 0.01%/8h(~11.6% APR)。[高]
- **按小时结算**(取 8h 费率 1/8),用 **oraclePx** 折名义,**impact price**(对预设名义撮合 live 订单簿)算溢价 → 与 Binance/Bybit 不同,**跨所拼接 funding 前必须归一**;薄盘小币 funding 噪声更大,横截面比较要按流动性分层。[高]

### 3.3 永续/链上因子
- **funding-carry**:做空高正 funding 永续 + 持现货,收 funding。学术样本 2020-25 年化 Sharpe 一度 6.45,**但 2024 降至 4.06、2025 转负 → 强衰减,不可外推**。[中｜BIS wp1087]
- **funding 极值 + OI 同高 = 多头拥挤**,常先于尖锐反转(风险/反转指标,非精确择时;单看 funding 阈值不可靠,需叠加 OI 变化与清算)。[中]
- **清算级联**:高杠杆强平 → 市价单 → 进一步挤压 → 更多强平;Coinglass 清算热力图估算大额强平价格带。清算量 z-score 尖峰 + 单边比例极端 → 短期均值回归信号。[中]
- **链上(Glassnode)**:SOPR(>1 获利了结、<1 亏损抛售)、MVRV(>3.5 顶部区,Z-Score 定周期)、**交易所净流入/流出**(持续流出=吸筹)、**SSR 稳定币供应比**(场外干火药)、巨鲸分层(1k-10k BTC=whale)。STH/LTH 分界 155 天。[中-高]

### 3.4 加密因子的学术结论(硬锚点)
- **Liu-Tsyvinski-Wu(JF 2022)**:加密三因子 = **市场 + 规模 + 动量**,可解释横截面;10 个从股市移植的特征构成的多空策略全被该三因子吸收;**股票模型(FF3/Carhart4/FF5)无法解释加密**。[高｜jofi.13119]
- 加密**动量更强且窗口更短**:时间序列动量在 **1-4 周** horizon 最显著(股票 3-12 月);横截面动量随币种市值上升而衰减。加密动量利润**未随时间衰减**(与股票不同),但等权动量组合有严重 crash 尾部。size 因子多空收益在加密里**显著为负**(方向与股票相反,需谨慎)。[高/中]

---

## §4 HIP-3 与"外部预测"作为因子

### 4.1 Hyperliquid HIP-3(Builder-Deployed Perpetuals)
- **2025-10-13 主网上线**,第三方可在 HyperCore 部署独立永续 DEX,无需逐一审批。[高｜官方 HIP-3 文档]
- 主网部署需**质押 500,000 HYPE**,最短 **183 天**锁定;门槛预期随成熟下降。[高(HYPE 数量/锁定期);美元估值随币价浮动=中]
- 标的不按资产类别硬限,仅要求"明确定义、难操纵的底层/喂价" → **股票/外汇/商品永续在协议层允许**,但 oracle/合规风险由部署者承担。[高]
- 实际已上线以**美股 + 商品永续**为主:trade.xyz 等上了 Tesla/Apple/Nvidia/Amazon/MSFT/Meta 24/7 永续 + 合成 Nasdaq 指数(`XYZ100`),以及黄金/白银/原油;2026-03 报道 S&P 500 合约获授权。[中｜媒体/交易所,非一手,名单随时间变]
- **数据可程序化抓取**:HIP-3 perp 用 dex 名前缀(如 `xyz:XYZ100`),info 端点支持 `perpDexs`,WS 订阅可带 `dex` 参数 → 拿 mark/funding/OI/fills。[高]
- ⚠️ **风险**:部署者掌握 mark price/oracle 设定权;validator 可对恶意运营 slash(最高 100%);这些是**合成永续**,价格 = 部署者 oracle,可能偏离真实标的 → 既是对手方/喂价风险,**也可能是"HIP-3 mark vs 真实标的"的偏离因子**。[中-高]

### 4.2 预测市场作为方向因子
- **校准良好**:Polymarket 定价 ~30% 的事件大样本下约 30% 发生;Kalshi 越临近到期越准。可把合约价直接读作隐含概率。[中-高｜Kalshi 学术研究 karlwhelan.com]
- **系统性 favorite-longshot 偏差**:低概率合约被高估、扣费后亏损 → 极端概率端要**去偏校准**,不可线性直接用。[高]
- 理论(Wolfers-Zitzewitz, NBER w12083):均衡价 = 交易者信念的预算加权平均,通常优于中等复杂度基准。[高]
- 最后 72 小时市场优于会过时的民调,但对突发新闻有**短期过度反应** → 可证伪策略:新闻冲击后做"概率均值回归"短期因子。[中]
- 转方向因子核心:`edge = 自有概率估计 − 市场隐含概率`;**按市场深度加权**(薄市场准确率可低至 ~61%)。[中]

### 4.3 分析师一致预期 / 目标价修正
- **"修正(revisions)"而非"水平(levels)"才有预测力**(水平已被价格吸收);1994-2023 稳健,市场对修正 underreaction。[高｜Mill Street + Fed wp]
- **修正一致性**:同一报告中盈利预测/推荐/目标价修正方向一致时,信号更可靠 → 用三者一致性作元过滤。[高｜Stanford GSB]

### 4.4 链上预言机喂价
- **Pyth**:除 price 外提供 **confidence interval(conf)**、exponent、publish time → σ/μ 可作"不确定性/拥挤"因子,超阈值降权/暂停。[高｜Pyth 官方]
- **Chainlink**:push 模型(deviation threshold + heartbeat),多节点中位数;偏离阈值未触发时的"陈旧度"是可交易信号。[中-高]
- **Oracle vs DEX/CEX 价偏离**:DEX 常滞后 CEX 数秒-数分钟,可作均值回归因子。[中]

### 4.5 把外部预测纳入因子的方法论
- 两种用法:(i) 作为**特征**直接进主模型;(ii) 作为 **meta-label**——主模型给方向,次模型(用预测市场概率/分析师修正/oracle 不确定性)估计该方向可靠性并定下注大小(López de Prado:event sampling + triple-barrier + meta-labeling 提升表现)。[高]
- **头号风险 = 信息泄漏与时效性**:必须用 **point-in-time** 数据(带 as-of 时间戳,避免"修订后回填");时序 CV 必须 purged/embargoed。**同一因子在 PIT 对齐前后 IC 若大幅缩水 = 原结果含泄漏。**[高]

---

## §5 真实表现预期与过拟合(把"85-90%"钉死)

### 5.1 IC 量级 → 命中率(数学反证,本报告独立核验)
- 命中率 ≈ `0.5 + arcsin(IC)/π`。IC=0.05→51.6%、0.10→53.2%、0.20→56.4%。**85% 需 IC≈0.89、90% 需 IC≈0.95**,真实因子 IC 只有 0.02-0.10 → 不可能。[高｜数学推导 + arxiv 2010.08601]
- 多个 ML 研究指数样本外方向命中率稳定 **~52%**(S&P500~52.5%、DJI~50.1%、IXIC~51.2%);公认上限 **55-57%**。[高｜MDPI 2025]

### 5.2 夏普量级 & "高胜率"陷阱
- 单策略成本后 Sharpe<1 常被淘汰;优秀单策略 1-2;组合后 1.5-2.5 已顶级。S&P500 滚动 Sharpe 仅 ~0.5。[高]
- **"高胜率"广告多靠止盈不止损**:把规律小亏转成稀有巨亏,胜率高但期望≤0。7 连亏概率仅 0.78%,但 500 次机会中预期发生 ~4 次 → 无止损的高胜率账户在足够样本下必被尾部清零。**看期望(expectancy),不看胜率。**[高]

### 5.3 过拟合的量化证据
- Bailey-Borwein-LdP-Zhu(Notices of AMS 2014):仅 5 年数据、尝试 **~45 个配置**就几乎保证出现一个样本内高、样本外差的"过拟合赢家";在记忆效应下样本外**期望收益为负**(不是回到零)。[高]
- Deflated Sharpe / MinBTL:期望最大样本内夏普随试验数 N 增长;若只有 2 年数据,可安全尝试的 N 很小。[高/中]
- HLZ t>3.0;HXZ 复现 447 异象,t>3 后 **85% 不显著**。[高]

### 5.4 容量、成本、有效性约束
- 已发表因子夏普逐年衰减 ~5pct;公开即被套利抹平。策略容量由毛夏普×流动性×衰减速度决定,**交易成本随规模超线性增长**;信号越快容量越低(IR-容量权衡)。市场冲击分临时/永久两类,高频纸面 alpha 扣冲击后被显著侵蚀。[高/中]

### 5.5 直接结论
> 在公开数据上看到 85-90% 命中率,成因只有四类且都不等于可盈利:**(a) 改标签定义(止盈不止损的路径标签);(b) 极短持有期 + 大样本均值回归(命中方向但单笔<成本);(c) 样本内数据窥探/前视;(d) 生存者偏差。** 这与"真实 IC 0.02-0.05⇒命中率 51-53%""已发表因子 64-85% 不可复现""信号公开即衰减"三条独立证据全面冲突。[高]

---

## §6 对"我们要设计的因子"的可操作结论

把上面证据翻译成设计决策(下一步实现的蓝图):

1. **目标量换成现实的**:不追命中率,追 **Rank-IC(目标 0.03-0.08)、分层单调性、扣成本后 Deflated Sharpe、最大回撤**。命中率 53-57% + 正期望就是好因子。
2. **多周期 = 多信号源,分开建模再合成**:
   - 次日:微观结构(OFI/OBI、隔夜跳空)——加密用 `l2Book` 的 px/sz/n,美股用 1m bar 的成交/跳空近似。
   - 周/月:12-1 横截面动量(跳过最近 1 月)+ 1 月短期反转 + 52 周高点接近度 + PEAD(美股)。
   - 年度:价值/质量/低波(美股);加密用市场+规模+动量三因子。
3. **双资产分别建因子,不要硬迁移**:股票 factor zoo 不适用加密;加密用 Liu-Tsyvinski-Wu 三因子 + funding/OI/basis/清算/链上独家因子。
4. **加密独家腿(护城河)**:`funding` carry(注意 2025 已衰减→滚动验证)、`OI` 变化 + funding 极值的拥挤反转、清算 z-score 反转、交易所净流/SSR 资金面。字段直接来自 Hyperliquid `metaAndAssetCtxs`/`fundingHistory`。
5. **外部预测做 meta-label,不做主信号**:预测市场概率(去 longshot 偏差、按深度加权)、分析师修正一致性、Pyth conf 不确定性 → 用于**决定下注大小**而非方向。
6. **跨市场新玩法(谨慎)**:HIP-3 合成美股永续(`xyz:XYZ100` 等)提供"24/7 美股 + 加密资金费"的混合标的,可做"HIP-3 mark vs 真实标的偏离"因子;但对手方/喂价风险高,先做研究不投实盘。
7. **评估协议(不可省)**:Point-in-time 数据对齐 → Purged K-Fold + Embargo / CPCV → 记录所有试验次数 N → Deflated Sharpe → 新因子门槛 t>3.0 → 公开因子预期 alpha 打 4-6 折 → 必含交易成本/冲击模型。

---

## 引用清单(按主题,均为一手或权威来源)

**因子工作流 / 防过拟合**
- Harvey, Liu & Zhu (2016) "…and the Cross-Section of Expected Returns", RFS 29(1) — https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF
- Bailey & López de Prado (2014) "The Deflated Sharpe Ratio", JPM — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, LdP, Zhu (2014) "Pseudo-Mathematics and Financial Charlatanism", Notices AMS — https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf
- Hou, Xue & Zhang (2020) "Replicating Anomalies", RFS — https://www.nber.org/system/files/working_papers/w23394/w23394.pdf
- McLean & Pontiff (2016) "Does Academic Research Destroy Stock Return Predictability?" — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623
- Gu, Kelly & Xiu (2020) "Empirical Asset Pricing via Machine Learning" — https://dachxiu.chicagobooth.edu/download/ML.pdf

**因子库(原始论文)**
- Fama-French (1993) 五/三因子 — https://tevgeniou.github.io/EquityRiskFactors/bibliography/FiveFactor.pdf
- Jegadeesh-Titman (1993) Momentum — https://www.bauer.uh.edu/rsusmel/phd/jegadeesh-titman93.pdf
- Frazzini-Pedersen (2014) Betting Against Beta — https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf
- Asness-Frazzini-Pedersen Quality Minus Junk — http://www.econ.yale.edu/~shiller/behfin/2013_04-10/asness-frazzini-pedersen.pdf
- Asness-Moskowitz-Pedersen (2013) "Value and Momentum Everywhere", JF — https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12021
- Moskowitz-Ooi-Pedersen (2012) "Time Series Momentum" — http://docs.lhpedersen.com/TimeSeriesMomentum.pdf

**多周期 / 微观结构**
- Cont-Kukanov-Stoikov "The Price Impact of Order Book Events" — https://arxiv.org/pdf/1011.6402
- Easley-López de Prado-O'Hara "Flow Toxicity / VPIN" — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1695041
- Lou-Polk-Skouras (2019) "A Tug of War: Overnight vs Intraday" — https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
- George-Hwang (2004) "The 52-Week High and Momentum" — https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf
- Post-Earnings-Announcement Drift(综述)— https://en.wikipedia.org/wiki/Post%E2%80%93earnings-announcement_drift

**加密 / Hyperliquid / 链上**
- Hyperliquid 官方 Info 端点 — https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid 官方 Funding 机制 — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding
- Hyperliquid 官方 HIP-3 — https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals
- Liu-Tsyvinski-Wu (2022) "Common Risk Factors in Cryptocurrency", JF — https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13119 (NBER: https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- Glassnode SOPR/MVRV/STH-LTH — https://research.glassnode.com/sth-lth-sopr-mvrv/
- BIS WP 1087 "Crypto carry" — https://www.bis.org/publ/work1087.pdf

**外部预测 / 预言机**
- Wolfers-Zitzewitz "Prediction Markets in Theory and Practice", NBER w12083 — https://www.nber.org/papers/w12083
- Kalshi 校准/longshot 偏差研究 — https://www.karlwhelan.com/Papers/Kalshi.pdf
- Pyth Best Practices(confidence interval)— https://docs.pyth.network/price-feeds/core/best-practices
- 分析师修正预测力 — https://www.millstreetresearch.com/do-analyst-estimate-revisions-still-help-forecast-relative-stock-returns/
- López de Prado meta-labeling / purged CV — https://en.wikipedia.org/wiki/Purged_cross-validation

**真实表现 / 过拟合反证**
- ML 指数命中率 ~52%(综述)— https://www.mdpi.com/2673-2688/6/10/268
- IC 量级 — https://arxiv.org/pdf/2010.08601
- 高胜率为何亏钱 — https://www.optionstrading.org/blog/why-high-win-rates-still-lose-money/

---

## 可信度与局限说明
- **最硬的结论**(高可信、多源/一手交叉):IC→命中率映射(本报告独立计算)、~52% 指数命中率上限、HLZ t>3.0、HXZ 复现率、McLean-Pontiff 26%/58% 衰减、12-1 动量 ~1%/月、TSMOM 58/58、Hyperliquid API 字段与 funding 机制、Liu-Tsyvinski-Wu 三因子。
- **需谨慎**(中可信、二手/预印本/时变):GOFI R²>85%、crypto carry Sharpe 6.45、HIP-3 已上线标的清单与美元估值、预测市场各类准确率统计、低波/质量 Sharpe。
- **几篇 Bailey/LdP 原始 PDF 为扫描件**,MinBTL 精确系数与期望最大夏普闭式公式未能逐字提取,方向与量级确定;如需论文级精确公式请核对 SSRN 原文。
- 本报告是**方法论与数据源铺垫**,不含本仓库的实证回测;下一步据 §6 蓝图实现可回测因子。
