# 行业/板块轮动与长期配置 — 深度研究报告

> 目的:为本系统的**长期(持有期数月至数年)做多/倾斜**方向,评估"商业周期板块轮动"与"板块动量(RRG)"的实证有效性,并给出扣成本、防过拟合、可落地的做法。
> 方法:多角度并行检索(周期轮动实证 / 板块动量净收益 / Fidelity 模型评价 / 集中度均值回归 / RRG 构造 / 免费数据)→ 一手来源 + 可信度标注 → 合成到本系统已有的 `sector_map.json` 与 `RrgChart`。
> 日期:2026-06-18。所有关键结论标注来源 URL 与可信度(高/中/低)。
> 立场(房子风格):**净·扣成本收益是唯一货币;不接受"早周期买金融、晚周期买能源"这类事后叙事;凡历史毛收益默认打折;明确标前视(real-time vs NBER 事后定相)、过拟合、容量。择时板块轮动的公开记录平庸,稳健做法是相对强弱倾斜 + 纪律再平衡,而非押周期相位。**

---

## 1. TL;DR(可证伪要点)

1. **"商业周期板块轮动"作为择时策略,实证记录平庸到负:同行评审研究无法找到任何行业有显著的周期 alpha,只能找到显著跑输的行业。** Molchanov & Stangl《The Myth of (Business Cycle) Sector Rotation》:基于 Fama-French 三因子与 Carhart 四因子,**没有任何行业表现出显著超额,只有显著跑输的行业**;按周期相位轮动在扩张早/中期相对市场各约 **−0.05%/月**,Stage I / Stage II 的 alpha 为 **−5.3% 与 −1.0%**(年化口径,样本内),且市场指数 Sharpe 高于轮动(中-高可信度,已发表 IJF&E 2024)[Molchanov-Stangl AUT PDF; Wiley 2024]。→ **默认周期相位轮动无 alpha**,把它当"叙事"而非"策略"。

2. **"事后看图说话"成立 ≠ "事前可交易"成立。** 经济相位只有在数据确认后(常滞后 1-2 季度,NBER 衰退定相平均滞后约 7-12 个月)才知道,而股市早已 price-in 并提前轮动;要靠周期轮动赚钱,等价于"持续比市场共识更准地预测经济相位"——这是强假设,违反弱有效市场(中-高可信度)[Molchanov-Stangl; Fidelity 自述"每轮周期都不同"]。→ 凡用"现在是晚周期所以买能源"的逻辑,先问:这个相位判断是 real-time 可得,还是事后才知道?

3. **真实世界的板块轮动基金跑输明显。** 对一只代表性 Sector Rotation Fund(NAVFX)2010-2022 与 S&P 500 比较,**年化跑输约 8.1%**(中可信度,单只基金、含费率,样本有限)[Molchanov-Stangl via 检索摘要]。→ 把"换手 + 择时"的拖累具象化:择时板块的钱大多被成本与错相吃掉。

4. **板块"动量/相对强弱"(≠ 周期相位)在长样本里有正记录,但脆弱、回撤大,扣成本后优势收窄。** Quantpedia 经典"Sector Momentum Rotational System"(10 个板块、取 12 月动量前 3、等权、月度再平衡)长样本(1928-2009)**CAGR 13.94%、Sharpe 0.54、最大回撤 −46.29%**,较买入持有约 +4%/年(中可信度,样本含大萧条、月度换手高、未充分扣冲击)[Quantpedia]。→ 动量是真因子,但**月度换手 + −46% 回撤**意味着实盘必须降频、控成本、能扛深回撤。

