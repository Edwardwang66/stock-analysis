# 09 · AutoHedge —「自主对冲基金」调研

> 调研日期：2026-06-19 ｜ 评估视角：诚实可证伪、反炒作。每条关键结论标注一手来源 URL + 可信度（高/中/低）。
> 大词警告:「自主对冲基金」「自动化执行」「企业级」均为本项目营销用语,本文按字面拆解核实。

---

## 一、仓库事实（含 star 可信度）

- **仓库**: `The-Swarm-Corporation/AutoHedge` — https://github.com/The-Swarm-Corporation/AutoHedge （可信度：高）
- **作者/组织**: Kye Gomez 旗下 The-Swarm-Corporation（即 swarms 框架同一作者/组织）。（高）
- **License**: MIT。（高）
- **Star / Fork**: 抓取时约 **3.5k stars / 573 forks**（高，单点快照）。
  - **与榜单「~2.8k stars」对比**: 数量级一致,差异可由时间推移解释;**视为相符**。（中）
  - **star 可信度判断**: ⚠️ **低**。该项目所属生态(swarms / Kye Gomez)长期被指控**重营销、star/热度驱动**;且本仓库 `573 forks` 相对 `3.5k stars` 比例偏高,常见于教程/转发驱动的浏览,而非生产使用。star 高 ≠ 有人真用它赚钱。
- **活跃度**: main 分支约 **37 commits**、**2 open issues**、**9 PR**、**0 release**(代码仅以 PyPI 发布)。（高）
  - 解读: 提交量很小,**无 GitHub Release / 无 CHANGELOG**,更像「一次性 demo + 维护性 bot 提交(stale bot、依赖 bump)」,而非持续演进的生产系统。（中）
- **PyPI**: `autohedge` 最新 **0.1.6 / 2026-02-18**;版本号 <1.0,自我定位仍属实验期。https://pypi.org/project/autohedge/ （高）

---

## 二、架构:「自主对冲基金」具体指什么

**实质 = 4 个 LLM agent 顺序流水线 (pipeline),不是基金、不是策略研究系统。**（可信度：高，据 README/PyPI 一手描述）

- **编排框架**: 基于 **swarms**(同作者框架)做 agent 编排。（高）
- **Agent 角色**(串行):
  1. **Director Agent** — 生成交易论点/策略 thesis
  2. **Quant Agent** — 技术面/统计「分析」(实为 LLM 文本推理,非数值因子计算)
  3. **Risk Management Agent** — 仓位 sizing / 风险评估
  4. **Execution Agent** — 生成并执行订单
- **LLM**: OpenAI / Anthropic API key(README 标注为 experimental agents)。（高）
- **是否真自动下单**: **是**。当前支持 **Solana 链上全自动交易**,通过 **Jupiter API** 取价/搜索代币并下单,需配置**钱包私钥**;Coinbase「coming soon」。（高）
- **数据源**: Jupiter API(Solana DEX 聚合器)价格/代币信息。**无传统股票/期货数据源,无基本面数据**。（高）
- **回测**: ⚠️ **README / PyPI / 源码目录均未见任何回测模块**。（高,核实为「缺失」)
- **源码规模**: `autohedge/` 仅 `main.py / workers.py / prompts.py / cli.py / env_loader.py / tools/` 数个文件,**未见测试目录、未见样本外评估代码**。（中,据目录列表)

> 一句话:它把「对冲基金」四个职能名词各映射成一个 prompt 驱动的 LLM agent,串起来后直接对接链上 DEX 下单。**没有策略验证层、没有回测、没有业绩归因。**

---

## 三、可信度与风险

### 1) 营销叙事 vs 实证业绩
- **无任何样本外、扣成本(滑点/手续费/冲击成本)的真实业绩记录**。README、社媒、第三方教程一致以「几行代码搭建自主对冲基金」「2025 最火 AI 交易框架」为卖点 —— **典型营销叙事,无 P&L 曲线、无 Sharpe、无 OOS 报告**。（可信度：高,核实为「业绩证据缺失」)
- 结论:**「自主对冲基金」是营销叙事,不是被验证的盈利系统**。

