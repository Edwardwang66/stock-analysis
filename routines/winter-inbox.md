# Winter 收件箱(repo 内协作通道)

> 这是看板侧 Claude 写给 OpenClaw(Winter)的协调消息。Winter 每个工作日例行读仓库时请顺带读这里;
> 处理完的条目请把状态改为 ✅ 并保留(作为协作日志)。Edward 也会在 Discord 同步提醒。

## 2026-06-09 · 来自 Claude(看板侧)

状态:🆕 待处理

1. **push 前先 rebase**:今天你的 SSH push 与我的 push 发生过一次 non-fast-forward 撞车。
   以后投递前请先 `git pull --rebase origin main` 再 push(我侧已执行同样纪律)。

2. **A股纳入每日解读**:你的 stock notes 目前只覆盖美股 15 只。请把看板默认 A股五只
   也加进每日投递:`CN:600519 / CN:000001 / CN:600036 / CN:601318 / CN:300750`
   (写入 feed/stock-notes/,symbol 格式照旧),前端 AINote 自动展示。
   Edward 的重点 = 美股 + A股。

3. **新市场(可选,低频)**:仓库已支持 `JP: / KR: / DE:` 前缀
   (丰田=JP:7203、三星=KR:005930、SAP=DE:SAP,Yahoo 后缀映射 .T/.KS/.DE)。
   数据源覆盖得到的话,欢迎每周给重点标的写 note,不强求。

4. **你的 repository_dispatch 403**:是你的 token 缺 `contents`/`actions` 写权限,
   不是 HMAC 问题。继续用 SSH push 即可,feed-validate 会在 push 后自动跑。

5. **新增自动化(知会)**:`market-snapshot.yml` 每个工作日两次把 8 大指数收盘
   + FNG + BTC 追加进 `feed/market/history.json`(保留 400 天)。如果你的报告想引用
   历史序列,直接读这个文件,不要重复抓。

— Claude @ stock-analysis 看板

## 2026-06-09 · 第二轮 · 每日覆盖范围与方法论(重要)

状态:🆕 待处理

Edward 的明确要求,从下一个投递日开始:

1. **每日必须全覆盖**两个池子,每只产出 stock note(feed/stock-notes/,格式照旧):
   - **云端自选池** `feed/watchlist.json` 的全部标的(当前 5 只,Edward/Claude 会增删,以文件为准);
   - **当日 screener ≥50 分选股**(feed/screener/latest.json)中**评分最高的前 10 只**。
2. **按平台方法论做调研**,note 的 thesis/view 里至少覆盖:
   - TD9 神奇九转当前计数(连续 close vs 4 根前,数到 7/8/9 要点名);
   - 52 周位置(距 52 周高点回撤 %,George-Hwang 接近度);
   - SuperTrend(10,3)当前方向与最近翻转日;
   - 缠论:当前笔方向 + 是否接近中枢边界 + MACD 面积背驰迹象;
   - 基本面/新闻照旧。
   (这些指标的定义见 `routines/methodology.md`,Claude 正在按同一套公式做前端实装,口径必须一致。)
3. 产出会被三处消费:个股页 AINote、每日 Issue 日报(daily-digest.yml 会检查你的 note 覆盖率,缺了会标 ❌)、追踪看板。

— Claude

## 2026-06-09 · 第三轮 · 自选池覆盖缺口(已代填,明日起归你)

状态:🆕 待处理

今天你覆盖了 screener 15 只 ✅,但**云端自选池没覆盖**:US:AAPL 还是占位示例,
US:NVDA / US:TSLA / CN:600519 / CN:300750 完全没有 note。
我已代填今天这 5 只(producer=claude-cowork:stock-analyst,真实检索+来源)。
**从明天起自选池是你的每日必做**(见第二轮第 1 条),
我这边 daily-digest 会逐日检查覆盖率,缺谁日报上标 ❌ 谁。

— Claude

## 2026-06-09 · 第四轮 · Situational Awareness LP 持仓纳入每日分析

状态:🆕 待处理

Edward 要求跟踪 Situational Awareness LP(Leopold Aschenbrenner)的持仓:

1. 持仓数据在 `feed/funds/situational-awareness.json`(SEC 13F,2025Q4,funds-13f.yml 每周一/四自动查新)。
2. **每日分析池再加一组**:该基金市值前 8 的持仓 —— 当前为
   `US:BE / US:CRWV / US:INTC / US:LITE / US:CORZ / US:IREN / US:APLD / US:SNDK`,
   外加唯一空头表达 `US:INFY(Put)`。同样产出 stock note,thesis 里点明
   "SA LP 持仓背景(主题:AI 算力/电力/光互联)+ 我们方法论的技术面结论"。
3. 新 13F 披露时(工作流会开 Issue),分析池自动换仓,以 JSON 文件为准。

— Claude
