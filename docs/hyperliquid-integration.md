# Hyperliquid 接口全图 → 信息缺口填补方案(2026-06-10 实测)

> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.

> 全部免 key,`POST https://api.hyperliquid.xyz/info`(WebSocket: `wss://api.hyperliquid.xyz/ws`)。
> 本文档:① API 面板实测结果;② 每个接口填我们哪个缺口;③ 已落地与路线图。

## 1. API 面板(2026-06-10 实测可用)

| 请求 type | 返回 | 实测规模 |
|---|---|---|
| `metaAndAssetCtxs` | 主 DEX 全永续:**funding/OI/premium/markPx/oraclePx/24h量/impactPxs** | 230 永续 |
| `metaAndAssetCtxs` + `dex` | **HIP-3 builder DEX 同字段** | 9 个 DEX,~99 个有量资产 |
| `perpDexs` | builder DEX 名册 | xyz/flx/vntl/hyna/km/abcd/cash/para |
| `predictedFundings` | 同资产 **Binance/HL/Bybit 预测资金费并排** | 230 资产 |
| `l2Book` | 真实订单簿(20 档/边,含笔数) | 已验证 BTC |
| `candleSnapshot` | OHLCV(任意周期,~5000 根上限) | 回测已用 |
| `fundingHistory` | 历史资金费(1h 粒度,分页) | 回测已用 |
| `spotMetaAndAssetCtxs` | 现货元数据+上下文 | 465 token/303 对 |

### HIP-3 关键发现(填最大缺口:美股 24/7 价格发现)

| DEX | 资产 | 流动性(24h) |
|---|---|---|
| **xyz** | 88 个:XYZ100(纳指代理)、SP500、个股(MU/SNDK/MRVL…)、大宗(CL/SILVER/BRENTOIL) | **XYZ100 $10亿、SP500 $7亿、MU $4亿** |
| **cash** | INTC/NVDA/GOOGL/EWY/SILVER/WTI | $8-17M/资产 |
| **vntl** | **私有公司永续:SPACEX/OPENAI/ANTHROPIC** + MAG7/INFOTECH | $0.1-0.8M(薄) |
| km | US500/USTECH/USOIL/EUR/BABA/TENCENT | $0.5-15M |
| flx | USA500/USA100/NVDA/GOLD/OIL/GAS | <$1M(薄) |

## 2. 缺口 → 接口映射(本仓视角)

| 系统缺口 | 用什么补 | 状态 |
|---|---|---|
| 美股收盘后/周末无价格(Yahoo 日线滞后) | HIP-3 股票/指数永续 markPx+prevDayPx(24/7) | ✅ 已落地(monitor) |
| 拥挤监控(§7.2)只有股票相关性代理 | 230 永续 funding 方向占比 + OI 膨胀率 | ✅ 已落地 |
| 跨所资金错位(压力/套利信号) | predictedFundings(HL vs Binance,年化对齐) | ✅ 已落地 |
| 私有公司估值脉搏(SpaceX/OpenAI/Anthropic) | vntl 永续 | ✅ 已落地(展示) |
| 微观结构/执行(§6.5 OFI) | l2Book 20档 + WebSocket trades | 🔜 路线图 |
| 隔夜跳空因子研究(gap_oc 是工厂最佳候选!) | HIP-3 candleSnapshot 历史 → 盘后永续走势 vs 次日开盘 | 🔜 路线图 |
| 加密回测(已有) | candleSnapshot/fundingHistory | ✅ 既有(backtest/cryptodata.py) |

## 3. 已落地(Cycle 7)

- `scripts/hyperliquid_monitor.py`:三路并采(主DEX持仓面 / 跨所错位 / HIP-3 资产),
  写 `feed/crypto/state.json`,发布 feed 报告(拥挤 warning / 资金费极端 / SP500 盘后代理 info)。
  子项失败自动回退上次快照(builder DEX 随时可能下线)。
- `.github/workflows/hyperliquid-monitor.yml`:**每 2h**(加密 24/7,周末照跑)。
- 看板 `/intel` 新增「🧲 衍生品情报」卡片;审计 SLA:crypto_state 0.5d warn / 2d critical。

## 4. 路线图(按信息增量排序)

1. **隔夜缺口研究**(高价值):用 xyz:SP500/个股永续的盘后走势预测次日开盘缺口——
   我们工厂的最佳落选因子就是 gap_oc(t=1.7);HIP-3 给了它一个**实时领先版本**。
   做法:candleSnapshot(dex=xyz)拉小时线,对齐次日 NYSE 开盘,测 IC(全程无未来函数)。
2. **l2Book 深度不平衡**:bid/ask 名义量差 → 短期方向微观信号(执行择时,非中频 alpha,D4 纪律)。
3. **资金费 carry 监控**:跨所错位持续>阈值 → carry 提示(注意:回测已证 fund_carry 单因子长样本无效,
   只作监控不作信号)。
4. **WebSocket 常驻**(若有常驻进程):trades/l2 实时流;当前 2h 轮询已够看板用。

## 5. 风险与诚实声明

- HIP-3 永续价 = **mark 价**(含资金费/溢价机制),不是证券交易所成交价;仅作盘后参考,不可当报价用。
- builder DEX 历史短、可下线、流动性参差(vntl/flx 很薄);monitor 对每个 dex 独立容错。
- 私有公司永续价格是**投机市场对估值的押注**,与一级市场实际估值可能差异巨大。
- 免费接口无 SLA;workflow 失败不重试超过 cron 周期,审计层兜底(crypto_state 超龄告警)。
