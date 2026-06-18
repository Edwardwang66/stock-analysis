# 长周期策略回测的统计陷阱 — 方法论严谨性

> 主题:长持有期 / 低频因子回测里,**显著性如何被系统性高估**,以及本系统该用哪些修正与 checklist 把它压回去。
> 立场:诚实可证伪。"长期=更可靠"是错觉——长样本期 ≠ 长**有效独立样本**。
> 日期:2026-06-18。可信度分级:**A**=同行评审/原始论文/监管原文;**B**=从业者一手研究/高质量二手;**C**=百科/博客/营销页(仅作公式核对,不作结论依据)。
> 凡无法核实之处标注 **[未核实]**。
> 本文件只做调研产出,不改动系统其他文件、不跑 git。

---

## 1) TL;DR

- **核心错觉:20 年月度数据 ≠ 240 个独立观测。** 长持有期 + 重叠收益(overlapping returns)+ 持续型预测变量(dividend yield、估值倍数)三者叠加,使**有效独立样本量**远小于名义样本量。20 年年度收益只有 ~20 个**真正独立**的年份;若研究的是 5 年持有期,独立的"不重叠区块"只有 ~4 个。t 统计量因此被**结构性放大**,显著性虚高。
- **重叠收益的两个后果:**(1)残差强自相关 → OLS 标准误下偏 → t 偏高;(2)即使用 Newey-West / Hansen-Hodrick HAC 修正,在**重叠期相对样本长度较大**时,HAC 标准误本身仍小样本下偏(Ang/相关文献,§2)。必须同时做 HAC 修正 **且** 用区块/独立样本量来校准你对显著性的信心。
- **长周期 ≠ 更可靠,而是更脆:** Boudoukh-Richardson-Whitelaw(2008,**A**)证明:在**无可预测性的零假设下**,长horizon回归系数和 R² 本来就会随 horizon 近似线性上升——"长期系数更大、R² 更高"这个被当成"长期可预测性更强"的证据,**恰恰是无可预测性时应有的样子**。1 年 vs 5 年估计量在零假设下相关性高达 94%。
- **前视/幸存者/restatement 对长周期放大:** horizon 越长,数据偏差累积越多。survivorship-free vs biased 在 CRSP 1926–2001 上是 7.4% vs 9.0%/年(差 ~1.6%,**B**);delisting bias 约高估小盘 ~1.5%/年(Shumway 1997,**A/B**);基本面数据若用 as-restated 而非 PIT,accrual 类异象收益会被显著改变(Lyle-Siano-Yohn,**A/B**)。
- **多重检验是低频策略最大的杀手:** 因子动物园 300+(Harvey-Liu-Zhu 2016,**A**),新因子 t 门槛应 ≥3.0 而非 2.0;Deflated Sharpe Ratio(Bailey-López de Prado 2014,**A**)按试验次数 N、SR 跨试验方差、偏度峰度联合压缩门槛。低频策略 T 小,DSR 惩罚尤其狠。
- **walk-forward 在长周期切不出足够 fold:** 20 年数据、5 年训练 + 1 年测试,只能切出 ~15 个不重叠测试窗;若持有期本身是多年,fold 数掉到个位数,统计功效极低(某市场微结构研究 34 个测试期仅 12% power,**B**)。CPCV(组合净化交叉验证,López de Prado 2018)能造多条回测路径缓解,但**无法凭空造出独立信息**。
- **本系统落地(§6):** 在已有防过拟合栈(DSR、CSCV-PBO、Purged K-Fold、t>3、真 holdout、PIT 重建)之上,补三件事:(a)对所有重叠/长 horizon 统计强制 HAC + 独立样本量报告;(b)把 N(试验次数)显式登记进 DSR;(c)长周期一律用 CPCV 多路径 + block bootstrap,而非单条 walk-forward。

---

## 2) 重叠收益 / 有效样本量 + 修正公式

### 2.1 重叠收益为什么制造假显著性

构造 k 期持有收益时,相邻观测共享 k−1 期的底层收益:

```
r_t^(k) = r_{t+1} + r_{t+2} + ... + r_{t+k}
r_{t+1}^(k) = r_{t+2} + ... + r_{t+k+1}
```

