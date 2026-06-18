# 可自动化的内在价值估算 — reverse DCF / RIM / owner earnings 深度研究

> 目的:为本系统的**长期(持有数月至数年)做多**方向,提供可自动化、可证伪、可落地的"内在价值"估算方法,产出一个 **"便宜/合理/贵"分档因子**用于排序而非精确点估。
> 方法:并行检索 Mauboussin/Rappaport(reverse DCF / Expectations Investing)、Penman(残差收益/RIM)、Buffett(owner earnings)、Damodaran(可复制估值法 + 免费数据集)→ 一手来源 + 可信度 → 合成 + 落地脚本设计。
> 日期:2026-06-18。关键数字标注来源 URL 与可信度(高/中/低)。无法核实者标"未核实"。
> 立场(房子风格):**纯自动 DCF 的点估几乎一定是 garbage-in;它对终值/WACC/增长极度敏感,只能做相对排序与情景区间。任何"算出内在价值 = $X"的单点输出默认不可信。RIM 因把账面价值锚进 PV、削弱终值占比而更稳健,是自动化的首选骨架。**

---

## 1. TL;DR(可证伪要点)

1. **reverse DCF 不预测未来,而是从当前价反推"市场已隐含的增长率/回报率",再让人判断这个预期是 brilliant 还是 bonkers(Mauboussin/Rappaport, Expectations Investing)。** 这把不可能的任务(预测)换成可管理的任务(评估当前预期是否过高)[fool.com Q&A; speedwellresearch](中-高可信度)。→ 本系统可自动算"隐含增长率",把它与历史实际增长/行业中位对比,产出"预期过高"信号,**比算点估值更稳健**。

2. **纯 FCF DCF 的终值通常占企业价值 60–80%,是单一最敏感假设;终值增长 g 变 0.5% 可使终值波动 10–20%。** 因此 DCF 输出**不是一个值,而是一个分布/区间**(Damodaran 反复强调)[soferadvisors; valuationmasterclass](中-高可信度,多源一致)。→ 自动 DCF 点估 = garbage-in;**只做情景区间 + 跨股排序**,不报"内在价值 = $X"。

3. **残差收益模型 RIM(Penman)把账面价值 B₀ 直接锚进现值,终值占比远小于 FCF DCF,对终值假设更稳健;在有实质账面价值的成熟公司上"更锚定可观察数据、更不受可裁量调整影响"。** V₀ = B₀ + Σ (ROEₜ − r)·Bₜ₋₁ / (1+r)ᵗ [analystprep RIM; researchgate Firm valuation comparison](中-高可信度)。→ **RIM 是本系统自动化的首选骨架**:输入全是 EDGAR 可得字段(净利润、账面净值、股本成本),少一层"自由现金流口径/维护性 capex"的主观拆分。

4. **owner earnings(Buffett)= 净利润 + 折旧摊销 + 其他非现金 − 维护性 capex ± 营运资本变动。** 难点在"维护性 capex"无法从财报直接取得,需用代理(如折旧、或 capex 的历史比例)[oldschoolvalue; stablebread owner earnings](中可信度,定义清晰但维护性 capex 不可机械化)。→ 自动化里用 **FCF = CFO − CapEx(全额)** 作可机械化代理,并明确标注它**高估了真实可分配现金**(因含增长性 capex 被全扣),作为保守口径。

5. **Damodaran 提供免费、年度更新的行业级 WACC / ERP / 增长 / ROE / 再投资率数据集(.xls),可作为自动估值的默认先验输入。** 2026 年 1 月 9 日更新[pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html](高可信度)。→ 用行业 WACC/ERP 做默认折现率,避免逐股估 beta 的噪声;但**这些是美股横截面均值,口径与 PIT 对齐需谨慎**(它是"当前"快照,非历史 vintage)。

6. **学术上,"隐含成本资本(ICC)"作为预期回报代理,与未来横截面收益的正向关系"一直未能被确证"(Hou-van Dijk-Zhang 2012,JAE)。** 即:把 reverse-DCF 隐含回报当 alpha 因子直接选股,证据偏弱[Hou et al. 2012 JAE; ScienceDirect](中-高可信度)。→ **不要把"隐含增长/隐含回报"当独立 alpha 源直接选股**;当作**情景过滤器 / 预期过高警示 / 与价值-质量复合腿正交的一维**,更稳。

