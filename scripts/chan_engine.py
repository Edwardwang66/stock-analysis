#!/usr/bin/env python3
"""缠论引擎(Python 版,与 frontend/lib/chan.ts 同口径)+ 全宇宙买卖点胜率统计。

口径(methodology §4,原文 24 课近似):
  包含合并 → 分型 → 笔(简化:合并K序号差≥2)→ 中枢(连续3笔重叠)→
  三类买卖点 + 背驰(同色 MACD 柱面积按笔端点截取)。

用法:
  python scripts/chan_engine.py            # 全宇宙(标普500∪纳指100)统计 → feed/signals/chan-stats.json
  python scripts/chan_engine.py --limit 30 # 调试小样本
统计:每类买卖点(1B/2B/3B/1S/2S/3S)在 +5/+20 根后的胜率与平均收益
  (买点算涨为胜,卖点算跌为胜);并输出「当前正处于买卖点附近(最近3根内)」的标的清单。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "feed" / "signals" / "chan-stats.json"

# 复用 daily_screener 的宇宙加载与K线抓取(同一套 httpx 逻辑)
from daily_screener import fetch_bars, load_universe  # noqa: E402
import httpx  # noqa: E402


# ── 与 chan.ts 一一对应的结构识别 ──

def ema(v: list[float], p: int) -> list[float | None]:
    out: list[float | None] = [None] * len(v)
    if len(v) < p:
        return out
    k = 2 / (p + 1)
    s = sum(v[:p]) / p
    out[p - 1] = s
    for i in range(p, len(v)):
        s = v[i] * k + s * (1 - k)
        out[i] = s
    return out


def macd_parts(closes: list[float]) -> tuple[list[float | None], list[float | None]]:
    ef, es = ema(closes, 12), ema(closes, 26)
    line: list[float | None] = [a - b if a is not None and b is not None else None for a, b in zip(ef, es)]
    idx = [i for i, x in enumerate(line) if x is not None]
    sig: list[float | None] = [None] * len(closes)
    if len(idx) >= 9:
        seq = [line[i] for i in idx]
        es2 = ema(seq, 9)  # type: ignore[arg-type]
        for j, i in enumerate(idx):
            sig[i] = es2[j]
    hist = [a - b if a is not None and b is not None else None for a, b in zip(line, sig)]
    return hist, line


def merge_inclusion(bars) -> list[dict]:
    out: list[dict] = []
    for i, b in enumerate(bars):
        if not out:
            out.append({"time": b.time, "high": b.high, "low": b.low, "idx": i})
            continue
        prev = out[-1]
        contains = (prev["high"] >= b.high and prev["low"] <= b.low) or (b.high >= prev["high"] and b.low <= prev["low"])
        if contains:
            up = out[-2]["high"] < prev["high"] if len(out) >= 2 else b.high > prev["high"]
            if up:
                prev["high"] = max(prev["high"], b.high)
                prev["low"] = max(prev["low"], b.low)
            else:
                prev["high"] = min(prev["high"], b.high)
                prev["low"] = min(prev["low"], b.low)
            prev["time"] = b.time
            prev["idx"] = i
        else:
            out.append({"time": b.time, "high": b.high, "low": b.low, "idx": i})
    return out


def find_fractals(mk: list[dict]) -> list[dict]:
    fs = []
    for i in range(1, len(mk) - 1):
        a, b, c = mk[i - 1], mk[i], mk[i + 1]
        if b["high"] > a["high"] and b["high"] > c["high"]:
            fs.append({"time": b["time"], "price": b["high"], "type": "top", "idx": b["idx"]})
        elif b["low"] < a["low"] and b["low"] < c["low"]:
            fs.append({"time": b["time"], "price": b["low"], "type": "bottom", "idx": b["idx"]})
    return fs


def build_strokes(fs: list[dict], mk: list[dict]) -> list[dict]:
    pos = {m["idx"]: i for i, m in enumerate(mk)}
    valid: list[dict] = []
    for f in fs:
        if not valid:
            valid.append(f)
            continue
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
    st = []
    for i in range(1, len(valid)):
        st.append({"frm": valid[i - 1], "to": valid[i],
                   "dir": "up" if valid[i]["price"] > valid[i - 1]["price"] else "down", "area": 0.0})
    return st


def find_pivots(st: list[dict]) -> list[dict]:
    ps = []
    for i in range(len(st) - 2):
        segs = [{"hi": max(s["frm"]["price"], s["to"]["price"]), "lo": min(s["frm"]["price"], s["to"]["price"])}
                for s in st[i:i + 3]]
        zd = max(s["lo"] for s in segs)
        zg = min(s["hi"] for s in segs)
        if zg > zd:
            ps.append({"zg": zg, "zd": zd, "startTime": st[i]["frm"]["time"], "endTime": st[i + 2]["to"]["time"]})
    return ps[-2:]


def find_pivots_hist(st: list[dict]) -> list[dict]:
    """全历史中枢(贪心不重叠:成枢即跳到枢后继续)。"""
    ps = []
    i = 0
    while i + 2 < len(st):
        segs = [{"hi": max(s["frm"]["price"], s["to"]["price"]), "lo": min(s["frm"]["price"], s["to"]["price"])}
                for s in st[i:i + 3]]
        zd = max(s["lo"] for s in segs)
        zg = min(s["hi"] for s in segs)
        if zg > zd:
            ps.append({"zg": zg, "zd": zd, "startTime": st[i]["frm"]["time"], "endTime": st[i + 2]["to"]["time"]})
            i += 3
        else:
            i += 1
    return ps


def buy_sell_points_hist(st: list[dict], pivots_all: list[dict]) -> list[dict]:
    """全历史买卖点(真回测口径):每个同向笔对/每个中枢/每个1B后都检查,不止最后一组。"""
    pts: list[dict] = []
    # 1B/1S:所有相邻同向笔对(隔一笔反向)
    for i in range(2, len(st)):
        c, a = st[i], st[i - 2]
        if c["dir"] != a["dir"]:
            continue
        if c["dir"] == "down" and c["to"]["price"] < a["to"]["price"] and abs(c["area"]) < abs(a["area"]):
            pts.append({"time": c["to"]["time"], "price": c["to"]["price"], "kind": "1B"})
        elif c["dir"] == "up" and c["to"]["price"] > a["to"]["price"] and abs(c["area"]) < abs(a["area"]):
            pts.append({"time": c["to"]["time"], "price": c["to"]["price"], "kind": "1S"})
    # 3B/3S:离开方向决定买卖——向上离开后第一个回踩不破 zg → 3B;向下离开后第一个反抽不上 zd → 3S。
    # (原实现只看枢后第一笔,「离开笔在前、回踩笔在后」的标准形态会漏检)
    for piv in pivots_all:
        after = [s for s in st if s["to"]["time"] > piv["endTime"]]
        if not after:
            continue
        if after[0]["dir"] == "up":
            pb = next((s for s in after if s["dir"] == "down" and s["to"]["type"] == "bottom"), None)
            if pb and pb["to"]["price"] > piv["zg"]:
                pts.append({"time": pb["to"]["time"], "price": pb["to"]["price"], "kind": "3B"})
        else:
            bo = next((s for s in after if s["dir"] == "up" and s["to"]["type"] == "top"), None)
            if bo and bo["to"]["price"] < piv["zd"]:
                pts.append({"time": bo["to"]["time"], "price": bo["to"]["price"], "kind": "3S"})
    # 2B/2S:每个 1B/1S 之后第一个不破前低的底 / 不破前高的顶
    for p in [x for x in pts if x["kind"] == "1B"]:
        after = next((s for s in st if s["dir"] == "down" and s["to"]["type"] == "bottom"
                      and s["to"]["time"] > p["time"] and s["to"]["price"] > p["price"]), None)
        if after:
            pts.append({"time": after["to"]["time"], "price": after["to"]["price"], "kind": "2B"})
    for p in [x for x in pts if x["kind"] == "1S"]:
        after = next((s for s in st if s["dir"] == "up" and s["to"]["type"] == "top"
                      and s["to"]["time"] > p["time"] and s["to"]["price"] < p["price"]), None)
        if after:
            pts.append({"time": after["to"]["time"], "price": after["to"]["price"], "kind": "2S"})
    seen = set()
    out = []
    for p in sorted(pts, key=lambda x: x["time"]):
        k = (p["time"], p["kind"])
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def buy_sell_points(st: list[dict], pivots: list[dict]) -> list[dict]:
    pts: list[dict] = []
    if len(st) < 3:
        return pts
    downs = [s for s in st if s["dir"] == "down"]
    ups = [s for s in st if s["dir"] == "up"]
    if len(downs) >= 2:
        last, prev = downs[-1], downs[-2]
        if last["to"]["price"] < prev["to"]["price"] and abs(last["area"]) < abs(prev["area"]):
            pts.append({"time": last["to"]["time"], "price": last["to"]["price"], "kind": "1B"})
    if len(ups) >= 2:
        last, prev = ups[-1], ups[-2]
        if last["to"]["price"] > prev["to"]["price"] and abs(last["area"]) < abs(prev["area"]):
            pts.append({"time": last["to"]["time"], "price": last["to"]["price"], "kind": "1S"})
    if pivots:
        piv = pivots[-1]
        for s in st:
            if s["to"]["time"] <= piv["endTime"]:
                continue
            if s["dir"] == "down" and s["to"]["type"] == "bottom" and s["to"]["price"] > piv["zg"]:
                pts.append({"time": s["to"]["time"], "price": s["to"]["price"], "kind": "3B"})
                break
            if s["dir"] == "up" and s["to"]["type"] == "top" and s["to"]["price"] < piv["zd"]:
                pts.append({"time": s["to"]["time"], "price": s["to"]["price"], "kind": "3S"})
                break
    one_b = next((p for p in pts if p["kind"] == "1B"), None)
    if one_b:
        after = next((s for s in st if s["dir"] == "down" and s["to"]["type"] == "bottom"
                      and s["to"]["time"] > one_b["time"] and s["to"]["price"] > one_b["price"]), None)
        if after:
            pts.append({"time": after["to"]["time"], "price": after["to"]["price"], "kind": "2B"})
    one_s = next((p for p in pts if p["kind"] == "1S"), None)
    if one_s:
        after = next((s for s in st if s["dir"] == "up" and s["to"]["type"] == "top"
                      and s["to"]["time"] > one_s["time"] and s["to"]["price"] < one_s["price"]), None)
        if after:
            pts.append({"time": after["to"]["time"], "price": after["to"]["price"], "kind": "2S"})
    seen = set()
    out = []
    for p in sorted(pts, key=lambda x: x["time"]):
        k = (p["time"], p["kind"])
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def analyze_symbol(bars) -> list[dict]:
    """全历史滚动识别买卖点:对每个时点 t(≥60 根),用截至 t 的数据找『新出现』的买卖点。
    简化为:整段识别一次(端点即信号时点)——与前端一致,统计意义足够。"""
    if len(bars) < 60:
        return []
    mk = merge_inclusion(bars)
    fs = find_fractals(mk)
    st = build_strokes(fs, mk)
    if not st:
        return []
    closes = [b.close for b in bars]
    hist, _ = macd_parts(closes)
    idx_by_time = {b.time: i for i, b in enumerate(bars)}
    for s in st:
        a, b2 = idx_by_time.get(s["frm"]["time"], 0), idx_by_time.get(s["to"]["time"], 0)
        total = 0.0
        for i in range(min(a, b2), max(a, b2) + 1):
            h = hist[i]
            if h is None:
                continue
            if s["dir"] == "up" and h > 0:
                total += h
            elif s["dir"] == "down" and h < 0:
                total += h
        s["area"] = total
    ps = find_pivots_hist(st)
    pts = buy_sell_points_hist(st, ps)
    # 事后表现
    out = []
    for p in pts:
        i = idx_by_time.get(p["time"])
        if i is None:
            continue
        r5 = (bars[i + 5].close / p["price"] - 1) * 100 if i + 5 < len(bars) else None
        r20 = (bars[i + 20].close / p["price"] - 1) * 100 if i + 20 < len(bars) else None
        recent = i >= len(bars) - 3
        out.append({**p, "r5": r5, "r20": r20, "recent": recent})
    return out


async def run(limit: int) -> int:
    async with httpx.AsyncClient() as client:
        uni = await load_universe(client)
        tickers = list(uni.items())[:limit] if limit > 0 else list(uni.items())
        print(f"[chan] 扫描 {len(tickers)} 只…")
        sem = asyncio.Semaphore(10)

        async def one(tk: str):
            async with sem:
                try:
                    raw = await fetch_bars(client, tk)
                    if not raw:
                        return tk, []
                    # backend Bar 用 ts(datetime);引擎统一为 time(epoch 秒)
                    from types import SimpleNamespace
                    bars = [SimpleNamespace(time=int(b.ts.timestamp()), high=b.high, low=b.low, close=b.close)
                            for b in raw]
                    return tk, analyze_symbol(bars)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {tk}: {e}", file=sys.stderr)
                    return tk, []

        results = await asyncio.gather(*[one(t) for t, _ in tickers])

    stats: dict[str, dict] = {}
    active: list[dict] = []
    for tk, pts in results:
        for p in pts:
            k = p["kind"]
            s = stats.setdefault(k, {"n5": 0, "win5": 0, "sum5": 0.0, "n20": 0, "win20": 0, "sum20": 0.0})
            is_buy = k.endswith("B")
            if p["r5"] is not None:
                s["n5"] += 1
                s["sum5"] += p["r5"]
                if (p["r5"] > 0) == is_buy:
                    s["win5"] += 1
            if p["r20"] is not None:
                s["n20"] += 1
                s["sum20"] += p["r20"]
                if (p["r20"] > 0) == is_buy:
                    s["win20"] += 1
            if p["recent"]:
                active.append({"symbol": tk, "kind": k, "price": round(p["price"], 2)})

    table = {}
    for k, s in sorted(stats.items()):
        table[k] = {
            "d5": {"n": s["n5"], "win_rate": round(s["win5"] / s["n5"], 3) if s["n5"] else None,
                    "avg_ret": round(s["sum5"] / s["n5"], 2) if s["n5"] else None},
            "d20": {"n": s["n20"], "win_rate": round(s["win20"] / s["n20"], 3) if s["n20"] else None,
                     "avg_ret": round(s["sum20"] / s["n20"], 2) if s["n20"] else None},
        }
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universe": len(results),
        "stats": table,
        "active": sorted(active, key=lambda x: x["kind"])[:40],
        "note": "全宇宙缠论买卖点统计(简化口径=chan.ts 同源);买点胜=之后上涨,卖点胜=之后下跌;active=最近3根内出现的买卖点。非投资建议。",
    }
    # 空结果保护:数据源整体故障时不要用空统计覆盖旧数据(保留旧文件并以失败退出,让 CI 暴露问题)
    if not table and OUT.exists():
        print("[chan] 全宇宙 0 个买卖点——疑似数据源故障,保留旧统计不覆盖", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    npts = sum(v["d5"]["n"] for v in table.values()) if table else 0
    print(f"[chan] 统计 {npts} 个买卖点(d5 样本)· 进行中信号 {len(active)} 个 → {OUT.name}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    raise SystemExit(asyncio.run(run(a.limit)))