相邻的 `r_t^(k)` 与 `r_{t+1}^(k)` 共享 (k−1)/k 的成分 → 构造性地引入强正自相关(MA(k−1) 结构),即使底层 `r` 完全 iid。后果:

- OLS 假设残差无自相关;重叠收益违反此假设 → **标准误下偏 → t 上偏 → 假显著**。
- 名义 N 个重叠观测里,**独立信息**只有 ~N/k 个不重叠区块。

### 2.2 有效独立样本量(effective sample size)

对正自相关序列,样本均值的方差不是 σ²/n,而是被**方差膨胀因子**放大。对相关数据(直观近似):

```
Var(Ȳ) = (σ²/n) · [1 + (n−1)ρ]        # 等相关近似(C 级,直觉用)
n_eff ≈ n / VIF,  VIF = 1 + 2·Σ_{j=1}^{n−1} (1 − j/n) ρ_j     # 一般 AR 结构
```

对**重叠 k 期收益**的实用经验法则(直觉,**[未核实]** 精确常数):重叠收益的有效独立样本 ≈ 名义样本 / k(即不重叠区块数)。把这个 n_eff 而非 n 代入你对 t 的直觉:

> **长 horizon 的"独立年"心算:** 20 年数据,持有期 H 年 → 独立不重叠观测 ≈ 20/H。H=1 → 20;H=5 → 4;H=10 → 2。任何 H≥3 的长期策略,**单一历史样本几乎无法支撑强显著性主张**——这是物理上限,不是修正能解决的。

### 2.3 HAC 修正:Newey-West vs Hansen-Hodrick

两者都是 HAC(异方差自相关一致)协方差估计,处理重叠/自相关残差:

```
V_HAC = (X'X)^{-1} · S · (X'X)^{-1}
S = Γ_0 + Σ_{j=1}^{L} w_j (Γ_j + Γ_j')      # Γ_j = lag-j 自协方差
```

- **Newey-West(1987):** 用 Bartlett 核 `w_j = 1 − j/(L+1)`,保证 S 半正定。带宽(lag)L 的常规选择:重叠 k 期收益用 **L = k 或 2k**(惯例)。
- **Hansen-Hodrick(1980):** 等权 `w_j = 1`(`j ≤ k`),不保证半正定,但在重叠回归里**覆盖率(coverage)在相关样本量下常优于 NW**(搜索结论,**B/C**);代价是有限样本下可能非半正定。

**关键警告(本主题最重要的一条):** HAC **不是万能药**。当**重叠期相对样本长度较大**时(正是长 horizon 的情形),HH 和 NW 标准误本身存在严重**小样本下偏**——来自自协方差矩阵估计的偏差,会让 t 仍然偏高(Ang 及相关文献,**A/B**,见 §8 Warwick/City/ScienceDirect 来源)。即:**你修正了一阶问题,但修正量本身在小样本里又被低估。** 因此长 horizon 不能只靠 HAC,必须叠加:(a)报告 n_eff;(b)block bootstrap 经验分布;(c)非重叠子样本对照。

### 2.4 Boudoukh-Richardson-Whitelaw:长 horizon "可预测性"多是假象

BRW(2008,*RFS*,**A**)的核心:**在无可预测性的零假设下**,对持续型预测变量(dividend yield 等),长 horizon 回归系数与 R² 会**随 horizon 近似成比例上升**——因为重叠收益 + 回归子持续性导致跨 horizon 估计量在零假设下几乎完全相关(1Y vs 2Y 相关 99%,1Y vs 5Y 相关 94%)。

> 含义:把"5 年系数比 1 年大、R² 更高"当作"长期更可预测"的证据是**循环论证**——那正是没有可预测性时的标准形态。本系统对任何"长 horizon 信号更强"的结论,必须用 BRW 式的零假设模拟(bootstrap 持续型回归子)作对照,而非直接信 t。

---

## 3) 前视 / 幸存者 / restatement(长周期放大,附来源可信度)

horizon 越长,这三类偏差累积越多,且与"长期=可靠"的错觉互相强化。

### 3.1 前视偏差(look-ahead)

