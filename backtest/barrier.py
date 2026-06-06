"""路径化标签回测(triple-barrier):演示"高胜率"如何来自标签定义而非预测力。

每次信号建仓后,逐日沿真实价格路径推进(无未来函数):
  - 先触止盈 tp  -> 记为 WIN,按 +tp 离场
  - 先触止损 sl  -> 记为 LOSS,按 -sl 离场(sl=None 表示不设止损)
  - 到期 H 日仍未触 -> 按到期收益结算,>0 记 WIN 否则 LOSS

结论性指标:胜率 win_rate、平均盈利、平均亏损、期望 expectancy(每笔平均收益)。
要点:不设止损 + 止盈不高 + 长到期,胜率可冲到 85-90%,但少数到期亏损很大(负偏),
期望未必更高 —— 胜率高 ≠ 赚得多。这是诚实拆解"正确率"的关键。
"""
from __future__ import annotations

import json
import os

import numpy as np

import data as datamod
import factors

HERE = os.path.dirname(os.path.abspath(__file__))


def barrier_trade(adj: np.ndarray, i: int, tp: float, sl: float | None, h: int) -> float | None:
    """从 i 日收盘建仓,返回这笔交易的实现收益;样本不足返回 None。"""
    entry = adj[i]
    end = min(i + h, len(adj) - 1)
    if end <= i:
        return None
    for j in range(i + 1, end + 1):
        ret = adj[j] / entry - 1.0
        if ret >= tp:
            return tp
        if sl is not None and ret <= -sl:
            return -sl
    return adj[end] / entry - 1.0   # 到期结算


def run(configs):
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    data_all = {tk: d for tk in uni["universe"]
                if (d := datamod.load(tk)) and len(d.get("adjclose", [])) > 260}

    # 用基础 TQM 信号(与定义无关,固定信号源)
    signals = {tk: factors.tqm_signal(np.asarray(d["adjclose"], dtype=float))
               for tk, d in data_all.items()}

    print(f"universe {len(data_all)} 只\n")
    print(f"{'止盈/止损/期限':<20} {'笔数':>7} {'胜率':>7} {'平均盈':>7} {'平均亏':>7} {'期望/笔':>8}")
    print("-" * 64)
    for tp, sl, h in configs:
        n = win = 0
        wins_r: list[float] = []
        loss_r: list[float] = []
        for tk, d in data_all.items():
            adj = np.asarray(d["adjclose"], dtype=float)
            sig = signals[tk]
            last = -10 ** 9
            for i in range(len(adj)):
                if not sig[i] or (i - last) < h:
                    continue
                r = barrier_trade(adj, i, tp, sl, h)
                if r is None:
                    continue
                last = i
                n += 1
                if r > 0:
                    win += 1
                    wins_r.append(r)
                else:
                    loss_r.append(r)
        exp = (sum(wins_r) + sum(loss_r)) / n if n else float("nan")
        sl_s = f"{sl*100:.0f}%" if sl is not None else "无"
        label = f"+{tp*100:.0f}%/{sl_s}/{h}d"
        print(f"{label:<20} {n:>7} {win/n*100:>6.1f}% "
              f"{np.mean(wins_r)*100 if wins_r else 0:>6.1f}% "
              f"{np.mean(loss_r)*100 if loss_r else 0:>6.1f}% "
              f"{exp*100:>7.1f}%")


if __name__ == "__main__":
    run([
        (0.15, 0.15, 252),   # 对称 15% 障碍:接近"公平"的方向胜率
        (0.10, 0.10, 252),
        (0.10, None, 252),   # 不设止损 + 10%止盈 + 1年到期 -> 胜率冲高
        (0.08, None, 252),
        (0.10, None, 504),   # 拉长到期 -> 胜率更高
    ])
