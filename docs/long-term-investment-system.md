# 长期投资系统设计(Long-Term Investment System, LIS v0.1)

> 把 [`research/long-term/`](../research/long-term/) 24 篇调研收敛成一个**可分期建造**的系统设计。
> 定位:现有 [`statarb.py`](../backtest/statarb.py) 是**中频做多做空**引擎(净 alpha≈0/负,真 alpha 在冷门层);
> 本设计是**互补的第二引擎** —— 多头为主、持有期数月至数年、靠基本面广度 + 合成 + 防过拟合纪律。
> 横向元结论与逐条证据见 [`research/long-term/README.md`](../research/long-term/README.md)。
> ⚠️ 信息研究,非投资建议。

---

## 0. 设计原则(从 24 篇调研收敛)

| # | 原则 | 来源报告 |
|---|---|---|
| P1 | **没有魔法**:护城河=广度×合成×纪律,不是单因子准 | quant-factor(既有)、factor-combination |
| P2 | **长期≠更可靠**:有效样本 n_eff≈n/H,验证门槛要**更高** | backtesting-longhorizon-pitfalls |
| P3 | **质量是长期腿的结构性优势**(低换手、容量大、扣成本存活) | quality-moat、low-vol |
| P4 | **基本面只信 PIT**:EDGAR `filed` 锚 + 冻结 vintage,回测含退市票 | sec-edgar-xbrl、free-fundamental-data |
| P5 | **风控是温和拨盘不是择时**:波动目标作用总敞口;趋势/宏观做软开关 | risk-drawdown、asset-allocation、macro |
| P6 | **LLM 不进决策链**:只做抽取/假设生成,产出须过公式因子门控 | ai-llm-fundamental-agents |
| P7 | **净·扣成本+税后**为唯一裁决货币;毛收益打 3-5 折 | 全体 |

---

## 1. 系统分层架构

```
┌─ L0 数据底座(PIT)──────────────────────────────────────────────┐
│  EDGAR XBRL 基本面面板(filed 锚)· FRED/ALFRED 宏观(vintage)    │
│  价格/成分(已有:data.py + pit_membership.py)· 加密(已有)      │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L1 因子库(多头腿)──────────────────────────────────────────────┐
│  价值 · 质量/复利 · 动量 · 低波 · (修正/情绪 当数据到位)          │
│  + 剔除闸(造假/破产/盈余质量红旗)                                │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L2 合成 LongScore ───────────────────────────────────────────────┐
│  winsorize 3σ → 行业+规模中性 → rank-z → 等权综合 → 剔除闸         │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L3 组合构建 ─────────────────────────────────────────────────────┐
│  顶档 ≥50 票 · 等权 · 带宽再平衡(±20% 相对带 + 月/季检查)       │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L4 风险叠加(总敞口层)──────────────────────────────────────────┐
│  波动目标(滞后实现波动,只缩不放)· 趋势软开关 · 宏观风险拨盘     │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L5 验证(上线前必过)────────────────────────────────────────────┐
│  PIT 审计 · n_eff/HAC · Deflated Sharpe · CSCV-PBO · t>3 · 2022 holdout │
└───────────────────────────────┬──────────────────────────────────┘
                                ▼
┌─ L6 feed + 看板 + 月度 routine ───────────────────────────────────┐
│  feed/longterm/*.json → /intel(或 /longterm)· monthly-studies.yml │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. L0 数据底座

### 2.1 EDGAR PIT 基本面(新 `scripts/edgar_fundamentals.py`)
- 端点(已实测,见 sec-edgar-xbrl 报告):`data.sec.gov/api/xbrl/companyfacts/CIK##########.json`、`companyconcept`、`frames/us-gaap/{tag}/USD/CY####Q#I.json`;ticker→CIK 用 `company_tickers.json`(`cik_str` 整数需补零 10 位)。
- **PIT 锚**:每条事实自带 `filed`;时点(资产负债表)无 `start`,时段(损益)有 `start`。**用 `filed ≤ as_of` 切片**。
- **防重述泄漏**:剔除无 `frame` 标记的比较列事实(活例:AAPL `end=2025-09-27` 出现在更晚 `filed=2026-01-30` 的下一年申报里);或落地到季度 **Financial Statement Data Sets** 冻结 vintage。
- 工程惯例:复用 `funds_13f.py` 的 SEC `User-Agent`(含联系邮箱)+ ≤10 req/s + accession 幂等 + 纯标准库。
- 关键 us-gaap 标签(带回退链)见各报告字段表:`Revenues`/`RevenueFromContractWithCustomerExcludingAssessedTax`、`NetIncomeLoss`、`OperatingIncomeLoss`、`GrossProfit`/(`Revenues`−`CostOfRevenue`)、`Assets`、`StockholdersEquity`、`CashAndCashEquivalentsAtCarryingValue`、`LongTermDebtNoncurrent`、`NetCashProvidedByUsedInOperatingActivities`、`PaymentsToAcquirePropertyPlantAndEquipment`、`PaymentsForRepurchaseOfCommonStock`、`dei:EntityCommonStockSharesOutstanding`。