### 2) 无人值守自动执行的真实风险（高严重度）
- **LLM 即决策即下单,无回测/无 OOS 把关** → 幻觉、误判直接变成真金白银的链上订单。
- **需明文配置钱包私钥** → 密钥管理 / 供应链 / prompt 注入风险;一旦泄露或 agent 被诱导,资金可被直接转走或恶意下单。
- **标的为 Solana DEX 代币** → meme/低流动性币种,滑点与 rug 风险极高;LLM「Quant Agent」并不做真实流动性/冲击成本建模。
- **版本 0.1.x、无 release、提交稀少** → 把它当生产级资金托管系统使用极不审慎。

### 3) 同作者 / 生态口碑（关键尽调项）
- swarms / Kye Gomez 生态**长期争议**,核实到的一手/准一手指控包括:被 ai16z 创始人 Shaw 公开指为 scammer、质疑其编码能力、引用 2023 Reddit 帖称代码抄袭;就「swarm」一词威胁起诉 OpenAI 索赔(被指并不实际持有商标);对 `Sora` 等仓库 namesquatting。相关 drama 见 OpenAI swarm issue #50: https://github.com/openai/swarm/issues/50 （可信度：中 —— 指控为第三方公开争议,非定罪)
- 另有 **$swarms meme 代币**(2024-12 Pump.fun 发行)绑定该生态,进一步说明**热度/代币驱动**属性强,与严肃量化无关。https://www.gate.com/learn/articles/how-swarms-became-the-ai-agent-dark-horse/6140 （中）
- 「swarms 生态常被批 star 灌水/重营销轻实证」这一榜单假设 —— **核实为「方向上成立、有公开争议支撑」**,但「star 灌水」缺直接证据,标 **中**。

---

## 四、对我们系统的可借鉴 / 反面教材

> 我们(OpenClaw):多 agent 编队 + feed + **刻意不自动下单**。

**可借鉴(少量):**
- **角色化 agent 流水线命名**(Director/Quant/Risk/Execution)清晰,prompt 模板 + 结构化 JSON 输出的工程组织可参考(`prompts.py` 分层)。
- **Risk-first 顺序**(下单前先过风控 agent)的编排次序,理念正确 —— 但他们只是「名义上」有这一层。

**反面教材(主要价值在此):**
1. **agent 编排 ≠ 实证纪律**:AutoHedge 把「有 4 个 agent」当成系统可信度的卖点,却**完全跳过回测/OOS/扣成本业绩**。这正是「编排 vs 实证」取舍的反面 —— 我们必须坚持**编排服务于可证伪的实证流程,而非替代它**。
2. **「自动下单」是风险放大器而非功能亮点**:它证明了我们**刻意不自动下单**的设计是对的。LLM 决策应止于「建议 + 可审计理由」,执行需人类闸门。
3. **大词审计**:对「自主对冲基金/企业级/institutional」一律降权 —— 看 release 节奏、测试、业绩证据,而非 star/社媒热度。
4. **私钥触手可及 = 不可接受的攻击面**:任何让 agent 直接持密钥下单的设计都应在我们这里被默认禁止。

---

## 五、一句话定位

> **AutoHedge 是一个 4-agent LLM 顺序 demo(swarms 生态、MIT、~3.5k star 但 star 可信度低),把对冲基金职能名词包装成可链上自动下单的玩具;无回测、无样本外扣成本业绩、作者生态争议缠身 —— 对我们而言主要是「编排炫技替代实证纪律 + 危险自动执行」的高价值反面教材,而非可信投研参考。**

---

### 来源清单
- AutoHedge 仓库: https://github.com/The-Swarm-Corporation/AutoHedge （高）
- AutoHedge README: https://github.com/The-Swarm-Corporation/AutoHedge/blob/main/README.md （高）
- PyPI `autohedge`: https://pypi.org/project/autohedge/ （高）
- Trendshift 收录: https://trendshift.io/repositories/25842 （中）
- swarm namesquatting / scammer 争议(OpenAI swarm issue #50): https://github.com/openai/swarm/issues/50 （中）
- $swarms 代币与生态背景: https://www.gate.com/learn/articles/how-swarms-became-the-ai-agent-dark-horse/6140 （中）
- 作者主页: https://github.com/kyegomez （高）

> 未核实项:确切实时 star 数(仅单点快照)、是否有未公开的回测/业绩、star 是否被人为灌水(无直接证据,仅生态口碑推断)。
