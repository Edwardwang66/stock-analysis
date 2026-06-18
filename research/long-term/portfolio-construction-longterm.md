# 长期组合构建:集中度、再平衡、换手、仓位 sizing — 深度研究报告

> 目的:为成熟量化/投研系统的**长期(持有期数月至数年)做多**方向,沉淀"持多少只、怎么加权、何时再平衡、换手/税收预算、仓位 sizing"的可证伪方法论与最新净收益证据。
> 方法:多角度并行检索(Evans-Archer/Statman 分散 / active share / 再平衡溢价(Daryanani) / Kelly / DeMiguel 1/N / 等权 vs 市值 / 税收-wash sale)→ 一手来源核验 → 合成。本系统已有组合构建模块(Garleanu-Pedersen aim、分层限额)、防过拟合(PBO/Deflated Sharpe)、成本闭环(`backtest/costs.py`:平方根冲击 + 容量地板)。
> 日期:2026-06-18。所有关键数字标注**来源 URL + 可信度(高/中/低)**;无法核实的标**"未核实"**。
> 立场(房子风格):**净·扣成本(并扣税)是唯一货币。** 再平衡溢价小且对成本极敏感;最优化权重极易过拟合;**简单规则(等权/上限/带宽)在样本外稳健**。任何"集中投资跑赢"叙事都先打幸存者偏差与归因折扣。

---

## 1) TL;DR(可证伪要点)

1. **20–30 只消掉"大部分"非系统风险,但"大部分"≠"全部",且分散收益是凹的、递减的。** Evans-Archer(1968)~10 只即接近市场波动;**Statman(1987)在含无风险资产与借贷成本后把门槛抬到 30–40 只**;近年文献(MDPI 2021 综述)指出要逼近"最大分散"常需 **50–100+ 只**,因尾部/相关性在危机时跳升。[高｜mdpi.com/1911-8074/14/11/551;Statman 1987] → **经验法则:30 只是"够用"的下限,不是"最优";因子组合(需要每个 sleeve 内横截面分散)要更宽(每腿 ≥50)。**

2. **"集中能跑赢"的最强学术证据(Active Share, Cremers-Petajisto 2009)已被作者本人的后续更新削弱。** 原文:最高 active share 基金扣费后跑赢基准、且有持续性;**但后续更长样本里高/低 active share 的收益差不再统计显著**。[中｜papers.ssrn.com/abstract_id=891719;activeshare.nd.edu] → **active share 是"是否真主动/别买贴牌指数"的过滤器,不是 alpha 预测器。** 集中本身不创造收益,集中只是放大(对或错的)信号。

3. **Buffett 式集中("分散是无知的保护")在数学上是 Kelly 的极端押注,但前提是"你真的有边际且估准了"——量化系统几乎不满足这个前提。** Buffett:懂行的人找 5–10 家便宜好公司,传统分散反而伤害结果。[中(语录,口径自报)｜berkshire 1993 letter via grahamvalue] → **量化的边际是统计性的小而宽,不是逐股深度;因此本系统应做"宽"(多腿、每腿宽),用分层限额防单股黑天鹅,而非学 Buffett 押 5 只。**

4. **再平衡溢价真实但很小(年化 ~0.3–0.5%),且大部分来自"卖涨买跌"的逆势暴露,扣成本/扣税后常被吃掉一半以上。** 5% 容差带 vs 1–2% 窄带:Daryanani 系 ~**+0.3–0.4%/年**(扣成本后),且交易次数从 8–12 次降到 3–4 次。[中(行业研究,口径自报)｜kitces.com;FPA Journal 2008 Daryanani] → **阈值带(±5% 相对)优于纯日历;"常看、少动"(频繁检查、宽带触发)是净收益最优近似。**

5. **DeMiguel-Garlappi-Uppal(RFS 2009):14 种"最优化"权重在样本外没有一个稳定打败 1/N(等权)。** 要让样本均值-方差稳定胜过 1/N,25 资产需 ~**3000 个月**估计窗、50 资产需 ~**6000 个月**——现实里拿不到。[高｜academic.oup.com/rfs/article-abstract/22/5/1915] → **过度优化权重 = 过拟合估计误差。等权是强基线;偏离等权必须用样本外(PBO/Deflated Sharpe)证明,而非样本内 Sharpe。**

