"""S&P500 时点成分(PIT membership)重建 + 幸存者偏差量化(Cycle 9)。

免费消偏差路径第一步(docs/survivorship-bias-data-sources.md):
  - 数据源:Wikipedia「List of S&P 500 companies」=当前成分表 + 历史变更表(日期/加入/移除)。
  - 重建:从当前成分出发,按变更逆序回放(query 日之后的每次变更反向应用),
    得到任意历史日期的成分集合 membership_asof(date)。
  - 量化:每年 1 月 1 日的成分中,①已不在当前名单的比例(流失率);
    ②流失者中 Yahoo 已无数据的比例(抽样实测)→ **数据缺失率 = 流失率 × 不可得率**。
    这把「幸存者偏差」从一句免责声明变成逐年可测的数字。

产出:
  backtest/pit_sp500.json                  当前成分+变更事件缓存(可复现)
  docs/study-pit-membership-<date>.md      逐年流失率/缺失率表 + 对现有结论的折扣建议
  (--publish) feed 报告

用法: python backtest/pit_membership.py [--publish] [--sample 30]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import data as datamod  # noqa: E402

WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CACHE = os.path.join(HERE, "pit_sp500.json")
SEED = 500


def _clean(c: str) -> str:
    c = re.sub(r"<[^>]+>", "", c)
    return c.replace("&amp;", "&").replace("&#91;", "[").replace("&#93;", "]").strip()


def fetch_tables(force: bool = False) -> dict:
    """{current: {ticker: sector}, changes: [{date, added, removed}]}(缓存落盘)。"""
    if not force and os.path.exists(CACHE):
        return json.load(open(CACHE))
    req = urllib.request.Request(WIKI, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
    tables = re.findall(r"<table[^>]*wikitable[^>]*>(.*?)</table>", html, flags=re.S)
    # 表0:当前成分
    current: dict[str, str] = {}
    for r in re.findall(r"<tr>(.*?)</tr>", tables[0], flags=re.S)[1:]:
        cells = [_clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)]
        if len(cells) >= 3 and cells[0]:
            current[cells[0].replace(".", "-")] = cells[2]
    # 表1:变更史(行有时缺日期/缺加入或移除,稳健解析)
    changes = []
    for r in re.findall(r"<tr>(.*?)</tr>", tables[1], flags=re.S)[2:]:   # 跳过两行表头
        cells = [_clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)]
        if len(cells) < 5:
            continue
        try:
            dt = datetime.strptime(cells[0], "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        added = cells[1].replace(".", "-") if cells[1] else None
        removed = cells[3].replace(".", "-") if cells[3] else None
        changes.append({"date": dt, "added": added, "removed": removed})
    out = {"fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "current": current, "changes": changes}
    json.dump(out, open(CACHE, "w"), ensure_ascii=False, indent=1)
    return out


def membership_asof(date: str, db: dict) -> set[str]:
    """date(YYYY-MM-DD)时点的成分集合:对 date 之后的变更逆序反向回放。"""
    members = set(db["current"])
    chs = sorted([c for c in db["changes"] if c["date"] > date],
                 key=lambda c: c["date"], reverse=True)
    for c in chs:
        if c["added"]:
            members.discard(c["added"])
        if c["removed"]:
            members.add(c["removed"])
    return members


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--sample", type=int, default=30, help="每个抽样池实测 Yahoo 可得性的标的数")
    ap.add_argument("--force", action="store_true", help="强制重抓 Wikipedia")
    args = ap.parse_args()

    db = fetch_tables(force=args.force)
    earliest = min(c["date"] for c in db["changes"])
    print(f"当前成分 {len(db['current'])} | 变更事件 {len(db['changes'])} | 覆盖最早 {earliest}")

    cur_set = set(db["current"])
    years = [y for y in range(2017, 2027)]
    rows = []
    all_lost: set[str] = set()
    for y in years:
        date = f"{y}-01-01"
        if date < earliest:
            rows.append({"year": y, "n": None})
            continue
        mem = membership_asof(date, db)
        lost = mem - cur_set
        all_lost |= lost
        rows.append({"year": y, "n": len(mem), "lost": len(lost),
                     "lost_rate": len(lost) / max(1, len(mem))})

    # 抽样实测:流失名单里 Yahoo 还能拿到多少(并购退市的通常拿不到)
    rng = np.random.default_rng(SEED)
    pool = sorted(all_lost)
    pick = [pool[i] for i in rng.permutation(len(pool))[:args.sample]] if pool else []
    ok = 0
    print(f"抽样实测 {len(pick)} 个流失标的的 Yahoo 可得性(2y 日线)...")
    for tk in pick:
        try:
            n = datamod.fetch_one(tk, range_="2y", max_age_hours=0)
            ok += 1 if n > 50 else 0
        except Exception:  # noqa: BLE001
            pass
    fetchable = ok / max(1, len(pick))
    print(f"  可得 {ok}/{len(pick)} = {fetchable*100:.0f}%(其余=退市/换代码,Yahoo 无数据)")

    date_s = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# S&P500 时点成分与幸存者偏差量化({date_s})",
        "",
        f"数据:Wikipedia 当前成分({len(db['current'])})+ 变更史({len(db['changes'])} 件,最早 {earliest})。",
        f"流失名单抽样 {len(pick)} 个,Yahoo 仍可得 **{fetchable*100:.0f}%**(不可得率 {100-fetchable*100:.0f}%)。",
        "",
        "| 年初 | 成分数 | 已不在当前名单 | 流失率 | **估计数据缺失率** |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        if r.get("n") is None:
            lines.append(f"| {r['year']} | —(变更史未覆盖) | | | |")
        else:
            miss = r["lost_rate"] * (1 - fetchable)
            lines.append(f"| {r['year']} | {r['n']} | {r['lost']} | {r['lost_rate']*100:.1f}% | **{miss*100:.1f}%** |")
    valid = [r for r in rows if r.get("n")]
    worst = max(valid, key=lambda r: r["lost_rate"]) if valid else None
    m2021 = next((r["lost_rate"] * (1 - fetchable) for r in valid if r["year"] == 2021), None)
    m2021_s = f"{m2021*100:.1f}%" if m2021 is not None else "N/A"
    lines += [
        "",
        "## 解读与折扣建议",
        f"- 回测起点越早,幸存者偏差越大:{worst['year']} 年初成分有 {worst['lost_rate']*100:.0f}% 已离开当前名单。" if worst else "",
        f"- 离开者中约 {100-fetchable*100:.0f}% 在 Yahoo 已无数据(并购/退市),这部分**完全缺席**我们的回测;",
        "  其余被降级/改名者仍可得,但当前 universe(取当前成分)同样不含它们。",
        "- 文献口径:幸存者偏差使长仓策略年化虚高约 1-4%。本仓引擎 2021 起回测,",
        f"  对应年初缺失率约 {m2021_s} → 现有「净 alpha≈0/为负」的结论**在消偏差后只会更差,不会更好**(方向稳健)。",
        "- 下一步(待办池):用 membership_asof 把横截面研究(factor_factory/xs_backtest)的",
        "  universe 换成时点成分(数据可得子集),并在报告里带上当期缺失率。",
        "",
        f"_缓存:backtest/pit_sp500.json(fetched {db['fetched_at']});抽样 seed={SEED},n={len(pick)}_",
    ]
    md = "\n".join(lines)
    out = os.path.join(os.path.dirname(HERE), "docs", f"study-pit-membership-{date_s}.md")
    open(out, "w", encoding="utf-8").write(md + "\n")
    print("\n" + md)

    if args.publish:
        import feed_lib as fl
        now = datetime.now(timezone.utc)
        miss_2021 = next((r["lost_rate"] * (1 - fetchable) for r in valid if r["year"] == 2021), None)
        report = {
            "schema_version": "1.0",
            "id": f"study-pit-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": date_s,
            "producer": {"name": "study-pit-membership", "agent_role": "engine"},
            "alerts": [{"level": "info", "code": "survivorship-quantified",
                        "message": f"幸存者偏差量化:2021 年初成分估计数据缺失率 "
                                   f"{miss_2021*100:.1f}%;流失者 Yahoo 不可得率 {100-fetchable*100:.0f}%。"
                                   f"现有净 alpha 结论消偏差后只会更差(方向稳健)。", "tickers": []}],
            "contribution": {"type": "regime_update",
                             "summary": f"PIT 成分重建({len(db['changes'])} 变更事件,覆盖至 {earliest});"
                                        f"逐年缺失率已量化,偏差从免责声明变成数字。"},
            "notes": "Wikipedia 变更表重建;抽样可得性 seed 预注册;退市者价格仍缺(真解=Norgate)。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("feed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
