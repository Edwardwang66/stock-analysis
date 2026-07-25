# 平台统一方法论(前端实装 与 OpenClaw 调研 共用同一口径)
> **Status:** Current
> **Scope:** Active analytical-method playbook; it does not prove cross-language implementation parity.
> **Last verified commit:** `a8d3d4c1a0ae707fca6c500f4de61a4bad0a8726`

Implementation boundaries and known drift are documented in [Current Architecture](../docs/current-architecture.md). Use [Compliance](../docs/compliance.md) for estimation and non-investment-advice boundaries.

> 2026-06-09 由方法论调研产出(原始报告含 13 种方法评分;此处为采纳的实施口径)。
> 所有方法只依赖 OHLCV。改口径必须同时改这里和实现,否则前端展示与 AI note 会打架。

## 1. TD9 神奇九转(只做 Setup 段,东方财富口径)
- 买入计数:连续 `close[i] < close[i-4]`;卖出计数:连续 `close[i] > close[i-4]`;断则清零,数满 9 重新数。
- 仅当连续段 ≥6 时显示数字(6 起显示,7/8/9 高亮);相等不计数(口径注明)。
- 完美 9(更强):买 9 的第 8 或 9 根 low ≤ min(第6,7根 low);卖侧镜像比较 high。
- 解读:涨数到 9 = 衰竭预警(卖参考);跌数到 9 = 超卖反弹预警。不做 Countdown 13。

## 2. 52 周位置(George-Hwang 2004)
- `nearness = close / 52周最高(252根滚动,盘中 high 口径,前复权)`;距高点回撤 = nearness − 1。
- 不足 252 根标「上市未满一年」。新高/新低判定用盘中 high/low。
- 解读:接近新高(nearness ≥ 0.95)动量学术上偏强;同时输出区间位置 (c−lo)/(hi−lo)。

## 3. SuperTrend(10, 3)
- ATR 用 Wilder RMA;basic 上/下轨 = (H+L)/2 ± 3×ATR10;final 轨带棘轮
  (下行中上轨只降不升,上行中下轨只升不降);方向翻转判定用 close 穿 final 轨。
- 解读:绿(上行)持有、翻红离场;震荡市会打脸,标注「趋势市指标」。

## 4. 缠论背驰度(原文第 24 课口径)
- 同级别比较(笔对笔):A、C 同向两段,B 中枢期间 |DIF| 须回拉(min|DIF| < 0.25×近期峰值)。
- `背驰度 = 1 − MACD柱面积(C) / MACD柱面积(A)`(上涨段只累计红柱、下跌段绿柱,按笔端点截取);
- 确认条件:C 创新高/新低 且 面积缩 且 |DIF| 峰值缩;度 ≥0.3 为显著。
- 文案:「进入背驰段,关注其后次级别回试」,不说"必反转"。

## 5. 周/月 Pivot Points(经典 + 斐波)
- 用上一完整周/月的 H/L/C:P=(H+L+C)/3;经典 R1=2P−L,S1=2P−H,R2=P+(H−L),S2=P−(H−L);
  斐波 R1/S1=P±0.382(H−L),R2/S2=P±0.618(H−L),R3/S3=P±(H−L)。

## 6. RS 相对强度
- RS 线 = 100 × (close/bench) 归一(起点 100);基准:美股 ^GSPC、A股 000300/000001.SS、港股 ^HSI。
- RS 评分(IBD 风格):raw = 0.4×63日收益 + 0.2×126日 + 0.2×189日 + 0.2×252日,全池百分位 → 1~99。

## 实施状态
- [x] 方法论调研(13 方法,含 Ichimoku(✅ 图上「一目」开关:转换/基准/云AB 简版)/VSA(✅ 图上 VSA 开关:高量滞涨/无供应/承接/放量突破)/RRG/波动率锥 等二期项)
- [x] TD9 前端叠加层(默认开,6起显示,完美9✓)
- [x] 52周距高点徽章 + 全市场榜(✅ rs-ranks 带 w52dd/w52pos,/screener 52周新高接近榜)
- [x] SuperTrend 叠加(开关,绿/红双线)
- [x] 背驰度徽章 + 买卖点历史表(个股页 ☯ 缠论结构面板:背驰度+确认三件套+历史表带事后表现)
- [x] 周 Pivot 水平线组(图上「支撑压力」开关;月线版 ✅ 月R1/月P/月S1 已并入支撑压力开关)
- [x] RS 榜(daily_screener 全宇宙百分位 → feed/signals/rs-ranks.json;desk RS 列+排序)

## 7. 综合评分 v2(2026-06-09 重构,前后端同口径)
> v1 缺陷:正分只有 趋势20+排列15+MACD15=50,RSI/布林加分与上升趋势互斥 → 看多股全部卡在 50。

十因子(求和后 clamp ±100):
1. price>MA50 ±20;2. MA50>MA200 ±15;3. MA20>MA50 ±10;
4. RSI14:≥80→-15 / 70-80→-5 / 55-70→+10 / 45-55→0 / 30-45→-5 / ≤30→+10;
5. MACD>信号线 ±10;6. DIF>0 零轴 ±5;7. 布林触上轨-5/下轨+5;
8. 52周接近度(≥200根):≥0.95→+10 / ≥0.80→+5 / ≤0.60→-5;
9. 近21日动量:≥+8%→+5 / ≤-8%→-5;10. 量比≥1.5:放量涨+5 / 放量跌-5。
典型强趋势股 70-90 分,弱多 30-45 分;≥50 门槛从"凑齐三件套"变为"多因子共振"。
verdict 档位不变(≥50 强烈看多 / ≥20 看多 / >-20 中性 / >-50 看空 / 其余强烈看空)。
