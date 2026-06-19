# 08 · Polymarket Agents 调研

> 目标:评估开源项目「Polymarket agents」作为**信号源 / 情报因子**对我方诚实可证伪量化系统的借鉴价值,严格区分「在预测市场赚钱」与「用预测市场数据做信号」。
> 纪律:每条关键结论标**一手来源 + 可信度**;无法核实标「未核实」。

---

## 一、仓库事实(核实结果)

| 项目 | 核实值 | 来源 / 可信度 |
|---|---|---|
| 真实仓库 | **`github.com/Polymarket/agents`**(**官方组织** Polymarket,非社区个人 fork) | <https://github.com/Polymarket/agents> · 高 |
| Star 数 | **约 3.7k**(榜单标 ~3.5k,基本相符,略偏高;star 随时间增长属正常) | 同上 · 高 |
| License | **MIT** | 同上 · 高 |
| 主语言 | **Python(99.6%)** | 同上 · 高 |
| 描述 | "Trade autonomously on Polymarket using AI Agents";自述为"a developer framework and set of utilities for building AI agents for Polymarket" | 同上 · 高 |
| 活跃度 | **已 Archive(只读,约 2026-05-11 归档)**;主分支仅约 **7 个 commit**,约 813 forks,17 open issues | 同上 · 高(归档状态高;commit 数为单次抓取值,**中**) |

**关键判断:** 这是 **Polymarket 官方** 出品的「开发者框架/脚手架」,而非成熟生产级交易系统。已**归档**意味着官方不再维护——作为「可运行交易 bot」其生命力存疑;但作为**参考架构与 API 接法示例**仍有价值。注意榜单把它标为「交易 agent」,实际定位更接近 **SDK + 示例 CLI**。

> 同名生态还有大量社区项目(`theSchein/pamela` ElizaOS、`llSourcell/Poly-Trader`、`Dhaiwat10/polymarket-ai` 等),均非官方,**未逐一核实**,本文聚焦官方仓库。

---

## 二、架构(基于官方 README,可信度 高)

数据流:**数据采集 → 向量化/RAG → LLM 分析 → CLOB 下单**。

- **接 Polymarket API**(两条线):
  - `Gamma.py` → **Gamma API**:市场元数据、可交易市场、事件发现(只读);
  - `Polymarket.py` → **CLOB**(中央限价订单簿):鉴权、行情、**订单构建/签名/执行**(链上 DEX)。
- **决策与情报:**
  - `Chroma.py`:用 **Chroma** 向量库把**新闻 / API 数据**向量化,支持 **本地 + 远程 RAG**;
  - 数据来源:**博彩服务、新闻提供商、Web 搜索**(自述);
  - `Objects.py`:Pydantic 数据模型(trades / markets / events)。
- **LLM:** **OpenAI**(通过 API key 配置);推理编排用 **Langchain**。**未见**官方默认接入 Anthropic/本地模型(如需我方接入,LLM 层应自行替换,非项目卖点)。
- **链上信号:** 下单走链上(订单签名 `python-order-utils`),但**未核实**其是否把**链上数据本身**作为 alpha 信号——其"on-chain"主要指执行层,而非链上情报因子。
- **依赖:** `py-clob-client`、`python-order-utils`、`langchain`、`chroma`、`openai`;CLI 如 `get-all-markets`(按成交量排序)。

**诚实评估:** 决策逻辑是「**LLM + RAG 读新闻 → 判断概率 → 下注**」的直觉式 agent,**无显式校准 / 回测 / 风控框架**,与我方「诚实可证伪、反炒作」标准差距大。作为**交易策略**借鉴价值低;作为**数据接入与情报管线**借鉴价值中。

---

## 三、预测市场数据可得性 & 作为外部因子(核实结果)

**数据免费可得 —— 已核实,可信度 高:**

- **价格历史端点** `GET https://clob.polymarket.com/prices-history`:
  - **无需鉴权 / 无 API key**(OpenAPI 标 `security: []`),**免费公开读取**;
  - 参数:`market`(asset id,必填)、`startTs`/`endTs`(Unix)、`interval`(max/all/1m/1w/1d/6h/1h)、`fidelity`(分钟,默认 1);
  - 返回时间序列 `{t, p}`。来源:<https://docs.polymarket.com/api-reference/markets/get-prices-history> · 高
