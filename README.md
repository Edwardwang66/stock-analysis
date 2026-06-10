# 多市场股票数据看板平台 (Multi-Market Stock Data Dashboard)

> 一个聚合 **美股 / 港股 / A股 / 加密货币** 行情、基本面、新闻舆情与 AI 分析的数据看板平台。
> 技术栈:**Next.js (前端) + Python / FastAPI (后端 · 数据 · AI)**。

当前阶段:**P1 MVP 编码中** — 美股 + 加密的实时行情看板 + **非 LLM 技术分析**已可运行,静态前端可部署到 GitHub Pages。

新增 **富途式看板(Futu-style)** 模块:**资金流向 / 主力资金**、**筹码分布 / 获利比例 / 支撑位·压力位**、**买卖盘口**、**基本面财报**,对标富途个股页。

## ✨ 看板功能一览(2026-06-10 更新)

**首页看板**:打开默认加载**全部市场**(美/港/A/加密并行,渐进式渲染:快源先上屏);
指数概览行(标普500/纳指/道指/恒指/上证,可点入详情);今日强弱 Top3 涨跌榜(零额外请求);
按市场分组的行情卡片(组内涨/跌/均值统计,开闭市状态徽标);涨跌热力图;
卡片右上角 ★ 一键自选;单卡失败可独立重试;tab/排序记忆;30s 自动刷新(后台页暂停)。

**个股页**:K线(日/周/小时 × 6mo-5y)+ 简化缠论叠加;页头实时价与 K线末根、技术指标**三者同源一致**;
主力资金/筹码分布/基本面;52 周区间;**⏰ 价格提醒**(纯前端,触发系统通知);K线 CSV 导出;
浏览器标签页实时显示价格。

**一致性口径**:加密涨跌 = **24h 滚动**,股票 = **较前收盘**,卡片/热力图/页脚均已标注;
screener 选股表加载后用统一数据层**实时价覆盖**清单生成时的冻结价;全站单一报价数据层(双层缓存:内存 30s + localStorage 秒开)。

**其他**:自选+提醒 JSON 导入导出(跨设备迁移);PWA manifest(手机可加到主屏);
`/sources` 页后端健康面板(运行时长/缓存/熔断实况);情报 feed 陈旧时首页轻提示;移动端 640px 适配。

**6-10 新增**:**中英双语**切换挂全站 + 搜索双语联想(中文名可搜美股);首页大分组折叠(默认 12 卡,可展开);
**`/desk` 工作台**:盘前隔夜要素行(premarket pack)+ 🔥 高波动榜(近 7 天事件聚合)+ 选股 winrate 上墙
+ 🌙 24/7 夜盘代理 + 🔮 Pre-IPO 永续定价(SpaceX/Anthropic/OpenAI,数据源 Hyperliquid HIP-3);
**`/screener`**:全宇宙 **RS 1-99 排名榜**(方法论六法落地)+ 每日技术评分≥80 清单 + **52周新高接近榜**
(距高≤3% 动量区,w52 位置随 screener 同趟产出);`/tracker` 选股表现追踪看板;
个股页 **☯ 缠论结构面板**(原文 24 课口径:背驰度量化 + 确认三件套 + 一二三类买卖点历史表与事后表现自检),
配套 Python 缠论引擎每周跑**全宇宙买卖点胜率统计**(`chan-stats.yml` → `/tracker` 看板);
K线再叠加**自动斐波回撤 / Ichimoku 简版 / VSA 量价异动标记**(方法论二期 5 项全落地)。

---

## 🛰️ 自我优化的做多做空情报闭环(新)

按设计文档《美股中频混合量化系统 v1.0》落成的**持续运转回路**:做多做空引擎(流 B 残差统计套利)+
每小时/每日 routine + LLM 假设工厂 + OpenClaw 外部 agent + 情报看板。总览见
[`docs/self-improving-alpha-loop.md`](docs/self-improving-alpha-loop.md)。

- **优化后的做多做空逻辑** [`backtest/statarb.py`](backtest/statarb.py):残差→OU s-score→滞回→**协整断裂熔断**→
  Garleanu-Pedersen aim 组合(控换手)→分层限额+**容量地板**→**净·扣成本** + Deflated Sharpe。
  诚实结论:免费数据上净 alpha ≈0/为负 —— 实证「真 alpha 在容量受限冷门层」。见 [`backtest/README_statarb.md`](backtest/README_statarb.md)。
