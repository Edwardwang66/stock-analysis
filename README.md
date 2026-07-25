# Stock Analysis — 个人多市场研究工作台

> **Status:** Current
> **Scope:** Repository entry point, runtime selection, verified quick start, and product limitations.
> **Last verified commit:** `5ab9e2711e46dd501f2140a0149aa133fc83bbc1`

面向个人研究与自托管的多市场行情、技术分析和自动化情报工作台。

## 它是什么 / 不是什么

这个仓库把 Next.js 研究界面、可选 FastAPI 行情服务、Git-backed feed，以及 Python 研究与自动化代码放在一个个人工作台里。它适合本地运行或由使用者自行托管，并允许在不同市场与数据源之间降级。

它不是券商交易执行系统，也没有多用户认证、账户隔离或后台推送服务。公开数据源、代理、缓存与定时任务不能保证实时性、完整性或持续可用；所有界面、规则、报告和研究结果都不是投资建议。

当前实现和目标架构必须分开阅读：[Current Architecture](docs/current-architecture.md) 记录本 checkout 的真实边界，[Target Architecture RFC](docs/rfcs/target-architecture.md) 只描述已接受但尚未完成的迁移目标。

## 当前能力

下表只使用四种状态：`Implemented` 表示代码在仓库内，`Optional` 表示可选集成，`External` 表示运行或控制权在仓库外，`Planned` 表示尚未实现。

