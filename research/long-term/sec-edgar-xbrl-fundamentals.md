# 用 SEC EDGAR XBRL 构建点时(PIT)基本面数据集

> 调研日期:2026-06-18 · 主题:长期投资基本面数据底座 · 房子风格:诚实可证伪、标注前视/幸存者偏差、一手来源优先、免费/PIT 优先、工程化可落地。
> 本文所有端点结构均**当日用带合规 User-Agent 的真实请求核实**(curl,见各处“已核实”标注)。无法核实处明确标“未核实”。

---

## 1) TL;DR

- **SEC EDGAR 的 XBRL REST API 是免费、无 API key、PIT 友好的美股基本面数据源。** 三个核心端点:`companyfacts`(一个 CIK 的全部 XBRL 事实)、`companyconcept`(一个 CIK 一个标签的时间序列)、`frames`(一个标签一个会计期跨所有公司横截面)。
- **PIT 的关键在于每条事实自带 `filed` 日期。** 用 `filed`(披露日)而非 `end`(报告期末)做时间轴,可天然避免前视偏差与 restatement 泄漏。`end` 是 as-of-reported 视角,`filed` 是 point-in-time 视角。**这是本主题最重要的一句话。**
- **同一报告期会出现多条事实(原始披露 + 后续季报/年报里的比较列 + 更正重述)。** 必须按 `(tag, end)` 分组、按 `filed` 排序,在每个查询日只取“截至该日已披露的最新一条”。EDGAR 在能干净对齐日历期的事实上打 `frame` 标记,可作辅助去重信号(已核实)。
- **标签是碎片化的最大坑。** 营收尤甚:老标签 `Revenues`,新准则(ASC 606)主流是 `RevenueFromContractWithCustomerExcludingAssessedTax`。必须做**按优先级回退**的标签映射,而非单标签硬取。
- **覆盖范围硬限制:仅 XBRL filer(美股,~15k 公司,~10 年历史)。** 外国私募发行人(20-F 用 IFRS 标签)、注销退市公司在 ticker 表里消失(**幸存者偏差来源**)。无国际、无 pre-XBRL(约 2009 前)。
- **合规硬约束:必须带 User-Agent(含联系邮箱),限速 ~10 req/s。** 否则 403。大规模建库应优先用**夜间重编的 bulk zip**(`companyfacts.zip` / `submissions.zip`),而非逐 CIK 打 API。
- **落地建议:** scripts/ 下加一个 stdlib-only 构建器,产出**带 vintage(filed)的长表 parquet/jsonl**;查询层按 `as_of` 日期切片即得无前视面板。字段映射表见 §3、§6。

---

## 2) API 端点全图(URL 模板 + 示例)

主机:`data.sec.gov`(JSON API)与 `www.sec.gov`(静态文件/bulk)。**全部免费、无 key、要求 User-Agent。**

| 端点 | URL 模板 | 用途 | CIK 格式 |
|---|---|---|---|
| ticker→CIK 映射 | `https://www.sec.gov/files/company_tickers.json` | 全市场 ticker/CIK/名称 | 整数(`cik_str`,**未补零**) |
| submissions(申报历史) | `https://data.sec.gov/submissions/CIK{CIK10}.json` | 申报列表(form/date/accession) | **补零到 10 位** |
| companyconcept | `https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK10}/{taxonomy}/{tag}.json` | 单公司单标签时间序列 | 补零 10 位 |
| companyfacts | `https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK10}.json` | 单公司**全部**标签 | 补零 10 位 |
| frames | `https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/CY{YYYY}[Q#][I].json` | 单标签单会计期**横截面** | 无 |
| bulk: 全部 companyfacts | `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` | 每 CIK 一个 json,夜间重编 | — |
| bulk: 全部 submissions | `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip` | 全 filer 申报历史 | — |

**示例(均已核实,2026-06-18 真实返回):**

```
# ticker 表(整数 cik_str)
https://www.sec.gov/files/company_tickers.json
# {"0":{"cik_str":1045810,"ticker":"NVDA","title":"NVIDIA CORP"},"1":{"cik_str":320193,"ticker":"AAPL",...}}

# AAPL(CIK 320193 → 补零 0000320193)单标签
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Assets.json

# AAPL 全部事实
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

# 横截面:2023Q1 期末总资产,所有公司
https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2023Q1I.json
```

