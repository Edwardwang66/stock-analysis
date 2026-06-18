# 行为/情绪指标与中长期反转(逆向)— 长期投资调研

> 主题:长期反转(De Bondt-Thaler)、情绪周期与极值逆向、分析师修正/分歧、PEAD、Baker-Wurgler 情绪指数。
> 视角:成熟中频 stat-arb + PIT 治理 + 防过拟合(Deflated Sharpe、t>3)系统的**长期配置 / 风险温度计**层。
> 货币单位:**净·扣成本的几何收益 / Sharpe / 信息比**。所有结论标 [可信度] 与一手 URL,优先 2023–2026。
> 调研日期:2026-06-18。声明:本文为文献综述与落地设计,非投资建议。未亲自跑回测的数字一律标 **[未核实]**。

---

## 1. TL;DR

1. **情绪极值最适合做"温和逆向倾斜 / 风险温度计",不适合做交易触发。** 几乎所有情绪极值信号(AAII bull-bear spread、Put/Call、VIX、CNN Fear&Greed)有同一个病:**择时差、样本少(极值是稀有事件,独立观测可能就几十个)、信号宽(指向"几个月内更可能反弹"而非"哪天买")**。它们刻画"赔率温度",不是"开关"。这是本文最重要的诚实结论。[高,综合多源]

