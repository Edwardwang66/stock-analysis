# Routine:长期投资腿(LIS)月度刷新

> 可执行 playbook:既可由 GitHub Actions 跑(`.github/workflows/longterm-screen.yml`,每月 2 日),
> 也可由 Claude Code 当 playbook 手动/定时执行(`/loop` 技能)。
> 目标:月度刷新长期腿的数据底座 + 质量/价值筛选 + 宏观拨盘,写入 `feed/`,让 `/longterm` 看板接受最新候选。
> 设计文档:[`docs/long-term-investment-system.md`](../docs/long-term-investment-system.md)。

对齐红线:**净·扣成本是唯一货币(R4)**;**LLM 只生成假设、不决策(R6)**;**结论须过真 holdout(R5)**;
**先证明能赚钱再加复杂度(R10)**。长期腿持有期数月-数年 → 月度刷新足矣,不追逐日内噪声。

---

## 触发节奏

| 频率 | 跑什么 | 为何 |
|---|---|---|
| 每月 2 日收盘后 | 宏观拨盘 + 质量/价值筛选 → `feed/longterm` `feed/macro` | 基本面季度更新 + 持有期长,月度够 |
| 每季度 | (可选)`study_longscore.py` 重跑验证 | 防参数漂移成新过拟合;新季度数据进 holdout |
| 盘中/每日 | **不跑** | 长期腿无日内动作;避免换手与噪声 |

---

## 每次运行的步骤(Claude 执行版)

> 自动版见 `longterm-screen.yml`。手动执行按此清单走。

1. **单测自检**(触网前先红灯):
   ```bash
   for t in edgar_fundamentals factors_fundamental factors_value longterm_screen macro_fred; do
     python scripts/tests/test_$t.py || exit 1
   done
   ```
2. **宏观风险拨盘**(FRED keyless):
   ```bash
   python scripts/macro_fred.py            # → feed/macro/latest.json(risk_dial∈[0,1])
   ```
3. **质量+价值筛选**(EDGAR PIT + 行情 join):
   ```bash
   python scripts/longterm_screen.py --universe scripts/ndx100.json --as-of "$(date -u +%F)" --with-value
   # → feed/longterm/longscore.json(LongScore 排行 + 剔除闸 + 估值)
   ```
4. **提交**:`git add feed/longterm feed/macro && git commit && git push`(看板走 raw,无需重建 Pages)。

---

## 诚实纪律(必读,勿跳过)

- **这是候选清单,不是下单信号**。`/longterm` 看板顶部的「验证裁决卡」就是提醒:截至最近一次
  `study_longscore.py`,LongScore 在 NDX100 上 **IC 不显著**、**价值腿在成长 universe 里 IC 为负**、
  对动量/规模正交化后增量 ≈ 0。**不得据此宣称 alpha**。
- **不要为了让 IC 转正而在样本内调 bucket 权重**——那正是系统反对的过拟合。要改权重必须:
  预注册 → 真 holdout(2022 入) → Deflated Sharpe/CSCV-PBO → 净·扣成本 → 对现有因子正交增量。全过才接受。
- **universe 选择会主导结论**:NDX100 是成长/科技重,价值天然吃亏。价值腿的公平检验需更广/更均衡的
  universe(如 S&P500 PIT 成分,见 `backtest/pit_membership.py`)。换 universe 前不要下"价值无效"的普遍结论。
- **幸存者偏差**:当前用固定 ticker 列表(当前成分)→ IC 偏高。消偏差路径 = PIT 成分史 + 含退市票。

---

## 验证(季度,或改动因子/权重时必跑)

```bash
python backtest/study_longscore.py --universe scripts/ndx100.json --start 2016 --end 2024 \
       --md docs/study-longscore-$(date -u +%F).md --force-prices    # 首跑或浅缓存时加 --force-prices
```
产出聚合 Rank-IC / ICIR / t / Q5-Q1 / 对动量·规模正交增量 + 自动诚实裁决。
**裁决不显著 → 看板保持「仅候选展示」,不进任何下单/组合层。**

> ⚠️ 研究/演示用途,非投资建议。所有数据为免费源(EDGAR/Yahoo/FRED)。
