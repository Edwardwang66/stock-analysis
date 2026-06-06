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
