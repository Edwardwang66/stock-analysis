# Routine:每日/每小时做多做空模型优化与情报投递

> 这是一份**可执行的 routine 说明**:既可由 GitHub Actions 自动跑(`.github/workflows/alpha-routine.yml`),
> 也可由 **Claude Code** 当作 playbook 手动/定时执行(`/loop` 技能可定时重复)。
> 目标:周期性地刷新做多做空模型、产出一份情报报告写入 `feed/`,让 `/intel` 看板与下游不断接受最新情况。

对齐设计文档红线:**净·扣成本是唯一货币(R4)**;**LLM 只生成假设、不决策(R6)**;
**结论须经真 holdout 终检(R5)**;**先证明基础能赚钱再加复杂度(R10)**。

---

## 触发节奏

| 频率 | 跑什么 | 为何 |
|---|---|---|
| 盘中每小时 | 引擎刷新 + 市场快照(`run_routine.py`) | 拥挤/regime/协整断裂是时变的(§7.2/§7.3) |
| 收盘后(EOD) | 引擎终版 + (可选)LLM 因子工厂 | 重活放盘后;factor-factory 须截止后验证(R6) |
| 周末 | 不跑 | 无新行情 |

---

## 每次运行的步骤(Claude 执行版)

> 自动版把以下步骤封装在 `scripts/run_routine.py` 里;Claude 手动执行时按此清单走,
> 并在最后用 `feed_lib.publish_report` 落盘(或直接调用脚本)。

1. **拉取数据**(无未来函数):下载/复用 `DEMO_UNIVERSE + 行业 ETF + SPY` 的日线缓存。
   ```bash
   cd backtest && python -c "import data,statarb as sa; data.fetch_universe(sa.DEMO_UNIVERSE+sa.SECTOR_ETFS+['SPY'])"
   ```
2. **运行做多做空引擎**(流 B 残差统计套利,`backtest/statarb.py`):
   - 条件因子残差 → OU s-score → 滞回开/平 → 协整断裂熔断 → aim 组合(控换手)→ 限额 → 容量地板。
   - 输出:**净·扣成本** Sharpe / 回撤 / 换手 / Deflated Sharpe / 当前持仓簿 + L6 裁决。
3. **市场状态快照**:regime(SPY 200dma + 20d 波动)、广度(50dma 上占比)、**拥挤代理**(平均两两相关)。
4. **(可选)LLM 假设工厂** —— 默认关闭。开启时:
   - 让 Claude 生成 N 条 **WorldQuant Alpha101 风格的可读公式因子**(非黑箱),每条附**事前经济假设**。
   - 对每条跑**六门控**(PBO<0.1 / 增量正交 IC / 相依 FDR t≳3 / 特征值广度 / 事前机制 / 扣成本 IR);
     **只在模型训练截止日之后的数据上评分(R6,防 Profit Mirage)**;锁定 `producer.model` 版本。
   - 未过门控 → `decision=reject`;过 → `shadow`(进 60 日影子,R3),**绝不直接 accept 上线**。
5. **风险告警**:拥挤告警(R7 先于人群减杠杆)、协整断裂数、回撤治理阈值(§7.4)。
6. **组装 + 发布**:按 `feed/schema/report.schema.json` 组装报告,`publish_report` 写入 `feed/`
   (刷新 `index/signals/market/factory`),`git commit` 回仓。看板与 OpenClaw 即可消费。

---

## 命令速查

```bash
# 全量(代表性,2021–今)
python scripts/run_routine.py
# fast(缩短区间,几秒,CI/调试)
python scripts/run_routine.py --fast
# 注入 1 条契约示例因子候选(演示看板⑥;明确标注未过门控)
python scripts/run_routine.py --demo-candidate
```

在 Claude Code 里定时重复:`/loop 60m python scripts/run_routine.py`(盘中每小时)。

---

## 如何接入真实 LLM 因子工厂(把第 4 步做实)

1. 在 `scripts/run_routine.py` 的 `propose_factory_candidates`(当前为占位)里调用 Claude:
   - 输入:近端因子/收益面板的**统计摘要**(不喂原始未来数据)、现有组合暴露、被拒候选历史。
   - 让 Claude 产出公式 + 假设;**用本仓 `backtest/validation.py` 跑 DSR/PBO,用真 holdout 评分**。
2. 设环境变量(模型版本锁定):`LLM_MODEL=claude-opus-4-8`,写进 `producer.model`。
3. 时序防火墙:RAG/检索文档打 PIT 时间戳;回测起点必须晚于模型训练截止日并留缓冲。
4. kill-switch:整层可删 —— 若连续若干周期无候选过门控,自动停用工厂(R6:证不出增量 IC 就删)。

> 诚实提醒:在当前免费数据(含幸存者偏差的流动大盘)上,引擎净 alpha ≈0/为负。
> routine 的价值不是制造圣杯,而是把「净·扣成本的真实增量」量化清楚,并把每次发现可审计地记录到看板。