6. **风险加权(逆波动/风险平价)降波动、抬 Sharpe,但不抬总收益且引入隐性杠杆/相关性假设。** 朴素逆波动给低波动资产更高权重;若各资产 Sharpe 与相关性相近则最优。单资产类(全股票)里它退化为"低波动因子暴露"。[中｜investresolve.com risk-parity whitepaper;gestaltu naive risk parity] → **在纯股票多头里,风险加权≈低波因子押注,要显式标注这是一次因子下注,不是"免费的分散"。**

7. **等权 S&P500 长期(2003–2022)年化 ~+1.0–1.5% 胜市值权,但这是 size+value+逆势 因子,且 2023 起被大盘集中行情反向吃掉 ~32%。** 扣 40bps 成本后季度再平衡的等权超额收益降到 ~**0.99%/年**(部分被成本侵蚀)。[中(行业/学术混合,口径自报)｜spglobal SPW 20-year;arxiv 1601.07626] → **等权的超额≈小盘+逆势因子敞口,不是"加权魔法";它有容量与换手代价,且会经历多年跑输(如 2023–24)。**

8. **换手的真敌人在长期账户里是税:美股长期资本利得(持有 >1 年)税率显著低于短期/普通收入;一次"卖赢"实现的税是确定的负 alpha,wash sale(±30 天买回实质相同标的)使亏损无法当期抵扣。** [高(税法定义)｜fidelity wash-sale;schwab] → **长期 sleeve 的换手预算应以"税后"计:能不实现的盈利尽量不实现;再平衡优先用新钱注入与分红再投,而非卖出已实现盈利。**

9. **Kelly 给"押多大"的理论上限,但全 Kelly 在参数估计有误时灾难性过押;分数 Kelly(半/四分之一)是估计不确定下的正确响应。** 半 Kelly 保留 ~75% 增长率、波动减半、"腰斩"概率从 1/2 降到 1/8;若真实 drift 被高估一倍,全 Kelly 可把真实增长率打到零甚至为负。[中(教学/综述,数学性质成立)｜en.wikipedia.org/wiki/Kelly_criterion;Thorp 用半 Kelly] → **本系统的仓位上限应等价于"四分之一~半 Kelly"的保守缩放,且永远在容量地板(ADV 参与率)与分层限额之内取 min。**

> **一句话:长期组合构建的净收益增量主要来自"少犯错"(够分散、不过拟合权重、控税后换手),而非"权重优化的精巧"。简单 + 纪律 > 复杂 + 最优化。**

---

## 2) 集中度 / 分散:多少只够、集中 vs 分散的证据

### 2.1 "够分散"的经典曲线(凹、递减)
- **Evans-Archer(1968)**:随机加股,组合标准差快速向市场水平收敛,~**10 只**已接近市场波动。这是"边际分散收益递减"的原始证据。[高(经典)｜mdpi 综述引]
- **Statman(1987)《How Many Stocks Make a Diversified Portfolio?》**:把**无风险资产、借贷成本**纳入后,理性投资者的"够分散"门槛升到**借入者 30 只 / 借出者 40 只**——因为再加股的分散收益必须超过其交易/持有成本。[高｜Statman 1987]
- **现代综述(MDPI, J. Risk Financial Manag. 2021)**:8–10 只的老法则被反复挑战;**逼近"最大分散效果"常需 30–50 只,甚至 100+**;关键是危机时相关性上行、尾部同向,样本期内估的相关性低估了真实尾部风险。[高｜mdpi.com/1911-8074/14/11/551]

**口径警告**:"够分散"对什么定义?(a)消掉**非系统(可分散)波动**:20–30 只就拿到大头;(b)逼近**市场组合的全部分散收益/最小化跑输市场的概率**:需要 50–100+。两者常被混为一谈。

