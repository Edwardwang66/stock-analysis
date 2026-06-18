# 多因子整合:合成(integrated)vs 顺序筛选(mixing/screening)— 长期投资深度调研

> 目的:为本系统的**长期腿(持有期数月至数年)**决定一件事——已有的价值/质量/动量/低波等因子,应该**先合成为单一综合 z-score 再选股(integrated)**,还是**各因子分别建组合再加总(mixing)**,或**顺序筛选(先价值再质量)**?给出可落地的综合打分公式 + 脚本骨架 + 验证纪律。
> 方法:fan-out 检索(AQR "Long-Only Style Investing" / Ghayur-Heaney-Platt FAJ 2018 反方 / 标准化中性化最佳实践 / 经典四因子组合 / Piotroski 交互 / 等权 vs 优化权重 DeMiguel)→ 一手/二手交叉核验 → 合成。
> 日期:2026-06-18。每条关键结论标注**来源 URL + 可信度(高/中/低)**;无法核实者标"未核实"。
> 立场承袭房子风格:**诚实可证伪;净·扣成本是唯一货币;标注样本内/前视/幸存者偏差;免费/PIT 数据优先;默认历史毛收益打 3-5 折。**

---

## 1) TL;DR(执行摘要)

1. **"先合后选"(integrated)对长期多因子腿是默认正确选择,但优势没有营销叙事那么干净——它是一个被两篇顶刊互相打脸的活议题。** AQR(Fitzgibbons-Friedman-Pomorski-Serban,JOI Winter 2017)在 MSCI World 类宇宙、1993-02 至 2015-12 的回测里,integrated 比 portfolio-mix **多约 1% p.a. 超额收益、信息比率高约 40%、换手降约 5-10%**;机制是 integrated 自动避开"在一个风格上很好、在另一个上很差"的相互抵消股。[高｜AQR 2017,二手交叉确认]

2. **反方同样是顶刊且更精细:Ghayur-Heaney-Platt(FAJ 2018)发现在低-中目标因子暴露下,portfolio-mix 反而胜出(IR 0.89 vs signal-blend 0.59,+51%),只有在高暴露下 integrated 才反超(0.61 vs 0.54)。** 关键洞见:mix 之所以在低暴露区赢,正是因为它**保留了**那些"相互抵消"的股票,而这些股票降低了主动风险、提升了主动收益(interaction effect 的另一面)。→ AQR 与 GHP 的分歧不是谁错,而是**取决于你想要的跟踪误差/暴露强度**。[高｜Ghayur-Heaney-Platt FAJ 2018]

3. **对本系统这条"低换手、数月-数年持有、温和暴露、不追极端集中"的长期腿,证据天平偏向 integrated,但要按 mix 的教训做修正:不要机械剔除所有抵消股。** 落地结论:**用单一综合 z-score 排序(integrated 主干),但保留温和暴露 + 行业内选股,而非追求极端综合分**——这恰好落在 GHP 两条曲线交叉点附近,两法差异最小、最稳健。[中-高｜两文综合推断]

4. **顺序筛选(screening,如"先筛便宜 30% 再在其中筛质量")是 mixing 的极端、有损版本:它把连续信息二值化,丢弃了"中等便宜但质量极高"这类被合成法奖励的股票。** 顺序筛选只在**条件提纯**场景有正当性(见第 4 节 Piotroski),不应作为多因子整合的主干。[中-高｜机制论证 + Piotroski 证据]

5. **标准化的标准件是:横截面 winsorize(±3σ 或 1/99 分位)→ z-score →(可选)行业 + 规模中性化 → 各因子等权相加 → 再 z-score。** 本系统 `backtest/factor_pipeline.py` 已实现这条管线(`winsorize(3σ)→standardize→neutralize[行业哑变量+size]`),综合打分只是把它从"单因子评估"推广到"多因子加总"。[高｜QuantRocket / SAS / 本仓代码]

