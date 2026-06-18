# 内部人交易(Form 4)与机构持仓(13F)作为长期信号 — 深度研究报告

> 目的:为本系统**长期(数月至数年)做多**方向,评估"内部人买入"与"超级投资者 13F 跟单"是否构成可落地的**净·扣成本**信号,并给出免费 PIT 获取与验证方案。
> 方法:多角度并行检索(Lakonishok-Lee / Cohen-Malloy-Pomorski / copycat 文献 / EDGAR 端点 / 聚合器)→ 一手来源 + 可信度(高/中/低)→ 合成。
> 日期:2026-06-18。
> 立场(房子风格):**净·扣成本是唯一货币;明确标注前视/幸存者偏差;凡 1970s-2000s 样本默认其近 10 年 alpha 已被套利吃掉,除非用 2013-2025 扣成本数据复证。** 核心结论:**多数跟单在扣 45 天披露滞后后 alpha 微弱;价值在于作为"质量/价值候选的二次确认",而非独立 alpha 源。**

---

## 1. TL;DR(可证伪要点)

1. **内部人"买入"有信息,"卖出"基本无信息。** 卖出动机噪声极大(分散、税务、流动性、10b5-1 计划),买入是自掏腰包的主动行为。Lakonishok-Lee(RFS 2001)、后续多源一致(高可信度)。→ 信号侧**只用买入**。

2. **"常规买入"弱、"机会型/集群买入"较强 —— 这是本主题最稳健的结论。** Cohen-Malloy-Pomorski《Decoding Inside Information》(JF 2012):剔除可预测的"常规"交易,**机会型内部人组合价值加权异常收益 82 bps/月(≈10%/年)**,而**常规交易者异常收益≈0**(高可信度,1986-2007 样本)[CMP 2012]。→ 区分"常规 vs 机会型"是把噪声变信号的关键。

3. **开放市场买入(Form 4 交易码 P)是唯一无歧义的看涨信号;期权行权(M)、授予(A)、税务扣股(F)都是噪声。** 区分交易码是把 Form 4 变成可用信号的第一步(高可信度,定义性)[13Finsight; SEC ownership XML spec]。→ 解析时**只保留 code=P 且 acquired/disposed=A**。

4. **集群买入(多名内部人短窗内同时买)显著放大信号。** 多源:集群买入历史上预示 6-12 个月 **4-8% 异常收益**;Lakonishok-Lee 记重度内部人买入股 12 个月平均超额 **~4.8%**(中可信度,口径不一,多为毛收益、偏小盘)[heygotrade; KEDM; LL 2001]。→ **集群 + 高管(CEO/CFO)+ 自有资金规模相对身家大** 是最强子集。

5. **13F 跟单(cloning)的净 alpha 在扣 45 天滞后后微弱,且高度集中于少数长持有期、高信念经理。** 同行评审共识(Frank-McNichols 2004;Verbeek-Wang 2013):**跟单 ≈ 扣掉被跟基金自身费用后打平**——你赚的"alpha"主要是**省掉的管理费,而非新 edge**;跑赢大盘**净收益未被稳健确立**(高可信度)[Frank 2004; Verbeek-Wang 2013]。

6. **滞后衰减是真实且可量化的。** "最佳点子"增量 alpha 起步约 **36 bps/首月,约 4 个月半衰期**;季度持仓被读到时平均已"陈旧"~3+ 个月,**约 1/3 到 1/2 的原始增量 alpha 已流失**(中可信度,精确半衰期未核实)[Quantpedia]。→ **只有真正 5 年+ 长持有期经理的仓位,滞后才"无所谓";churn 高的量化/对冲快仓跟单几乎无价值。**

7. **大幅跑赢的跟单数字(年化 +20~24%、Sharpe 1.8)全部来自非同行评审、易前视的回测,应重折。** 这些数字依赖**事后挑"top quartile/对的经理"**(教科书级前视/幸存者偏差),且多为毛收益(低可信度)[Schroeder 2024; olympus-trade]。→ 不作为系统决策依据。

