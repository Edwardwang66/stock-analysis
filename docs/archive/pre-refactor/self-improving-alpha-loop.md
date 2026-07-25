# 自我优化的做多做空情报闭环(Self-Improving Alpha Loop)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use [workflow operations](../../operations/workflows.md) and the [documentation index](../../README.md); historical relative links below are preserved verbatim and may not resolve from this archived location.


> 把设计文档(US Equity Mid-Frequency Hybrid Quant System v1.0)落成一个**持续运转的回路**:
> 做多做空引擎(流 B)+ 例行任务(routine)+ LLM 假设工厂 + OpenClaw 外部 agent + 情报看板。
> 本文是总览与导航;各部件有独立文档。

## 0. 全景

```
                      ┌──────────────── 输入:市场数据(Yahoo 日线 + 行业 ETF + SPY)────────────────┐
                      ▼                                                                              │
   ┌──────────────────────────────┐      ┌──────────────────────────────┐                          │
   │  做多做空引擎(流 B)          │      │  OpenClaw 外部 agent 编队     │                          │
   │  backtest/statarb.py          │      │  (残差/拥挤/事件/因子/红队)   │                          │
   │  残差→OU s-score→aim→熔断→净成本│      │  docs/openclaw-integration.md │                          │
   └───────────────┬──────────────┘      └───────────────┬──────────────┘                          │
                   │ run_routine.py                       │ openclaw_client.py(签名)               │
                   ▼ (每小时/EOD)                          ▼ (github-api / dispatch / PR)            │
   ┌──────────────────────────────────────────────────────────────────────────────┐                │
   │  CI 安全闸门 validate_feed.py(schema ✓ 签名 ✓ 边界 ✓ 幂等 ✓)                  │                │
   └───────────────────────────────────┬──────────────────────────────────────────┘                │
                                        ▼                                                            │
   ┌──────────────────────────── feed/(JSON 单一真相源)──────────────────────────┐                  │
   │  index.json · reports/ · signals/latest · market/state · factory/candidates   │                  │
   └───────────────────────────────────┬──────────────────────────────────────────┘                  │
                  GitHub raw(实时,无需重建 Pages)│  + 捆绑快照 public/feed(兜底)                    │
                                        ▼                                                            │
   ┌──────────────────────────── 静态网页 /intel 情报看板 ─────────────────────────┐                  │
   │  ①新鲜度 ②信息量+时间线 ③市场状态 ④引擎裁决 ⑤做多做空簿 ⑥工厂候选 ⑦贡献日志 ⑧告警 │                  │
   └───────────────────────────────────────────────────────────────────────────────┘                │
                                        └───────────────── 人/红队回看 → 调参/接受/否决 ─────────────┘
```

## 1. 优化后的做多做空逻辑(Part 1)

`backtest/statarb.py` —— 流 B 条件因子统计套利残差均值回归引擎:
**残差(SPY+行业 ETF 回归)→ OU s-score → 滞回开/平 → 协整断裂熔断 → Garleanu-Pedersen aim 组合
→ 分层限额 + 容量地板 → 净·扣成本评估 + Deflated Sharpe**。详见 [`backtest/README_statarb.md`](../backtest/README_statarb.md)。

**诚实结论**:在免费数据(含幸存者偏差的流动大盘)上净 Sharpe 为负 —— 实证了设计文档第 10 章:
真 alpha 在容量受限冷门层,免费数据触及不到。引擎是正确脚手架,转正靠**更冷门 universe + PIT 数据**。

## 2. LLM 每天/每小时优化模型 + 不断 post 报告(Part 2/3)

- **Routine**:[`routines/daily-alpha-routine.md`](../routines/daily-alpha-routine.md) 是 Claude 可执行的 playbook;
  `scripts/run_routine.py` 是自动实现;`.github/workflows/alpha-routine.yml` 定时(盘中每小时 + EOD)跑并 commit `feed/`。
- **LLM 角色**:只在第 4 步生成**可审计公式因子**(Alpha101 风格)+ 过**六门控**,**不决策**(R6);
  默认关闭,接入指引见 routine 文档。Claude Code 里可用 `/loop 60m python scripts/run_routine.py` 定时。

## 3. 静态网页不断接受的模式(Part 4)

`frontend/lib/feed.ts`:**双源取数** —— 先 GitHub raw `feed/`(新 commit 即时可见,**无需重建 Pages**),
失败回退到部署时捆绑的 `public/feed/` 快照。看板每 5 分钟自动刷新。这就是「静态页不断接受」的机制:
数据更新(便宜、raw)与页面部署(重、Pages)**解耦**。

## 4. OpenClaw 完整方案(Part 5)

[`docs/openclaw-integration.md`](openclaw-integration.md):agent 名册、调度、六门控、三种投递通道
(github-api / repository_dispatch / PR)、HMAC 签名、最小权限、CI 安全闸门、提示词注入防御。
参考客户端 `scripts/openclaw_client.py`,投递契约 = `feed/schema/report.schema.json`。

## 5. 情报看板(Part 6)

`/intel`(`frontend/app/intel/page.tsx`)直接回答用户三问:
- **什么时候获得了多少信息** → ②区统计卡 + 每日时间线 + by_producer 来源分布。
- **怎么帮助到你了** → ⑦贡献日志(每条投递的 type/summary/净 Sharpe 变化)+ ⑥工厂候选门控结果。
- **repo 是否最新** → ①新鲜度横幅(`market_data_asof` / 滞后天数 / 上次报告 / stale)。
另含 ③市场状态、④引擎净·扣成本裁决、⑤当前做多做空簿、⑧风险告警。

## 6. 红线贯穿(设计文档 §9)

R4 净成本唯一货币 · R5 真 holdout + 预注册 · R6 LLM 截止后验证否则删 · R7 拥挤先于人群减杠杆 ·
R9 容量以扣冲击定义。看板与引擎处处以「净·扣成本」与「可审计、可删除」为准绳。

## 7. 一次跑通(本地)

```bash
pip install -r scripts/requirements.txt
cd backtest && python -c "import data,statarb as sa; data.fetch_universe(sa.DEMO_UNIVERSE+sa.SECTOR_ETFS+['SPY'])" && cd ..
python scripts/run_routine.py --demo-candidate          # 引擎 + 报告 → feed/
FEED_HMAC_SECRET=demo python scripts/openclaw_client.py --mode local   # 模拟 OpenClaw 投递
FEED_HMAC_SECRET=demo python scripts/validate_feed.py --merge feed/inbox/*.json   # 校验并入
cd frontend && npm i && NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run build       # 看板静态导出
```