- **报告滞后:** 年报/季报在财年末后数周至数月才披露。用财年末日期对齐信号 = 前视。必须用 **filing date**(SEC EDGAR 的 `filed` 时间戳)对齐,常规再加保守滞后(如季度数据滞后 1 期 / +N 天)。
- **数据厂商回填(backfill):** Compustat 等常把后续修正悄悄写回历史序列,不打标记 → 前视。Lyle-Siano-Yohn 用 Compustat Snapshot(PIT)对照发现:持续的数据调整**显著改变 sales/earnings**,使 earnings response coefficient 和 accrual 对冲组合收益**随访问时点不同而实质性不同**(SSRN 5107985 / Yale 工作论文,**A/B**)。
- **可信度:** 前视机制 **A**(同行评审 + Compustat 官方文档确认 PIT 库正是为此而建);具体收益数字差异 **B**(依赖具体样本/因子)。

### 3.2 幸存者 / 退市偏差(survivorship / delisting)

- **量级证据:** CRSP US 1926–2001,survivorship-free vs biased 年化 **7.4% vs 9.0%**(差 ~1.6%/年,二手引用 CRSP,**B**)。Shumway(1997)delisting bias 使小盘收益被实质高估,修正后**小盘溢价降 ~1.5%/年**(**A/B**,常被引)。共同基金层面某研究 survival bias ~157 bp/年(**B**,但属基金非个股)。
- **退市终端收益:** 退市常伴随最后几日的剧烈负收益(破产/摘牌)。若价格序列止于最后正常交易日而不含 delisting return,你**漏掉了最有信息量的那一笔** → 系统性高估。
- **指数成分的回溯污染:** "S&P 500 策略"若用**今日**成分回测历史 = 幸存者偏差(今日成分是历史赢家的幸存者)。必须用 **PIT 成分重建**(本系统已有此能力)。
- **可信度:** 机制 **A**;具体 bp 量级 **B**(随样本/年代/市值段差异大,勿当精确常数)。

### 3.3 restatement(财报重述)

- 公司 7 月报 Q2,9 月悄悄修正。回测若对 8 月的信号用**修正后**数字 = 用了未来信息。
- 正确做法:用 **as-reported(原始申报值)+ filing date 时间戳**,而非 as-restated。需要 PIT 数据库或自建 PIT 快照(本系统从 SEC EDGAR XBRL 自建,有此条件)。
- **可信度:** **A/B**(Compustat PIT 文档 + Lyle 等研究确认重述实质改变研究结论)。

> **长周期放大逻辑:** 20 年回测里,前视/幸存者/restatement 不是一次性误差,而是**逐年累积的复利偏差**。横截面上 survivorship 只影响起点构成;时间序列上它影响**整条复利路径**。horizon 越长,幸存者组合相对真实可投资域的偏离越大。

---

## 4) 多重检验 / Deflated Sharpe Ratio(低频策略尤其致命)

### 4.1 多重检验门槛(Harvey-Liu-Zhu 2016)

- 文献已发表 **300+** 个声称预测股票收益的因子("因子动物园")。在如此密集的测试下,t>2.0 的传统门槛**远远不够**;HLZ 建议新因子需 **t ≥ ~3.0**(随时间上调,因累计测试次数增加)。用 |t|>3 准则,313 个变量里仅 ~9 个存活。(*RFS* 2016,**A**)。
- 对**低频/长周期**:T 小 → SR 估计本身方差大 → 跨多次试验取最大,选择性偏差(selection bias)对 max-SR 的抬高尤其严重。

### 4.2 Probabilistic Sharpe Ratio(PSR)— 单策略、含偏度峰度

PSR 给出"真实 SR > 基准 SR*"的概率,**显式纳入偏度 γ₃、峰度 γ₄**(非正态修正):

```
PSR(SR*) = Z[ ( (SR − SR*) · √(T−1) ) / √(1 − γ₃·SR + ((γ₄−1)/4)·SR²) ]
```

- `Z[·]` = 标准正态 CDF;`T` = 样本观测数;`SR` 用同频率(非年化)。
- 负偏 + 高峰(典型 carry/卖波/低波动策略)→ 分母变大 → PSR 下降。**长周期 T 虽大,但若策略左尾肥,PSR 仍可能不显著。**