2. **长期反转(De Bondt-Thaler,3-5 年输家跑赢)真实存在但在美股近 20 年明显衰减。** 原始 1985 年结果稳健且有国际证据;但用 2000–2021 数据复制(Fortune 500),赢家和输家组合 36 个月远期收益都很强,**两者差(反转 alpha)却很小** → 美股过度反应效应近年走弱。长期反转还高度受**税收/微小盘/流动性**污染(George-Hwang)。[中-高]
   - 一手:[De Bondt & Thaler 1985 复制(2000 后数据), ResearchGate 2024/2025](https://www.researchgate.net/publication/393123188_Does_the_Stock_Market_Still_Overreact_A_Replication_of_De_Bondt_and_Thaler_1985_Using_Post-2000_Data);[George & Hwang, "Long-Term Return Reversals: Overreaction or Taxes?"](https://www.bauer.uh.edu/tgeorge/papers/gh5-paper.pdf)

3. **分析师"修正(revisions)"比"水平(levels)"更有预测力,且方向有惯性——这是情绪族里最可落地、最稳健的一支。** Mill Street:修正广度(上调/下调分析师比例)top vs bottom decile 年化约 **15.6% vs 8.0%(差 7.6pp,p<0.003)**[未核实,厂商回测、未扣成本];修正方向 1 个月后约 **83% 仍同向**(对比股价收益仅 ~50%)。机制:投资者对修正**反应不足**(underreaction),与情绪极值的"过度反应/反转"逻辑相反但互补。[中-高]
   - 一手:[Mill Street Research, "Do Analyst Estimate Revisions (Still) Help Forecast Relative Stock Returns?"](https://www.millstreetresearch.com/do-analyst-estimate-revisions-still-help-forecast-relative-stock-returns/)

4. **PEAD(财报后漂移,1-3 月中期)仍可盈利但在美国大盘衰减。** Garfinkel-Hribar-Hsiao(2024):top–bottom SUE 十分位对冲组合 3 个月风险调整收益约 **5.1%(年化 >20%)**[未核实,毛回报、含小盘];但多项研究(Martineau 2022 等)记录美国大盘 PEAD 走弱,而文本化盈余惊喜(Meursault et al. 2023)显示 2008–2019 仍强。**PEAD 是 underreaction 系,不是逆向系。**[中-高]
   - 一手:[Quantpedia "Post-Earnings Announcement Effect"](https://quantpedia.com/strategies/post-earnings-announcement-effect);[PEAD review, ScienceDirect 2020](https://www.sciencedirect.com/science/article/pii/S2214635020303750)

5. **Baker-Wurgler 情绪指数:横截面方向稳健,择时方向弱且不对称。** 情绪低时,**小/年轻/高波/不盈利/不分红/极端成长/困境股**随后收益相对高(横截面效应稳健);但作为**总量(market)择时**主要在"高情绪期"才有逆向预测力,**低情绪期预测力弱**——这是著名的不对称性。BW 指数月频、滞后大,只能做慢倾斜。[中-高]
   - 一手:[Baker & Wurgler, JF 2006, 作者站 PDF](https://pages.stern.nyu.edu/~jwurgler/papers/wurgler_baker_cross_section.pdf)

6. **本系统落地:三条独立"行为信号"分层用。**(a)**逆向温度计**=情绪极值(AAII+Put/Call+VIX+F&G)→ 慢速、有界、对称地调风险预算(±,非 all-in/out);(b)**横截面倾斜**=分析师修正广度(underreaction,中期 1-3 月,可作正式因子);(c)**长期反转**=只作 deep-value 的辅助、且必须剔小盘/税效应后才信。每条都过 Deflated Sharpe / 样本外 / 交易成本三关,否则降级为 feed-only 不入仓。[本系统设计,见 §6]

---

## 2. 长期反转与情绪指标:定义

### 2.1 长期反转(Long-Term Reversal, LTR)

直觉:De Bondt-Thaler(1985)——按过去 **3-5 年**累计收益排序,极端"输家"组合在随后 **3-5 年**跑赢极端"赢家"组合。解释为**过度反应**(investors overreact to news,价格偏离基本面后回归)。

```
形成期 J = 36~60 个月,跳过最近 1 个月(避开短期反转/微观结构)
排序:按 [t-60, t-13] 累计收益分十分位
持有期 K = 36~60 个月
LTR 多空 = 输家十分位 − 赢家十分位
```

与动量的关系(关键):
- **短期(1 个月):反转**(流动性/做市/买卖价差驱动)。
- **中期(3-12 个月):动量**(Jegadeesh-Titman;PEAD、分析师 underreaction 是其燃料)。
- **长期(3-5 年):反转**(过度反应回归)。
- 三段并存且方向交替 → 任何"反转因子"必须明确**形成期/持有期/跳空**,否则把动量当反转用会反向亏钱。[高]

污染源(诚实):
- **税损卖出 / 1 月效应**:George-Hwang 主张很大一部分"长期反转"实为税收驱动的价格压低与回弹,而非纯过度反应。[中-高]
- **微小盘 / 流动性**:输家组合系统性偏小盘、低价、低流动 → 毛 alpha 大、净 alpha 经买卖价差与冲击后大幅缩水。[高]
- **与 value 共线**:长期输家往往已变"便宜" → LTR 很大程度是 value 的换皮,持有已分散的 value 后增量有限。[中]

### 2.2 情绪极值指标(Sentiment Extremes — 逆向温度计候选)

| 指标 | 定义 | 逆向解读 | 频率 | 极值阈值(经验) |
|---|---|---|---|---|
| **AAII Bull-Bear Spread** | AAII 散户周度调查,看多% − 看空%,预期未来 6 个月 | spread 极高=过度乐观(看空);极低=过度恐惧(看多) | 周(1987 至今) | > +20~+30 偏空;< −20 偏多 |
| **CBOE Put/Call Ratio** | 看跌期权量 / 看涨期权量(equity 或 total) | 极高=恐慌/对冲过度→反弹;极低=自满 | 日 | equity PCR > 1.2~1.5 偏多 |
| **VIX** | S&P500 30 天隐含波动率 | 极高=恐慌капитуляция→未来收益偏高;极低=自满 | 日(1990 至今) | spike(>30~40)历史上接近更好买点 |
| **Investors Intelligence** | 投顾通讯多空比(机构/顾问视角) | 同 AAII,逆向 | 周(付费) | bull-bear 极端 |
| **CNN Fear & Greed** | 7 因子合成 0–100 | <25 极度恐惧(逆向看多);>75 极度贪婪(看空) | 日 | <20 / >80 |

CNN F&G 七因子(等权):市场动量(S&P vs 125 日均线)、股价强度、股价广度(McClellan)、Put/Call、市场波动(VIX)、垃圾债需求、避险需求(20 日股债收益差)。**注意:F&G 本身就含 VIX+Put/Call+动量 → 与其它情绪指标高度重叠,不是独立第 5 个信号。**[高]

### 2.3 Baker-Wurgler 情绪指数(BW)

合成"难套利、难估值"股票的情绪代理,横截面工具。6 个代理(JF 2006 版):封闭式基金折价、NYSE 换手率、IPO 数量、IPO 首日收益、新发行中权益占比、股利溢价。先对各代理剔除宏观周期成分,再取主成分。[高]

---

## 3. 预测力证据与噪声(按可信度)

### 3.1 长期反转

- **[中-高] 原始 + 国际证据真实**:De Bondt-Thaler 1985/1987 稳健;多国市场再检验多数支持长期过度反应。
  - 一手:[De Bondt & Thaler 1987, JF](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1987.tb04569.x);[国际证据综述, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0378426698001332)
- **[中-高] 美股近 20 年衰减**:2000–2021 复制中赢家/输家 36 月远期收益都强,**反转价差很小**。叠加交易成本与小盘剔除,净 alpha 可能不显著。
  - 一手:[Post-2000 复制](https://www.researchgate.net/publication/393123188_Does_the_Stock_Market_Still_Overreact_A_Replication_of_De_Bondt_and_Thaler_1985_Using_Post-2000_Data)
- **[中-高] 税/微观结构混淆**:George-Hwang 重估,反转很大程度可被税损卖出解释。
  - 一手:[George & Hwang PDF](https://www.bauer.uh.edu/tgeorge/papers/gh5-paper.pdf)
- **噪声/陷阱**:形成期/持有期重叠 → 独立观测少;前视偏差风险(用 restated 财报或未来成分股);survivorship(退市输家被剔除会高估反转)。**做法见 §6。**

### 3.2 AAII Bull-Bear Spread

- **[中] 极值有逆向倾向,但 timing 差、近期失效**:历史上 spread > +30pp 后 6/12 个月收益低于长期均值;但 **2023–2024 大盘集中行情中,spread 长期停在 +20~+40 却没有出现历史预期的随后跑输** → 信号"早 + 钝"。
  - 一手:[AAII Bull/Bear Spread 术语页](https://www.aaii.com/terms/a/373957-aaii-bullbear-spread);[AAII 散户情绪 38 年回顾 (Medium/FearGreedChart, 2026)](https://feargreedchart.medium.com/the-aaii-sentiment-survey-ce3c9cc38aad)
- **[中-高] 方法学批评(核心噪声)**:周度仅约 **200–300 名会员**响应,自选样本、非随机抽样、无成交额加权 → 单周读数统计噪声大;须用多周平滑(如 4/8 周均值或 z-score)才有意义。
  - 一手:[Edge and Odds, "Investor Sentiment Surveys: Don't Be Too Sentimental"](https://www.edgeandodds.com/investor-sentiment-surveys-dont-be-too-sentimental/)
- **诚实做法**:用"without hindsight"评估——只用截至当时已知数据生成信号再算前向收益。AAII 自己的"无后见之明"分析强调:简单看历史图很有诱惑性,真实可交易的边际很弱。[中,AAII Journal,正文 403 未取全文,标 **部分未核实**]
  - 参考:[AAII Journal "Analyzing the AAII Sentiment Survey Without Hindsight"](https://www.aaii.com/journal/article/analyzing-the-aaii-sentiment-survey-without-hindsight)(访问受限)

### 3.3 Put/Call 与 VIX 极值

- **[中] 极端恐惧后有"上偏的非对称赔率",非精确 timing**:Put/Call equity > 1.2–1.5 或 VIX spike 后 30–60 日 S&P 平均收益高于常态;PCR+VIX **同时**走极端时信号最强。但"识别极端"≠"精确入场",横盘市里几乎无用。
  - 一手:[Britannica Money, Put-Call Ratio vs VIX](https://www.britannica.com/money/put-call-ratio);[Put-Call vs VIX 比较研究, ResearchGate](https://www.researchgate.net/publication/284698793_Measures_Of_Investor_Sentiment_A_Comparative_Analysis_Put-Call_Ratio_Vs_Volatility_Index)
- **噪声**:Put/Call 受指数对冲/做市结构影响(equity-only vs total 信号会冲突);VIX 极低("自满")作为看空信号比 VIX 极高作为看多信号**弱得多**(不对称,同 BW)。[中]

### 3.4 CNN Fear & Greed

- **[低-中] 教学/沟通好,统计独立性差**:7 因子合成、阈值化清晰、免费实时;但成分与 Put/Call、VIX、动量重叠,**不提供超出已有信号的独立信息**;无长公开回测、方法学不完全透明。当"仪表盘 / feed 展示"用,不当独立因子。
  - 一手:[CNN Fear & Greed 官方页](https://www.cnn.com/markets/fear-and-greed);[Supertype 方法学拆解](https://supertype.ai/notes/fear-greed-index-part1)

### 3.5 Baker-Wurgler

- **[中-高] 横截面方向稳健 + 总量不对称**:情绪低→投机性子集随后收益高(横截面);总量逆向预测主要在高情绪期有效,低情绪期弱。月频、滞后,只能慢用。近年有"增强版 BW"(让各成分权重时变)提升预测力。
  - 一手:[Baker & Wurgler JF 2006 PDF](https://pages.stern.nyu.edu/~jwurgler/papers/wurgler_baker_cross_section.pdf);[An Enhanced Investor Sentiment Index (Taylor & Francis 2023)](https://www.tandfonline.com/doi/full/10.1080/1351847X.2023.2247440)

---

## 4. 分析师预期修正与分歧(本族最可落地)

### 4.1 修正(Revisions)> 水平(Levels)

- **核心结论 [中-高]**:重要的是 EPS 预期的**变化方向/广度**,不是绝对预测水平。即便分析师系统性乐观,**方向修正仍含预测力**,因投资者对修正**反应不足**,价格逐步消化。
- **量化(Mill Street,2003–至今)[未核实,厂商回测、毛收益]**:按修正广度,top decile **15.6%** vs bottom **8.0%** 年化(差 **7.6pp**,p<0.003)。
- **广度 > 幅度**:上调/下调分析师**比例(breadth,~100 日)**比共识 EPS **百分比变化(magnitude,~1 月)**更持久更可预测。
- **惯性**:修正方向 1 个月后约 **83%** 仍同向(股价收益仅 ~50%)→ 修正信号比价格动量更"黏",换手可更低。
- **协同**:修正 + 价格动量 + 估值三因子合用增强(Mill Street 的 MAER)。这与本系统已有 value/momentum 层天然耦合。
- **宏观层证据 [中]**:Fed(2024)记录 1994–2023 修正与市场收益强正相关;聚合修正在预测财报后收益上甚至**大于**盈余惊喜本身的系数。
  - 一手:[Mill Street](https://www.millstreetresearch.com/do-analyst-estimate-revisions-still-help-forecast-relative-stock-returns/);[Fed FEDS 2024-049 PDF](https://www.federalreserve.gov/econres/feds/files/2024049pap.pdf)

### 4.2 分歧(Dispersion)与过度乐观

- **分析师分歧高 → 随后收益低(Diether-Malloy-Scherbina 2002 的经典"分歧异象")**:高分歧股在意见分歧+卖空受限下被乐观者定价过高,随后跑输。**这是逆向/情绪味的横截面信号**:把高分歧当"乐观过头"的红旗。[中,经典文献;近年稳健性有争议,标注谨慎]
- **系统性过度乐观**:卖方分析师长期偏乐观(承销/通道激励),**水平有偏 → 必须用修正而非水平**,这正是 §4.1 的根因。[高]
- **可落地变量**:`std(EPS_forecasts)/|mean|`(分歧),`#上调−#下调 / #分析师`(修正广度),`Δconsensus_EPS / |EPS|`(修正幅度),SUE(标准化盈余惊喜,接 PEAD)。

### 4.3 PEAD(财报后漂移,中期 1-3 月)

- **机制**:盈余惊喜后价格**漂移**数周到数月,投资者对盈余信息 underreaction。属**动量/underreaction 系**,与情绪极值的过度反应相反。
- **证据 [中-高]**:Garfinkel-Hribar-Hsiao(2024)top–bottom SUE 3 月风险调整约 **5.1%**(年化 >20%)[未核实,毛、含小盘];但美国大盘 PEAD 衰减(Martineau 2022),文本化盈余惊喜仍强(Meursault 2023)。
- **落地**:作为**中期(1-3 月)横截面倾斜**因子,与修正广度并列;注意 PEAD 高度集中在小盘/低关注/财报日附近,大盘净 alpha 弱。
  - 一手:[Quantpedia PEAD](https://quantpedia.com/strategies/post-earnings-announcement-effect);[PEAD review 2020](https://www.sciencedirect.com/science/article/pii/S2214635020303750)

---

## 5. 数据与可得性(优先免费)

| 数据 | 来源 | 免费? | 频率/历史 | 备注 |
|---|---|---|---|---|
| **AAII Bull-Bear** | AAII 官网 Sentiment Survey + Past Results | 部分免费(历史 CSV 会员/有限) | 周,1987 至今 | [past results](https://www.aaii.com/sentimentsurvey/sent_results);MacroMicro 有图 |
| **CBOE Put/Call(equity/total)** | CBOE Historical Data / DataShop | 部分免费(部分区间免费档案) | 日;历史档约 2006–2019 免费档,新数据部分付费 | [CBOE historical](https://www.cboe.com/us/options/market_statistics/historical_data/) |
| **VIX** | CBOE / **FRED `VIXCLS`** | 是(FRED 全免费) | 日,1990 至今 | FRED 最省事 |
| **CNN Fear & Greed** | CNN 官网(有非官方 JSON 端点) | 是(展示);历史需第三方 | 日,2011 至今 | [CNN](https://www.cnn.com/markets/fear-and-greed);历史用 finhacker/第三方 |
| **Investors Intelligence** | II / Yardeni | 多为**付费** | 周 | 免费替代:用 AAII |
| **Baker-Wurgler 指数** | **Jeffrey Wurgler NYU 站点**(月度 CSV) | 是(免费下载) | 月,1965 起,定期更新 | [Wurgler 论文/数据页](https://pages.stern.nyu.edu/~jwurgler/) |
| **分析师修正/分歧** | I/B/E/S(付费)、Zacks、Refinitiv | 多为付费 | 日/周 | 免费近似:Finnhub/Financial Modeling Prep 免费档有 estimate/revision;yfinance 有有限 recommendations |
| **盈余惊喜/SUE** | Compustat/IBES(付费);Finnhub/FMP 免费档 | 部分 | 季 | 自建:actual − consensus,标准化 |

要点:**最免费且独立的三件套 = FRED(VIX)+ CBOE 免费档(Put/Call)+ Wurgler 站(BW 月度)**;AAII 周度图免费但**机读历史**需自行抓取/会员。分析师修正是本族最有价值但**最贵**的一块,免费档(Finnhub/FMP)质量参差,需做 PIT 校验。

---

## 6. 落地到本系统(逆向温度计 / feed / 脚本 / 验证)

设计原则:**三条独立轴,分层用,默认保守,信号必过三关。**

### 6.1 轴 A — 逆向"风险温度计"(慢、有界、对称)

- **输入**:把 AAII(4–8 周平滑)、Put/Call(equity,5–10 日平滑)、VIX(z-score)、CNN F&G 各自转成**自身历史 percentile / z-score**,再合成一个 `Sentiment_Temp ∈ [−1, +1]`(注意去重叠:F&G 已含 VIX+Put/Call,合成时降权或只取残差,避免重复计数)。
- **用法**:**不是交易触发**,而是调**风险预算 / 总仓位倾斜**:
  ```
  极度恐惧(Temp 低分位,如 <10%) → 风险预算上调 +X%(温和加仓/加 beta)
  极度贪婪(Temp 高分位,如 >90%) → 风险预算下调 −X%
  中间区(10%–90%) → 不动(避免噪声交易)
  ```
  约束:`|ΔTemp 倾斜| ≤ ±15~25%` 相对基准;变更**慢速**(EWMA、每周 ≤1 次);**对称**;有死区(deadband)。
- **理由**:极值稀有、timing 差 → 只在尾部温和倾斜,赚"赔率",不赌"拐点"。

### 6.2 轴 B — 横截面行为因子(中期 1-3 月,可正式入仓)

- **`rev_breadth`** = (#上调 − #下调) / #分析师(过去 ~60–100 日);**`rev_mag`** = Δconsensus_EPS / |EPS|;**`SUE`**(PEAD)。
- **`dispersion`** = std(EPS_est)/|mean| → **高分歧作负向(乐观过头)红旗**(谨慎,稳健性弱,先 feed-only)。
- 这些是 **underreaction 系**,与已有 momentum/value 层耦合;按本系统标准做正交化(对 size/value/mom 回归取残差),避免重复暴露。

### 6.3 轴 C — 长期反转(仅辅助 deep-value)

- 只在**剔除微小盘 + 控制税效应/1 月季节 + 与 value 正交后**仍显著时,才作 value 的小幅辅助倾斜;否则**降级为研究 feed,不入仓**。

### 6.4 Feed / 看板

- 看板新增 **"行为/情绪面板"**:`Sentiment_Temp` 仪表(含各分项 percentile)、AAII spread 时序、Put/Call、VIX、F&G、BW 月度;再加**横截面榜**:本周修正广度上调榜/下调榜、SUE 榜、高分歧红旗榜。
- 全部标**前视安全戳**(每个数值标 as-of 日期,确保 PIT)。

### 6.5 脚本(建议路径,沿用本仓 `scripts/` 与 `feed/`)

- `scripts/fetch_sentiment.py`:拉 FRED VIX、CBOE Put/Call、AAII(抓取)、CNN F&G(JSON 端点)、Wurgler BW → 落地标准化 parquet,带 as-of 戳。
- `scripts/build_sentiment_temp.py`:percentile/z-score + 去重叠合成 `Sentiment_Temp`,输出风险预算倾斜建议(有界、对称、死区)。
- `scripts/fetch_revisions.py`:分析师修正/分歧/SUE(免费档 Finnhub/FMP)→ 横截面因子,PIT 对齐。
- `backtest/`:复用现有框架跑轴 B 因子的 IC / 分组 / Deflated Sharpe;轴 A 跑"温度→风险预算"的事件研究(极值后 1/3/6/12 月分布)。

### 6.6 验证清单(防过拟合三关)

1. **样本外 / 子周期**:1987–2007 vs 2008–2026 分段;情绪信号必须报告 **2023–2024 失效区间**的表现(AAII 在该区间钝化是已知警讯)。
2. **Deflated Sharpe / 多重检验**:情绪极值阈值是典型"多重比较温床"(试过多少阈值?),用 Deflated Sharpe、要求 **t>3**,阈值参数做敏感性曲面(不能只报最优点)。
3. **净·扣成本**:长期反转/PEAD 的 alpha 高度集中在小盘 → **必须扣买卖价差 + 冲击 + 借券成本(空头腿)**后再判;轴 A 温倾斜本身换手低,成本小但要算。
4. **前视/泄漏审计**:财报数据用 PIT(announcement date 可得值,非 restated);AAII/调查用**发布日**对齐;BW 月度有**发布滞后**,不可用当月底即时值。
5. **without-hindsight 评估**:所有情绪信号只用截至当时已知数据生成 → 算前向收益,禁止用全样本分位阈值回看。

---

## 7. 风险与反方

- **情绪极值=稀有事件 → 统计功效天然低**:几十年里真正的极值可能只有几十次,任何"极值后必反弹"的 backtest 都建立在**极少独立观测**上,过拟合风险极高。这是最根本的反方。[高]
- **2023–2024 反例**:AAII spread 长期高企却无随后跑输 → 情绪指标可能**结构性失效或滞后拉长**(散户结构变化、被动资金、零佣金/期权散户化改变了 Put/Call 含义)。[中-高]
- **重叠 / 共线**:F&G ⊃ VIX+Put/Call+动量;长期反转 ≈ value;BW 横截面 ≈ 投机性子集 ≈ size/低质量。**很多"情绪信号"是已有因子的换皮**,合成不去重会重复下注。[高]
- **不对称性(反复出现)**:"极度恐惧→看多"通常比"极度贪婪→看空"更可靠;VIX 低/自满作空头信号弱;BW 高情绪期逆向有效、低情绪期弱。**别假设对称。**[中-高]
- **分歧异象稳健性争议**:Diether-Malloy-Scherbina 经典,但近年有文献质疑其在剔除小盘/流动性后是否稳健 → dispersion 先 feed-only。[中]
- **数据质量(免费档)**:免费分析师修正/SUE(Finnhub/FMP)覆盖、PIT 准确性参差;CBOE 免费 Put/Call 历史档断点(~2019)需拼接。[中]
- **反方观点(有效市场/数据挖掘派)**:大量情绪异象在样本外、扣成本、控已知因子后消失(McLean-Pontiff 式衰减)。**默认假设:情绪信号入仓前先证伪。**[高]
- **拥挤 / 反身性**:CNN F&G、AAII 已被广泛跟踪,广为人知的逆向信号边际会被套利掉;修正/PEAD 被机构高度挖掘,美国大盘段衰减即证据。[中-高]

---

## 8. 参考来源(URL + 可信度)

**长期反转**
- [中-高] [De Bondt & Thaler 1987, JF (overreaction & seasonality)](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1987.tb04569.x) — 原始过度反应一手。
- [中-高] [De Bondt-Thaler 1985 复制 (post-2000 data), 2024/2025](https://www.researchgate.net/publication/393123188_Does_the_Stock_Market_Still_Overreact_A_Replication_of_De_Bondt_and_Thaler_1985_Using_Post-2000_Data) — 美股反转衰减证据。
- [中-高] [George & Hwang, "Long-Term Return Reversals: Overreaction or Taxes?" PDF](https://www.bauer.uh.edu/tgeorge/papers/gh5-paper.pdf) — 税收混淆。
- [中] [Do markets overreact: International evidence, ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0378426698001332) — 国际稳健性。
- [中] [Alpha Architect, Long-Term Return Reversal](https://alphaarchitect.com/quantitative-momentum-research-long-term-return-reversal/) — 实务综述。

**AAII / 情绪极值**
- [中] [AAII Bull/Bear Spread 术语页](https://www.aaii.com/terms/a/373957-aaii-bullbear-spread) — 定义/阈值,一手。
- [中] [AAII Sentiment Survey 官页](https://www.aaii.com/sentimentsurvey) + [Past Results](https://www.aaii.com/sentimentsurvey/sent_results) — 数据一手。
- [部分未核实] [AAII Journal "Analyzing AAII Sentiment Survey Without Hindsight"](https://www.aaii.com/journal/article/analyzing-the-aaii-sentiment-survey-without-hindsight) — 全文 403,仅据标题/检索摘要。
- [中] [Edge and Odds, "Don't Be Too Sentimental"](https://www.edgeandodds.com/investor-sentiment-surveys-dont-be-too-sentimental/) — 方法学批评(样本小)。
- [中] [FearGreedChart, 38 年 AAII 回顾 (2026)](https://feargreedchart.medium.com/the-aaii-sentiment-survey-ce3c9cc38aad) — 长期统计,二手。

**Put/Call & VIX**
- [中] [Britannica Money, Put-Call Ratio (vs VIX)](https://www.britannica.com/money/put-call-ratio) — 定义/对比。
- [中] [Put-Call vs VIX 比较研究, ResearchGate](https://www.researchgate.net/publication/284698793_Measures_Of_Investor_Sentiment_A_Comparative_Analysis_Put-Call_Ratio_Vs_Volatility_Index) — 学术比较。
- [中] [Spotting a market bottom with put/call, luckbox](https://luckboxmagazine.com/techniques/spotting-market-bottom-put-call-ratio/) — 实务(2007–2022 回测)。

**CNN Fear & Greed**
- [低-中] [CNN Fear & Greed 官页](https://www.cnn.com/markets/fear-and-greed) — 一手实时。
- [低-中] [Supertype 方法学拆解](https://supertype.ai/notes/fear-greed-index-part1) — 成分解释。
- [低] [finhacker F&G 历史数据 2011–2026](https://www.finhacker.cz/en/fear-and-greed-index-historical-data-and-chart/) — 历史序列(第三方)。

**Baker-Wurgler**
- [高] [Baker & Wurgler, JF 2006 作者站 PDF](https://pages.stern.nyu.edu/~jwurgler/papers/wurgler_baker_cross_section.pdf) — 原始一手。
- [高] [Jeffrey Wurgler NYU 站点(数据下载)](https://pages.stern.nyu.edu/~jwurgler/) — 免费月度指数。
- [中] [An Enhanced Investor Sentiment Index, T&F 2023](https://www.tandfonline.com/doi/full/10.1080/1351847X.2023.2247440) — 时变权重增强版。

**分析师修正 / 分歧 / PEAD**
- [中-高] [Mill Street, Analyst Estimate Revisions](https://www.millstreetresearch.com/do-analyst-estimate-revisions-still-help-forecast-relative-stock-returns/) — 修正>水平,广度>幅度,量化(厂商回测)。
- [中] [Fed FEDS 2024-049, Predicting Analysts' S&P500 Forecast Errors PDF](https://www.federalreserve.gov/econres/feds/files/2024049pap.pdf) — 修正与市场收益,1994–2023。
- [中] [Stanford GSB, Analyst Revisions & Accruals Pricing](https://www.gsb.stanford.edu/faculty-research/working-papers/analyst-earnings-forecast-revisions-pricing-accruals) — 修正预测收益。
- [中-高] [Quantpedia, Post-Earnings Announcement Effect](https://quantpedia.com/strategies/post-earnings-announcement-effect) — PEAD 策略/数据。
- [中] [A review of PEAD, ScienceDirect 2020](https://www.sciencedirect.com/science/article/pii/S2214635020303750) — 综述+衰减证据。

**数据源**
- [高] [FRED VIXCLS](https://fred.stlouisfed.org/series/VIXCLS) — VIX 全免费日频 [未核实链接,标准 FRED 序列]。
- [中] [CBOE Historical Options Data](https://www.cboe.com/us/options/market_statistics/historical_data/) — Put/Call 免费档。
- [中] [MacroMicro CBOE Put/Call](https://en.macromicro.me/charts/449/us-cboe-options-put-call-ratio) — 图/数据(第三方)。

---

### 附:本族信号的"机制象限"(理解为何分层)

| 信号 | 行为机制 | 方向 | 最佳期限 | 本系统角色 |
|---|---|---|---|---|
| 长期反转 | 过度反应回归 | 逆向 | 3-5 年 | 辅助 deep-value(剔小盘/税后) |
| 情绪极值(AAII/PC/VIX/F&G) | 过度反应(尾部) | 逆向 | 周-月(尾部) | 风险温度计(慢/有界/对称) |
| Baker-Wurgler | 投机性溢价 | 逆向(横截面) | 月-年 | 慢倾斜(高情绪期更可信) |
| 分析师修正 | 反应不足 | 顺势 | 1-3 月 | 正式横截面因子 |
| 分歧(dispersion) | 乐观过头+卖空限制 | 逆向 | 月 | feed-only(稳健性弱) |
| PEAD/SUE | 反应不足 | 顺势 | 1-3 月 | 正式横截面因子 |

**关键洞察:这一族里"逆向(过度反应)"和"顺势(反应不足)"机制并存且期限不同——情绪极值/长期反转是逆向,分析师修正/PEAD 是顺势。把它们混成一个"行为因子"会自相抵消;必须按象限分层。**