5. **板块动量的成本敏感性是核心风险:经典"相对强弱"策略亏在高成本标的上;但用流动 ETF 实现时,ETF 价差远低于盈亏平衡成本。** 学术上 momentum 在个股层面"赚的恰是交易成本最高的股票",净化后利润大幅缩水;板块层面用 SPDR sector ETF(价差极窄、容量大)实现,则"价差远低于隐含盈亏平衡成本"(中可信度)[Lesmond/Korajczyk 系;Quantpedia 注]。→ **结论:在板块层面做动量倾斜可行,前提是低频(季度)+ ETF/大盘股 + 带宽缓冲。**

6. **再平衡频率决定成败:月度换手过高、年度太迟钝,季度是实证甜点。** 多份板块轮动研究指向**季度再平衡**在"响应度 vs 换手成本"间最优,并能产生统计显著的风险调整收益(中可信度,部分为近期/机器学习类研究,需独立复现)[MDPI 2026 TSX60;检索综述]。→ 本系统默认**季度**节奏,而非日/月。

7. **当前科技/IT 权重接近历史极值(~32-33% vs 2000 年 8 月峰值 ~33.6%),叠加 top-10 ~40%、单一 NVDA ~8%,集中度均值回归是长期配置的真实尾部风险。** 历史上"市场冠军"约半数在随后 10-20 年跑输并跌出前 15,几乎所有冠军最终被取代;集中度高且下行时,等权常大幅跑赢市值权重(中-高可信度)[S&P/SSGA;Bridgewater Life Cycle of Market Champions;Barclays 2025]。→ 长期组合应对"科技单押"做**显式约束**(板块上限/等权对冲腿),而非默认市值权重裸奔。

8. **稳健落地不是"押相位",而是"相对强弱倾斜 + 板块上限 + 季度再平衡"。** 本系统已有 `sector_map.json`(GICS 映射)与 `RrgChart`(rs/r63 近似 RRG)。落地路径:把个股 rs 聚合成**板块级 RRG**(用 SPDR sector ETF 或板块等权代理),在 Leading/Improving 象限做**有上限的小幅倾斜**,Lagging 减配,季度再平衡;并用本系统 PIT + 防过拟合纪律(Deflated Sharpe / PBO)对倾斜版 vs 等权/市值做净·扣成本对照——**若不显著胜出,就退回等权 + 板块上限**(本系统纪律)。

---

## 2. 定义:周期轮动 vs 板块动量(RRG)

### 2.1 商业周期板块轮动(Fidelity 模型)
来源:Fidelity Learning Center《An introduction to sector rotation strategies》[fidelity.com](中可信度,机构教育材料,利益相关)。
四相位 + 经典"应超配"板块(事后叙事版):
- **早周期(Early)**:衰退后急复苏、宽货币、利差扩张、利润率回升 → 经典超配**可选消费、金融、工业、原材料、房地产**(高 β、利率敏感)。
- **中周期(Mid)**:最长相位,温和增长、信贷扩张 → **信息科技**等领涨;无强方向,接近市场。
- **晚周期(Late)**:经济过热、通胀高于趋势、政策收紧、利润率走坏 → 经典超配**能源、原材料、必需消费、医疗、公用**。
- **衰退(Recession)**:利润下滑、信贷收缩 → 防御:**必需消费、公用、医疗**。

Fidelity 自己的免责声明(重要):"每一轮周期都以自己的方式不同";板块轮动"可能增加波动并跑输宽基";板块内不同行业的基本面驱动可能差异巨大(中可信度,Fidelity 自述)[fidelity.com]。

### 2.2 板块动量 / 相对强弱(与"周期相位"无关)
- **核心**:买"最近相对市场强"的板块,卖相对弱的;不依赖任何宏观相位判断,纯价格驱动。
- **经典实现**(Quantpedia):10 板块、按 12 月动量排序、取前 3 等权、月度再平衡。
- **RRG(Relative Rotation Graph)**:Julius de Kempenaer ~2004-05 提出,把"相对强度趋势"(RS-Ratio,x 轴)与"相对强度的动量/变速"(RS-Momentum,y 轴)放在以 (100,100) 为中心的四象限里,资产**理想上顺时针**轮动:Leading(强且加速)→ Weakening(强但减速)→ Lagging(弱且减速)→ Improving(弱但加速)→ 回 Leading(高可信度,定义)[StockCharts ChartSchool;relativerotationgraphs.com]。

