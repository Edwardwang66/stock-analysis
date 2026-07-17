#!/usr/bin/env python3
"""Pre-IPO / 24-7 代理价历史积累(hyperliquid-monitor 每 2h 顺手追加)。

从 feed/crypto/state.json 摘取关键标的 mark 价,追加进
feed/crypto/preipo-history.json(保留 1200 点 ≈ 100 天 @2h)。
积累后可画:AI 私有公司(SpaceX/Anthropic/OpenAI)估值曲线、
存储链美股永续的夜盘轨迹。幂等:同一 updated_at 不重复追加。
"""
from __future__ import annotations

import json
from pathlib import Path

import feed_lib as fl

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "feed" / "crypto" / "state.json"
OUT = ROOT / "feed" / "crypto" / "preipo-history.json"
KEEP = 1200


def main() -> int:
    try:
        st = json.loads(
            STATE.read_text(),
            parse_constant=fl.reject_json_constant,
        )
    except Exception:  # noqa: BLE001
        print("state.json 不可读,跳过")
        return 0
    ep = st.get("equity_perps") or {}
    marks: dict[str, float] = {}
    for grp in ("private", "indices", "stocks"):
        for x in ep.get(grp) or []:
            sym, mark = x.get("symbol"), x.get("mark")
            if sym and isinstance(mark, (int, float)):
                marks[sym] = round(float(mark), 4)
    if not marks:
        print("无 equity_perps 数据,跳过")
        return 0

    hist: list = []
    try:
        hist = json.loads(
            OUT.read_text(),
            parse_constant=fl.reject_json_constant,
        )
    except Exception:  # noqa: BLE001
        pass
    at = st.get("updated_at")
    if hist and hist[-1].get("at") == at:
        print("同一快照,跳过")
        return 0
    hist.append({"at": at, "marks": marks})
    hist = hist[-KEEP:]
    fl.save_json(str(OUT), hist)
    print(f"preipo-history: +1 → {len(hist)} 点({len(marks)} 标的)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