8. **13F 的结构性盲点决定它只能当二次确认:** 无空头、无现金/债券/非美/衍生品、季度快照看不到盘中进出、"超级投资者"名单事后幸存者偏差。把对冲掉的多头当净多头跟,等于继承经理已对冲掉的 beta(高可信度,结构事实)。→ **本系统定位:13F/Form4 = 已通过价值/质量初筛候选的二次确认信号,非独立选股 alpha。**

---

## 2. 内部人 / 13F 信号定义

### 2.1 Form 4(内部人 = 董事、高管、≥10% 持有人)
- **谁报:** 受益所有权变动须在交易后 **2 个工作日内**报 Form 4(Form 3=初始,Form 5=年度补报)。比 13F 及时得多。
- **交易码(transactionCode)—— 信号 vs 噪声**(来源:SEC ownership XML 规范;13Finsight):

| 码 | 含义 | 信号 |
|----|------|------|
| **P** | 开放市场/私下**买入**(自有资金) | **最强看涨**,保留 |
| S | 开放市场**卖出** | 弱信号(动机噪声大) |
| A | 来自发行人的授予/奖励(薪酬) | 噪声 |
| M | 衍生品/期权**行权**转换 | 噪声(机械) |
| F | 以股抵缴行权价/税 | 噪声(机械) |
| G | 赠与 / C 转换 / X 行权 / J 其他 | 噪声(读脚注) |

- **"常规 vs 机会型"分类法(CMP 2012,可落地):** 若某内部人在**过去若干年的同一日历月**反复交易 → 标为**常规**(无信息);否则**机会型**(承载全部预测力)。→ 本系统可对每个 reportingOwner 维护历史交易月份分布,打"常规度"标签。具体操作口径(CMP 原文精神,本系统建议):对某 owner,看其过去 3 年的买入是否落在**可被预测的同一日历月**(如每年 12 月行权后例行加仓)——能预测 = 常规;落点散乱 = 机会型。机会型且为 code=P 的买入才计入信号。
- **集群买入定义(业界惯例):** 同一标的 **7-14 天内 ≥2(或 ≥3)名不同内部人** 的开放市场买入(P);叠加高管职级、交易额相对身家、价格簇拥度。本系统建议默认参数:**窗口 14 天、≥2 名去重 owner、含 ≥1 名 officer/CEO/CFO、合计金额 ≥ $100k 且非纯象征**(避免 1 股摆拍)。
- **信号强度排序(自最强至最弱,供置信加权):** ① 机会型 + 集群 + 含高管 + 大额 P 买入 → 最强;② 单一高管大额机会型 P 买入 → 较强;③ 普通董事单笔小额 P → 弱;④ 纯 A/M/F/G、常规交易者、任何卖出 → 不计入(或仅作风险旗标)。

### 2.2 13F-HR(机构投资经理,管理 ≥$1 亿美股)
- 季度披露,**季末后最多 45 天**;仅美股多头与期权,**不含空头/现金/非美/债券**;按 CUSIP 报,无 ticker(本系统已在 `funds_13f.py` 注释中正确标注此限制)。
- **可用子信号:** ① "最佳点子"= 经理最大权重仓(Cohen-Polk-Silli:best ideas 比组合其余高 ~2.8-4.5%/年,但**这是报告日口径、毛收益,非扣 45 天滞后**);② **共识/多机构增持**(多个选定经理同时持同一名);③ 高信念(仓位权重大、连续多季加仓)。

### 2.3 Form 4 vs 13F —— 信号特性对照(决定用法)

| 维度 | Form 4(内部人) | 13F(机构) |
|------|------------------|------------|
| 申报滞后 | 交易后 **2 个工作日** | 季末后**最多 45 天**(实际位置平均陈旧 ~3 个月) |
| 信息源 | 公司内部人(信息优势最大) | 外部机构(信息优势较小) |
| 标的标识 | 含 ticker(友好) | 仅 CUSIP/名称(需映射) |
| 信号方向 | 买入有信息、卖出弱 | 增持/best idea 有信息、整体组合弱 |
| 容量 | 偏小盘、低容量 | 偏大中盘、容量较高 |
| 盲点 | 仅个人持仓变动 | 无空头/现金/非美/盘中进出 |
| 最佳用法 | 集群 + 机会型 + 高管的**二次确认** | 长持有期经理共识的**二次确认** |