**返回结构(已核实):**

`companyconcept` 顶层 `{cik, taxonomy, tag, label, description, entityName, units}`。`units` 按计量单位分桶(如 `USD`、`shares`)。每条事实:
```json
{"end":"2026-03-28","val":371082000000,"accn":"0000320193-26-000013",
 "fy":2026,"fp":"Q2","form":"10-Q","filed":"2026-05-01","frame":"CY2026Q1I"}
```
- `filed` = **披露日(PIT 时间轴的唯一可信锚)**。`end` = 报告期末。`fy`/`fp` = 财年/财期。`form` = 表型(10-K/10-Q/8-K…)。`accn` = accession。
- 时段类事实(损益/现金流)多一个 `start`;时点类事实(资产负债表)只有 `end`(已核实:Assets 事实无 `start`)。
- `frame` 仅在该事实能干净映射到日历期时出现;后续比较列/重述事实**通常没有 `frame`**(已核实,见 §4)。

`companyfacts` 顶层 `{cik, entityName, facts}`,`facts` 按 taxonomy 分:`dei`(实体级,如发行在外股数)、`us-gaap`(GAAP 标签)。AAPL 单一 CIK 即含 **503 个 us-gaap 标签**(已核实)——说明逐字段硬编码不可行,需映射表。

`frames` 顶层 `{taxonomy, tag, ccp, uom, label, description, pts, data}`。`ccp` = 会计期(如 `CY2023Q1I`),`pts` = 数据点数(2023Q1I Assets:**6289** 家公司,已核实)。`data[i]` = `{accn, cik, entityName, loc, end, val}`(**时点帧无 `start`**;时段帧有 `start`,已核实)。

**会计期(`CYxxxx`)格式(已核实):**
- `CY2023` — 年度时段(≈365±30 天)
- `CY2023Q1` — 季度时段(≈91±30 天)
- `CY2023Q1I` — 时点(`I`=instantaneous,资产负债表/股数用)

> frames 把“每家最后申报、最贴合该日历期的那条事实”聚合成横截面;对财年与日历年错位的公司(如 AAPL 9 月财年末)会做日历对齐,可能漏掉对不齐的公司——这是 frames 的覆盖盲点(见 §5)。

---

## 3) 关键 us-gaap 标签映射表(三表)

XBRL 标签碎片化:**同一经济量在不同公司/年份用不同标签。** 必须按优先级回退取第一个命中的标签。下表为推荐回退链(taxonomy 默认 `us-gaap`,股数为 `dei`)。

