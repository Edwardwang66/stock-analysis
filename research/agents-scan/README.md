# 10 大开源 AI 交易 Agent 项目 — 诚实扫描 + 采纳矩阵

> 来源:用户提供的「10大 AI 交易 Agent 开源项目排行榜」图。方法:10 个并行 agent 各核实一个项目
> (真实仓库 / star 核实 / 架构 / 可信度 / 可借鉴),房子风格:**反炒作、star≠能赚、区分真证据与营销**。
> 逐项详见本目录 `01-…10-*.md`。配套既有调研:[`../ai-agents-skills-market-scan.md`](../ai-agents-skills-market-scan.md)、
> [`../long-term/ai-llm-fundamental-agents-2026.md`](../long-term/ai-llm-fundamental-agents-2026.md)。

---

## 一、核实后的事实表(榜单 vs 真实)

| # | 榜单名 | 真实仓库 | star(核实) | License | 关键纠偏 |
|---|---|---|---|---|---|
| 1 | TradingAgents | `TauricResearch/TradingAgents` | ~87k(榜单 78k 偏低) | Apache-2.0 | 多 agent 辩论框架;**Profit Mirage 论文证伪** |
| 2 | TradingAgents-CN | `hsliuping/TradingAgents-CN` | ~28.7k | **混合(app/前端专有)** | 中文 LLM+A股数据;**非纯开源** |
| 3 | AI-Trader | `HKUDS/AI-Trader` | ~20k | — | **学术评测基准≠赚钱系统**;Issue#207 量化打脸 |
| 4 | Vibe-Trading | `HKUDS/Vibe-Trading` | ~12.7k(榜单 8k 偏低) | MIT | NL→策略;**护栏做得较认真** |
| 5 | TensorTrade | `tensortrade-org/tensortrade` | ~6.3k | Apache-2.0 | RL 框架;**2022 起休眠**,玩具业绩扣费转负 |
| 6 | QuantDinger | `brokermr810/QuantDinger` | ~6.4k | 混合(前端 source-available) | 「多 agent」实为 MCP 网关;营销账号红旗 |
| 7 | (OpenBB?) | 最可能 `TraderAlice/OpenAlice` | ~5.4k | AGPL-3.0 | **榜单张冠李戴**(OpenBB 是 Python 69k);Trading-as-Git |
| 8 | Polymarket agents | `Polymarket/agents`(官方) | ~3.7k | MIT | **已归档**;SDK 脚手架;**数据免费可得=真价值** |
| 9 | AutoHedge | `The-Swarm-Corporation/AutoHedge` | ~3.5k | MIT | 链上真自动下单+私钥;**纯营销,高价值反面教材** |
| 10 | TradingGym | `Yvictor/TradingGym` | ~1.9k | MIT | 2017 RL 回放环境;已休眠 |

---

## 二、跨项目元结论(诚实)

1. **star 数与盈利能力零相关。** 多个项目 star 由营销驱动(swarms 生态、新营销账号、强 CTA 求 star);榜单数字与实际多有出入(有的偏低如 TradingAgents/Vibe,有的张冠李戴如第 7)。
2. **10 个项目无一有真实「样本外 + 扣成本 + 多资产」可复现业绩。** 全部停在 demo/自报/paper-trading;有的连风险免责都没有(AI-Trader、AutoHedge)。
3. **最强的负面证据来自学术:** TradingAgents 被 **Profit Mirage(arXiv 2510.07920)** 实证——测试期移出 LLM 知识窗后 Sharpe 衰减 55.68%,业绩主要来自**训练集泄漏**而非推理。直接印证我方既有结论(`ai-llm-fundamental-agents-2026.md`:LLM 选股=泄漏)。
4. **真正值得抄的是「架构模式」与「工程护栏」,不是「让 LLM 决策」。** 多 agent 分工 + Bull/Bear 对抗辩论是好编排;但**谁都不该让 LLM 直接决策/下单/持私钥**(AutoHedge 是反面教材的极致)。
5. **AutoHedge 的存在反向证明我方设计正确**:刻意**不自动下单、不让 agent 持密钥、净·扣成本是唯一货币**。

---

## 三、采纳矩阵(借鉴什么 → 怎么并入我们系统)

| 模式 | 来源项目 | 并入方式(尊重纪律) | 状态 |
|---|---|---|---|
| **Polymarket 事件概率(免费只读)** | Polymarket agents | `scripts/polymarket_events.py` → `feed/events/` 外部事件/不确定性因子(longshot 去偏);**不下注** | ✅ 本轮落地 |
| **Bull/Bear/Risk 结构化辩论** | TradingAgents | OpenClaw agent 编队加「红蓝队对抗」playbook:LLM 只产**可证伪论点+证据**,过门控,不决策 | ✅ 本轮 playbook |
| **NL→策略的工程护栏** | Vibe-Trading | lookahead 哨兵 / AST 纯度门 / 断网 kill-switch 思路并入因子工厂六门控的「候选自检」清单 | ✅ 本轮文档 |
| **多源降级取数 + AkShare 仅盘后 ETL** | TradingAgents-CN | A股接入时的工程纪律(已记入路线图);实盘读本地库不实时爬 | 📋 路线图 |
| **MCP 最小权限 + paper-only 默认 + 审计** | QuantDinger | 外部 AI agent 接入平台的安全范式(对标我方 OpenClaw HMAC+CI 闸门) | 📋 已有等价物 |
| **数据 payload 带来源戳+staleness** | OpenAlice | 我方 feed 已有 `asof`/`age_days`/`stale`(`feed_lib`)——**已具备,印证方向** | ✅ 已有 |
| **凭证/执行与 AI 层硬隔离** | OpenAlice / QuantDinger | 我方刻意不接实盘,天然隔离;若未来接券商按此 | 📋 原则 |
| **RL 回放环境 / cost-explicit reward** | TensorTrade / TradingGym | **不引入 RL 主线**(非平稳+过拟合,与 DSR/PBO 栈相悖);仅理念存档 | ❌ 不采纳 |
| **让 LLM 决策/下单/持私钥** | AutoHedge / AI-Trader | **明确拒绝**(反面教材) | ❌ 红线 |

---

## 四、本轮落地的具体集成

1. **Polymarket 事件概率因子**(免费、无 key、零合规风险——只读不下注):
   `scripts/polymarket_events.py` 拉取金融/宏观相关市场(Fed 降息/衰退/CPI/BTC 目标价等)的隐含概率 →
   `feed/events/latest.json`,带 **longshot 去偏**注记;`/intel` 看板展示;月度/周度工作流刷新。
   依据:我方既有调研已将预测市场列为「可作 meta-labeling 外部预测因子」,且本轮核实 **`clob.polymarket.com/prices-history` 与 Gamma API 免鉴权免费**。
2. **红蓝队辩论 playbook**:把 TradingAgents 的 Bull/Bear/Risk 结构并入 OpenClaw agent 提示词——
   LLM 只产「可证伪论点 + 一手证据 + 反方」,落 `feed/` 由人/门控裁决,**不决策**(R6)。

> ⚠️ 全部研究/演示用途,**非投资建议**。这 10 个项目里**没有一个**提供了可信的赚钱证据;
> 我们抄的是工程模式与反面教训,绝不抄它们的「结论」或「让 LLM 决策」的范式。