### 2.3 RRG 构造公式(公开复现版,用于落地校准)
来源:StockCharts ChartSchool;BennyThadikaran/RRG-Lite Wiki(公开复现,非官方专有口径——官方 JdK 平滑细节未公开,**标:近似口径**)[github RRG-Lite;chartschool](中可信度)。
- **原始相对强度**:`RS = (板块价格 / 基准价格) × 100`(基准用 SPY/标普)。
- **RS-Ratio(趋势,归一化到 ~100)**:`RS_Ratio = 100 + (RS − SMA(RS, m)) / StdDev(RS, m)`,默认 `m = 14`(周线 14 周)。即对 RS 做滚动 z-score 后以 100 为中心。
- **RS-Momentum(变速)**:先 `ROC = (RS_t / RS_{t−k} − 1) × 100`(k 常用 52 周或较短),再同样 z-score:`RS_Mom = 100 + (ROC − SMA(ROC, m)) / StdDev(ROC, m)`。
- **象限**:RS_Ratio>100 且 RS_Mom>100 = Leading;>100 且 <100 = Weakening;<100 且 <100 = Lagging;<100 且 >100 = Improving。中心 (100,100) = 基准本身。
- **注**:官方 RRG 的具体 EMA/缩放为专有,**公开复现与官方数值会有差异**;本系统只需"象限 + 顺时针变速"的相对口径,不必复刻官方绝对值。

> 与本系统现有 `RrgChart.tsx` 的口径差异(已在文件注释中诚实标注):现有图 x 轴用 `rs`(全宇宙相对强度**分位 0-100**),y 轴用 `r63`(63 日动量 %),并以 `r63 − r126` 的箭头表示加速/减速——这是 RRG 的**近似**,不是 JdK RS-Ratio/RS-Momentum 的 z-score 口径。两者方向一致(右上=强且升),但绝对值不可比。落地时若要更贴近 RRG,见 §6。

---

## 3. 实证有效性证据(带来源可信度)

### 3.1 周期相位轮动:无 alpha(高权重证据)
- **Molchanov & Stangl,《The Myth of (Business Cycle) Sector Rotation》**(AUT 工作论文;发表为 Molchanov, *Int. J. of Finance & Economics*, 2024):
  - **核心结论**:按周期相位轮动**全面跑输**——Sharpe、市场择时、以及此前文献报告的轮动策略,均不如市场;基于三因子/四因子,**无任何行业显著超额,只有显著跑输的行业**(中-高可信度;已发表,但 PDF 为作者非盲版,数字以检索摘要为准,**部分具体数值未逐一核实原文**)。
  - **数量级**(检索摘要):早/中扩张期"应涨"行业实际相对市场约 **−0.05%/月**;Stage I / II 轮动 alpha **−5.3% / −1.0%**;NAVFX 类轮动基金 2010-2022 年化跑输 S&P 500 **~8.1%**。
  - 来源:https://acfr.aut.ac.nz/__data/assets/pdf_file/0005/294287/The-Myth-of-Sector-Rotation-non-blind.pdf ;https://onlinelibrary.wiley.com/doi/full/10.1002/ijfe.2882 (Wiley 正式版**付费墙**,摘要经检索获得,正文未核实)。
- **Stangl(早期工作论文,Sector Rotation over Business-Cycles)**:同一作者线,结论一致——"板块轮动可行"的流行信念"至多只是边际正确";板块回报在周期不同点可预测,与有效市场基本假设相悖(中可信度)[citeseerx]。
- **机制解释**(为何无 alpha):相位识别滞后(NBER 事后定相);市场提前轮动;要赚钱需持续优于共识地预测宏观——强假设。