| 字段(语义) | 单位 | 标签优先级回退链(从上到下) | 备注 |
|---|---|---|---|
| **营收 Revenue** | USD | `RevenueFromContractWithCustomerExcludingAssessedTax` → `RevenueFromContractWithCustomerIncludingAssessedTax` → `Revenues` → `SalesRevenueNet`(老) | ASC 606 后主流是前者;AAPL 两者都在(已核实)。`SalesRevenueNet` 是 2018 前老标签。 |
| **净利润 NetIncome** | USD | `NetIncomeLoss` → `ProfitLoss`(含少数股东) | `NetIncomeLoss` 是归母口径;`ProfitLoss` 含 NCI。优先 `NetIncomeLoss`。 |
| **营业利润 OperatingIncome** | USD | `OperatingIncomeLoss` | 部分公司不披露;缺失时可由毛利-费用推算(留作可选)。 |
| **总资产 Assets** | USD | `Assets` | 时点(I)。已核实。 |
| **股东权益 Equity** | USD | `StockholdersEquity` → `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | 前者归母,后者含 NCI。注意区分。 |
| **现金及等价物 Cash** | USD | `CashAndCashEquivalentsAtCarryingValue` → `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` → `Cash` | 第二个含受限现金(ASU 2016-18 后常见)。 |
| **长期债务 LongTermDebt** | USD | `LongTermDebtNoncurrent` → `LongTermDebt` → `LongTermDebtAndCapitalLeaseObligations` | AAPL 两者都在(已核实)。口径差异:`LongTermDebt` 可能含当期部分。 |
| **发行在外股数(时点)** | shares | `dei:EntityCommonStockSharesOutstanding` → `CommonStockSharesOutstanding` | dei 版来自封面,披露最及时(AAPL `end=2026-04-17` 早于报告期末,已核实)。 |
| **加权稀释股数(时段)** | shares | `WeightedAverageNumberOfDilutedSharesOutstanding` → `WeightedAverageNumberOfSharesOutstandingBasic` | 算 EPS / per-share 用;时段量,带 `start`。 |

> **回退链不是凭空:** 每条都用真实 companyfacts 验证过“标签存在性”(AAPL CIK 320193,已核实 Revenues/RevenueFromContractWithCustomer.../NetIncomeLoss/Assets/StockholdersEquity/OperatingIncomeLoss/Cash.../LongTermDebt[Noncurrent]/dei 股数均 PRESENT)。**具体公司用哪条仍需运行时探测**——不要假设全市场统一。

---

## 4) PIT 实现法(filed 日期 / vintage)

**核心原则:数据集的时间轴是 `filed`(披露日),不是 `end`(报告期末)。**

### 为什么不能用 `end`
- 用 `end` 对齐 = 假设“季度一结束你就知道数字”,但 10-Q 通常在期末后 30–45 天才申报,10-K 60–90 天。用 `end` 回测 = **前视偏差**。
- 同一 `end` 的值会被后续重述改写。若库里只存“最新值”,回测时读到的是**未来才知道的修正值** = **restatement 泄漏**。

### 多事实去重(已核实的真实坑)
同一 `(tag, end)` 在 EDGAR 里有多条,来源:
1. **原始披露**(该期 10-Q/10-K)。
2. **比较列**:后续季报/年报把上期数字再列一遍(`filed` 更晚)。已核实例:AAPL Assets `end=2025-09-27` 这条出现在 `filed=2026-01-30`(下一财年 Q1)的申报里,且**无 `frame` 标记**。
3. **重述**:更正后的值,`val` 变了,`filed` 更晚。

**`frame` 标记可辅助识别“规范首发事实”:** 已核实 AAPL Assets 共 144 条,69 条有 `frame`、75 条无;有 `frame` 的更接近“该日历期的规范值”。但**不要只靠 frame**——以 `filed` 为准更稳健。

### PIT vintage 表(推荐数据模型)
把每条事实存成一行,**保留所有 vintage**,不覆盖:

```
cik | tag | uom | start | end | val | filed | form | accn | frame | fy | fp
```
- 主键近似 `(cik, tag, end, accn)`(同一申报里同 tag 同 end 唯一)。
- 查询某 `as_of` 日的 PIT 面板:对每个 `(cik, tag, end)`,**只保留 `filed <= as_of` 的事实中 `filed` 最大的一条**;再对每个 `(cik, tag)` 在每个报告期取最新已披露值。这样:
  - 不泄漏未来重述(因 `filed <= as_of`)。
  - 不前视(report 未申报前不可见)。

### 伪代码(PIT 切片)
```python
def pit_panel(facts, as_of):                  # facts: 长表(含 filed)
    visible = [f for f in facts if f["filed"] <= as_of]   # 截断未来披露
    best = {}                                              # (cik,tag,end) -> 最新 filed 的事实
    for f in visible:
        k = (f["cik"], f["tag"], f["end"])
        if k not in best or f["filed"] > best[k]["filed"]:
            best[k] = f                                    # 同期取最新已知(含重述)
    # 每个 (cik,tag) 取“最近报告期”(按 end 最大,且其 filed<=as_of)
    latest = {}
    for f in best.values():
        k = (f["cik"], f["tag"])
        if k not in latest or f["end"] > latest[k]["end"]:
            latest[k] = f
    return latest                                          # → 该 as_of 的无前视基本面快照