→ **两者互补:Form 4 更及时、信息含量更高但容量小;13F 更滞后但覆盖大票。本系统两路并取交集时置信最高。**

---

## 3. 净 alpha 证据与滞后衰减(按可信度)

### 3.1 内部人买入
- **Lakonishok & Lee,《Are Insider Trades Informative?》(RFS 2001):** 聚合内部人交易可预测市场;**买入比卖出更有信息**;效应**集中在小公司**;**累计买入 > 单笔**。重度内部人买入股 12 个月平均超额 ~4.8%(中-高可信度;一手 SSRN 页面 403 未能直接读全文,数字来自二手综述,**精确数字未核实**)[SSRN 253079 abstract]。
- **Cohen-Malloy-Pomorski,《Decoding Inside Information》(JF 2012):** 机会型组合 **82 bps/月(价值加权)/180 bps/月(等权)≈10%/年**;常规交易者 ≈0;机会型内部人**预测未来公司新闻、盈利与管理层指引**(高可信度,1986-2007)[CMP, Harvard CorpGov; NBER w16454]。
- **诚实折扣:** 上述多为**毛收益、偏小盘、容量有限**;2012 后该信号被广泛商品化(openinsider 等),近年实盘 alpha 应假设已被压缩。小盘集群买入的近期再现(如某些 2024-2026 二手回测称 12 个月 ~7.4% 异常收益)**未经同行评审,未核实**。

**为什么内部人买入优先于 13F 跟单(机制):** ① 内部人有**最大信息优势**且**自掏腰包**(委托代理成本最低);② 滞后仅 2 天 vs 45 天;③ 学术效应(CMP 82bps/月)远大于跟单净 alpha(~省费打平)。代价是容量小、偏小盘。→ 两者间**内部人集群买入是更优先的确认信号**,13F 共识为补充。

### 3.2 13F 跟单 —— 净 alpha 与滞后
- **Frank, McNichols, Bhattacharya & Stanford,《Copycat Funds》(J. Law & Economics 2004):** 主动基金**费前**高于 copycat,但**费后两者统计上无法区分**——跟单的价值**主要是省费,非新 alpha**;未确立扣成本跑赢大盘。样本窄(1990s 高费基金)(高可信度,同行评审)[uchicago DOI 10.1086/422982]。
- **Verbeek & Wang,《Better than the Original?》(J. Banking & Finance 2013):** 扣披露滞后与交易成本后,copycat **平均比原基金高几个 bps**(即**净打平原基金费后**);**2004 起(共同基金强制季度披露)相对成功度上升**;但**跑赢基金宇宙的部分集中于"复制过去赢家/披露具代表性的基金"**(高可信度;**对象是共同基金,套用到 45 天 13F 超投是外推**)[SSRN 1566794]。
- **Angelini-Iqbal-Jivraj,《Systematic 13F Hedge Fund Alpha》(SSRN 3459526, 2019):** **在 13F 申报日(含 45 天滞后)再平衡**,选长持有期经理 + 信念(仓位权重)+ 共识(多经理同持),宣称 **年化跑赢标普 ~3.80%、Sharpe ~0.75(2004Q1-2019Q2)**。最可信的"扛过滞后"数字,但**依赖事后经理选择(前视风险)、似为毛收益、工作论文**(中可信度;净额与是否样本内选经理**未核实**)[SSRN 3459526; Lancaster FoFI PDF]。
- **滞后衰减量化:** 新披露最佳点子增量 alpha **~36 bps/首月,约 4 个月半衰期**;考虑季末 + 45 天 + 反应时间,有效陈旧 ~3+ 个月,**约 1/3-1/2 原始增量 alpha 在你能交易前已流失**(中可信度;**精确半衰期一手出处未核实**)[Quantpedia]。Hedge fund 披露/13F 申报与**基金业绩下滑相关**(滞后吃 alpha 的机制,JFE 2018,二手)[ScienceDirect S0304405X17301186,未直接读全文]。

