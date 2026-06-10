"""chan_engine 纯逻辑单测:EMA/MACD/包含合并/分型/笔/中枢/买卖点 + analyze_symbol 集成冒烟。

与 backend/tests 同风格:直接 python 运行,assert 失败即退出非零。
"""
import math
import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from chan_engine import (  # noqa: E402
    analyze_symbol,
    build_strokes,
    buy_sell_points_hist,
    ema,
    find_fractals,
    find_pivots_hist,
    macd_parts,
    merge_inclusion,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


def bar(t, h, lo, c=None):
    return SimpleNamespace(time=t, high=h, low=lo, close=c if c is not None else (h + lo) / 2)


print("== EMA / MACD ==")
e = ema([1, 2, 3, 4, 5], 3)  # k=0.5;种子=均值2.0
ok("EMA 种子=前p均值", e[2] == 2.0)
ok("EMA 递推", e[3] == 3.0 and e[4] == 4.0)
ok("EMA 不足p全None", all(x is None for x in ema([1, 2], 3)))

hist, line = macd_parts([100.0] * 40)
ok("MACD 常数序列柱=0", hist[33] is not None and abs(hist[33]) < 1e-9)
ok("MACD 信号线前柱为None", hist[32] is None and line[24] is None and line[25] is not None)
ok("MACD 长度与输入一致", len(hist) == 40 and len(line) == 40)

print("== 包含合并 ==")
mk = merge_inclusion([bar(0, 10, 5), bar(1, 9, 6), bar(2, 12, 8)])
ok("后K被前K包含→向下合并(取低)", mk[0]["high"] == 9 and mk[0]["low"] == 5)
ok("合并继承末K时间与序号", mk[0]["time"] == 1 and mk[0]["idx"] == 1)
ok("无包含不合并", len(mk) == 2 and mk[1]["high"] == 12)

print("== 分型 ==")
mk2 = [
    {"time": 0, "high": 5, "low": 4, "idx": 0},
    {"time": 1, "high": 7, "low": 6, "idx": 1},   # 顶分型
    {"time": 2, "high": 5, "low": 3, "idx": 2},
    {"time": 3, "high": 4, "low": 1, "idx": 3},   # 底分型
    {"time": 4, "high": 6, "low": 2, "idx": 4},
]
fs = find_fractals(mk2)
ok("识别顶/底分型", [f["type"] for f in fs] == ["top", "bottom"])
ok("分型价取极值", fs[0]["price"] == 7 and fs[1]["price"] == 1)

print("== 笔 ==")
mk3 = [{"time": i, "high": 0, "low": 0, "idx": i} for i in range(10)]
fs3 = [
    {"time": 0, "price": 10, "type": "top", "idx": 0},
    {"time": 1, "price": 11, "type": "top", "idx": 1},     # 同型更高→替换前者
    {"time": 4, "price": 5, "type": "bottom", "idx": 4},   # 间隔≥2→成笔
    {"time": 7, "price": 12, "type": "top", "idx": 7},
]
st = build_strokes(fs3, mk3)
ok("同型分型保留更极端者", st[0]["frm"]["price"] == 11)
ok("成笔两段且方向正确", len(st) == 2 and st[0]["dir"] == "down" and st[1]["dir"] == "up")

print("== 中枢(全历史) ==")


def stroke(t0, p0, t1, p1, area=0.0, typ=None):
    d = "up" if p1 > p0 else "down"
    return {"frm": {"time": t0, "price": p0, "type": "bottom" if d == "up" else "top"},
            "to": {"time": t1, "price": p1, "type": typ or ("top" if d == "up" else "bottom")},
            "dir": d, "area": area}


st3 = [stroke(0, 10, 1, 20), stroke(1, 20, 2, 12), stroke(2, 12, 3, 18)]
ps = find_pivots_hist(st3)
ok("三笔重叠成枢 zg/zd", len(ps) == 1 and ps[0]["zg"] == 18 and ps[0]["zd"] == 12)
ok("无重叠不成枢", find_pivots_hist([stroke(0, 10, 1, 20), stroke(1, 20, 2, 1), stroke(2, 1, 3, 2)]) == [])

print("== 买卖点(全历史) ==")
# 新低 + 动能(面积)收缩 → 1B;其后不破前低的底 → 2B
st4 = [
    stroke(0, 20, 1, 10, area=-8),            # 下
    stroke(1, 10, 2, 16, area=+3),            # 上
    stroke(2, 16, 3, 8, area=-2),             # 下:新低+面积缩 → 1B@8
    stroke(3, 8, 4, 14, area=+2),             # 上
    stroke(4, 14, 5, 9, area=-1),             # 下:不破前低 → 2B@9
]
pts = buy_sell_points_hist(st4, [])
kinds = [p["kind"] for p in pts]
ok("背驰识别 1B", "1B" in kinds and next(p for p in pts if p["kind"] == "1B")["price"] == 8)
ok("1B 后不破低 → 2B", "2B" in kinds and next(p for p in pts if p["kind"] == "2B")["price"] == 9)
ok("买卖点按时间排序", [p["time"] for p in pts] == sorted(p["time"] for p in pts))
# 动能未收缩(面积放大)→ 不算背驰
st5 = [stroke(0, 20, 1, 10, area=-2), stroke(1, 10, 2, 16, area=3), stroke(2, 16, 3, 8, area=-9)]
ok("面积放大不判背驰", all(p["kind"] != "1B" for p in buy_sell_points_hist(st5, [])))
# 中枢上方回踩不破 zg → 3B
st6 = [stroke(0, 10, 1, 20), stroke(1, 20, 2, 12), stroke(2, 12, 3, 18),
       stroke(3, 18, 4, 30), stroke(4, 30, 5, 19, typ="bottom")]
pts6 = buy_sell_points_hist(st6, find_pivots_hist(st6))
ok("中枢后回踩不破 zg → 3B", any(p["kind"] == "3B" and p["price"] == 19 for p in pts6))

print("== analyze_symbol 集成冒烟 ==")
ok("不足60根返回空", analyze_symbol([bar(i, 10, 9) for i in range(59)]) == [])
waves = []
for i in range(120):
    c = 100 + 10 * math.sin(i / 5) + i * 0.05
    waves.append(bar(i * 86400, c + 1, c - 1, c))
res = analyze_symbol(waves)
ok("正弦序列识别出买卖点", len(res) >= 1, f"got {len(res)}")
by_time = {b.time: i for i, b in enumerate(waves)}
for p in res:
    i = by_time[p["time"]]
    if p["r5"] is not None:
        expect = (waves[i + 5].close / p["price"] - 1) * 100
        assert abs(p["r5"] - expect) < 1e-9, f"r5 口径错: {p}"
    if i >= len(waves) - 3:
        assert p["recent"], "recent 标记缺失"
ok("r5 事后收益口径正确(全部抽查)", True)
ok("kind 合法", all(p["kind"] in {"1B", "2B", "3B", "1S", "2S", "3S"} for p in res))

print(f"\nchan_engine 全部通过:{PASS} 项")
