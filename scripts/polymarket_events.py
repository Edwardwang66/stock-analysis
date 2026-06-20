#!/usr/bin/env python3
"""Polymarket 事件概率因子 → feed/events/latest.json。

来源:research/agents-scan(Polymarket agents 调研)+ 既有调研把预测市场列为「可作 meta-labeling
外部预测因子」。本脚本**只读**拉取金融/宏观相关市场的隐含概率(Fed 降息/衰退/CPI/BTC 目标价等),
作为**外部事件/不确定性因子**喂入 feed 与看板。**不下注**(longshot 偏差 + 美国辖区限制 + 链上风险)。

数据:Gamma API `gamma-api.polymarket.com/markets` **免鉴权免费**(本轮实测)。
诚实:预测市场校准良好但有 **favorite-longshot 偏差**(极端概率偏置)——脚本标注 longshot 区间,
不做激进校准(避免又一层过拟合);隐含概率=市场价格,不等于真实概率。

纯逻辑(is_relevant / parse_market / longshot_flag)与网络分离,可离线单测。仅标准库。

用法:python scripts/polymarket_events.py [--limit 200] [--top 25]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feed" / "events" / "latest.json"
UA = {"User-Agent": "stock-analysis-dashboard admin@example.com"}

# 金融/宏观相关关键词(小写匹配 question);命中即纳入。
RELEVANT_KW = [
    "fed", "interest rate", "rate cut", "rate hike", "fomc", "powell", "recession",
    "cpi", "inflation", "gdp", "unemployment", "jobs report", "nonfarm", "treasury",
    "yield", "tariff", "s&p", "sp500", "s&p 500", "nasdaq", "dow ", "stock market",
    "bitcoin", "btc", "ethereum", " eth ", "crypto", "solana", "microstrategy",
    "nvidia", "tesla", "apple", "rate decision", "debt ceiling", "default",
    "ipo", "fed chair", "russell",
]
# 排除明显无关的高量市场(体育等),即便偶然命中关键词
EXCLUDE_KW = ["world cup", "fifa", "super bowl", "nba ", "nfl ", "premier league",
              "champions league", "uefa", "ballon", "oscar", "grammy"]


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


# ----------------------------- 纯逻辑(可离线单测)-----------------------------

def is_relevant(question: str) -> bool:
    q = (question or "").lower()
    if any(x in q for x in EXCLUDE_KW):
        return False
    return any(kw in q for kw in RELEVANT_KW)


def _loads(x):
    """Gamma 的 outcomes / outcomePrices 可能是 JSON 字符串或已是 list。"""
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except (ValueError, TypeError):
            return []
    return []


def longshot_flag(p: float) -> bool:
    """极端概率区间(longshot/重仓 favorite),favorite-longshot 偏差最大,谨慎解读。"""
    return p is not None and (p >= 0.90 or p <= 0.10)


def parse_market(m: dict) -> dict | None:
    """从 Gamma market 对象抽取:问题 / Yes 概率 / 成交量 / 流动性 / 截止日。Yes-No 二元优先。"""
    q = m.get("question")
    if not q:
        return None
    outcomes = _loads(m.get("outcomes"))
    prices = _loads(m.get("outcomePrices"))
    if not outcomes or not prices or len(outcomes) != len(prices):
        return None
    try:
        pf = [float(x) for x in prices]
    except (ValueError, TypeError):
        return None
    # 二元 Yes/No:取 Yes 概率;多元:取最高概率结果
    prob, outcome, oidx = None, None, 0
    low = [o.lower() for o in outcomes]
    if "yes" in low:
        oidx = low.index("yes")
        prob, outcome = pf[oidx], "Yes"
    else:
        oidx = int(max(range(len(pf)), key=lambda k: pf[k]))
        prob, outcome = pf[oidx], outcomes[oidx]
    def num(k):
        v = m.get(k)
        try:
            return float(v) if v is not None else None
        except (ValueError, TypeError):
            return None
    # 所选结果对应的 CLOB token id(用于拉历史隐含概率)
    tokens = _loads(m.get("clobTokenIds"))
    token_id = tokens[oidx] if oidx < len(tokens) else None
    return {
        "question": q,
        "outcome": outcome,
        "prob": round(prob, 4),
        "prob_pct": round(prob * 100, 1),
        "longshot": longshot_flag(prob),
        "volume_usd": num("volumeNum") or num("volume"),
        "liquidity_usd": num("liquidityNum") or num("liquidity"),
        "end_date": m.get("endDate"),
        "slug": m.get("slug"),
        "token_id": token_id,
    }


def history_features(history: list[dict], days: tuple = (7, 30)) -> dict:
    """从 prices-history([{t,p}])算各窗口隐含概率变化 + 末段火花线。t 为 unix 秒,p∈[0,1]。"""
    pts = sorted((h for h in history if h.get("t") and h.get("p") is not None),
                 key=lambda h: h["t"])
    if len(pts) < 2:
        return {}
    last_t, last_p = pts[-1]["t"], float(pts[-1]["p"])
    out = {}
    for d in days:
        cutoff = last_t - d * 86400
        prior = [h for h in pts if h["t"] <= cutoff]
        ref = prior[-1] if prior else pts[0]   # 不足 d 天则用最早点(诚实:窗口不满)
        out[f"prob_chg_{d}d"] = round(last_p - float(ref["p"]), 4)
    out["spark"] = [round(float(h["p"]), 3) for h in pts[-12:]]
    return out


# ----------------------------- 网络 + CLI -----------------------------

def fetch_markets(limit: int = 300, page: int = 100) -> list[dict]:
    """按成交量降序分页拉取(Gamma 每页上限 ~100,金融市场常在体育之后,需翻页)。"""
    out: list[dict] = []
    offset = 0
    while len(out) < limit:
        qs = urllib.parse.urlencode({"closed": "false", "order": "volumeNum",
                                     "ascending": "false", "limit": page, "offset": offset})
        try:
            data = json.loads(_get(f"https://gamma-api.polymarket.com/markets?{qs}"))
        except Exception:  # noqa: BLE001  深翻页可能 422,容错停止
            break
        batch = data if isinstance(data, list) else data.get("data", [])
        if not batch:
            break
        out.extend(batch)
        offset += page
        if len(batch) < page:
            break
    return out


def fetch_history(token_id: str, interval: str = "1m", fidelity: int = 1440) -> list[dict]:
    """CLOB prices-history(免鉴权):返回 [{t,p}] 隐含概率时序。失败返回 []。"""
    if not token_id:
        return []
    qs = urllib.parse.urlencode({"market": token_id, "interval": interval, "fidelity": fidelity})
    try:
        d = json.loads(_get(f"https://clob.polymarket.com/prices-history?{qs}"))
        return d.get("history", []) if isinstance(d, dict) else []
    except Exception:  # noqa: BLE001
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Polymarket 事件概率因子")
    ap.add_argument("--limit", type=int, default=300, help="拉取的市场数(按成交量降序)")
    ap.add_argument("--top", type=int, default=25, help="输出的相关市场上限")
    ap.add_argument("--no-trend", action="store_true", help="跳过 prices-history 趋势(更快)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    try:
        raw = fetch_markets(args.limit)
    except Exception as e:  # noqa: BLE001
        print(f"抓取失败:{e}", file=sys.stderr)
        return 1
    rel = []
    for m in raw:
        if not is_relevant(m.get("question", "")):
            continue
        pm = parse_market(m)
        if pm and pm.get("volume_usd"):
            rel.append(pm)
    rel.sort(key=lambda x: -(x.get("volume_usd") or 0))
    rel = rel[:args.top]

    # 趋势富集:对入选市场拉历史隐含概率,算 7d/30d 变化 + 火花线(信念动量比水平更有信息)
    if not args.no_trend:
        import time as _t
        for m in rel:
            feats = history_features(fetch_history(m.get("token_id")))
            m.update(feats)
            m.pop("token_id", None)
            _t.sleep(0.1)
    else:
        for m in rel:
            m.pop("token_id", None)

    doc = {
        "schema_version": "1.0",
        "kind": "event_probabilities",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Polymarket Gamma API (keyless, read-only)",
        "note": ("预测市场隐含概率=市场价格,非真实概率;有 favorite-longshot 偏差(已标 longshot)。"
                 "外部事件/不确定性因子,**非下注信号、非投资建议**。"),
        "n_markets": len(rel),
        "markets": rel,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"写入 {out_path}:{len(rel)} 个金融/宏观相关市场")
    for m in rel[:12]:
        ls = " ⚠longshot" if m["longshot"] else ""
        c30 = m.get("prob_chg_30d")
        trend = f"  ({c30*100:+.0f}pp/30d)" if c30 is not None else ""
        print(f"  {m['prob_pct']:5.1f}%{trend}  {m['question'][:55]}{ls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