### 3.3 大数字的反方
- **Schroeder(2024)称 top-quartile clone 年化风险调整跑赢标普 ~24.3%(15万组合,2013-2023):** 量级离谱、单作者非评审、"分 quartile"本身是前视/选择构造、扣成本与可交易性未核实(**低可信度**)[SSRN 5399672]。任何 ~20%+ 跟单宣传默认按"前视回测"折到接近 0。

---

## 4. 集群 / 确认用法(本系统主用法)

把内部人/13F 当**过滤与确认层**,叠在价值/质量初筛之上,而非独立打分:

1. **集群买入二次确认(最强子集):** 候选股若近 90 天出现 **≥2-3 名不同内部人 code=P 开放市场买入、含 ≥1 名高管(CEO/CFO)、合计金额非象征性** → 提升候选权重/置信标签。对应 Lakonishok-Lee 的"累计 > 单笔" + CMP 的"机会型"。
2. **剔除噪声:** 忽略纯 A/M/F/G;对反复同月交易的 owner 标"常规"降权。
3. **13F 共识确认:** 候选股若被**多个长持有期超级投资者**同时持有/加仓(共识),且为某经理**最大权重仓之一**(best idea)→ 二次确认。**不**因单一经理单季买入就建仓(滞后 + 盘中进出风险)。
4. **方向一致性:** 内部人买入 + 13F 增持 + 价值/质量初筛三者**同向**时,信号最可信;任一相反则降级。
5. **明确定位:** 这些信号**不产生独立 alpha 预期**;它们降低"价值陷阱/基本面恶化"误选概率(类似 F-Score 在便宜股池里的过滤角色)。把历史毛收益默认打 3-5 折后,作为**置信加权**而非收益预测。

### 4.1 组合决策逻辑(示意,本系统建议)

```
候选股已通过 价值/质量 初筛 → base_score
confirm_flags = {
  insider_cluster_opportunistic_buy : +强   # Form4: ≥2 owner, 14d, code=P, 机会型, 含高管, ≥$100k
  insider_single_exec_buy           : +中   # 单一高管大额机会型 P
  13f_longhorizon_consensus_bestidea: +中   # ≥N 名长持有期经理同持 且 属其权重前列
  direction_consistent              : +小   # 三者同向
}
reverse_flags = {
  exec_cluster_sell + 13f_big_trim  : 降级/剔除   # 强反向
}
final = base_score * (1 + clamp(Σ confirm − Σ reverse, 0, 0.20))
# 确认层加成封顶 ~20%,不允许由确认信号单独决定建仓
```

要点:① 确认是**乘性小幅加成**,不喧宾夺主;② **无信号 ≠ 负信号**(集群买入稀有,多数候选无信号属正常);③ 仅**强反向**才触发剔除;④ 全部以申报日对齐,杜绝前视。

---

## 5. 数据与可得性(免费 EDGAR Form4 / 13F 端点)

**通用约束(高可信度,SEC 官方):** 聚合 **≤10 请求/秒/IP**(超限 → HTTP 403 封 ~10 分钟,实操压到 ~8/s);**每请求必带声明式 User-Agent**(`"Name AdminContact@example.com"`);无 API key;大批量优先用 bulk flat files。

### 5.1 Form 4(内部人)
- **申报历史(每个 filer):** `https://data.sec.gov/submissions/CIK##########.json`(CIK **零填充 10 位**)。**Form 4 出现在此**;公司 CIK 与内部人本人 CIK 均可;过滤 `form=="4"`(及 3/5)。`filings.recent` 是**并列数组**(列式,同索引对齐):`accessionNumber/form/filingDate/reportDate/primaryDocument/...`。更早历史在 `filings.files` 列出的附加 JSON。
- **取文档(注意 CIK 填充差异):** data.sec.gov 用**填充** CIK;Archives 路径用**不填充** CIK:
  `https://www.sec.gov/Archives/edgar/data/{CIK_unpadded}/{ACCESSION_无横线}/{primaryDocument}`;目录清单 `.../{ACCESSION_无横线}/index.json`。解析**原始 XML**(非 XSL 渲染的 HTML)。
