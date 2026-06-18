# 宏观/领先指标对长周期股票回报的预测力

> 调研目标:评估收益率曲线、信用利差、Sahm Rule、ISM/PMI、LEI、金融条件指数(NFCI)等
> 宏观/领先指标对 **6–24 个月股票回报** 的真实可预测力,并给出可落地到本系统的做法。
> 房规:净·扣成本唯一货币;诚实可证伪;标注前视/幸存者偏差;关键结论标一手来源 URL + 可信度;
> 偏好免费/PIT(FRED + ALFRED vintage)。
>
> 调研日期:2026-06-18 · 数据优先区间 2023–2026 · 作者:research routine
>
> **可信度图例**:🟢 高(一手:Fed/官方/同行评审) · 🟡 中(机构研报/可信媒体) · 🔴 低/未核实(二手、博客、AI 摘要)

---

## 1) TL;DR

1. **宏观择时的历史记录很差。** 学术界对"用宏观变量预测股票超额回报"的共识是:**样本外 R² 通常 ≈ 0 或为负**,
   绝大多数预测变量无法稳定打败"历史均值"这个朴素基准(Goyal–Welch 2008,以及 2024 RFS 重做,🟢)。
   因此本系统**不做宏观择时**,只把这些指标当作**温和的风险开关(risk dial)**,影响仓位/杠杆/对冲强度,
   而非"清仓/满仓"的二元开关。

2. **收益率曲线(10y-3m / 10y-2y)是最有名的衰退领先指标,但 2022–2024 是一次典型"狼来了"。**
   2022 年中倒挂、深度且持续到 2024 年,却**没有衰退**,经济 2023 增长 2.9%、2024 多季度 3%+(🟡)。
   这削弱了"倒挂 → 必衰退 → 必熊市"的链条,但**没有证伪**它"提高了风险概率"。

3. **信用利差(HY OAS / BAA-AAA)是更同步、噪音更低的风险溢价信号**,通常在股票见顶前数月走阔(🟡),
   作为"市场已经在重新定价风险"的同步/略领先指标,比纯利率曲线更可用于风险开关。

4. **Sahm Rule 2024 年 7 月被触发但无衰退**(移民推高失业率而非需求走弱),Sahm 本人也说"不在衰退,只是风险升高"(🟢)。
   这是该规则的第二次假阳性(2003、2024)。

5. **Conference Board LEI 在 2022 连续暴跌、预测"数月内衰退",结果没有**;TCB 事后修改了判定规则(🟡)。
   LEI 过度偏向制造业(仅占经济 ~11%),2023 制造业衰退但服务业(~89%)强劲。

6. **NFCI / ANFCI(Chicago Fed)** 是周频、广覆盖(105 个指标)的金融条件指数,
   **正值=偏紧、负值=偏松**;ANFCI 剔除了与经济活动相关的部分,更"纯"。适合做连续风险开关输入。

7. **关键数据源:FRED API(免费、PIT 友好、有 ALFRED vintage)**。
   核心 series:`T10Y3M`、`T10Y2Y`、`BAMLH0A0HYM2`(HY OAS)、`BAMLC0A0CM`(IG OAS)、
   `UNRATE`、`SAHMREALTIME`、`NFCI`、`ANFCI`、`USREC`(NBER 衰退,事后)。
   **重要坑:ISM/PMI 系列已从 FRED 下架(版权),不能再免费拉**(详见 §5)。

8. **落地建议**:新增 `feed/macro/latest.json`(连续 0–1 的 `risk_dial` + 各分项),由 GitHub Actions
   周频/日频脚本从 FRED 拉取并写入;消费端只允许**温和**调节 `market_state.regime` 与对冲比例,
   且必须**用 ALFRED vintage 做 PIT 回测**才能声称任何预测力(否则前视污染)。

---

## 2) 各指标定义 + FRED series ID

> 单位/频率以 FRED 页面为准;下面是常用核心集合。已下架者明确标注。