### 2.2 集中(active share / Buffett) vs 量化做宽
- **Active Share(Cremers-Petajisto 2009)**:定义 = Σ|w_fund − w_bench|/2;高 active share(>60% 才算非"贴牌指数")原文扣费后跑赢、且持续。**但 Cremers 本人后续更长样本里,高/低 active share 收益差不再显著。** [中｜ssrn 891719;activeshare.nd.edu] → active share 是"诚实度过滤器"(别为主动费率买被动组合),不是收益预测。
- **Buffett 集中论**:"分散是对无知的保护;若你懂行,5–10 家便宜好公司胜过 50 家研究不足的"。本质是 **Kelly 在高置信边际下的大额押注**。[中(语录)｜grahamvalue;mastersinvest] → **前提是"逐股深度边际 + 估准"。量化系统的边际是统计性的(横截面小幅、可重复),不满足 Buffett 前提,故应做"宽"而非"押"。**
- **结论(本系统)**:不学 Buffett 押 5 只。做"宽"的同时用**分层限额**(单股/行业/因子腿上限)把任一只的下行限住。集中只在"信号置信度极高且容量允许"时,经分数 Kelly 缩放后小幅体现。

---

## 3) 再平衡频率与带(来源可信度)

### 3.1 日历 vs 阈值带 vs"常看-宽带"
- **Daryanani(2008, FPA Journal《Opportunistic Rebalancing》)**:在 1992–2004 多资产组合上,**"频繁检查(≈每两周/10 交易日一次)+ 相对 20% 再平衡带"** 净收益最优;**检查间隔超过 ~2 周后,再平衡收益开始递减**。核心:**"看"要勤(零成本),"动"要稀(有成本)**。[中(行业期刊,口径自报)｜FPA Journal 2008;kitces.com 复盘]
- **5% 容差带 vs 1–2% 窄带**:窄带触发 8–12 次/期、宽带 3–4 次;**宽带净收益 ~+0.3–0.4%/年**(扣成本),因为减少了无谓小额交易。[中｜kitces.com] → **过度频繁再平衡是负 alpha;阈值带优于固定日历。**

### 3.2 再平衡溢价的本质与脆弱性(诚实)
- 再平衡溢价 = **逆势(卖涨买跌)+ 多样化收益(diversification return ≈ 各资产方差差异)** 的副产品,量级通常 **年化 0.1–0.5%**,**强趋势市(如 2023–24 大盘集中)里再平衡反而拖累**(过早卖出赢家)。
- **对成本/税极敏感**:扣交易成本 + 扣实现资本利得税后,小盘/高换手版本的溢价常被吃掉过半。→ **不要把"再平衡溢价"当独立 alpha 源建模;把它当"控制漂移、维持目标暴露"的纪律副产品。**

### 3.3 与本系统 Garleanu-Pedersen aim 的关系
- GP(JF 2013)给的是**连续/动态版的"阈值带"**:最优策略 = **"瞄准目标前方(aim in front of the target)" + "向 aim 部分移动(trade partially toward the aim)"**,移动幅度由 **预期 alpha 衰减速度 / 交易成本** 决定。aim 组合是当前 Markowitz 组合与未来各期预期 Markowitz 组合的加权平均。[高｜onlinelibrary.wiley.com/10.1111/jofi.12080;nber.org/papers/w15205] → **离散的"5% 带"是 GP "部分移动"的粗近似:成本越高、信号越慢衰减 ⇒ 带越宽、移动比例越小。本系统已有 aim 模块,带宽应由成本/衰减反推,而非拍脑袋。**

---

## 4) 换手 / 税收预算

### 4.1 美股长期账户的税几何
- **持有 >1 年 = 长期资本利得**(税率显著低于短期/普通收入);**短期(≤1 年)按普通收入征**。→ 任何在 1 年内卖出赢家的再平衡都把潜在长期税率"升级"成短期,是确定的负 alpha。[高(税法)｜fidelity;schwab]
- **Wash sale(§1091)**:在卖出亏损标的的**前后各 30 天**(共 61 天窗)买入"实质相同(substantially identical)"标的,**亏损当期不可抵扣**,被计入替代标的成本基础;原持有期被"接续(tacked on)"。[高｜fidelity wash-sale;turbotax]
- **税亏收割(TLH)**:卖亏损实现损失抵当年资本利得 + 至多 $3,000 普通收入,余额结转。**用同行业 ETF/不同标的替代**可在 31 天内维持暴露而不触 wash sale。[高｜vanguard TLH;greenbush]