6. **rank-then-z(先排名再标准化)比裸 z-score 更稳健,对厚尾/异常会计值不敏感——这是 QMJ、AQR 实践的默认。** 本仓 `factor_factory.py` 的 `_transform` 已支持 `rank` 与 `z` 两档(`fx.zscore(fx.rankdata(x))`),长期腿建议默认用 **rank-z**。[高｜AFP QMJ;本仓代码交叉确认]

7. **经典组合 = 价值 + 质量 + 动量 + 低波,等权,长期证据扎实且互补:质量与价值/动量低/负相关(质量对市场 beta -0.59、对 size -0.50、对价值 0.17、对动量 0.29),是天然分散器。** MSCI 50 年:动量/增强价值总收益最高(13.5% / 13.3%),但任何单因子都有多年跑输期,**分散是为了在再定价时点不被单押打死**,不是为了加 alpha。[中-高｜MSCI Factor Indexing Through the Decades]

8. **因子交互真实存在且应被利用,但用合成法(连续乘法/协同)而非顺序硬过滤来表达。** Piotroski F-Score 的价值是**在便宜股池内提纯**(剔价值陷阱),Fama-French 国际证据显示 F-Score 与"过去价格表现一致时"协同最强——即"便宜 + 基本面改善 + 有动量"三者congruent 时收益集中。合成法可用交互项 `z(value)·z(quality_delta)` 捕捉,但**交互项极易过拟合,默认不开,需 t>3 + BY-FDR 单独过门**。[中-高｜Piotroski 国际证据]

9. **不要做数据挖掘式权重优化。等权(1/N)在样本外极难被打败——DeMiguel-Garlappi-Uppal(2009)证明均值-方差及其多数扩展无法显著超越 1/N,因为估计误差吞掉了理论增益。** 因子权重同理:**默认等权,任何非等权必须有事前经济理由 + 样本外验证,且把权重搜索次数计入 BY-FDR 试验预算**。[高｜DeMiguel-Garlappi-Uppal RFS 2009]

10. **一句话落地:本系统把已有因子(价值/质量/动量/低波)各自 rank-z + 行业中性化,等权相加成单一 `LongScore`,在行业内做温和暴露排序;交互项与非等权权重一律走影子(shadow)+ 六门控,不直接进生产。**

---

## 2) integrated vs mixing:定义 + 证据(含可信度)

### 2.1 三种整合方式的精确定义

| 方式 | 别名 | 流程 | 信息保真度 |
|---|---|---|---|
| **Integrated / signal blending** | "先合后选"、bottom-up、composite scoring | 每只股票在每个因子上打分(z 或 rank-z)→ 加权相加成单一综合分 → 按综合分一次性选股/配权 | 高(连续、全维同时评估) |
| **Mixing / portfolio blending** | "分别建组合再加总"、portfolio-mix、top-down | 每个因子各自建一个子组合 → 子组合按权重加总 | 中(子组合内部丢失跨因子交互) |
| **Sequential screening** | 顺序筛选、漏斗 | 先按因子 A 筛 top X% → 在子集内按因子 B 筛 → … | 低(每步二值化、丢弃连续信息) |

**核心张力一句话:** integrated **惩罚**"一好一差"的相互抵消股(把它们的综合分拉到中间、选不上);mixing **保留**它们(它们同时出现在两个子组合里)。谁更好取决于这些抵消股是"噪音"(integrated 对)还是"分散器"(mixing 对)。

### 2.2 正方:AQR "Long-Only Style Investing: Don't Just Mix, Integrate"(2017)