- 三套 API 分工:**Gamma**(市场/事件元数据,只读免鉴权)、**CLOB**(行情+下单,下单需钱包签名)、**Data**(持仓/成交)。读行情**全部免费、免 key**;**只有真正下单才需要钱包鉴权**。来源:Polymarket 官方文档汇总 · 高
- 官方 Python 客户端 `py-clob-client`(PyPI)可直接取数。可信度 高。

**作为「外部不确定性 / 事件概率因子」—— 与我方既有调研一致,可信度 中-高:**

- 校准良好:Polymarket 价格紧贴实现概率,**校准曲线接近对角线**,长周期约 90%+、临近结算 96%+ 命中。来源:multiple(StockAlarm Pro 3,587 市场分析、Fensory Brier 追踪)· 中(媒体/二手聚合)。
- **存在 favorite-longshot 偏差**:>80% 的事件实际仅约 84% 兑现(低于预期约 6pt);<10% 隐含概率事件实际发生约 14%;长周期价格**向 50% 压缩**(低估favorite),**政治类**尤甚。来源:SSRN Reichenbach & Walther;arXiv「Domain-Specific Calibration Dynamics」· 中-高(学术 preprint)。
- 含义:**可作外部事件概率因子,但不可直接当真实概率**——需做**偏差校正(longshot de-biasing)**与按 domain 分层。这与我方"可作 meta-labeling 外部预测因子"结论吻合。

---

## 四、可借鉴模式:把 Polymarket **概率接入 feed**(而非下注)

**推荐做法 —— 把 Polymarket 当「外部预测因子 / 情报」,不在其上交易:**

1. **数据管线(零成本接入):** 直接调 `prices-history` + Gamma 事件元数据(免鉴权),拉相关宏观/事件市场(FOMC 加息、CPI、大选、地缘、个股事件型市场)的**隐含概率时间序列**,落地为 feed 因子。无需 `py-clob-client` 的下单/签名部分,**只取只读 REST**,依赖极轻。
2. **作为外部不确定性 / 事件概率因子:**
   - **事件概率因子**:把"加息概率""某事件发生概率"作为外生特征,喂给主模型或 **meta-labeling** 层(过滤/加权我方信号);
   - **不确定性 / 分歧度**:用 bid-ask 价差、价格波动、成交量做**事件不确定性**代理;
   - **变化率 / 跳变**:概率的快速重定价 = 新信息冲击,可作事件驱动触发器。
3. **必做的诚实校正:** 接入前做 **longshot 去偏**(尾部概率回归校正)、按 **domain 分层**校准、对**低流动性市场打折**(薄市价格噪声大)。把 Polymarket 概率视为**有偏但信息量正**的外部先验,而非 ground truth。
4. **借鉴其工程模式(非策略):** RAG 把**新闻向量化 + 事件市场**联合检索的管线结构,可复用为"事件情报层";但其 LLM-下注决策逻辑**不予采纳**。

**坚决区分(诚实纪律):**
- 🔴 **在预测市场赚钱**(直接下注):需面对 longshot 偏差、薄流动性、**US/部分司法辖区交易受限**(官方明示)、链上执行/Gas/对手风险——非我方目标,风险敞口与合规成本高。
- 🟢 **用预测市场数据做信号**:**数据全球可读、免费、免 key**,只读接入、零交易/合规风险,**这才是对我方的真实价值**。两者必须分开评估,不可用"市场很准"为"去下注"背书。

---

## 五、一句话定位

> **`Polymarket/agents` 是官方出品但已归档的「LLM+RAG 自动下注脚手架」(MIT,~3.7k★,Python);其作为交易策略参考价值低、合规风险高,但它暴露的 Polymarket 免费免鉴权行情 API 极有价值——我方应只读接入其事件隐含概率,经 longshot 去偏与分层校准后,作为外部事件概率/不确定性因子喂入 feed 与 meta-labeling 层,而非在预测市场上下注。**

---

### 来源清单(一手优先)
- 仓库:<https://github.com/Polymarket/agents> ·(README:<https://github.com/Polymarket/agents/blob/main/README.md>)— 高
- 价格历史 API:<https://docs.polymarket.com/api-reference/markets/get-prices-history> — 高
- 校准/偏差(学术):SSRN Reichenbach & Walther <https://papers.ssrn.com/sol3/Delivery.cfm/5910522.pdf>;arXiv 2602.19520 <https://arxiv.org/pdf/2602.19520> — 中-高
- 准确率聚合(二手媒体):StockAlarm Pro、Fensory、PredictionNews — 中
- **未核实**:精确 commit/contributor 数(单次抓取)、社区同名项目细节、项目是否含链上情报因子。