### 3.2 板块动量 / 相对强弱:正记录但脆弱(中等权重证据)
- **Quantpedia Sector Momentum Rotational System**:1928-2009,10 板块取 12 月动量前 3、月度、等权:**CAGR 13.94%、Sharpe 0.54、MaxDD −46.29%、年化超 B&H ~+4%**(中可信度,长样本含大萧条、月度换手高、扣成本不充分)[quantpedia.com]。
- **再平衡频率**:多研究指向**季度**为甜点(月度换手过高、年度太迟钝),季度版能产生统计显著的风险调整收益(中可信度,含近期 ML 类研究,需独立复现)[MDPI 2026 TSX60 综述]。
- **成本结构(关键)**:个股层面 momentum"赚的恰是高交易成本的股票",净化后利润大缩;**板块 ETF 层面价差远低于盈亏平衡成本**,故板块动量比个股动量更可净落地(中可信度)[Quantpedia 注;Lesmond/Korajczyk 文献线,未逐一核实]。

### 3.3 集中度 / 均值回归:长期尾部风险(中-高权重)
- **当前集中度**:IT 板块权重 ~**31.6%(2025-05)→ ~32.3%**,逼近 2000-08 峰值 **~33.6%**;top-10 ~**40%**,NVDA 单一 ~**8%**(中-高可信度,机构口径)[SSGA;MacroMicro;DoubleLine]。
- **冠军生命周期**:Bridgewater《The Life Cycle of Market Champions》——随后 10-20 年约**半数冠军跑输并跌出前 15**,长期"几乎所有冠军被取代"(创造性破坏)(中-高可信度)[bridgewater.com]。
- **集中度均值回归的可操作含义**:集中度**高且下行**时,**等权常大幅跑赢市值权重**(Barclays;一般指数数学)(中可信度)[Barclays 2025;Research Affiliates 类论证]。
- **估值校准(降低恐慌系数)**:2000 年 IT 峰值 ~50x NTM P/E;今日 tech 估值显著低于当年(约低 ~69%),即**集中度像 2000,但估值不像**——尾部风险真实但非"等同 2000 崩盘"(中可信度)[SSGA]。

---

## 4. 扣成本 / 过拟合 / 前视(诚实账)

### 4.1 成本账(为什么择时轮动赔钱)
- **换手**:周期相位轮动每次相位切换是全板块腾挪;板块动量月度版换手亦高。每次双边换手吃 5-20+ bps(ETF 价差 + 冲击),一年多次即吞掉个位数百分点——与 NAVFX ~8.1%/年的跑输方向一致。
- **解药**:① 降频到**季度**;② 用**带宽/缓冲**(只有当板块越过明显阈值才动,避免边界抖动反复交易);③ 用**倾斜而非全押**(目标权重 ±5-10pp,而非 0/1 切换),把换手压到最低。

### 4.2 过拟合签名(必须防的坑)
- **相位定义自由度**:用 4 相位 × 11 板块 × 多种动量窗 × 多种再平衡频率,组合爆炸,极易挑出"历史最优"——这是经典 PBO 温床。
- **NBER 事后定相 = 前视泄漏**:回测里若用"已知是衰退"的标签买防御板块,等于偷看未来。**必须用 real-time 可得的相位代理**(如失业率趋势、收益率曲线、PMI 的当时值),且接受其滞后。
- **样本期**:1928-2009 含大萧条/二战,与今日市场结构差异巨大;近 15 年(科技主导)板块离散度与相关结构已变。
- **纪律**:对任何"轮动倾斜版"用 **Deflated Sharpe / CSCV-PBO / t>3** 复测,**历史毛收益默认打 3-5 折**作为实盘预期(本系统纪律)。