### 4.2 换手预算落地原则(税后净)
1. **不对称对待盈/亏**:盈利尽量不实现(延税 = 无息复利);亏损主动收割(在不触 wash sale 前提下)。
2. **新钱优先**:再平衡优先用**注资 + 分红再投**把欠配腿买够,而非卖出已实现盈利的腿——这是"税后零成本"的再平衡。
3. **换手上限以税后计**:把"换手 × (短期-长期税率差 + 成本)"作为再平衡触发的硬门槛;预估的再平衡收益必须 > 这个税后成本才动手(与 §3.2 同构)。
4. **wash sale 守门**:任何 sleeve 的卖出-买回若落在 ±30 天且标的实质相同(同股/紧密替代 ETF),系统应自动阻断或改用替代标的。

---

## 5) 仓位 sizing:Kelly / 分数 Kelly 与风险加权

### 5.1 Kelly 与分数 Kelly
- **Kelly**:最大化对数财富的长期增长率 ⇒ 押注 ∝ 边际/方差(单押 f* = edge/odds;连续版 f* = μ/σ²)。**问题:输入(μ)估不准时灾难性。**
- **分数 Kelly(半/四分之一)**:半 Kelly 保留 ~75% 增长、波动减半、腰斩概率 1/2→1/8;**过押远比欠押危险**——真实 drift 被高估一倍,全 Kelly 把真实增长打到 0。Thorp(把 Kelly 引入投资)实战用半 Kelly。[中(数学性质成立,综述/教学源)｜en.wikipedia.org/wiki/Kelly_criterion] → **量化系统 μ 估计天然有选择/拥挤/过拟合偏差 ⇒ 默认用 ¼–½ Kelly 缩放,绝不用全 Kelly。**

### 5.2 风险加权 / 风险平价 vs 等权
- **DeMiguel-Garlappi-Uppal(RFS 2009)**:14 个最优化模型样本外无一稳定胜 1/N;**估计误差吞掉最优化的理论收益**。最小方差不利用错误定价,反而常输给 1/N。[高｜academic.oup.com/rfs/.../22/5/1915] → **等权是必须打败的强基线。**
- **逆波动/风险平价**:给低波动资产更高权重;**降波动、抬 Sharpe,但不抬总收益**,且在纯股票里退化为"低波动因子下注"。需估协方差(估计误差再入场)。[中｜investresolve risk-parity;gestaltu] → **在多头股票 sleeve 内,风险加权 = 一次显式的低波因子押注,要这样标注,不当"免费午餐"。**

### 5.3 本系统的 sizing 栈(建议顺序,逐层取 min)
```
target_w_i  = sleeve 内信号权重(默认等权;偏离等权须 PBO 证明)
            × 风险缩放(可选逆波动,显式标注为低波因子押注)
kelly_w_i   = clip(target_w_i, 0, frac_kelly * mu_i / sigma_i^2)   # frac_kelly ∈ [0.25, 0.5]
cap_w_i     = capacity_cap_weights(...)   # backtest/costs.py:ADV 参与率 ≤5%
tier_w_i    = 分层限额(单股 ≤X%、行业 ≤Y%、因子腿 ≤Z%)
final_w_i   = min(target_w_i, kelly_w_i, cap_w_i, tier_w_i) 后归一(被截断不回填,诚实降规模)
```

---

## 6) 落地到本系统(组合规则 / 脚本 / 验证)

### 6.1 默认组合规则(长期做多 sleeve)
- **持股数**:每因子腿 **≥50 只**(横截面分散,呼应 §1.1/§5.2 的 1/N 强基线);总组合(多腿合并去重)目标 **60–150 只**。低于 30 只触发"集中度告警"。
- **加权**:**腿内默认等权**;若用逆波动,在报告里标注为"低波因子押注"并单独跑因子归因。**禁止样本内均值-方差最优化权重**(§1.5)。
- **再平衡**:**相对阈值带 ±20%(或绝对 ±5% NAV)+ 每 ~10 交易日检查一次**(Daryanani 最优近似,§3.1);触发后按 GP **"部分向 aim 移动"**(本系统已有 aim),移动比例由成本/信号衰减反推。
- **税后门槛**:再平衡仅当 `预估再平衡收益 > 成本 + 税(短期-长期差×实现盈利)`;盈利腿优先用新钱/分红补,不卖;wash sale ±30 天守门。
- **sizing 上限**:`final_w = min(等权/信号权, ¼–½Kelly, 容量上限, 分层限额)`,被截断不回填(诚实降规模)。