### 2.1 收益率曲线(期限利差)
| 指标 | FRED series | 含义 | 频率 |
|---|---|---|---|
| 10y − 3m 期限利差 | `T10Y3M` | 学术上对衰退预测最优的曲线口径(NY Fed 模型用此) | 日 |
| 10y − 2y 期限利差 | `T10Y2Y` | 媒体最常引用;2022-07 倒挂 | 日 |
| 10y 名义国债 | `DGS10` | 构造自定义口径用 | 日 |
| 3m 国债 | `DGS3MO` | 同上 | 日 |
| 2y 国债 | `DGS2` | 同上 | 日 |

- **倒挂 = 利差 < 0**。NY Fed 的 Estrella–Mishkin probit 用 `T10Y3M` 估"未来 12 个月衰退概率",
  历史阈值经验值 ~20–30%(🟢,见 §3.1)。

### 2.2 信用利差(风险溢价)
| 指标 | FRED series | 含义 | 频率 |
|---|---|---|---|
| 美国高收益 OAS | `BAMLH0A0HYM2` | ICE BofA US High Yield Index 期权调整利差;投机级违约风险定价 | 日 |
| 美国投资级 OAS | `BAMLC0A0CM` | ICE BofA US Corporate(IG)OAS | 日 |
| BBB OAS | `BAMLC0A4CBBB` | 投资级最低档,常作"风险偏好"代理 | 日 |
| Moody's Baa 收益率 | `DBAA` / `BAA` | 经典 BAA-AAA 利差的构件 | 日/月 |
| Moody's Aaa 收益率 | `DAAA` / `AAA` | 同上 | 日/月 |

- **BAA-AAA 利差**没有现成单一 series,需 `DBAA - DAAA`(或月频 `BAA - AAA`)自行相减。
- HY OAS 走阔 = 投资者要求更高补偿(违约预期↑或流动性↓);与 S&P500 显著负相关(🟡,见 §3.2)。

### 2.3 劳动力市场 / Sahm Rule
| 指标 | FRED series | 含义 | 频率 |
|---|---|---|---|
| 失业率 | `UNRATE` | U-3 失业率 | 月 |
| Sahm Rule(实时口径) | `SAHMREALTIME` | 用**当时已知**的失业率算,适合 PIT | 月 |
| Sahm Rule(当期修订口径) | `SAHMCURRENT` | 用最新修订数据,**含前视偏差**,回测勿用 | 月 |

- **Sahm Rule 触发**:失业率 3 个月移动均值 − 过去 12 个月最低值 ≥ 0.50 个百分点。
- **PIT 注意**:回测**必须**用 `SAHMREALTIME`(St. Louis Fed 已替你处理 vintage),
  用 `SAHMCURRENT` 会因失业率事后修订而前视污染(🟢,见 §4)。

### 2.4 金融条件指数(NFCI)
| 指标 | FRED series | 含义 | 频率 |
|---|---|---|---|
| NFCI | `NFCI` | Chicago Fed 国家金融条件指数;**正=偏紧,负=偏松** | 周 |
| 调整后 NFCI | `ANFCI` | 剔除与经济活动/通胀相关的部分(更"纯"的金融条件) | 周 |
| NFCI 信用子指数 | `NFCICREDIT` | 信用条件分项 | 周 |
| NFCI 杠杆子指数 | `NFCILEVERAGE` | 债务/股权杠杆分项 | 周 |
| NFCI 风险子指数 | `NFCIRISK` | 波动/融资风险分项 | 周 |

### 2.5 ISM / PMI(⚠️ FRED 已下架,见 §5)
| 指标 | 旧 FRED series | 状态 |
|---|---|---|
| ISM 制造业 PMI | `NAPM` / `ISMMAN`(旧) | 🔴 **已从 FRED 下架(版权)**,不能再免费拉 |
| ISM 服务业 PMI | `NMFCI` 等(旧) | 🔴 同上 |

- 替代:`FRED-MD` 月度宏观库历史上含 ISM 类指标,但当前发布版可能同样受限;
  或用与 PMI 高相关的免费代理(详见 §5)。**未核实当前 FRED-MD 是否仍含 ISM。**