### 4.3 Deflated Sharpe Ratio(DSR)— 多重检验修正

DSR = PSR,但把基准 SR* 换成**多重检验下的期望最大 SR**(`SR̂₀`,零技能假设下纯噪声 N 次试验的 max 期望):

```
E[max{SR̂_n}] ≈ E[SR̂_n] + √(V[SR̂_n]) · ( (1−γ)·Z⁻¹[1 − 1/N] + γ·Z⁻¹[1 − 1/(N·e)] )

γ ≈ 0.5772156649  (Euler-Mascheroni 常数)
e ≈ 2.71828
V[SR̂_n] = 跨 N 次试验的 SR 估计方差
N = 独立试验次数
```

```
DSR = Z[ ( (SR̂ − SR̂₀) · √(T−1) ) / √(1 − γ₃·SR̂ + ((γ₄−1)/4)·SR̂²) ]
```

- DSR 输出 = "真实 SR 超过选择偏差门槛 SR̂₀ 的概率"。
- **三个杠杆**都惩罚你:N 越大、SR 跨试验方差越大、样本 T 越小 → SR̂₀ 越高、DSR 越低。**低频策略 T 小,DSR 惩罚最重**——这正是为什么"长期但只有 ~20 个独立年"的策略难过 DSR。
- (Bailey-López de Prado 2014,SSRN 2460551 / davidhbailey.com,**A**。公式经多个二手实现核对一致,**B**。)

### 4.4 最短track record / backtest 长度

- **Minimum Track Record Length(MinTRL):** 达到给定置信度所需的最短样本长度,是 PSR 的反解。长周期策略要"统计上确信 SR>0",MinTRL 常以**年**计 —— 直接暴露"独立年太少"的问题。
- **Minimum Backtest Length(MinBTL):** 给定试验次数 N,避免过拟合所需的最短回测长度;N 越大 MinBTL 越长。低频 + 高 N → MinBTL 可能超过你拥有的历史。(同上来源,**A**;精确表达式 **[未核实]**,需回原文核对常数。)

### 4.5 CSCV / PBO(Bailey-Borwein-López de Prado-Zhu 2013)

- **CSCV(组合对称交叉验证):** 把样本切成 S 块,所有 C(S, S/2) 种 in-sample/out-of-sample 划分都跑,统计"IS 最优策略在 OOS 排名靠后"的频率。
- **PBO = logit 分布中 OOS 排名落到下半区的概率。** PBO 高 = 你的"赢家"很可能是过拟合产物。例:某案例 PBO 仅 13%(算好)。(SSRN 2326253 / davidhbailey.com,**A**;R 包 `pbo` 实现,**B**。)
- **对长周期的局限:** CSCV 需要足够多的块 S 才有意义;长 horizon / 低频下块数本就少,C(S,S/2) 组合塌缩,PBO 估计方差大。**[未核实]** 长周期下 CSCV 稳定性的定量边界。

---

## 5) walk-forward / 样本外在长周期的局限

- **切不出足够 fold:** 20 年、训练 5 年 + 测试 1 年滚动 → ~15 个测试窗;若**持有期本身多年**,不重叠测试窗掉到个位数。统计功效随之崩塌(某市场微结构 walk-forward 研究:34 个测试期仅 **12% statistical power**,**B**)。
- **训练数据利用率低 + fold 间方差大:** walk-forward 用的训练数据远少于 K-fold;参数/策略空间大时这一缺陷被放大,fold 间不稳定、低分离群点增多(Grokipedia/QuantInsti 综述,**C**;arXiv 实证 **B**)。
- **反应而非预测 regime:** walk-forward 适应已发生的 regime 切换,但**滞后**于切换本身;长周期里少数 regime(如一次大熊市)主导结果 → 单条路径结论脆。
- **数据窥探仍在:** 反复调 walk 窗口/参数/变体本身就是多重检验,间接过拟合。walk-forward **不等于**免疫过拟合。
- **CPCV(组合净化交叉验证,López de Prado 2018)缓解但不消除:**
  - 系统化构造多个 train/test 划分,**purge**(剔除与测试集时间重叠的训练样本)+ **embargo**(测试集后留隔离期)防泄漏。
  - 生成**多条回测路径**(而非 1 条)→ 得到 OOS 性能的**分布**,可做"统计回测",并直接喂给 DSR/PBO。实证上 CPCV 比 walk-forward 有更低 PBO、更高 DSR、更好稳定性(ScienceDirect 2024,**A/B**;Wikipedia/Towards AI 综述,**C**)。
  - **诚实边界:** CPCV 造的是**多路径**,不是**多独立信息**。底层独立年仍是 ~20;路径间高度相关。CPCV 改善的是估计的**稳定性与可证伪性**,**不能**把"20 个独立年"变成"200 个"。长周期的根本约束(独立样本少)无法被任何重采样技巧绕过。