### 6.2 脚本与验证(在现有 backtest 框架内)
- **复用 `backtest/costs.py`**:`portfolio_turnover_cost(dw, ...)` 已把 Δw 换算为价差+平方根冲击成本;**再平衡决策应调用它做"动不动"的成本门槛**。新增一个 `tax_drag(dw, holding_period, st_rate, lt_rate)` 函数(本系统暂无,标"待实现")把实现资本利得税并入门槛。
- **复用 `backtest/xs_portfolio.py`**:其 `long_short_series` 已算 top-decile **换手**;扩展为"带宽再平衡 vs 月度日历再平衡"的 A/B:对比两者**扣成本+扣税后**的净年化与净 Sharpe,验证 §3 的"宽带小幅胜"。
- **防过拟合(强制)**:任何"非等权/最优化权重"或"窄带优于宽带"的结论,必须过 `backtest/study_pbo.py`(CSCV-PBO)与 Deflated Sharpe;**样本内 Sharpe 提升不算数**。这是 §1.5 的纪律实现。
- **A/B 实验清单(可直接排期)**:
  1. 持股数扫描 {20,30,50,75,100}:净 Sharpe vs 数量,确认凹曲线与"≥50"门槛。
  2. 再平衡 {月度日历, ±5%带, ±20%相对带 + 10日检查}:净·税后年化对比。
  3. 加权 {等权, 逆波动, 最小方差}:样本外(PBO)对比,验证 1/N 是否仍是赢家。
  4. sizing {全 target, ½Kelly, ¼Kelly}:净 Sharpe 与最大回撤对比。

### 6.3 看板/feed 埋点
- 在组合看板新增:**实际持股数、Herfindahl 集中度(Σw²)、各腿换手(年化)、年内已实现资本利得($/估算税)、距下次再平衡带宽触发的距离**。让"集中度/换手/税"成为一等公民指标(净货币口径)。

---

## 7) 风险与反方

1. **"再平衡溢价"可能是样本期产物**:逆势在均值回复市占优,在强趋势/集中市(2023–24 大盘 7 雄)里是负贡献。再平衡的价值是"控暴露纪律",不是稳定 alpha。**反方成立时:宽带 + 少动 仍是更稳健选择**(少犯错)。
2. **等权超额 = 因子押注,会长期跑输**:等权的小盘+逆势暴露可经历多年跑输(2023–24 等权 S&P 落后市值权 ~32%)。把等权当"中性基线"是一种隐性因子下注。[中｜spglobal]
3. **Active share / 集中"跑赢"证据脆弱**:原始结论被作者本人后续样本削弱;集中只放大信号,不创造 alpha。押集中=押"你真有边际",量化通常不具备逐股深度边际。
4. **Kelly 输入(μ)是过拟合重灾区**:横截面 alpha 的 μ 估计带选择/拥挤/前视偏差;**用它直接驱动全 Kelly 会系统性过押**。分数 Kelly 是必需,不是可选。
5. **风险加权引入协方差估计误差与隐性杠杆**:风险平价在跨资产类有意义,在纯股票多头里退化为低波因子,且需杠杆才"平"——长期 sleeve 不应隐性加杠杆。
6. **税的不确定性**:税率/规则随账户类型(应税 vs 递延)与立法变化;本报告税口径基于现行美股规则,**未来税法变动未核实**。递延账户(IRA/401k)里 wash sale / 实现税逻辑不同,需分账户建模。
7. **所有外部数字均为样本内/作者自报或行业研究**:Daryanani、SPW 超额、OSAM 式收益等都未做独立 PIT 复现;按本系统纪律,**历史毛口径默认打 3–5 折**后再用于预期。

---

## 8) 参考来源(URL + 可信度)

