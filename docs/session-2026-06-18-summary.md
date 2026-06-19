# 会话工程总结(2026-06-18)— LIS 长期投资系统 + 中频引擎补强

> 接力文档:下个 session 开工前读这份 + [`iteration-log.md`](iteration-log.md) Cycle 12-17,避免重复劳动。
> 本会话从「持续调研 + 调用 20+ agent」起,落成完整的**长期投资系统(LIS)**,并补强中频引擎的
> 三处净成本/偏差缺口。**贯穿纪律:每个模块内建诚实裁决——能赚报喜,不能赚明确否定并拒绝接入(R5/R10)。**

---

## 1. 一句话成果

- **调研**:24 个并行 agent → 24 篇带源调研 + 2 篇综合设计([`research/long-term/`](../research/long-term/README.md))。
- **LIS 全栈**:数据底座(EDGAR PIT + FRED)→ 因子/剔除闸 → 合成 LongScore → `/longterm` 看板 → L-5 验证。
- **中频补强**:PIT 成分过滤、meta-labeling(L2)、借券费/做空可行性模型 + 引擎集成。
- **规模**:~44 提交、8 套单测(160+ 断言)全绿、3 条新工作流;全部 push `claude/investment-system-agents-x17liw`。

---

## 2. 建了什么(模块 → 文件 → 诚实裁决)

### 2.1 长期投资腿(LIS)
| 模块 | 文件 | 诚实裁决 |
|---|---|---|
| EDGAR PIT 基本面 | `scripts/edgar_fundamentals.py` | ✅ 可用;`filed≤as_of` 防重述、防拆股股数;Visa 类多类股/陈旧标签诚实置 None |
| 宏观风险拨盘 | `scripts/macro_fred.py` | ✅ FRED keyless;只做温和拨盘非择时 |
| 三剔除闸 | `backtest/factors_fundamental.py` | ✅ Altman Z''/Beneish M/Piotroski F;**双确认**防 NVDA 类高增长假阳性 |
| 价值因子 | `backtest/factors_value.py` | ✅ E/P, EBIT/EV, 净股东收益(需价格 join) |
| 质量+价值合成 | `scripts/longterm_screen.py` | ✅ LongScore(bucket rank-z 等权 integrated) |
| 看板 | `frontend/app/longterm/page.tsx` | ✅ 候选/宏观/验证三卡 + 逐期 IC 表 |
| **L-5 验证** | `backtest/study_longscore.py` | ⚠ **裁决:无可证明 alpha**(见下) |

### 2.2 中频引擎补强
| 模块 | 文件 | 诚实裁决 |
|---|---|---|
| PIT 成分过滤 | `backtest/pit_membership.py`(+ xs_backtest/factor_pipeline 接入) | ✅ 消前视性成员偏差;实测 |IC| 向 0 收 |
| meta-labeling L2 | `backtest/meta_label.py` + `study_meta_label.py` | ⚠ **OOS AUC 0.479 → 否定,不接入下注层** |
| 借券费/做空可行性 | `backtest/costs.py`(借券模型)+ `study_short_feasibility.py` | ✅ 模型可用;S&P600 仍 GC,真借券墙在微盘 |
| 借券费引擎集成 | `backtest/statarb.py`(`borrow_costs`) | ✅ 空头净成本不再低估;上报 `borrow_cost_ann` |

---

## 3. 核心科学结论(诚实负面结果,已归档)

### 3.1 LongScore(长期腿)无可证明 alpha
`study_longscore.py` 跨 3 个 universe + 正交化 + PIT + 剔除闸功效:

| 测试 | NDX100 | 价值均衡+PIT | 小盘 S&P600 |
|---|---|---|---|
| LongScore IC (t) | +0.047 (1.17) | +0.046 (0.84) | +0.029 (0.56) |
| 价值腿 IC | −0.035 | +0.005 | −0.0005 |
| **⊥动量/规模增量** | +0.033 (0.71) | **−0.025 (−0.46)** | −0.022 (−0.53) |

