"""交易成本与容量模型 —— 「净成本是唯一计价货币」(设计文档 D9/R4)。

设计文档 §3.8 / §6.5 / §6.6 的成本闭环:
  - 价差成本(half-spread):每单位换手按固定 bps 计。
  - 市场冲击(平方根律):I ≈ Y·σ·√(参与率),与时长无关、只取决于参与率
    (Sato-Kanazawa, PRL 2025 全量数据验证 δ=1/2)。
  - 容量地板:单笔成交占 ADV 的比例封顶(默认 ≤5% ADV);预估冲击 > 预期 alpha 即不交易。

所有函数纯 numpy,无第三方依赖。成本以「占成交名义额的比例」返回,便于直接从组合收益里扣除。
"""
from __future__ import annotations

import numpy as np

# 默认参数(保守起点;实盘须用自身成交回报校准 Y —— 见设计文档 §6.5)
DEFAULT_HALF_SPREAD_BPS = 5.0      # 单边价差成本(bps);设计文档 §5 举例 5bp 即可把 13.84%→3.66%
DEFAULT_IMPACT_Y = 0.5             # 平方根冲击系数 Y(无量纲);文献区间 ~0.3–1.0
DEFAULT_MAX_PARTICIPATION = 0.05   # 单日参与率上限(占 ADV 比例),容量地板(D6/R9)


def sqrt_impact_frac(sigma_daily: np.ndarray, trade_notional: np.ndarray,
                     adv_notional: np.ndarray, Y: float = DEFAULT_IMPACT_Y) -> np.ndarray:
    """平方根冲击律:返回每笔成交的冲击成本(占该笔名义额的比例)。

    sigma_daily   : 标的日波动率(小数,如 0.02 = 2%)。
    trade_notional: 本次成交名义额($,绝对值)。
    adv_notional  : 标的日均成交额($,ADV)。
    冲击 = Y · σ · √(参与率),参与率 = 成交额 / ADV。
    """
    adv = np.where(adv_notional > 0, adv_notional, np.nan)
    participation = np.abs(trade_notional) / adv
    impact = Y * sigma_daily * np.sqrt(np.clip(participation, 0, None))
    return np.nan_to_num(impact, nan=0.0)


def trade_cost_frac(sigma_daily: np.ndarray, trade_notional: np.ndarray,
                    adv_notional: np.ndarray, half_spread_bps: float = DEFAULT_HALF_SPREAD_BPS,
                    Y: float = DEFAULT_IMPACT_Y) -> np.ndarray:
    """单笔总成交成本(占名义额比例)= 价差 + 平方根冲击。"""
    spread = half_spread_bps * 1e-4
    impact = sqrt_impact_frac(sigma_daily, trade_notional, adv_notional, Y)
    return spread + impact


def portfolio_turnover_cost(dw: np.ndarray, sigma_daily: np.ndarray,
                            adv_notional: np.ndarray, aum: float,
                            half_spread_bps: float = DEFAULT_HALF_SPREAD_BPS,
                            Y: float = DEFAULT_IMPACT_Y) -> float:
    """组合一次再平衡的总成本(占 NAV 的比例,小数)。

    dw            : 各标的权重变化(占 NAV 的小数,Δw)。
    sigma_daily   : 各标的日波动率。
    adv_notional  : 各标的 ADV($)。
    aum           : 组合资产规模($),用于把 Δw 换成名义成交额。
    返回:本次再平衡成本 / NAV(正数,直接从当日收益里减去)。
    """
    trade_notional = np.abs(dw) * aum
    frac = trade_cost_frac(sigma_daily, trade_notional, adv_notional, half_spread_bps, Y)
    cost_dollars = (frac * trade_notional).sum()
    return float(cost_dollars / aum) if aum > 0 else 0.0


def capacity_cap_weights(w: np.ndarray, adv_notional: np.ndarray, aum: float,
                         max_participation: float = DEFAULT_MAX_PARTICIPATION) -> np.ndarray:
    """容量地板:把单标的权重压到「单日可成交」之内(|w|·AUM ≤ 参与率·ADV)。

    这是设计文档 R9「容量以扣冲击净值定义、ADV 参与率封顶」的硬约束近似。
    被截断的权重不会被重新分配(诚实地降低组合规模),返回截断后的权重。
    """
    if aum <= 0:
        return w
    cap_notional = max_participation * np.where(adv_notional > 0, adv_notional, 0.0)
    cap_w = cap_notional / aum
    return np.sign(w) * np.minimum(np.abs(w), cap_w)


