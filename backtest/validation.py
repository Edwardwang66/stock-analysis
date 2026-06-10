"""防过拟合与统计套利诊断 —— 验证层 L6 的可复用工具(设计文档 §6.7 / §7.3)。

包含:
  - deflated_sharpe : Deflated Sharpe Ratio(Bailey-Lopez de Prado 2014),按申报试验次数
                      与非正态修正「最优回测实为过拟合」的概率。
  - hurst_exponent  : Hurst 指数(R/S 法),>0.55 视为残差从均值回归漂向随机游走(D13/§7.3)。
  - max_drawdown    : 峰谷最大回撤(R1 的判据)。
  - ou_from_ar1     : 由 AR(1) 拟合反解 OU 参数(κ、半衰期、σ_eq、s-score 用的均衡均值)。

纯 numpy。统计量用正态近似(无 scipy),够用于研究层诊断;实盘上线前应换更精确实现。
"""
from __future__ import annotations

import math
import numpy as np


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def sharpe(returns: np.ndarray, periods_per_year: int = 252) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))


def deflated_sharpe(returns: np.ndarray, n_trials: int = 1,
                    periods_per_year: int = 252) -> dict:
    """Deflated Sharpe Ratio。返回 {sr, sr_annual, dsr, p_value, skew, kurt, n}。

    dsr = 观测 SR 在「多重试验 + 非正态 + 有限样本」下显著为正的概率(>0.95 才算可信)。
    n_trials = 申报的独立策略试验次数(只能扣「申报的」N —— 见设计文档 §6.7 元过拟合警告)。
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 8 or r.std(ddof=1) == 0:
        return {"sr": float("nan"), "sr_annual": float("nan"), "dsr": float("nan"),
                "p_value": float("nan"), "skew": float("nan"), "kurt": float("nan"), "n": n}
    mu, sd = r.mean(), r.std(ddof=1)
    sr = mu / sd                          # 每期(非年化)SR
    z = (r - mu) / sd
    skew = float((z ** 3).mean())
    kurt = float((z ** 4).mean())         # 非超额峰度(正态=3)

    # 期望最大 SR(多重试验下):用 N 个独立标准正态的期望最大值近似
    if n_trials > 1:
        e = 0.5772156649
        inv = _norm_inv(1.0 - 1.0 / n_trials)
        inv2 = _norm_inv(1.0 - 1.0 / (n_trials * math.e))
        sr0 = (1.0 / math.sqrt(n)) * ((1 - e) * inv + e * inv2)  # 期望最大 SR 门槛(每期)
    else:
        sr0 = 0.0

    # DSR:观测 SR 超过门槛 sr0 的概率(对非正态做修正)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2))
    dsr = _norm_cdf((sr - sr0) * math.sqrt(n - 1) / denom)
    p_value = 1.0 - dsr
    return {"sr": float(sr), "sr_annual": float(sr * math.sqrt(periods_per_year)),
            "dsr": float(dsr), "p_value": float(p_value),
            "skew": skew, "kurt": kurt, "n_trials": int(n_trials), "n": n}


def _norm_inv(p: float) -> float:
    """标准正态分位数(Acklam 近似),避免依赖 scipy。"""
    p = min(max(p, 1e-9), 1 - 1e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def hurst_exponent(x: np.ndarray, max_lag: int = 20) -> float:
    """Hurst 指数(基于不同 lag 的方差标度)。

    H≈0.5 随机游走;H<0.5 均值回归(好);H>0.55 漂向趋势/随机游走(协整断裂预警,§7.3)。
    用 log Var(x_{t+lag}-x_t) ~ 2H·log(lag) 的斜率估计,稳健且无需 scipy。
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < max_lag * 2:
        return float("nan")
    lags = np.arange(2, max_lag + 1)
    tau = []
    for lag in lags:
        diff = x[lag:] - x[:-lag]
        tau.append(np.sqrt(np.mean(diff ** 2)) + 1e-12)
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return float(poly[0])


