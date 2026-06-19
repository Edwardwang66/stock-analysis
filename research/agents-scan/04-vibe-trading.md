# 04 · Vibe-Trading 调研

> 调研日期 2026-06-19。诚实纪律:每条关键结论标 **一手来源 URL + 可信度(高/中/低)**;star 高 ≠ 能赚;无法核实标「未核实」。

## 一、仓库事实(含确认难度)

榜单写「~8k stars / 个人交易」,但「Vibe-Trading」这个名字在 GitHub 上**有多个同名/蹭名仓库**(`VibeTradingLabs/vibetrading`、`vibe-trading-agent/vibe-trading`、`catveg/vibe-trading`、`vibetrading.dev` 等),**确认难度=中**。需按「README 内容 + star 量 + 维护组织」三重交叉,才能锁定榜单所指的主仓库。

最匹配、且体量与榜单同量级(实际更高)的是 **`HKUDS/Vibe-Trading`**:

| 项 | 值 | 来源 / 可信度 |
|---|---|---|
| 准确 URL | https://github.com/HKUDS/Vibe-Trading | 高 |
| 作者/组织 | HKUDS = Data Intelligence Lab @ 香港大学(港大,负责人 Chao Huang),非「个人」 | https://github.com/HKUDS · https://sites.google.com/view/chaoh · 高 |
| 实际 star | **~12.7k**(skillsllm 镜像计 12,611,2.4k forks)——**比榜单「8k」高**,榜单偏低/过时 | https://github.com/HKUDS/Vibe-Trading · https://skillsllm.com/skill/vibe-trading · 高 |
| License | MIT | GitHub 仓库页 · 高 |
| 语言 / Python | Python 3.11+,包名 `vibe-trading-ai` | pyproject · 高 |
| 活跃度 | 高频:v0.1.10 于 2026-06-19(当天)发布,版本号密集迭代 | GitHub releases · 高 |
| 榜单「个人交易」标签 | **不准确**:实为高校 AI 实验室的多智能体研究框架(同生态有 LightRAG/AI-Trader/nanobot) | 高 |

**判断**:榜单条目大概率指向 `HKUDS/Vibe-Trading`,但「~8k stars / 个人」两项标注都**有偏差**(star 偏低、作者非个人)。HKUDS 是有 EMNLP2025 论文(LightRAG)背书的真实学术团体,**组织可信度=高**;但「能不能赚钱」与组织声誉无关(见第三节)。

## 二、概念与工作流

「vibe trading」确为「vibe coding」在交易域的延伸:**自然语言意图 → LLM 生成可回测/可执行策略代码**,把 ideation→research→backtest→deploy 从数周压到数分钟(行业语境,来源 wundertrading / blockeden,可信度 中)。

`HKUDS/Vibe-Trading` 自述工作流(README,来源高):
1. **Plan** — agent 选 finance skills / 工具 / 数据源 / swarm 预设;
2. **Ground** — 经 loader 拉市场上下文(A 股、美股、crypto、forex、文档、web);
3. **Execute** — 生成可测策略代码,跑工具 + 匹配的回测引擎(股/期/汇/期权/crypto);
4. **Validate** — 加指标、基准对比、Monte Carlo / Bootstrap / Walk-Forward、run card;
5. **Deliver** — 出报告、工具 trace、导出(Pine Script / TDX / MT5)。

定位为「research workspace」:**不持资金、不自营撮合**;broker 实盘(如 Robinhood OAuth)被明确标注为「experimental、未经真实账户验证」(README,高)。

## 三、可信度与过拟合风险

- **真实样本外业绩 / 实盘 track record:无。** README 未提供任何 OOS/live 业绩数字,且自带免责声明「not investment advice, holds no funds」「历史验证不保证未来」(来源高)。→ 与所有同类项目一样:**star ≠ 赚钱,无可验证的前瞻收益证据**(可信度 高,这是「无证据」本身的高可信)。
- **过拟合 / 数据窥探风险:结构性偏高。** 自然语言生成天然是「随口一个想法 → LLM 拟合历史」的窥探机器:用户口语化念头 → LLM 在已知历史上反复试到「好看」的因子。多次试探、自由参数、未登记的搜索空间 = 经典 data-snooping。
- **值得注意:该项目自己装了护栏**(README,高),比多数同类成熟:
  - AST 纯度门 + **300 行 lookahead 哨兵测试**(抓未来函数 / 前视泄漏);
  - `pytest-socket` 断网 kill-switch(防回测期数据泄漏);
  - **strict alpha-bench:同 universe 随机对照 + OOS split**(抓「只是 tracking beta」的伪因子);
  - Walk-Forward / Bootstrap CI 可选。
- **但护栏≠免疫**:单次 OOS split + 随机对照,**挡不住跨多次对话的多重检验**(用户反复 prompt 直到通过门控);未见「试验次数登记 / 多重检验校正(如 Deflated Sharpe、White's Reality Check / SPA)」。→ **过拟合风险=中高(已部分缓解,但缺多重检验纪律)**,可信度 中(基于 README 所列与未列,未逐行审计源码,**代码级核实=未核实**)。

## 四、对我方系统的可借鉴

我方有「LLM 假设工厂(只产可审计公式因子 / 过六门控 / 不决策)」,可直接借鉴它**已工程化的几道门**:
1. **lookahead 哨兵 + 断网 kill-switch**:把「未来函数 / 回测期数据泄漏」做成自动化测试,纳入我方六门控的「无前视」一门——简单、强、可证伪。
2. **AST 纯度门**:对 LLM 生成的因子做语法层白名单,杜绝偷取未来数据 / 危险调用,契合我方「只产可审计公式」原则。
3. **同 universe 随机对照 + OOS split**:作为我方「不只 track beta」一门的实现参考。

**我方门控如何防它变成过拟合机器(这是关键纪律,该项目尚缺):**
- **试验登记 + 多重检验校正**:每个由自然语言派生的因子都计数,统计阈值随试探次数收紧(Deflated Sharpe / White Reality Check / SPA / Bonferroni),封死「反复 prompt 到通过」。
- **预注册式 OOS 锁仓**:OOS 区间在因子定稿前冻结,LLM 不可见、不可重采样;失败即弃，不许回炉再调。
- **公式可审计 + 不决策**:坚持 LLM 只产人类可读公式因子(非黑箱代码 alpha)、且**不下单**,把「自然语言→策略」截断在「自然语言→候选假设」,决策权留给六门控与人。
- **样本外/实盘留痕**:要求前瞻业绩,而非回测曲线,才能反炒作。

## 五、一句话定位

`HKUDS/Vibe-Trading`(港大 AI 实验室,~12.7k★ / MIT / 高频迭代,榜单「8k·个人」两项均有偏差)是**目前护栏做得较认真的自然语言→策略研究框架**:工程门控(lookahead 哨兵、AST 门、断网、OOS 对照)值得抄;但**无任何样本外/实盘业绩、缺多重检验纪律**,本质仍是高过拟合风险的「想法拟合器」——可借其门控、**绝不可借其结论**。
