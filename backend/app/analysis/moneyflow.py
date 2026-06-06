"""资金流向 / 主力资金(估算)—— 与 frontend/lib/moneyflow.ts 保持一致。

⚠️ 真实「特大/大/中/小单」「主力资金」基于 Level-2 逐笔成交;免费行情无逐笔与买卖盘方向,
这里用分钟 K 线做透明代理估算:成交额按分位数分档 + 收盘涨跌定方向,主力=特大+大。
仅供趋势参考,非真实逐笔(见 docs/compliance.md)。
"""
from __future__ import annotations

from ..models import Bar


def _quantile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]


def compute_moneyflow(bars: list[Bar]) -> dict:
    if len(bars) < 4:
        return {"bars": 0, "note": "数据不足,无法估算资金流向。"}

    amt = [((b.high + b.low + b.close) / 3.0) * (b.volume or 0.0) for b in bars]
    sorted_amt = sorted(a for a in amt if a > 0)
    t_small = _quantile(sorted_amt, 0.55)
    t_med = _quantile(sorted_amt, 0.80)
    t_large = _quantile(sorted_amt, 0.95)

    names = ["特大单", "大单", "中单", "小单"]
    buckets = {n: {"name": n, "inflow": 0.0, "outflow": 0.0} for n in names}
    series = []
    cum_all = cum_main = 0.0

    for i, b in enumerate(bars):
        a = amt[i]
        if a <= 0:
            series.append({"time": int(b.ts.timestamp()), "cum_all": cum_all, "cum_main": cum_main})
            continue
        ref = bars[i - 1].close if i > 0 else b.open
        sign = 1 if b.close > ref else -1 if b.close < ref else 0
        if sign == 0:
            series.append({"time": int(b.ts.timestamp()), "cum_all": cum_all, "cum_main": cum_main})
            continue
        name = "特大单" if a > t_large else "大单" if a > t_med else "中单" if a > t_small else "小单"
        bk = buckets[name]
        if sign > 0:
            bk["inflow"] += a
        else:
            bk["outflow"] += a
        signed = sign * a
        cum_all += signed
        if name in ("特大单", "大单"):
            cum_main += signed
        series.append({"time": int(b.ts.timestamp()), "cum_all": cum_all, "cum_main": cum_main})

    out_buckets = []
    for n in names:
        bk = buckets[n]
        bk["net"] = bk["inflow"] - bk["outflow"]
        out_buckets.append(bk)

    inflow = sum(bk["inflow"] for bk in out_buckets)
    outflow = sum(bk["outflow"] for bk in out_buckets)
    main_inflow = buckets["特大单"]["inflow"] + buckets["大单"]["inflow"]
    main_outflow = buckets["特大单"]["outflow"] + buckets["大单"]["outflow"]
    main_net = main_inflow - main_outflow

    if main_net > 0:
        note = "主力资金净流入,资金在进场。"
    elif main_net < 0:
        note = "主力资金净流出,资金在撤离。"
    else:
        note = "主力资金基本均衡。"

    return {
        "inflow": inflow, "outflow": outflow, "net": inflow - outflow,
        "buckets": out_buckets,
        "main_inflow": main_inflow, "main_outflow": main_outflow, "main_net": main_net,
        "series": series, "bars": len(bars), "note": note,
    }