---

## 6) 落地到本系统(验证 checklist / 统计修正 / 脚本钩子)

本系统已有:Deflated Sharpe、CSCV-PBO、Purged K-Fold、t>3、真 holdout、PIT 成分重建。下面是**长周期因子研究专用**的增量。

### 6.1 长周期因子验证 checklist(每个长 horizon 因子研究必过)

```
[ ] 数据 PIT 审计
    [ ] 信号对齐用 filing date(EDGAR `filed`),非财年末;季度数据 +保守滞后
    [ ] 用 as-reported 值,非 as-restated;restatement 不回填进历史
    [ ] 成分用 PIT 重建(含已退市/被并购标的);delisting return 已纳入
    [ ] 跑一遍"信号整体再滞后 1 期"鲁棒性:若 alpha 蒸发 → 疑似前视

[ ] 重叠收益 / 有效样本
    [ ] 报告 n_nominal 与 n_eff(≈ 不重叠区块数 ≈ n/k)
    [ ] 报告"独立年" ≈ 样本年数 / 持有期年数;若 <10 → 标红、降级为"探索性"
    [ ] 所有重叠回归用 HAC(Newey-West,L=k 或 2k;长 horizon 加报 Hansen-Hodrick 对照)
    [ ] 叠加 block bootstrap 经验分布(块长 ≥ 持有期),不只信 HAC 的 t

[ ] 零假设对照(BRW)
    [ ] 对持续型回归子(估值/yield),跑无可预测性零假设的 bootstrap 模拟
    [ ] 确认观测到的"长 horizon 系数/R² 上升"超出零假设下的自然上升

[ ] 多重检验登记
    [ ] 显式登记本研究的试验次数 N(参数网格×变体×因子数,诚实计数)
    [ ] DSR 用登记的 N + 跨试验 SR 方差;偏度峰度入 PSR/DSR 分母
    [ ] 新因子门槛 t ≥ 3.0(HLZ),不是 2.0
    [ ] 报告 PBO(CSCV);PBO > 0.5 → 拒绝

[ ] 样本外 / 路径
    [ ] 长周期用 CPCV 多路径(purge + embargo),不用单条 walk-forward
    [ ] 报告 OOS 性能分布,不只点估计;真 holdout 末段从不参与任何调参

[ ] 偏差量级 sanity
    [ ] survivorship/delisting 修正前后对比(预期差 ~1-2%/年量级)
    [ ] 标注每个关键结论的前视/幸存者暴露与可信度等级
```

### 6.2 统计修正(实现要点)

- **HAC 标准误:** 用 `statsmodels` `cov_type='HAC'`, `maxlags=2k`(Bartlett=NW);或自实现 Hansen-Hodrick 等权核做对照。两者不一致时,以更保守(更大 SE)者为准,并在报告标注小样本下偏风险。
- **有效样本量:** 默认输出 `n_eff = n / k` 与"独立年";在结论卡片上把 t 旁边永远配一个 `n_eff`,杜绝"240 观测"的错觉。
- **DSR:** N 来自**登记表**而非事后猜测;`V[SR̂_n]` 用试验网格实测方差,缺失时用保守上界。PSR/DSR 分母带 γ₃、γ₄。
- **零假设模拟:** 对 BRW 风险,用 AR(1) 拟合回归子持续性后 bootstrap,生成零假设下的系数/R² 分布作显著性校准。

