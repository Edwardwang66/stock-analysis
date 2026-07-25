# 因子研究与回测系统 — 功能总览
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

本目录(`backtest/`)是一套**端到端的量化因子研究与回测系统**,覆盖美股与加密,
贯穿"研究 → 因子设计 → 多周期回测 → 严格样本外验证 → 标准因子测试体系 → 拟合"全流程。
**核心原则:全程无未来函数(no look-ahead),诚实报告,不为追求好看数字而过拟合或偷看答案。**

---

## 一、模块地图

| 模块 | 功能 | 配套文档 |
|---|---|---|
| `data.py` | 美股日线下载与缓存(Yahoo,516 只 S&P500∪Nasdaq-100,10 年) | `README.md` |
| `factors.py` / `run.py` | **TQM 时序择时因子**(趋势×质量×动量)+ 多 horizon 正确率回测 | `README.md` |
| `walkforward.py` | **严格样本外**(walk-forward + embargo),修正数据窥探 | `README.md` §3 |
| `barrier.py` | 路径标签(triple-barrier),拆穿"85-90% 正确率"的来源 | `README.md` §4 |
| `factors_xs.py` / `xs_backtest.py` / `xs_portfolio.py` | **美股横截面多因子**:Rank-IC / 分层 / 长短组合 | `README_xs.md` |
| `factor_pipeline.py` | **完整因子测试体系(美股)**:去极值+标准化+行业/市值中性化 → IC/IR → 分层 → 无未来函数 1 月验证 | `README_pipeline.md` |
| `cryptodata.py` / `crypto_factors.py` / `crypto_backtest.py` / `crypto_pnl.py` | **加密多因子(Hyperliquid)**:funding/OI/basis 等独家因子 + 手配权重 vs **Ridge 拟合**(Purged walk-forward) | `README_crypto.md` |
| `crypto_pipeline.py` | **完整因子测试体系(加密)**:中性化(size+BTC-beta)→ IC/IR → 分层 → 无未来函数验证 | `README_crypto_pipeline.md` |
| `binancedata.py` / `binance_pipeline.py` | **8 年长历史**(Binance.vision,2017+)补足样本,真正时间切分样本外(训练 2017-22 / 测试 2023-26) | `README_binance.md` |
| `research/quant-factor-deep-research.md` | **深度研究报告**:顶级量化如何设计因子/预测多周期价格(5 角度、带引用、独立核验) | (在 `../research/`) |

---

## 二、做了哪些"feature"(按交付顺序)

1. **深度研究报告**(`research/quant-factor-deep-research.md`):5 角度并行检索 + 关键结论独立核验,
   覆盖量化因子工作流、多周期信号、加密 Hyperliquid/HIP-3、外部预测、过拟合反证;**数学核验"85-90% 命中率不可能"**。
2. **TQM 时序因子 + 全市场回测**:趋势×质量×动量,多 horizon 正确率。
3. **严格样本外框架**:walk-forward + embargo 隔离带,修正"同段数据既调参又评估"的数据窥探。
4. **路径标签实验**:用 triple-barrier 演示"高胜率"如何来自标签定义而非预测力(负偏巨亏)。
5. **美股横截面多因子**:12-1 动量/短期反转/52 周高点/低波,Rank-IC + 分层 + 长短 Sharpe。
6. **完整因子测试体系(美股)**:去极值 → 标准化 → **行业(GICS)+ 市值中性化** → IC/IR → 5 分层 → 无未来函数的 1 月验证 + 滚动 12 月 OOS。
7. **加密多因子 + 拟合**:Hyperliquid 永续 funding/OI/basis 独家因子;**手配权重 vs Ridge 拟合**(Purged walk-forward),含可交易性诊断。
8. **完整因子测试体系(加密)**:中性化对象换成 size + BTC-beta;**中性化暴露假因子**(低波 alpha 实为市场 beta)。
9. **多数据源接入 + 8 年长历史**:Binance.vision(绕开 451)拉 2017+ 日线与资金费;Bybit 被地理封锁;HIP-3 合成美股永续存在但无长历史。真正时间切分样本外。

---

## 三、一句话诚实结论

跑遍美股(2017-26,514 只)+ 加密(2017-26,54 币,Binance 长历史)、用尽标准方法学
(中性化 / Rank-IC·IR / 分层 / 严格样本外 / 拟合 / Deflated-Sharpe 思想):

> **没有任何因子同时满足 IC>0.05、IR>0.5、多空 Sharpe 为正、分层单调。**
> 真实单因子 IC 仅 0.02–0.13;最强信号(加密低波 vol_30 样本外 IC 0.068)IR 仅 0.31、Sharpe 为负;
> "85-90% 正确率"在数学上要求 IC≈0.9,公开数据不存在,只能来自改标签/数据窥探/生存者偏差。
> **这套系统的价值不是找到圣杯,而是用诚实、可复现、无未来函数的方法,证明圣杯不存在,并把每一分真实但微薄的 alpha 量化清楚。**

---

## 四、复现

```bash
cd backtest && pip install -r requirements.txt
# 美股
python data.py && python run.py && python walkforward.py && python factor_pipeline.py
# 加密(Hyperliquid 近 2 年 + Binance 8 年长历史)
python cryptodata.py && python crypto_pipeline.py
python binancedata.py && python binance_pipeline.py
```

> 数据缓存(`data_cache/`、`crypto_cache/`、`binance_cache/`)不入库,由脚本按需重新下载。

## 五、未完成 / 下一步(需明确工程投入)
- 消除**幸存者偏差**(接入历史时点成分股 / 退市币)。
- **历史 OI 时间序列**落库(WebSocket),做 OI+funding 拥挤反转。
- **CPCV + Deflated Sharpe** 给最终组合做过拟合校验;加入**交易成本/换手**约束。
- 接入**财报 PIT 数据**做 value/quality/PEAD(需授权数据源,避免前视)。