- **来源:** Fitzgibbons, Friedman, Pomorski, Serban,*The Journal of Investing*,Winter 2017(working paper 2016)。[一手页:https://www.aqr.com/Insights/Research/White-Papers/Long-Only-Style-Investing ｜SSRN:https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2802849]
- **宇宙/样本:** 大盘股、发达国家(大致 MSCI World),**1993-02 至 2015-12**。[高｜二手 Swedroe 转述:https://larryswedroe.substack.com/p/the-integration-of-factors-advantage]
- **关键数字(二手交叉确认,一手 PDF 为扫描/二进制未能直接解析,标"二手核实"):**
  - integrated 比 portfolio-mix **多约 +1% p.a. 超额收益**(相对 cap-weighted 基准);
  - **信息比率高约 +40%**;
  - **换手降约 5-10%**(→ 更低交易成本、更好税务效率)。[中-高｜二手 Swedroe + 多源一致;一手 PDF 未直接核实]
- **机制:** mixing 会持有"在一个风格上极好、在另一个上极差"的股票,造成"内部冲突",稀释每个溢价;integrated 同时在所有维度评估每只股票,自动避开抵消股、偏向"全维温和正暴露"的股票。[高]
- **房子打折:** 这是 AQR 自家方法论白皮书,**作者利益相关**;样本含 2008-09、含发达国家大盘(容量友好但也最被套利);1% p.a. 是毛口径概念,扣实盘成本后净增益更小。当作"方向证据"而非"幅度承诺"。

### 2.3 反方:Ghayur-Heaney-Platt(FAJ 2018)— 在低暴露区 mix 反而赢

- **来源:** Ghayur, Heaney, Platt,"Comparing Portfolio Blending and Signal Blending When Constructing Multifactor Portfolios",*Financial Analysts Journal* 2018。[https://rpc.cfainstitute.org/research/financial-analysts-journal/2018/ip-v3-n1-11-comparing-portfolio-blending ｜CFA Institute,高可信度独立同行评审]
- **关键数字(一手页直接核实):**
  - **低-中因子暴露:portfolio-blend(mix)IR = 0.89 vs signal-blend(integrated)IR = 0.59**(mix +51%);
  - **高因子暴露:signal-blend IR = 0.61 vs portfolio-blend 0.54**(integrated 反超);
  - 机制:低 TE 时,**只被 mix 持有的"抵消股"降低了主动风险、提升主动收益**(interaction effect);随 TE 升高,两组合重叠度下降、个股特异风险压过交互收益,integrated 的分散优势胜出。[高]
- **作者点评:** "投资者通常不会在高因子暴露下实施多因子策略"——即**现实场景多落在 mix 占优的低-中暴露区**。[高]

### 2.4 如何调和两文(本系统的判断)

- 两文**不矛盾**:AQR 强调避开抵消股的好处,GHP 指出抵消股在低 TE 时是分散器。差异源于**目标暴露强度**与**抵消股是噪音还是分散器**的假设。
- **本系统长期腿的定位:** 低换手、温和暴露、行业内分散、不追极端综合分、不追高 TE。这正好落在**两条曲线交叉点附近**——此处 integrated 与 mix 差异最小,选哪个都稳健。
- **工程结论:选 integrated 作主干**(实现简单、单一可审计排序分、天然降换手、与本仓 `factor_pipeline` 一脉相承),**但吸收 mix 的教训:不机械剔除抵消股,保留温和暴露 + 行业中性**,避免把组合推向 GHP 警告的"高暴露 + 高特异风险"区。

### 2.5 顺序筛选的信息损失(为何不作主干)

- 顺序筛选 = mixing 的二值化极端版。"先筛便宜 30% → 再筛质量 top 50%"会**丢弃**:中等便宜(第 35 百分位)但质量顶级的股票——而 integrated 会因其综合分高而选中它。
- 每一步的硬阈值都是一个**隐藏的自由参数**(为何是 30% 不是 25%?),极易事后调参过拟合;且阈值附近的股票对阈值微小变化高度敏感(不稳健)。
- **唯一正当用途:条件提纯**——当因子 B 只在因子 A 的子集内有意义时(Piotroski F-Score 只在 value 池内有信号,见 §4.3)。此时顺序是**经济机制**而非调参,但仍建议用**连续交互项**而非硬阈值实现。[中-高｜机制论证]

---

## 3) 标准化 / 中性化方法(可落地管线)

> 目标:得到横截面可比、对厚尾/会计异常不敏感、行业/规模偏差被剔除的信号,再加总成综合分。本仓 `backtest/factor_pipeline.py` 已实现核心步骤。

### 3.1 标准管线(每个调仓日、每个因子,横截面执行)

```
raw_i                                  # 因子原始值(如 EV/EBIT 倒数、GP/A、r12_1、−vol)
 → winsorize(±3σ 或 1/99 分位)          # 削极端值/会计异常(本仓:np.clip(x, m−3s, m+3s))
 → [可选] rank → z                      # rank-then-z:对厚尾更稳健,QMJ/AQR 默认
 → standardize: z=(x−μ)/σ               # 横截面均值0、标准差1(本仓 standardize())
 → [可选] neutralize(行业哑变量 + size)  # OLS 残差再标准化(本仓 neutralize())
```

本仓现成实现(`factor_pipeline.py`):
- `winsorize(x, n_std=3.0)`:`np.clip(x, mean−3σ, mean+3σ)`。
- `standardize(x)`:`(x−mean)/std`,std=0 时返回 0 向量(防除零)。
- `neutralize(x, sector_ids, size)`:对 `[行业哑变量 + standardize(size) + 截距]` 做 OLS,返回**标准化残差**。
- `preprocess(...) = neutralize(standardize(winsorize(raw,3)), ...)`。

### 3.2 关键方法选择(均有证据/惯例支撑)

- **winsorize vs trim:** winsorize(截断到分位值)优于直接删除(trim),保留样本量;阈值常用 ±3σ 或 1%/99% 或 5%/95%。[中｜SAS "Winsorization good/bad/ugly":https://blogs.sas.com/content/iml/2017/02/08/winsorization-good-bad-and-ugly.html]
- **rank-z vs 裸 z:** rank-z(先排名再 z)抹平厚尾、对单个异常会计值免疫,代价是丢失"差距幅度"信息。长期基本面因子(易有会计异常)**默认 rank-z**;价格类动量因子可用裸 z。[中-高｜AFP QMJ 实践]
- **行业中性化:** 去均值(demean)只剔除"某行业整体偏高/低";z-score(行业内标准化)**额外**剔除"某行业方差更大"。本仓 `neutralize` 用行业哑变量 OLS = 去均值口径;若要更强,可改行业内 z。[高｜QuantRocket "Sector Neutralization":https://www.quantrocket.com/blog/sector-neutralization/]
- **规模中性化:** 把 `size`(log 市值)作为回归自变量,剔除因子的市值偏向(很多价值/质量因子隐含小盘暴露)。本仓已做。[高｜本仓代码]
- **是否中性化是一个赌注,不是免费午餐:** 行业中性化会**剔除"行业层面的价值/动量"alpha**(如整个能源板块便宜)。长期腿若相信跨行业再定价,可对部分因子**只做规模中性、不做行业中性**。本仓 `preprocess(do_neutralize=...)` 已留开关。诚实标注:中性化与否需各自回测,不可拍脑袋。[中]

### 3.3 缺失值与对齐

- 缺失因子值:横截面中性插补(填该日横截面均值=z 后填 0),而非剔除整只股票(否则丢失其他因子信息)。
- PIT 对齐:所有基本面字段必须用**财报可得日**而非财报期末日(本仓有 `backtest/pit_membership.py` / `study_pit_bite.py`),否则前视污染综合分。[高｜本仓纪律]

---

## 4) 经典组合权重与因子交互

### 4.1 经典四件套:价值 + 质量 + 动量 + 低波

- **为何是这四个:** 低/负相关 → 分散。质量对市场 beta **−0.59**、对 size **−0.50**、对价值 **0.17**、对动量 **0.29**(MSCI 口径),价值与动量长期负相关(经典互补)。组合后效率前沿显著优于任一单因子。[中-高｜MSCI Factor Indexing Through the Decades:https://www.msci.com/research-and-insights ｜数字为二手转述,标"二手核实"]
- **长期幅度(MSCI 50 年,毛口径、样本内):** 动量 ~13.5%、增强价值 ~13.3% 总收益领先;质量溢价 1964-2023 约 **4.7% p.a.、σ 9.9、Sharpe ~0.47**。**任何单因子都有多年(甚至十几年)跑输期**——见 `factor-valuation-timing.md` 中 HML 2007-2020 回撤 ~54.8%/13.5 年。[中｜MSCI/AQR 二手;打 3-5 折]
- **权重:默认等权(各因子 1/4)。** 见 §7 反方:非等权权重优化是过拟合重灾区。

### 4.2 因子交互:协同效应真实存在

- **"便宜 + 改善 + 有动量"的协同:** 不是三个独立赌注相加,而是有正交互——基本面改善 + 价格动量一致(congruent)时,收益集中且更可信(市场对基本面变化反应不足)。[中-高｜Fama-French/Piotroski 国际证据:https://link.springer.com/article/10.1057/s41260-020-00157-2]
- **但交互项 = 自由参数:** `z(value)·z(quality)` 这类乘法项会指数级放大过拟合空间。**默认综合分不含交互项(纯加性)**;若要加,单个交互项必须独立过 BY-FDR + |t|≥3 + 净成本门,且计入试验预算。

### 4.3 Piotroski F-Score:条件提纯的典范(顺序筛选的正当用法)

- **原始证据:** Piotroski(2000),1976-1996,在**高 B/M(便宜)子集内**用 F-Score(9 项二值基本面健康分)做多高分(F≥8)、做空低分(F≤1),高低价差 ~**23%/年**(样本内、小盘、高 B/M 子集)。[高｜见本仓 `value-investing-frameworks.md` §2.3]
- **关键洞见:F-Score 脱离便宜股池单用,信号弱。** 它是**条件过滤器**(在 value universe 内提纯,剔价值陷阱),不是独立 alpha 源。这是"顺序/条件"逻辑唯一有经济机制支撑的场景。[高]
- **国际证据(Springer JAM 2020):** F-Score 与"过去价格表现一致"时交互最强——便宜 + 基本面强 + 价格也涨 三者一致时收益集中。[中-高｜https://link.springer.com/article/10.1057/s41260-020-00157-2]
- **落地映射:** 在 integrated 主干里,F-Score 可作为**价值因子的质量提纯项**(把 F-Score 的 z 加进 value 桶,或作 value×quality 交互),**而非**作为独立的顺序硬过滤步骤。

---

## 5) 数据与可得性

| 因子桶 | 字段(Compustat/SEC 口径) | PIT 来源 | 本系统现状 |
|---|---|---|---|
| 价值 | EV/EBIT、FCF/EV、B/M(扣无形)、E/P | SEC EDGAR XBRL(`sec-edgar-xbrl-fundamentals.md`) | 部分;EV/EBIT、FCF/EV 优先(不依赖账面净值) |
| 质量 | GP/A、现金型经营利润、ROIC−WACC、低应计、F-Score | 同上 + Ball 现金利润口径 | 见 `quality-moat-factors.md` / `accruals-earnings-quality.md` |
| 动量 | r12_1(过去 12 月跳过最近 1 月) | 价格(本仓 `factory` 已有 mom_12_1) | 已有 |
| 低波 | 过去 63/252 日实现波动、低 beta | 价格(本仓已有 lowvol/vol21/vol63) | 已有 |
| 行业/规模 | GICS 行业、log 市值 | 价格 + 元数据 | 本仓 `neutralize` 已用 sector_ids + size |

- **可得性现实:** 价格类(动量/低波)即时可得且 PIT 干净;基本面类(价值/质量)受 XBRL 覆盖、财报滞后、口径不一限制——综合分的瓶颈在**基本面 PIT 对齐**,不在价格因子。
- **免费优先:** SEC EDGAR XBRL(基本面)+ 价格源,无需付费 Compustat 即可搭起四件套的最小可用版(质量/价值会略糙,需诚实标注覆盖率)。

---

## 6) 落地到本系统(综合打分公式 / 脚本 / 验证)

### 6.1 综合长期排序分 `LongScore`(integrated 主干,纯加性,等权)

对每个调仓日 t、每只在册股票 i,横截面计算:

```
# 步骤(全部横截面、PIT 对齐、t 日只用 ≤t 数据):
val_i  = preprocess( rank_z(EV/EBIT 倒数, FCF/EV, B/M⊥intangibles 的等权), sector, size )
qual_i = preprocess( rank_z(GP/A, 现金型经营利润, −应计, F-Score 的等权),      sector, size )
mom_i  = preprocess( z(r12_1),                                              sector, size )
lvol_i = preprocess( z(−vol_252),                                           sector, size )

LongScore_i = 0.25*val_i + 0.25*qual_i + 0.25*mom_i + 0.25*lvol_i   # 等权,默认
```

- **桶内**:多个原始变量先各自 rank-z(基本面)或 z(价格),等权合成桶分,再 winsorize→standardize→neutralize。
- **桶间**:四桶**等权**相加成 `LongScore`(integrated 的核心:一次性综合排序)。
- **选股/配权**:按 `LongScore` 在**行业内**做温和暴露(如行业内 top 分位超配),**不**追极端综合分(吸收 GHP 教训,避免高 TE/高特异风险区)。
- **不做**:顺序硬过滤(除 F-Score 已并入 qual 桶)、非等权桶权重、交互项(除非各自过门)。

### 6.2 脚本骨架(复用本仓 `factor_pipeline.py`,新增多因子加总)

```python
# 伪代码:扩展 factor_pipeline 的 preprocess 到多桶加总(integrated)
from backtest.factor_pipeline import winsorize, standardize, neutralize

def rank_z(x):                      # rank-then-z(基本面默认)
    from backtest.factors_xs import rankdata, zscore
    return zscore(rankdata(x))

def bucket(raw_list, use_rank=True):     # 桶内:多变量等权合成
    zs = [ (rank_z(r) if use_rank else standardize(r)) for r in raw_list ]
    return standardize(sum(zs) / len(zs))

def long_score(buckets, sector, size, weights=None):   # 桶间:等权 integrated
    w = weights or [1.0/len(buckets)]*len(buckets)      # 默认等权
    procd = [ neutralize(standardize(winsorize(b,3.0)), sector, size) for b in buckets ]
    s = sum(wi*pi for wi,pi in zip(w, procd))
    return standardize(s)                               # 单一可审计排序分

# 用法:
# val  = bucket([ev_ebit_inv, fcf_ev, bm_adj], use_rank=True)
# qual = bucket([gpa, cash_op, neg_accruals, fscore], use_rank=True)
# mom  = standardize(r12_1)          # 价格类用裸 z
# lvol = standardize(-vol_252)
# score = long_score([val, qual, mom, lvol], sector_ids, size)   # 等权 LongScore
```

- **不新建独立框架**:这是 `preprocess` 的多因子推广,沿用同一 winsorize/standardize/neutralize,审计连续。
- **rank vs z 开关**:基本面桶默认 `use_rank=True`(对接 `factor_factory._transform` 的 rank 档),价格桶用裸 z。

### 6.3 验证纪律(对接本仓六门控 / BY-FDR / 净成本)

1. **门控③ BY-FDR + |t|≥3**:`LongScore` 整体、以及任何**非等权权重方案/交互项**,都作为独立候选计入试验预算,过 Benjamini-Yekutieli 相依 FDR(q<0.10)+ |t|≥3。等权方案是 1 个试验;每尝试一组权重就是 +1 试验,**权重搜索的成本必须显式计入**(防 §7 过拟合)。
2. **门控② 增量正交 IC**:`LongScore` 必须对现有因子(mom_12_1/reversal/hi52/lowvol)做横截面回归后,**残差 IC 仍显著**——否则它只是已有因子的线性重排,无增量。本仓 `factor_factory.py` 已有此门。
3. **门控⑥ 净成本存活**:decile L/S 扣 5bp + 冲击后 IR>0;integrated 的低换手在此处兑现优势。
4. **integrated vs mixing 横评**:同一组桶,分别跑 (a) integrated 单分排序 (b) 各桶独立组合加总 (c) 顺序筛选,在 **train 段**比净 IR/换手/TE,**holdout 仅一次终检**。这是把 AQR/GHP 之争**在本系统数据上实证**,而非照搬别人结论。
5. **过拟合复测**:Deflated Sharpe / CSCV-PBO;默认历史毛收益打 3-5 折作扣成本/扣再定价后的实盘预期(本仓纪律)。
6. **PIT**:所有基本面字段走财报可得日,综合分不得含前视(`pit_membership.py` / `study_pit_bite.py`)。

---

## 7) 风险与反方(尤其权重过拟合)

1. **【最大风险】因子权重过拟合。** 一旦从等权转向"优化权重",自由度爆炸:4 桶权重 + 桶内变量权重 + 交互项 + 中性化开关 = 极易在样本内拟合出漂亮曲线、样本外崩塌。**DeMiguel-Garlappi-Uppal(RFS 2009)**:均值-方差及其多数扩展**无法显著超越 1/N**,因估计误差吞掉理论增益。[高｜https://www.researchgate.net/publication/31210252 ｜RFS,高可信度]。→ **铁律:默认等权;任何非等权须有事前经济理由 + 样本外验证 + 计入 BY-FDR 试验数。**

2. **integrated 的结论被 GHP(2018)在低暴露区证伪。** 本系统不能照抄 AQR"integrated 总是更好"——必须在自己数据上跑 integrated/mix/screening 横评(§6.3.4),按本系统实际 TE/暴露区间下结论。诚实标注:**两法孰优是数据依赖的,不是定律。**[高｜GHP FAJ 2018]

3. **中性化是赌注不是免费午餐。** 行业中性化剔除行业层面 alpha;若长期腿相信跨行业再定价(整个板块便宜),全因子行业中性会误伤。需逐因子回测中性化与否,不可一刀切。[中]

4. **AQR 1% p.a. / +40% IR 是毛口径 + 作者利益相关 + 含 1993-2015 特定样本。** 扣实盘成本、扣容量、用 2016-2026 样本外,净增益可能显著缩水。当方向证据,不当幅度承诺。一手 PDF 未直接解析,数字为二手核实。[中-高]

5. **交互项/协同是过拟合的另一入口。** "便宜且改善且有动量"听起来很美,但乘法交互项指数级放大搜索空间。默认不开;开则单独过门。[中-高]

6. **综合分掩盖 trade-off。** 高 `LongScore` 可能来自一两个桶极端、其余平庸(integrated 的已知弱点:composite 高分可能掩盖某维严重劣势)。缓解:除综合分外,**保留各桶分用于监控**,对"单桶极端拉动"的持仓做事后审查;或对单桶设软下限(但软下限本身是参数,需克制)。[中｜搜索结果机制论证]

7. **数据可得性偏差。** 基本面桶受 XBRL 覆盖/滞后限制,小盘/新股覆盖差,综合分在这些股票上由价格桶主导——需诚实标注综合分的"基本面有效覆盖率"。[中]

8. **全网回测过的公式极易过拟合到历史窗口。** 价值/质量/F-Score/动量的公开公式被反复回测,默认其近 10 年 alpha 已部分被套利;用 PIT + Deflated Sharpe 复测,毛收益打 3-5 折。[高｜本仓纪律]

---

## 8) 参考来源(URL + 可信度)

| # | 来源 | URL | 可信度 | 用途 |
|---|---|---|---|---|
| 1 | Fitzgibbons-Friedman-Pomorski-Serban, "Long-Only Style Investing: Don't Just Mix, Integrate", JOI Winter 2017(AQR) | https://www.aqr.com/Insights/Research/White-Papers/Long-Only-Style-Investing | 高(顶刊;作者利益相关,打折) | integrated 正方:+1% p.a.、+40% IR、−5~10% 换手 |
| 2 | 同上 SSRN | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2802849 | 高 | 一手 working paper |
| 3 | Swedroe, "The Integration of Factors Advantage"(转述 AQR 数字) | https://larryswedroe.substack.com/p/the-integration-of-factors-advantage | 中-高(二手,数字交叉一致) | AQR 数字 + 样本期 1993-02~2015-12 二手核实 |
| 4 | Ghayur-Heaney-Platt, "Comparing Portfolio Blending and Signal Blending", FAJ 2018 | https://rpc.cfainstitute.org/research/financial-analysts-journal/2018/ip-v3-n1-11-comparing-portfolio-blending | 高(CFA Institute,独立同行评审) | 反方:低暴露 mix 胜(IR 0.89 vs 0.59);高暴露 integrated 反超(0.61 vs 0.54) |
| 5 | Alpha Architect, "Should Investors Combine or Separate Their Factor Exposures?" | https://alphaarchitect.com/should-investors-combine-or-separate-their-factor-exposures/ | 中(独立博客;本次 WebFetch 返回 403,标"未直接核实") | AQR 结论二手讨论 |
| 6 | ThinkNewfound, "Multi-Factor: Mix or Integrate?" | https://blog.thinknewfound.com/2016/07/multi-factor-mix-integrate/ | 中(独立从业者博客) | integrated/mix 机制科普 |
| 7 | QuantRocket, "Sector Neutralization: Why It Matters and How to Use It" | https://www.quantrocket.com/blog/sector-neutralization/ | 中-高(从业者文档) | 去均值 vs 行业内 z 的区别 |
| 8 | SAS, "Winsorization: The good, the bad, and the ugly" | https://blogs.sas.com/content/iml/2017/02/08/winsorization-good-bad-and-ugly.html | 中-高 | winsorize 方法与陷阱 |
| 9 | DeMiguel-Garlappi-Uppal, "Optimal Versus Naive Diversification (1/N)", RFS 2009 | https://www.researchgate.net/publication/31210252 | 高(RFS 顶刊) | 等权稳健性;反对权重优化 |
| 10 | MSCI, "Factor Indexing Through the Decades (50 years)" | https://www.msci.com/research-and-insights(具体 PDF 见 MSCI 站内) | 中(指数厂商;数字二手核实) | 四因子长期收益、质量相关性 −0.59/−0.50/0.17/0.29 |
| 11 | Springer JAM 2020, "Piotroski's FSCORE: international evidence" | https://link.springer.com/article/10.1057/s41260-020-00157-2 | 中-高(同行评审) | F-Score 国际证据 + 与价格表现交互 |
| 12 | Piotroski 2000(经本仓 `value-investing-frameworks.md` §2.3 转述) | (见同目录文件) | 高 | F-Score 条件提纯、23%/年高低价差(样本内) |
| 13 | 本仓 `backtest/factor_pipeline.py` | 本地 | 高(一手代码) | winsorize/standardize/neutralize 现成实现 |
| 14 | 本仓 `backtest/factor_factory.py` | 本地 | 高(一手代码) | 六门控/BY-FDR/rank-z/增量正交 IC |
| 15 | CFA Institute(Smart Beta Multifactor: Mixing vs Integrating, JII) | https://www.pm-research.com/content/iijindinv/8/4/47 | 中(同行评审,未全文核实) | mixing vs integrating 方法论补充 |

> **未核实标注:** 来源 #5(WebFetch 403)、#10(MSCI 具体 PDF 链接未逐一打开,数字为搜索结果二手转述)、#15(仅摘要)。AQR 一手 PDF(JOI-LongOnlyStyleInvesting_Winter-2017.pdf)为 4.4MB 二进制,本次未能直接解析正文,其 +1% p.a./+40% IR/−5~10% 换手数字依赖二手(#3)交叉确认,标"二手核实"。

---

### 附:与本系统已有调研的衔接
- 价值桶口径与价值陷阱过滤:见 `research/long-term/value-investing-frameworks.md`、`factor-valuation-timing.md`。
- 质量桶(GP/A、现金利润、QMJ 合成架构):见 `quality-moat-factors.md`、`accruals-earnings-quality.md`。
- 低波桶:见 `low-vol-defensive.md`。动量桶:见 `long-horizon-momentum-trend.md`。
- 基本面 PIT/XBRL:见 `sec-edgar-xbrl-fundamentals.md`。
- 本报告的 `LongScore` 是上述各桶的**integrated 加总层**,不重复定义桶内公式,只定义"如何合成 + 为何 integrated + 如何验证"。