# ----------------------------- 借券费 / 做空可行性(空头腿)-----------------------------
# 设计文档 R4:净·扣成本唯一货币。空头腿除价差+冲击外,还要付**借券费**(annualized),
# 且小盘/冷门股常**借不到**(unshortable)。免费数据无真实借券率,故用 ADV 分档代理(诚实标注)。
# 量级参考:大盘 general-collateral ~0.2–0.5%/yr;hard-to-borrow 小盘可达 3–20%+/yr;
# 微盘常无券可借。实盘须换券商真实 borrow rate / locate 可得性。

SHORTABLE_MIN_ADV = 0.5e6     # ADV 低于此($/日)视为不可做空(借不到券)
# (ADV 下界 $, 年化借券率) —— 阶梯,越冷门越贵
BORROW_TIERS = [
    (50e6, 0.003),   # ≥$50M ADV:GC,~30bps/yr
    (10e6, 0.010),   # $10–50M:~1%/yr
    (2e6, 0.030),    # $2–10M:~3%/yr(hard-to-borrow 起)
    (0.5e6, 0.080),  # $0.5–2M:~8%/yr
]


def borrow_rate_proxy(adv_notional: np.ndarray) -> np.ndarray:
    """按 ADV 分档的年化借券率代理(小数)。低于 SHORTABLE_MIN_ADV 返回 nan(不可做空)。"""
    adv = np.asarray(adv_notional, dtype=float)
    rate = np.full(adv.shape, np.nan)
    # 从高到低分档赋值(高 ADV 先填,低档覆盖更小的)
    for lo, r in BORROW_TIERS:
        rate = np.where((adv >= lo) & np.isnan(rate), r, rate)
    rate = np.where(adv < SHORTABLE_MIN_ADV, np.nan, rate)
    return rate


def shortable_mask(adv_notional: np.ndarray) -> np.ndarray:
    """是否可做空(ADV ≥ 阈值且有有效借券率)。"""
    return np.asarray(adv_notional, dtype=float) >= SHORTABLE_MIN_ADV


def borrow_cost_daily(short_weight_abs: np.ndarray, adv_notional: np.ndarray) -> float:
    """持有空头一天的借券成本(占 NAV 比例)= Σ |w_short| · 年化率 / 252。
    不可做空的名(rate=nan)按**最贵档**惩罚(若强行做空)——诚实地反映成本下限。"""
    w = np.abs(np.asarray(short_weight_abs, dtype=float))
    rate = borrow_rate_proxy(adv_notional)
    worst = BORROW_TIERS[-1][1]
    rate = np.where(np.isnan(rate), worst, rate)   # 不可借者按最贵档计(保守)
    return float(np.nansum(w * rate) / 252.0)


def borrow_drag_annual(short_weights: np.ndarray, adv_notional: np.ndarray) -> dict:
    """对一个空头簿估年化借券拖累 + 不可做空占比。short_weights 为负权重(或绝对值)。
    返回 {ann_borrow_cost, unshortable_frac, mean_rate, n_short, n_unshortable}。"""
    w = np.abs(np.asarray(short_weights, dtype=float))
    sel = w > 1e-9
    w, adv = w[sel], np.asarray(adv_notional, dtype=float)[sel]
    if w.sum() == 0:
        return {"ann_borrow_cost": 0.0, "unshortable_frac": 0.0, "mean_rate": 0.0,
                "n_short": 0, "n_unshortable": 0}
    rate = borrow_rate_proxy(adv)
    unshort = np.isnan(rate)
    worst = BORROW_TIERS[-1][1]
    rate_filled = np.where(unshort, worst, rate)
    ann = float(np.sum(w * rate_filled))                       # 年化借券成本(占 NAV)
    return {
        "ann_borrow_cost": ann,
        "unshortable_frac": float(w[unshort].sum() / w.sum()),  # 按权重计的不可做空占比
        "mean_rate": float(np.sum(w * rate_filled) / w.sum()),
        "n_short": int(sel.sum()),
        "n_unshortable": int(unshort.sum()),
    }