### 6.3 脚本钩子(建议落点,非本次实现 — 仅指明位置)

> 仅为路线图;**本次任务不创建/不修改这些文件**。位置基于仓库现有 `backtest/`、`scripts/`、`routines/` 目录(已 `ls` 确认存在,具体内部接口 **[未核实]**)。

```
backtest/   → 增 stats 层:hac_se()、effective_sample_size()、psr()、dsr()、
              expected_max_sr()、min_trl();cpcv_paths(purge, embargo)
scripts/    → 增 pit_audit.py(filing-date 对齐 + restatement 检测 +
              "信号再滞后一期"鲁棒性回归)
routines/   → 因子研究 routine 末尾挂 checklist gate:n_eff/独立年、PBO、
              DSR、survivorship-delta 不达标则标记 fail / 降级为探索性
state/      → 试验次数 N 登记表(multiple-testing ledger),全局累计、防低报
```

---

## 7) 反方(对冲本文观点)

- **"过度保守会扼杀真实的长期 alpha":** 把门槛抬到 t≥3 + DSR + PBO + n_eff,会让**很多真实但低频的长期效应**(如真实的价值/质量溢价)无法通过单一历史样本"证明",从而被错误丢弃。统计严谨的代价是**第二类错误(漏真)上升**。对长期投资,经济学先验 + 跨市场/跨资产 OOS 证据,可能比单一样本的 t 更可靠。
- **HAC 本身有限样本下偏,可能把已经诚实的研究再打一棒:** 既然长 horizon 下 NW/HH 标准误自身下偏,机械堆修正未必收敛到真相;过度修正 + bootstrap 可能制造**虚假的不显著**。务实派主张:接受"长周期就是统计弱",转而靠**样本量替代物**(更多市场、更多资产、更长非重叠拼接)而非更复杂的单样本修正。
- **DSR 的 N 不可知:** "独立试验次数 N"在现实研究里几乎无法诚实计数(包括别人发表的、你脑内丢弃的试验)。N 是主观输入,DSR 的精确数值因此有**伪精确**风险——它是排序/警示工具,不是真理裁决。
- **CPCV/CSCV 假设可交换性:** purge+embargo 缓解泄漏,但金融数据**非平稳**,块间不可交换;组合交叉验证的统计保证在 regime 变化下打折。**[未核实]** 其在强非平稳长样本上的实际覆盖率。
- **"长期不可靠"被过度推销:** 部分从业者用"统计陷阱"全盘否定长期回测,反而走向另一极端(只信短期/高频)。长期投资的价值恰在于经济机制的持久性,统计弱不等于经济学无效——两者需分开判断。

---

## 8) 参考来源(URL + 可信度)

**重叠收益 / HAC / 有效样本**
- Boudoukh, Richardson, Whitelaw (2008), *The Myth of Long-Horizon Predictability*, RFS — https://pages.stern.nyu.edu/~rwhitela/papers/mlhp%20rfs08.pdf — **A**(同行评审,核心反方证据:零假设下系数/R² 随 horizon 升)
- NBER w11841 同论文 — https://www.nber.org/papers/w11841 — **A**
- Neuberger 等, *Improved Inference and Estimation in Regression With Overlapping Observations*, Warwick WBS — https://warwick.ac.uk/fac/soc/wbs/subjects/finance/faculty1/anthony_neuberger/improved.pdf — **A/B**(重叠观测推断改进)
- City University, *Overlapping observations* (JBFA) — http://openaccess.city.ac.uk/15212/1/JBFA%20Overlapping%20observations%20with%20BrittenJones.pdf — **A/B**
- ScienceDirect (2024), *Estimation and inference in low frequency factor model regressions with overlapping observations* — https://www.sciencedirect.com/science/article/abs/pii/S0927539824000719 — **A**(2024,低频 + 重叠,正中主题)
- ScienceDirect, *Biases in long-horizon predictive regressions* — https://www.sciencedirect.com/science/article/abs/pii/S0304405X21004013 — **A**
- HAC / Newey-West 背景:Econometrics with R 15.4 — https://www.econometrics-with-r.org/15.4-hac-standard-errors.html — **C**(教学,公式核对)

