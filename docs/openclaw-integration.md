# OpenClaw 集成方案 —— 外部 Agent 编队如何为本系统做分析并把结果 POST 回 GitHub

> 目标:让一支跑在本仓之外的 **OpenClaw**(Claude / agent 编队)持续做市场与因子分析,
> 把可审计的结论以**统一契约**投递回本 GitHub 仓的 `feed/`,经 CI 安全闸门校验后并入,
> 供做多做空引擎与 `/intel` 情报看板消费。
>
> **关于 "OpenClaw" 的假设(可替换)**:本方案把 OpenClaw 视为一个**与本仓解耦的自治 agent 服务**
> (自托管的 Claude agent 编队,或任意能调用 LLM + 数据的 worker)。契约是 agent 无关的 ——
> 任何外部系统按本规范投递即可,无需是某个特定产品。

本方案对齐设计文档(US Equity Mid-Frequency Hybrid Quant System v1.0):
**LLM/agent 是研究放大器,不是决策者(R6)**;一切产出须可审计、可门控、可删除、带 kill-switch。

---

## 0. 一图流

```
┌─────────────────────────── OpenClaw(本仓之外)───────────────────────────┐
│  Orchestrator(调度)                                                       │
│    ├─ residual-analyst    残差/协整健康度、配对候选                          │
│    ├─ crowding-monitor    拥挤/同质化/资金流(尾部风险 §7.2)                 │
│    ├─ event-risk          财报/FOMC/CPI/指数重构/SSR 事件标注                │
│    ├─ factor-factory      可审计公式因子挖掘(进化式,六门控自检)            │
│    └─ red-team            对每条结论做对抗核验(Profit Mirage / 五偏差)      │
│  每个 agent 产出 → 汇总为 1 份 report.schema.json → HMAC 签名               │
└───────────────────────────────────┬───────────────────────────────────────┘
            POST(三选一)             │
   ┌─────────────┬───────────────────┴───────────────┐
   ▼             ▼                                   ▼
github-api    repository_dispatch                 PR(人审)
PUT inbox     event=openclaw-report               改 feed/inbox/**
   └─────────────┴───────────────────┬───────────────┘
                                     ▼
                 CI 闸门 feed-validate.yml + scripts/validate_feed.py
                 (schema ✓ + 签名 ✓ + 边界 ✓ + 幂等 ✓)→ 并入 feed/reports/
                                     ▼
                 feed/index.json 重建 → 静态网页 /intel 看板消费
```

---

## 1. OpenClaw 端:怎么调用 agent 做分析

### 1.1 Agent 名册(对齐设计文档「LLM 委员会」+ 流 B 需求)

| agent_role | 职责 | 输入 | 产出(写进 report) |
|---|---|---|---|
| `residual-analyst` | 残差均值回归健康度:κ/半衰期漂移、Hurst、协整断裂预警 | 价格、行业 ETF | `alerts`(协整断裂)、`market_state.residual_dispersion` |
| `crowding-monitor` | 拥挤/同质化:同类持仓重叠、short interest、Amihud、ETF 资金流 | 持仓/流动性数据 | `market_state.crowding_*`、`alerts`(crowding) |
| `event-risk` | 事件日历:财报、FOMC/CPI、指数重构、SSR 触发标的 | 日历、SEC | `alerts`(event-risk),**仅标注/回避,不做方向 alpha**(D4) |
| `factor-factory` | 进化式挖掘**可审计公式因子**(Alpha101 风格) | 因子/收益面板 | `factory_candidates[]`(含六门控自检结果) |
| `red-team` | 对抗核验:记忆性前视、五偏差、增量正交 IC 是否成立 | 上述全部 | 覆写 `decision=reject` + `note` |

### 1.2 调度(Orchestrator)

- **节奏**:盘中每小时跑 `residual-analyst` + `crowding-monitor` + `event-risk`;
  收盘后跑 `factor-factory` + `red-team`(重活)。可用 cron / 队列。
- **委员会模式(可选)**:`factor-factory` 产候选 → `red-team` 匿名互评 → Orchestrator 综合,
  对应设计文档 §2「LLM Council」三阶段(并行作答 → 互评去偏 → 主席综合)。
- **时序防火墙(R6 硬约束)**:任何 LLM 候选必须在**模型训练截止日之后**的数据上验证增量 IC;
  RAG 文档打 PIT 时间戳;**锁定模型版本**(写进 `producer.model`),版本变更视为新策略重验。

### 1.3 六门控(`factor-factory` 自检,缺一即 `reject`)

对应设计文档 §6.2.3 / §6.7,每条候选填进 `factory_candidates[]`:

1. 预注册搜索空间与试验次数 → `pbo` (CSCV) < 0.05–0.10
2. `incremental_ic` 增量正交 IC(对现有组合回归后残差 IC 仍显著)
3. 相依 FDR(Benjamini-Yekutieli / Romano-Wolf)→ `t_stat` ≳ 3
4. 广度按特征值参与率折算(非按个数)
5. `hypothesis` 事前经济机制(非事后编故事)
6. 扣真实成本后 IR 存活

`passed_gates=true` 才允许 `decision ∈ {accept, shadow}`;否则 `reject`。
**门控由本仓 CI 与 L6 复核,OpenClaw 的自检不被信任为终判。**

---

## 2. 投递端:怎么把结果 POST 回这个 GitHub

所有投递都是一份符合 [`feed/schema/report.schema.json`](../feed/schema/report.schema.json) 的报告,
`kind="openclaw"`,**必须带 HMAC 签名**。参考实现见 [`scripts/openclaw_client.py`](../scripts/openclaw_client.py)。