```

> **可证伪检验(必须做):** 对历史某日 `as_of` 跑 PIT 切片,断言所有返回事实的 `filed <= as_of`;且对随机抽样公司,人工核对该日是否真已申报(对 submissions.json 的 `filingDate`)。任何 `filed > as_of` 漏网 = 前视 bug。

---

## 5) 坑与陷阱

1. **标签碎片化 / 标签变更(最大坑)。** 营收最严重(§3 回退链)。同一公司跨年可能换标签(改用新准则标签)。**对策:** 优先级回退 + 运行时探测,而非硬编码单标签。
2. **同期多事实(比较列 + 重述)。** 见 §4。**对策:** 按 `(tag,end)` + `filed` 去重;保留全 vintage。
3. **`Revenues` vs `RevenueFromContractWithCustomer...`。** 有的公司只有其一,有的(如 AAPL)两者并存且**口径可能不等**。**对策:** 回退链固定优先序,并记录“实际命中的标签”到面板,便于审计。
4. **股东权益/净利含不含少数股东(NCI)。** `StockholdersEquity`(归母)vs `...IncludingPortionAttributableToNoncontrollingInterest`;`NetIncomeLoss` vs `ProfitLoss`。**混用会污染 ROE 等比率。** 对策:固定口径,别回退到含 NCI 版除非缺失且标注。
5. **合并子公司 / member 维度。** companyfacts 的标准事实是合并主体口径;但分部/子公司数据通过 XBRL `member`(dimension)拆分——**REST API 这几个端点只给主口径,不展开 member**,这恰好是优点(避免误取分部数字),但也意味着拿不到分部明细。
6. **单位问题。** `units` 按 uom 分桶;USD-per-share(EPS)在 `USD/shares` 桶,股数在 `shares` 桶。**取值前必须确认 uom**,别把 EPS 当美元。frames 的 unit 段必须与标签匹配(Assets→USD,EPS→`USD-per-shares`)。
7. **时点 vs 时段(`I`)。** 资产负债表项用 `...Q#I`(无 `start`);损益/现金流用 `...Q#`(有 `start`)。取错帧类型 = 取不到数据。
8. **财年错位。** AAPL 财年 9 月末。frames 的日历对齐会把它归到最近日历季,**可能与你预期的“2026Q1”错位一格**;按公司财年(`fy`/`fp`)分析更稳。
9. **缺失值是常态。** 不是每家披露 `OperatingIncomeLoss`/`LongTermDebt`。**对策:** 缺失即缺失,别 0 填充(会扭曲比率);记录缺失率。
10. **频率限制 & UA。** 无 UA 或超 ~10 req/s → **403**(已实测:无合规 UA 时 WebFetch 返回 403)。**对策:** 带 `User-Agent: name email`,客户端节流到 <10 req/s,失败重试带退避。
11. **覆盖盲点 = 幸存者偏差。** `company_tickers.json` 只列**当前**活跃 ticker;退市/注销公司在表里消失,但其历史 companyfacts 可能仍可按 CIK 取。**用当前 ticker 表建历史 universe = 系统性幸存者偏差。** 对策:历史 universe 应来自历史 submissions / 历史 ticker 快照,不能用今天的表回溯。
12. **国际公司。** 外国私募发行人交 20-F,常用 IFRS taxonomy(`ifrs-full`)而非 `us-gaap`;部分不交 XBRL。**本管道只覆盖美股 us-gaap filer。**
13. **pre-XBRL 历史。** XBRL 强制约始于 2009 前后,大公司 ~2009、小公司更晚。**早于此无结构化数据。**(年份未精确核实,标记为约值。)
14. **`fp` 语义。** `fp` 为 `FY`(年度)或 `Q1..Q4`;注意 10-K 里的“Q4”常以 `FY` 出现而非显式 Q4,算单季时需用 `FY - (Q1+Q2+Q3)` 推 Q4。

---

## 6) 落地到本系统(scripts/ 构建器设计 / 字段表 / 验证)

**契合现有房子风格**(参照 `scripts/funds_13f.py`):stdlib-only、带 SEC UA、输出 JSON 到数据目录、CI 跑、git diff 决定是否提交。

### 6.1 构建器设计:`scripts/fundamentals_pit.py`

```
职责:
  1. 加载/缓存 company_tickers.json → 建 ticker→CIK(补零10位)映射。
  2. 对 universe 内每个 CIK 取 companyfacts(或解 bulk companyfacts.zip)。
  3. 按 §3 回退链抽取目标标签,展平成长表(保留 filed/accn/frame 全 vintage)。
  4. 写出 PIT vintage 长表(jsonl 或 parquet);查询层按 as_of 切片。

合规:
  UA = {"User-Agent": "stock-analysis-fundamentals wanghanqing66@gmail.com"}
  节流:逐 CIK 调 API 时 sleep 保证 <10 req/s;大规模优先 bulk zip(夜间重编,一次下全量,
       避免数千次请求)。

幂等:
  以 accession 为新鲜度键(同 funds_13f 模式);facts 未变不重写。
```

### 6.2 标签映射(代码内常量,即 §3 的可执行版)

