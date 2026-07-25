# 成本测算 — 数据源 + Claude API + 基础设施
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the [repository README](../../../README.md); historical prose below is preserved, and moved local link targets are redirected to their current repository locations.


> 配套:[`architecture.md`](../../architecture.md) · [`../research/ai-agents-skills-market-scan.md`](../../../research/ai-agents-skills-market-scan.md)(数据源价格来源)
> ⚠️ 本文为**量级估算**(order-of-magnitude),用于决策,非财务承诺。价格为 2026-06 检索值,会变动。

按三档规模测算月成本:**1k / 10k / 100k 月活(MAU)**。

---

## 1. Claude API 单价(权威,来自 claude-api 参考)

| 模型 | 输入 $/1M tok | 输出 $/1M tok | 用途 |
|------|--------------|--------------|------|
| **Opus 4.8** (`claude-opus-4-8`) | $5.00 | $25.00 | 复杂编排/研报 |
| **Sonnet 4.6** (`claude-sonnet-4-6`) | $3.00 | $15.00 | 主力对话(性价比) |
| **Haiku 4.5** (`claude-haiku-4-5`) | $1.00 | $5.00 | 分类/情绪/轻任务 |

**省钱杠杆**:
- **Prompt caching**:缓存命中 ≈ **0.1×** 输入价;写入 1.25×(5分钟)/2×(1小时)。系统提示+工具定义固定前缀做缓存,长对话省 ~90% 输入。
- **Batch API**:非实时任务(批量情绪分析、夜间研报)**−50%**。
- **分级路由**:情绪用 Haiku/开源 FinBERT,对话用 Sonnet,只有复杂研报上 Opus。

---

## 2. 单次 AI 交互成本(假设)

主力对话用 **Sonnet 4.6**,启用缓存。单次问答假设:
- 系统提示+工具定义 ≈ 3k tok(**缓存命中**,按 0.1× 计 → 等效 0.3k)
- 本轮用户问题 + 工具返回数据 ≈ 5k tok 输入(全价)
- 回答 ≈ 1.5k tok 输出

单次成本 ≈ (0.3k+5k)/1e6 × $3 + 1.5k/1e6 × $15 ≈ **$0.0159 + $0.0225 ≈ $0.038 / 次**。

> 取整 **≈ $0.04/次对话**(Sonnet+缓存)。若用 Opus 约为其 ~1.6×(输出 $25)→ ≈ $0.06/次。情绪分类走 Haiku/FinBERT ≈ 可忽略(<$0.001/条)。

---

## 3. 三档规模月成本估算

**用量假设**:人均每月 AI 交互次数随活跃度变化;数据源走免费档优先 + 缓存。

### 📊 1k MAU(MVP/早期)
| 项 | 假设 | 月成本 |
|----|------|-------|
| AI 对话 | 1k 人 × 20 次/月 × $0.04 | **~$800** |
| 数据源 | 免费档(yfinance/AkShare/Finnhub 免费/Binance/CoinGecko) | **$0** |
| 基础设施 | 1 台中型云主机 + PG + Redis(容器化单机) | **~$100–200** |
| **合计** | | **≈ $0.9k–1k/月** |

### 📊 10k MAU(增长期)
| 项 | 假设 | 月成本 |
|----|------|-------|
| AI 对话 | 10k × 25 次 × $0.04(缓存+批处理优化后) | **~$10k** |
| 数据源 | 开始付费:Finnhub ~$50 + FMP ~$50 + Polygon/Massive ~$200 + Tushare 积分 + CoinGecko ~$129 | **~$0.5k** |
| 基础设施 | 多实例 + 托管 PG/Redis + 对象存储 + 监控 | **~$0.8k–1.5k** |
| **合计** | | **≈ $11k–12k/月** |

### 📊 100k MAU(规模化)
| 项 | 假设 | 月成本 |
|----|------|-------|
| AI 对话 | 100k × 30 次 × $0.03(规模化优化:更多缓存/Haiku 分流/批处理) | **~$90k** |
| 数据源 | 商用授权档(含重分发权,如 financialdatasets Pro $2000、Polygon Advanced、Finnhub Enterprise、Tushare 付费、多市场授权) | **~$5k–10k** |
| 基础设施 | K8s 集群 + 高可用 PG/Timescale + Redis 集群 + CDN + 可观测 | **~$8k–15k** |
| **合计** | | **≈ $103k–115k/月** |

> **AI 是主成本项**。规模越大,缓存命中率、Haiku/FinBERT 分流、批处理的优化收益越关键。

---

## 4. 成本优化清单(按收益排序)

1. **Prompt caching**(固定系统提示+工具定义)——长对话输入省 ~90%。
2. **分级模型路由**——情绪/分类 → Haiku 或开源 FinBERT;对话 → Sonnet;复杂研报 → Opus。
3. **Batch API −50%**——夜间批量研报、全市场情绪扫描。
4. **数据缓存优先**——Redis 报价缓存 + TimescaleDB 落历史,减少外部源调用与限频。
5. **限流与配额**——免费用户限 AI 次数;高频/实时行情留给付费档。
6. **token 预算**——回答 `max_tokens` 合理上限,避免冗长输出(输出 token 最贵)。

---

## 5. 关键结论

- **早期(1k)≈ $1k/月**,可控,免费数据源足够。
- **AI 调用是边际成本主项**,务必从 P3(AI 上线)起就做缓存 + 分级 + 批处理。
- **数据源在商用阶段才是大头**(因重分发授权),MVP 阶段几乎免费。
- 监控必须包含 **token 成本 / 缓存命中率 / 数据源命中率**(见 [`architecture.md`](../../architecture.md) §8)。