- **Form 4 XML(ownershipDocument 架构,解析字段清单):** 根 `<ownershipDocument>`。
  - 头部:`<issuer>`(`issuerCik` / `issuerName` / `issuerTradingSymbol` —— 直接给 ticker,比 13F 的 CUSIP 友好);`<reportingOwner>`(`reportingOwnerId/rptOwnerCik`、`reportingOwnerRelationship` 下 `isDirector` / `isOfficer` / `isTenPercentOwner` / `officerTitle` —— 用于判高管 + 集群去重)。
  - 非衍生交易:`<nonDerivativeTable>` → 0+ `<nonDerivativeTransaction>`:`<securityTitle><value>`;`<transactionDate><value>`;`<transactionCoding><transactionCode>`(P/S/A/M/F…);`<transactionAmounts>` 含 `<transactionShares><value>`、`<transactionPricePerShare><value>`、`<transactionAcquiredDisposedCode><value>`(A=获得 / D=处置);`<postTransactionAmounts><sharesOwnedFollowingTransaction>`(用于算 ΔOwn%);`<ownershipNature><directOrIndirectOwnership>`(D/I)。
  - 衍生交易:`<derivativeTable>` → `<derivativeTransaction>`(期权/RSU,含 `conversionOrExercisePrice` / `exerciseDate` / `underlyingSecurity`)—— **行权(M/X)落在此或对应非衍生行,本系统一律视为噪声丢弃。**
  - **解析规则(核心):保留 `transactionCode=='P'` 且 `transactionAcquiredDisposedCode=='A'` 的非衍生交易;其余全部丢弃。** 每件 Form 4 可含多行,逐行过滤后按 (issuer, owner, 日期) 聚合。
- **全文检索(发现用):** `https://efts.sec.gov/LATEST/search-index?q=...&forms=4&startdt=YYYY-MM-DD&enddt=YYYY-MM-DD`(仅索引 2001+);`ciks`/`entityName`/`size` 上限**未核实,需实测**。"列某公司/某人全部 Form 4" 用 submissions API 更可靠。
- **批量(回测/全市场):** **Insider Transactions Data Sets(Form 345)季度 TSV 压缩包**——`https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{YYYY}q{N}_form345.zip`(例 `2025q1_form345.zip`)。含 `SUBMISSION/REPORTINGOWNER/NONDERIV_TRANS(含 TRANS_CODE,TRANS_ACQUIRED_DISP_CD,TRANS_SHARES,TRANS_PRICEPERSHARE)/...`。**精确列拼写按 `insider_transactions_readme.pdf`(未核实,需对 readme 确认)。** 用它做全市场回测,请求量远小于逐件抓取。

**端到端取数配方(单标的 Form 4,纯标准库可实现):**
1. 由 ticker → issuer CIK(用 `https://www.sec.gov/files/company_tickers.json` 一次性映射,缓存)。
2. `GET https://data.sec.gov/submissions/CIK{10位填充}.json`,过滤 `form=="4"`,取近 N 天 `accessionNumber/primaryDocument`。
3. 对每件:`GET https://www.sec.gov/Archives/edgar/data/{CIK不填充}/{acc无横线}/{primaryDocument}` 取 XML;若 primaryDocument 非 xml,退回 `index.json` 找 `.xml`(类比现有 `funds_13f.py` 的 `info_table_url`)。
4. 解析 ownershipDocument,保留 `code=P & A/D=A`,聚合到标的级。
5. 全程带 `User-Agent`,sleep 限速 ≤8 req/s;失败指数退避。
**回测全市场时不要走步骤 2-3 逐件抓取**,改用 §5.1 的 Form 345 季度包一次性载入。

