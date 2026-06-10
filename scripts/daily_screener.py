#!/usr/bin/env python3
"""每日技术评分选股:扫描 标普500 + 纳指100,输出评分≥阈值的清单。

复用后端的同一套非 LLM 技术评分(backend/app/analysis/signals.analyze)。
数据源:Yahoo Finance chart(服务端直连,免代理)。
产出:
  feed/screener/latest.json     —— 最新清单(供 /screener 页面 + Issue)
  feed/screener/<YYYY-MM-DD>.json —— 当日存档
  feed/screener/issue.md        —— GitHub Issue 正文(Markdown)

用法:
  python scripts/daily_screener.py --threshold 80 [--limit N] [--concurrency 8]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# 复用后端分析
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.analysis.signals import analyze  # noqa: E402
from app.models import Bar  # noqa: E402

SP500_CSV = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-screener/0.1)"}


async def load_universe(client: httpx.AsyncClient) -> dict[str, dict]:
    """返回 {ticker: {name, indices:[...]}}。S&P500 从 datahub CSV;NDX100 从本地 json。"""
    uni: dict[str, dict] = {}
    # S&P 500
    try:
        r = await client.get(SP500_CSV, timeout=30)
        r.raise_for_status()
        for row in csv.DictReader(io.StringIO(r.text)):
            sym = row["Symbol"].strip().upper().replace(".", "-")  # BRK.B -> BRK-B (Yahoo)
            uni[sym] = {"name": row.get("Security", sym), "indices": ["SP500"], "sector": row.get("GICS Sector") or row.get("Sector") or ""}
        print(f"[universe] S&P500: {len(uni)} 只")
    except Exception as e:  # noqa: BLE001
        print(f"[universe] S&P500 CSV 拉取失败({e}),仅用 NDX100")
    # Nasdaq 100
    try:
        ndx = sorted(set(s.strip().upper() for s in json.loads((ROOT / "scripts" / "ndx100.json").read_text())))
        for s in ndx:
            if s in uni:
                if "NDX100" not in uni[s]["indices"]:
                    uni[s]["indices"].append("NDX100")
            else:
                uni[s] = {"name": s, "indices": ["NDX100"]}
        print(f"[universe] NDX100 合并后共 {len(uni)} 只")
    except Exception as e:  # noqa: BLE001
        print(f"[universe] NDX100 读取失败:{e}")
    return uni


async def fetch_bars(client: httpx.AsyncClient, ticker: str) -> list[Bar] | None:
    """拉 2 年日线,带一次重试。"""
    for attempt in range(2):
        try:
            r = await client.get(f"{YAHOO}{ticker}", params={"range": "2y", "interval": "1d"}, headers=UA, timeout=20)
            if r.status_code != 200:
                await asyncio.sleep(0.5)
                continue
            res = r.json()["chart"]["result"][0]
            ts = res.get("timestamp") or []
            q = res["indicators"]["quote"][0]
            bars: list[Bar] = []
            for i, t in enumerate(ts):
                o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
                if None in (o, h, l, c):
                    continue
                bars.append(Bar(ts=datetime.fromtimestamp(t, tz=timezone.utc), open=o, high=h, low=l, close=c,
                                volume=(q.get("volume") or [0])[i] or 0))
            return bars if len(bars) >= 60 else None
        except Exception:  # noqa: BLE001
            await asyncio.sleep(0.5)
    return None


async def score_one(client, sem, ticker, meta) -> dict | None:
    async with sem:
        bars = await fetch_bars(client, ticker)
        if not bars:
            return None
        a = analyze(f"US:{ticker}", bars)
        price = bars[-1].close
        prev = bars[-2].close if len(bars) >= 2 else price
        chg = (price / prev - 1) * 100 if prev else 0.0
        bull = sum(1 for s in a.signals if s["verdict"] in ("看多", "超卖"))
        return {
            "symbol": ticker, "name": meta["name"], "indices": meta["indices"],
            "score": a.score, "verdict": a.verdict, "price": round(price, 2),
            "change_pct": round(chg, 2), "rsi14": round(a.indicators.get("rsi14") or 0, 1),
            "bullish_signals": bull,
        }


async def run(threshold: int, limit: int, concurrency: int, out_dir: Path):
    async with httpx.AsyncClient() as client:
        uni = await load_universe(client)
        tickers = list(uni.items())
        if limit > 0:
            tickers = tickers[:limit]
        print(f"[scan] 开始扫描 {len(tickers)} 只(并发 {concurrency})…")
        sem = asyncio.Semaphore(concurrency)
        results = await asyncio.gather(*[score_one(client, sem, t, m) for t, m in tickers])

    scored = [r for r in results if r]
    picks = sorted([r for r in scored if r["score"] >= threshold],
                   key=lambda x: (x["score"], x["bullish_signals"], x["change_pct"]), reverse=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "universe_size": len(uni),
        "scanned": len(scored),
        "count": len(picks),
        "items": picks,
        "note": "规则化技术评分(SMA/RSI/MACD/布林,范围 -100..100),非 LLM、非投资建议。",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (out_dir / f"{today}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (out_dir / "issue.md").write_text(render_issue(payload))
    # 全宇宙分数表(看板分档标签用:90+/80+/70+ 等任意档位)
    scores_path = out_dir / "scores.json"
    scores_path.write_text(json.dumps({
        "date": payload["date"], "generated_at": payload["generated_at"],
        "scores": {r["symbol"]: r["score"] for r in scored},
        "sectors": {sym: (meta.get("sector") or "") for sym, meta in uni.items() if meta.get("sector")},
    }, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"[done] 扫描 {len(scored)} / 命中 ≥{threshold}: {len(picks)} 只 -> {out_dir}/latest.json")


def render_issue(p: dict) -> str:
    top = p["items"][:80]
    lines = [
        f"# 📈 每日技术评分 ≥ {p['threshold']} 选股清单 · {p['date']}",
        "",
        f"扫描 **标普500 + 纳指100** 共 {p['universe_size']} 只(成功 {p['scanned']} 只),"
        f"命中评分 ≥ {p['threshold']} 的 **{p['count']} 只**。",
        "",
        "| # | 代码 | 名称 | 评分 | 结论 | 价格 | 涨跌% | RSI | 指数 |",
        "|--:|------|------|--:|------|--:|--:|--:|------|",
    ]
    for i, r in enumerate(top, 1):
        idx = "·".join("标普500" if x == "SP500" else "纳指100" for x in r["indices"])
        lines.append(f"| {i} | `{r['symbol']}` | {r['name']} | **{r['score']}** | {r['verdict']} | "
                     f"{r['price']} | {r['change_pct']:+.2f} | {r['rsi14']} | {idx} |")
    if p["count"] > len(top):
        lines.append(f"\n_(还有 {p['count'] - len(top)} 只未列出,完整见 `feed/screener/latest.json` 或 /screener 页面)_")
    lines += [
        "",
        "> 评分为**规则化技术指标**(均线/RSI/MACD/布林,-100..100),**非 LLM、非投资建议**(Not financial advice)。",
        f"> 数据源 Yahoo Finance · 生成 {p['generated_at']}",
        "> 在线看板:https://edwardwang66.github.io/stock-analysis/screener/",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=80)
    ap.add_argument("--limit", type=int, default=0, help="0=全部;调试时可限量")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "feed" / "screener"))
    args = ap.parse_args()
    asyncio.run(run(args.threshold, args.limit, args.concurrency, Path(args.out)))


if __name__ == "__main__":
    main()
