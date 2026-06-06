"""加密横截面因子(Hyperliquid 永续)——纯链上/盘口可得,无未来函数。

设计依据 research/quant-factor-deep-research.md §3:
  - 加密只需"市场+规模+动量"三因子(Liu-Tsyvinski-Wu),股票因子不能直接搬。
  - 加密动量窗口比股票短(1-4 周最显著)。
  - funding/OI/basis 是股票没有的独家正交信息;高正 funding = 多头拥挤 -> 反转倾向。

因子(均在 rebalance 日 i 用 ≤i 数据计算,返回原始值;符号见 SIGN):
  mom_14    : 过去 14 日收益(跳过最近 2 日)         + 动量
  reversal_3: 过去 3 日收益                          - 短期反转
  vol_20    : 过去 20 日年化波动                      - (留待拟合定夺)
  fund_carry: 过去 7 日"日资金费之和"的均值           - 高funding=多头拥挤=看空
  basis     : 过去 7 日 premium 均值(perp-spot 溢价) - 高溢价=拥挤=看空
"""
from __future__ import annotations

import numpy as np

SIGN = {"mom_14": +1, "reversal_3": -1, "vol_20": -1, "fund_carry": -1, "basis": -1}
FACTORS = list(SIGN.keys())


def compute(adj: np.ndarray, i: int, fund_sum: np.ndarray, prem: np.ndarray) -> dict | None:
    """adj/fund_sum/prem 为按日对齐的数组;i 为当前日索引。"""
    if i < 21:
        return None
    if adj[i] <= 0 or adj[i - 14] <= 0 or adj[i - 3] <= 0 or adj[i - 2] <= 0:
        return None
    seg = adj[i - 20:i + 1]
    rets = np.log(seg[1:] / seg[:-1])
    vol = float(rets.std(ddof=1) * np.sqrt(365)) if len(rets) > 2 else np.nan
    # funding/basis 过去 7 日均值(允许 nan -> 用 nan 过滤)
    fc = np.nanmean(fund_sum[i - 6:i + 1]) if i >= 6 else np.nan
    bs = np.nanmean(prem[i - 6:i + 1]) if i >= 6 else np.nan
    return {
        "mom_14": adj[i - 2] / adj[i - 14] - 1.0,   # 跳过最近 2 日
        "reversal_3": adj[i] / adj[i - 3] - 1.0,
        "vol_20": vol,
        "fund_carry": fc,
        "basis": bs,
    }