### 5.2 13F(机构)
- 用 submissions API 找 `13F-HR`(修正 `13F-HR/A`;`13F-NT`=通知无持仓)→ 取 information table XML。本系统 `scripts/funds_13f.py` 已正确实现此路径(submissions → index.json → infotable XML,命名空间 `…/thirteenf/informationtable`,字段 `nameOfIssuer/cusip/value/shrsOrPrnAmt/sshPrnamt/putCall`)。
- **注意 value 单位切换:** 2023 起 13F 以**整美元**申报,此前为**千美元** —— 跨期回测需归一化(中可信度,需对历史样本实测)。
- **批量:** 季度 13F 数据集 `…/form-13f-data-sets/{YYYY}q{N}_form13f.zip`(`INFOTABLE/COVERPAGE/...`;**确切 zip 名未核实,需实测**)。

### 5.3 免费聚合器(便利,但作辅助,凡 load-bearing 必回 EDGAR 核对)
- **openinsider.com:** 免费、近实时、爬 Form 4。screener URL 参数:`s`=ticker、`o`=内部人名、`xp=1`(含买入)、`xs=1`(含卖出)、`fd`=申报日窗口天数(或 `fd=-1`+`fdr={start}+-+{end}`)、`vl/vh`=金额、角色旗标 `isceo/iscfo/isdirector=1`、`cnt` 行数、CSV 下载链接。**Latest Cluster Buys** 视图直接给集群。**警告:非官方、无 API 契约、HTML 脆弱、无 SLA。**
- **Dataroma:** 免费追 ~82 名"超级投资者"13F(人工核对 EDGAR,准确度高);并列出超投持仓内的内部人买入(≥$50k)。**警告:仅策展子集、无官方 API、ToS 限爬、无审计业绩记录。**
- **GuruFocus:** freemium,免费层浅;非可靠批量源。

---

## 6. 落地到本系统(确认信号 / feed / 脚本 / 验证)

**复用现有 `scripts/funds_13f.py` 的 SEC 抓取范式(纯标准库、UA、submissions→index→XML),新增内部人侧。**

1. **新增 `scripts/insiders_form4.py`(建议,纯标准库):**
   - 输入:本系统候选股的 issuer CIK 列表(或反向:扫 Form 345 季度包按 CUSIP/ticker 命中候选)。
   - 用 submissions API 拉 `form=="4"` → 解析 ownershipDocument XML → **只留 code=P & A/D=A**。
   - 输出每标的近 90 天:买入内部人数(去重)、是否含 CEO/CFO(用 `reportingOwnerRelationship`)、合计金额、是否构成集群(≥2-3 人 / 14 天)、各 owner "常规度"标签(历史同月交易频率)。
   - 写 `feed/insiders/<ticker>.json`,字段示例:
     ```json
     {
       "ticker": "US:XXXX", "issuer_cik": "0000000000",
       "window_days": 90, "asof": "2026-06-18",
       "cluster": true, "n_buyers": 3, "has_exec": true,
       "buyers": [{"name": "...", "title": "CEO", "code": "P",
                   "shares": 10000, "price": 12.3, "value": 123000,
                   "trade_date": "2026-05-30", "filed": "2026-06-01",
                   "opportunistic": true}],
       "total_value": 250000, "opportunistic_any": true,
       "source": "SEC Form 4 (ownershipDocument)"
     }
     ```
