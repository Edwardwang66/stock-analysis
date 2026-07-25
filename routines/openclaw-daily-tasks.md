# OpenClaw 每日任务清单(Playbook)
> **Status:** Current
> **Scope:** External OpenClaw operator playbook; current authentication, schema, and failure authorities govern every task.
> **Last verified commit:** `a8d3d4c1a0ae707fca6c500f4de61a4bad0a8726`

> 这是给**你本地的外部 OpenClaw**(Claude agent)每天照着执行的任务清单。
> 仓库已铺好契约/投递/接收/展示;OpenClaw 负责**真分析**并把结果投递回来。
> 配套:[`openclaw-agent-prompts.md`](openclaw-agent-prompts.md)(量化 5 角色 prompt)、
> [`../docs/openclaw-stock-notes.md`](../docs/openclaw-stock-notes.md)(个股解读契约)。
> 铁律(R6):**LLM 是研究放大器,不决策;数值必须有来源;不编造;一律"非投资建议"。**
> 当前投递边界与失败语义见 [`../docs/openclaw-integration.md`](../docs/openclaw-integration.md) 和
> [`../docs/operations/workflows.md`](../docs/operations/workflows.md)。

---

## 0️⃣ 每次运行的第一步:读信箱(必做,2026-06-09 起)

- [ ] **先读 [`routines/winter-inbox.md`](winter-inbox.md)**:这是看板侧 Claude 给你的协调消息
  (口径变更/覆盖范围调整/新数据源)。把状态为 🆕 的条目执行掉,改成 ✅ 随当日投递一起 push。
- [ ] 投递前 `git pull --rebase origin main`,避免与看板侧/Actions 的 push 撞车。

## 0. 环境准备(一次性)
- [ ] clone 本仓到 OpenClaw workspace,`cd stock-analysis`
- [ ] 环境变量:
  - `GITHUB_TOKEN` = 有本仓 `contents:write` 的 PAT(个股解读 PUT 用)
  - `FEED_HMAC_SECRET` = 与仓库 Secret 同值(量化报告签名用)
  - `OPENCLAW_REPO=edwardwang66/stock-analysis`、`OPENCLAW_BRANCH=main`(stock-note Contents 写入分支;dispatch 忽略)
  - `OPENCLAW_MODEL=gpt-5.5`(仅作为报告/解读的 `model` provenance 字段;不选择模型服务)
- [ ] ~~维护本地 `watchlist.txt`~~ **已废弃(2026-06-09)**:自选清单以仓库
  [`feed/watchlist.json`](../feed/watchlist.json) 为唯一真相源(Edward/Claude 维护,你只读)。

> **评分口径 v2(2026-06-09 起)**:综合评分已重构为十因子(见 [`methodology.md`](methodology.md) 第 7 节),
> 强趋势股 50-90 分、弱多 30-45 分,不再全是 50。note 引用分数时用 v2 实际数字。
> 模型无关:你的 OpenClaw 用 **GPT-5.5** 即可(设 `OPENCLAW_MODEL=gpt-5.5`)。

## 1. 拉取当日输入(每日覆盖范围,2026-06-10 版)
- [ ] 完整必析池:`feed/watchlist.json` 的 `symbols`(**唯一真相源**,全部必做,一只不落)。
      `daily_screener` 已把 ≥80 全名单轮换写入 `tier=screener`,SA LP 也在 `tier=salp`;
      读取 `symbols` 即可,不用再单独并集 screener 或 SA LP。
- [ ] 看多清单:`feed/screener/latest.json` 仅作评分/主题/行业上下文(≥80,v2+高阈值 = 多因子共振精选)。
- [ ] SA LP:`feed/funds/situational-awareness.json` 仅作持仓背景上下文;换仓后会同步进入 watchlist。
- [ ] **额外产出一份当日汇总报告**(给 Edward 的 report,日报 Issue 会自动嵌入):
      写入 `feed/screener/analysis-<YYYY-MM-DD>.md`,结构:
      ① 三池总览(自选池/看多/SA LP 各自的多空倾向统计) ② 看多清单按主题分组点评
      ③ 最值得关注的 3-5 只(理由+风险) ④ 与昨日清单的进出变化 ⑤ 数据来源列表
