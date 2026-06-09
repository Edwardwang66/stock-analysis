# OpenClaw 每日任务清单(Playbook)

> 这是给**你本地的外部 OpenClaw**(Claude agent)每天照着执行的任务清单。
> 仓库已铺好契约/投递/接收/展示;OpenClaw 负责**真分析**并把结果投递回来。
> 配套:[`openclaw-agent-prompts.md`](openclaw-agent-prompts.md)(量化 5 角色 prompt)、
> [`../docs/openclaw-stock-notes.md`](../docs/openclaw-stock-notes.md)(个股解读契约)。
> 铁律(R6):**LLM 是研究放大器,不决策;数值必须有来源;不编造;一律"非投资建议"。**

---

## 0. 环境准备(一次性)
- [ ] clone 本仓到 OpenClaw workspace,`cd stock-analysis`
- [ ] 环境变量:
  - `GITHUB_TOKEN` = 有本仓 `contents:write` 的 PAT(个股解读 PUT 用)
  - `FEED_HMAC_SECRET` = 与仓库 Secret 同值(量化报告签名用)
  - `OPENCLAW_REPO=edwardwang66/stock-analysis`、`OPENCLAW_BRANCH=main`
  - `OPENCLAW_MODEL=gpt-5.5`(你的 OpenClaw 模型;会写进报告/解读的 `model` 字段)
- [ ] 维护一个自选清单 `watchlist.txt`(每行一个,如 `US:AAPL`),没有就先用选股清单前 N 只

> **本清单只分析「看多列表」**:`feed/screener/latest.json` 里全是评分 ≥ 50 的**强烈看多**标的——就是你的看多列表。
> 模型无关:你的 OpenClaw 用 **GPT-5.5** 即可(设 `OPENCLAW_MODEL=gpt-5.5`)。

## 1. 拉取当日输入(看多清单)
- [ ] 看多清单:`curl -s https://raw.githubusercontent.com/edwardwang66/stock-analysis/main/feed/screener/latest.json -o screener.json`
- [ ] 要分析的标的集合 = **看多清单**(前 15 只,或全部)∪ 自选 `watchlist.txt`(去重)
- [ ] (量化用)拉市场快照:`feed/market/state.json`、`feed/signals/latest.json`

---

## 2. 任务 A — 每日个股 AI 解读(stock-analyst)
对集合里**每只**标的:
- [ ] 用 [stock-analyst prompt](../docs/openclaw-stock-notes.md#stock-analyst-角色-prompt交给你的-openclaw) 让 Claude 基于**真实**行情/财报/新闻产出 JSON(字段:`stance/thesis/earnings/news/risks/view/sources`)
- [ ] 校验:`stance ∈ {看多,看空,中性}`;`sources` 非空(数值有出处);无"买入/卖出/目标价"
- [ ] 存成 `note.json`,投递:
  ```bash
  python scripts/openclaw_client.py --mode github-api --stock-note <US:XXXX> --report-file note.json
  ```
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
- [ ] 全程未输出任何投资建议措辞

---

## 6. 建议节奏
- **美股收盘后**(北京时间次日早)跑一轮:任务 A(个股)+ 任务 B(5 角色)+ 任务 C(综述)
- 盘中如需,只跑任务 A 的自选子集 + `crowding-monitor`/`event-risk`
- 把本清单设为 OpenClaw 的每日 routine;失败重试 + 把 run_url 填进报告 `producer.run_url` 便于溯源

> 可执行骨架见 [`../scripts/openclaw_daily.py`](../scripts/openclaw_daily.py):已写好"拉清单→遍历→投递"的管道,
> 只需把其中的 `analyze_stock()` / `analyze_role()` 接到你的 OpenClaw/Claude。
