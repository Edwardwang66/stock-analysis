# 收盘前报告 2026-06-18(15:15 ET / 19:15 UTC)

> 产出:claude-cowork(看板侧代班 —— Winter 本地 OpenClaw 近期未投递盘前/收盘前叙事报告,本轮补位)。
> 数据源:`feed/market/state.json`、`feed/signals/*`、`feed/intraday/latest.json`、`feed/reports/routine-2026-06-18T1735Z.json`、
> `feed/reports/hl-monitor-2026-06-18T1835Z.json`(均为本仓自动馈送,数值附 asof)。**非投资建议。**

## ① 尾盘 30 分钟关注点

- **大盘 risk-on,广度过半但不极端**:regime=`risk_on`、SPY 在 200dma 上方,20 日年化波动 16.4%,
  广度(50dma 上占比)52.2%,拥挤代理 0.109 **无拥挤告警**(`market/state.json` asof 17:35Z)。
  典型的"指数稳、强弱分化"日,尾盘重点看强势主线能否守住盘中高点而非指数方向。
- **今日主线 = 存储/半导体设备/AI 算力**:池内涨幅榜 SNDK **+10.9%**、INTC **+9.8%**、BE +9.2%、
  SMCI +8.7%、KLAC +8.4%(`intraday/latest.json` 快照 15:59 UTC / 11:59 ET,池 136 只,涨 80 / 跌 52,中位 +0.41%)。
  新高事件里 KLAC、以及 AMZN(244.32)、META(578.69)、UBER(72.49)、DIS(102.95)齐刷当日高点 ——
  **大盘科技 + 存储半导体双轮**,是今天最强的相对强度簇。
- **尾盘要盯的"是否过热"**:存储三强相对强度已极端拉伸 —— SNDK/WDC/MU 均 RS=99,
  其中 SNDK 252 日动量 +4330%、WDC +1140%、MU +770%(`rs-ranks.json` asof 06-17,w52pos 93/100/95)。
  按方法论(TD9 / SuperTrend / 缠论背驰),这类抛物线段易在尾盘出现获利了结上影,**追高风险高于趋势风险**,
  尾盘留意是否放量滞涨。
- **弱侧点名**:INFY **-8.4%**(印度 IT,跟随软件/IT 服务弱势 —— INTU/CSGP/TTD/TSCO 均处 RS 最低十分位)、
  MSTR -5.2%(加密代理,BTC 敏感)、USB 与 BIIB 双双刷**当日新低**(区域银行 + 生物科技走弱)。
- **衍生品/盘后参考**:SP500 永续 24h 仅 -0.22%(mark 7493.6,$397M/日),无方向性挤压;
  资金费极值仅出现在加密 VVV(-265%)、XMR(+113%),与美股池无直接传导(`hl-monitor-2026-06-18T1835Z`)。

## ② 当日全池复盘要点

- **风格:动量延续、非转向日**。今日看多清单(≥80)48 只、阈值 80、最高 85;权重集中在
  半导体设备(ARM/ASML/LRCX/KLAC/TER)、金融(GS/PNC/CFG/FITB/IBKR/MTB)、工业(CAT/CMI/HWM/EMR)、
  可选消费(HLT/MAR/TJX/WSM)。与 RS 榜方向一致 —— 强者恒强,**未见 06-10 那种 AI 链全板块 risk-off 的特征**。
- **领导集中在"存储 + 光互联 + 算力硬件"**:RS 前列 MU/WDC/SNDK(99)、DELL/MRVL/INTC/STX/LITE(98)、
  ARM/AMD/COHR/CIEN/TER(97);AMZN/META/UBER 新高说明大盘科技与高 beta 半导体**同向**,
  这是健康 risk-on 的结构(而非仅靠防御撑指数)。
- **落后簇:软件/IT 服务 + 部分医疗**。RS 最低十分位 INTU、CSGP、TTD、PODD、BSX、CHTR、TSCO;
  叠加今日 INFY -8.4%、BIIB 新低 —— **资金明显从软件/IT 服务流向硬件/算力**,主题轮动延续上周判断。
- **引擎(残差统计套利)如实记录**:净·扣成本 Sharpe **-0.27**、holdout(2025-01 起)Sharpe **-0.43 ≤ 0**,
  按 R4/R5 **终检不过应淘汰**;当前 33 多 / 22 空、净敞口 ≈0(-0.0007)、gross 0.456,
  空头集中在均值回归过热的 NKE/GE/PSX(`routine-2026-06-18T1735Z`)。基础引擎在免费数据上不赚钱,
  不掩饰、不叠复杂度(R10)。

## ③ 明日前瞻

- **存储/半导体设备**:领导地位明确但拉伸极端(抛物线段)。明日关注**强势能否在不破 SuperTrend 多头的前提下消化获利盘**;
  若 SNDK/WDC/MU 出现放量长上影或跌破 5 日,警惕高 beta 簇连锁回撤(动量清单天然高 beta,转向日会如实暴露)。
- **软件/IT 服务**:INFY 大跌后看是否扩散到 INTU/TTD/CSGP 等 RS 垫底名 —— 是"补跌出清"还是"继续阴跌"决定该簇能否企稳。
- **金融**:≥80 名单银行权重高,但 USB 今日创新低 —— **货币中心行 vs 区域行分化**,明日看离散度是收敛还是扩大。
- **加密代理**:MSTR -5.2%,BTC 敏感度高;永续资金费无极端股票传导,但加密若隔夜走弱会先压 MSTR/COIN 一类代理。
- **事件窗口(诚实标注)**:本地 feed 暂无已验证的明日经济日历;具体事件以次日 `intraday/overnight.json`
  (12:40 UTC 自动生成,含期货/亚欧盘/隔夜异动)为准,不在此臆测 FOMC/CPI 等具体日程。

---

> 说明:本报告为 §7 硬性时点(收盘前,deadline 19:30 UTC)的代班补位;池内个股 note 由
> `openclaw-notes.yml`(Actions 备胎)每交易日重算覆盖。数值均来自上列自动馈送,口径见 `routines/methodology.md`。非投资建议。