### 2.6 衰退基准(用于评估,非预测)
| 指标 | FRED series | 含义 |
|---|---|---|
| NBER 衰退指示 | `USREC` | NBER 事后认定的衰退月(0/1)。**事后**,只能当评估标签,不能当实时信号 |
| Conference Board LEI | (FRED 无官方免费 series) | TCB 版权数据,FRED 上无完整免费 series;见 §3.5 |

---

## 3) 预测力证据与失灵

### 3.1 收益率曲线:经典证据 + 2022–2024 失灵
- **经典正面证据(🟢)**:NY Fed 的 Estrella–Mishkin(1996)probit 模型用 `T10Y3M` 期限利差,
  自 1950s 以来**几乎预测了每一次衰退(仅 1967 例外)**;经验阈值"12 个月衰退概率 >20–30%"。
  - NY Fed FAQ:<https://www.newyorkfed.org/research/capital_markets/ycfaq>(🟢 一手)
  - 原始论文(Current Issues 2.7):<https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci2-7.pdf>(🟢)
  - Chicago Fed《Why Does the Yield-Curve Slope Predict Recessions?》:
    <https://www.chicagofed.org/publications/chicago-fed-letter/2018/404>(🟢)
  - Cleveland Fed 收益率曲线-GDP 模型(实时更新):
    <https://www.clevelandfed.org/indicators-and-data/yield-curve-and-predicted-gdp-growth>(🟢)
- **2022–2024 失灵("狼来了",🟡)**:
  - 10y-2y 于 **2022-07-05** 倒挂、深且久,10y-3m 也深度倒挂至 2024,**却无衰退**;
    经济 2023 增长 2.9%、2024 二/三季度年化 3%+。常见解释:本轮经济**对利率不那么敏感**。
  - U.S. News《Inverted Yield Curve: Is it Still a Recession Indicator?》:
    <https://money.usnews.com/investing/articles/inverted-yield-curve-is-it-still-a-recession-indicator>(🟡)
  - S&P Global(2024-08,曲线接近 un-invert):
    <https://www.spglobal.com/market-intelligence/en/news-insights/articles/2024/8/key-portion-of-yield-curve-near-inversion-end-with-another-still-deeply-negative-82817957>(🟡)
- **对"股票回报"的可预测力(关键,且诚实)**:曲线预测的是**衰退**,不是**股票回报**。
  即使倒挂→衰退命中,衰退与熊市的**时点错位**可达 12–24 个月,期间股市常**继续上涨**(2022–2024 即如此)。
  作为 6–24 个月股票回报的直接预测变量,**样本外 R² 很低**(见 §3.6)。

### 3.2 信用利差(HY OAS / BAA-AAA):更同步、噪音更低
- **机制**:`BAMLH0A0HYM2` 是债市对投机级违约风险的**实时**定价;走阔=风险重定价。
  机构信用投资者通常比股票投资者**更早**重定价风险,故 HY OAS 常在股票见顶前数月走阔(🟡)。
  - FRED series 页:<https://fred.stlouisfed.org/series/BAMLH0A0HYM2>(🟢 数据一手)
  - 与 S&P500 显著负相关的二手分析(🔴/🟡,博客类,**未独立核实回归系数**):
    <https://www.money365.market/articles/credit-cycle-analysis>
- **诚实**:信用利差与股票更像**同步**而非领先;它"领先股票见顶数月"的说法多来自事后挑选的样本,
  **存在叙事偏差**。但作为**风险开关输入**,HY OAS 的优点是:连续、日频、市场定价(不靠预测模型)、
  与股票尾部风险同号。BAA-AAA 是其低频版本,信息重叠。

### 3.3 Sahm Rule:2024 假阳性
- **定义见 §2.3**。**2024-07 触发**(3 个月失业率均值高出近一年低点 0.53pp),**无衰退**。
  Sahm 本人:风险升高但"不在衰退";学界归因于**移民激增推高失业率供给端**,而非需求走弱(🟢)。
  - CRS(国会研究服务)《Is the United States in a Recession?》:
    <https://www.congress.gov/crs-product/IN12410>(🟢 一手政府)
  - Richmond Fed《SOS! Signaling Recessions Earlier》(2025):
    <https://www.richmondfed.org/publications/research/economic_brief/2025/eb_25-07>(🟢)
  - FRED `SAHMREALTIME`:<https://fred.stlouisfed.org/series/SAHMREALTIME>(🟢)