- LongScore IC **不显著**(t<1.2),**对动量/规模正交后增量≈0/为负**(抛硬币)。
- 价值腿**强 universe 依赖**:成长指数里负、均衡里≈0(印证调研)。
- 剔除闸下行保护**无法在免费数据检验**(被剔除名+89.5% 是幸存者偏差——暴雷者退市无数据)。
- → `/longterm` **永远只是候选展示**,不进交易层。

### 3.2 meta-labeling 在 statarb 信号上零预测力
9406 入场样本,OOS AUC=0.479(<0.5)、单特征 |s| AUC=0.50 → OU 特征对「哪笔反转会赚」无信息。

### 3.3 「下沉救 alpha」在 S&P600 层面证伪(但非借券所致)
S&P600 有流动性入选门槛 → 空头仍 GC(借券 0.1%/年,0 不可做空);下沉净增益**扣借券前就为负**。
真正的借券墙在 S&P600 以下的微盘——需 microcap universe + 真实 borrow rate 才咬合。

---

## 4. 数据瓶颈(为何停在这里——不是能力问题,是数据问题)

这套系统的诚实结论高度受限于**免费数据**。要突破,需以下付费/难获数据:

| 想验证的事 | 缺的数据 | 出处 |
|---|---|---|
| 剔除闸下行保护是否真有效 | **含退市/破产票的 PIT 行情**(blowups 不能缺席) | Norgate $50/月 / CRSP |
| 价值/质量因子真实 alpha | **更广 universe + 含退市 PIT 基本面** | Sharadar SF1 / Compustat PIT |
| 分析师修正因子(调研指最稳健) | **PIT 分析师预期/修正** | I/B/E/S(贵) |
| 「下沉救 alpha」+ 借券墙 | **microcap universe + 真实 borrow rate / locate** | 券商 / Ortex |
| OFI/盘口执行层 | **分钟级逐笔/盘口**(美股免费源无) | 券商 LV2 |

**继续在免费数据上硬做这些会变成无数据支撑的空壳——违背 R10。已登记待办池。**

---

## 5. 下个 session 怎么接力

**若拿到上述任一付费数据源**:
1. 把 `data.py` 换成含退市票的 PIT 行情源 → 重跑 `study_longscore` / `xs_backtest`(PIT 过滤已就位),
   消幸存者偏差后看因子是否还活;`study_short_feasibility` 换真实 borrow rate。
2. `study_meta_label` 的标签/特征管线已通用,换更强主信号(如有真 alpha 的因子)即可复用。
3. 分析师修正数据到位 → 在 `factors_value`/`longterm_screen` 加 revisions bucket(调研指最稳健的免费缺口)。

**纯免费数据内仍可做的合规增量**(不违背纪律):
- 看板/文档打磨;把 `study_longscore` / `study_short_feasibility` 接月度 CI 自动刷新(longscore 已接 monthly-studies)。
- 给更多既有研究脚本补对动量/规模的正交增量检验(meta_label/neutralize 工具已通用)。

**红线提醒**:不要为了让任何 IC/AUC 转正而在样本内调权重/阈值——那是系统反对的过拟合。
任何「转正」都须:预注册 → 真 holdout(2022 入)→ Deflated Sharpe/CSCV-PBO → 净·扣成本 → 正交增量,全过才接受。

---

## 6. 测试与运维

- **单测(8 套 160+ 断言,全进 `tests.yml` 闸门)**:edgar_fundamentals / factors_fundamental / factors_value /
  longterm_screen / macro_fred / pit_membership / meta_label / costs_borrow。
- **工作流**:`longterm-screen.yml`(月度 LIS 刷新)、`monthly-studies.yml`(加 L-5 验证)、`tests.yml`(加长期腿+PIT+meta+borrow 单测)。
- **feed**:`feed/longterm/`(longscore/validation/meta_label/short_feasibility)+ `feed/macro/latest.json`,接 `feed_lib` 新鲜度。

> ⚠️ 全部研究/演示用途,**非投资建议**。诚实是这套系统的第一原则。
