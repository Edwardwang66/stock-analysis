# Need to Fix — 功能审查问题清单(持续更新)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [current architecture](../../current-architecture.md); historical relative links below are preserved verbatim and may not resolve from this archived location.


> 持续审查新开发功能的**时效性 / 有效性 / 鲁棒性**,问题记录在此。
> 状态:✅ 已修 · 🔶 待修 · 👀 需确认。最后更新 2026-06-10。

## ✅ 已修(修复在 main,附根因)

1. **backend/requirements.txt 双版本 pin** — Dependabot PR 合并冲突解错,fastapi/uvicorn 各 pin 两个版本,
   `pip install` 直接 ResolutionImpossible → daily-screener 连红、Render 部署失败、dependabot pip job 失败。
   已去重并加 `tests.yml` 闸门防回归。
2. **daily-screener 开 Issue 无当日去重** — push 路径触发 + 手动 dispatch 一天多跑,每跑一次开一个新 Issue
   (06-10 当天刷出 8 个重复)。已改为「当日已有→更新正文」;title 阈值也改为跟随 dispatch 输入(原硬编码 ≥80,
   与正文/实际阈值不一致)。历史重复 Issue 已按 duplicate 关闭(保留 #42/#18)。
3. **premarket-pack 读到陈旧盘中快照(时效性)** — 盘中 5 分钟心跳只写 live 分支,main 上的
   `feed/intraday/latest.json` 是过期副本;盘前要素包却从 main 读。已改为先从 live 分支 checkout 最新快照。
4. **.gitignore 整目录拦截 overnight.json** — `feed/intraday/` 被整目录 ignore,premarket-pack 的
   `git add` 退出码 1(首跑失败)。已改为 `feed/intraday/*` + 负向豁免。
5. **chan_engine 3B/3S 漏检标准形态(有效性)** — 原实现只看中枢后第一笔,「向上离开(笔)→回踩(笔)」
   的教科书三买形态永远检测不到。已改为按离开方向找第一个回踩/反抽。单测覆盖。
6. **chan_engine 空结果无保护(鲁棒性)** — 数据源整体故障时会用空统计覆盖 feed 里的旧数据。
   已加保护:0 买卖点且旧文件存在 → 保留旧文件并失败退出(CI 可见)。

## 🔶 待修

7. **缠论胜率统计存在确认滞后偏差(有效性,重要)** — 信号时点 = 笔端点(分型极值),但分型需要其后
   若干根 K 线才能确认;实盘无法在端点当根入场。r5/r20 胜率因此**系统性偏乐观**,active 清单里
   「最近3根」的信号本质上未确认。建议:统计时把入场点后移到分型确认根(端点后第2根合并K收盘),
   或在 /tracker 看板明确标注「理论值,含确认滞后偏差」。
8. **frontend/lib/chan.ts 与 Python 引擎双实现无一致性检测** — 前端个股页与周报统计号称「同口径」,
   但两套代码各自演化(本次 3B 修复只改了 Python 侧,chan.ts 同样漏检标准三买形态——前端面板显示的
   3B/3S 与周报口径已经漂移)。建议:① chan.ts 同步修复;② 用同一份 golden K线 JSON 做跨实现一致性测试。
9. **前端零测试基础设施** — chan.ts/feed.ts/search.ts 等纯逻辑库无任何单测。建议引入 vitest(轻量,
   配 Next 14 兼容),先覆盖 chan.ts 与 search 双语联想。
10. **daily-screener / premarket 等任务同样缺「空结果保护」** — 同第 6 条问题:Yahoo 全挂时
    latest.json 会被空清单覆盖(/screener 页面变空白)。建议复用 chan_engine 的保护模式。
11. **dependabot-automerge 的 sweep 无视测试状态合并** — sweep 只查 statusCheckRollup,而在
    `tests.yml` 落地前 PR 上没有任何检查 → 实质裸合并。现在有 tests 了,建议:仓库开分支保护把
    `Tests (单元测试闸门)` 设为 required,sweep 的「检查全绿才合」才真正生效。
12. **deploy-pages 捆绑 feed 快照 `cp ... || true` 静默吞错** — 快照目录缺失时 Pages 照样发布,
    首屏兜底数据悄悄变旧。建议改为显式列目录、缺失即 warning。
13. **intraday 心跳数据的其他消费端时效性需自查(时效性)** — 同第 3 条根因:任何从 main(raw)读
    `feed/intraday/latest.json` 的消费端(前端 /desk、/intel 等)拿到的都是过期副本,需逐一确认
    实际读取分支。

16. **夜盘数据无时效防护(时效性,优先级↑)** — 全站夜盘层(`nightquotes.ts`)的 mark 来自
    hyperliquid-monitor 2h 定时,最多滞后 ~2 小时;两处消费端都没查 `updatedAt`:
    ① 卡片「隐含高开/低开」用陈旧 mark 对比正股价,隔夜剧烈波动时失真;
    ② **价格提醒在闭市时直接用夜盘 mark 触发系统通知**(page.tsx 夜盘增强)——旧价可能误报/漏报。
    建议:`useNightQuotes` 暴露 stale 标志(updatedAt > 3h),提醒触发跳过 stale 价,卡片标注快照时间。

17. **intraday `*/15` cron 改后未自燃(时效性)** — 07:36 改完调度到 08:1x 没有一次 schedule 触发
    (新 cron 注册延迟 + GitHub 高频 cron 不可靠),盘中流靠手动 dispatch 续命(07:40、08:1x 两次)。
    建议的稳健化:让 keep-warm(12 分钟一班,历史触发稳定)加一步「live 超 10 分钟未更新 →
    `gh workflow run intraday-report.yml`」,把高频任务从"靠 cron 自燃"改成"低频看门狗拉起"。
    属于盘中流水线的架构决策,留给主开发线确认。

## 👀 需确认

14. **screener Issue 评分口径漂移** — 06-09 的 Issue 里同一批股票评分全是 50,06-10 变成 80-90,
    疑似 signals.analyze 评分标尺当天有调整;若是,历史 winrate/tracker 数据跨日不可比。
15. **卖点胜率的 0 收益归类** — r==0 时按「买点不胜/卖点胜」处理(`(r>0)==is_buy`),对卖点略偏乐观;
    样本大时影响小,统计口径文档里应注明。
