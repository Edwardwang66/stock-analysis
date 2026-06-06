"""简化版缠论(Chan)结构识别 —— 纯 Python,与 frontend/lib/chan.ts 逻辑一致。

包含处理 -> 分型 -> 笔 -> 中枢 -> 买卖点(含 MACD 背驰)。非 LLM。
灵感来自「观潮 TideView」(闭源商业产品)的缠论标注能力,此为独立简化实现。
"""
from __future__ import annotations

from typing import Optional

from ..models import Bar
from . import indicators as ind


def _merge_inclusion(bars: list[Bar]) -> list[dict]:
    out: list[dict] = []
    for i, b in enumerate(bars):
        if not out:
            out.append({"idx": i, "high": b.high, "low": b.low})
            continue
        prev = out[-1]
        contains = (prev["high"] >= b.high and prev["low"] <= b.low) or (b.high >= prev["high"] and b.low <= prev["low"])
        if contains:
            up = prev["high"] > out[-2]["high"] if len(out) >= 2 else b.high > prev["high"]
            if up:
                prev["high"], prev["low"] = max(prev["high"], b.high), max(prev["low"], b.low)
            else:
                prev["high"], prev["low"] = min(prev["high"], b.high), min(prev["low"], b.low)
            prev["idx"] = i
        else:
            out.append({"idx": i, "high": b.high, "low": b.low})
    return out


def _fractals(mk: list[dict]) -> list[dict]:
    fs: list[dict] = []
    for i in range(1, len(mk) - 1):
        a, b, c = mk[i - 1], mk[i], mk[i + 1]
        if b["high"] > a["high"] and b["high"] > c["high"]:
            fs.append({"idx": b["idx"], "price": b["high"], "type": "top"})
        elif b["low"] < a["low"] and b["low"] < c["low"]:
            fs.append({"idx": b["idx"], "price": b["low"], "type": "bottom"})
    return fs


def _strokes(fs: list[dict], mk: list[dict]) -> list[dict]:
    pos = {m["idx"]: i for i, m in enumerate(mk)}
    valid: list[dict] = []
    for f in fs:
        if not valid:
            valid.append(f); continue
        last = valid[-1]
        if f["type"] == last["type"]:
            if (f["type"] == "top" and f["price"] > last["price"]) or (f["type"] == "bottom" and f["price"] < last["price"]):
                valid[-1] = f
        else:
            gap = abs(pos.get(f["idx"], 0) - pos.get(last["idx"], 0))
            if gap >= 2:
                valid.append(f)
            elif (f["type"] == "top" and f["price"] > last["price"]) or (f["type"] == "bottom" and f["price"] < last["price"]):
                valid[-1] = f
    st: list[dict] = []
    for i in range(1, len(valid)):
        st.append({"from": valid[i - 1], "to": valid[i],
                   "dir": "up" if valid[i]["price"] > valid[i - 1]["price"] else "down", "area": 0.0})
    return st


def _pivots(st: list[dict]) -> list[dict]:
    ps: list[dict] = []
    for i in range(len(st) - 2):
        segs = [st[i], st[i + 1], st[i + 2]]
        zd = max(min(s["from"]["price"], s["to"]["price"]) for s in segs)
        zg = min(max(s["from"]["price"], s["to"]["price"]) for s in segs)
        if zg > zd:
            ps.append({"zg": zg, "zd": zd, "start_idx": st[i]["from"]["idx"], "end_idx": st[i + 2]["to"]["idx"]})
    return ps[-2:]


def _buy_sell_points(st: list[dict], pivots: list[dict]) -> list[dict]:
    pts: list[dict] = []
    if len(st) < 3:
        return pts
    downs = [s for s in st if s["dir"] == "down"]
    ups = [s for s in st if s["dir"] == "up"]
    if len(downs) >= 2 and downs[-1]["to"]["price"] < downs[-2]["to"]["price"] and abs(downs[-1]["area"]) < abs(downs[-2]["area"]):
        pts.append({"idx": downs[-1]["to"]["idx"], "price": downs[-1]["to"]["price"], "kind": "1B", "detail": "底背驰"})
    if len(ups) >= 2 and ups[-1]["to"]["price"] > ups[-2]["to"]["price"] and abs(ups[-1]["area"]) < abs(ups[-2]["area"]):
        pts.append({"idx": ups[-1]["to"]["idx"], "price": ups[-1]["to"]["price"], "kind": "1S", "detail": "顶背驰"})
    if pivots:
        piv = pivots[-1]
        for s in st:
            if s["to"]["idx"] <= piv["end_idx"]:
                continue
            if s["dir"] == "down" and s["to"]["type"] == "bottom" and s["to"]["price"] > piv["zg"]:
                pts.append({"idx": s["to"]["idx"], "price": s["to"]["price"], "kind": "3B", "detail": f"回踩不破 ZG {piv['zg']:.2f}"}); break
            if s["dir"] == "up" and s["to"]["type"] == "top" and s["to"]["price"] < piv["zd"]:
                pts.append({"idx": s["to"]["idx"], "price": s["to"]["price"], "kind": "3S", "detail": f"反抽不破 ZD {piv['zd']:.2f}"}); break
    return sorted(pts, key=lambda p: p["idx"])


def compute_chan(bars: list[Bar]) -> dict:
    if len(bars) < 8:
        return {"fractals": [], "strokes": [], "pivots": [], "points": [], "note": "数据不足,无法识别缠论结构"}
    mk = _merge_inclusion(bars)
    fs = _fractals(mk)
    st = _strokes(fs, mk)

    closes = [b.close for b in bars]
    _, _, hist = ind.macd(closes)
    for s in st:
        a, b = s["from"]["idx"], s["to"]["idx"]
        s["area"] = sum(h for h in hist[min(a, b):max(a, b) + 1] if h is not None)

    ps = _pivots(st)
    pts = _buy_sell_points(st, ps)

    def t(i: int) -> str:
        return bars[i].ts.isoformat()

    last_stroke = st[-1] if st else None
    last_piv = ps[-1] if ps else None
    price = bars[-1].close
    note = ""
    if last_stroke:
        note += f"当前为{'向上' if last_stroke['dir'] == 'up' else '向下'}笔。"
    if last_piv:
        loc = "中枢上方(强势)" if price > last_piv["zg"] else "中枢下方(弱势)" if price < last_piv["zd"] else "中枢震荡区内"
        note += f"最近中枢 [{last_piv['zd']:.2f}, {last_piv['zg']:.2f}],价格位于{loc}。"
    else:
        note += "暂未形成有效中枢。"
    if pts:
        note += f"最近买卖点:{pts[-1]['kind']}({pts[-1]['detail']})。"
    note += " 简化缠论,仅供参考,非投资建议。"

    return {
        "fractals": [{"time": t(f["idx"]), "price": f["price"], "type": f["type"]} for f in fs],
        "strokes": [{"from_time": t(s["from"]["idx"]), "to_time": t(s["to"]["idx"]),
                     "from_price": s["from"]["price"], "to_price": s["to"]["price"],
                     "dir": s["dir"], "area": s["area"]} for s in st],
        "pivots": [{"zg": p["zg"], "zd": p["zd"], "start_time": t(p["start_idx"]), "end_time": t(p["end_idx"])} for p in ps],
        "points": [{"time": t(p["idx"]), "price": p["price"], "kind": p["kind"], "detail": p["detail"]} for p in pts],
        "note": note,
    }