### 2.1 通道 A — GitHub Contents API(推荐,最简单)

把报告 PUT 到 `feed/inbox/<id>.json`(建议投到专用分支 `openclaw-inbox` 再开 PR,或直接走 PR)。

```bash
export FEED_HMAC_SECRET=...        # 与仓库 Secrets 同一把共享密钥
export GITHUB_TOKEN=...            # 细粒度 PAT / GitHub App,最小权限:contents:write(仅本仓)
python scripts/openclaw_client.py --mode github-api --role residual-analyst
```

CI(`feed-validate.yml`,PR 触发)校验通过后合并 PR → `validate_feed.py --merge` 并入 `feed/reports/`。

### 2.2 通道 B — repository_dispatch(无文件,事件携带 payload)

```bash
curl -X POST https://api.github.com/repos/edwardwang66/stock-analysis/dispatches \
  -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
  -d '{"event_type":"openclaw-report","client_payload":{"report": <签名后的报告 JSON>}}'
```

`feed-validate.yml`(repository_dispatch 触发)落盘 → 校验 → 合并 → 推送。适合无需保留 PR 痕迹的高频投递。

### 2.3 通道 C — 直接开 PR(需人审的重要结论)

OpenClaw 自己 fork/branch,把文件加到 `feed/inbox/**` 开 PR;CI 校验 + 人工审阅后合并。
适合 `factor-factory` 的 `accept` 候选(影响实盘,应有人 gate)。

### 2.4 鉴权与最小权限

- **GitHub App / 细粒度 PAT**,权限仅 `contents: read/write`,**仅限本仓** `edwardwang66/stock-analysis`。
- 共享密钥 `FEED_HMAC_SECRET` 存仓库 **Settings → Secrets and variables → Actions**;OpenClaw 侧同值。
- 密钥轮换:`signature.key_id` 标识密钥版本,便于灰度轮换。

---

## 3. 本仓端:安全闸门(把外部投递当不可信输入)

`scripts/validate_feed.py`(被 `feed-validate.yml` 调用)逐项拒绝:

| 检查 | 拒绝条件 |
|---|---|
| Schema | 不符合 `report.schema.json`(draft-07) |
| 签名 | `kind=openclaw` 无有效 HMAC-SHA256 签名 |
| 冒充 | 外部投递使用 `kind=routine`(冒充本仓任务) |
| 体量 | 文件 >512KB / positions >400 / candidates >50 |
| 幂等 | `id` 已存在于 `feed/reports/`(重复投递) |

> **提示词注入防御**:报告里的 `notes` / `hypothesis` / `message` 等自由文本被视为**数据**,
> 只在看板展示,**绝不作为指令执行**;任何 `decision=accept` 的因子仍须过本仓 L6 与人审,
> OpenClaw 无权直接改动交易逻辑或权重。

---

## 4. 报告契约(关键字段速查)

完整定义见 schema。一份最小 OpenClaw 报告:

```json
{
  "schema_version": "1.0",
  "id": "openclaw-residual-analyst-2026-06-06T1400Z",
  "kind": "openclaw",
  "produced_at": "2026-06-06T14:00:11Z",
  "asof_data": "2026-06-05",
  "producer": { "name": "openclaw-agent:residual-analyst", "model": "claude-opus-4-8",
                "agent_role": "residual-analyst", "run_url": "https://..." },
  "market_state": { "crowding_proxy": 0.41, "crowding_alert": false },
  "factory_candidates": [ { "expr": "...", "hypothesis": "...", "incremental_ic": 0.011,
      "post_cutoff": true, "pbo": 0.18, "t_stat": 2.1, "passed_gates": false, "decision": "reject" } ],
  "alerts": [ { "level": "info", "code": "event-risk", "message": "下周 FOMC + CPI" } ],
  "contribution": { "type": "new_factor", "summary": "1 条候选(被门控拒绝)+ 事件提示" },
  "signature": { "alg": "HMAC-SHA256", "key_id": "default", "value": "<hex>" }
}
```

---

## 5. 看板如何反映 OpenClaw 的贡献

`/intel` 情报看板(见 [`docs/self-improving-alpha-loop.md`](self-improving-alpha-loop.md)):
- **②获取了多少信息** 的「来源数 / by_producer」会列出每个 OpenClaw agent 投了多少份。
- **⑦贡献日志** 列出每条投递的 `contribution.type / summary` 与净 Sharpe 变化 —— 即「怎么帮助到你了」。
- **⑥LLM 假设工厂候选** 展示每条候选的六门控结果与 `decision`,被拒的清楚标注原因。

---

## 6. 落地清单(给 OpenClaw 运维)

- [ ] 在仓库 Secrets 配 `FEED_HMAC_SECRET`(本仓 CI 与 OpenClaw 共享)。
- [ ] 准备细粒度 PAT / GitHub App(`contents:rw`,仅本仓)。
- [ ] 实现 5 个 agent 的分析逻辑,产出填进 `report.schema.json`。
- [ ] 用 `scripts/openclaw_client.py` 做投递(或按 §2 自实现,签名算法见 `feed_lib.sign_report`)。
- [ ] 时序防火墙:锁模型版本、PIT RAG、截止后验证 —— 否则 CI/L6 会拒。
- [ ] 监控:OpenClaw 侧记录每次投递的 `id` 与 CI 结果,失败重试(幂等键=id,安全)。