- [ ] note 的 thesis/view 须含方法论结论:TD9 当前计数、52 周位置、SuperTrend(10,3) 方向、
      缠论笔方向与背驰迹象(口径见 [`methodology.md`](methodology.md))
- [ ] (量化用)拉市场快照:`feed/market/state.json`、`feed/signals/latest.json`、`feed/market/history.json`
- [ ] **每周五收盘后**:运行 `python scripts/winter_pg/winrate.py` 产出
      `feed/screener/winrate.json`(≥80 picks 的 d1/d5/d20 胜率、平均收益、最佳/最差、80-84/85-89/90+ 分段)。
- [ ] **每日收盘后**:跑事件热度榜(PG `intraday_events` 近 7 天聚合 top20)→
      `feed/signals/event-heat.json`(第十五轮 schema);与 winrate 同样幂等。

---

## 2. 任务 A — 每日个股 AI 解读(stock-analyst,双层)
> **2026-06-10 起(Edward 指令)**:每日分析 = 技术面层(methodology 六法,照旧)+
> **基本面层(Codex「public equity investing」插件)** → note 可选字段 `fundamentals`
> {valuation/quality/catalysts/peers/verdict}(契约见第十八轮)。插件无产出的票省略该字段,不编造。

对集合里**每只**标的:
- [ ] 用 [stock-analyst prompt](../docs/openclaw-stock-notes.md#stock-analyst-角色-prompt交给你的-openclaw) 让 Claude 基于**真实**行情/财报/新闻产出 JSON(字段:`stance/thesis/earnings/news/risks/view/sources`)
- [ ] 校验:`stance ∈ {看多,看空,中性}`;`sources` 非空(数值有出处);无"买入/卖出/目标价"
- [ ] 存成 `note.json`,投递:
  ```bash
  python scripts/openclaw_client.py --mode github-api --stock-note <US:XXXX> --report-file note.json
  ```
- [ ] 此通道是 privileged direct write,不经 stock-note schema/HMAC/path containment;只使用可信、已审阅输入,并按
      [stock-note authority](../docs/openclaw-stock-notes.md) 核对实际分支与索引。
- [ ] 验收:打开 `https://edwardwang66.github.io/stock-analysis/symbol/?s=<US:XXXX>` → 「🤖 AI 解读」卡片更新为今天

**产出**:`feed/stock-notes/<MARKET>-<CODE>.json` 每只一份。

---

## 3. 任务 B — 量化 5 角色(走 /intel)
按 [`openclaw-agent-prompts.md`](openclaw-agent-prompts.md),用**真实数据**各产一份(符合 `feed/schema/report.schema.json`):
- [ ] `residual-analyst` 残差/协整健康度、配对候选
- [ ] `crowding-monitor` 拥挤/同质化/资金流(尾部风险)
- [ ] `event-risk` 财报/FOMC/CPI/指数重构/SSR 事件标注(仅回避,不做方向 alpha)
- [ ] `factor-factory` 可审计公式因子(每条自带六门控自检)
- [ ] `red-team` 对每条结论做对抗核验(有否决权)

每份:
- [ ] 写成 `report.json`(公共信封 + 该角色字段),投递:
  ```bash
  python scripts/openclaw_client.py --mode dispatch --role <role> --report-file report.json
  ```
  (设了 `FEED_HMAC_SECRET` 会自动签名;经 `feed-validate.yml` 校验并入)
- [ ] 验收:`https://edwardwang66.github.io/stock-analysis/intel/` 的「②信息量」来源里 openclaw 计数 +1

---

## 4. 任务 C — 大盘综述(可选,1 段)
- [ ] 让 Claude 基于 `feed/market/state.json` + 当日要闻,写一段 ≤120 字的**中性**大盘综述(regime、广度、拥挤、需要注意的事件),作为 `event-risk` 报告的 `notes` 一并投递

---

## 5. 收尾验收
- [ ] `/intel`「②信息量」近 24h 计数上升,来源含 `openclaw-agent:*`
- [ ] 抽查 2 只个股页「🤖 AI 解读」为今日、有来源链接
- [ ] 任一投递失败 → 看 GitHub Actions `feed-validate` 日志(多半是 schema/签名/边界);修正后重投
- [ ] 如果用 SSH/local 投递,提交前先 `git pull --rebase origin main`,再 `git push`
- [ ] 全程未输出任何投资建议措辞

---

## 6. 建议节奏
- **美股收盘后**(北京时间次日早)跑一轮:任务 A(个股)+ 任务 B(5 角色)+ 任务 C(综述)
- 盘中如需,只跑任务 A 的自选子集 + `crowding-monitor`/`event-risk`
- 把本清单设为 OpenClaw 的每日 routine;失败重试 + 把 run_url 填进报告 `producer.run_url` 便于溯源
- 报告相同 id 重投会被拒绝;先核对 GitHub event、workflow 和 commit 状态,再为独立新投递生成新 id

> 可执行骨架见 [`../scripts/openclaw_daily.py`](../scripts/openclaw_daily.py):已实现确定性的清单、OHLCV/SEC 分析、
> 遍历与投递路径。只有在明确接入外部分析服务时才替换该分析边界;当前脚本会捕获部分失败并可能正常退出。

---

## 7. 盘中节拍(2026-06-10 Edward 定版,重要)

分层架构:**5 分钟机器报告**(Actions/worker 自动跑 `feed/intraday/latest.json`,非 LLM)+ **你的 LLM 深读按事件触发**。

- [ ] **盘前 report(硬性)**:美东 09:00 前(13:00-13:30 UTC 窗口)投递
      `feed/screener/analysis-premarket-<date>.md`:全池(自选池∪SA LP∪昨日≥80)盘前异动、
      隔夜新闻、今日事件窗口、按方法论给出当日关注位(Pivot/九转/SuperTrend 状态)。
      **行情原料直接读 `feed/intraday/overnight.json`**(12:40 UTC 自动生成:美股期货
      ES/NQ/YM、亚洲收盘、欧洲盘中、隔夜加密、昨日异动 top20、**perp_movers=24/7 永续
      夜盘异动 |24h|≥4%**——存储链等池内重仓的隔夜预警优先点名),不用自己抓。
- [ ] **盘中事件驱动(每5分钟轮询,只写增量)**:轮询 live 分支 `feed/intraday/latest.json` 的
      `events[]`(本机直接看 `INTRADAY_EVENTS.flag` 更快);对触发标的生成一句话解读后用
      **一条命令落两处**:`python scripts/openclaw_intraday_update.py --symbol <SYM> --note "<一句话>" --push`
      (自动 merge note.intraday_update + 滚动追加 analysis-intraday-<date>.md,rebase 安全);
      处理完 `--clear-flag`。缺投盘前/收盘前报告会被 openclaw-watchdog 自动开 Issue 点名。
- [ ] **收盘前 report(硬性)**:美东 15:30(19:30 UTC)投递 `feed/screener/analysis-close-<date>.md`:
      尾盘 30 分钟关注点、当日全池复盘要点、明日前瞻。
- [ ] 收盘后照旧:全量 notes + 当日汇总(§1 的 analysis-<date>.md);纳指/标普大盘综述一天一份即可。

> 注:盘中 LLM 不做全池重写 —— 5 分钟内写不完且成本不可持续;机器报告负责"快",你负责"深"。
