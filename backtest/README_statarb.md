# 流 B —— 条件因子统计套利 做多/做空引擎(`statarb.py`)

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

这是按设计文档(US Equity Mid-Frequency Hybrid Quant System v1.0)**优化后的做多做空逻辑**,
取代旧 `xs_portfolio.py` 的「raw 因子分层多空」(那是流 A:毛口径、含幸存者偏差、无成本)。

## 它实现了报告的哪些核心要求

| 设计文档 | 本引擎实现 |
|---|---|
| §3.1 真 alpha = 定价错误(残差均值回归) | 每只股票对 `[SPY, 行业 ETF]` 滚动回归取**残差**,残差累积过程 = 套利状态变量 |
| §6.2.2 流 B 三步 | ①条件因子残差 → ②OU `s-score=(X−m)/σ_eq` → ③扣成本仓位 |
| Avellaneda-Lee(2010) | AR(1) 反解 OU:κ、半衰期 `ln2/κ`、均衡均值 m、σ_eq;滞回开/平(s_open=1.25 / s_close=0.5) |
| §6.5 Garleanu-Pedersen aim 组合(D2) | `w_t = w_{t-1} + trade_rate·(target−w_{t-1})` + 无交易带 —— **换手匹配半衰期** |
| §7.3 / D13 协整断裂熔断 | Hurst>0.55 / 半衰期出 [5,25] / 极端 s → 立即排除,**禁止「会回归」式向下加仓** |
| §7.1 分层限额 | 单股 ≤4%、行业(软)中性 + 净暴露 ≤12%、毛杠杆封顶、**美元中性**(实现簿钉回) |
| §6.5 容量地板(D6/R9) | `costs.py` ADV 参与率封顶(≤5% ADV)+ 平方根冲击律,**诚实降规模不重分配** |
| §3.8 净成本(R4) | `costs.py` 价差 + `Y·σ·√(参与率)` 冲击;**净·扣成本是唯一裁决口径** |
| §6.7 防过拟合 | `validation.py` Deflated Sharpe(扣申报试验次数)+ Hurst + 最大回撤;L6 风格 `verdict` |

## 运行

```bash
cd backtest
python -c "import data,statarb as sa; data.fetch_universe(sa.DEMO_UNIVERSE+sa.SECTOR_ETFS+['SPY'])"  # 下载
python statarb.py            # 跑引擎,打印净·扣成本绩效 + 当前持仓簿 + L6 裁决
```

或经 routine 产出结构化报告写入 `feed/`:`python ../scripts/run_routine.py`。

## 诚实结论(与 `FEATURES.md` 一致)

在**可得免费数据**(Yahoo 日线、当前流动大盘 ~115 只、含幸存者偏差)上,2021–2026:

> 残差均值回归有**微弱毛边际**(毛 Sharpe ~0),但**扣成本后净 Sharpe 为负**;Deflated Sharpe≈0。
> 按 R4「净成本是唯一货币」**应淘汰** —— 这恰好**实证了设计文档第 10 章的核心论点**:
> 真 alpha 在**容量受限的冷门层**(巨头进不来),而免费数据 + 拥挤大盘**触及不到**那一层。

引擎本身(残差 + OU + aim + 熔断 + 容量 + 净成本 + DSR)是**正确且可复用**的脚手架;
要让它转正,需要的是**更冷门的 universe + PIT 数据 + 更干净的条件因子**,而非更复杂的模型(D7/D8)。

## 参数(`StatArbParams`,均为经济动机默认,非按结果调参 —— 见 R5)

`window=60`(估计窗)、`s_open/s_close=1.25/0.5`(滞回)、`hl∈[5,25]`(半衰期)、`hurst_max=0.55`(熔断)、
`name_cap=0.04`、`sector_cap=0.12`、`gross_leverage=1.0`、`max_positions=80`、`trade_rate=0.15`、
`max_participation=0.05`、`half_spread_bps=5`、`impact_Y=0.5`、`n_trials=200`(DSR 申报试验次数)。
