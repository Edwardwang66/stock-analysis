# 长期投资系统 — 深度调研合集与横向综合

> 24 篇并行 agent 调研(2026-06-18)的索引 + **跨报告的元结论**。
> 方法:24 个独立 agent 各做一路 fan-out 网络检索 + 对抗式核验,房子风格统一:
> **诚实可证伪 · 净·扣成本为唯一货币 · 每条关键结论标一手来源 URL + 可信度 · 显式标注样本内/前视/幸存者偏差 · 偏好免费且可 PIT 的数据源。**
> 配套落地设计见 [`../../docs/long-term-investment-system.md`](../../docs/long-term-investment-system.md)。

本合集的定位:现有系统是**中频做多做空 stat-arb**(`backtest/statarb.py`,实证净 alpha≈0/负——真 alpha 在容量受限冷门层)。
长期投资腿(持有期数月至数年)是**互补的第二引擎**:换手低、容量大、靠基本面广度 + 合成 + 防过拟合纪律,
而非择时或单因子"高命中率"。本合集为这条腿钉证据、定边界、给落地。

---

## 📑 报告索引(24 篇)

### A. 选股因子(多头腿的 alpha 来源)
| 文件 | 主题 | 一句话结论 |
|---|---|---|
| [value-investing-frameworks.md](value-investing-frameworks.md) | 价值框架量化(Graham/Magic Formula/F-Score/Acquirer's Multiple) | 2014 起 Magic Formula 几乎无一年跑赢;深度价值>质量-价值;F-Score 是**陷阱过滤器**非独立 alpha;HML 被 FF5 的 RMW+CMA 部分吸收 |
| [quality-moat-factors.md](quality-moat-factors.md) | 质量因子与护城河(毛利率/ROIC/QMJ) | **质量是少数扣成本后仍存活的因子**(换手<50%/月);护城河=ROIC−WACC 利差×**持续时长**;现金型经营利润吞并应计异象、可延伸预测 10 年 |
| [compounders-quality-growth.md](compounders-quality-growth.md) | 优质复利机器(Fundsmith 式) | `g=ROIC×再投资率`;Buffett alpha 1976-2011 夏普 0.76,**控制 BAB+QMJ+杠杆(1.6:1)后 alpha 转不显著**;估值纪律决定成败 |
| [shareholder-yield-buybacks.md](shareholder-yield-buybacks.md) | 股息/回购/总股东收益 | **Net Payout Yield**(股息+净回购)比股息率稳健(Boudoukh JF 2007);单买高息踩陷阱;回购须用股本法吸收 SBC 稀释 |
| [long-horizon-momentum-trend.md](long-horizon-momentum-trend.md) | 长周期动量与趋势 | 12-1 动量稳健但有崩盘(2009);时序动量/趋势是回撤护栏;价值×动量负相关 ~−0.5,50/50 提夏普 |
| [factor-valuation-timing.md](factor-valuation-timing.md) | 因子择时与估值价差 | 激进择时易过拟合;**因子动量**(Ehsani-Linnainmaa)是更稳健、更"免费"的择时;value spread 是慢变赔率非精确开关 |
| [factor-combination-multifactor.md](factor-combination-multifactor.md) | 多因子整合 vs 混合 | 文献**有争议**:高暴露下 integrated 胜(AQR),低暴露下 mixing 胜(Ghayur-Heaney-Platt);本系统处临界点→integrated 骨架+温和暴露 |
| [dcf-intrinsic-value-automation.md](dcf-intrinsic-value-automation.md) | 内在价值自动化 | 纯自动 DCF=garbage-in(终值占 60-80%);用 **RIM(残差收益)**做骨架(账面值锚,终值不敏感);出**便宜/合理/贵分档**而非点估 |

### B. 风控与剔除(下行保护)
| 文件 | 主题 | 一句话结论 |
|---|---|---|
| [accruals-earnings-quality.md](accruals-earnings-quality.md) | 盈余质量/造假规避(Sloan/Beneish/Altman) | 这类指标的价值在**剔除/下行保护,不在 alpha**;应计多空 alpha 2003 后被套利侵蚀;M-Score/Z'' 作硬剔除规则 |
| [low-vol-defensive.md](low-vol-defensive.md) | 低波/防御异象 | BAB 长期夏普 ~0.78(19 国);**alpha 在多头腿**(利好不做空的长期持有者);拥挤+估值抬升是当前实活风险 |
| [risk-drawdown-management-longterm.md](risk-drawdown-management-longterm.md) | 回撤与风险管理 | **唯一稳健的是对总敞口做波动目标**(Harvey 2018);禁止对横截面因子 vol-scale(Moreira-Muir OOS 失败);序列风险是"保护有真实数学价值"的最强场景 |
| [backtesting-longhorizon-pitfalls.md](backtesting-longhorizon-pitfalls.md) | 长周期回测统计陷阱 | **长样本期 ≠ 多独立样本**(n_eff≈n/H);重叠收益虚高显著性;HAC 非万能;Deflated Sharpe 对低频惩罚最重 |

### C. 配置与择时(温和的风险拨盘)
| 文件 | 主题 | 一句话结论 |
|---|---|---|
| [asset-allocation-regime.md](asset-allocation-regime.md) | 资产配置与市场状态 | 系统已有克制的 PIT-clean regime;2022 股债相关翻正使 All Weather/风险平价失效,**唯时序趋势对冲住**;只做软开关+波动目标,不上 HMM |
| [macro-leading-indicators.md](macro-leading-indicators.md) | 宏观领先指标 | 宏观择时记录差(Goyal-Welch 样本外 R²≈0);只做温和风险拨盘;FRED+ALFRED vintage 防前视;ISM/LEI 已从 FRED 下架(版权) |
| [sector-industry-rotation.md](sector-industry-rotation.md) | 行业/板块轮动 | **周期相位轮动=无 alpha+前视陷阱**;板块动量(RRG 倾斜)有正记录但脆弱,季度再平衡;集中度均值回归(IT ~33%)是尾部风险 |
| [behavioral-sentiment-contrarian.md](behavioral-sentiment-contrarian.md) | 行为/情绪/逆向 | 情绪极值=温和逆向温度计非触发;**分析师修正最稳健可落地**(underreaction);逆向与顺势必须分层否则自抵消 |

### D. 数据底座与外部信号
| 文件 | 主题 | 一句话结论 |
|---|---|---|
| [sec-edgar-xbrl-fundamentals.md](sec-edgar-xbrl-fundamentals.md) | EDGAR XBRL 构建 PIT 基本面 | 端点全部实测;每条事实自带 `filed` 字段=PIT 锚;**比较列/重述泄漏有活例**(无 `frame` 标记);bulk zip 可用 |
| [free-fundamental-data-landscape.md](free-fundamental-data-landscape.md) | 免费基本面数据全景 | **EDGAR 是唯一真·免费·PIT·可重分发的基本面源**;分析师预期/修正几乎全付费(系统的真缺口);Sharadar SF1 是低成本 PIT 兜底 |
| [insider-13f-smart-money.md](insider-13f-smart-money.md) | 内部人交易与 13F | 集群买入/高管买入较强;13F 跟单受 45 天滞后衰减;价值在做质量/价值候选的**二次确认**,非独立 alpha |
| [international-em-diversification.md](international-em-diversification.md) | 国际/新兴市场分散 | 最优本土权重 ~30-35%;分散是结构性尾部保险非危机对冲(危机相关上升);**中国 A 股动量反转**需 CH-3/CH-4;AkShare 最佳免费 A 股源 |
| [crypto-longterm-onchain-valuation.md](crypto-longterm-onchain-valuation.md) | 加密长期链上估值 | MVRV/NUPL **同根共线**(非独立佐证);**S2F 已证伪**;halving 仅 n=3;只做有界 DCA/再平衡倾斜;CoinMetrics Community API 免费 |
| [thematic-secular-growth.md](thematic-secular-growth.md) | 主题/结构性成长 | **基金发行≈主题顶部**(专门化 ETF 发行后 5 年风险调整 −30%,RFS 2023);15 年仅 ~9% 主题基金存活+跑赢;护栏=发行后/估值/盈利兑现三闸 |
| [ai-llm-fundamental-agents-2026.md](ai-llm-fundamental-agents-2026.md) | LLM 基本面 agent(2025-26) | 净证据强烈倾向**"LLM 选股=泄漏"**(Profit Mirage 夏普衰减 51-62%);LLM 真价值在**文本→结构化抽取+假设生成**;禁止让 LLM 给方向/定仓位/产数值 |

---

## 🧭 跨报告元结论(20 条,这是真正的产出)

把 24 路证据收敛成可执行的判断。每条都已在对应报告里钉源,这里只给结论与落地方向。

### 哲学与边界
1. **没有魔法**:长期方向命中率上限同样受 IC 约束(见仓内 `quant-factor-deep-research.md`)。长期腿的护城河 = **广度 × 合成 × 防过拟合纪律**,不是单因子准。
2. **长期 ≠ 更可靠的错觉**:20 年月度、持有期 H 年 → 有效独立样本 ≈ 20/H。重叠收益让显著性虚高,Deflated Sharpe 对低频惩罚最重。**长周期策略的验证门槛要更高,不是更低。**
3. **LLM 不进决策链**:2025-26 证据(Profit Mirage / Memorization / Lookahead)显示 LLM 直接预测=泄漏。LLM 只做**抽取器 / 假设生成器 / RAG 检索器**,产出必须 operationalize 成可审计公式因子再过门控。

### 因子设计(多头腿)
4. **质量是长期腿的结构性优势**:换手低(<50%/月)、容量大、扣成本后存活。优先**现金型经营利润 / 毛利率(GP/A) / ROIC**,而非易被套利的纯应计。
5. **价值用便宜度做主驱动,质量做硬过滤**:深度价值(EV/EBIT、Acquirer's Multiple)历史>质量-价值;但纯深度价值踩陷阱多,用 F-Score / Z'' / M-Score 做**剔除闸**而非加权。
6. **股东收益用 Net Payout Yield**:股息+净回购−增发,股本法吸收 SBC 稀释;单买高息是陷阱。
7. **动量是稳健的分散腿**:12-1 + 52 周高点接近度;价值×动量负相关 ~−0.5,合成提夏普。**因子动量**比 value-spread 择时更稳健。
8. **低波的 alpha 在多头腿**——对不做空的长期持有者正好可用,价值是**更高几何收益/更低回撤=更好复利**,但要监控拥挤/估值抬升。
9. **合成用 integrated 骨架 + 温和暴露**:winsorize 3σ → 行业+规模中性 → rank-z → 等权综合分;**等权是默认**(DeMiguel 1/N),任何非等权要过 BY-FDR + |t|≥3 并计入试验预算;不要机械剔除"互相抵消"的票(吸收 Ghayur-Heaney-Platt 教训)。
10. **估值用 RIM 出分档**:残差收益模型(账面值锚)比 FCF-DCF 终值稳健;产出便宜/合理/贵**分档**,不出点估;reverse-DCF 反推隐含增长率做合理性检查。

### 风控与配置(温和拨盘,不是择时)
11. **波动目标只作用于总敞口**(Harvey 2018 稳健),用滞后实现波动,只缩不放(若无杠杆,平静牛市会退化为纯拖累——这是已知代价)。**禁止对横截面因子做 vol-scale。**
12. **趋势/regime 做软开关**:复用已有 `feed/market/state.json`(SPY>200dma + 波动 + 广度);连续杠杆 1.0/0.7/0.4 而非全进全出;加 `stock_bond_corr_60d` 早警 2022 类失效。
13. **宏观只做风险拨盘**:FRED 信用利差(HY OAS)>曲线>金融条件>劳动;ALFRED vintage 防前视;弃用已下架的 ISM/LEI。
14. **板块不押相位**:周期相位轮动无 alpha+前视;只做 RRG 倾斜(±5-10pp)+ 板块上限 + 季度再平衡;监控集中度均值回归尾部风险。

### 组合工程
15. **宽 + 等权 + 带宽再平衡**:每腿 ≥50 只、等权默认、相对带 ±20% + 周期检查("look often, trade rarely");再平衡溢价小且对成本/税敏感。
16. **税后换手预算**:不主动实现收益、收割亏损(wash sale ±30 天)、用新钱补再平衡;分数 Kelly(半 Kelly 保留 ~75% 增长、减半波动)。
17. **国际是结构性尾部保险**:本土 ~30-35%,几何收益提升有限但降单国尾部;A 股需 CH-3/CH-4(动量反转),用 AkShare。

### 数据底座(决定一切的地基)
18. **EDGAR 是唯一真·免费·PIT·可重分发的基本面源**:用 `filed` 日对齐、冻结季度 vintage(Financial Statement Data Sets)防重述泄漏;比较列/无 `frame` 标记的事实要剔。
19. **分析师修正是最有价值但最贵的缺口**:免费源(Yahoo 快照)用于回测=前视。修正因子(underreaction,方向惯性 ~83%)值得投入,但需付费 PIT 数据或先搁置。
20. **外部信号做二次确认而非独立 alpha**:13F(45 天滞后衰减)、内部人集群买入、链上 MVRV(同根共线、小样本)——都挂在已有候选上做确认/温度计,不单独下注。

---

## 🔬 统一验证纪律(所有长期因子上线前必过)

沿用并强化系统已有的防过拟合栈(`backtest/validation.py` / `study_pbo.py`):

1. **PIT 审计**:基本面用 `filed ≤ as_of`;价格用时点成分(`pit_membership.py`);回测域含已退市/破产票。
2. **有效样本修正**:报告 `n_eff≈n/H`;重叠收益用 Newey-West/Hansen-Hodrick HAC;对照 BRW(2008)零假设(长 horizon R² 本就虚高)。
3. **多重检验**:Deflated Sharpe(按试验数 N 通缩)+ CSCV-PBO + BY-FDR + |t|≥3(非 2.0);登记所有回测次数。
4. **真 holdout**:**2022 必须入样本外**(股债相关翻正的压力测试);holdout 恶化即淘汰。
5. **增量价值**:对已有因子(HML/RMW/UMD/系统现有因子)正交化后仍有独立 Rank-IC;否则是换皮重复下注,否决。
6. **净·扣成本**:扣冲击+借券+税后为唯一裁决货币;毛收益一律打 3-5 折(McLean-Pontiff 发表后衰减)。
7. **幸存者自查**:含退市 PIT 全集 vs 当前成分股的 alpha 差,作为偏差量级上界。

---

## 📍 与现有系统的接缝

- **数据**:新增 `scripts/edgar_fundamentals.py`(PIT 基本面面板)、`scripts/macro_fred.py`(宏观拨盘);复用现有 `funds_13f.py` 的 SEC UA + 幂等 + stdlib 惯例。
- **因子**:扩 `backtest/factors_xs.py` / `factor_factory.py`(已有 winsorize/中性化/rank-z/六门控管线)增长期 bucket;`factor_pipeline.py` 接 PIT 过滤。
- **组合/风控**:`xs_portfolio.py` 加 ≥50 票等权+带宽;`statarb.py` 的波动目标选项复用到总敞口层。
- **feed/看板**:`feed/longterm/*.json` + `/intel`(或新 `/longterm`)面板;月度 `routines/` playbook + `monthly-studies.yml` 定时。
- **完整落地蓝图与分期路线图** → [`../../docs/long-term-investment-system.md`](../../docs/long-term-investment-system.md)。

---

> ⚠️ 全部为信息研究,**非投资建议**。所有自报/二手数字按房子规则打折,未核实项已在各报告内显式标注。