2. **回测/初始化用 Form 345 批量包**(`{YYYY}q{N}_form345.zip`)做全市场扫描,避免逐件请求触发限速;周更用 submissions API 增量。
3. **feed/看板:** 复用现有 funds feed 模式,新增"内部人确认"徽章:在候选股卡片上显示 `集群买入 ✓ / 高管买入 ✓ / 机会型 ✓`,以及 13F 共识(几位长持有期超投同持)。**仅作置信加权与排序提示,不触发自动建仓。**
4. **共识层:** 在 `funds_13f.py` 的多基金 JSON 上做交集,标出"≥N 名长持有期经理同持 + 属其 best idea(权重前列)"的标的,与内部人集群求交。
5. **置信加权打分(建议把信号叠加到初筛分,而非替代):** 候选股已通过价值/质量初筛得分 `base` 后,加一个**有上限的确认加成**(如 ≤ base 的 15-20%),例如:`confirm = w1·机会型集群P买入 + w2·含高管 + w3·13F长持有期共识(best idea) + w4·方向一致`。任一**强反向**(高管集中卖出 + 13F 大幅减持)触发降级或剔除。**确认层只调排序/置信,不产生独立收益预期。**
6. **PIT 验证(防过拟合,本系统纪律):**
   - **严格用申报日(filingDate)而非交易日/季末**对齐信号 → 内生 45 天 13F 滞后、2 天 Form 4 滞后,杜绝前视。事件研究的 t=0 必须是**你实际能读到该信息的日期**。
   - 对"集群买入确认是否提升候选股 6-12 个月净收益"做事件研究:对照组 = 同期通过初筛但无内部人确认的候选;扣交易成本/冲击,**Deflated Sharpe / CSCV-PBO / t>3** 复测;**历史毛收益默认打 3-5 折**作扣成本、扣再定价后预期。
   - 经理选择**不可事后挑**:跟单只用**先验可定义**规则(如"持有期中位数 >2 年"用滚动窗口实时估,而非事后知道谁赢);"长持有期经理"集合每季按当时可见数据重算。
   - **容量/小盘体检:** 因内部人 alpha 集中小盘,需报告确认子集的市值分布、平均成交额、估算冲击成本;若信号只在低流动性尾部成立,标注容量限制。
   - 报告**净·扣成本**对照 S&P500,标注样本期、容量、小盘暴露、是否仅在某子周期成立。

---

## 7. 风险与反方(诚实)

- **滞后吃 alpha:** 13F 45 天(+ 季末陈旧)使约 1/3-1/2 增量 alpha 在可交易前流失;Form 4 仅 2 天滞后,但 P 信号本身近年被商品化。
- **结构盲点(13F):** 无空头 → 把对冲掉的多头当净多头跟,继承不想要的 beta;无现金/非美/债券/衍生 → 跟到的是陈旧、片面、仅美股切片(如经理转向国际市场对你不可见);盘中进出不可见。
- **前视 / 幸存者偏差:** "超级投资者"名单事后策展;"top quartile/选对经理"回测是前视构造;blow-up 基金从聚合中消失,夸大跟单收益(Brown 1992 / Carpenter-Lynch 1999 机制)。
- **容量与小盘:** 内部人买入 alpha 集中于小公司,容量低、冲击成本高,难规模化。
- **内部人卖出几乎无信息**,不要据卖出做空。
- **聚合器不可靠:** openinsider/Dataroma 无 SLA、HTML 脆弱、无审计业绩;load-bearing 决策必回 EDGAR。
- **过拟合:** 这些公开信号被全网回测,极易过拟合历史窗口;无独立 OOS + 扣成本复证前,不计入收益预期。
- **10b5-1 与误读:** 部分卖出/甚至买入受预定 10b5-1 计划驱动,非即时信息;Form 4 不总能区分,降低单笔可读性 —— 集群与机会型过滤部分缓解。
- **稀有性与覆盖:** 集群机会型买入是稀有事件,多数候选股任一时点**无**确认信号;确认层只能"加分一小部分候选",不能覆盖全宇宙,避免把"无信号"误当"负信号"。
- **信号商品化:** openinsider/Dataroma 让该信号几乎零成本可得,意味着任何易得 alpha 已被部分套利;近年实盘预期应比 2012 前学术值更低。
- **诚实底线:** 同行评审共识是"跟单 ≈ 省费打平",**不是**独立 alpha。本系统据此把它定位为**二次确认**,符合证据。

---

## 8. 参考来源(URL + 可信度)

**内部人交易(学术,高可信度):**
- Lakonishok & Lee,《Are Insider Trades Informative?》(RFS 2001):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=253079 (高;**一手 403 未直接读全文,数字经二手核**)
- Cohen, Malloy & Pomorski,《Decoding Inside Information》(JF 2012):https://corpgov.law.harvard.edu/2012/02/03/decoding-inside-information/ ;NBER w16454:https://www.nber.org/system/files/working_papers/w16454/w16454.pdf (高)
- AQR 版:https://www.aqr.com/Insights/Research/Journal-Article/Decoding-Inside-Information (高)