### 4.3 前视清单(落地时逐条勾)
- [ ] 相位/动量信号只用截至 t 日可得数据(无未来收益、无事后 NBER 标签)。
- [ ] 再平衡在信号日**之后**的可执行价成交(非信号日收盘)。
- [ ] 板块成分用**当时**的 GICS 映射(`sector_map.json` 是当前快照,历史回测需 PIT 成分,否则有幸存者/重分类偏差)。
- [ ] 成本模型含价差 + 冲击,且对换手敏感。

---

## 5. 数据与可得性(免费优先)

### 5.1 板块代理:两条路
1. **SPDR Select Sector ETF(11 个 GICS 板块)** — 推荐做 RRG/动量的板块代理(流动、价差窄、容量大):
   - XLC 通讯服务 / XLY 可选消费 / XLP 必需消费 / XLE 能源 / XLF 金融 / XLV 医疗 / XLI 工业 / XLB 原材料 / XLRE 房地产 / XLK 信息科技 / XLU 公用事业(高可信度)[SSGA;stockanalysis.com]。
   - 注:Select Sector 体系把 GICS 11 板块**装进 11 只 ETF**,但历史上通讯服务(XLC)2018 年才从科技/可选消费拆出——长回测需注意板块定义变更(PIT)。
2. **板块等权代理(用本系统已有 `sector_map.json`)** — 把 S&P 成分按 GICS 分组、组内等权(或市值权重),自建 11 条板块净值。优点:免费、可控、可做 PIT;缺点:需自己维护历史成分。

### 5.2 免费历史数据源
- **Stooq**(`stooq.com`,日线 CSV,含 XLK 等 ETF):本系统其它脚本风格可直接 GET CSV,无 key(中可信度,免费、覆盖 ETF,偶有缺口/复权口径需校验)。
- **Yahoo Finance**(非官方端点):11 只 SPDR 日/周/月线,回溯至发行日(中可信度,口径需校验,ToS 灰区)。
- **StockCharts**:对较新板块用模型回填近似历史(中可信度,**近似值,非真实成交**,只宜参考)。
- **GICS 分类**:本系统 `backtest/sector_map.json` 已是 ticker→GICS sector 的现成映射(当前快照);MSCI/S&P 官方 GICS 为付费,免费可用现有快照 + ETF 成分公开披露交叉校验。

### 5.3 与本系统现状对接
- `backtest/sector_map.json`:~500 个 ticker → 11 GICS sector(当前快照,**非 PIT**)。
- `backtest/statarb.py`:已支持传入 `sector_map`,默认读 `sector_map.json` 做行业回归(stat-arb 腿)——板块层数据管道已存在,可复用。
- `scripts/daily_screener.py`:已为每个 symbol 算 `rs`(0.4·r63+0.2·r126+0.2·r189+0.2·r252 的全宇宙分位)、`r63/r126/r252`——**板块级 RRG 所需的个股动量已现成**,只差"按 sector 聚合"。
- `frontend/components/RrgChart.tsx`:已渲染个股 RRG 近似(x=rs 分位,y=r63%,箭头=r63−r126 加速度)。

---

## 6. 落地到本系统(RRG 倾斜 / 脚本 / 验证)

### 6.1 设计原则(由 §3 证据推导)
- **不押周期相位**(无 alpha、前视风险),**改做相对强弱倾斜**(动量是真因子)。
- **季度再平衡 + 带宽缓冲 + 倾斜(非全押)**,把换手成本压到最低。
- **板块上限**(对冲集中度均值回归尾部):任一板块目标权重 ≤ 基准权重 + 上限(如 +8pp),或设硬顶(如单板块 ≤ 25%)。
- **诚实退路**:倾斜版若净·扣成本不显著胜等权/市值,**退回等权 + 板块上限**。

### 6.2 板块级 RRG(最小落地)
把现有个股 `rs/r63/r126` 按 `sector_map.json` 聚合成 11 个板块点,喂给现有 `RrgChart`:

