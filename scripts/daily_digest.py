#!/usr/bin/env python3
"""每日股票分析日报:选股入库追踪 + 表现回看 + 自选股异动 → GitHub Issue 推送。

流程(由 .github/workflows/daily-digest.yml 在每个交易日美股收盘后运行):
  1. 把今天 feed/screener/latest.json 的 ≥阈值 选股(按分数取前 TRACK_TOP)追加到
     feed/screener/history.json(选股追踪看板 /tracker 的数据源,保留 60 个交易日)
  2. 取最近一个历史交易日的选股,拉实时报价算「第二天涨没涨」(命中率/平均涨幅)
  3. 云端自选池 feed/watchlist.json 全量报价 + 是否有当日 OpenClaw note
  4. 市场快照(指数/恐惧贪婪)取 feed/market/history.json 最新一条
  5. 汇总成 Markdown,经 GitHub REST 开 Issue 指派 owner(邮件即推送)

仅用标准库;单项失败降级不阻断(Issue 内容能写多少写多少)。
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENER_LATEST = ROOT / "feed" / "screener" / "latest.json"
HISTORY = ROOT / "feed" / "screener" / "history.json"
WATCHLIST = ROOT / "feed" / "watchlist.json"
MARKET_HIST = ROOT / "feed" / "market" / "history.json"
NOTES_DIR = ROOT / "feed" / "stock-notes"

TRACK_TOP = 20          # 每天最多追踪前 N 只(防止清单暴涨拖慢报价)
KEEP_DAYS = 60
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-dashboard-digest/0.1)"}


def jload(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default


def yahoo_code(symbol: str) -> str:
    market, code = symbol.split(":", 1)
    if market in ("US", "IDX"):
        return code
    if market == "HK":
        return f"{code.zfill(4)}.HK"
    if market == "CN":
        return f"{code}.SS" if code.startswith("6") else f"{code}.SZ"
    if market == "JP":
        return f"{code}.T"
    if market == "KR":
        return f"{code}.KS"
    if market == "DE":
        return f"{code}.DE"
    return code


def quote(symbol: str):
    """实时价 + 较昨收涨跌%(失败回 None)。加密走 Binance,其余 Yahoo。"""
    try:
        market, code = symbol.split(":", 1)
        if market == "CRYPTO":
            u = f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={code}"
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode())
            return {"price": float(d["lastPrice"]), "pct": float(d["priceChangePercent"])}
        u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             f"{urllib.parse.quote(yahoo_code(symbol))}?range=1d&interval=1d")
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            m = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
        price = m.get("regularMarketPrice")
        prev = m.get("regularMarketPreviousClose") or m.get("chartPreviousClose") or m.get("previousClose")
        pct = (price - prev) / prev * 100.0 if (price is not None and prev) else None
        return {"price": price, "pct": round(pct, 2) if pct is not None else None}
    except Exception as e:  # noqa: BLE001
        print(f"  ! quote {symbol}: {e}", file=sys.stderr)
        return None


def fmt_pct(x):
    return "—" if x is None else f"{'+' if x >= 0 else ''}{x:.2f}%"


def main() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = []

    # 1) 今日选股入库
    latest = jload(SCREENER_LATEST, None)
    hist: list = jload(HISTORY, [])
    todays_items = []
    if latest and latest.get("items"):
        todays_items = sorted(latest["items"], key=lambda x: -x.get("score", 0))[:TRACK_TOP]
        entry = {
            "date": latest.get("date") or today,
            "generated_at": latest.get("generated_at"),
            "threshold": latest.get("threshold"),
            "items": [{"symbol": f"US:{x['symbol']}", "name": x.get("name"),
                       "score": x.get("score"), "pick_price": x.get("price")} for x in todays_items],
        }
        hist = [h for h in hist if h.get("date") != entry["date"]]
        hist.append(entry)
        hist.sort(key=lambda h: h.get("date", ""))
        hist = hist[-KEEP_DAYS:]
        HISTORY.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")) + "\n")
        lines.append(f"## 📈 今日选股(评分≥{latest.get('threshold')},共 {latest.get('count')} 只,追踪前 {len(todays_items)})\n")
        lines.append("| 代码 | 名称 | 评分 | 自选中价 |")
        lines.append("|---|---|---|---|")
        for x in todays_items[:10]:
            lines.append(f"| {x['symbol']} | {x.get('name','')} | {x.get('score')} | {x.get('price')} |")
        lines.append("")
    else:
        lines.append("## 📈 今日选股\n\n_screener 今日无数据(休市或任务未跑)。_\n")

    # 2) 上一交易日选股表现
    prev_entries = [h for h in hist if h.get("date") and h["date"] < (latest.get("date") if latest else today)]
    if prev_entries:
        prev = prev_entries[-1]
        rows, wins, rets = [], 0, []
        for it in prev["items"]:
            q = quote(it["symbol"])
            time.sleep(0.35)
            if not q or q["price"] is None or not it.get("pick_price"):
                continue
            r = (q["price"] / it["pick_price"] - 1) * 100.0
            rets.append(r)
            if r > 0:
                wins += 1
            rows.append((it["symbol"], it.get("score"), it["pick_price"], q["price"], r))
        if rows:
            avg = sum(rets) / len(rets)
            lines.append(f"## 🎯 昨日选股表现({prev['date']} → 现在)\n")
            lines.append(f"**命中率 {wins}/{len(rows)}({wins/len(rows)*100:.0f}%) · 平均 {fmt_pct(avg)}**\n")
            lines.append("| 代码 | 评分 | 选中价 | 现价 | 收益 |")
            lines.append("|---|---|---|---|---|")
            for s, sc, pp, cp, r in sorted(rows, key=lambda x: -x[4]):
                lines.append(f"| {s} | {sc} | {pp} | {round(cp,2)} | {fmt_pct(r)} |")
            lines.append("")

    # 3) 云端自选池
    wl = jload(WATCHLIST, {}).get("symbols", [])
    if wl:
        lines.append("## ⭐ 自选池(云端跟踪)\n")
        lines.append("| 代码 | 现价 | 当日 | OpenClaw 解读 |")
        lines.append("|---|---|---|---|")
        for s in wl:
            q = quote(s)
            time.sleep(0.35)
            note = NOTES_DIR / f"{s.replace(':', '-')}.json"
            nd = jload(note, None)
            has_note = "✅ " + (nd.get("date", "") if nd else "") if nd else "❌ 缺"
            lines.append(f"| {s} | {q['price'] if q else '—'} | {fmt_pct(q['pct']) if q else '—'} | {has_note} |")
        lines.append("")

    # 4) 市场快照
    mh = jload(MARKET_HIST, [])
    if mh:
        m = mh[-1]
        idx = m.get("indices", {})
        def ip(c):
            v = idx.get(c, {})
            return f"{v.get('close', '—')}({fmt_pct(v.get('change_pct'))})"
        lines.append("## 🌐 市场快照\n")
        lines.append(f"- 标普500 {ip('^GSPC')} · 纳指 {ip('^IXIC')} · 上证 {ip('000001.SS')} · 恒指 {ip('^HSI')}")
        fng = m.get("fng", {})
        btc = m.get("btc", {})
        lines.append(f"- 加密情绪 FNG **{fng.get('value', '—')}**({fng.get('label', '—')}) · BTC {btc.get('price', '—')}({fmt_pct(btc.get('change_pct_24h'))})\n")

    lines.append("---\n_由 daily-digest.yml 自动生成 · 追踪看板:https://edwardwang66.github.io/stock-analysis/tracker/ · 仅供信息参考,非投资建议。_")
    body = "\n".join(lines)

    # 5) 开 Issue(在 Actions 内;本地试跑只打印)
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        owner = repo.split("/")[0]
        payload = json.dumps({
            "title": f"📊 每日股票分析日报 {today}",
            "body": body,
            "labels": ["daily-digest"],
            "assignees": [owner],
        }).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/issues", data=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json", **UA},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"Issue created: {json.loads(r.read().decode()).get('html_url')}")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