**分散 / 集中**
- Statman, "How Many Stocks Make a Diversified Portfolio?" (1987) — 30/40 只门槛。[高(经典)｜未直接核验原文 PDF,经多源转引]
- MDPI, J. Risk Financial Manag. 14(11):551 (2021),"How Many Stocks Are Sufficient…A Review" — 综述,8–10 vs 30–50 vs 100+。[高｜https://www.mdpi.com/1911-8074/14/11/551]
- Cremers & Petajisto (2009), "How Active Is Your Fund Manager?" SSRN 891719 — active share 定义与原始结论。[中(原文高;但结论被后续削弱)｜https://papers.ssrn.com/sol3/papers.cfm?abstract_id=891719]
- Notre Dame Active Share research portal — 后续样本里高/低 active share 收益差不显著。[中｜https://activeshare.nd.edu/academic-research/]
- Buffett 集中论(1993/分散语录)— 语录,口径自报。[中｜https://www.grahamvalue.com/blog/warren-buffett-and-diversification]

**再平衡**
- Daryanani, "Opportunistic Rebalancing" (FPA Journal 2008) — 频繁看+20%带最优。[中(行业期刊)｜https://www.financialplanningassociation.org/sites/default/files/2020-05/9%20Opportunistic%20Rebalancing%20A%20New%20Paradigm%20for%20Wealth%20Managers.pdf]
- Kitces, "Optimal Rebalancing — Time Horizons vs Tolerance Bands" — 5% 带 vs 窄带净收益。[中｜https://www.kitces.com/blog/best-opportunistic-rebalancing-frequency-time-horizons-vs-tolerance-band-thresholds/]
- Gârleanu & Pedersen, "Dynamic Trading with Predictable Returns and Transaction Costs" (JF 2013) — aim / 部分移动。[高｜https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12080;NBER w15205 https://www.nber.org/papers/w15205]

**换手 / 税**
- Fidelity, "Wash-Sale Rules" — ±30 天、实质相同、持有期接续。[高(税务实务)｜https://www.fidelity.com/learning-center/personal-finance/wash-sales-rules-tax]
- Schwab, "Primer on Wash Sales"。[高｜https://www.schwab.com/learn/story/primer-on-wash-sales]
- Vanguard, "Tax-loss harvesting explained"。[高｜https://investor.vanguard.com/investor-resources-education/taxes/offset-gains-loss-harvesting]

**仓位 sizing / 加权**
- Kelly criterion — Wikipedia(数学性质、半 Kelly、过押风险)。[中(教学;性质成立)｜https://en.wikipedia.org/wiki/Kelly_criterion]
- DeMiguel, Garlappi & Uppal, "Optimal Versus Naive Diversification" (RFS 2009) — 1/N 难被打败、估计窗需求。[高｜https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901]
- ReSolve/InvestResolve, "Risk Parity: Methods and Measures" — 逆波动/风险平价性质。[中(行业白皮书)｜https://investresolve.com/inc/uploads/pdf/risk-parity-methods-and-measures-of-success.pdf]

**等权 vs 市值**
- S&P DJI, "More Equal Than Others: 20 Years of the S&P 500 Equal Weight Index" — 长期超额、季度再平衡机制。[中(指数商,口径自报)｜https://www.spglobal.com/spdji/en/documents/research/research-more-equal-than-others-20-years-of-the-sp-500-equal-weight-index.pdf]
- arXiv 1601.07626, "Trading-profit attribution for the size factor" — 扣 40bps 后等权超额 ~0.99%/年。[中｜https://arxiv.org/pdf/1601.07626]

**本系统内部锚点(代码,非外部来源)**
- `backtest/costs.py` — 平方根冲击 + 容量地板(单笔 ≤5% ADV);再平衡成本门槛复用点。
- `backtest/xs_portfolio.py` — 月度非重叠分层组合 + top-decile 换手;带宽 vs 日历 A/B 扩展点。
- `backtest/study_pbo.py` — CSCV-PBO 防过拟合;非等权/窄带结论的强制验证关。

---

*注:本报告所有外部收益数字均为样本内 / 作者自报 / 行业研究口径,未做独立 PIT 复现;按本系统纪律默认打 3–5 折后用于预期。标"未核实"处需进一步取原文核验。净·扣成本(并扣税)是唯一货币。*