- **routine(不断 post 报告)** [`routines/daily-alpha-routine.md`](routines/daily-alpha-routine.md) +
  [`scripts/run_routine.py`](scripts/run_routine.py) + 定时工作流 `alpha-routine.yml`。
- **静态网页不断接受** [`frontend/lib/feed.ts`](frontend/lib/feed.ts):GitHub raw 实时 + 捆绑快照兜底,**无需重建 Pages**。
- **OpenClaw 完整方案** [`docs/openclaw-integration.md`](docs/openclaw-integration.md):agent 名册 + 三投递通道 +
  HMAC 签名 + CI 安全闸门(`scripts/validate_feed.py`)。
- **情报看板 `/intel`**:何时获得多少信息 / 怎么帮助到系统 / 仓库是否最新(站内 🛰️ 情报看板入口)。
- **引擎迭代(Cycle 1-6,2026-06-10)**:真 holdout 终检 + 净值曲线/SR 趋势上看板(C1);数据**实效性/连贯性审计**体系
  + CSCV-PBO 过拟合研究([`docs/study-pbo-2026-06-10.md`](docs/study-pbo-2026-06-10.md))+ 公式因子工厂(C2-4);
  **回撤治理阶梯 + SSR 做空约束**进引擎,审计全绿(C5);**D5 下沉实验首次实证** + 月度研究定时(`monthly-studies.yml`)
  + 幸存者偏差数据源调研(C6);**Hyperliquid 全接口接入**——HIP-3 24/7 美股代理 + 持仓面拥挤 + 跨所错位,
  配 2h 衍生品情报定时(C7);隔夜缺口研究——代理 corr 0.965 但信号无预测力,**诚实否定**(C8,
  迭代日志见 [`docs/iteration-log.md`](docs/iteration-log.md))。
- **OpenClaw 专项(持续多轮,至第 9 轮)**:三报告上看板 + note schema v2;winrate 上墙 + stance 翻转检测 + 事件热度任务;
  高波动榜消费端 + **投递 SLA 看门狗**(`openclaw-watchdog.yml`,缺投自动开 Issue);盘前隔夜要素包(`premarket-pack.yml`);
  Codex public-equity-investing 插件接入。

**🔧 自动化运维**:17 个 GitHub Actions 工作流无人值守 —— 13 个定时任务(screener/digest/intraday/市场快照/13F/
缠论周报/盘前要素包/月度研究/Hyperliquid 2h 情报/双看门狗/keep-warm/alpha-routine)+ Pages 部署 + 投递校验闸门
+ **单元测试闸门**(`tests.yml`:后端冒烟 + 缠论引擎/投递闸门单测,push 与 PR 都跑)
+ **Dependabot 自动合并**(`dependabot-automerge.yml`:月度 minor/patch 自动合,major 拦截留人工)。
已知问题与技术债持续记录在 [`docs/need-to-fix.md`](docs/need-to-fix.md)。

**主力资金的数据真实性(重要)**:
- **暗号**:接入 Binance **真实逐笔(aggTrades)+ 真实盘口(depth)**,按成交额分档 + 主动买卖方向算 → **真·主力资金 / 真·买卖盘**(免费源里少数能拿到逐笔的市场)。
- **股票**:免费行情无逐笔/盘口,用 **分钟 K 线** 做透明代理估算(成交额分位数分档 + 收盘涨跌定方向,主力=特大+大),UI 标注「K线估算」,仅供趋势参考。要还原券商口径需券商 LV2 / 富途 OpenAPI,A 股可在境内部署接东方财富资金流。

**新接入的免费数据源(2026-06 实测,零/免费 key)**:Binance(逐笔+盘口)、SEC EDGAR(美股官方财报)、Frankfurter/ECB(外汇)、OKX/Coinbase/CoinPaprika(跨所校验)、open.er-api。站内 **`/sources`** 页有实时演示 + 完整登记表(详见 [`docs/working-apis.md`](docs/working-apis.md))。
> ⚠️ 均为免费源,仅供演示/自用,**非投资建议**;商用对外须换授权源(见 [`docs/compliance.md`](docs/compliance.md))。
> 修复:公共代理 `corsproxy.io` 已失效,改为 `allorigins` 优先(影响全部美/港/A 股浏览器直连)。

## 🚀 快速开始

```bash
# 前端(静态站点,零 key,浏览器直连公开 API)
cd frontend && npm install && npm run dev        # http://localhost:3000

# 后端(可选,更稳定 / 未来部署)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

**GitHub Pages 部署**:仓库 Settings → Pages → Source 选 **GitHub Actions**;推送后 `.github/workflows/deploy-pages.yml` 自动构建发布。站点地址:`https://edwardwang66.github.io/stock-analysis/`。