- **历史假阳性**:2003、2024。样本极少(只覆盖几次衰退),**统计置信度本就有限**——
  谨防把"5/5 命中"当成强证据(自由度太小)。

### 3.4 ISM / PMI
- PMI<50 表示制造业收缩,历史上与工业周期/盈利周期相关。但:
  - **2023 制造业衰退、整体经济不衰退**——制造业仅占经济 ~11%,PMI 对整体的代表性下降。
  - **数据可得性问题**:ISM 系列**已从 FRED 下架**(版权),见 §5。这直接影响"免费/PIT"约束。

### 3.5 LEI(Conference Board):2022 假信号 + 事后改规则
- **失灵(🟡)**:2022 LEI 暴跌后 TCB 预测"数月内衰退",**没发生**;
  旧经验法则"连续 3 个月下滑=衰退"被 TCB 改为"6 个月内多少分项在跌"。
  - Conference Board《Leading Indicators and the Oncoming Recession》:
    <https://www.conference-board.org/publications/Leading-Indicators-Recession>(🟡 一手但有立场)
  - 批评性二手:<https://www.investing.com/analysis/leading-economic-index-misses-again-are-recession-forecasts-broken-200646272>(🔴/🟡)
  - <https://www.acgbiz.com/insights/conference-board-backs-its-recession-forecast>(🔴)
- **可得性**:LEI 是 TCB 版权产品,**FRED 无完整免费 series**;不满足"免费/PIT"——**降权或弃用**。

### 3.6 对"股票回报"的总体可预测力(最重要、最诚实的一节)
- **Goyal–Welch(2008)及 2024 RFS 重做(🟢,核心权威)**:
  系统性检验大量宏观/估值预测变量对**股票超额回报**的预测,结论:
  - **样本外**多数模型 **R² 为负或仅略正**,无法稳定打败"历史均值"基准。
  - 2024 重做检验了 2008 后 26 篇论文的 29 个"新变量",**逾 1/3 连样本内都不再显著**,
    显著者中**约一半样本外表现差**。
  - 论文(RFS 2024):<https://academic.oup.com/rfs/article/37/11/3490/7749383>(🟢 同行评审)
  - SSRN/NBER 版:<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=517667> ·
    <https://www.nber.org/system/files/working_papers/w10483/w10483.pdf>(🟢)
- **含义**:本系统**不应**用任何单一宏观指标做月度/季度择时。这些指标能提供的,顶多是
  **缓慢移动的风险概率**(衰退/紧缩概率),用于**温和**地调整风险敞口与对冲,而不是预测回报方向。

---

## 4) PIT / vintage 问题(ALFRED)

> 这是把宏观指标用于回测时**最容易翻车**的地方。不处理 vintage = 前视污染 = 回测虚高。

- **为什么宏观数据有 vintage**:GDP、失业率、LEI、ISM 等都会被**多次修订**。
  "今天看到的 2024-07 失业率"≠"2024-08 当时公布的值"。用最终修订值回测 = **前视偏差**。
- **ALFRED(Archival FRED)**:捕捉每个 series 的**每一次修订(vintage)**,
  可检索"某个历史日期当时已知的版本"。每个观测有三日期:`date`、`realtime_start`、`realtime_end`。
  - ALFRED:<https://alfred.stlouisfed.org/>(🟢)
  - FRED API real-time period 文档:<https://fred.stlouisfed.org/docs/api/fred/realtime_period.html>(🟢)
- **发布滞后(release lag)同样要建模**:失业率约下月初公布、GDP 滞后更久、ISM 月初、NFCI 周更但有几天滞后。
  回测时**任何 t 时刻只能用 realtime_start ≤ t 的数据**。