def max_drawdown(equity_or_returns: np.ndarray, is_returns: bool = True) -> float:
    """峰谷最大回撤(负数,如 -0.15)。"""
    r = np.asarray(equity_or_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return float("nan")
    equity = np.cumprod(1 + r) if is_returns else r
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(dd.min())


def cscv_pbo(returns_matrix: np.ndarray, n_blocks: int = 8) -> dict:
    """CSCV(组合对称交叉验证)估 PBO —— Bailey-Borwein-LdP-Zhu(2014)。

    returns_matrix: (n_configs, T) 各候选配置的日收益序列(同一时间轴)。
    把 T 日切成 n_blocks 块,取一半块作 IS、另一半作 OOS,遍历全部 C(n,n/2) 组合:
    每个组合在 IS 上选 Sharpe 最优配置,看它在 OOS 的排名;
    PBO = IS 最优在 OOS 落入后半段(中位数以下)的组合占比。
    返回 {pbo, n_combos, n_configs, avg_oos_rank, is_best_oos_sharpe_mean}。
    """
    from itertools import combinations
    M = np.asarray(returns_matrix, dtype=float)
    n_cfg, T = M.shape
    if n_cfg < 2 or T < n_blocks * 4:
        return {"pbo": float("nan"), "n_combos": 0, "n_configs": n_cfg}
    edges = np.linspace(0, T, n_blocks + 1, dtype=int)
    blocks = [list(range(edges[i], edges[i + 1])) for i in range(n_blocks)]

    def _sr(r):                       # 每期 Sharpe(不年化;排名用,量纲无关)
        sd = r.std(ddof=1, axis=-1)
        return np.where(sd > 0, r.mean(axis=-1) / np.where(sd > 0, sd, 1), -np.inf)

    below_median = 0
    oos_ranks, is_best_oos = [], []
    combos = list(combinations(range(n_blocks), n_blocks // 2))
    for c in combos:
        is_idx = np.concatenate([blocks[i] for i in c])
        oos_idx = np.concatenate([blocks[i] for i in range(n_blocks) if i not in c])
        sr_is = _sr(M[:, is_idx])
        sr_oos = _sr(M[:, oos_idx])
        best = int(np.argmax(sr_is))
        # OOS 相对排名 ∈ (0,1):1=最好
        rank = (np.sum(sr_oos <= sr_oos[best]) - 0.5) / n_cfg
        oos_ranks.append(rank)
        is_best_oos.append(float(sr_oos[best]))
        if rank <= 0.5:
            below_median += 1
    return {
        "pbo": float(below_median / len(combos)),
        "n_combos": len(combos), "n_configs": n_cfg,
        "avg_oos_rank": float(np.mean(oos_ranks)),
        "is_best_oos_sharpe_mean": float(np.mean(is_best_oos)),
    }


def ou_from_ar1(x: np.ndarray, dt: float = 1.0 / 252) -> dict | None:
    """对序列 x 拟合 AR(1): x_{t}=a+b·x_{t-1}+ζ,反解 OU 参数(Avellaneda-Lee 2010)。

    返回 {kappa, halflife_days, m, sigma_eq, s_score, b}。
    kappa 年化均值回归速度;halflife 半衰期(交易日);m 均衡均值;sigma_eq 均衡标准差;
    s_score=(x_last - m)/sigma_eq。b 不在 (0,1) 视为不可均值回归 -> 返回 None。
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return None
    x0, x1 = x[:-1], x[1:]
    # 最小二乘 x1 = a + b x0
    A = np.vstack([np.ones_like(x0), x0]).T
    coef, *_ = np.linalg.lstsq(A, x1, rcond=None)
    a, b = float(coef[0]), float(coef[1])
    if not (0 < b < 1):
        return None
    resid = x1 - (a + b * x0)
    var_z = float(resid.var(ddof=2)) if len(resid) > 2 else float("nan")
    kappa = -math.log(b) / dt                      # 年化
    halflife_days = math.log(2) / (-math.log(b))   # 交易日
    m = a / (1 - b)
    sigma_eq = math.sqrt(max(1e-18, var_z / (1 - b ** 2)))
    s_score = (x[-1] - m) / sigma_eq if sigma_eq > 0 else float("nan")
    return {"kappa": float(kappa), "halflife_days": float(halflife_days),
            "m": float(m), "sigma_eq": float(sigma_eq), "s_score": float(s_score), "b": b}