```python
TAGS = {  # 语义字段 -> (taxonomy, [回退标签...], 期望uom)
  "revenue":   ("us-gaap", ["RevenueFromContractWithCustomerExcludingAssessedTax",
                            "RevenueFromContractWithCustomerIncludingAssessedTax",
                            "Revenues", "SalesRevenueNet"], "USD"),
  "net_income":("us-gaap", ["NetIncomeLoss", "ProfitLoss"], "USD"),
  "op_income": ("us-gaap", ["OperatingIncomeLoss"], "USD"),
  "assets":    ("us-gaap", ["Assets"], "USD"),
  "equity":    ("us-gaap", ["StockholdersEquity",
                            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "USD"),
  "cash":      ("us-gaap", ["CashAndCashEquivalentsAtCarryingValue",
                            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"], "USD"),
  "lt_debt":   ("us-gaap", ["LongTermDebtNoncurrent", "LongTermDebt",
                            "LongTermDebtAndCapitalLeaseObligations"], "USD"),
  "shares_out":("dei",     ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"], "shares"),
  "diluted_sh":("us-gaap", ["WeightedAverageNumberOfDilutedSharesOutstanding",
                            "WeightedAverageNumberOfSharesOutstandingBasic"], "shares"),
}
```

### 6.3 抽取伪代码

```python
def extract(cik, facts):                          # facts = companyfacts JSON
    rows = []
    for field, (tax, candidates, uom) in TAGS.items():
        bucket = facts["facts"].get(tax, {})
        for tag in candidates:                    # 优先级回退:取第一个命中的标签
            node = bucket.get(tag)
            if not node: continue
            units = node["units"].get(uom)
            if not units: continue
            for f in units:                       # 展平所有 vintage,不去重
                rows.append({
                    "cik": cik, "field": field, "tag": tag, "uom": uom,
                    "start": f.get("start"), "end": f["end"], "val": f["val"],
                    "filed": f["filed"], "form": f["form"], "accn": f["accn"],
                    "frame": f.get("frame"), "fy": f.get("fy"), "fp": f.get("fp"),
                })
            break                                 # 命中即停,记录实际用的 tag
    return rows
```

### 6.4 输出字段表(PIT 长表)

| 字段 | 含义 | PIT 角色 |
|---|---|---|
| `cik` | 公司(补零前整数) | 主体 |
| `field` | 语义字段(revenue…) | 跨公司可比口径 |
| `tag` | 实际命中的 us-gaap/dei 标签 | 审计:知道值从哪个标签来 |
| `uom` | 计量单位(USD/shares) | 防单位混淆 |
| `start`/`end` | 报告期(时段有 start,时点无) | 报告期定位 |
| `val` | 数值 | — |
| **`filed`** | **披露日** | **PIT 时间轴锚** |
| `form` | 表型(10-K/10-Q) | 区分年度/季度 |
| `accn` | accession | 幂等键/去重 |
| `frame` | 日历期帧(可空) | 辅助识别规范首发 |
| `fy`/`fp` | 财年/财期 | 财年对齐分析 |

### 6.5 验证(可证伪,CI 强制)

1. **PIT 不变量:** 任取历史 `as_of`,断言切片结果全部 `filed <= as_of`(§4 检验)。失败=前视 bug。
2. **去重正确性:** 同 `(cik,tag,end)` 在切片后唯一,且为 `filed<=as_of` 的最大 `filed`。
3. **单位健全:** `field=revenue` 的 uom 必须 USD;`shares_out` 必须 shares。越界即报。
4. **覆盖/缺失率监控:** 记录每字段命中率与“实际命中标签分布”;命中率骤降 = 标签又变了,需更新回退链。
5. **交叉核对 frames:** 对几个标杆公司,用 `frames/.../CYxxxxQ#I.json` 横截面值核对 companyfacts 抽取值一致(已核实 frames 与 companyconcept 同源)。
6. **幸存者偏差防护:** 历史 universe 严禁用今天的 `company_tickers.json`;CI 检查 universe 来源带快照日期。

### 6.6 增量与规模