### 2.2 宏观拨盘(新 `scripts/macro_fred.py`)
- FRED series:`T10Y3M`/`T10Y2Y`(曲线)、`BAMLH0A0HYM2`(HY OAS,主驱动)、`NFCI`/`ANFCI`(金融条件)、`SAHMREALTIME`(劳动,**必须用 REALTIME 防前视**)、`USREC`。
- **弃用** ISM/PMI、Conference Board LEI(已从 FRED 下架/版权,违反免费+PIT 约束)。
- 回测用 ALFRED `realtime_start/end` vintage;输出 `feed/macro/latest.json`(连续 `risk_dial` + 分项贡献)。

### 2.3 缺口(诚实标注)
- **分析师预期/修正**几乎无真·免费·PIT 源(Yahoo 仅当前快照=回测前视)。修正因子(underreaction,最稳健)**搁置**至有付费 PIT 数据(I/B/E/S/Sharadar)或自建 surprise 近似。

---

## 3. L1 因子库(多头腿)

每个 bucket 是若干子因子的 rank-z 等权合成。**等权是默认**;任何非等权要过 BY-FDR + |t|≥3。

### 3.1 价值 bucket(便宜度做主驱动)
- `ep` = 净利/市值;`ebit_ev` = EBIT/EV(Magic Formula 腿 / Acquirer's Multiple);`fcf_ev` = (CFO−CapEx)/EV;`npy` = (股息+净回购−增发)/市值(股本法,吸收 SBC);`bm_intan` = 无形资产调整后账面市值比。
- `rim_val` = RIM 分档:`V0 = B0·(ROE−g)/(r−g)`(账面值锚,终值不敏感);出便宜/合理/贵三档,不出点估;reverse-DCF 反推隐含增长率做合理性闸。

### 3.2 质量/复利 bucket(硬过滤 + 加权双用)
- `gp_a` = (营收−COGS)/总资产(Novy-Marx);`cash_op` = 现金型经营利润/资产(吞并应计、延伸预测 10 年,**落地首选**);`roic`;`qmj` 四维代理(盈利+成长+安全+派息)。
- `compounder` = z(ROIC) + z(再投资率) + z(毛利稳定) − z(杠杆),**估值护栏**:估值>历史 80 分位则封顶(避免为质量付过高价,Nifty Fifty 教训)。复利数学 `g=ROIC×再投资率`。

### 3.3 动量 bucket(分散腿)
- `mom_12_1`(已有 `factors_xs.py`)、`hi52`(52 周高点接近度,已有);可选 `factor_mom`(因子自身时序动量,比 value-spread 择时稳健)。

### 3.4 低波 bucket(为复利,多头腿)
- `lowvol`(已有 `factors_xs.py`)/ trailing beta;价值在更高几何收益/更低回撤;监控拥挤(因子估值价差 gate)。

### 3.5 剔除闸(硬规则,下行保护,**非 alpha**)
- `Altman Z'' < 阈值`(破产风险,跨行业版,纯免费可算);`Beneish M-Score > −1.78`(盈余操纵);`Sloan 应计`高分位降权;`Piotroski F-Score` 地板;伪回购惩罚(回购金额 vs 股本实际下降背离)。
- 金融/REIT/公用事业**豁免**(指标不适用)。这些是**剔除/降权**,不进综合分加权。

### 3.6 外部二次确认(不独立下注)
- Form 4 内部人**集群/机会型买入**(`code=P & 获得=A`,新 `scripts/insiders_form4.py`);13F 增持(45 天滞后,仅确认);挂在已有候选上做置信加权。

---

## 4. L2 合成 LongScore

复用 `factor_pipeline.py` 的 `winsorize 3σ → standardize → neutralize[行业 dummies + 规模]` 与 `factor_factory.py` 的 rank-z + 六门控:

```
LongScore = mean_z( value_bucket, quality_bucket, momentum_bucket, lowvol_bucket )
            applied AFTER 剔除闸 (Z''/M-Score/F-Score)
```
- **integrated 骨架 + 温和暴露**:本系统多头腿处 AQR vs Ghayur-Heaney-Platt 两曲线临界点 → 用单一综合分(integrated)做骨架,但保持温和因子暴露、行业中性、不极端集中、**不机械剔除"互相抵消"的票**。
- 顺序筛选(先价值再质量)是 mixing 的有损极端 → 改为质量作连续交互项(Piotroski 提纯价值),不做硬筛。

---

## 5. L3 组合构建

- 取 LongScore 顶 decile/quintile;**每腿 ≥50 票**(消大部分可分散波动 + 维持因子广度)。
- **等权默认**(DeMiguel 1/N 基线);权重优化须证明扣估计误差后仍胜等权,否则否决。
- **带宽再平衡**:相对带 ±20% + 月/季周期检查("look often, trade rarely");对接已有 Garleanu-Pedersen aim(部分向 aim 交易=带宽的连续形式)。
- **税后换手预算**:不主动实现收益、收割亏损(wash sale ±30 天)、用新钱补再平衡;仓位用分数 Kelly(半 Kelly)与容量地板取 min。

---

## 6. L4 风险叠加(总敞口层)

- **波动目标**:对**组合总敞口**用滞后 60 日实现波动 `vol_scale=clip(target/realized, 0.3, 1.0)`;**只缩不放**(无杠杆下平静牛市纯减仓=已知拖累代价)。**禁止对横截面因子做 vol-scale**(Moreira-Muir OOS 失败)。
- **趋势软开关**:复用 `feed/market/state.json`(SPY>200dma + 波动 + 广度);连续杠杆 1.0/0.7/0.4,非全进全出。
- **宏观风险拨盘**:`feed/macro/latest.json` 的 `risk_dial`(信用>曲线>FCI>劳动),滞回防抖。
- **2022 早警**:监控 `stock_bond_corr_60d`(股债相关翻正使 All Weather/风险平价失效,唯时序趋势对冲住)。
- **板块**:RRG 倾斜 ±5-10pp + 板块上限 + 季度再平衡;**不押周期相位**(无 alpha+前视)。

---

## 7. L5 验证纪律(上线前必过 7 关)

> 见 `research/long-term/README.md` §统一验证纪律;强化已有 `validation.py`/`study_pbo.py`。

1. **PIT 审计**:`filed ≤ as_of` + 时点成分 + 回测域含退市/破产票。
2. **有效样本**:报告 `n_eff≈n/H`;重叠收益 Newey-West/Hansen-Hodrick HAC;对照 BRW 零假设。
3. **多重检验**:Deflated Sharpe(按 N 通缩)+ CSCV-PBO + BY-FDR + |t|≥3;登记回测次数。
4. **真 holdout**:**2022 必入样本外**;holdout 恶化即淘汰。
5. **增量价值**:对 HML/RMW/UMD/系统现有因子正交化后仍有独立 Rank-IC;否则换皮否决。
6. **净·扣成本+税后**唯一货币;毛收益打 3-5 折。
7. **幸存者自查**:含退市 PIT 全集 vs 当前成分股 alpha 差 = 偏差量级上界。

---

## 8. L6 feed + 看板 + routine

- `feed/longterm/`:`longscore.json`(顶档名单+分档+贡献分解)、`buckets.json`(各 bucket 暴露)、`exclusions.json`(被剔除闸拦下的票+原因)、`risk.json`(波动目标/趋势/宏观拨盘当前值)。
- 看板:`/intel` 新增"🏛 长期腿"卡,或新建 `/longterm` 页(顶档名单 + 因子暴露雷达 + 剔除原因 + 风险拨盘)。
- routine:`routines/longterm-monthly.md`(Claude 可执行 playbook)+ 接入 `monthly-studies.yml`(月度跑 + 防参数漂移)。

---

## 9. 分期路线图

| 阶段 | 交付 | 验收 |
|---|---|---|
| **L-1 数据底座** | `edgar_fundamentals.py`(PIT 面板,~500 美股大盘起步)+ `macro_fred.py` | 任意 `as_of` 取出无前视的三表;`filed≤as_of` 不变量 CI 通过 |
| **L-2 单因子落地** | 质量(`cash_op`/`gp_a`)+ 价值(`ebit_ev`/`npy`)+ 剔除闸(Z''/M-Score)进 `factors_xs.py` | 各子因子 Rank-IC + 分层单调 + 对 RMW/HML 正交增量;2022 holdout |
| **L-3 合成 + 组合** | `LongScore` 综合分 + `xs_portfolio.py` ≥50 票等权带宽 | integrated vs mixing vs screening 三对照;净·扣成本胜等权基准 |
| **L-4 风险叠加** | 总敞口波动目标 + 趋势/宏观软开关 + `stock_bond_corr` 早警 | 净·扣成本下降回撤,**不宣称 alpha**(降回撤即合格) |
| **L-5 feed/看板/routine** | `feed/longterm/*` + `/longterm` 面板 + 月度 routine | feed 校验闸通过;看板展示顶档+剔除原因+风险拨盘 |
| **L-6 增强(可选)** | 内部人/13F 二次确认;LLM 抽取器(过门控);加密 DCA 倾斜;A 股 CH-3/CH-4 | 每项独立过 7 关验证,不过则降级为展示/否决 |

**诚实预期**:多数因子扣成本+发表衰减后增量有限;长期腿的现实价值大概率是**容量大、换手低、回撤更可控的稳健复利**,而非高 alpha。任何"跑赢"结论都要过 §7 七关,否则只当展示。

---

## 10. 与现有红线一致

沿用 `self-improving-alpha-loop.md` 的 R4-R9:净成本唯一货币(R4)· 真 holdout + 预注册(R5)· LLM 产出必须可审计可删除(R6)· 拥挤先减仓(R7)· 容量以扣冲击定义(R9)。LIS 的每一层都以"净·扣成本、可审计、可证伪、可删除"为准绳。
