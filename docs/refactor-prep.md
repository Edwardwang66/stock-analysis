# 框架梳理与重构准备 — Framework Refactor Prep

> 目的:在动手重构**之前**,把当前系统的**真实结构(as-is)**完整摊开,作为重构规划的统一底图。
> 本文不是设计愿景(那是 [`architecture.md`](architecture.md)),而是「代码现在到底长什么样、各块怎么连、债在哪、动哪里安全」。
> 生成日期:2026-06-29。覆盖:backend / frontend / backtest / scripts+feed 自动化 / 横切关注点。

---

## 0. 一句话现状

这是一个**以静态前端 + JSON feed 为中心的多市场行情·情报看板**,而**不是** `architecture.md` 描述的那套
「FastAPI 网关 + PostgreSQL/TimescaleDB + Redis + Celery + AI 编排」服务化平台。

```
┌─ 真实运行形态(as-is) ─────────────────────────────────────────────┐
│                                                                     │
│  ① 静态前端 (Next.js export → GitHub Pages)                         │
│       浏览器直连公开 API(Yahoo/Binance/…) + 读 feed/ JSON           │
│                                                                     │
│  ② feed/ = 唯一真相源(全 JSON,git 仓库即数据库)                    │
│       ▲ 写:GitHub Actions 定时脚本 / Winter 本地 loop / OpenClaw    │
│       ▼ 读:前端 + /intel 看板 + 任意下游(GitHub raw)               │
│                                                                     │
│  ③ FastAPI 后端(可选、旁路,Render 部署)                           │
│       行情代理 + 非 LLM 分析;前端有 HAS_BACKEND 开关,默认走浏览器  │
│                                                                     │
│  ④ backtest/ 研究代码(本地/CI 跑,产出喂回 feed/signals、factory)   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> **重构第一性事实**:`architecture.md` 是**目标蓝图**,当前代码**没有** PostgreSQL(winter_pg 例外、可选)、
> **没有** Redis、**没有** Celery、**没有** AI Agent 编排。重构要么把现实往蓝图收敛,要么把蓝图改成承认现实。
> 这个落差本身是重构的头号议题,先决策方向,再动代码。

---

## 1. 子系统地图

### 1.1 后端 `backend/` — FastAPI 行情·分析代理(可选旁路)

- **入口** `app/main.py`(FastAPI v0.2.0 + Uvicorn),路由前缀 `/api/v1`:
  `health` · `cache` · `search` · `quotes`(批量) · `ohlcv` · `analysis`(规则评分) ·
  `moneyflow` · `chips` · `chan`。CORS 全开(仅 GET)、GZip、生命周期内共享 httpx.AsyncClient + 6h 清理 janitor。
- **数据源适配器** `app/providers/`:`base.py`(DataProvider Protocol + `Unsupported`)、
  `router.py`(按市场的降级链 + 3 连败 120s 熔断 + 批量报价)、`yahoo`/`binance`/`okx`/`tencent`/`stooq`。
  链路硬编码在 `router.py` 的 `CHAINS` dict(US: Yahoo→Tencent→Stooq;CRYPTO: Binance→OKX;…)。
- **分析引擎** `app/analysis/`:`indicators`(纯 Python 指标,无 pandas)、`signals`(v2 十因子评分 -100..100)、
  `chan`(合并 K→分型→笔→中枢→买卖点 + MACD 背驰)、`chips`(筹码成本分布)、`moneyflow`(分钟 K 估算资金流,非 LV2)。
- **存储/缓存** `cache.py`(SQLite + 内存兜底,stale-while-revalidate)、`barstore.py`(K 线增量 UPSERT,
  时间归一化防跨源重复)、`store.py`(数据访问层:会话感知 TTL + 单飞 + 批量)。
- **部署**:`Dockerfile`(python:3.11-slim)、`Procfile`、`runtime.txt`;依赖仅 `fastapi/uvicorn/httpx` 三件。
- **测试**:`tests/test_backend.py`(17 断言,离线:缓存/熔断/增量/单飞/批量)+ `test_api.py`(13 断言,HTTP 层)。
  **后端是全仓测试最好的部分。**

### 1.2 前端 `frontend/` — Next.js 静态看板(主交付物)

- **页面** `app/`:`page`(多市场首页)、`symbol`(个股,10 种叠加 + 信号雷达)、`screener`(选股榜)、
  `desk`(工作台)、`tracker`(选股回测)、`intel`(情报看板)、`reports`、`portfolio`、`alerts`、`sources`、`help`。
  另有 `app/api/{ohlcv,quote}`(Edge 代理,Vercel 部署时用;静态导出时不可用)。
- **数据/逻辑层** `lib/`(~3100 行):
  - *取数*:`datasource`(三层缓存:内存 30s + localStorage 10min + API)、`feed`(GitHub raw + 捆绑快照兜底)、
    `multiprice`(跨所聚合,demo)、`livePrice`(Binance WS)、`nightquotes`(Hyperliquid 夜盘代理层)。
  - *分析*:`analysis` / `chan` / `chips` / `indicators` / `moneyflow` / `sentiment`。
  - *领域*:`markets` `marketstatus` `sectors` `names`(中英双语)`search` `watchlist` `portfolio`
    `alerts` `forex` `fundamentals` `news` `crypto` `sources` `timefmt`。
- **组件** `components/`(17 个,~1550 行):`Chart`(lightweight-charts + 8 叠加)、`QuoteCard`、`Heatmap`、
  `MoneyFlow`、`Chips`、`ChanPanel`、`AINote`、`SignalRadar`、`RrgChart`、`SearchBox` 等。
- **构建/部署**:`next.config.mjs` 双目标(Vercel 全功能 / GitHub Pages 静态 `output: export`);
  依赖极简(next 14 + react 18 + lightweight-charts,无 UI 框架、无状态库、无取数库)。
- **状态**:watchlist / alerts / portfolio 全部 localStorage(单用户、隐私优先、不跨设备同步)。
- **测试**:**0**。所有纯逻辑库(chan/indicators/search/feed)无任何单测。

### 1.3 回测 `backtest/` — 量化研究代码(本地/CI 跑)

- **核心框架**:`engine`(前向收益 + 命中率)、`data`(Yahoo 日线 + CSV 缓存)、`costs`(半价差 + 平方根冲击 + ADV 地板)、
  `factors`(TQM 时序因子)、`barrier`(三重障碍)、`validation`(Deflated Sharpe / Hurst / 回撤 / OU)。
- **股票统计套利(Flow B 生产引擎)**:`statarb`(575 行:残差→OU s-score→滞回→协整熔断→Garleanu-Pedersen aim→
  分层限额→净扣成本 + DSR)、`factor_pipeline`、`factor_factory`(可审计公式因子搜索 + 六闸门)、
  `factors_xs`、`xs_backtest`、`xs_portfolio`、`walkforward`、`pit_membership`(S&P500 时点成分重建)。
- **加密管线**:`crypto_*`(Hyperliquid ~2y)、`binance_*`(Binance ~8.8y 长历史)。
- **研究脚本**:`study_pbo` `study_downshift` `study_overnight_gap` `study_pit_bite` `experiment_regime`。
- **配置 JSON**:`universe`(515 名单)、`sector_map`、`pit_sp500`、`*_universe`。
- **接线**:`scripts/run_routine.py` 导入 `backtest/{data,statarb}` → 日跑 → 写 `feed/signals` `feed/market` `feed/factory`;
  `monthly-studies.yml` 跑 `study_*` → 写 `docs/study-*.md`。
- **测试**:核心工具(engine/costs/validation/PBO)**无单测**。

### 1.4 自动化 `scripts/` + `feed/` + `.github/workflows/` — 数据管线(系统心脏)

- **17 个工作流**(13 定时 + Pages 部署 + 投递校验 + 测试 + dependabot 自动合并)。代表:
  `daily-screener`(22:30 选股)、`alpha-routine`(整点 + EOD 跑 statarb)、`intraday-report`(*/15 盘中)、
  `openclaw-notes`(01:00 确定性方法 6 法)、`hyperliquid-monitor`(2h 衍生品)、`feed-watchdog`(SLA 看门狗,
  live 超 30min 陈旧 → 拉起 intraday)、`feed-validate`(HMAC + schema 闸门)、`chan-stats`(周报)。
- **脚本**:`feed_lib.py`(7 个脚本共享:IO/schema/HMAC/publish_report 自动重建 index)、
  `daily_screener` `run_routine` `intraday_report` `premarket_pack` `market_snapshot` `funds_13f`
  `hyperliquid_monitor` `chan_engine` `openclaw_daily` `validate_feed` `audit_feed`。
- **`winter_pg/`**:OpenClaw 本地 Postgres 仓(可选、非公开):`schema.sql` + `ingest`/`winrate`/`event_heat`。
  **没有任何工作流自动调用它**,Postgres 缺席则 `winrate.json`/`event-heat.json` 不产出。
- **`feed/` 结构**:`index`(自动重建)、`health`、`watchlist`、`reports/`(routine/openclaw/manual)、
  `inbox/`(OpenClaw 暂存)、`schema/report.schema.json`(draft-07 契约)、`screener/` `stock-notes/`
  `signals/` `market/` `factory/` `funds/` `crypto/` `intraday/`。
- **分支策略**:`main` 存长期结构化状态;`live` **只**放 `feed/intraday/latest.json`(5min 心跳 78 提交/天,
  防污染 main)。
- **三股并发写入流**:① GitHub Actions(main,确定性,rebase 重试)② Winter 本地 loop(live,5min 低延迟)
  ③ OpenClaw 外部 agent(inbox → 校验 → reports)。三者互为降级兜底。

---

## 2. 横切关注点(跨子系统的债,重构主战场)

### 2.1 分析逻辑「双实现」漂移(最高优先级)
同一套口径在 **Python(backend + scripts)** 和 **TypeScript(frontend)** 各写一遍:

| 口径 | 后端/脚本 | 前端 | 风险 |
|------|-----------|------|------|
| 指标 | `backend/app/analysis/indicators.py` | `frontend/lib/indicators.ts` | 数值精度漂移 |
| 信号评分 v2 | `signals.py` + `scripts/daily_screener.py` | `lib/analysis.ts` | 评分标尺跨端不一致 |
| 缠论 | `chan.py` + `scripts/chan_engine.py` | `lib/chan.ts` | **已实证漂移**:3B/3S 修复只改了 Python 侧(见 need-to-fix #8) |
| 筹码 | `chips.py` | `lib/chips.ts` | 估算口径分叉 |
| 资金流 | `moneyflow.py` | `lib/moneyflow.ts` | 分档阈值分叉 |

- `routines/methodology.md` 是名义上的「统一口径规范」,但**没有自动化测试**保证三处实现真的一致。
- **重构方向候选**:① 抽一份 golden K 线 JSON 做跨实现一致性测试(最小改动、立刻止血);
  ② 长期把分析核算下沉到单一实现(如后端为权威 + 前端只渲染,或共享 WASM/同构 TS)。

### 2.2 取数/报价层碎片化
前端报价语义散在 5 个模块:`datasource`(三层缓存)、`multiprice`(跨所,基本未用)、`livePrice`(WS)、
`nightquotes`(夜盘 3min TTL)、`portfolio`(自带 FX)。**无统一报价总线**,实时语义不一致。
后端侧缓存又散在 `cache.py` / `barstore.py` / `store.py` 三处,stale-while-revalidate 逻辑重复三遍。

### 2.3 测试覆盖严重不均
- ✅ 后端:`test_backend.py` + `test_api.py`,覆盖好。
- ❌ 前端:**0** 单测(纯逻辑库可测却没测)。
- ❌ 回测:核心工具(engine/costs/validation/PBO/Hurst)无单测。
- ❌ 跨实现一致性:无(2.1 的根因)。

### 2.4 feed 契约与时效性
- `feed/schema/report.schema.json` 是 reports 的契约,但 `intraday/` `crypto/` `overnight` **无 schema**。
- 部分 feed(`watchlist`/`stock-notes/index`/`factory/candidates`)缺显式 `generated_at`,时效只能靠 git 提交时间推断。
- reports 无 `version` 字段,schema 变更对旧订阅者是**静默不兼容**。
- `intraday_report.py` 事件类型用英文(`move`/`new_high`),`winter_pg/schema.sql` 中英混用,join 口径含糊。

### 2.5 调度脆弱性
- 多个 cron 撞点(22:30 screener + 22:30 alpha EOD + 22:45 snapshot)靠 rebase 重试,非原子。
- `live` 分支「单写者」假设靠 ~290s 新鲜度检查,非强互斥;Winter 静默卡死时 Actions 可能写陈旧数据。
- GitHub 高频 cron 不可靠,盘中流靠 `feed-watchdog` 看门狗拉起(已是当前缓解方案)。

### 2.6 重复的研究层样板
回测里 Winsorize/Standardize/Neutralize、面板加载、IC/ICIR 计算在 `factor_pipeline` / `crypto_pipeline` /
`binance_pipeline` / `xs_backtest` 各写一遍;成本模型也不统一(`costs.py` 未被 `xs_portfolio` 使用)。

---

## 3. 重构候选清单(按 收益/风险/独立性 排序)

> 原则:先做**高收益、低风险、可独立验证**的「止血」与「立桩」,再碰跨子系统的大改。

| # | 重构项 | 类型 | 收益 | 风险 | 前置依赖 |
|---|--------|------|------|------|----------|
| R1 | **跨实现一致性测试**:golden K 线 JSON,Python vs TS 同口径断言 | 立桩 | 高(锁死 2.1 漂移) | 低 | 无 |
| R2 | **前端引入 vitest**,先覆盖 chan/indicators/search/feed | 立桩 | 高 | 低 | 无 |
| R3 | **chan.ts 同步修复 3B/3S**(need-to-fix #8),并入 R1 测试 | 止血 | 中 | 低 | R1 |
| R4 | **feed 契约补全**:intraday/crypto schema + 统一 `generated_at`/`version` | 立桩 | 中 | 低 | 无 |
| R5 | **空结果保护**推广到 screener/premarket(复用 chan_engine 模式,need-to-fix #10) | 止血 | 中 | 低 | 无 |
| R6 | **统一报价层**:前端 5 模块收敛为单一 quote 总线 | 结构 | 高 | 中 | R2 |
| R7 | **后端缓存层收敛**:cache/barstore/store 的 SWR 抽成统一策略 | 结构 | 中 | 中 | 后端测试已有 |
| R8 | **回测研究层去重**:抽 preprocessing/panel/IC 共享工具 + 统一成本模型 | 结构 | 中 | 中 | 回测补单测 |
| R9 | **分析核算单一化**:决定权威实现(后端 or 同构),消除双实现 | 架构 | 高 | 高 | R1/R6 |
| R10 | **架构文档对齐现实**:`architecture.md` 标注「目标 vs 现状」,或决策收敛方向 | 决策 | 高 | 低 | 无(但需用户拍板) |

---

## 4. 重构红线(不可破坏的不变量)

动代码时,以下契约**不能默默改坏**,否则线上看板/管线会静默失真:

1. **feed/ JSON 是对外契约**:前端 + 任意下游靠 GitHub raw 读;字段改名/结构变动 = 破坏订阅者。改 schema 必须升版本 + 兼容过渡。
2. **`live` 分支只放 `feed/intraday/latest.json`**:别把别的状态写进 live,会污染 5min 心跳。
3. **三处口径一致性**(methodology.md):改任一处分析逻辑,三处(+golden 测试)同步,否则跨端评分不可比。
4. **静态导出约束**:GitHub Pages 部署是 `output: export`,**没有服务端运行时**;`app/api/*` 仅 Vercel 有效,前端不能假设后端常在(`HAS_BACKEND` 开关)。
5. **看门狗/兜底链**:`feed-watchdog`→`intraday-report`→Winter loop 的降级链是盘中数据的生命线,重构调度别拆了兜底。
6. **HMAC + schema 投递闸门**(`validate_feed.py`):OpenClaw 外部投递的安全边界,不能绕过。
7. **数据真实性标注**:moneyflow/chips 是「K 线估算、非 LV2」,UI/feed 的免责标注不能丢(合规)。

---

## 5. 建议的重构推进顺序

```
阶段一 · 立桩与止血(低风险,先做,给后续大改铺安全网)
   R1 一致性测试  →  R2 前端 vitest  →  R3 chan.ts 修复  →  R4 feed 契约  →  R5 空结果保护
   └ 同时:R10 让用户拍板「往蓝图收敛 vs 承认现实」的大方向

阶段二 · 结构收敛(中风险,有测试护栏后做)
   R6 统一报价层  →  R7 后端缓存收敛  →  R8 回测研究层去重

阶段三 · 架构级(高风险,依赖前两阶段 + 用户方向决策)
   R9 分析核算单一化(消双实现)  →  按 R10 决策落地服务化/或固化现状
```

---

## 6. 待用户决策的开放问题

1. **方向**:重构是把现实**往 `architecture.md` 蓝图收敛**(引入 PG/Redis/服务化),还是**承认现状**
   (静态 + feed 中心)并把蓝图改写成现实?——这决定后续所有结构调整的目标形态。
2. **分析双实现**:接受「双实现 + 一致性测试」长期共存,还是投入做单一权威实现?
3. **范围**:本轮重构是**全仓**,还是只聚焦某一子系统(如前端 / 数据管线)?
4. **winter_pg**:Postgres 仓是扶正(纳入 CI 自动跑)还是标记为可选实验、不投入?

> 建议:先从**阶段一**无争议的立桩/止血开始(不依赖上述决策即可推进),并行就第 1、2 题做方向决策,
> 再进入阶段二/三。
</content>
</invoke>