```python
# scripts/sector_rrg.py(新脚本,只读现有 screener 输出 + sector_map.json,产出板块级 RRG JSON)
# 口径:沿用 daily_screener 的 rs(全宇宙分位)/r63/r126,按 GICS sector 取中位数聚合。
# 诚实标注:这是 RRG 近似(分位+动量%),非 JdK RS-Ratio/RS-Momentum z-score 口径。
import json, statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
sector_map = json.load(open(HERE.parent / "backtest" / "sector_map.json"))
ranks = json.load(open(HERE.parent / "frontend/public/feed/.../daily_ranks.json"))  # 按实际路径接

buckets: dict[str, list[dict]] = {}
for sym, r in ranks.items():
    sec = sector_map.get(sym)
    if not sec or r.get("rs") is None or r.get("r63") is None:
        continue
    buckets.setdefault(sec, []).append(r)

COLOR = {"Information Technology": "#4c8dff", "Financials": "#26a69a", "Energy": "#ef5350"}  # ...补全
out = []
for sec, rows in buckets.items():
    rs = st.median(x["rs"] for x in rows)
    r63 = st.median(x["r63"] for x in rows)
    r126 = st.median(x["r126"] for x in rows if x.get("r126") is not None) if any(x.get("r126") is not None for x in rows) else None
    out.append({"symbol": sec, "name": sec, "rs": round(rs, 1), "r63": round(r63, 1),
                "r126": (round(r126, 1) if r126 is not None else None), "color": COLOR.get(sec, "#888")})
json.dump(out, open(HERE.parent / "frontend/public/feed/sector_rrg.json", "w"), ensure_ascii=False)
```

- 前端复用 `RrgChart`:`<RrgChart items={sectorRrg} />`(`RrgItem` 接口已兼容:symbol/name/rs/r63/r126/color)。
- **更贴近 JdK 的可选升级**:若想要真 RS-Ratio/RS-Momentum,用 §2.3 公式对 11 只 SPDR ETF 价格 vs SPY 直接算(需 ETF 日线;Stooq 可取),再把 x=RS_Ratio、y=RS_Mom 映射进同一图——但要**新加口径标注**,不要和现有分位口径混用。

### 6.3 倾斜配置脚本(季度、带宽、上限)
```python
# scripts/sector_tilt.py(新脚本,产出建议板块权重,供看板展示;不自动下单)
# 基准:11 板块基准权重 base_w(可用市值或等权 1/11)。
# 倾斜:Leading/Improving 象限 +tilt,Lagging −tilt;带宽缓冲避免边界抖动;板块上限封顶。
def sector_tilt(rrg: list[dict], base_w: dict, tilt=0.05, cap=0.25, band=5.0):
    w = dict(base_w)
    for s in rrg:
        rs, mom = s["rs"], s["r63"]               # rs 分位>50 视为强;mom>0 视为加速(近似象限)
        if rs > 50 + band and mom > 0:            # Leading
            w[s["symbol"]] = w.get(s["symbol"], 0) + tilt
        elif rs < 50 - band and mom < 0:          # Lagging
            w[s["symbol"]] = max(0.0, w.get(s["symbol"], 0) - tilt)
    w = {k: min(v, cap) for k, v in w.items()}    # 板块上限
    tot = sum(w.values())
    return {k: round(v / tot, 4) for k, v in w.items()}  # 归一
```
- **季度执行**:只在季度末重算并应用;季度内不动(降换手)。
- **带宽 `band`**:象限边界 ±5 分位内不触发,防抖。
- **上限 `cap`**:对科技集中度上尾部的显式约束(§3.3)。