- **本系统纪律(硬性)**:
  1. **回测**:对所有月频/季频宏观系列,用 ALFRED vintage(`realtime_start`/`realtime_end`)做 PIT 对齐;
     Sahm 用 `SAHMREALTIME` 而非 `SAHMCURRENT`。
  2. **日频市场系列**(`T10Y3M`、`BAMLH0A0HYM2`、`NFCI`)修订很小,但**发布滞后**仍需对齐(用收盘后/下一交易日)。
  3. 任何"宏观预测股票回报"的**声明**,若未用 vintage 复核,一律在报告里标 **未核实**。
- **工具**:`fredapi`(Python)提供 `get_series_all_releases` / `get_series_as_of_date` 解析 ALFRED vintage。
  - <https://github.com/mortada/fredapi>(🟡 社区维护,API key 免费)

---

## 5) 数据与可得性(FRED 免费)

- **FRED API**:免费,需注册 **API key**(`https://fred.stlouisfed.org/docs/api/api_key.html`)。
  - 端点示例:`https://api.stlouisfed.org/fred/series/observations?series_id=T10Y3M&api_key=KEY&file_type=json`
  - vintage:加 `realtime_start` / `realtime_end` 参数即得 PIT 版本。
  - 速率:有限速但对每日/每周拉几十个 series 完全够用(**具体每秒/每日上限未核实**,实践中以"礼貌轮询+缓存"应对)。
  - 许可:FRED 多数美国官方系列**可免费再分发**;但**第三方版权系列(ISM、Conference Board LEI 等)受限**。
- **⚠️ ISM/PMI 已下架**:FRED 公告"Institute for Supply Management Data To Be Removed from FRED",
  22 个 ISM 制造业/非制造业系列从 FRED(含 API、Excel 插件、App)**移除**(版权原因)。
  - <https://research.stlouisfed.org/fred2/series/NAPM>(🟢 一手公告;**具体下架日期未逐字核实**,搜索摘要称"6 月 24 日")
  - **后果**:ISM/PMI **不满足本系统"免费/PIT"约束**。处理:
    - (a)**弃用**,用 HY OAS + NFCI + 曲线覆盖大部分风险信息;或
    - (b)用免费代理(如地区联储制造业调查 `GACDISA066MSFRBPHI`=Philly Fed、
      Empire State、Chicago PMI 的部分公开口径——**各自可得性与版权未逐项核实**);或
    - (c)若确需 ISM,改走付费/官方 ISM 渠道(违反"免费优先",仅在证明有增量价值后)。
- **LEI(Conference Board)**:版权,FRED 无完整免费 series → 本系统**默认弃用**,
  其制造业偏置 + 2022 假信号也降低了它的边际价值。
- **可免费、PIT 友好、推荐纳入的核心集合**:
  `T10Y3M`, `T10Y2Y`, `DGS10`, `DGS3MO`, `DGS2`,
  `BAMLH0A0HYM2`, `BAMLC0A0CM`, `BAMLC0A4CBBB`, `DBAA`, `DAAA`,
  `UNRATE`, `SAHMREALTIME`,
  `NFCI`, `ANFCI`, `NFCICREDIT`, `NFCILEVERAGE`, `NFCIRISK`,
  `USREC`(评估用标签)。

---

## 6) 落地到本系统

> 设计原则与本仓一致:`feed/` 是 JSON 单一真相源(GitHub raw/Pages 可直取);
> GitHub Actions 例行任务产出;无重型依赖;失败降级不阻断;净·扣成本唯一货币。
> 已存在的整合点:`feed/schema/report.schema.json` 里 `market_state.regime ∈ {risk_on,neutral,risk_off,unknown}`。

### 6.1 宏观风险开关(risk dial)——温和,不是择时
- **输出**:连续值 `risk_dial ∈ [0,1]`(0=极度 risk-off,1=极度 risk-on),由若干**标准化分项**加权:
  - 曲线分项:`T10Y3M`(及其 z-score / 是否倒挂)。
  - 信用分项:`BAMLH0A0HYM2` 的水平 + 近 N 日变化的 z-score(走阔→risk-off)。**权重最高**(同步、市场定价、低噪)。
  - 金融条件分项:`NFCI` / `ANFCI`(正→偏紧→risk-off)。
  - 劳动分项:`SAHMREALTIME`(触发→risk-off),**低权重**(月频、假阳性、自由度小)。
