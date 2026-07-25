# 持续迭代日志(Continuous Development Log)
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24

Current replacement: use the maintained [documentation catalog](../README.md).

> 每小时迭代循环的台账:做了什么、验证结果、诚实结论。**新循环开工前先读本文件,避免重复劳动。**
> 体例:Cycle N(日期)| 交付 | 验证 | 结论/遗留。

## Cycle 1(2026-06-10,PR #35)
- 真 holdout 切分(R5,holdout≥2025-01-01,裁决以 holdout 为准);净值曲线+SR趋势上看板
- **修 CI 缓存陈旧 bug**(Actions 恢复昨日缓存→引擎跑旧数据;>12h 自动刷新)
- 结论:train 净SR −0.20 / holdout −0.58,样本外恶化,按 R4/R5 淘汰(诚实)

## Cycle 2(2026-06-10,PR #36)
- validation.cscv_pbo(Bailey-LdP;多种子无偏验证)+ study_pbo.py 参数网格研究
- **PBO=0.59 → 本引擎上调参改进大概率是噪声**;vol_target=4% 唯一正净SR(holdout+0.03≈0),
  不据此改默认(R5)。docs/study-pbo-2026-06-10.md
- statarb 增加 vol_target 选项(默认关)

## Cycle 3(2026-06-10,PR #36)
- factor_factory.py:预注册预算化公式因子搜索(N=304)+六门控(BY-FDR+|t|≥3+净成本)
- **0/304 过门**(最佳 |t|=1.9)——验证漏斗按设计杀掉全部噪声;接入 EOD routine
- LLM 接入只需替换 propose_candidates,门控管线不变

## Cycle 4(2026-06-10,PR #36)— 数据实效性/连贯性大审计(用户优先级)
- 修:持仓簿滞后3日(改在最后bar构簿)/ asof_data 污染(取真实数据末日)/
  index 新鲜度语义(只取引擎报告)/ **Yahoo 长区间接口比 5d 滞后1日(5d 尾部合并补丁)**
- scripts/audit_feed.py(SLA+连贯性硬规则→feed/health.json)+watchdog 升级+看板①区健康徽标
- dependabot-automerge.yml(事件层+6h清扫层;npm/pip major 拦截);清存量 PR #31-34

## Cycle 5(2026-06-10,PR #38/#41)
- **热修:requirements.txt 双钉 uvicorn(0.49+0.34)→ daily-screener 连续失败的根因**;
  修后 rs-ranks 生成(511只),13F 刷到 2026Q1
- 回撤治理阶梯(§7.4:-6/-8/-12%分级降仓+峰谷-15% kill+单日-2%冻结)+
  SSR 做空约束(Reg SHO 201 日线代理;5.4年拦截24次加空)
- 诚实结论:低波配置下阶梯零触发(月-6%≈7σ),属尾部保险管道;净SR三位小数不变
- **终审:audit_feed 全绿(0 critical/0 warn/0 info)**

## Cycle 6(2026-06-10,进行中)
- study_downshift.py:D5 容量护城河第一次实证(S&P600 分层抽样 vs 大盘,同参零调参对照)
- monthly-studies.yml:PBO+下沉研究月度定时(防参数漂移成新过拟合)
- docs/survivorship-bias-data-sources.md:免费消偏差路径=Wikipedia 时点成分+缺失率量化;
  真解=Norgate $50/月(设计文档工具栈)
- 遗留→Cycle 7:pit_membership.py(时点成分重建+缺失率曲线)

## Cycle 7(2026-06-10,用户指令:围绕 Hyperliquid 接口开发)
- 实测 API 全面板:perpDexs(9个 builder DEX)/predictedFundings(230资产跨所)/l2Book/spot
- **发现 HIP-3 合成美股/指数/私有公司永续 24/7 交易**(XYZ100 $10亿/日,SP500 $7亿,
  SPACEX/OPENAI/ANTHROPIC 私有公司永续)→ 填"美股盘后无价格发现"缺口
- scripts/hyperliquid_monitor.py(三路采集+容错回退)→ feed/crypto/state.json + feed报告;
  hyperliquid-monitor.yml 每2h;/intel 新增🧲衍生品情报卡;审计 SLA crypto_state
- docs/hyperliquid-integration.md:接口全图+缺口矩阵+路线图(隔夜缺口研究=下一个高价值项)
- 连贯性自查:监控报告不带 market_state(避免覆盖引擎完整市场状态文件)

## Cycle 8(2026-06-10)— 隔夜缺口研究(HL 路线图首项)
- study_overnight_gap.py:6 资产对 × 584 天,HIP-3 永续盘后走势 vs 次日开盘/盘中
- **Q1 代理质量成立:平均 corr +0.965**(SP500→SPY 0.981/命中96%/MAE 9bps)
  → 看板「盘后代理」有真实信息,HL 接入获得实证背书
- **Q2 信号价值不成立:盘后走势→开盘后盘中 t≈-0.6** —— 开盘价吸收隔夜信息,
  诚实否定(符合§3.8);1 次试验已登记,不进工厂
- 闹钟机制修正:Monitor 上限30分钟 → 28分钟单发心跳,两跳≈1小时汇报

## Cycle 9(2026-06-10)— PIT 时点成分 + 幸存者偏差量化
- pit_membership.py:Wikipedia 变更史(399件,溯至1976)重建任意日期 S&P500 成分;
  抽样实测流失者 Yahoo 可得性(40%可得/60%彻底无数据)
- **逐年数据缺失率:2017=16.9% / 2021(引擎起点)=10.0% / 2025=3.1%**
  → 偏差可测了;现有「净alpha≈0/负」结论消偏差后只会更差,方向稳健
- 缓存 pit_sp500.json 可复现;membership_asof() 供后续横截面研究换时点 universe

## Cycle 10(2026-06-10)— 因子工厂接入时点成分(PIT)
- factor_factory.build_panel(pit_filter=True):每个 rebal 日剔除「当日不在 S&P500」的票
  (消指数成员前视/未来赢家泄漏);剔除统计入日志
- 修一个被宽 except 吞掉的真 bug:load_pit 缺 import json → NameError 被吞返回 None
  (教训:窄化异常捕获,不吞 NameError)
- **诚实阴性发现:当前 DEMO 面板剔除 0/7360**(老牌大盘股全程在指数)→ 过滤器已装好,
  咬合点在含近年新增成分的广 universe(ABNB/APP 等)

## Cycle 11(2026-06-10)— 516 全名单 PIT 咬合量化 + 报告浏览 UI
- study_pit_bite.py:516 名单双面板对照(PIT开/关)。**咬合 11.0%**(3604/32832 名·期);
  无 PIT 把 top 候选 t 从 1.89 虚增至 2.17,部分因子变号 → 前视"白送显著性"被量化
  (两版均 0 过门,结论方向不变);NDX 成员资格无变更史,诚实标注未过滤
- /intel 新增「🗂 报告浏览」:近 20 份报告点行展开(裁决/告警/候选/贡献/notes)
- factor_factory.build_panel 支持 tickers 参数(任意 universe)

## 待办池(按优先级)
1. xs_backtest/factor_pipeline(516名单)接 PIT 过滤(那里会真正咬合)
2. 下沉层若毛增益显著:小盘 universe 的借券费/做空可行性建模
3. /intel 报告详情浏览(点击报告看全文)
4. meta-labeling(L2):numpy 逻辑回归预测「该信号这次会不会赚」,分离方向与下注
5. OFI/盘口模块(需分钟级数据,执行层 §6.5)
