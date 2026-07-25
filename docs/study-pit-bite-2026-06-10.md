# PIT 过滤咬合量化:516 全名单(2026-06-10)

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

**咬合度:剔除 3604/32832(11.0%) 名·期** —— 这就是「用今天的成分回测过去」在真实研究 universe 上的前视暴露面。

| 面板 | 期数 | 平均横截面 | 过六门候选 | top1 |t| | top1 表达式 |
|---|---|---|---|---|---|
| PIT开(时点成分) | 64 | 455 | 0 | 1.89 | `rank(hi52) - rank(gap_oc)` |
| PIT关(当前成分=有前视) | 64 | 506 | 0 | 2.17 | `rank(hi52) - rank(gap_oc)` |

前视「白送」的过门候选数:+0(关-开)。
## top5 对照(PIT开 → 关)
- `rank(hi52) - rank(gap_oc)` t +1.89 | 无PIT版 t +2.17
- `z(vol21) - z(vz21)` t -1.74 | 无PIT版 t -2.16
- `z(vz21) - z(vol21)` t +1.74 | 无PIT版 t -1.88
- `z(rev1) - rank(gap_oc)` t +1.72 | 无PIT版 t +1.86
- `z(r21) - z(vol63)` t +1.70 | 无PIT版 t -1.86

## 诚实声明
- 仍有幸存者偏差残留:被剔的是「当时不在指数」的票,但「当时在指数后来退市」的票本就缺数据
  (Cycle 9 量化:2021 缺失率 ~10%),PIT 过滤无法找回它们,只能消「未来赢家提早入场」这一半。
- NDX100 成员资格未做 PIT(只有 S&P500 变更史);516 名单中纯 NDX 票不受过滤。
