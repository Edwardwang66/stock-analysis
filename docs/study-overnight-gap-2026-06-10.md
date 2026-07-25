# 隔夜缺口研究:HIP-3 永续盘后走势的信息含量(2026-06-10)

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

| 资产对 | 天数 | 代理 corr | 方向命中 | MAE | 盘后走势→开盘后盘中 corr |
|---|---|---|---|---|---|
| xyz:SP500 → SPY | 56 | +0.981 | 96% | 9bps | +0.014 |
| xyz:XYZ100 → QQQ | 140 | +0.977 | 91% | 13bps | -0.128 |
| xyz:MU → MU | 115 | +0.975 | 91% | 60bps | +0.041 |
| cash:NVDA → NVDA | 93 | +0.960 | 91% | 28bps | -0.022 |
| cash:GOOGL → GOOGL | 91 | +0.948 | 84% | 35bps | -0.104 |
| cash:INTC → INTC | 89 | +0.947 | 91% | 79bps | -0.050 |

**Q1 代理质量**:平均 corr=+0.965 —— 成立:看板「盘后代理」功能有真实信息。
**Q2 信号价值**:合并 584 天,盘后走势→开盘后盘中收益 corr=-0.025(t≈-0.6) —— 无显著预测力(开盘价已吸收信息,与有效市场一致)。

## 诚实声明
- 样本极短(HIP-3 历史 3-7 个月);t 未经多重检验校正;本研究 1 次试验已登记。
- 永续 mark 价含资金费/溢价;Yahoo 原始价除息日有小误差;未建模任何交易成本。
- Q2 若不显著恰恰符合预期:开盘集合竞价会吸收隔夜公开信息(§3.8)。
