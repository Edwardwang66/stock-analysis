"""筹码分布(成本分布 · 估算)—— 与 frontend/lib/chips.ts 保持一致。

用历史日 K 的量价堆积近似筹码:成交量在 [low, high] 均匀摊到价格桶 + 时间衰减。
获利比例 = 现价之下筹码占比;支撑/压力 = 现价上下最大筹码峰。估算参考,非真实持仓成本。
"""
from __future__ import annotations

from ..models import Bar


def compute_chips(bars: list[Bar], price: float, n_bins: int = 60, half_life: int = 60) -> dict | None:
    data = [b for b in bars if b.high > 0 and b.low > 0 and b.volume > 0]
    if len(data) < 10 or not price or price <= 0:
        return None

    lo = min(b.low for b in data)
    hi = max(b.high for b in data)
    if hi <= lo:
        return None
    step = (hi - lo) / n_bins
    bins = [0.0] * n_bins

    decay = 0.5 ** (1.0 / max(1, half_life))
    n = len(data)
    for i, b in enumerate(data):
        w = decay ** (n - 1 - i)
        vol = b.volume * w
        a = max(0, int((b.low - lo) / step))
        z = min(n_bins - 1, int((b.high - lo) / step))
        per = vol / (z - a + 1)
        for k in range(a, z + 1):
            bins[k] += per

    total = sum(bins) or 1.0
    levels = [{"price": lo + (i + 0.5) * step, "volume": v, "profit": (lo + (i + 0.5) * step) <= price}
              for i, v in enumerate(bins)]

    profit_ratio = sum(l["volume"] for l in levels if l["profit"]) / total
    avg_cost = sum(l["price"] * l["volume"] for l in levels) / total

    support = resistance = None
    s_v = r_v = 0.0
    for l in levels:
        if l["price"] < price and l["volume"] > s_v:
            s_v, support = l["volume"], l["price"]
        if l["price"] > price and l["volume"] > r_v:
            r_v, resistance = l["volume"], l["price"]

    low_cut, high_cut = total * 0.05, total * 0.95
    acc = 0.0
    c_low, c_high = levels[0]["price"], levels[-1]["price"]
    for l in levels:
        before = acc
        acc += l["volume"]
        if before < low_cut <= acc:
            c_low = l["price"]
        if before < high_cut <= acc:
            c_high = l["price"]
            break

    if profit_ratio >= 0.7:
        note = "高获利盘,上方抛压偏重。"
    elif profit_ratio <= 0.2:
        note = "深度套牢盘,反弹易遇压。"
    else:
        note = "获利与套牢盘相对均衡。"

    return {
        "price": price, "profit_ratio": profit_ratio, "avg_cost": avg_cost,
        "support": support, "resistance": resistance,
        "conc90": {"low": c_low, "high": c_high}, "levels": levels, "note": note,
    }
