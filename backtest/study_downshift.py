"""Universe 下沉实验 —— 设计文档 D5 的第一次实证检验。

核心论点(§4.3/D5):「容量受限的冷门层是小玩家的结构性护城河——巨头进不来」。
检验方式:同一引擎、同一默认参数(零调参,R5),分别跑在:
  A. 大盘基线  : DEMO_UNIVERSE(~115 只 S&P500 流动大盘,拥挤层)
  B. 小盘下沉  : S&P600 分层抽样 ~120 只(行业分层、种子化,选取规则预注册于本文件)
对比净/毛 Sharpe、holdout、容量地板的绑定程度(实现毛杠杆 vs 目标)。

诚实前提(先说丑话):
  - 两个 universe 都是「当前成分股」→ 幸存者偏差,且**小盘层偏差更严重**
    (退市/被并购比例高),小盘结果应视为「上界」。
  - 免费日线无借券费/可借量数据,小盘空头腿成本被低估。
  - 数据源 Yahoo,部分小盘历史短(<10y 自动剔除不足 260 bar 者)。

用法: python backtest/study_downshift.py [--publish] [--sample 120]
首次运行会从 Wikipedia 拉 S&P600 成分(缓存到 sp600_universe.json)并下载行情(~2-3 分钟)。
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

import data as datamod   # noqa: E402
import statarb as sa     # noqa: E402

SEED = 600               # 预注册抽样种子
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
CACHE = os.path.join(HERE, "sp600_universe.json")


def fetch_sp600() -> dict[str, str]:
    """{ticker: GICS sector};Wikipedia 成分表,缓存落盘(可复现)。"""
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    req = urllib.request.Request(WIKI, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
    m = re.search(r"<table[^>]*wikitable[^>]*>(.*?)</table>", html, flags=re.S)
    out: dict[str, str] = {}
    for r in re.findall(r"<tr>(.*?)</tr>", m.group(1), flags=re.S)[1:]:
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in
                 re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S)]
        if len(cells) >= 3 and cells[0]:
            tk = cells[0].replace(".", "-")          # Yahoo 记号
            out[tk] = cells[2].replace("&amp;", "&")
    json.dump(out, open(CACHE, "w"), ensure_ascii=False, indent=1)
    print(f"[sp600] {len(out)} 成分已缓存 -> sp600_universe.json")
    return out


def stratified_sample(uni: dict[str, str], n: int) -> list[str]:
    """行业分层、按层内字母序 + 种子洗牌的确定性抽样(规则预注册,防挑选)。"""
    rng = np.random.default_rng(SEED)
    by_sec: dict[str, list[str]] = {}
    for tk, sec in sorted(uni.items()):
        by_sec.setdefault(sec, []).append(tk)
    total = len(uni)
    picked: list[str] = []
    for sec, tks in sorted(by_sec.items()):
        k = max(2, round(n * len(tks) / total))
        idx = rng.permutation(len(tks))[:k]
        picked += [tks[i] for i in sorted(idx)]
    return picked[:n + 10]


def summarize(rep: dict, label: str) -> dict:
    lb = rep["latest_book"]
    return {
        "label": label, "universe": rep["universe_size"],
        "net_sharpe": rep["net"]["sharpe"], "gross_sharpe": rep["gross"]["sharpe"],
        "net_ann": rep["net"]["ann_return"], "cost_drag": rep["cost_drag_ann"],
        "train_sharpe": rep["train"]["sharpe"], "holdout_sharpe": rep["holdout"]["sharpe"],
        "max_dd": rep["net"]["max_drawdown"],
        "realized_gross_lev": lb["gross_leverage"],   # vs 目标 1.0:容量地板绑定程度
        "avg_positions": rep["book"]["avg_positions"],
        "turnover_daily": rep["turnover"]["avg_daily"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=120)
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    uni600 = fetch_sp600()
    small = stratified_sample(uni600, args.sample)
    print(f"S&P600 分层抽样 {len(small)} 只(seed={SEED})")

    need = small + sa.SECTOR_ETFS + ["SPY"]
    print("下载/刷新行情 ...")
    res = datamod.fetch_universe(need, range_="10y", workers=12)
    ok = sum(1 for v in res.values() if v > 0)
    print(f"  {ok}/{len(set(need))} 成功")

    p = sa.StatArbParams()                      # 同一默认参数,零调参(R5)
    print("\n[A] 大盘基线(拥挤层)...")
    rep_big = sa.run(p=sa.StatArbParams(), verbose=False)
    print("[B] 小盘下沉(护城河层)...")
    rep_small = sa.run(small, sa.StatArbParams(), verbose=False, sector_map=uni600)

    rows = [summarize(rep_big, "大盘 S&P500 拥挤层"), summarize(rep_small, "小盘 S&P600 下沉层")]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    import datetime as _dt
    spy_ts = datamod.load("SPY")["ts"]
    asof = _dt.datetime.utcfromtimestamp(int(spy_ts[-1])).strftime("%Y-%m-%d")

    lines = [
        f"# Universe 下沉实验(D5 容量护城河,{date})",
        "",
        "同一引擎、同一默认参数(零调参 R5),大盘拥挤层 vs S&P600 下沉层(分层抽样,seed 预注册)。",
        "",
        "| 层 | N | 毛SR | 净SR | train | holdout | 成本拖累 | 实现毛杠杆 | 日换手 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['label']} | {r['universe']} | {r['gross_sharpe']:+.2f} | {r['net_sharpe']:+.2f} "
                     f"| {r['train_sharpe']:+.2f} | {r['holdout_sharpe']:+.2f} | {r['cost_drag']*100:.1f}%/年 "
                     f"| {r['realized_gross_lev']:.2f} | {r['turnover_daily']*100:.0f}% |")
    gross_gain = rows[1]["gross_sharpe"] - rows[0]["gross_sharpe"]
    net_gain = rows[1]["net_sharpe"] - rows[0]["net_sharpe"]
    lines += [
        "",
        f"毛 Sharpe 下沉增益:{gross_gain:+.2f};净 Sharpe 增益:{net_gain:+.2f}。",
        f"容量地板绑定:小盘实现毛杠杆 {rows[1]['realized_gross_lev']:.2f}(目标 1.0)"
        f" vs 大盘 {rows[0]['realized_gross_lev']:.2f} —— 地板把规模诚实地压下来,这正是护城河的另一面。",
        "",
        "## 诚实解读",
        "- 两层都是当前成分股(幸存者偏差),**小盘层偏差更重**,其结果应视为上界;",
        "- 小盘空头腿借券费/可借量未建模,净 SR 偏乐观;",
        "- 结论只用于方向判断(下沉层毛 alpha 是否更厚),不直接据此切换生产 universe;",
        "- 若毛增益为正而净增益被成本吃掉 → 正符合设计文档「容量地板决定净容量」的预期。",
    ]
    md = "\n".join(lines)
    out = os.path.join(os.path.dirname(HERE), "docs", f"study-downshift-{date}.md")
    open(out, "w", encoding="utf-8").write(md + "\n")
    print("\n" + md)
    print(f"\n已写 {os.path.relpath(out)}")

    if args.publish:
        import feed_lib as fl
        now = datetime.now(timezone.utc)
        report = {
            "schema_version": "1.0",
            "id": f"study-downshift-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": asof,
            "producer": {"name": "study-downshift", "agent_role": "engine"},
            "alerts": [{"level": "info", "code": "downshift-study",
                        "message": f"D5 下沉实验:小盘毛SR {rows[1]['gross_sharpe']:+.2f} vs 大盘 {rows[0]['gross_sharpe']:+.2f}"
                                   f"(增益 {gross_gain:+.2f});净SR {rows[1]['net_sharpe']:+.2f} vs {rows[0]['net_sharpe']:+.2f}。"
                                   f"详见 docs/study-downshift-{date}.md", "tickers": []}],
            "contribution": {"type": "regime_update",
                             "summary": f"Universe 下沉实验:毛SR增益 {gross_gain:+.2f},净SR增益 {net_gain:+.2f};"
                                        f"容量地板将小盘实现杠杆压至 {rows[1]['realized_gross_lev']:.2f}。"},
            "notes": "同参零调参对照;幸存者偏差小盘更重(结果为上界);不据此直接切生产 universe。",
        }
        res2 = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("feed 发布:", "OK" if res2["ok"] else res2["errors"])


if __name__ == "__main__":
    main()
