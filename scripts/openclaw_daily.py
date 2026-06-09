#!/usr/bin/env python3
"""OpenClaw 每日调度骨架 —— 拉选股清单 + 自选 → 遍历 → 投递。

管道已写好(拉取/遍历/投递/校验);你只需把 analyze_stock() / analyze_role()
接到你的 OpenClaw/Claude(让它按 prompt 做真分析,返回 dict)。
不接也能跑:默认产出占位模板,用于先打通链路。

用法:
  # 先打通(本地写占位,不联网投递)
  python scripts/openclaw_daily.py --mode local
  # 真投递(需 GITHUB_TOKEN;量化报告另需 FEED_HMAC_SECRET)
  GITHUB_TOKEN=... FEED_HMAC_SECRET=... python scripts/openclaw_daily.py --mode github-api
  python scripts/openclaw_daily.py --stocks-only --top 10 --watchlist watchlist.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402
import openclaw_client as oc  # noqa: E402

SCREENER_URL = "https://raw.githubusercontent.com/edwardwang66/stock-analysis/main/feed/screener/latest.json"


# ======================================================================
# 把下面两个函数接到你的 OpenClaw / Claude —— 这是「真分析」发生的地方。
# 现在是占位实现:返回模板,便于先把投递链路跑通。
# ======================================================================
def analyze_stock(symbol: str, name: str, screener_item: dict | None) -> dict:
    """TODO: 调你的 OpenClaw,用 docs/openclaw-stock-notes.md 的 stock-analyst prompt,
    基于真实行情/财报/新闻产出 {stance,thesis,earnings,news,risks,view,sources}。"""
    note = oc.stock_note_template(symbol)
    note["view"] = f"[占位] {name} 待 OpenClaw 真分析。把 analyze_stock() 接到你的 Claude 即可。"
    return note


def analyze_role(role: str, context: dict) -> dict:
    """TODO: 调你的 OpenClaw,用 routines/openclaw-agent-prompts.md 对应角色 prompt,
    基于真实数据产出符合 feed/schema/report.schema.json 的报告(含信封)。"""
    return oc.sample_report(role)  # 占位:示例报告


# ======================================================================
# 以下为管道,通常无需改动。
# ======================================================================
def fetch_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"[daily] 拉取失败 {url}: {e}")
        return None


def load_universe(top: int, watchlist: str | None, screener_file: str | None) -> list[tuple[str, str, dict | None]]:
    # 看多清单 = 选股清单 items(全是评分≥50「强烈看多」)。top<=0 取全部。
    scr = fl.load_json(screener_file) if screener_file else fetch_json(SCREENER_URL)
    all_items = (scr or {}).get("items", [])
    items = all_items if top <= 0 else all_items[:top]
    uni: dict[str, tuple[str, dict | None]] = {}
    for it in items:
        sym = f"US:{it['symbol']}"
        uni[sym] = (it.get("name", it["symbol"]), it)
    if watchlist and os.path.exists(watchlist):
        for line in open(watchlist):
            s = line.strip().upper()
            if s and ":" in s:
                uni.setdefault(s, (s.split(":")[1], None))
    return [(s, n, i) for s, (n, i) in uni.items()]


def dispatch_stock(note: dict, mode: str, repo: str, token: str | None):
    rel = oc.stock_note_relpath(note["symbol"])
    if mode == "local":
        fl.save_json(os.path.join(fl.REPO_ROOT, rel), note)
        print(f"[daily] 本地写入 {rel}")
    else:
        oc.put_github_path(note, repo, token, rel, f"openclaw: 个股解读 {note['symbol']} {note['date']}")


def dispatch_role(report: dict, mode: str, repo: str, token: str | None, secret: str | None):
    if secret:
        fl.sign_report(report, secret)
    ok, errs = fl.validate_report(report)
    if not ok:
        print(f"[daily] 报告校验失败 {report.get('id')}: {errs}")
        return
    if mode == "local":
        oc.post_local(report)
    else:
        oc.post_dispatch(report, repo, token)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "github-api", "dispatch"], default="local")
    ap.add_argument("--top", type=int, default=15, help="看多清单取前 N 只(0=全部看多清单)")
    ap.add_argument("--watchlist", default=os.environ.get("OPENCLAW_WATCHLIST"))
    ap.add_argument("--screener-file", default=None)
    ap.add_argument("--repo", default=os.environ.get("OPENCLAW_REPO", oc.DEFAULT_REPO))
    ap.add_argument("--stocks-only", action="store_true")
    ap.add_argument("--roles-only", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("OPENCLAW_TOKEN")
    secret = os.environ.get("FEED_HMAC_SECRET")
    if args.mode != "local" and not token:
        print("[daily] 非 local 模式需 GITHUB_TOKEN/OPENCLAW_TOKEN"); sys.exit(2)

    # 任务 A:个股解读
    if not args.roles_only:
        uni = load_universe(args.top, args.watchlist, args.screener_file)
        print(f"[daily] 个股解读 {len(uni)} 只(mode={args.mode})")
        for sym, name, item in uni:
            try:
                note = analyze_stock(sym, name, item)
                dispatch_stock(note, args.mode, args.repo, token)
            except Exception as e:  # noqa: BLE001
                print(f"[daily] {sym} 失败: {e}")

    # 任务 B:量化 5 角色
    if not args.stocks_only:
        ctx = {"market": fetch_json(SCREENER_URL.replace("screener/latest.json", "market/state.json")),
               "signals": fetch_json(SCREENER_URL.replace("screener/latest.json", "signals/latest.json"))}
        print(f"[daily] 量化 5 角色(mode={args.mode})")
        for role in oc.ROLES:
            try:
                rep = analyze_role(role, ctx)
                dispatch_role(rep, args.mode, args.repo, token, secret)
            except Exception as e:  # noqa: BLE001
                print(f"[daily] 角色 {role} 失败: {e}")

    print("[daily] 完成。")


if __name__ == "__main__":
    main()