- **映射到 regime(温和)**:
  - `risk_dial ≥ 0.6` → 可标 `risk_on`;`≤ 0.4` → `risk_off`;之间 `neutral`。
  - **只允许影响**:总仓位上限、净敞口、对冲比例(如 SPY/IVOL 对冲强度),**不触发清仓/满仓**。
  - 中频 stat-arb 引擎本身市场中性,宏观开关主要调**对冲与杠杆**,不应反向交易残差信号。
- **诚实标注**:报告里写明"宏观择时历史记录差,本开关为温和风险调节,非回报预测",
  并给出 `risk_dial` 各分项贡献,可证伪、可回看。

### 6.2 feed 端点(新增)
- `feed/macro/latest.json`:最新一期快照
  ```json
  {
    "schema_version": "1.0",
    "asof_data": "2026-06-17",
    "produced_at": "2026-06-18T12:00:00Z",
    "risk_dial": 0.58,
    "regime_suggestion": "neutral",
    "components": {
      "curve":  {"series": "T10Y3M",        "value": 0.31, "z": -0.4, "inverted": false, "contrib": 0.15},
      "credit": {"series": "BAMLH0A0HYM2",   "value": 2.95, "z":  0.2, "widening_20d": false, "contrib": 0.30},
      "fci":    {"series": "ANFCI",          "value": -0.20, "z": -0.3, "contrib": 0.10},
      "labor":  {"series": "SAHMREALTIME",   "value": 0.13, "triggered": false, "contrib": 0.03}
    },
    "caveats": ["宏观择时记录差;仅温和风险开关", "ISM/PMI 因 FRED 下架未纳入"],
    "sources": ["FRED:T10Y3M","FRED:BAMLH0A0HYM2","FRED:ANFCI","FRED:SAHMREALTIME"]
  }
  ```
- `feed/macro/history.json`:保留最近 N 期(对齐本仓 `KEEP_DAYS≈60` 惯例,周频可保留更长)。
- **schema**:新增 `feed/schema/macro.schema.json`,或在 `report.schema.json` 的
  `additionalProperties` 框架下挂一个 `macro` 块;沿用 `feed_lib` 的签名/校验流程(HMAC + jsonschema 可选)。

### 6.3 脚本
- `scripts/macro_fred.py`(仅标准库 + 可选 `fredapi`):
  - 从 env 读 `FRED_API_KEY`;拉 §5 推荐核心集合(实时口径用于 latest,vintage 口径用于回测脚本)。
  - 计算各分项 z-score(滚动窗口,如 5y)→ 合成 `risk_dial` → 写 `feed/macro/latest.json` + 追加 history。
  - 失败降级:单 series 拉取失败则跳过该分项并在 `caveats` 记录,不阻断整体。
- GitHub Actions:`.github/workflows/macro-fred.yml`,**周频**(NFCI 周更)+ 每个交易日收盘后跑一次
  (日频曲线/信用更新)。沿用本仓 routine 风格(参考 `scripts/run_routine.py` / `daily_digest.py`)。

### 6.4 验证(没有 PIT 回测就不准声称预测力)
- `scripts/macro_backtest.py`(离线,不进 feed):
  - 用 **ALFRED vintage** 拉每个 series 的 PIT 版本(`fredapi.get_series_as_of_date` 或 API `realtime_*`)。
  - 对齐发布滞后,构造**任意 t 时刻可见**的 `risk_dial`。
  - 评估对 **6/12/24 个月前瞻 SPY(或本系统组合)超额回报** 的**样本外 R²**,
    基准=历史均值(对齐 Goyal–Welch 方法)。预期 R² 接近 0——**如果远大于 0,先怀疑前视/数据泄漏**。
  - 同时评估对 `USREC` 的衰退分类 AUC(作为"风险概率"而非"回报预测"的合理性检查)。