### 6.4 验证(本系统纪律,决定是否上线)
对照实验,**净·扣成本**:
1. **基准腿**:等权 11 板块 + 季度再平衡;市值权重 S&P(买入持有)。
2. **倾斜腿**:§6.3 的 RRG 倾斜 + 季度 + 带宽 + 上限。
3. **指标**:CAGR、Sharpe、MaxDD、换手率、**扣成本后超额**、年度命中率;并跑 **Deflated Sharpe / CSCV-PBO**,要求 **t > 3** 且 PBO 低。
4. **成本模型**:ETF 双边价差 + 冲击,按实际换手计提。
5. **PIT**:回测用当时 GICS 成分(若只有当前快照,**明确标注为近似、有重分类偏差**)。
6. **判定**:倾斜腿若扣成本后**不显著**胜等权,则**不上线**,看板只展示板块 RRG 作为观察工具,配置退回"等权 + 板块上限"。

### 6.5 推荐落地形态(诚实版)
- **主用**:板块 RRG 作为**观察/风险监控**面板(集中度、相对强弱、谁在转弱)。
- **配置**:在等权/市值基准上做**小幅 RRG 倾斜(±5-10pp)+ 板块上限 + 季度再平衡**,且仅在 §6.4 验证显著时启用。
- **不做**:基于"现在是 X 周期"的相位全押(§3.1 证据:无 alpha + 前视)。

---

## 7. 风险与反方(对自己开火)

1. **动量也会失效/崩溃**:Quantpedia 版 MaxDD −46%;momentum crash(2009 反弹、风格急转)会在最坏时点重伤倾斜腿。→ 倾斜幅度要小、要有板块上限与防御腿。
2. **板块定义会变(GICS 重分类)**:2018 通讯服务拆分、房地产 2016 独立——历史回测若不 PIT,板块净值不可比,易造假阳性。
3. **集中度"均值回归"可能很久不来**:科技集中已逼近 2000 峰值数年仍在走高;"逆集中度"过早 = 长期跑输。→ 用**上限约束**而非**做空/重仓逆向**,只削尾部不赌反转时点。
4. **RRG 是描述性工具,不是预测器**:象限顺时针轮动是"理想化"模式,实盘常不规则、会原地打转或逆时针;不可把"进入 Leading"当必赚信号(StockCharts 自述"并非总是完美圆形")。
5. **本系统现有口径是近似**:`RrgChart` 的 rs/r63 不是 JdK z-score;聚合到板块再取中位数又叠加一层近似。结论方向可用,绝对阈值不可硬信。
6. **单只基金/单一区间证据弱**:NAVFX 8.1%/年跑输是单基金、单窗口,**不能外推为"所有轮动基金都差"**,但与学术因子结论同向,作为佐证而非铁证。
7. **付费墙正文未核实**:Wiley 2024 正式版数字以检索摘要为准,**部分具体数值未逐一核实原文**(已标)。
8. **反方观点(为公平)**:近期(2026)部分 ML/季度再平衡研究称季度板块轮动有显著风险调整收益——但多为近期、可能过拟合、未充分独立复现,**默认打折,等独立验证**。

---

## 8. 参考来源(URL + 可信度)

**周期轮动实证(核心)**
- Molchanov, A. & Stangl, J.,《The Myth of (Business Cycle) Sector Rotation》,AUT 工作论文(非盲版 PDF):https://acfr.aut.ac.nz/__data/assets/pdf_file/0005/294287/The-Myth-of-Sector-Rotation-non-blind.pdf — **中-高**(PDF 为二进制,正文未逐字提取,数字依检索摘要)。
- Molchanov, A.,《The myth of business cycle sector rotation》,*Int. J. of Finance & Economics*, 2024,Wiley:https://onlinelibrary.wiley.com/doi/full/10.1002/ijfe.2882 — **中-高**(已发表;**付费墙,正文未核实**)。
- Stangl, J.,《Sector Rotation over Business-Cycles》(工作论文),citeseerx:https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=671041c161b6ebec6f4ef01d0aa3db66426a1d0b — **中**(工作论文)。

