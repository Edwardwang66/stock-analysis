# 2026 免费/低成本 基本面 + 预期数据源全景(长期投资用)

> 调研日期 **2026-06-18**。面向成熟量化/投研系统的**长期投资**用途:PIT 治理、防过拟合、免费数据优先、feed+看板。
> 房子风格:**诚实可证伪**,标注**许可/重分发限制**,关键结论给**一手来源 URL + 可信度**。
> ⚠️ 价格 / 免费层 2025-2026 频繁变动;无法从一手源核实的数字一律标 **未核实**。
> 配套:[`../../docs/compliance.md`](../../docs/compliance.md)(§1 数据重分发红线)· [`../../docs/working-apis.md`](../../docs/working-apis.md)(本仓库实测可用 API)。
> 可信度口径:**高** = 官方一手页面/文档当日可达;**中** = 官方页面 JS 渲染只取到摘要 + 近期第三方互证;**低** = 仅第三方/旧值。

---

## 1) TL;DR

1. **免费、真·PIT(point-in-time / as-originally-filed)的基本面只有一个:SEC EDGAR。** 美股、公有领域、可商用可重分发、10 req/s、无 key。这是全景里**唯一**同时满足"免费 + PIT + 可重分发"的源。**长期投资的基本面底座必须是 EDGAR。**
2. **EDGAR 的 JSON / frames API 本身并非严格"原始申报值"** —— companyfacts/frames 会被修正值覆盖(frames 返回"最贴近该期、最后申报"的那条)。**要拿真·PIT 必须落地到季度 Financial Statement Data Sets(每季冻结的 vintage)或自己解析单份 filing。** 这是最容易被忽视的坑。
3. **分析师预期 / 盈利修正几乎全付费。** 不存在真·免费、真·PIT 的 consensus/revisions 源。免费的(Yahoo)只是**当前快照、重述、易碎、非商用**。要做修正因子,**预算一个付费 vendor**(I/B/E/S、FactSet、Visible Alpha、Zacks)。
4. **免费聚合/补洞层**:**OpenBB Platform** 是开源**聚合器(自身不持有数据)**,用它统一接 SEC + Yahoo + FMP/Tiingo/AV 免费层。但聚合器解决不了"许可"与"PIT"——许可随底层源走。
5. **低成本 PIT 付费选项**:**Sharadar SF1**(经 Nasdaq Data Link,AR 维度真·PIT,~1998 起,个人档历史约 $30/月**未核实 2026 价**)是性价比最高的"EDGAR 兜底/校验"。**SimFin**($0–$71/月)便宜但 **PIT 未核实**。**Norgate**($,US/AU)是**价格+成分股**做无幸存者偏差,**不是基本面库**。
6. **几乎所有免费源禁止商用/重分发**(yfinance/Yahoo、AkShare、Stockanalysis、FMP/Tiingo/AV/Finnhub 免费档)。对外看板**只能暴露 EDGAR(公有领域)**;其余免费源仅供**内部计算/缓存/原型**,与本仓库 `compliance.md` 既有立场一致。
7. **国际/A股/港股**:`AkShare`(MIT 代码,爬取,易碎,数据许可灰色)+ `Tushare`(积分制、有 `ann_date` 可近似 PIT、墙外访问慢)。两者皆**非商用重分发**。

**一句话落地:EDGAR 为主(PIT 底座)+ Sharadar SF1 兜底/校验(若有预算)+ Yahoo/yfinance 仅做快速原型与非美兜底 + 预期数据按需付费。**

---

## 2) 数据源对比大表

> PIT 列:✅=源生真·PIT;⚠️=部分/需额外处理;❌=重述(restated, latest-only);未核实=无法证实。
> 重分发列:✅=许可允许;❌=禁止/需单独授权。