**Form 4 交易码与集群(中可信度,定义/业界):**
- 13Finsight 交易码:https://13finsight.com/learn/how-to-read-form-4-transaction-codes-insider-trading (中,定义)
- KEDM 集群买入定义:https://kedm.com/services/cluster-insider-buys/ (中)
- heygotrade 集群/C-suite:https://www.heygotrade.com/en/blog/insider-buying-signals-should-you-follow-the-c-suite/ (中)
- 小盘集群 7.4% 异常收益(二手,**未核实**):https://quantdecoded.com/en/insider-trading-signals-informative-trades (低)

**13F 跟单(学术,高/中可信度):**
- Frank, McNichols et al.,《Copycat Funds》(J. Law & Econ 2004):https://www.journals.uchicago.edu/doi/abs/10.1086/422982 (高)
- Verbeek & Wang,《Better than the Original?》(JBF 2013):https://www.ssrn.com/abstract=1566794 (高;**对象为共同基金,套用 13F 系外推**)
- Cohen, Polk, Silli,《Best Ideas》:https://personal.lse.ac.uk/polk/research/bestideas.pdf (高;**alpha 为报告日/毛收益**)
- Angelini, Iqbal & Jivraj,《Systematic 13F Hedge Fund Alpha》(SSRN 3459526, 2019):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3459526 ;Lancaster PDF:http://wp.lancs.ac.uk/fofi2020/files/2020/04/FoFI-2020-090-Farouk-Jivraj.pdf (中;**净额/样本内选经理未核实**)
- 披露与基金业绩下滑(JFE 2018):https://www.sciencedirect.com/science/article/abs/pii/S0304405X17301186 (中-高;**403 未直接读全文**)

**滞后衰减与反方:**
- Quantpedia,《Alpha Cloning - Following 13F Filings》(36bps/4 月半衰期、survivorship/backfill 警示):https://quantpedia.com/strategies/alpha-cloning-following-13f-fillings (中;**精确半衰期一手出处未核实**)
- Schroeder(2024)~24% 跟单(**低,前视嫌疑**):https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5399672 (低)

**EDGAR 端点与数据集(高可信度,SEC 官方):**
- SEC EDGAR APIs:https://www.sec.gov/search-filings/edgar-application-programming-interfaces (高)
- Accessing EDGAR Data(速率/UA):https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data (高)
- Ownership(Form 3/4/5)XML 规范:https://www.sec.gov/info/edgar/ownershipxmlspec-v1-r1.doc (高)
- Insider Transactions(Form 345)数据集公告:https://www.sec.gov/newsroom/whats-new/osd-announcement-081222-form-345-data-sets ;readme:https://www.sec.gov/files/insider_transactions_readme.pdf (高;**列拼写未核实**)
- data.gov 目录:https://catalog.data.gov/dataset/insider-transactions-data-sets (高)
- EFTS 全文检索 FAQ:https://www.sec.gov/edgar/search/efts-faq.html (高)
- Form 13F XML 技术规范 / 数据集:https://www.sec.gov/files/form_13f.pdf (高)

**免费聚合器(低-中,辅助):**
- openinsider screener:http://openinsider.com/screener ;Latest Cluster Buys:http://openinsider.com/latest-cluster-buys (低,非官方)
- 开源 openinsider 抓取器:https://github.com/sd3v/openinsiderData (低)
- Dataroma 经理列表:https://www.dataroma.com/m/managers.php (中,人工核 EDGAR;无审计业绩)
- GuruFocus gurus:https://www.gurufocus.com/guru/portfolio (低,freemium)

---

> **未核实清单(诚实标注):** Lakonishok-Lee 精确 4.8% 数字(一手 403);Angelini-Iqbal-Jivraj 净额与是否样本内选经理;Quantpedia 36bps/4 月半衰期的一手学术出处;openinsider EFTS `ciks/size` 上限;Form 345 / 13F 数据集确切 zip 文件名与 readme 列拼写;13F value 千美元↔整美元切换的历史样本处理;小盘集群 7.4% 二手数字。以上凡 load-bearing 须实测/读一手后再入模型。