**Deflated Sharpe / PBO / 多重检验**
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, SSRN 2460551 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 — **A**
- 同论文 PDF — https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf — **A**(DSR/E[maxSR]/MinTRL 原始来源)
- Bailey, Borwein, López de Prado, Zhu (2013), *The Probability of Backtest Overfitting* (CSCV/PBO) — https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf — **A**
- 同论文 SSRN 2326253 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 — **A**
- Harvey, Liu, Zhu (2016), *…and the Cross-Section of Expected Returns*, RFS — https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF — **A**(t≥3 门槛,因子动物园)
- 同论文 NBER w20592 — https://www.nber.org/system/files/working_papers/w20592/w20592.pdf — **A**
- López de Prado, *A Practical Solution to the Multiple-Testing Crisis* — https://lncohn.com/finance/Prado-APracticalSolutionToMultiTestingCrisis.pdf — **A/B**
- DSR/PSR 公式核对(二手,公式与原文一致):marti.ai — https://marti.ai/qfin/2018/05/30/deflated-sharpe-ratio.html — **B/C**
- PSR 参考实现:rubenbriones/Probabilistic-Sharpe-Ratio — https://github.com/rubenbriones/Probabilistic-Sharpe-Ratio — **B**(代码,可对公式)
- R 包 `pbo`(CSCV 实现) — https://cran.r-project.org/web/packages/pbo/readme/README.html — **B**

**walk-forward / CPCV**
- Purged cross-validation, Wikipedia — https://en.wikipedia.org/wiki/Purged_cross-validation — **C**(CPCV 概念/历史核对)
- ScienceDirect (2024), *Backtest overfitting in the ML era: comparison of OOS testing methods* — https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110 — **A/B**(CPCV vs walk-forward 实证,低 PBO/高 DSR)
- López de Prado, *10 Reasons Most ML Funds Fail*, GARP — https://www.garp.org/hubfs/Whitepapers/a1Z1W0000054x6lUAA.pdf — **B**
- arXiv 2025, *Rigorous Walk-Forward Validation Framework*(34 测试期 12% power 例) — https://arxiv.org/pdf/2512.12924 — **B**
- Walk-forward 综述:QuantInsti — https://blog.quantinsti.com/walk-forward-optimization-introduction/ — **C**

**前视 / 幸存者 / restatement**
- Lyle, Siano, Yohn, *Re-Adjusted Financial Statement Data*, SSRN 5107985 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5107985 — **A/B**(PIT vs restated 实质改变 accrual 结论)
- 同主题 Yale 版 — https://som.yale.edu/sites/default/files/2024-07/Re-Standardized%20Financial%20Statement%20Data.pdf — **A/B**
- Compustat PIT 库说明(O'Reilly 摘录) — https://www.oreilly.com/library/view/equity-valuation-and/9780470929919/chap12-sec33.html — **B/C**
- Refinitiv, *Using point-in-time data to avoid bias* — https://perspectives.refinitiv.com/future-of-investing-trading/how-to-use-point-in-time-data-to-avoid-bias-in-backtesting/ — **C**(厂商,机制核对)
- 幸存者/退市量级(CRSP 7.4% vs 9.0%;Shumway 1997 小盘 ~1.5%)— 二手综述:https://hedgefundalpha.com/education/backtesting-mistakes-kill-quant-strategies-guide/(本次 WebFetch 返回 403,内容来自搜索摘要,**B**,**[量级未独立核实]**)
- CFA L2 *Problems in Backtesting and Biases in Data* — https://analystprep.com/study-notes/cfa-level-2/problems-in-backtesting/ — **C**

> 可信度自评:核心方法论结论(重叠收益假显著、BRW 零假设效应、DSR/PBO 机制、HLZ t≥3、HAC 小样本下偏、CPCV 缓解但不造独立信息)均有 **A** 级原始论文支撑。具体偏差**量级**(1.6%、1.5%、157bp、12% power)为二手引用,标 **B** 且部分 **[量级未独立核实]**。DSR/PSR/E[maxSR] 公式经原始论文 + 多个二手实现交叉核对一致;MinBTL 精确常数 **[未核实]**,使用前应回 Bailey-López de Prado 原文确认。