7. **结论:把估值做成横截面分档(便宜/合理/贵)而非点估。** 用 RIM-implied value / price 比值、reverse-DCF 隐含增长 vs 行业中位、FCF/EV 收益率三条线,跨股 z-score + 分位 → 三档。**点估的"精确"是假精确;排序的"相对便宜"才有信息**(Damodaran: value is a distribution)[soferadvisors](中可信度)。→ 见 §6 落地。

8. **所有自动估值必须先过护栏:剔除负账面净值、负 TTM 收益、金融/公用事业(口径不同)、极小市值、ROE 异常高/低、净债务异常。** garbage-in 的主源是异常分母与会计扭曲(无形资产密集行业账面净值系统性偏低)。→ 与本系统已有的 intangibles 调整、F-Score 过滤复用(见 `value-investing-frameworks.md`)。

---

## 2. reverse DCF / RIM / owner earnings — 一手公式

### 2.1 标准两阶段 FCF DCF(作为对照,不作主输出)
企业价值
> EV = Σ_{t=1..N} FCFFₜ / (1+WACC)ᵗ + TV / (1+WACC)ᴺ
> TV(永续增长法)= FCFF_{N+1} / (WACC − g) = FCFF_N·(1+g) / (WACC − g)

- FCFF(自由现金流给公司)= EBIT·(1−税率) + 折旧摊销 − CapEx − ΔNWC。
- 股权价值 = EV − 净债务;每股内在价值 = 股权价值 / 稀释股数。
- **致命点**:TV 占 EV 60–80%,且对 (WACC − g) 的差极敏感;WACC、g、N、margin 路径全是主观 → **点估不可自动化为可信值**[soferadvisors; valuationmasterclass](中-高可信度)。

### 2.2 reverse DCF — 从价反推隐含增长(本系统主用法之一)
**思路**:把当前价/EV 当已知,固定 WACC 与终值结构,**反解唯一自由变量(通常是收入或 FCF 的复合增长率 g_implied)**,使 PV(现金流) = 当前 EV。

**算法(可机械化,数值求根)**:
```
给定: P0(当前 EV 或市值), FCF0(当前自由现金流), r(WACC), N(显式期, 如10), g_term(终值增长, 如=长期GDP~2.5%)
定义 PV(g) = Σ_{t=1..N} FCF0·(1+g)^t / (1+r)^t
            + [FCF0·(1+g)^N·(1+g_term)] / [(r-g_term)·(1+r)^N]
求 g* 使 PV(g*) = P0     # 单调 → 二分法 bisection 即可
输出 g_implied = g*       # 市场隐含的 N 年现金流复合增长
```
- 单调性:PV 对 g 单调递增 → **二分法稳定收敛**(护栏:限定 g ∈ [−20%, +60%],r > g_term)。
- **判读**:把 g_implied 与 (a) 公司历史 5 年实际增长、(b) Damodaran 行业基本面增长、(c) 分析师一致预期 对比。g_implied 远高于三者 → "市场预期过高"(贵)。
- **实例佐证**:Speedwell 对 Meta(2023.01)构造 6 组收入增长×EBIT margin 情景,**令 DCF = 当前市值反解隐含回报**,最保守"0% 增长 + 中性 margin"≈ 9% 回报[speedwellresearch](中可信度,单案例,作者自述)。
- **局限(其自述)**:"out year assumptions seem to be baseless";终值把企业当永续年金,outyear 假设无依据[speedwellresearch](中可信度)。

### 2.3 残差收益模型 RIM / EVA(本系统主骨架)
来源:Penman《Accounting for Value》/《Financial Statement Analysis and Security Valuation》;CFA/analystprep RIM[analystprep RIM; cfainstitute RIM 2026](中-高可信度,公式为标准教科书定义)。

> **V₀ = B₀ + Σ_{t=1..∞} RIₜ / (1+r)ᵗ**
> 其中 RIₜ(残差收益)= Eₜ − r·Bₜ₋₁ = (ROEₜ − r)·Bₜ₋₁
> Eₜ=t 期净利润,Bₜ₋₁=期初账面净值,r=股本成本,ROEₜ=Eₜ/Bₜ₋₁