| 源 | 覆盖 | 历史深度 | PIT | 限频 | 许可(重分发/商用) | 免费额度 / 价格 | 可信度 |
|---|---|---|:--:|---|---|---|:--:|
| **SEC EDGAR** | 美股全 XBRL 申报人 | XBRL 2009→今(文本 1994→) | ⚠️ JSON=latest;**FSDS 季度集=真PIT** | **10 req/s**,需 User-Agent | **✅ 公有领域,可商用可重分发** | **免费,无 key** | **高** |
| **Sharadar SF1**(NDL) | >14,000 公司 / >21,000 含退市 | **~1998→今** | **✅ AR 维度** | NDL API 限频 | ❌ 标准档不含重分发;分 personal/pro | ~$30/月个人(**2026 价未核实**) | 高(规格)/中(价) |
| **SimFin** | ~5,000+ 美股 | 5 / 10 / 15 / 20+ 年(按档) | **未核实** | 2→20 req/s;月 credits | ❌ 退订需删数据 | $0 / $15 / $35 / $71 月 | 高 |
| **FMP** | 免费≈美股为主 | 免费 ~5 年 | ❌(未核实) | 250 calls/日 | ❌ 个人非商用,展示/重分发需单独协议 | 免费 250/日 | 中(ToS=高) |
| **Tiingo** | 6.5万+ 美股+ETF+中概 | 免费 ~5 年(基本面) | 未核实 | 50/时,1000/日,500 符号/月 | ❌ 商用需 Business $50/月 | 基本面为**付费 add-on**(DOW30 demo) | 中 |
| **Alpha Vantage** | 美股为主 + 部分全球 | ~5–20 年(确切未核实) | ❌(未核实) | **25/日,5/分** | ❌ 商用需 premium | 免费 25/日 | **高** |
| **Finnhub** | 免费=美股 | 免费深度未核实 | As-Reported=⚠️ 但**付费** | **60/分**(~30/秒) | ❌ 商用/重分发需付费 | 免费 60/分;Basic Financials 免费 | 中 |
| **OpenBB Platform** | **聚合器(不持数据)** | 随底层源 | 随底层源 | 随底层源 | 代码 **AGPLv3**;数据随源 | 平台免费;Workspace Pro 付费 | 高 |
| **Norgate** | **US + AU**;价格+成分股 | 数十年(价格) | 成分股/退市=✅;**非基本面** | 本地库,非 per-call | ❌ 个人单用户,不可重分发 | ~$70–80/月/市场(**2026 未核实**) | 高 |
| **Stockanalysis.com** | 美股+大量国际 | Pro ~10 年 | ❌ | 无官方 API | ❌ 禁爬/禁重分发 | 免费档 + Pro ~$10–15/月(未核实) | 中-高 |
| **Yahoo / yfinance** | 全球 Yahoo 所示 | **~4 年年报 / 4–5 季** | ❌ 重述 | 无官方;429 易封 | ❌ ToS 个人非商用 | 免费,无 key | 中(易碎) |
| **分析师预期(免费)** | Yahoo 等仅当前快照 | 无 PIT 历史 | ❌ | — | ❌ | 免费但快照/重述/易碎 | 低 |
| **分析师预期(付费)** | I/B/E/S / FactSet / Visible Alpha / Zacks / Bloomberg | 深,真PIT+修正史 | ✅ | — | 企业授权 | **全付费,无免费层** | 高 |
| **AkShare** | A股/港/美+期货基金宏观 | 按端点而异 | ❌ | 爬取,易封 IP | ❌ 代码 MIT,**数据灰色** | 免费,无 key | 中 |
| **Tushare** | A股核心 + 部分港/美 | 深(A股) | ⚠️ 有 `ann_date` 可近似 | 积分制 + 每分钟限 | ❌ 个人/研究,不含重分发 | 免费但积分受限;会员 ~¥200+/年 | 中-高 |

---

## 3) 逐源详评