- **过拟合纪律**(与本仓 §6.7 一致):任何宏观开关参数(阈值/权重/窗口)若经搜索得到,
  用 Deflated Sharpe / 多重检验校正;权重尽量**先验设定**(信用>曲线>FCI>劳动),少调参。

### 6.5 看板
- 在现有看板加一个**宏观风险条**:显示 `risk_dial`、各分项贡献、`regime_suggestion` 与 caveats,
  并标注"非回报预测,仅风险调节"。可链到 FRED 原图增强可证伪性。

---

## 7) 风险与反方

1. **宏观择时基本无效(主反方)**:Goyal–Welch 等证据表明样本外几乎打不过历史均值。
   → 缓解:不做择时,只做温和风险开关;权重先验、少调参;强制 PIT 回测,R² 远超 0 视为告警而非胜利。
2. **样本量太小**:衰退在二战后仅 ~11 次,曲线/Sahm/LEI 的"X/X 命中"自由度极低,**易过拟合历史**。
   → 缓解:不依赖单指标;承认置信区间宽;不把"5/5"当强证据。
3. **结构性漂移("这次不一样"有时真不一样)**:2022–2024 经济对利率不敏感、移民扰动失业率、
   制造业占比下降使 PMI/LEI 失真——历史关系会**漂移**。→ 缓解:用市场定价类(HY OAS、NFCI)为主,
   它们是"市场当下的判断"而非"历史回归外推"。
4. **PIT/前视污染**:不用 vintage 会让回测虚高。→ 缓解:ALFRED 强制;Sahm 用 REALTIME;建模发布滞后。
5. **数据可得性/版权**:ISM、LEI 不免费/已下架,可能诱使用付费或代理数据 → 偏离"免费优先",
   且代理与原指标未必一致。→ 缓解:默认弃用,用免费 PIT 系列覆盖。
6. **同步 vs 领先的叙事偏差**:"信用利差领先股票见顶数月"多为事后挑样本。
   → 缓解:把 HY OAS 当**同步**风险温度计,不宣称稳定领先。
7. **过度反应风险**:即便"温和"开关,频繁切换 regime 也会增加换手与成本(违反净·扣成本货币)。
   → 缓解:加滞回(hysteresis)/最小持续期;开关只调对冲与杠杆,不强制交易。
8. **多重检验**:试了曲线/信用/Sahm/LEI/PMI/NFCI 多个指标再挑"有效"的=幸存者偏差。
   → 缓解:先验固定指标集与权重,报告所有(含失效)指标。

---

## 8) 参考来源(URL + 可信度)

**收益率曲线 / 衰退概率**
- NY Fed《The Yield Curve as a Leading Indicator》FAQ — <https://www.newyorkfed.org/research/capital_markets/ycfaq> 🟢
- Estrella–Mishkin《Yield Curve as a Predictor of U.S. Recessions》— <https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci2-7.pdf> 🟢
- Chicago Fed《Why Does the Yield-Curve Slope Predict Recessions?》— <https://www.chicagofed.org/publications/chicago-fed-letter/2018/404> 🟢
- Cleveland Fed《Yield Curve and Predicted GDP Growth》— <https://www.clevelandfed.org/indicators-and-data/yield-curve-and-predicted-gdp-growth> 🟢
- St. Louis Fed《What Is the Probability of a Recession? …Yield Spreads》(2023)— <https://www.stlouisfed.org/on-the-economy/2023/sep/what-probability-recession-message-yield-spreads> 🟢
- U.S. News《Inverted Yield Curve: Is it Still a Recession Indicator?》— <https://money.usnews.com/investing/articles/inverted-yield-curve-is-it-still-a-recession-indicator> 🟡
- S&P Global(2024-08 曲线接近 un-invert)— <https://www.spglobal.com/market-intelligence/en/news-insights/articles/2024/8/key-portion-of-yield-curve-near-inversion-end-with-another-still-deeply-negative-82817957> 🟡
- Marketplace《Why the inverted yield curve is typically a recession predictor》(2024)— <https://www.marketplace.org/story/2024/09/12/inverted-yield-curve-recession-predictor-indicator> 🟡

