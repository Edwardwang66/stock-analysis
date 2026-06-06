# `feed/` —— 情报馈送(统一契约,单一真相源)

本目录是「**例行任务 + OpenClaw 投递 → 静态网页/看板消费**」这条闭环的**数据中枢**。
全部是 JSON,GitHub raw / Pages 直接可取,所以静态网页能「不断接受」最新情况而无需后端。

## 结构

```
feed/
├── schema/report.schema.json   # 报告契约(draft-07)。所有写入必须通过它(scripts/validate_feed.py)
├── index.json                  # 清单/看板数据源:新鲜度 + 统计 + 时间线 + 报告列表 + 贡献日志(自动重建)
├── reports/<id>.json           # 每次运行/投递的完整报告(routine / openclaw / manual)
├── signals/latest.json         # 当前做多做空簿(引擎最新持仓)
├── market/state.json           # 最新市场状态快照(regime / 广度 / 拥挤)
├── factory/candidates.json     # LLM 假设工厂候选 + 六门控结果(滚动)
└── inbox/                       # OpenClaw 投递落点 → CI 校验通过后并入 reports/
```

## 谁写、谁读

- **写**:`scripts/run_routine.py`(本仓 routine)、`scripts/validate_feed.py --merge`(并入 OpenClaw 投递)。
- **读**:`frontend/lib/feed.ts` → `/intel` 情报看板;以及任何想消费的下游(raw GitHub 即可)。

## 写入纪律

1. 一律先过 `report.schema.json` 校验;`kind=openclaw` 还须 HMAC 签名(`scripts/feed_lib.sign_report`)。
2. `id` 是幂等键 —— 重复 id 会被 CI 拒绝。
3. 写报告用 `feed_lib.publish_report`,它会自动刷新 `index/signals/market/factory`(勿手改 `index.json`)。

## 新鲜度语义(看板「是否最新」)

`index.json.freshness`:`market_data_asof`(分析所用最新数据日)、`report_age_hours`、`data_age_days`、
`stale`(>36h 无更新)。看板①区直接展示这些。

> ⚠️ 研究/演示用途,非投资建议。引擎在免费数据上净 alpha ≈0/为负(见 `backtest/README_statarb.md`)。