| 能力 | 状态 | 当前边界 / 权威 |
|---|---|---|
| Next.js UI 的 11 个页面路由 | Implemented | 页面代码在 `frontend/app/`；职责见 [Current Architecture](docs/current-architecture.md#frontend-pages-and-responsibilities)。 |
| 仓库内 Next quote/OHLCV route implementation | Implemented | `GET /api/quote` 与 `GET /api/ohlcv` 的 Edge route code 已实现；静态导出只在临时构建副本中移除 `app/api`，Server build 保留它们。见 [Deployment Matrix](docs/deployment-matrix.md#vercel-edge-assisted-variant)。 |
| 八个普通市场组与独立指数目录 | Implemented | US、CN、HK、CRYPTO、JP、KR、DE、GB，加 IDX；目录存在不代表搜索、报价、K 线、基本面或盘前盘后能力等深。见 [Current Architecture](docs/current-architecture.md#system-boundary)。 |
| Quote/OHLCV adapters | Implemented | 前端、FastAPI 与公共 provider 的适配链已存在，但 quote 与 OHLCV 的顺序不同，也没有全市场语义一致性保证。见 [Deployment Matrix](docs/deployment-matrix.md#capability-and-degradation-matrix)。 |
| 本地自选、价格提醒和模拟持仓 | Implemented | 数据保存在当前浏览器 `localStorage`，没有账户或跨设备同步；提醒也不是后台推送。见 [Current Architecture](docs/current-architecture.md#state-and-persistence)。 |
| 规则式技术面板 | Implemented | TypeScript、FastAPI Python 与定时 Chan 代码存在重复实现，尚无统一分析权威或完整 parity gate。见 [Current Architecture](docs/current-architecture.md#known-duplication-and-semantic-drift)。 |
| Git-backed feed consumption | Implemented | 前端默认先读 raw GitHub `main/feed`，`NEXT_PUBLIC_FEED_BASE` 可替换 remote base，失败后再读同源 bundled snapshot；多 writer 与跨文件代际一致性仍有限。见 [Feed Contract](docs/data-contracts/feed.md)。 |
| Research/backtest code | Implemented | 仓库包含可执行研究程序；忽略的缓存、变化中的 provider、回顾式切分与成本假设限制复现和解释。见 [Research Index](docs/research/index.md)。 |
| Actions stock-note 的 deterministic fallback | Implemented | 该 workflow 的 fallback 用 OHLCV/SEC 规则生成，不调用 LLM；它设置的 `OPENCLAW_MODEL` 值只填 provenance metadata，不会选择或调用 model，也不能证明外部 agent 参与。见 [OpenClaw Stock Notes](docs/openclaw-stock-notes.md)。 |
| 本地 deterministic/non-LLM formula-factor factory | Implemented | 当前只评估本地公式候选；breadth gate 未实现、PIT 缺失时可跳过过滤、切分是回顾式。见 [Research Index](docs/research/index.md#equity-factor-and-walk-forward-studies)。 |
| FastAPI 数据与兼容分析服务 | Optional | 两种 frontend build profile 都可不启用；无应用认证或 rate limit，且与前端分析代码可能漂移。见 [Backend Guide](backend/README.md)。 |
| 自定义 `NEXT_PUBLIC_EDGE_BASE` 或自有 Next Edge 部署 | Optional | 可替代默认外部别名；当前没有受支持的配置能完全禁用 hard-coded hosted attempt。见 [Configuration](docs/configuration.md)。 |
| Hosted FastAPI backend | Optional | 仓库提供 Render、Dockerfile 与 Procfile building blocks；在线 revision、provider 健康和持久性仍由 operator/host 负责。见 [Deployment Matrix](docs/deployment-matrix.md#hosted-frontend-and-hosted-fastapi)。 |
| Winter/PostgreSQL projection | Optional | `scripts/winter_pg/` 是独立投影/本地分析仓库，不是 FastAPI persistence，也不是基础 profile 依赖。见 [Current Architecture](docs/current-architecture.md#state-and-persistence)。 |
| `https://stock-analysis-ten-phi.vercel.app` 默认别名 | External | checkout 不拥有其在线 revision 或可用性；未配置 custom Edge 且不在 same-origin Vercel 时会尝试它，当前没有受支持的完全禁用开关。见 [Deployment Matrix](docs/deployment-matrix.md#vercel-edge-assisted-variant)。 |
| Public market providers 与 CORS proxies | External | Yahoo、Tencent、Stooq、Binance、OKX、SEC 等的可用性、许可、深度、延迟和返回语义不由仓库保证。见 [Compliance](docs/compliance.md)。 |
| 外部提交的 OpenClaw narrative/agent artifacts | External | Signed external report path 在启用 signature enforcement 时有 HMAC/schema/path 边界；stock-note 是不共享这些边界的独立 privileged direct-write path。Provenance 字段也不是执行证明。见 [OpenClaw Integration](docs/openclaw-integration.md)。 |
| Hyperliquid 数据与服务 | External | 研究和夜盘/衍生品视图依赖外部 API；可达性、内容与历史复现不受 checkout 控制。见 [Research Index](docs/research/index.md#crypto-and-hyperliquid-studies)。 |
| GitHub Actions scheduling/control plane | External | YAML 中的 triggers、job permissions、commands 和 concurrency 是仓库实现；实际 scheduler、runner、Secrets/Variables、platform enforcement 和执行状态属于 GitHub 外部状态，成功 run 也可能只覆盖部分数据。见 [Workflow Operations](docs/operations/workflows.md)。 |
| Hosting platforms | External | GitHub Pages、Vercel、Render 等托管面的 revision、runtime、路由和回滚状态必须在平台侧验证。见 [Deployment Matrix](docs/deployment-matrix.md)。 |
| Factor-factory LLM proposer | Planned | 当前 tracked entry matrix 只有 deterministic formula-candidate factory，没有 LLM proposer implementation。见 [Backtest Guide](backtest/README.md#entry-point-matrix)。 |
| Generated cross-language contracts | Planned | TypeScript/Python models 仍手写且会漂移；尚无生成管线。见 [Target Architecture RFC](docs/rfcs/target-architecture.md#contract-authority)。 |
| Explicit DataGateway profiles | Planned | 页面目前直接调用 library modules；profile abstraction 尚未落地。见 [Current Architecture](docs/current-architecture.md#frontend-pages-and-responsibilities)。 |
| Shared deterministic `analysis-core` | Planned | 前端指标/信号与 Python 分析仍是多个实现，尚无共享权威。见 [Target Architecture RFC](docs/rfcs/target-architecture.md#deterministic-analysis-authority)。 |
| Python `stock_core` package | Planned | 研究与自动化仍通过不稳定 import path 共享代码，稳定 package 尚未建立。见 [Target Architecture RFC](docs/rfcs/target-architecture.md#python-research-boundary)。 |
| Staged atomic reader-facing feed manifests | Planned | 当前 `FEED_PUBLICATION_MANIFEST` 只是 workflow-local Git staging allowlist，不是 reader snapshot 或回滚协议。见 [Feed Contract](docs/data-contracts/feed.md#current-publication-limitations)。 |
| Full semantic parity CI | Planned | Static/Server 共享目标语义，但当前 source order、failure timing 与重复分析代码仍可能不同。见 [Deployment Matrix](docs/deployment-matrix.md#current-gaps-before-semantic-parity)。 |

## 选择运行模式

Static 与 Server 是两个同等支持的 frontend build profile。它们共享 UI，也都可以选择 FastAPI；profile 只决定 Next.js 输出形式，不选择唯一 data plane。共享语义是接受的目标，不是当前已证明的事实。

| 维度 | Static profile | Server profile |
|---|---|---|
| Prerequisites | Node `20.20.2`、npm `10.8.2`。 | Node `20.20.2`、npm `10.8.2`；只有启用可选 FastAPI 时才要求 primary Python `3.11.15`。Python `3.12.13` 仅用于 compatibility CI。 |
| Primary data path | `frontend/out` 中的 UI、bundled/raw Git feed、browser-safe providers，以及当前 Edge selector/fallback 链。 | 同一 frontend，加上保留的 Next quote/OHLCV handlers；仍使用相同 browser/feed fallbacks。 |
| Optional adapters | FastAPI (`NEXT_PUBLIC_API_BASE`)；custom `NEXT_PUBLIC_EDGE_BASE` 或 self-owned Edge deployment。 | FastAPI (`NEXT_PUBLIC_API_BASE`)；custom/same-origin Next Edge deployment。 |
| Persistence | 当前 browser profile 的 `localStorage`；repository/bundled feed snapshot。 | 同样的 browser/feed state；FastAPI 可选 SQLite JSON cache 和 OHLCV bar store，默认 `/tmp` 在 hosted restart 后可能丢失。 |
| Deployment variants | GitHub Pages 或本地静态 build；导出物在 `frontend/out`。 | 自托管 Next 或 Vercel；FastAPI 可另行本地/托管，但不是 Server build 的必选项。 |
| Build command | `npm run build:static` | `npm run build:server` |
| Smoke command | `npm run smoke:static` | `npm run smoke:server`；只测 Next UI/routes，不验证 FastAPI。 |
| Current limitations | 导出物没有本地 Next handlers，依赖 browser-reachable external sources；未证明与 Server 等义。 | 保留 handlers 也不强制 FastAPI；source order、analysis duplication 与外部部署状态仍可能造成差异。 |

如果既没有 `NEXT_PUBLIC_EDGE_BASE`，页面也不在 same-origin `*.vercel.app`，进入 Edge stage 的请求会尝试 hard-coded `https://stock-analysis-ten-phi.vercel.app`。当前没有受支持的配置能把这次尝试完全关闭。

## 快速开始

### Static profile

以下是长时间运行的 Next development preview；它不是 `frontend/out` 的静态文件服务器：

```bash
cd frontend
npm run dev
```

静态交付物使用 profile table 中的 build/smoke 命令生成和验证；完整部署边界见 [Deployment Matrix](docs/deployment-matrix.md#static-profile)。

### Server profile

Next development preview 与上面相同。启用可选 FastAPI 时，在已经按受控 Python lock 准备好的环境中另起这个长时间运行的进程：

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

前端的 `NEXT_PUBLIC_API_BASE` 必须指向可达 FastAPI base，且不能带 trailing slash。Server build 本身不会自动启动或强制使用 FastAPI；安装、托管与 health 边界见 [Backend Guide](backend/README.md)。

### 验证安装

前端公开验证命令要求 exact Node `20.20.2` / npm `10.8.2`：

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test:scripts
npm run build:static
npm run smoke:static
npm run build:server
npm run smoke:server
cd ..
```

下面只是 compact local smoke subset，不是完整 Python CI matrix。它假设当前环境已经由 union CI/release-gate lock 准备好；仅安装 `backend/requirements.txt` 不保证根目录的 feed test 拥有 `jsonschema`。权威 release acceptance 是 [Stage 1C plan 的 exact Python 3.11/3.12 container gates](docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md#controlled-stage-1b-acceptance-gates)。

```bash
cd backend
python tests/test_backend.py
python tests/test_api.py
cd ..
python scripts/tests/test_chan_engine.py
python scripts/tests/test_validate_feed.py
```

## 页面与能力地图

| 路由 | 当前职责 |
|---|---|
| `/` | 多市场报价、指数、自选、feed freshness，以及当前页面可见时的提醒检查。 |
| `/symbol` | Quote/OHLCV、规则指标与信号、Chan/筹码/资金流、比较、提醒配置和 CSV 导出；本页不轮询提醒。 |
| `/desk` | 市场、隔夜、自选、事件、报告与 feed 状态工作区。 |
| `/screener` | 消费定时生成的筛选结果。 |
| `/tracker` | 选股追踪与历史 win-rate 视图。 |
| `/intel` | Feed-backed 市场状态、信号、研究候选、报告、持仓与 freshness 面板。 |
| `/reports` | 展示 Markdown 分析报告。 |
| `/portfolio` | 当前浏览器中的模拟持仓与行情估值。 |
| `/alerts` | 当前浏览器中的价格提醒管理；页面可见时轮询和通知。 |
| `/sources` | 数据源登记、可用性演示与可选后端状态。 |
| `/help` | 当前产品功能地图与使用说明。 |

## 市场与数据能力

市场目录包含八个普通组 `US`、`CN`、`HK`、`CRYPTO`、`JP`、`KR`、`DE`、`GB`，以及独立的 `IDX`。直接使用 `MARKET:CODE` 的 route coverage 比搜索发现范围更广；FastAPI search 主要发现 CRYPTO 与部分 US/HK/CN，不能据此推断 IDX/JP/KR/DE/GB 不可直查，也不能把目录存在解释为各市场能力等深。

FastAPI 的大致 provider chains 是 US 的 Yahoo → Tencent → Stooq、HK/CN 的 Tencent → Yahoo、CRYPTO 的 Binance mirror → OKX，以及 IDX/JP/KR/DE/GB 的 Yahoo。具体 history cap、interval、freshness、license 和 fallback 会随 provider/market 改变，详见 [Backend Guide](backend/README.md#providers-and-market-coverage)。

Watchlist、`alerts:v1` 和 `portfolio:v1` 保存在这个 browser profile 的 `localStorage`，没有账号、服务端同步或跨设备一致性。`/symbol` 只配置提醒；只有首页或 `/alerts` 保持打开且可见时才会轮询并触发浏览器通知，没有后台 push service。

只有 Binance CRYPTO 路径读取真实 `aggTrades` 与 order-book `depth`。股票 money-flow 和 chip distribution 是由 K 线价格/成交量推导的估算，不是交易所逐笔、账户持仓或“主力”真值。SEC EDGAR fundamentals 只覆盖可用 XBRL 的美国申报主体，并非全球基本面服务。

## 数据来源、时效与估算口径

Quote 与 OHLCV 不是一条虚构的统一链。它们都受 market-aware freshness、browser persistence、外部 provider、CORS 与 runtime profile 影响。

**Quote 当前顺序：**

1. market-aware freshness window 内的新鲜 memory quote 或 browser-persisted quote；
2. optional FastAPI batch，限 non-IDX symbols；
3. unresolved non-crypto symbols 的 Edge quote route；
4. 至少三个 non-crypto symbols 仍 unresolved 时读取 fresh `live`-branch snapshot；该 unresolved set 可以包含 IDX；
5. unresolved non-IDX symbols 的 per-symbol FastAPI fallback；
6. crypto 直连 Binance；其他 unresolved symbols 通过 ordered public CORS proxies 访问 Yahoo；
7. 只有 per-symbol fetch 抛错时，才使用不超过 10 分钟的 persisted quote。

**OHLCV 当前顺序：**

1. 新鲜 `localStorage` bar series；
2. 每个市场都先尝试 Edge OHLCV route，包括 CRYPTO 与 IDX；
3. optional FastAPI，限 non-IDX symbols；
4. 直连 Binance，或通过 ordered public CORS proxies 访问 Yahoo；
5. 只有 fetch 抛错时，才使用不超过 24 小时的 persisted bars。

一次成功但返回空数组的 OHLCV fetch 会保持为空，不会触发 stale-series exception fallback。配置了 FastAPI 也不代表每个请求都会经过它；provider freshness、proxy/CORS、snapshot age 和 stale behavior 会按市场与 profile 不同。完整链路权威是 [Current Architecture](docs/current-architecture.md#current-interactive-data-paths)。

## Feed 与自动化

`feed/` 是多 writer 的 Git-backed publication surface 和 integration surface，不是全系统唯一真值。前端对多数 intelligence artifact 默认先尝试 raw GitHub `main/feed`；`NEXT_PUBLIC_FEED_BASE` 可替换这个 remote base，失败后再尝试 same-origin bundled `public/feed`。Live intraday quote snapshot 则来自独立 `live` branch，因此一次页面读取可能混合不同 generation。

GitHub Actions 的 tracked YAML 实现 triggers、job permissions、validation/publication commands 和 concurrency policy；实际 scheduler、runner、Secrets/Variables、platform enforcement 和执行状态则在仓库外。一个 workflow 成功不等于所有 market/provider 都成功，也不证明产物完整或 hosted 页面已经更新；普通 feed-only commit 通常不会触发 Pages bundle rebuild。

Actions stock-note fallback 是 deterministic OHLCV/SEC rule path，不调用 LLM。只有外部提交的 OpenClaw narrative/agent artifacts 属于外部 agent 输出；该 workflow 的 `OPENCLAW_MODEL` 值只填 provenance metadata，不会选择或调用 model，也不能单独证明执行来源。

OpenClaw 有两条不同的 trust path：signed external report ingress 在相应配置下执行 HMAC/schema/path validation；standalone stock-note client 则可由受信 operator 直接写文件，不经过 report HMAC、report schema、`feed/inbox/` 或 approved-root containment，也不会自动重建 stock-note index。不要把两者描述成统一 validation pipeline；详见 [OpenClaw Stock Notes](docs/openclaw-stock-notes.md#authentication-and-trust)。

当前 `FEED_PUBLICATION_MANIFEST` 只是部分 workflow 使用的 Git staging allowlist。它不是前端读取的 atomic snapshot manifest，也不保证跨文件 completeness 或 previous-complete rollback；reader-facing staged atomic manifests 仍是 Planned。权威边界见 [Feed README](feed/README.md)、[Feed Contract](docs/data-contracts/feed.md) 和 [Workflow Operations](docs/operations/workflows.md)。

## 研究与回测

`backtest/` 与 `scripts/` 包含当前可执行的 equity、stat-arb、crypto、PIT、screening 和 operational research code。历史页面保留当时的方法与结果，不是当前产品保证；不能把旧指标、回测标签或报告日期解释为实时 alpha、可交易性或可复现性。

本地 factor factory 当前是 deterministic/non-LLM formula-candidate evaluator。它没有实现 breadth gate，PIT 文件缺失或无效时会 warning 后跳过过滤，split 是 retrospective；LLM proposer 仍是 Planned。更多复现、survivorship、cache、cost、borrow/locate 和 execution-timing 限制见 [Research Index](docs/research/index.md) 与 [Backtest Guide](backtest/README.md)。

Hyperliquid 与其他 live research inputs 属于 External。忽略的 cache、变化中的 universe/provider 和未冻结的 raw inputs 会让相同代码产生不同覆盖或结果。

## 部署

- Static profile 可发布 `frontend/out` 到 GitHub Pages，也可保留为本地静态 build。Pages workflow 使用临时、fail-closed feed snapshot；普通 feed-only 更新通常不会重建 bundle。
- Server profile 可部署保留 Next route handlers 的 server output。FastAPI 是独立可选进程，可本地运行或按已跟踪 Render/Docker building blocks 托管。
- Hard-coded Vercel alias、GitHub Pages、Render 与其他 hosting platform 的在线 revision、runtime、配置、路由和回滚都属于外部状态；可达不等于与当前 checkout 一致。
- Production start、health、base path、rollback 和 host-specific caveat 统一以 [Deployment Matrix](docs/deployment-matrix.md) 为准；环境变量所有权见 [Configuration](docs/configuration.md)。

不要从一次 smoke test 推断外部 provider、FastAPI 或 hosted deployment 健康。`smoke:server` 验证的是 Next UI/routes，不是 FastAPI。

## 仓库结构

```text
.
├── .github/      # GitHub Actions definitions and repository automation
├── backend/      # Optional FastAPI market-data/cache/analysis service
├── backtest/     # Executable research and backtest programs
├── docs/         # Current authorities, RFCs, plans, and historical studies
├── feed/         # Git-backed generated JSON/Markdown publication surface
├── frontend/     # Next.js UI, data adapters, routes, and static/server builds
├── requirements/ # Hash-locked union requirements for CI/automation contexts
├── research/     # Two dated historical external-research snapshots
├── routines/     # Operational playbooks and agent task definitions
├── scripts/      # Producers, validators, monitors, and operations tooling
└── state/        # Current Winter polling cursor/state
```

## 文档导航

- 先理解当前系统：[Current Architecture](docs/current-architecture.md)
- 选择运行与部署方式：[Deployment Matrix](docs/deployment-matrix.md)
- 配置 public/internal 环境变量：[Configuration](docs/configuration.md)
- 运行可选 FastAPI：[Backend Guide](backend/README.md)
- 理解 feed 读写、schema 与 atomicity：[Feed README](feed/README.md) / [Feed Contract](docs/data-contracts/feed.md)
- 审计 workflow trigger、权限、writer 与 failure mode：[Workflow Operations](docs/operations/workflows.md)
- 理解 OpenClaw 边界：[OpenClaw Integration](docs/openclaw-integration.md) / [OpenClaw Stock Notes](docs/openclaw-stock-notes.md)
- 运行和解释研究：[Backtest Guide](backtest/README.md) / [Research Index](docs/research/index.md)
- 区分目标与现状：[Target Architecture RFC](docs/rfcs/target-architecture.md)
- 检查许可、隐私与使用限制：[Compliance](docs/compliance.md)

## 已知限制

- Static 与 Server 尚无 full semantic parity；source ordering、failure timing、handwritten contracts 和重复分析实现都可能漂移。
- 未配置 custom Edge 且不在 same-origin Vercel 时会尝试 hard-coded external alias，当前没有受支持的完全关闭方式。
- Public providers、CORS proxies、raw GitHub、hosting 与 schedules 可失败、限流、改变语义或返回不等深数据；market catalog 不是 coverage guarantee。
- FastAPI Binance adapter 没有正确映射 `30m`：请求可能实际取得 daily bars，却仍以 `30m` 标记、存储和返回；修复前不要把该路径当作 30-minute data。
- FastAPI 默认 SQLite cache/bar store 位于 `/tmp`，hosted restart/instance change 后可能是冷的或丢失；bar-store high-water mark 也不证明 provider history 完整。
- Feed reader 没有 atomic cross-file generation contract，raw/bundled/live-branch reads 可以混合代际；workflow success 也可以与 partial coverage 或 producer failure 共存。
- OpenClaw stock-note direct write 没有 external report ingress 的 HMAC/schema/path containment，且不会自动重建 note index；只能交给受信 operator 与受限 token。
- Pages 的普通 feed-only 更新通常不触发 bundle rebuild，因此 repository feed 比已部署 bundle 新并不反常。
- Browser state 不同步；提醒只在首页或 `/alerts` 打开且可见时工作，没有 service worker/backend push。
- Stock money-flow/chips 是 K-line estimates，SEC fundamentals 仅限可用 XBRL 的 US filers，search discovery 也窄于 direct route support。
- 研究依赖 mutable providers、ignored caches 和不完整的 PIT/cost/execution assumptions；历史结果和标签不是未来表现、实时状态或交易保证。
- Next Edge 与 FastAPI routes 没有应用级 authentication/rate limiting；不要把公开部署当作私有或 multi-tenant boundary。

## 安全、合规与非投资建议

本项目面向个人研究和 self-hosting。不要向 feed、browser storage、Git history、logs 或 public environment variables 写入 broker credential、个人身份信息、交易账户资料或其他 secret。任何外部 ingress、workflow permission、host variable 和 deployment revision 都应独立审计。

免费或非官方 market endpoints 不等于可重分发授权；commercial/public use 必须重新核对 provider terms、地域规则、数据许可、SEC/交易所要求与适用法律。详见 [Compliance](docs/compliance.md)。

本项目不连接券商下单，不提供受托管理、个性化投资建议或收益保证。行情、估算、信号、自动化产物、OpenClaw 内容和回测都仅供信息与研究；做任何资金决策前应自行核验原始数据、风险、成本和合规条件。