**信用利差**
- FRED `BAMLH0A0HYM2`(US HY OAS)— <https://fred.stlouisfed.org/series/BAMLH0A0HYM2> 🟢(数据一手)
- Money365《Credit Cycle Analysis》(HY-IG vs S&P500 相关性,**回归系数未独立核实**)— <https://www.money365.market/articles/credit-cycle-analysis> 🔴

**Sahm Rule / 劳动力**
- CRS《The Sahm Rule Trigger: Is the United States in a Recession?》— <https://www.congress.gov/crs-product/IN12410> 🟢
- Richmond Fed《SOS! Signaling Recessions Earlier》(2025)— <https://www.richmondfed.org/publications/research/economic_brief/2025/eb_25-07> 🟢
- FRED `SAHMREALTIME` — <https://fred.stlouisfed.org/series/SAHMREALTIME> 🟢
- FRED `SAHMCURRENT` — <https://fred.stlouisfed.org/series/SAHMCURRENT> 🟢
- Britannica Money《Sahm Rule…Definition, Accuracy》— <https://www.britannica.com/money/sahm-rule-recession-indicator> 🟡
- Wikipedia《Sahm rule》— <https://en.wikipedia.org/wiki/Sahm_rule> 🟡

**LEI(Conference Board)**
- Conference Board《Leading Indicators and the Oncoming Recession》— <https://www.conference-board.org/publications/Leading-Indicators-Recession> 🟡(一手但有立场)
- Investing.com《LEI Misses Again: Are Recession Forecasts Broken?》— <https://www.investing.com/analysis/leading-economic-index-misses-again-are-recession-forecasts-broken-200646272> 🔴
- ACG《The Conference Board Backs Off Its Recession Forecast》— <https://www.acgbiz.com/insights/conference-board-backs-its-recession-forecast> 🔴

**金融条件指数(NFCI)**
- Chicago Fed《About the NFCI》— <https://www.chicagofed.org/research/data/nfci/about> 🟢
- FRED `NFCI` — <https://fred.stlouisfed.org/series/NFCI> 🟢
- FRED `ANFCI` — <https://fred.stlouisfed.org/series/ANFCI> 🟢

**股票回报可预测力(核心)**
- Goyal–Welch–Zafirov《A Comprehensive 2022 Look at the Empirical Performance of Equity Premium Prediction》RFS 2024 — <https://academic.oup.com/rfs/article/37/11/3490/7749383> 🟢
- SSRN 原版 — <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=517667> 🟢
- NBER w10483 — <https://www.nber.org/system/files/working_papers/w10483/w10483.pdf> 🟢

**FRED / ALFRED / PIT**
- ALFRED 主页 — <https://alfred.stlouisfed.org/> 🟢
- FRED API real-time period 文档 — <https://fred.stlouisfed.org/docs/api/fred/realtime_period.html> 🟢
- FRED API key 申请 — <https://fred.stlouisfed.org/docs/api/api_key.html> 🟢
- `fredapi`(Python,ALFRED vintage 支持)— <https://github.com/mortada/fredapi> 🟡
- St. Louis Fed《ISM Data To Be Removed from FRED》(NAPM 公告页)— <https://research.stlouisfed.org/fred2/series/NAPM> 🟢(下架**具体日期未逐字核实**)

---

### 核实状态备注
- 收益率曲线 2022-07-05 倒挂、2023 GDP 2.9% 等宏观数字来自搜索结果二手摘要,**方向可信、具体小数未逐一核对原始 BEA/Treasury 数据**。
- ISM 从 FRED 下架为**一手公告**,但"6 月 24 日"这一**具体日期来自搜索摘要,未逐字核实**。
- HY OAS"领先股票见顶 4–8 个月"等具体提前量来自二手/AI 摘要,**未在同行评审中独立核实**,正文已降权处理。
- FRED API 具体速率上限**未核实**。
- 凡标 🔴 或"未核实"者,落地前需以一手来源复核。