### 3.1 SEC EDGAR —— 唯一真·免费·PIT 基本面(底座)
- **一手源(高):** [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) · [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
- **端点(子代理当日实测 HTTP 200):** `submissions/CIK##########.json`、`api/xbrl/companyconcept/CIK########## /us-gaap/<tag>.json`、`api/xbrl/companyfacts/CIK##########.json`、`api/xbrl/frames/us-gaap/<tag>/<unit>/CY####Q#.json`。无 key、无注册。本仓库 `frontend/lib/fundamentals.ts` 已接 companyconcept(见 working-apis.md)。
- **覆盖:** 所有 XBRL 申报人(10-K/10-Q/8-K/20-F/40-F/6-K 等)。**历史:** 结构化 XBRL 自 **2009** SEC 强制起;文本申报回溯 ~1994。
- **PIT —— 关键细节:** companyfacts/frames **跨申报聚合**,修正/重述值会覆盖或并存;frames 文档明确返回"该期最后申报、最贴近"的那条 → **不是 as-originally-filed**。**真·PIT 路径:用季度 Financial Statement Data Sets(DERA,每季冻结 ZIP,2009Q1→今,2023-04 起另有月度集),或自己解析每份 filing 并以 filing 日期建 vintage。**
- **限频/礼仪:** **10 req/s**(超 → 429 + 约 10 分钟临时封 IP);**必须带描述性 User-Agent(含联系邮箱)**,否则 403。**批量:** 夜间 `companyfacts.zip` / `submissions.zip`(13,000+ 公司一次拉全,远快于逐 CIK 调用)。
- **许可:** **美国政府作品,公有领域** —— 可自由重分发、可商用。**全景中唯一对外看板可直接暴露的免费基本面源。**
- **局限:** 仅美股;XBRL 标签不规范/自定义扩展(extension tags)导致跨公司对齐成本高;XBRL 前(2009 前)无结构化数据;非财报型预期数据没有。

### 3.2 Sharadar SF1(经 Nasdaq Data Link)—— 低成本真·PIT 兜底
- **一手源(高/价格中):** [NDL SF1](https://data.nasdaq.com/databases/SF1) · [Sharadar](https://www.sharadar.com/) · [QuantRocket Sharadar](https://www.quantrocket.com/sharadar/)
- **NDL 2026 仍在运营**(Quandl 已并入 data.nasdaq.com,旧链重定向)。**覆盖:** 150 指标;>14,000 公司;>21,000 含退市(无幸存者偏差)。**历史:** 基本面 **~1998 起**(部分营销称 1990,**未核实**,以 1998 为准)。
- **PIT:** **✅ 真·PIT** —— 提供 **ARQ/ARY/ART(As-Reported)** 与 **MRQ/MRY/MRT(Most-Recent)** 维度,AR 保留首次申报值与修正历史。**这是相对 EDGAR JSON 的核心增值:开箱即用的 PIT,免去自建 vintage。**
- **许可:** 分 Non-Professional / Professional;标准订阅**不含重分发**。**价格:** 登录墙;历史上个人档 ≈ **$30/月**、bundle ≈ $59–99/月;**2026 确切价未核实**。
- **定位:** 若有预算,**这是 EDGAR 的最佳兜底/交叉校验**(尤其 PIT 因子回测),性价比最高。

### 3.3 SimFin —— 便宜但 PIT 未证实
- **一手源(高):** [SimFin Pricing](https://www.simfin.com/en/prices/) · [GitHub](https://github.com/SimFin/simfin)
- **覆盖** ~5,000+ 美股;**历史** 5/10/15/20+ 年(免费/START/BASIC/PRO)。**价格 2026:** **$0 / $15 / $35 / $71 月**(年付约 -40%)。**限频** 2→20 req/s + 月度 credits;BASIC+ 才有完整 bulk CSV。
- **PIT:** **未核实** —— AI 抽取的标准化"as-reported",**无明确 PIT/原始申报快照保证**。当标准化基本面用,别当已验证 PIT。
- **许可:** 退订需删数据 → **不可重分发**。便宜、bulk 友好,但 PIT 不可靠 → **不适合做严肃 PIT 因子的唯一源**。

### 3.4 Financial Modeling Prep(FMP)—— 免费层仍在,但商用/重分发严
- **一手源:** [ToS(高)](https://site.financialmodelingprep.com/terms-of-service) · [Pricing(中,403/JS)](https://site.financialmodelingprep.com/developer/docs/pricing)
- **免费 250 calls/日**,免费档**美股为主**、EOD、年报 ~5 年。**PIT:** 重述、非 PIT(未核实)。
- **许可(高):** ToS 明确**免费/个人档禁止任何 Commercial Use**(含受雇于企业即算),**展示/重分发禁止**,需单独 Data Display & Licensing 协议。本仓库 compliance.md 已记此点。
- **2025-2026:** 免费仍 250/日可用;**无证据基本面被新关进付费墙**(未核实)。

### 3.5 Tiingo —— 基本面是付费 add-on
- **一手源(中,JS):** [Pricing](https://www.tiingo.com/pricing) · [Fundamentals Docs](https://www.tiingo.com/documentation/fundamentals)
- 免费 50/时、1000/日、500 符号/月;价格 EOD 历史深(30–50 年)。但**基本面 API 是付费 add-on,非免费档**(历史上 beta 提供 **DOW30 样本**做评估)。**商用需 Business $50/月。****PIT 未核实。**
- 定位:价格源还行;**基本面对免费用户基本不可用**。

### 3.6 Alpha Vantage —— 免费基本面端点齐但 25/日地板
- **一手源(高,页面可渲染):** [Premium/Pricing](https://www.alphavantage.co/premium/) · [Documentation](https://www.alphavantage.co/documentation/)
- **免费 25 请求/日、5/分**(已从早年 500/日降到 25/日,2026 确认)。**基本面端点 OVERVIEW / INCOME_STATEMENT / BALANCE_SHEET / CASH_FLOW / EARNINGS 免费可用**(每调用计入 25/日)。
- **覆盖** 美股为主 + 部分全球;**历史** ~5–20 年(确切未核实);**PIT** 重述、非 PIT(未核实)。**许可** 商用需 premium($49.99/月起)。
- 定位:25/日地板太低,**只够小批量点查/校验**,不适合全市场扫描。本仓库已登记(working-apis.md)。

### 3.7 Finnhub —— 免费 Basic Financials,as-reported 要付费
- **一手源(中,JS):** [Pricing](https://finnhub.io/pricing) · [Rate Limit](https://finnhub.io/docs/api/rate-limit) · [Financials As Reported](https://finnhub.io/docs/api/financials-reported)
- **免费 60/分**;免费含**美股** quote/news/**Basic Financials(关键比率)**/profile/SEC filing 搜索。**`financials-reported`(最接近 PIT 的原样申报)与完整标准化报表 = 付费;国际/详尽基本面 = 付费。**
- **许可** 免费=个人非商用;商用/重分发需付费档。本仓库 working-apis.md 标"免费 60/分,CORS OK",compliance.md 标"重分发权仅 Startup/Enterprise"。
- 定位:**免费基本面里 CORS 友好 + 限频宽松**的最佳之一,但只有 Basic Financials,**无 as-reported 报表**。

### 3.8 OpenBB Platform —— 开源聚合器(不持数据)
- **一手源(高):** [GitHub](https://github.com/OpenBB-finance/OpenBB) · [Providers](https://docs.openbb.co/odp/python/extensions/providers) · [Sunsetting Terminal](https://openbb.co/blog/sunsetting-openbb-terminal-why-how-and-what-now/)
- **本质=聚合/封装,自身不托管数据**(官方原话)。现名 **Open Data Platform (ODP)**。**免费基本面 provider:** 无 key—Yahoo、**SEC**、CBOE;免费需 key—FMP、Tiingo、Alpha Vantage、Polygon、FRED。→ 免费基本面实际靠 **SEC + Yahoo + FMP/Tiingo/AV 免费层** 实现。
- **2026 形态:** **OpenBB Terminal(旧)已于 2024-03 sunset** → 开源 **Platform + CLI**(AGPLv3,`pip install openbb`,最新稳定版 2026-04);**Workspace** = 企业 UI(原 Terminal Pro),**Workspace Pro 付费(席位制)**;**OpenBB Hub/Account 模块退役**。
- 定位:**统一适配层值得用**(一套接口接多源),但**许可与 PIT 仍随底层源**,聚合器本身不改变红线。

### 3.9 Norgate Data —— 价格+成分股无幸存者偏差,非基本面库
- **一手源(高):** [norgatedata.com](https://norgatedata.com) · [Pricing](https://norgatedata.com/pricing.php)
- **US + AU** 两个市场包;**主要是 价格(复权 OHLCV)+ 历史指数成分股 + 退市标记**,**不是财报/基本面数据库**。**无幸存者偏差**是核心卖点(含退市、历史成分时间线)。
- **PIT:** 成分股/退市=as-of 正确;价格为复权(非原始 print)。**价格:** 历史上 Platinum ~$70–80/月/市场;**2026 确切未核实**。**许可:** 个人单用户,不可重分发。
- 定位:**做美股/澳股回测的"无幸存者偏差价格+成分"底座**,与 EDGAR 基本面互补;**不解决基本面**。

### 3.10 Stockanalysis.com —— 显示级基本面,禁爬禁重分发
- **一手源(中):** [stockanalysis.com](https://stockanalysis.com) · [Pro](https://stockanalysis.com/pro/)
- 覆盖广(美股+大量国际),报表/比率干净;Pro ~10 年年报 + 季报。**无官方公开 API**(站内 JSON 为非官方,抓取不被许可)。**价格** 免费档 + Pro ~$10–15/月(未核实)。**ToS 禁爬、禁批量、禁重分发。**
- 定位:**人看的二次核对**好用;**不可程序化/重分发**;重述非 PIT。

### 3.11 Yahoo Finance / yfinance —— 快速原型,字段易碎、非商用
- **一手源(中):** [yfinance GitHub](https://github.com/ranaroussi/yfinance)(代码 Apache-2.0)· 数据源 finance.yahoo.com
- **基本面字段** `income_stmt`/`balance_sheet`/`cashflow`/`info`:**深度浅(~4 年年报 / 4–5 季)**、**重述非 PIT**、**易碎**(Yahoo 改端点/加 crumb-cookie/consent → 2025-2026 反复 429、`info` 返回空、解密变更,靠点版本被动修)。无官方 API/配额;重度使用触发 429 临时封 IP。
- **许可:** **代码 Apache-2.0,但数据受 Yahoo ToS 约束 = 个人非商用、禁重分发**。本仓库 compliance.md 标"重分发风险最高"。
- 定位:**快速原型 + 非美兜底**;**绝不作 PIT 回测/对外商用的依据**。

### 3.12 分析师预期 / 盈利修正 —— 稀缺性诚实评估
**结论:不存在真·免费、真·PIT 的 consensus/revisions 源。** PIT 预期(知道历史某日 Street 的预期 + 修正史)是**许可门控的付费产品**。
- **Yahoo(免费):** 有 `recommendations`/`analyst_price_targets`/`earnings_estimate`/`eps_trend` 等,但**仅当前快照、重述、无 PIT 历史、浅、易碎、非商用**。可读"当前大致 consensus",**无法做修正回测**。可信度**低**。
- **Finnhub** 估计/修正端点 = **付费**;**Zacks**(Zacks Rank 修正鼻祖)= 付费;**TipRanks/Koyfin** = 付费(仅查看,无重分发);**Nasdaq 站** 系统化估计 = 付费。
- **付费 PIT consensus 全集(均企业定价、无免费层):** LSEG/Refinitiv **I/B/E/S**、**FactSet**、**Visible Alpha**、**S&P Capital IQ**、**Zacks**、**Bloomberg BEst**。
- 落地:**修正因子要么放弃,要么预算一个付费 vendor**;不要用 Yahoo 快照伪造"历史 consensus"(前视偏差)。

### 3.13 AkShare / Tushare —— A股/港/美 国际兜底
- **AkShare(中):** [GitHub](https://github.com/akfamily/akshare)(代码 **MIT**)· [docs](https://akshare.akfamily.xyz)。覆盖**广**(A股/港/美+期货基金宏观),A股基本面来自**爬取**东财/新浪/同花顺等。**重述非 PIT**;**免费无 key**;**易碎、墙外易被限频/封 IP**;**数据许可灰色(随被爬站点 ToS)**,**不可商用重分发**。本仓库 compliance.md 已标"法律灰色,易封 IP"。
- **Tushare(中-高):** [tushare.pro](https://tushare.pro) · [docs](https://tushare.pro/document/2)。A股核心更结构化、更稳(官方 API 非爬)。**积分制**:免费注册积分低 → 端点/调用受限,积分越高每分钟限越宽;高价值端点需高积分(贡献或**付费会员 ~¥200+/年**)。报表带 **`ann_date`/`f_ann_date`/`end_date`** → **可近似 PIT 申报时点**(本组里最接近 PIT),但 vendor 级修正 vintage **未核实**。**服务器在中国,墙外慢/可能受限**;**个人/研究,不含重分发**。
- 定位:**A股/港股基本面的现实免费选项**;Tushare 因 `ann_date` 优于 AkShare/Yahoo 用于近似 PIT;**均仅内部用**。

---

## 4) PIT 与许可红线

**PIT 红线**
- **真·PIT(免费)只有一条路:EDGAR 季度 Financial Statement Data Sets / 自解析 filing + filing-date vintage。** EDGAR 的 companyfacts/frames JSON **不是** as-originally-filed(会被修正覆盖)—— 直接拿来回测 = **悄悄引入前视/重述偏差**。
- **真·PIT(付费)开箱:Sharadar SF1 的 AR 维度**。预算允许时优先,省自建 vintage 的工程量。
- **其余免费源(SimFin/FMP/Tiingo/AV/Finnhub Basic/Yahoo/Stockanalysis/AkShare)默认是重述(latest-only)**,**不可直接用于 PIT 因子**。Tushare 的 `ann_date` 仅"近似"。
- **预期数据 PIT 几乎不可免费获得** —— 用 Yahoo 快照当历史 consensus = 严重前视偏差,**禁止**。

**许可红线(对齐 `compliance.md`)**
- **唯一可对外重分发/商用的免费基本面 = SEC EDGAR(公有领域)。**
- yfinance/Yahoo、AkShare(爬取)、Stockanalysis、FMP/Tiingo/AV/Finnhub 免费档:**禁止商用/重分发**,仅内部计算/缓存/原型。
- 付费源(Sharadar/SimFin/Norgate)标准订阅**通常不含重分发**;对外展示需单独 Display/Enterprise 协议。
- **工程化:** 数据源适配器层带 `commercial_redistribution: bool` 与 `pit_grade: {true_pit | approx | restated}` 两个标志;**对外接口默认只暴露 `commercial_redistribution=true`(即 EDGAR);PIT 因子回测只允许 `pit_grade=true_pit` 的源。**

---

## 5) 落地到本系统(优先级:EDGAR 为主 + 谁兜底)

本仓库现状(见 working-apis.md):已接 **SEC EDGAR XBRL companyconcept**(`frontend/lib/fundamentals.ts`),已验证 **Finnhub / AlphaVantage** 免费,Yahoo 经代理,A股有 Sina/Tencent(行情),Tushare/AkShare 在升级路径。建议:

| 层级 | 用途 | 选型 | 理由 |
|---|---|---|---|
| **P0 基本面底座(美股,PIT)** | 长期因子、估值、质量 | **SEC EDGAR + 自建 filing-date vintage**(落地 FSDS 季度集) | 唯一免费·PIT·可重分发;对外看板可直接用 |
| **P0 工程** | EDGAR JSON ≠ PIT 的修正 | **离线跑 FSDS/companyfacts.zip 建 PIT 快照表**,而非直接信 frames | 防止悄悄前视偏差(§4) |
| **P1 PIT 兜底/校验(有预算)** | 交叉验 EDGAR、补 AR 维度 | **Sharadar SF1**(~$30/月个人,未核实) | 开箱 AR-PIT,工程省;无幸存者偏差 |
| **P1 聚合适配层** | 统一多源接口 | **OpenBB Platform(AGPLv3)** | 一套接口接 SEC+Yahoo+FMP/AV;但许可/PIT 仍随源 |
| **P2 美股快速点查/补洞** | 当前值、比率、原型 | **Finnhub Basic Financials(60/分)> AV(25/日)** | 仅内部;非 PIT;Finnhub 限频更宽 |
| **P2 非美 / A股 / 港股** | 国际基本面 | **Tushare(`ann_date` 近似 PIT)> AkShare** | 仅内部;墙外慢;非商用 |
| **P3 显示级二次核对** | 人工复核 | **Stockanalysis.com**(人看)+ yfinance(原型) | 禁程序化/重分发;易碎 |
| **预期/修正** | forward EPS、修正因子 | **默认放弃免费;要做就预算 I/B/E/S/FactSet/Zacks** | 无真·免费·PIT consensus(§3.12) |
| **价格无幸存者偏差(美/澳)** | 回测 universe | **Norgate**($,可选) | 价格+成分,非基本面,与 EDGAR 互补 |

**取舍要点**
- **对外看板**:基本面只暴露 EDGAR(合规);其余源标"内部/缓存"。
- **回测**:只准 `true_pit` 源(EDGAR-vintage 或 Sharadar)。Yahoo/SimFin/FMP 的重述值进回测会高估因子(survivorship + look-ahead)。
- **成本上限**:零预算 → EDGAR + Finnhub + Tushare 即可覆盖"美股 PIT + 美股点查 + A股";加 ~$30/月 → Sharadar 让 PIT 工程量骤降。

**EDGAR 真·PIT 落地配方(可直接照做)**
1. **拉数据**:夜间下载 `companyfacts.zip`(全公司 facts)+ 季度 **Financial Statement Data Sets**(`num.txt`/`sub.txt`/`tag.txt`),后者每季冻结 = 天然 vintage。优先 FSDS 而非逐 CIK 调 JSON。
2. **建 vintage 表**:对每条 fact 记 `(cik, tag, period_end, value, filed_date, form, adsh)`;**以 `filed_date` 为 PIT 锚** —— 因子在日期 `t` 只能看到 `filed_date <= t` 的最新一条;同一 `period_end` 的后续 amendment 作为**新 vintage 行**追加,不覆盖。
3. **修正处理**:保留 original 与每次 restatement 两条,因子默认用"截至 t 已申报"的值;研究 restatement 信号时再对比 vintage。
4. **对齐脏活**:custom extension tag 映射到标准概念(自建 tag→concept 字典);单位(`us-gaap` unit)与 quarterly/TTM 口径统一。
5. **校验**:抽样用 Sharadar AR 维度或 10-K 原文交叉核对 N 家公司,锁定解析误差后再上回测。
6. **限频礼仪**:批量走 ZIP;API 仅做增量,严格 ≤10 req/s + 带 `User-Agent: <app> <email>`,否则 403/429。

**逐源"内部 vs 对外"落地标志(适配器层填 `commercial_redistribution` / `pit_grade`)**

| 源 | `commercial_redistribution` | `pit_grade` | 系统内角色 |
|---|:--:|:--:|---|
| SEC EDGAR | `true` | `true_pit`(走 FSDS vintage) | 对外看板 + 回测底座 |
| Sharadar SF1 | `false`(需单独协议) | `true_pit` | 内部回测校验 |
| SimFin | `false` | `restated`(PIT 未核实) | 内部补洞 |
| FMP / Tiingo / AV | `false` | `restated` | 内部点查/原型 |
| Finnhub Basic | `false` | `restated` | 内部点查(限频宽) |
| Yahoo / yfinance | `false` | `restated` | 原型/非美兜底 |
| AkShare / Tushare | `false` | `restated` / `approx`(Tushare `ann_date`) | 内部 A股/港股 |
| Norgate | `false` | 成分=`true_pit`;基本面=n/a | 内部回测 universe(价格) |

---

## 6) 反方 / 局限

- **"EDGAR 就够了"过于乐观**:XBRL 自定义扩展标签使跨公司对齐脏活很多;2009 前无结构化数据;仅美股;自建 PIT vintage 是**真实工程成本**(解析 FSDS、处理 amendment/dimension)。Sharadar 之所以值钱正是因为它替你做了这些。
- **本调研多个一手页 JS 渲染/登录墙**(FMP 403、Tiingo/Finnhub 仅摘要、Sharadar/Nasdaq 价格登录墙)→ 这些源的**价格/免费额度可信度仅"中"**,落地前需在各自 pricing 页**当场复核**(已标 **未核实**项尤甚)。
- **免费层是移动靶**:AV 已从 500/日 → 25/日;免费基本面历史上多次被收紧。**不要把生产管线绑死在单一免费层**;EDGAR(公有领域)是唯一无此风险的。
- **预期数据的悲观结论可能让人想"凑合用 Yahoo"** —— 但 Yahoo 预期无 PIT 历史,**任何用它回测修正因子的尝试都是前视偏差**;诚实的做法是**承认这是付费缺口**,而非自欺。
- **SimFin 的 PIT 未核实**:若它实际非 PIT 却被当 PIT 用,会污染回测;在证实前**按重述对待**。
- **Sharadar 2026 价 / 起始年(1990 vs 1998)未核实**:订阅前需 NDL 登录确认。
- **AkShare/Tushare 数据许可**:即便"内部用",爬取/积分源的合规边界在不同法域不同;A股数据出境另有限制(见 compliance.md §3)。

---

## 7) 参考来源(URL + 可信度)

**一手 · 高**
- SEC EDGAR APIs — https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC Accessing EDGAR Data(限频/User-Agent/公有领域)— https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC Financial Statement Data Sets(季度 PIT vintage)— https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets
- Alpha Vantage Premium(免费 25/日)— https://www.alphavantage.co/premium/
- Alpha Vantage Documentation(基本面端点)— https://www.alphavantage.co/documentation/
- FMP Terms of Service(免费=非商用,禁重分发)— https://site.financialmodelingprep.com/terms-of-service
- SimFin Pricing($0/15/35/71)— https://www.simfin.com/en/prices/
- OpenBB GitHub / Providers / Sunsetting Terminal — https://github.com/OpenBB-finance/OpenBB · https://docs.openbb.co/odp/python/extensions/providers · https://openbb.co/blog/sunsetting-openbb-terminal-why-how-and-what-now/
- Sharadar SF1(NDL)/ Sharadar 官网 — https://data.nasdaq.com/databases/SF1 · https://www.sharadar.com/
- Norgate Data / Pricing — https://norgatedata.com · https://norgatedata.com/pricing.php
- yfinance GitHub(Apache-2.0 代码 / Yahoo ToS 数据)— https://github.com/ranaroussi/yfinance
- AkShare GitHub(MIT)— https://github.com/akfamily/akshare
- Tushare 文档 — https://tushare.pro/document/2

**一手页(JS/登录墙,仅摘要)· 中**
- FMP Pricing(403/JS)— https://site.financialmodelingprep.com/developer/docs/pricing
- Tiingo Pricing / Fundamentals Docs — https://www.tiingo.com/pricing · https://www.tiingo.com/documentation/fundamentals
- Finnhub Pricing / Rate Limit / Financials As Reported — https://finnhub.io/pricing · https://finnhub.io/docs/api/rate-limit · https://finnhub.io/docs/api/financials-reported
- Stockanalysis.com / Pro — https://stockanalysis.com · https://stockanalysis.com/pro/

**第三方近期(2026)互证 · 中**
- SEC EDGAR API Rate Limits & Best Practices(2026)— https://tldrfiling.com/blog/sec-edgar-api-rate-limits-best-practices
- EDGAR 10 req/s Fair Access 解析 — https://dealcharts.org/blog/edgar-scraping-rate-limits-explained
- QuantRocket Sharadar 文档 — https://www.quantrocket.com/sharadar/

**本仓库内部交叉引用**
- 数据重分发红线 — [`../../docs/compliance.md`](../../docs/compliance.md)
- 实测可用 API(2026-06)— [`../../docs/working-apis.md`](../../docs/working-apis.md)

---

> **未核实清单(落地前必复核):** FMP 是否新关基本面付费墙;FMP/AV 免费基本面历史深度精确值;Tiingo/SimFin 基本面 PIT 状态;Sharadar SF1 的 2026 确切价与起始年(1990 vs 1998);Norgate 2026 价;Tushare 2026 积分阈值/会员价;Stockanalysis Pro 精确价。