> 实测可用的数据 API 见 [`docs/working-apis.md`](docs/working-apis.md)。当前分析**全程非 LLM**(纯技术指标规则)。

## 📁 仓库结构

```
.
├── README.md                          # 本文件:项目总览
├── frontend/                          # Next.js 静态前端(GitHub Pages):看板 + /intel 情报看板
├── backend/                           # FastAPI 后端:行情适配器 + 非LLM分析(Python)
├── backtest/                          # 因子研究 + 回测;statarb.py = 流 B 做多做空引擎
├── feed/                              # 情报馈送(JSON 单一真相源):routine + OpenClaw 写,看板读
├── scripts/                           # 定时任务执行端:screener/digest/intraday/快照/13F/盘前包/审计/投递
├── routines/                          # Claude 可执行 routine playbook
├── state/                             # 跨 session 持久状态(winter 轮询位点等)
├── .github/workflows/                 # 17 个工作流:13 定时任务 + Pages 部署 + 投递/测试闸门 + dependabot 自动合并
├── research/
│   └── ai-agents-skills-market-scan.md  # 市场调研:股票/经济/市场相关 AI Agent 与 Skills 全景
└── docs/
    ├── architecture.md                # 平台技术架构设计
    ├── roadmap.md                     # 分阶段路线图与 MVP 范围
    ├── positioning.md                 # 差异化定位分析(vs 竞品)
    ├── cost-estimate.md               # 成本测算(数据源 + Claude API + 基建)
    ├── compliance.md                  # 合规 / 法律专项
    ├── data-model-api.md              # 数据模型 / REST·WS API 契约
    └── …                              # self-improving-alpha-loop / openclaw-integration / study-pbo 等,见文档导航
```

## 🎯 项目定位

**数据看板(Data Dashboard)**——以"看得清、查得到、问得懂"为核心:

1. **行情看板**:多市场实时/历史行情、K线、指标、热力图。
2. **基本面**:财务报表、估值、财报解读。
3. **新闻舆情**:聚合新闻 + AI 情绪分析。
4. **AI 助手**:自然语言查询、个股分析、研报生成(基于 Claude / 开源金融模型)。

## 🌍 覆盖市场

| 市场 | 代表数据源 | 备注 |
|------|-----------|------|
| 美股 US | yfinance / Finnhub / Polygon(现 Massive) / FMP / Alpha Vantage | 数据源最丰富 |
| 港股 HK | yfinance / Futu OpenAPI / AkShare | 部分源覆盖 |
| A股 CN | Tushare / AkShare / 东方财富 | 注意合规与重分发限制 |
| 加密 Crypto | Binance / CoinGecko / CoinMarketCap | 7×24 行情 |

## 📚 文档导航

- 想了解**市面上有哪些 AI 股票工具/Agent/Skills** → [`research/ai-agents-skills-market-scan.md`](research/ai-agents-skills-market-scan.md)
- 想了解**平台怎么搭** → [`docs/architecture.md`](docs/architecture.md)
- 想了解**先做什么、后做什么** → [`docs/roadmap.md`](docs/roadmap.md)
- 想了解**我们凭什么赢(竞品差异化)** → [`docs/positioning.md`](docs/positioning.md)
- 想了解**要花多少钱** → [`docs/cost-estimate.md`](docs/cost-estimate.md)
- 想了解**合规怎么办** → [`docs/compliance.md`](docs/compliance.md)
- 想了解**数据模型与 API 长什么样** → [`docs/data-model-api.md`](docs/data-model-api.md)
- 想了解**哪些数据 API 实测可用** → [`docs/working-apis.md`](docs/working-apis.md)
- 想速查**所有接入的端点(上游源 + 本平台 API)** → [`docs/endpoints.md`](docs/endpoints.md)
- 想看**已知问题 / 技术债清单(持续审查)** → [`docs/need-to-fix.md`](docs/need-to-fix.md)
- 想跑**后端** → [`backend/README.md`](backend/README.md)
- 想**部署后端**(摆脱公共代理限流) → [`docs/deploy-backend.md`](docs/deploy-backend.md)

## ⚖️ 合规提示

- 多数免费行情源(如 yfinance/Yahoo)**禁止商业化重分发**,生产环境需采购正规授权数据。
- A股数据源(Tushare 等)有积分/权限与再分发限制。
- 平台所有 AI 输出均为**信息参考,非投资建议**(not financial advice)。
