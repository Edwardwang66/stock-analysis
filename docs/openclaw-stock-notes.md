# OpenClaw 每日个股 AI 解读(stock-analyst 角色)

> 让你**本地的外部 OpenClaw**(Claude agent)每天对「选股清单 + 你的自选」做真分析,
> 把结果投递回本仓 `feed/stock-notes/`,**个股页**(`/symbol`)自动显示「🤖 AI 解读」卡片。
> 量化 5 角色(残差/拥挤/事件/因子/红队)走 `/intel`,见 [`openclaw-integration.md`](openclaw-integration.md);本文是新增的**面向个股**的解读通道。

## 数据契约(每只股票一个 JSON)
路径:`feed/stock-notes/<MARKET>-<CODE>.json`(如 `US-AAPL.json`)。形状:
```json
{
  "symbol": "US:AAPL",
  "date": "2026-06-09",
  "model": "gpt-5.5 (via OpenClaw)",
  "producer": "openclaw-agent:stock-analyst",
  "stance": "看多 | 看空 | 中性",
  "thesis": "多空逻辑(多头/空头各自核心论点)",
  "earnings": "最近一季营收/EPS/指引要点",
  "news": "近一周关键新闻与多空含义",
  "risks": "监管/供应链/事件窗口等风险点",
  "view": "一句话综合看法",
  "sources": [{ "title": "来源标题", "url": "https://..." }]
}
```
个股页只在该文件存在时显示卡片;`stance` 决定徽章颜色。

> **与模型无关**:你的 OpenClaw 用 **GPT-5.5**(或任意 LLM)都行——契约和 prompt 不绑定模型。
> 设环境变量 `OPENCLAW_MODEL=gpt-5.5`,投递时会自动写进 `model` 字段。

## OpenClaw 端怎么跑(每日)
**输入(只分析"看多清单")**:① 当日选股清单 `feed/screener/latest.json` —— 全是评分 ≥ 80 的多因子共振标的(就是你的精选看多列表);② 你的自选 watchlist。
**对清单里每只股票**,用下面的 prompt 让你的 OpenClaw(GPT-5.5)产出一份 stock-note,再投递。

### stock-analyst 角色 prompt(交给你的 OpenClaw)
```
你是严谨的卖方股票分析师。针对标的 {SYMBOL}({NAME}),基于你能获取的最新公开数据
(行情/财报/新闻),输出一份**多空均衡**的解读,严格用 JSON 输出,字段:
  stance: 看多/看空/中性(给出净判断)
  thesis: 多头与空头各自最强的 1-2 个论点
  earnings: 最近一季营收/EPS/指引的关键数字与超预期与否
  news: 近一周最重要的 1-3 条新闻及其多空含义
  risks: 最值得警惕的风险点
  view: 一句话综合看法
  sources: 你引用的来源(标题+链接)
铁律:① 区分事实与观点,数值必须有来源;② 不得编造数据,拿不到就说明;
③ 这是信息参考,绝不输出"买入/卖出/目标价"式投资建议(Not financial advice)。
```

### 投递(两种方式,任选)
- **直接 PUT(推荐,简单)**:用本仓 `scripts/openclaw_client.py`:
  ```bash
  # 把 OpenClaw 产出的 note JSON 存成文件,然后:
  GITHUB_TOKEN=<你的PAT> OPENCLAW_BRANCH=main \
    python scripts/openclaw_client.py --mode github-api --stock-note US:AAPL --report-file note.json
  # 不带 --report-file 会生成一份占位模板,便于先打通链路:
  python scripts/openclaw_client.py --mode local --stock-note US:AAPL
  ```
  它会写/更新 `feed/stock-notes/US-AAPL.json`。raw GitHub 即时可见,**无需重建 Pages**。
- **本地测试**:`--mode local` 直接写仓内文件。

### 建议节奏
在你的 OpenClaw 侧加个每日 cron(美股收盘后):读 `feed/screener/latest.json` 的前 N 只 + 你的自选 →
逐只跑上面 prompt → `--mode github-api --stock-note <symbol>` 投递。个股页次日即显示。

## 量化 5 角色也要"真跑"
现有 `openclaw_client.py` 的 5 个角色函数返回的是**示例数据**(模板)。要让 `/intel` 的 OpenClaw 报告变"真":
在你的 OpenClaw 侧按 [`routines/openclaw-agent-prompts.md`](../routines/openclaw-agent-prompts.md) 的角色 prompt
用**真实数据**分析,产出符合 `feed/schema/report.schema.json` 的报告(可用 `--report-file` 覆盖示例),
`--mode dispatch` 投递(经 `feed-validate.yml` 校验)。建议每日 1 次,5 角色各一份。

> 安全:个股 stock-notes 走 Contents API 直接 PUT(你的 PAT、你的仓),不经 HMAC 门控——属个人项目可接受;
> 量化报告仍走 HMAC + schema 门控(`FEED_HMAC_SECRET`)。