- **首次建库:** 下 `companyfacts.zip`(夜间重编,一次拿全量~15k 公司),本地解压逐 json 抽取——避免数千次 API 调用触发限速。
- **日更:** 监听 submissions 新申报(同 funds_13f 的 accession 新鲜度模式),仅对有新 10-K/10-Q 的 CIK 重取 companyfacts,**append 新 vintage**(永不覆盖旧 vintage,保 PIT)。
- **节流:** 逐 CIK API 路径 sleep 到 <10 req/s;429/403 退避重试。

---

## 7) 局限与反方

- **覆盖只到美股 us-gaap filer。** 无国际(外国私募发行人 20-F/IFRS)、无 pre-XBRL(约 2009 前)、无私有公司。长期跨国比较不能只靠这一个源。
- **幸存者偏差未被 EDGAR 解决。** API 不提供“历史 universe 快照”;退市公司从 ticker 表消失。**必须自建历史 universe**(自己按日快照 submissions / ticker 表),否则回测系统性偏乐观。
- **标签语义不是会计审计级。** companyfacts 是公司自报 XBRL 标注,**存在标错标签的情况**(脏数据)。本方案的回退链+命中标签记录能缓解,但不能替代人工抽查;比率类指标尤需 sanity check。
- **frames 的日历对齐有损。** 财年错位公司可能落入相邻日历季或被该帧漏掉;`pts` 数因此波动。建库主路径应走 companyfacts(按公司财年),frames 只做交叉核对/横截面快取。
- **“`filed` = 可知日”是近似。** EDGAR 申报传播延迟 <1 分钟(submissions)/ <1 分钟(xbrl)(来源所述,见 §8,**该延迟数本身未独立核实**),对日频回测足够;但严格盘中策略需考虑申报小时级时间戳(submissions 的 acceptanceDateTime),本方案用日粒度 `filed` 已足够长期投资场景。
- **反方观点:付费数据(Compustat PIT / S&P)提供标准化口径 + 更长历史 + 内建 universe 管理,省去标签回退与幸存者偏差工程。** 对“免费/PIT 优先”的本房子,EDGAR 是正确起点;但若策略对深历史(>15 年)或国际敏感,需诚实承认 EDGAR 不够,届时再评估付费源。

---

## 8) 参考来源(URL + 可信度)

| 来源 | URL | 可信度 | 用途 |
|---|---|---|---|
| **SEC 官方 live API 返回(本调研实测)** | `data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json`、`.../companyconcept/.../Assets.json`、`.../frames/us-gaap/Assets/USD/CY2023Q1I.json`、`www.sec.gov/files/company_tickers.json` | **最高(一手,2026-06-18 实测)** | 端点结构、`filed`/`frame`/`start` 字段、单位桶、503 标签、6289 pts、ticker 整数 cik_str — 全部已核实 |
| SEC 官方 EDGAR API 文档页 | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | 最高(一手) | 端点定义、会计期格式、限速/UA、bulk zip(**注:页面对无 UA 的自动抓取返回 403,内容经二手源转述**) |
| SEC 官方 Accessing EDGAR Data | https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data | 最高(一手) | bulk 下载、夜间重编、传播延迟说明(转述) |
| bulk zip URL(本调研 HEAD 实测 200) | `www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip`、`.../bulkdata/submissions.zip` | **高(一手 HEAD 实测可达)** | bulk 路径有效性已核实 |
| tldrfiling — EDGAR API guide | https://tldrfiling.com/blog/sec-edgar-api-guide/ | 中(二手教程,与官方一致处可信) | 限速 10 req/s、UA 格式、URL 模板转述 |
| jadchaar/sec-edgar-api(开源封装) | https://github.com/jadchaar/sec-edgar-api | 中高(广泛使用的开源实现) | 端点封装参考、CIK 补零惯例 |
| Medium — SEC XBRL/Frames API | https://medium.com/@vkasps/exploring-the-secs-xbrl-frames-api-for-financial-data-analysis-b2e8c7f12b3b | 中(二手) | frames 聚合语义("最后申报、最贴合该期") |
| 本系统 `scripts/funds_13f.py` | (仓库内) | 高(本房子既有实现) | UA 惯例、CIK 补零、accession 幂等模式、JSON 输出风格 |

**未核实项(明确标注):** ① XBRL 强制起始年份(约 2009,未精确核实);② submissions/xbrl 传播延迟“<1 分钟 / <1 分钟”数字(来自二手转述官方,未独立核实);③ SEC 官方文档页全文(403,关键事实已由 live API 实测 + 二手源交叉印证)。