- **EVA 等价物(企业口径)**:EVA = NOPAT − WACC·投入资本;同构,只是用投入资本与 WACC。
- **为什么更稳健**:B₀ 是已观测的账面净值,直接进 PV;价值的大部分来自 B₀ 与近端 RI,**终值占比远小于 FCF DCF** → 对永续假设不敏感[analystprep RIM vs DDM/FCF; researchgate comparison](中-高可信度)。
- **单阶段闭式(可机械化)**:若 ROE、r、g 恒定,
  > **V₀ = B₀ · [1 + (ROE − r)/(r − g)] = B₀ · (ROE − g)/(r − g)**
  这是本系统**首选自动估值公式**:输入 B₀、ROE(用 TTM 或 3 年均)、r(行业股本成本)、g(保守,≤ 长期 GDP),全部 EDGAR/Damodaran 可得。
- **隐含价值比值**(分档用):`rim_ratio = V₀ / 市值`。>1 偏便宜,<1 偏贵。
- **clean surplus 假设**:RIM 要求账面净值变动 = 净利润 − 分红(干净盈余);OCI/回购/增发会破坏它,需护栏与近似(见 §6)。
- **驱动**:RI 两个驱动是 ROE(ROCE)与账面净值增长 g[researchgate tutorial RIM](中可信度)。

### 2.4 owner earnings / FCF(保守现金口径)
来源:Buffett 1986 致股东信(owner earnings 概念);二手整理[oldschoolvalue; stablebread](中可信度)。

> **Owner Earnings = 净利润 + 折旧摊销 + 其他非现金 − 维护性 CapEx ± Δ营运资本**

- **不可机械化的点**:维护性 capex(只保维持现状的资本支出),财报不披露,需估计;Buffett 自己也说"只能估个区间"。
- **自动化代理(可机械化、保守)**:
  > **FCF_proxy = CFO − CapEx(全额)** (= NetCashProvidedByUsedInOperatingActivities − PaymentsToAcquirePropertyPlantAndEquipment)
  全扣 capex(含增长性)→ **系统性低估真实 owner earnings**,作保守口径接受;输出 `fcf_yield = FCF_proxy / EV`。
- 进阶代理:维护性 capex ≈ min(CapEx, 折旧摊销),则 OE ≈ 净利润 + (D&A − 维护capex) ± ΔNWC;**列为可选,默认不用**(引入新主观)。

---

## 3. 敏感性与可靠性证据(来源 + 可信度)

| 论断 | 证据/数字 | 来源 | 可信度 |
|---|---|---|---|
| 终值占 DCF 价值 60–80%,是最敏感假设 | "Terminal value accounts for 60–80% of total enterprise value, the single most sensitive assumption" | soferadvisors; valuationmasterclass | 中-高(多源一致) |
| g 变 0.5% → 终值波动 10–20% | "even a 0.5% change in g can shift terminal value by 10% to 20%" | soferadvisors | 中 |
| DCF 应输出区间/分布而非单点 | "A DCF that gives a single estimate of value is a flawed model … present value as a distribution or range"(归于 Damodaran) | soferadvisors(转述) | 中(转述,理念与 Damodaran 公开立场一致) |
| RIM 对终值不敏感(账面价值锚) | "book value constitutes a large portion of PV … unlike DDM/FCF where terminal values make up a significant portion" | analystprep RIM vs DDM/FCF | 中-高 |
| RIM 更锚定可观察数据、更不受可裁量调整影响 | "more anchored on observable data, less sensitive to discretionary adjustment, more economically transparent" | researchgate(RI vs DCF in valuation disputes) | 中 |
| reverse DCF = 反推市场隐含预期 | "work backward from the stock price to figure out the performance the market is already expecting" | fool.com Mauboussin/Rappaport Q&A; streetfins | 中-高 |
| 隐含回报(ICC)与未来横截面收益正向关系**未被确证** | "existing cross-sectional studies on the ICC have been unable to conclusively establish a positive relation between ICC and future returns" | Hou, van Dijk, Zhang 2012, JAE | 中-高 |

**可证伪推论**:既然 (a) DCF 点估对终值/WACC/g 极敏感,(b) ICC 直接选股证据弱 → **本系统不把估值当点估或独立 alpha,而当横截面"贵/便宜"分档与"预期过高"过滤**;历史回测的任何估值因子毛收益,默认按本系统纪律打 3–5 折(扣成本/再定价/拥挤)。

---

## 4. Damodaran 免费输入(默认先验数据集)

来源:[pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html](高可信度);**年度更新,最近 2026-01-09**;均 .xls/.xlsx 直接下载,无需 key。