**Fidelity 周期模型(被评对象)**
- Fidelity,《An introduction to sector rotation strategies》:https://www.fidelity.com/learning-center/trading-investing/markets-sectors/intro-sector-rotation-strats — **中**(机构教育材料,利益相关;含其自身免责声明)。
- Fidelity,《The Business Cycle Approach to Equity Sector Investing》(PDF):https://www.fidelity.com/webcontent/ap101883-markets_sectors-content/21.01.0/business_cycle/Business_Cycle_Sector_Approach_2020.pdf — **中**(同上)。

**板块动量 / 成本 / 再平衡**
- Quantpedia,《Sector Momentum - Rotational System》:https://quantpedia.com/strategies/sector-momentum-rotational-system — **中**(策略库,长样本含大萧条、扣成本不充分)。
- MDPI 2026,《Sector Rotation Strategies in the TSX 60 …(2000–2025)》:https://www.mdpi.com/1911-8074/19/1/70 — **中-低**(近期、ML 类、需独立复现)。
- ResearchGate,《Transaction Costs, Trading Volume and Momentum Strategies》:https://www.researchgate.net/publication/314324454 — **中**(摘要,正文未核实)。

**RRG 构造**
- StockCharts ChartSchool,《Relative Rotation Graphs (RRG Charts)》:https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts — **高**(定义/象限)。
- RelativeRotationGraphs.com,《Construction of Relative Rotation Graphs》:https://www.relativerotationgraphs.com/blog/resources/construction-of-relative-rotation-graphs — **中**(官方但未公开数值细节)。
- BennyThadikaran/RRG-Lite Wiki,《RS-ratio and Momentum calculations》:https://github.com/BennyThadikaran/RRG-Lite/wiki/RS-ratio-and-Momentum-calculations — **中**(开源复现,非官方专有口径)。

**集中度 / 均值回归**
- Bridgewater,《The Life Cycle of Market Champions》:https://www.bridgewater.com/research-and-insights/the-life-cycle-of-market-champions — **中-高**。
- SSGA / State Street《Mind on the Market》《Sector Tracker》:https://www.ssga.com/us/en/institutional/insights/mind-on-the-market-17-november-2025 — **中-高**(权重/估值数据)。
- DoubleLine,《Sector Concentration in the S&P 500》:https://doubleline.com/markets-insights/sector-concentration-in-the-sp-500-digital-versus-physical-sectors/ — **中**。
- Barclays Private Bank,《Market concentration — is it really an issue?》(2025-09):https://privatebank.barclays.com/insights/market-perspectives-september-09-2025/market-concentration-is-it-really-an-issue/ — **中**。
- MacroMicro,《S&P 500 Weightings by GICS Sector (Monthly)》:https://en.macromicro.me/collections/34/us-stock-relative/121244/sp-500-gics-sectors-weightings-monthly — **中**(数据聚合)。

**免费数据 / 板块 ETF**
- StockAnalysis,《11 SPDR Sector ETFs》:https://stockanalysis.com/list/sector-etfs/ — **高**(清单)。
- SSGA Select Sector ETFs:https://www.ssga.com/us/en/intermediary/capabilities/equities/sector-investing/select-sector-etfs — **高**(发行方)。
- Stooq(免费日线 CSV,含 ETF):https://stooq.com — **中**(免费,口径/缺口需校验)。
- StockCharts 历史板块数据说明:https://help.stockcharts.com/data-and-ticker-symbols/data-availability/historical-data/stockcharts-historical-sector-data — **中**(部分为模型回填近似)。

---

*未核实清单:Wiley 2024 正文具体数字(付费墙);Molchanov-Stangl PDF 内 Sharpe/alpha 逐项(二进制未提取,依检索摘要);NAVFX 8.1%/年跑输的精确区间与口径;MDPI 2026 与各 momentum 成本论文的正文。以上均标"中"或更低,落地前应以原文/自建回测复核。本报告所有历史毛收益默认打 3-5 折作为实盘预期(本系统纪律)。*
