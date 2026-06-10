"""流 B —— 条件因子统计套利 残差均值回归 做多/做空引擎(系统核心 alpha)。

严格对齐设计文档(US Equity Mid-Frequency Hybrid Quant System v1.0):
  §3.1 Alpha 三分法    : 真 alpha 来自定价错误(残差均值回归),不是风险溢价 beta。
  §6.2.2 流 B 三步     : ①条件因子残差 rᵢ=βᵢᵀf+εᵢ → ②OU s-score 信号 → ③扣成本仓位。
  §6.5 / costs.py      : 平方根冲击律 + 价差 + ADV 参与率容量地板。
  §7.3 协整断裂熔断 D13: Hurst>0.55 / κ 滚动下降 / 价差持续偏离 → 立即砍仓,禁止向下加仓。
  §7.1 分层限额        : 单股 ≤5%、行业中性、毛杠杆封顶、美元中性。
  §6.7 / validation.py : Deflated Sharpe 作过拟合校验;「净·压力成本」是唯一计价货币(R4)。

与旧 xs_portfolio.py 的区别:旧的是 raw 因子分层多空(流 A,毛口径、含幸存者偏差);
本引擎是流 B 残差套利、全程扣成本、带熔断与容量地板 —— 这是报告要求「优化」的做多做空逻辑。

依赖:numpy + 本目录 data.py / costs.py / validation.py。纯研究层,诚实声明见文末。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np

import costs
import data as datamod
import validation as val

HERE = os.path.dirname(os.path.abspath(__file__))

# GICS 行业 -> SPDR 行业 ETF(作为「条件因子」回归自变量,Avellaneda-Lee 用 ETF 收益做因子)
SECTOR_ETF = {
    "Information Technology": "XLK", "Health Care": "XLV", "Financials": "XLF",
    "Consumer Discretionary": "XLY", "Communication Services": "XLC",
    "Industrials": "XLI", "Consumer Staples": "XLP", "Energy": "XLE",
    "Utilities": "XLU", "Real Estate": "XLRE", "Materials": "XLB",
}
SECTOR_ETFS = sorted(set(SECTOR_ETF.values()))

# 演示用流动大盘 universe(跨行业、ADV 大,容量地板下仍可成交);可被 run() 覆盖。
# 广度是绑定约束(§3.2 基本定律),故取 ~120 只以获得有效广度 ~50–150 的下限。
DEMO_UNIVERSE = [
    # Information Technology
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "CSCO", "ACN",
    "INTC", "QCOM", "TXN", "IBM", "AMAT", "MU", "ADI", "LRCX", "KLAC", "NOW", "INTU",
    # Communication Services
    "GOOGL", "META", "DIS", "VZ", "T", "NFLX", "TMUS", "CMCSA", "CHTR",
    # Consumer Discretionary
    "AMZN", "HD", "MCD", "NKE", "LOW", "SBUX", "TSLA", "BKNG", "TJX", "ORLY", "MAR",
    # Consumer Staples
    "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "CL", "MO", "PM", "TGT",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SCHW", "SPGI", "CB", "PGR", "PNC", "USB",
    # Health Care
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY", "AMGN", "MDT", "GILD", "CVS", "ISRG",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX",
    # Industrials
    "CAT", "GE", "HON", "UNP", "BA", "RTX", "DE", "LMT", "UPS", "ADP", "ETN", "EMR",
    # Materials
    "LIN", "SHW", "APD", "FCX", "NEM", "ECL",
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP",
    # Real Estate
    "AMT", "PLD", "EQIX", "PSA", "O",
]


@dataclass
class StatArbParams:
    start_year: int = 2021          # 回测起始年(留 1 年预热)
    window: int = 60                # 残差/OU 估计窗口(交易日)
    hl_min: float = 5.0             # 半衰期下限(交易日),设计文档 §6.2.2 取 5–25
    hl_max: float = 25.0
    s_open: float = 1.25            # |s| ≥ 此值才建仓(Avellaneda-Lee 经典阈值)
    s_close: float = 0.5            # |s| < 此值才平仓(滞回:建/平不同阈值,抑制频繁翻仓)
    s_cap: float = 2.0              # s 截断,防极端值主导
    hurst_max: float = 0.55         # >此值视为协整断裂(漂向随机游走),熔断(§7.3)
    name_cap: float = 0.04          # 单股权重上限(占 NAV),硬限额 §7.1
    sector_cap: float = 0.12        # 行业净暴露上限(占 NAV)
    gross_leverage: float = 1.0     # 目标毛杠杆(sum|w|);中频统计套利适宜偏低
    max_positions: int = 80         # 头部信号上限(§3.2 有效广度 ~50–150;广度本身是 alpha)
    trade_rate: float = 0.15        # aim 组合:每日向目标收敛比例(Garleanu-Pedersen,§6.5/D2),偏粘以匹配半衰期
    no_trade_band: float = 0.003    # 无交易带:|Δw|<此值不动(抑制碎单换手)
    neutral_band: float = 0.03      # 净敞口超此值才钉回美元中性(避免每日扰动全簿)
    aum: float = 25e6               # 资产规模($),用于容量地板与冲击成本
    max_participation: float = 0.05 # 单日参与率上限(占 ADV)
    half_spread_bps: float = 5.0    # 单边价差成本(bps)
    impact_Y: float = 0.5           # 平方根冲击系数
    n_trials: int = 200             # 申报试验次数(用于 Deflated Sharpe;诚实登记,见 §6.7)
    holdout_start: str = "2025-01-01"  # 真 holdout 起点(R5):此日(含)之后只做终检,不据其调参
    vol_target: float | None = None  # 年化波动目标(如0.04);None=关闭。开启则按近21日实现波动缩放毛杠杆(§6.3)
    governance: bool = True          # 回撤治理阶梯(§7.4):月内-6%/-8%/-12%分级降仓,峰谷-15% kill,单日-2%冻结
    factors: list[str] = field(default_factory=lambda: ["SPY", "SECTOR"])


# ----------------------------- 数据对齐 -----------------------------

def _aligned(ticker: str, dates: np.ndarray, dmap: dict | None = None):
    """把单标的对齐到主日历 dates,返回 (adj[], vol[], low[], close_raw[]),缺失为 nan。"""
    d = datamod.load(ticker)
    if not d or len(d.get("adjclose", [])) < 260:
        return None
    ts = np.asarray(d["ts"], dtype=np.int64)
    adj = np.asarray(d["adjclose"], dtype=float)
    vol = np.asarray(d["volume"], dtype=float)
    low = np.asarray(d.get("low", d["adjclose"]), dtype=float)
    craw = np.asarray(d.get("close", d["adjclose"]), dtype=float)
    m = {int(t): i for i, t in enumerate(ts)}
    a = np.full(len(dates), np.nan)
    v = np.full(len(dates), np.nan)
    lo = np.full(len(dates), np.nan)
    cr = np.full(len(dates), np.nan)
    for k, dt in enumerate(dates):
        i = m.get(int(dt))
        if i is not None:
            a[k], v[k], lo[k], cr[k] = adj[i], vol[i], low[i], craw[i]
    return a, v, lo, cr


def _returns(adj: np.ndarray) -> np.ndarray:
    r = np.full_like(adj, np.nan)
    r[1:] = adj[1:] / adj[:-1] - 1.0
    return r


def load_market(tickers: list[str], start_year: int):
    """加载主日历 + 因子(SPY/行业 ETF)+ 标的的对齐收益/ADV。"""
    spy = datamod.load("SPY")
    if not spy:
        raise SystemExit("缺少 SPY 缓存,请先 `python data.py` 或运行 build_demo_cache()。")
    sts = np.asarray(spy["ts"], dtype=np.int64)
    import datetime as _dt
    keep = np.array([_dt.datetime.utcfromtimestamp(int(t)).year >= start_year - 1 for t in sts])
    dates = sts[keep]
    spy_adj = np.asarray(spy["adjclose"], dtype=float)[keep]
    spy_ret = _returns(spy_adj)

    # 行业 ETF 因子收益
    sector_ret = {}
    for etf in SECTOR_ETFS:
        al = _aligned(etf, dates)
        sector_ret[etf] = _returns(al[0]) if al else np.full(len(dates), np.nan)

    sectors = json.load(open(os.path.join(HERE, "sector_map.json")))
    names = {}
    for tk in tickers:
        al = _aligned(tk, dates)
        if al is None:
            continue
        adj, vol, low, craw = al
        ret = _returns(adj)
        sec = sectors.get(tk, "")
        etf = SECTOR_ETF.get(sec, "SPY")
        adv = np.full(len(dates), np.nan)             # 滚动 ADV($)
        notional = adj * vol
        for k in range(len(dates)):
            lo = max(0, k - 20)
            seg = notional[lo:k + 1]
            seg = seg[np.isfinite(seg)]
            adv[k] = seg.mean() if len(seg) else np.nan
        # SSR(Reg SHO Rule 201,§6.5):日内低点较前收跌 ≥10% 触发,当日+次日生效。
        # 日线代理:low[k]/close_raw[k-1] - 1 ≤ -10%(无逐笔数据,保守近似)。
        ssr = np.zeros(len(dates), dtype=bool)
        trig = np.zeros(len(dates), dtype=bool)
        for k in range(1, len(dates)):
            if np.isfinite(low[k]) and np.isfinite(craw[k - 1]) and craw[k - 1] > 0:
                trig[k] = (low[k] / craw[k - 1] - 1.0) <= -0.10
            ssr[k] = trig[k] or trig[k - 1]
        names[tk] = {"ret": ret, "adj": adj, "adv": adv, "sector": sec, "etf": etf, "ssr": ssr}
    return dates, spy_ret, sector_ret, names


# ----------------------------- 信号 -----------------------------

def residual_signal(name_ret: np.ndarray, spy_ret: np.ndarray, etf_ret: np.ndarray,
                    k: int, p: StatArbParams) -> dict | None:
    """在日期索引 k 上,用 [SPY, 行业 ETF] 作条件因子回归求残差,拟合 OU 得 s-score。"""
    lo = k - p.window + 1
    if lo < 1:
        return None
    y = name_ret[lo:k + 1]
    f1 = spy_ret[lo:k + 1]
    f2 = etf_ret[lo:k + 1]
    mask = np.isfinite(y) & np.isfinite(f1) & np.isfinite(f2)
    if mask.sum() < p.window * 0.8:
        return None
    y, f1, f2 = y[mask], f1[mask], f2[mask]
    if "SECTOR" in p.factors and np.isfinite(f2).all():
        X = np.vstack([np.ones_like(f1), f1, f2]).T
    else:
        X = np.vstack([np.ones_like(f1), f1]).T
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    Xcum = np.cumsum(resid)                 # 残差累积过程(OU 的状态变量)
    ou = val.ou_from_ar1(Xcum)
    if ou is None:
        return None
    hurst = val.hurst_exponent(Xcum, max_lag=min(20, len(Xcum) // 2))
    ou["hurst"] = hurst
    ou["beta_mkt"] = float(coef[1]) if len(coef) > 1 else float("nan")
    return ou


def book_for_day(dates, spy_ret, sector_ret, names, k: int, p: StatArbParams,
                 prev_w: dict, active: set):
    """构造第 k 日的目标权重簿,并以 aim 组合向目标平滑收敛。

    流程:信号 → 滞回开/平仓 → 熔断 → 目标 tilt → 美元/行业中性 + 限额 + 容量地板
          → Garleanu-Pedersen aim 平滑(只走 trade_rate 比例,无交易带过滤碎单)。
    返回 (weights, diag, breaker, new_active)。
    """
    tilt, diag, breaker = {}, {}, {}
    sig_sigma, sig_adv = {}, {}
    new_active = set()
    for tk, nm in names.items():
        sig = residual_signal(nm["ret"], spy_ret, sector_ret.get(nm["etf"], spy_ret), k, p)
        if sig is None:
            continue
        diag[tk] = sig
        win = nm["ret"][max(1, k - p.window + 1):k + 1]
        win = win[np.isfinite(win)]
        sig_sigma[tk] = float(np.std(win)) if len(win) > 5 else 0.02
        sig_adv[tk] = float(nm["adv"][k]) if np.isfinite(nm["adv"][k]) else 0.0
        s = sig["s_score"]
        # 熔断:协整断裂(§7.3 / D13)——立即标记平仓,禁止持有等待
        if not np.isfinite(sig["hurst"]) or sig["hurst"] > p.hurst_max:
            breaker[tk] = f"hurst={sig['hurst']:.2f}>{p.hurst_max}"
            continue
        if not (p.hl_min <= sig["halflife_days"] <= p.hl_max):
            breaker[tk] = f"halflife={sig['halflife_days']:.1f} 出区间[{p.hl_min},{p.hl_max}]"
            continue
        if not np.isfinite(s) or abs(s) > p.s_cap + 1.5:   # 价差极端持续 -> 价值陷阱,回避
            breaker[tk] = f"s={s:.2f} 极端,疑价值陷阱"
            continue
        # 滞回:已持仓则 |s|>s_close 继续持有;未持仓则需 |s|≥s_open 才新建
        was = tk in active
        if was and abs(s) >= p.s_close:
            keep = True
        elif (not was) and abs(s) >= p.s_open:
            keep = True
        else:
            keep = False
        if keep:
            tilt[tk] = -float(np.clip(s, -p.s_cap, p.s_cap))  # s>0 做空、s<0 做多

    # 只交易头部信号:按 |tilt|(=|clip(s)|)取前 max_positions
    if len(tilt) > p.max_positions:
        top = sorted(tilt, key=lambda t: -abs(tilt[t]))[:p.max_positions]
        tilt = {t: tilt[t] for t in top}
    new_active = set(tilt)

    # ---- 目标簿:中性化 + 限额 + 容量地板 ----
    target = {}
    if tilt:
        tks = list(tilt)
        w = np.array([tilt[t] for t in tks])
        secs = np.array([names[t]["sector"] for t in tks])
        w = w - w.mean()                                    # 美元中性
        for s in set(secs):                                 # 软行业中性:仅 ≥3 只的行业内去均值
            idx = secs == s
            if idx.sum() >= 3:
                w[idx] = w[idx] - w[idx].mean()
        gross = np.abs(w).sum()
        if gross > 0:
            w = w * (p.gross_leverage / gross)
        w = np.clip(w, -p.name_cap, p.name_cap)             # 单股限额
        for s in set(secs):                                 # 行业净暴露限额
            idx = secs == s
            net = w[idx].sum()
            if abs(net) > p.sector_cap:
                w[idx] = w[idx] - (net - np.sign(net) * p.sector_cap) / max(1, idx.sum())
        adv = np.array([sig_adv[t] for t in tks])
        w = costs.capacity_cap_weights(w, adv, p.aum, p.max_participation)
        target = {t: float(wi) for t, wi in zip(tks, w)}

    # ---- aim 平滑:从 prev_w 向 target 走 trade_rate;熔断/退出名目标=0 ----
    smoothed = {}
    for t in set(prev_w) | set(target):
        cur = prev_w.get(t, 0.0)
        tgt = target.get(t, 0.0)
        nw = cur + p.trade_rate * (tgt - cur)
        # 无交易带只对「持有中(目标非 0)」生效;退出/熔断名必须让其衰减归零,否则碎仓被冻住
        if tgt != 0.0 and abs(nw - cur) < p.no_trade_band:
            nw = cur
        if abs(nw) < 0.0008:                                # 碎仓阈值:小于此值直接清掉,完成退出
            nw = 0.0
        if abs(nw) > 1e-6:
            smoothed[t] = nw
    # 对「实现簿」做条件美元中性:仅当净敞口超 neutral_band 才钉回(避免每日扰动全簿、虚增换手)
    weights = {}
    if smoothed:
        tks2 = list(smoothed)
        w2 = np.array([smoothed[t] for t in tks2])
        if abs(w2.sum()) > p.neutral_band:
            w2 = w2 - w2.sum() / len(w2)                    # 单次平移消除方向 beta
        w2 = np.clip(w2, -p.name_cap, p.name_cap)
        weights = {t: float(wi) for t, wi in zip(tks2, w2) if abs(wi) > 1e-6}

    # SSR(Reg SHO Rule 201):触发日+次日,空头腿只许持有/回补、不许加空(§6.5)
    ssr_blocked = 0
    for t in list(weights):
        if names[t]["ssr"][k] and weights[t] < prev_w.get(t, 0.0) and weights[t] < 0:
            weights[t] = min(prev_w.get(t, 0.0), 0.0)
            if abs(weights[t]) < 1e-6:
                del weights[t]
            ssr_blocked += 1

    for t, sig in diag.items():
        sig["sigma_d"] = sig_sigma.get(t, 0.02)
        sig["adv_usd"] = sig_adv.get(t, 0.0)
    return weights, diag, breaker, new_active, ssr_blocked


# ----------------------------- 回测主循环 -----------------------------

def run(tickers: list[str] | None = None, p: StatArbParams | None = None,
        verbose: bool = True) -> dict:
    p = p or StatArbParams()
    tickers = tickers or DEMO_UNIVERSE
    import datetime as _dt
    dates, spy_ret, sector_ret, names = load_market(tickers, p.start_year)
    start_k = next((k for k, d in enumerate(dates)
                    if _dt.datetime.utcfromtimestamp(int(d)).year >= p.start_year), p.window)
    start_k = max(start_k, p.window + 1)

    prev_w: dict[str, float] = {}
    active: set = set()
    net_rets, gross_rets, turnovers, n_pos, breaker_counts = [], [], [], [], []
    ret_ts: list[int] = []          # 每条净收益对应的实现日(t+1)时间戳
    # 回撤治理状态(§7.4 阶梯;全部因果:只用已实现净收益)
    import datetime as _dt2
    equity = 1.0
    global_peak = 1.0
    month_peak = 1.0
    cur_month = None
    killed_month = None             # 峰谷 -15% kill-switch:清仓至当月结束(模拟口径,R1)
    gov_days = {"yellow": 0, "orange": 0, "red": 0, "kill": 0, "daily_freeze": 0}
    ssr_blocks_total = 0

    for k in range(start_k, len(dates) - 1):
        weights, diag, breaker, active, ssr_blocked = book_for_day(
            dates, spy_ret, sector_ret, names, k, p, prev_w, active)
        ssr_blocks_total += ssr_blocked
        # vol-scaling(§6.3,因果:只用过去净收益):实现波动高于目标则等比降杠杆
        if p.vol_target and len(net_rets) >= 21:
            rv = float(np.std(net_rets[-21:], ddof=1)) * np.sqrt(252)
            if rv > 1e-6:
                scale = float(np.clip(p.vol_target / rv, 0.5, 1.5))
                weights = {t: w * scale for t, w in weights.items()}

        # ---- 回撤治理阶梯(§7.4):月内回撤 -6%/-8%/-12% 分级降仓;峰谷 -15% kill ----
        month = _dt2.datetime.utcfromtimestamp(int(dates[k])).strftime("%Y-%m")
        if month != cur_month:
            cur_month = month
            month_peak = equity
        mtd_dd = equity / month_peak - 1.0
        pv_dd = equity / global_peak - 1.0
        if p.governance:
            if killed_month == month or pv_dd <= -0.15:
                if killed_month != month and pv_dd <= -0.15:
                    killed_month = month
                weights = {}
                gov_days["kill"] += 1
            elif net_rets and net_rets[-1] < -0.02:
                weights = dict(prev_w)              # 单日亏 >2%:冻结一日,不下新单
                gov_days["daily_freeze"] += 1
            elif mtd_dd <= -0.12:
                weights = {t: w * 0.3 for t, w in weights.items()}
                gov_days["red"] += 1
            elif mtd_dd <= -0.08:
                weights = {t: w * 0.5 for t, w in weights.items()}
                gov_days["orange"] += 1
            elif mtd_dd <= -0.06:
                weights = {t: w * 0.75 for t, w in weights.items()}
                gov_days["yellow"] += 1
        # 实现下一日收益(t->t+1)
        gross_r = 0.0
        for t, w in weights.items():
            r1 = names[t]["ret"][k + 1]
            if np.isfinite(r1):
                gross_r += w * r1
        # 换手成本
        union = set(weights) | set(prev_w)
        dw, sig_d, adv_d = [], [], []
        for t in union:
            dw.append(weights.get(t, 0.0) - prev_w.get(t, 0.0))
            sig_d.append(diag.get(t, {}).get("sigma_d", 0.02))
            adv_d.append(diag.get(t, {}).get("adv_usd", names[t]["adv"][k] if np.isfinite(names[t]["adv"][k]) else 0.0))
        cost = costs.portfolio_turnover_cost(np.array(dw), np.array(sig_d), np.array(adv_d),
                                             p.aum, p.half_spread_bps, p.impact_Y)
        turnover = float(np.abs(dw).sum())
        net_rets.append(gross_r - cost)
        gross_rets.append(gross_r)
        ret_ts.append(int(dates[k + 1]))
        equity *= (1 + net_rets[-1])
        global_peak = max(global_peak, equity)
        month_peak = max(month_peak, equity)
        turnovers.append(turnover)
        n_pos.append(len(weights))
        breaker_counts.append(len(breaker))
        prev_w = weights

    net = np.array(net_rets)
    gross = np.array(gross_rets)
    rep = _summarize(net, gross, np.array(ret_ts, dtype=np.int64),
                     turnovers, n_pos, breaker_counts, dates, start_k, p)
    # 实时簿:在最后一根 bar(无需 t+1 实现收益)上再构一次,asof=数据最新日,消除 1 日滞后
    live_w, live_diag, live_breaker, _, _ = book_for_day(
        dates, spy_ret, sector_ret, names, len(dates) - 1, p, prev_w, active)
    rep["latest_book"] = _latest_book(live_w, live_diag, names, dates[-1])
    rep["latest_breaker"] = [{"ticker": t, "reason": r} for t, r in sorted(live_breaker.items())]
    rep["universe_size"] = len(names)
    rep["risk_governance"] = {"enabled": p.governance, "days": gov_days,
                              "ssr_short_blocks": int(ssr_blocks_total)}
    rep["_net_series"] = net.tolist()          # 日净收益全序列(供 CSCV/研究脚本;不入 feed)
    if verbose:
        _print_report(rep)
    return rep


def _slice_stats(r: np.ndarray) -> dict:
    """一段净收益的标准统计(净口径)。"""
    if len(r) < 5:
        return {"sharpe": float("nan"), "ann_return": float("nan"), "ann_vol": float("nan"),
                "max_drawdown": float("nan"), "hit_rate": float("nan"), "n_days": int(len(r))}
    return {
        "sharpe": val.sharpe(r), "ann_return": float(r.mean() * 252),
        "ann_vol": float(r.std(ddof=1) * np.sqrt(252)),
        "max_drawdown": val.max_drawdown(r), "hit_rate": float((r > 0).mean()),
        "n_days": int(len(r)),
    }


def _equity_curve(net: np.ndarray, ret_ts: np.ndarray, max_points: int = 280) -> list[dict]:
    """净值曲线(累积,起点 1.0),降采样到 ≤max_points 供看板绘制。"""
    if len(net) == 0:
        return []
    equity = np.cumprod(1 + net)
    import datetime as _dt
    idx = list(range(0, len(net), max(1, len(net) // max_points)))
    if idx[-1] != len(net) - 1:
        idx.append(len(net) - 1)
    return [{"d": _dt.datetime.utcfromtimestamp(int(ret_ts[i])).strftime("%Y-%m-%d"),
             "v": round(float(equity[i]), 5)} for i in idx]


def _summarize(net, gross, ret_ts, turnovers, n_pos, breaker_counts, dates, start_k, p):
    import datetime as _dt
    ann = float(net.mean() * 252)
    vol = float(net.std(ddof=1) * np.sqrt(252)) if len(net) > 1 else float("nan")
    dsr = val.deflated_sharpe(net, n_trials=p.n_trials)

    # 真 holdout 切分(R5):holdout_start(含)之后为终检段,之前为研究段
    ho_ts = int(_dt.datetime.strptime(p.holdout_start, "%Y-%m-%d")
                .replace(tzinfo=_dt.timezone.utc).timestamp())
    in_ho = ret_ts >= ho_ts
    train_stats = _slice_stats(net[~in_ho])
    holdout_stats = _slice_stats(net[in_ho])
    holdout_stats["start"] = p.holdout_start
    return {
        "engine": "stream_b_statarb_residual_meanreversion",
        "period": {
            "start": _dt.datetime.utcfromtimestamp(int(dates[start_k])).strftime("%Y-%m-%d"),
            "end": _dt.datetime.utcfromtimestamp(int(dates[-1])).strftime("%Y-%m-%d"),
            "trading_days": len(net),
        },
        "params": dict(p.__dict__),
        "net": {
            "ann_return": ann, "ann_vol": vol,
            "sharpe": val.sharpe(net), "max_drawdown": val.max_drawdown(net),
            "hit_rate": float((net > 0).mean()), "avg_daily": float(net.mean()),
        },
        "gross": {"sharpe": val.sharpe(gross), "ann_return": float(gross.mean() * 252)},
        "cost_drag_ann": float((gross.mean() - net.mean()) * 252),
        "turnover": {"avg_daily": float(np.mean(turnovers)),
                     "ann_2way": float(np.mean(turnovers) * 252)},
        "book": {"avg_positions": float(np.mean(n_pos)),
                 "avg_breaker_per_day": float(np.mean(breaker_counts))},
        "deflated_sharpe": dsr,
        "train": train_stats,
        "holdout": holdout_stats,
        "equity_curve": _equity_curve(net, ret_ts),
        "verdict": _verdict(val.sharpe(net), dsr, holdout_stats),
    }


def _verdict(net_sharpe: float, dsr: dict, holdout: dict | None = None) -> str:
    """L6 口径的诚实裁决(R4/R5):净 Sharpe + DSR + holdout 段是否过门。

    裁决以 holdout 段(从未据其调参)为准 —— 全样本数字只作背景(R5)。
    """
    ho_sr = (holdout or {}).get("sharpe", float("nan"))
    if not np.isfinite(net_sharpe):
        return "数据不足,无法裁决"
    parts = []
    if np.isfinite(ho_sr):
        if ho_sr <= 0:
            parts.append(f"holdout({(holdout or {}).get('start','?')}起)净 Sharpe={ho_sr:.2f}≤0 —— 终检不过,按 R4/R5 应淘汰")
        else:
            parts.append(f"holdout 净 Sharpe={ho_sr:.2f}>0 —— 终检段存活")
    if net_sharpe <= 0:
        parts.append(f"全样本净 Sharpe={net_sharpe:.2f}≤0(净成本是唯一货币 R4)")
    elif dsr.get("dsr", 0) < 0.95:
        parts.append(f"全样本 DSR={dsr.get('dsr', float('nan')):.2f}<0.95(扣 {dsr.get('n_trials')} 次试验后不显著)")
    else:
        parts.append(f"全样本净 Sharpe={net_sharpe:.2f} 且 DSR={dsr.get('dsr'):.2f}≥0.95")
    return ";".join(parts)


def _latest_book(weights, diag, names, asof_ts):
    import datetime as _dt
    rows = []
    for t, w in weights.items():
        d = diag.get(t, {})
        rows.append({
            "ticker": t, "side": "LONG" if w > 0 else "SHORT", "weight": round(w, 4),
            "s_score": round(d.get("s_score", float("nan")), 3),
            "halflife_days": round(d.get("halflife_days", float("nan")), 1),
            "kappa": round(d.get("kappa", float("nan")), 2),
            "hurst": round(d.get("hurst", float("nan")), 3),
            "sector": names[t]["sector"],
        })
    rows.sort(key=lambda r: r["weight"])
    return {
        "asof": _dt.datetime.utcfromtimestamp(int(asof_ts)).strftime("%Y-%m-%d"),
        "n_long": sum(1 for r in rows if r["side"] == "LONG"),
        "n_short": sum(1 for r in rows if r["side"] == "SHORT"),
        "gross_leverage": round(sum(abs(r["weight"]) for r in rows), 3),
        "net_exposure": round(sum(r["weight"] for r in rows), 4),
        "positions": rows,
    }


def _print_report(rep):
    print("=" * 78)
    print("流 B —— 条件因子统计套利 做多/做空(净·扣成本口径)")
    print("=" * 78)
    pr = rep["period"]
    print(f"区间 {pr['start']} ~ {pr['end']}  ({pr['trading_days']} 交易日)  "
          f"universe {rep['universe_size']} 只")
    n, g = rep["net"], rep["gross"]
    print(f"\n  净 Sharpe   {n['sharpe']:+.2f}    年化 {n['ann_return']*100:+.1f}%   "
          f"波动 {n['ann_vol']*100:.1f}%   最大回撤 {n['max_drawdown']*100:.1f}%   胜率 {n['hit_rate']*100:.0f}%")
    print(f"  毛 Sharpe   {g['sharpe']:+.2f}    年化 {g['ann_return']*100:+.1f}%   "
          f"成本拖累 {rep['cost_drag_ann']*100:.1f}%/年")
    print(f"  日均换手 {rep['turnover']['avg_daily']*100:.0f}%  双边年化 {rep['turnover']['ann_2way']*100:.0f}%   "
          f"日均持仓 {rep['book']['avg_positions']:.0f}  日均熔断 {rep['book']['avg_breaker_per_day']:.1f}")
    dsr = rep["deflated_sharpe"]
    print(f"  Deflated Sharpe={dsr['dsr']:.3f} (n_trials={dsr['n_trials']}, skew={dsr['skew']:.2f}, kurt={dsr['kurt']:.1f})")
    tr, ho = rep["train"], rep["holdout"]
    print(f"\n  研究段(train)  净 Sharpe {tr['sharpe']:+.2f}  年化 {tr['ann_return']*100:+.1f}%  "
          f"回撤 {tr['max_drawdown']*100:.1f}%  ({tr['n_days']}日)")
    print(f"  终检段(holdout≥{ho.get('start')}) 净 Sharpe {ho['sharpe']:+.2f}  年化 {ho['ann_return']*100:+.1f}%  "
          f"回撤 {ho['max_drawdown']*100:.1f}%  ({ho['n_days']}日)")
    rg = rep.get("risk_governance", {})
    if rg:
        print(f"  风险治理: {'开' if rg.get('enabled') else '关'}  触发 {rg.get('days')}  "
              f"SSR拦截加空 {rg.get('ssr_short_blocks')} 次")
    print(f"\n  裁决:{rep['verdict']}")
    lb = rep["latest_book"]
    print(f"\n  最新持仓簿 @ {lb['asof']}:多 {lb['n_long']} / 空 {lb['n_short']}  "
          f"毛杠杆 {lb['gross_leverage']}  净敞口 {lb['net_exposure']:+.3f}")
    for r in lb["positions"][:5] + lb["positions"][-5:]:
        print(f"     {r['side']:<5} {r['ticker']:<6} w={r['weight']:+.3f}  s={r['s_score']:+.2f}  "
              f"hl={r['halflife_days']}d  H={r['hurst']}  {r['sector']}")
    print("\n  诚实声明:universe=当前流动大盘(含幸存者偏差,高估);残差因子=SPY+行业 ETF(非全 Barra);")
    print("  无 PIT 基本面;成本为模型估计(平方根律+价差),非实盘成交回报。结论须经真 holdout 终检(R5)。")
    print("=" * 78)


if __name__ == "__main__":
    run()