| 用途 | 数据集 | 直链(US) | 含字段 |
|---|---|---|---|
| 行业 WACC / 股本成本 / 债务成本 / 市场债务比 | Costs of Capital by Industry | `…/pc/datasets/wacc.xls` | cost of equity / debt / capital,market D/(D+E),按行业分组 |
| ERP(历史) | Historical Returns Stocks/Bonds/Bills | `…/pc/datasets/histretSP.xls` | 1928–今年度收益,估 ERP 起点 |
| ERP(隐含) | Implied Equity Risk Premiums | `…/pc/datasets/histimpl.xls` | 2 阶段增广 DDM 反推的隐含 ERP |
| 国家风险溢价 | Risk Premiums for Other Markets | `…/pc/datasets/ctryprem.xlsx` | 基于 Moody's 评级 + CDS |
| beta(行业) | Levered/Unlevered Betas by Industry | `…/pc/datasets/betas.xls` | levered/unlevered/pure-play beta |
| 利润率 | Operating & Net Margins by Industry | `…/pc/datasets/margin.xls` | gross / pre-tax operating / net margin |
| ROE 分解 | ROE Decomposition by Industry | `…/pc/datasets/roe.xls` | ROE = 净利/账面净值,拆成 ROC + 杠杆 |
| 历史增长 | Historical Growth in Earnings | `…/pc/datasets/histgr.xls` | 近 5 年盈利/收入增长(行业) |
| 基本面增长 | Fundamental Growth in EPS / EBIT | `…/pc/datasets/fundgr.xls`, `fundgrEB.xls` | 稳态 EPS 增长;EBIT 增长 = ROC×再投资率 |
| 再投资率 / 销售投入资本比 | CapEx, Depreciation, Reinvestment | `…/pc/datasets/capex.xls` | 再投资率(占营业利润%)、sales/capital |

**护栏/garbage-in**:这些是**美股当前横截面均值的快照,不是历史 vintage** → 用作"当前先验/默认折现率与行业增长基准"可,**回测历史 PIT 面板时不可把今天的行业 WACC 套到 2015 年**(前视)。落地时把 Damodaran 集快照下载日期作为 vintage 标记;历史回测优先用"行业内可 PIT 重建的 ROE/增长中位"。行业映射需把 EDGAR SIC → Damodaran 行业分组(手工映射表,中等工作量,标"未核实精度")。

---

## 5. 数据与可得性(EDGAR 字段)

数据源、PIT 规范、tag fallback 链见同目录 `sec-edgar-xbrl-fundamentals.md`(本系统已成稿,复用)。本主题所需字段:

| 语义 | taxonomy | tag fallback 链 | 用途 |
|---|---|---|---|
| 净利润 E | us-gaap | `NetIncomeLoss` → `ProfitLoss` | RIM 的 E,ROE 分子 |
| 账面净值 B | us-gaap | `StockholdersEquity` → `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | RIM 的 B₀,P/B |
| 营业利润 EBIT | us-gaap | `OperatingIncomeLoss` | FCFF、EV/EBIT、NOPAT |
| 经营现金流 CFO | us-gaap | `NetCashProvidedByUsedInOperatingActivities` | FCF_proxy |
| 资本支出 CapEx | us-gaap | `PaymentsToAcquirePropertyPlantAndEquipment` → `PaymentsToAcquireProductiveAssets` | FCF_proxy |
| 折旧摊销 D&A | us-gaap | `DepreciationDepletionAndAmortization` → `DepreciationAmortizationAndAccretionNet` | owner earnings、FCFF |
| 现金 | us-gaap | `CashAndCashEquivalentsAtCarryingValue` → `CashCashEquivalentsRestrictedCash…` | 净债务、EV |
| 长期债务 | us-gaap | `LongTermDebtNoncurrent` → `LongTermDebt` | 净债务、EV |
| 稀释股数(期) | us-gaap | `WeightedAverageNumberOfDilutedSharesOutstanding` → `…Basic` | 每股值 |
| 流通股(时点) | dei | `EntityCommonStockSharesOutstanding` → `CommonStockSharesOutstanding` | 市值 |
| 所得税/税前 | us-gaap | `IncomeTaxExpenseBenefit`, `IncomeLossFromContinuingOperationsBeforeIncomeTaxes…` | 有效税率 → NOPAT |

**PIT 铁律(复用 `sec-edgar-xbrl-fundamentals.md` §4)**:时间轴用 `filed`(披露日),**不是** `end`(期末);同 `(cik, tag, end)` 保留全部 vintage,查询时 `filed ≤ as_of` 后按 `(cik,tag,end)` 取最大 `filed` 去重 → 再按 `(cik,tag)` 取最新 `end`。价格来自现有日线缓存(`backtest/data_cache/<TICKER>.csv`),市值 = 时点价 × 时点流通股(用最近 `filed ≤ as_of` 的股数)。

**可得性坑(garbage-in)**:
- 负 `StockholdersEquity`(回购导致,如部分蓝筹)→ RIM 分母/锚失效,**剔除**。
- 负 TTM 净利润 → ROE 无意义,**剔除或单独档**。
- 金融/公用事业:EBIT/capex/账面净值口径不可比,**默认排除**。
- 无形资产密集(软件/医药):账面净值系统性偏低 → RIM 高估"贵"。复用 `value-investing-frameworks.md` 的 R&D/SG&A 资本化(iHML)修正,或改用 FCF/EV 不依赖账面净值的便宜度。
- tag 缺失/单位(USD vs USD/shares)/合并报表少数股东权益口径 → 用 fallback 链 + 单位校验。

---

## 6. 落地到本系统(估值分档因子 / 脚本 / 护栏 / 验证)

### 6.1 设计目标
产出一个**横截面价值分档因子** `val_bucket ∈ {cheap, fair, expensive}`(及连续分 `val_score`),作为长期做多腿的一维,**与现有价值-质量复合腿正交**(避免与 EV/EBIT 等重复)。**不输出点估"内在价值=$X"**。

### 6.2 三条独立估值线(全部可机械化)
1. **RIM 比值**(主):单阶段闭式 `V0 = B0·(ROE − g)/(r − g)`;`rim_ratio = V0 / 市值`。r 用 Damodaran 行业股本成本;g 保守取 min(行业基本面增长, 长期GDP 2.5%);ROE 用 3 年均 TTM(降噪)。
2. **reverse-DCF 隐含增长缺口**(过滤/警示):二分法解 `g_implied`(§2.2);`growth_gap = g_implied − max(hist_growth_5y, 行业基本面增长)`。gap 越大越"贵"。
3. **FCF/EV 收益率**(保守现金口径):`fcf_yield = (CFO − CapEx) / EV`,EV = 市值 + 净债务。

### 6.3 合成与分档(复用现有横截面机制)
复用 `backtest/factors_xs.py` 的 `zscore()` / `rankdata()` 与 `xs_backtest.py` 的 `decile_spread()`:
```python
# val_score = w1·z(log rim_ratio) − w2·z(growth_gap) + w3·z(fcf_yield)
# 方向:rim_ratio↑/fcf_yield↑ → 便宜(+);growth_gap↑ → 贵(−)
# 默认等权 w=1/3;在 train 段用 IC 加权(embargo,无前视)
# 分档:val_score 横截面分位 → top 30% cheap / mid fair / bottom 30% expensive(或十分位 D10-D1 看单调)
```
新增因子注册:扩 `FACTOR_SIGN`、在 `factor_values()` 同构位置加 `rim_ratio/growth_gap/fcf_yield`(但这些是**基本面字段**,需新建 PIT 面板源,见下脚本)。

### 6.4 脚本(新增,不改现有;stdlib + numpy,跟随 `scripts/funds_13f.py` / `fundamentals_pit.py` 风格)
- `scripts/intrinsic_value.py`(建议):
  - `load_pit_fundamentals(as_of)`:从 vintage 表取 `filed ≤ as_of` 的 E/B/EBIT/CFO/CapEx/股数/债务/现金。
  - `cost_of_equity(sic) / wacc(sic)`:读本地缓存的 Damodaran 行业表(.xls→csv,带下载日 vintage 标记)。
  - `rim_value(B0, roe, r, g)` → V0;`reverse_dcf_growth(P0, fcf0, r, N, g_term)` → g*(二分法);`fcf_yield(cfo, capex, ev)`。
  - `compute_panel(as_of, universe)` → 每股 `{rim_ratio, growth_gap, fcf_yield}`,带护栏剔除。
  - `--publish`:走 `scripts/feed_lib.py` 的 `publish_report(...)`,发 `feed/reports/<id>.json`(估值分档快照),供 `frontend/lib/feed.ts` 消费。
- CLI 模板与发布遵循 `backtest/factor_factory.py` / `scripts/run_routine.py` 的 argparse + `if args.publish` 模式;可挂 `.github/workflows/monthly-studies.yml` 月更。

### 6.5 护栏(garbage-in 防线,硬编码)
- 剔除:`B0 ≤ 0`;`TTM 净利润 ≤ 0`(或单列"亏损/特殊"档);金融(SIC 6xxx)/公用事业(SIC 49xx)。
- 数值护栏:RIM 要求 `r > g`(否则发散)→ 强制 `g ≤ r − 1%`;reverse-DCF 限 `g_implied ∈ [−20%, 60%]`、`r > g_term`、二分上限迭代次数。
- 极值:ROE 在 [−50%, +80%] 外裁剪或剔除;`rim_ratio` 取 log 后 winsorize 1%/99%;`fcf_yield` 负值保留但 winsorize。
- 会计:clean surplus 破坏(大额 OCI/回购)→ 用 `ΔB ≈ 净利润 − 分红` 校验,偏差大者降权或标记。
- vintage:Damodaran 行业数据按下载日打 vintage;**历史回测禁止用未来快照**(前视),回测段优先用可 PIT 重建的行业内 ROE/增长中位作 r、g 先验。

### 6.6 验证(复用本系统防过拟合纪律)
- **预期判读优先于选股**:先验证 `growth_gap`(隐含增长 vs 实际)能否分离"事后增长不及预期 → 下修 → 跑输"的样本(事件研究),而非直接当 alpha 排序。
- **Rank-IC + 十分位单调**:用 `spearman()` 算 `val_score` 与未来 3–12 月收益的 Rank-IC;`decile_spread()` 看 D1–D10 单调与 top-bottom 价差。
- **正交化**:对现有 EV/EBIT、F-Score、动量做横截面回归,看 `val_score` 残差是否仍有 IC(避免与裸价值重复;呼应 FF 五因子 HML 冗余教训)。
- **扣成本 + 防过拟合**:净·扣成本口径(±5bp + 冲击);Deflated Sharpe / CSCV-PBO / t>3;**历史毛收益默认打 3–5 折**。
- **稳健性**:对 r(±1.5%)、g(±1%)、N(5/10/15)做敏感性网格,报"分档稳定性"(同一股在参数扰动下是否换档),而非报点估方差——这正是把 DCF 当区间/排序的体现。

---

## 7. 风险与反方

1. **隐含回报/ICC 直接选股证据弱**(Hou et al. 2012):reverse-DCF 隐含增长当独立 alpha 风险高 → 仅作过滤/警示一维[Hou 2012 JAE](中-高)。
2. **RIM 不是终值无关,只是终值占比小**:仍依赖 ROE 持续性与 g;若 ROE 均值回归比假设快,RIM 同样高估。clean surplus 在 OCI/回购密集公司被破坏 → 账面净值口径噪声。
3. **账面价值会计扭曲**:无形资产密集行业账面净值系统性偏低 → RIM 高估"贵";需 iHML 修正,否则把成长科技股全打成"贵"是已知 2010s 价值失效的会计真因(见 `value-investing-frameworks.md`)[AHKL 2020](中-高)。
4. **Damodaran 数据是横截面快照非 vintage**:误用即前视;行业映射(SIC→Damodaran 分组)精度"未核实"。
5. **维护性 capex 不可机械化** → owner earnings 真值不可自动算;FCF_proxy(全扣 capex)保守但对重资产成长股系统性低估现金。
6. **拥挤/再定价**:估值便宜度是被全网回测烂的公因子,任何历史 alpha 默认已被部分套利;时序极不稳定(价值 2007–2020 历史性回撤)。
7. **反方最强论点**:对许多公司,"自动估值"无论 RIM 还是 DCF,信噪比都低于简单 multiples(EV/EBIT、FCF/EV)。→ **本因子的价值主张应是"情景区间 + 预期过高警示 + 与裸价值正交的增量",而非取代 multiples 或给点估**;若正交化后无增量 IC,应**否决**(房子纪律:可证伪、可被砍)。

---

## 8. 参考来源(URL + 可信度)

reverse DCF / Expectations Investing:
- [fool.com — Expectations Investing Q&A, Mauboussin & Rappaport (2022)](https://www.fool.com/investing/2022/01/19/expectations-investing-qanda-mauboussin-rappaport/) — 一手作者访谈,中-高
- [speedwellresearch — Explaining the Reverse DCF (2024)](https://speedwellresearch.com/2024/10/03/investing-is-just-answering-a-series-of-questions-explaining-the-reverse-dcf/) — 含 Meta 实例与局限自述,中
- [streetfins — Expectations Investing Framework](https://streetfins.com/expectations-investing/) — 框架综述,中

RIM / 残差收益 / 终值敏感性:
- [analystprep — Residual Income Model (CFA L2)](https://analystprep.com/study-notes/cfa-level-2/residual-income-model/) — 标准公式,中-高
- [analystprep — Residual Income vs DDM and FCF Models](https://analystprep.com/study-notes/cfa-level-2/residual-income-vs-ddm-and-fcf-models/) — 终值占比对比,中-高
- [cfainstitute — Residual Income Valuation (refresher 2026)](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/residual-income-valuation) — 权威定义,高
- [researchgate — Firm valuation: RI vs DCF approaches](https://www.researchgate.net/publication/222343393_Firm_valuation_Comparing_the_residual_income_and_discounted_cash_flow_approaches) — RI vs DCF,中
- [researchgate — DCF and Residual Earnings in Valuation Disputes](https://www.researchgate.net/publication/235983747) — "更锚定可观察数据",中
- [Penman — Valuation Models: An Issue of Accounting Theory (Columbia)](https://business.columbia.edu/sites/default/files-efs/pubfiles/6208/Valuation%20Models%20Routledge.pdf) — Penman 一手,高(理论)

DCF 终值/WACC 敏感性 + 区间论:
- [soferadvisors — Terminal Value Formula in a DCF](https://soferadvisors.com/insights/blog/terminal-value-formula-how-to-calculate-it-in-a-dcf/) — 60–80%、0.5%→10–20%、区间论,中
- [valuationmasterclass — DCF Valuation Guide](https://valuationmasterclass.com/dcf-valuation/) — 终值占比,中
- [Damodaran — Ten Myths about DCF (Temasek PDF)](https://pages.stern.nyu.edu/~adamodar/pdfiles/country/DCFmythsTemasek.pdf) — 一手(PDF 抓取失败,内容据 Damodaran 公开立场转述,标"未核实原文逐句")
- [Damodaran — Growth Rates and Terminal Value (Stern PDF)](https://pages.stern.nyu.edu/~adamodar/pdfiles/ovhds/dam2ed/growthandtermvalue.pdf) — 一手,高(未逐句核实)

owner earnings:
- [oldschoolvalue — What is Owner Earnings (Buffett)](https://www.oldschoolvalue.com/what-is-owner-earnings/) — 公式整理,中
- [stablebread — Warren Buffett's Owners Earnings](https://stablebread.com/warren-buffett-owners-earnings/) — 维护性 capex 讨论,中

Damodaran 免费数据集:
- [Damodaran — Current Data (datacurrent.html)](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datacurrent.html) — 行业 WACC/ERP/beta/增长/ROE/再投资,年度更新 2026-01-09,高
- 直链示例:`…/pc/datasets/wacc.xls`(WACC)、`histimpl.xls`(隐含 ERP)、`roe.xls`(ROE 分解)、`capex.xls`(再投资率)、`fundgr.xls`/`fundgrEB.xls`(基本面增长)

ICC 与横截面收益(反方证据):
- [Hou, van Dijk, Zhang — The Implied Cost of Capital: A New Approach (JAE 2012, PDF)](https://care-mendoza.nd.edu/assets/152192/houpaper.pdf) — ICC 与未来收益关系未确证,中-高

本系统内部参考(已成稿,复用):
- `research/long-term/sec-edgar-xbrl-fundamentals.md` — EDGAR XBRL tag fallback + PIT vintage 规范
- `research/long-term/value-investing-frameworks.md` — EV/EBIT、F-Score、iHML 无形资产修正、防过拟合纪律
- `backtest/factors_xs.py`(`zscore`/`rankdata`/`spearman`)、`backtest/xs_backtest.py`(`decile_spread`)、`backtest/factor_factory.py`(门控+发布)、`scripts/feed_lib.py`(`publish_report`)

> 自检:无法核实原文逐句处已标注(Damodaran Ten Myths PDF 抓取失败、SIC→行业映射精度);所有历史收益按房子纪律默认打 3–5 折;本因子若正交化后无增量 IC 应否决。
