# 差异化定位分析 — 我们凭什么赢
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [repository README](../../../README.md); historical prose below is preserved, and moved local link targets are redirected to their current repository locations.


> 配套:[`../research/ai-agents-skills-market-scan.md`](../../../research/ai-agents-skills-market-scan.md)(竞品全景)· [`architecture.md`](../../architecture.md)

平台定位:**多市场(美/港/A/加密)统一数据看板 + AI 助手**。本文回答:市面竞品已经很多,**我们的切入点和差异化在哪**。

---

## 1. 竞品分层与各自短板

| 竞品类型 | 代表 | 强项 | 对本平台的启示/短板 |
|---------|------|------|---------------------|
| 对话式投研 | Fiscal.ai、Perplexity Finance | AI 问答 + 全球财报库 | 偏美股;**多市场(尤其 A/港)+ 加密统一**弱 |
| 券商内置 AI | 富途、老虎、Public Alpha | 行情+交易+AI 一体 | 绑定开户;**非券商的中立看板**有空间 |
| 中国大模型投研 | 东方财富妙想、同花顺问财 | A股深、中文强、自然语言选股 | **只做 A股**,基本不覆盖美/港/加密 |
| AI 评分/选股 | Danelfin、Kavout、Tickeron | 量化评分、信号 | 黑盒、偏美股、订阅贵 |
| 社交投资 | 雪球、StockTwits | 社区/情绪 | AI 轻;看板与数据深度弱 |
| 开源框架 | OpenBB、TradingAgents | 强大但**面向开发者** | 普通用户用不了,可作我们的底层能力 |

**核心空白**:几乎没有一个产品同时做到「**四市场统一 + 中立(不绑券商)+ AI 看板(非黑盒评分)+ 普通用户可用**」。

---

## 2. 我们的差异化支点(4 条)

1. **真·多市场统一视图**
   把美股/港股/A股/加密放进**同一套 Symbol 模型与同一块看板**,支持跨市场对比(如"茅台 vs 帝亚吉欧 vs BTC 近一年走势")。这是单市场玩家(妙想/问财=A股,Fiscal=美股)结构上做不到的。

2. **中立 + 聚合,不绑券商**
   不卖交易、不导流开户,做"看行情/查数据/问 AI"的中立工具。用户不必为看四个市场装四个 App。

3. **可解释的 AI,而非黑盒评分**
   不学 Danelfin 给一个不透明的"AI Score";AI 回答**必须带数据来源与引用**(RAG + 工具调用),数值来自真实行情而非臆测。建立信任。

4. **复用开源能力,快速追平**
   底层直接站在 OpenBB / TradingAgents / FinBERT / 现成 MCP 的肩膀上,把"开发者才会用"的能力产品化给普通用户——研发省、上线快。

---

## 3. 一句话定位

> **"一个看板看懂全球四大市场,问 AI 得到有出处的答案。"**
> (A neutral, multi-market dashboard where AI answers come with sources.)

---

## 4. 目标用户与场景

| 用户 | 痛点 | 我们提供 |
|------|------|---------|
| 跨市场散户(同时炒美/港/A/币) | 要装 4 个 App、来回切 | 一块看板全看 |
| 中文投资者看美股/加密 | 英文工具门槛高 | 中文 AI + 中文界面 |
| 轻度研究者 | 不会用 OpenBB/写代码 | 自然语言问出研报级答案 |

---

## 5. 不做什么(边界,避免变成"又一个全家桶")

- **不做交易/经纪**(合规重、且偏离看板定位)。
- **不做投资建议/荐股**(法律风险);只做信息与分析,全站"非投资建议"。
- **不与彭博/万得拼机构深度**;主打零售/中文/多市场可达性。

---

## 6. 风险与应对

| 风险 | 应对 |
|------|------|
| 巨头(东方财富/Perplexity)横向扩市场 | 先用"中立 + 中文 + 加密"形成差异;速度取胜 |
| 数据合规/重分发(见 [`compliance.md`](../../compliance.md)) | 免费源仅自用,商用采购授权 |
| AI 成本(见 [`cost-estimate.md`](cost-estimate-2026-06.md)) | 缓存 + 分级模型 + 批处理控成本 |
