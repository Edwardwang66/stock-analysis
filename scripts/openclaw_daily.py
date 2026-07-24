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
  python scripts/openclaw_daily.py --stocks-only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402
import openclaw_client as oc  # noqa: E402

SCREENER_URL = "https://raw.githubusercontent.com/edwardwang66/stock-analysis/main/feed/screener/latest.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; OpenClaw stock-analysis/1.0)"}
SEC_UA = {"User-Agent": "OpenClaw stock-analysis edwardwang66/stock-analysis"}
DEFAULT_DAILY_STOCK_NOTES = [
    ("CN:600519", "贵州茅台"),
    ("CN:000001", "平安银行"),
    ("CN:600036", "招商银行"),
    ("CN:601318", "中国平安"),
    ("CN:300750", "宁德时代"),
]
WATCHLIST_FILE = os.path.join(fl.REPO_ROOT, "feed", "watchlist.json")
SA_LP_FILE = os.path.join(fl.REPO_ROOT, "feed", "funds", "situational-awareness.json")
RS_RANKS_FILE = os.path.join(fl.REPO_ROOT, "feed", "signals", "rs-ranks.json")
_RS_CACHE: dict | None = None


# ======================================================================
# OpenClaw 本地分析实现。只使用可回溯的公开源:Yahoo chart/search/RSS + SEC companyfacts。
# ======================================================================

def _url_json(url: str, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _fmt(n, digits: int = 2, suffix: str = "") -> str:
    if n is None:
        return "n/a"
    if abs(n) >= 1_000_000_000:
        return f"{n / 1_000_000_000:.{digits}f}B{suffix}"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.{digits}f}M{suffix}"
    return f"{n:.{digits}f}{suffix}"


def _chart(symbol: str, range_: str = "1y") -> tuple[dict, dict]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval=1d"
    data = _url_json(url)
    res = (data.get("chart", {}).get("result") or [{}])[0]
    quote = ((res.get("indicators", {}) or {}).get("quote") or [{}])[0]
    return quote, res.get("meta", {}) or {}


def _closes(symbol: str, range_: str = "1y") -> tuple[list[float], dict]:
    quote, meta = _chart(symbol, range_)
    closes = [float(x) for x in (quote.get("close") or []) if x is not None]
    return closes, meta


def _returns(xs: list[float]) -> list[float]:
    return [(xs[i] / xs[i - 1] - 1.0) for i in range(1, len(xs)) if xs[i - 1]]


def _sma(xs: list[float], n: int) -> float | None:
    return (sum(xs[-n:]) / n) if len(xs) >= n else None


def _corr(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 20:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def _linreg_residuals(y: list[float], x: list[float]) -> list[float]:
    n = min(len(y), len(x))
    if n < 40:
        return []
    y, x = y[-n:], x[-n:]
    mx, my = statistics.mean(x), statistics.mean(y)
    vx = sum((v - mx) ** 2 for v in x)
    beta = (sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / vx) if vx else 0.0
    alpha = my - beta * mx
    return [yi - (alpha + beta * xi) for xi, yi in zip(x, y)]


def _zscore(xs: list[float], n: int = 60) -> float | None:
    if len(xs) < max(20, n // 2):
        return None
    win = xs[-n:]
    sd = statistics.stdev(win) if len(win) > 1 else 0
    return ((win[-1] - statistics.mean(win)) / sd) if sd else None


def _yahoo_search(symbol: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}&quotesCount=1&newsCount=4"
    try:
        return _url_json(url)
    except Exception:
        return {"quotes": [], "news": []}


def _rss_news(symbol: str) -> list[dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            root = ET.fromstring(r.read())
        out = []
        for item in root.findall("./channel/item")[:4]:
            dt = item.findtext("pubDate") or ""
            try:
                iso = parsedate_to_datetime(dt).date().isoformat()
            except Exception:
                iso = ""
            out.append({"title": item.findtext("title") or "", "link": item.findtext("link") or "", "date": iso})
        return out
    except Exception:
        return []


def _market_data_symbol(symbol: str) -> str:
    market, code = symbol.upper().split(":", 1)
    if market == "CN":
        return code if "." in code else f"{code}.{'SS' if code.startswith('6') else 'SZ'}"
    if market == "HK":
        return code if code.endswith(".HK") else f"{code.zfill(4)}.HK"
    if market == "JP":
        return code if code.endswith(".T") else f"{code}.T"
    if market == "KR":
        return code if code.endswith((".KS", ".KQ")) else f"{code}.KS"
    if market == "DE":
        return code if code.endswith(".DE") else f"{code}.DE"
    return code


_CIK_MAP = None


def _cik_for(symbol: str) -> str | None:
    global _CIK_MAP
    if _CIK_MAP is None:
        try:
            data = _url_json("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA)
            _CIK_MAP = {v["ticker"].upper(): f"{int(v['cik_str']):010d}" for v in data.values()}
        except Exception:
            _CIK_MAP = {}
    return _CIK_MAP.get(symbol.upper())


def _latest_sec_fact(symbol: str) -> dict | None:
    cik = _cik_for(symbol)
    if not cik:
        return None
    try:
        facts = _url_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=SEC_UA)
    except Exception:
        return None
    gaap = ((facts.get("facts") or {}).get("us-gaap") or {})

    def latest(concepts: list[str], unit: str):
        rows = []
        for c in concepts:
            rows += (((gaap.get(c) or {}).get("units") or {}).get(unit) or [])
        rows = [r for r in rows if r.get("form") in ("10-Q", "10-K") and r.get("end") and r.get("val") is not None]
        return max(rows, key=lambda r: (r.get("filed", ""), r.get("end", ""))) if rows else None

    revenue = latest(["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"], "USD")
    net_income = latest(["NetIncomeLoss"], "USD")
    eps = latest(["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares")
    if not any([revenue, net_income, eps]):
        return None
    return {"revenue": revenue, "net_income": net_income, "eps": eps}


def _stock_metrics(symbol: str) -> dict:
    quote, meta = _chart(symbol, "1y")
    closes = [float(x) for x in (quote.get("close") or []) if x is not None]
    highs = [float(x) for x in (quote.get("high") or []) if x is not None]
    lows = [float(x) for x in (quote.get("low") or []) if x is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    sma20, sma50, sma200 = _sma(closes, 20), _sma(closes, 50), _sma(closes, 200)
    ret20 = (price / closes[-21] - 1) if price and len(closes) > 21 else None
    ret60 = (price / closes[-61] - 1) if price and len(closes) > 61 else None
    return {"price": price, "sma20": sma20, "sma50": sma50, "sma200": sma200, "ret20": ret20,
            "ret60": ret60, "meta": meta, "closes": closes, "highs": highs, "lows": lows}


def _ema(xs: list[float], n: int) -> list[float]:
    if not xs:
        return []
    alpha = 2 / (n + 1)
    out = [xs[0]]
    for x in xs[1:]:
        out.append(out[-1] + alpha * (x - out[-1]))
    return out


def _td9(closes: list[float]) -> tuple[int, str]:
    if len(closes) < 5:
        return 0, "样本不足"
    direction = 1 if closes[-1] > closes[-5] else (-1 if closes[-1] < closes[-5] else 0)
    if direction == 0:
        return 0, "中断"
    count = 0
    for i in range(len(closes) - 1, 3, -1):
        ok = closes[i] > closes[i - 4] if direction > 0 else closes[i] < closes[i - 4]
        if not ok:
            break
        count += 1
        if count >= 9:
            break
    label = "上行" if direction > 0 else "下行"
    return count, label


def _supertrend(highs: list[float], lows: list[float], closes: list[float], period: int = 10, mult: float = 3.0) -> tuple[str, str]:
    n = min(len(highs), len(lows), len(closes))
    if n < period + 2:
        return "样本不足", "n/a"
    highs, lows, closes = highs[-n:], lows[-n:], closes[-n:]
    trs = [highs[0] - lows[0]]
    for i in range(1, n):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr = []
    for i, tr in enumerate(trs):
        if i == 0:
            atr.append(tr)
        else:
            atr.append((atr[-1] * (period - 1) + tr) / period)
    direction = []
    final_upper, final_lower = [], []
    for i in range(n):
        hl2 = (highs[i] + lows[i]) / 2
        upper = hl2 + mult * atr[i]
        lower = hl2 - mult * atr[i]
        if i == 0:
            final_upper.append(upper)
            final_lower.append(lower)
            direction.append(1)
            continue
        final_upper.append(upper if upper < final_upper[-1] or closes[i - 1] > final_upper[-1] else final_upper[-1])
        final_lower.append(lower if lower > final_lower[-1] or closes[i - 1] < final_lower[-1] else final_lower[-1])
        if closes[i] > final_upper[-2]:
            direction.append(1)
        elif closes[i] < final_lower[-2]:
            direction.append(-1)
        else:
            direction.append(direction[-1])
    last_flip = "未见近端翻转"
    for i in range(n - 1, 0, -1):
        if direction[i] != direction[i - 1]:
            last_flip = f"约 {n - i} 个交易日前翻转"
            break
    return ("多头" if direction[-1] > 0 else "空头"), last_flip


def _chan_macd_summary(closes: list[float]) -> str:
    if len(closes) < 40:
        return "缠论近似: 样本不足，无法稳定判断笔/背驰"
    ema12, ema26 = _ema(closes, 12), _ema(closes, 26)
    macd = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema(macd, 9)
    hist = [m - s for m, s in zip(macd, signal)]
    short = closes[-1] - closes[-6]
    mid = closes[-1] - closes[-21]
    pen = "上行笔" if short > 0 and mid >= 0 else ("下行笔" if short < 0 and mid <= 0 else "震荡笔")
    recent_high, recent_low = max(closes[-20:]), min(closes[-20:])
    pos = (closes[-1] - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
    boundary = "接近中枢上沿" if pos >= 0.75 else ("接近中枢下沿" if pos <= 0.25 else "位于中枢内部")
    hist5 = sum(abs(x) for x in hist[-5:])
    hist20 = sum(abs(x) for x in hist[-20:-15]) if len(hist) >= 20 else hist5
    divergence = "有背驰迹象" if (pen == "上行笔" and hist5 < hist20 * 0.75) or (pen == "下行笔" and hist5 < hist20 * 0.75) else "暂未见明显 MACD 面积背驰"
    return f"缠论近似: 当前{pen}，{boundary}，{divergence}"


def _rs_for_symbol(symbol: str) -> int | None:
    global _RS_CACHE
    if _RS_CACHE is None:
        _RS_CACHE = fl.load_json(RS_RANKS_FILE, {"ranks": {}}) if os.path.exists(RS_RANKS_FILE) else {"ranks": {}}
    market, code = symbol.split(":", 1)
    keys = [symbol.upper(), code.upper()]
    if market.upper() == "US":
        keys.append(f"US:{code}".upper())
    ranks = _RS_CACHE.get("ranks") or {}
    for key in keys:
        val = ranks.get(key)
        if isinstance(val, dict) and val.get("rs") is not None:
            return int(val["rs"])
        if isinstance(val, (int, float)):
            return int(val)
    return None


def _methodology_fields(metrics: dict, rs: int | None = None) -> dict:
    closes = metrics.get("closes") or []
    highs = metrics.get("highs") or []
    lows = metrics.get("lows") or []
    price = metrics.get("price") or (closes[-1] if closes else None)
    td_count, td_dir = _td9(closes)
    hi52 = max(highs or closes) if (highs or closes) else None
    lo52 = min(lows or closes) if (lows or closes) else None
    drawdown = ((price / hi52 - 1) * 100) if price and hi52 else None
    pos52 = ((price - lo52) / (hi52 - lo52) * 100) if price and hi52 and lo52 and hi52 > lo52 else None
    st_dir, st_flip = _supertrend(highs, lows, closes)
    chan = _chan_macd_summary(closes)
    td_text = f"{td_dir}{td_count}" + ("(防衰竭)" if td_count >= 7 else "")
    pos_text = f"距高 {drawdown:.1f}% · {pos52:.0f}分位" if pos52 is not None and drawdown is not None else "样本不足"
    chan_text = chan.replace("缠论近似: 当前", "")
    return {
        "td9": td_text,
        "week52": pos_text,
        "supertrend": f"{st_dir}·{st_flip}",
        "chan": chan_text,
        **({"rs": rs} if rs is not None else {}),
    }


def _methodology_summary(fields: dict) -> str:
    td = fields.get("td9", "样本不足").replace("(防衰竭)", "，7/8/9 高阶计数需防短线衰竭")
    week52 = fields.get("week52", "样本不足").replace(" · ", "、")
    return (
        f"TD9 {td}；52周位置 {week52}；SuperTrend(10,3) {fields.get('supertrend', '样本不足')}；"
        f"缠论近似: 当前{fields.get('chan', '样本不足')}。"
    )


def analyze_stock(symbol: str, name: str, screener_item: dict | None) -> dict:
    """基于公开行情、SEC companyfacts(美股)与 Yahoo 新闻生成每日个股解读。"""
    market = symbol.split(":", 1)[0].upper()
    code = _market_data_symbol(symbol)
    metrics = _stock_metrics(code)
    methodology = _methodology_fields(metrics, _rs_for_symbol(symbol))
    method = _methodology_summary(methodology)
    search = _yahoo_search(code)
    quote = (search.get("quotes") or [{}])[0]
    sec = _latest_sec_fact(code) if market == "US" else None
    news = (search.get("news") or [])[:3] or _rss_news(code)[:3]

    note = oc.stock_note_template(symbol)
    note["methodology"] = methodology
    score = (screener_item or {}).get("score")
    rsi = (screener_item or {}).get("rsi14")
    price = metrics["price"] or (screener_item or {}).get("price")
    above50 = bool(price and metrics["sma50"] and price > metrics["sma50"])
    above200 = bool(price and metrics["sma200"] and price > metrics["sma200"])
    extended = bool(rsi and rsi >= 68)
    if score is None:
        note["stance"] = "看多" if above50 and not extended else "中性"
    else:
        note["stance"] = "看多" if score >= 50 and above50 and not extended else ("中性" if score >= 50 else "看空")

    sector = quote.get("sectorDisp") or quote.get("sector") or "unknown sector"
    industry = quote.get("industryDisp") or quote.get("industry") or "unknown industry"
    trend_bits = [
        f"技术评分 {score if score is not None else 'n/a'}、RSI14 {rsi if rsi is not None else 'n/a'}",
        f"最新价约 {_fmt(price)}，20/50/200日均线约 {_fmt(metrics['sma20'])}/{_fmt(metrics['sma50'])}/{_fmt(metrics['sma200'])}",
        method,
    ]
    if screener_item and screener_item.get("source_context"):
        trend_bits.append(str(screener_item["source_context"]))
    if metrics["ret20"] is not None or metrics["ret60"] is not None:
        trend_bits.append(f"近20/60交易日收益约 {_fmt((metrics['ret20'] or 0) * 100, 1, '%')}/{_fmt((metrics['ret60'] or 0) * 100, 1, '%')}")
    note["thesis"] = (
        f"多头: {name} 属于 {sector}/{industry}，当前进入看多清单，" + "；".join(trend_bits) +
        "。空头: 若 RSI 接近过热或价格远高于短均线，短线回撤风险会上升；财报与新闻仍需逐日复核。"
    )
    if sec:
        rev, ni, eps = sec.get("revenue"), sec.get("net_income"), sec.get("eps")
        parts = []
        if rev:
            parts.append(f"最近 SEC {rev.get('form')}({rev.get('end')}) revenue={_fmt(float(rev.get('val')))}")
        if ni:
            parts.append(f"net income={_fmt(float(ni.get('val')))}")
        if eps:
            parts.append(f"diluted/basic EPS={_fmt(float(eps.get('val')))}")
        note["earnings"] = "；".join(parts) + "。SEC companyfacts 口径可能混合 10-Q/10-K，作为事实摘录而非盈利预测。"
    else:
        filing_hint = "SEC companyfacts" if market == "US" else f"{market} 交易所/公司公告源"
        note["earnings"] = f"本轮未从 {filing_hint} 可靠取得最近一季核心字段；不编造财报数字。"
    if news:
        items = []
        for n in news:
            title = n.get("title") or ""
            pub = n.get("publisher") or n.get("date") or ""
            items.append(f"{title}" + (f"({pub})" if pub else ""))
        note["news"] = "近端公开新闻标题: " + "；".join(items[:3]) + "。标题只作事件线索，未把新闻当方向性 alpha。"
    else:
        note["news"] = "本轮未抓到可用的 Yahoo Finance 近端新闻；新闻项留空，不补写。"
    note["risks"] = "风险: 技术评分同质化、财报/宏观事件窗口、估值回撤、行业 beta 与流动性冲击；本文仅信息参考，非投资建议。"
    note["view"] = f"{note['stance']}: {method} 规则化技术面只适合作为观察清单；需要结合后续财报与事件风险复核。"
    note["sources"] = [
        {"title": f"Yahoo Finance chart: {code}", "url": f"https://finance.yahoo.com/quote/{code}/chart/"},
        {"title": f"Yahoo Finance search/news: {code}", "url": f"https://finance.yahoo.com/quote/{code}/news/"},
    ]
    if sec:
        cik = _cik_for(code)
        note["sources"].append({"title": f"SEC companyfacts CIK{cik}", "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"})
    for n in news[:2]:
        if n.get("link"):
            note["sources"].append({"title": n.get("title", "Yahoo Finance news"), "url": n["link"]})
    return note


def _theme_for(symbol: str, item: dict | None, sectors: dict, sa_theme: dict) -> str:
    market, code = symbol.split(":", 1)
    plain = code.replace("^", "")
    if symbol in sa_theme:
        return f"SA LP/{sa_theme[symbol]}"
    if market == "US" and code in sectors:
        return sectors[code]
    if market == "CN":
        return "A股/中国资产"
    if market == "HK":
        return "港股/中国资产"
    if market == "KR":
        return "韩国/半导体链"
    if market == "IDX":
        return "指数/对冲工具"
    if item and item.get("indices"):
        return ",".join(item.get("indices") or [])
    return plain


def _stance_counts(notes: list[dict]) -> str:
    counts = {"看多": 0, "中性": 0, "看空": 0}
    for n in notes:
        counts[n.get("stance", "中性")] = counts.get(n.get("stance", "中性"), 0) + 1
    return " / ".join(f"{k} {v}" for k, v in counts.items())


def _prev_screener_snapshot(date: str) -> tuple[str | None, dict]:
    """找出严格早于 date 的最近一个 feed/screener/<YYYY-MM-DD>.json 日切片(给 ④ 进出变化用)。"""
    import glob
    import re
    root = os.path.join(fl.FEED, "screener")
    dates = []
    for p in glob.glob(os.path.join(root, "*.json")):
        stem = os.path.basename(p)[:-5]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem) and stem < date:
            dates.append(stem)
    if not dates:
        return None, {"items": []}
    prev = max(dates)
    return prev, fl.load_json(os.path.join(root, f"{prev}.json"), {"items": []})


def write_daily_analysis(date: str, universe: list[tuple[str, str, dict | None]]) -> None:
    latest = fl.load_json(os.path.join(fl.FEED, "screener", "latest.json"), {"items": []})
    scores = fl.load_json(os.path.join(fl.FEED, "screener", "scores.json"), {"sectors": {}})
    watch = fl.load_json(WATCHLIST_FILE, {"symbols": []})
    salp = fl.load_json(SA_LP_FILE, {"positions": []})
    sectors = scores.get("sectors") or {}
    sa_theme = {p.get("ticker"): p.get("theme", "13F 持仓") for p in salp.get("positions", []) if p.get("ticker")}
    screener_symbols = [f"US:{it['symbol']}" for it in latest.get("items", [])]
    item_by_symbol = {f"US:{it['symbol']}": it for it in latest.get("items", [])}

    notes = []
    for sym, _, _ in universe:
        rel = oc.stock_note_relpath(sym)
        n = fl.load_json(os.path.join(fl.REPO_ROOT, rel), {})
        if n:
            notes.append(n)

    buckets: dict[str, list[str]] = {}
    for sym, name, item in universe:
        theme = _theme_for(sym, item_by_symbol.get(sym) or item, sectors, sa_theme)
        buckets.setdefault(theme, []).append(sym)
    grouped = sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    top_items = latest.get("items", [])[:5]
    top_lines = [
        f"- US:{it['symbol']}({it.get('name', it['symbol'])}): v2 {it.get('score')} 分，"
        f"RSI14 {it.get('rsi14', 'n/a')}，bullish_signals {it.get('bullish_signals', 'n/a')}。"
        for it in top_items
    ]
    prev_date, prev = _prev_screener_snapshot(date)
    prev_set = {f"US:{it['symbol']}" for it in prev.get("items", [])}
    cur_set = set(screener_symbols)
    entered = sorted(cur_set - prev_set)[:25]
    exited = sorted(prev_set - cur_set)[:25]

    lines = [
        f"# OpenClaw 全量投递汇总 {date}",
        "",
        "## ① 三池总览",
        f"- 自选池: {len(watch.get('symbols') or [])} 只；本轮与看多清单去重后覆盖 {len(universe)} 只。",
        f"- 今日看多清单: {len(screener_symbols)} 只，阈值 {latest.get('threshold')}，最高分 {max([it.get('score', 0) for it in latest.get('items', [])] or [0])}。",
        f"- SA LP: {len(watch.get('tiers', {}).get('salp', []))} 只已随自选池覆盖；主题以 AI 算力/电力/光互联/存储为主。",
        f"- 本轮 note 倾向统计: {_stance_counts(notes)}。",
        "",
        "## ② 看多清单按主题分组",
    ]
    for theme, syms in grouped[:18]:
        picks = [s for s in syms if s in cur_set]
        if picks:
            lines.append(f"- {theme}: {', '.join(picks[:12])}" + (" ..." if len(picks) > 12 else ""))
    lines += [
        "",
        "## ③ 最值得关注的 3-5 只",
        *top_lines,
        "",
        "这些标的只是多因子共振最强的观察对象；事件窗口、拥挤与财报风险仍需逐日复核，非投资建议。",
        "",
        f"## ④ 与上一交易日({prev_date or 'n/a'} → {date})≥80 清单的进出变化",
        f"- 新进入: {', '.join(entered) if entered else '无'}",
        f"- 离开: {', '.join(exited) if exited else '无'}",
        "",
        "## ⑤ 数据来源",
        "- feed/watchlist.json",
        "- feed/screener/latest.json",
        "- feed/screener/scores.json",
        "- feed/funds/situational-awareness.json",
        "- Yahoo Finance chart/search/news；美股财报事实优先使用 SEC companyfacts，取不到则明确说明。",
    ]
    out = os.path.join(fl.FEED, "screener", f"analysis-{date}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    fl.record_publication_path(out)
    print(f"[daily] 本地写入 {os.path.relpath(out, fl.REPO_ROOT)}")


def analyze_role(role: str, context: dict) -> dict:
    """用 screener + Yahoo 日线构造 5 个角色的可审计日报。"""
    scr = fl.load_json(os.path.join(fl.REPO_ROOT, "feed", "screener", "latest.json"), {"items": []})
    items = (scr.get("items") or [])[:30]
    symbols = [it["symbol"] for it in items]
    close_map, ret_map = {}, {}
    for s in symbols + ["SPY"]:
        try:
            closes, _ = _closes(s, "6mo")
            close_map[s] = closes
            ret_map[s] = _returns(closes)
            time.sleep(0.05)
        except Exception:
            pass
    spy_ret = ret_map.get("SPY", [])
    residual_rows = []
    for s in symbols:
        res = _linreg_residuals(ret_map.get(s, []), spy_ret)
        z = _zscore(res, 60) if res else None
        if z is not None:
            residual_rows.append((s, z, statistics.stdev(res[-60:]) if len(res) >= 20 else 0.0))
    residual_rows.sort(key=lambda x: abs(x[1]), reverse=True)
    residual_disp = statistics.mean([r[2] for r in residual_rows]) if residual_rows else None
    pair_corrs = []
    for i, a in enumerate(symbols[:15]):
        for b in symbols[i + 1:15]:
            c = _corr(ret_map.get(a, []), ret_map.get(b, []))
            if c is not None:
                pair_corrs.append(c)
    crowding = statistics.mean(pair_corrs) if pair_corrs else None
    above50 = [1 for s in symbols if close_map.get(s) and _sma(close_map[s], 50) and close_map[s][-1] > _sma(close_map[s], 50)]
    breadth = len(above50) / len(symbols) if symbols else None
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "id": f"openclaw-{role}-{now.strftime('%Y-%m-%dT%H%M')}Z",
        "kind": "openclaw",
        "produced_at": fl.now_iso(),
        "asof_data": scr.get("date") or now.strftime("%Y-%m-%d"),
        "producer": {"name": f"openclaw-agent:{role}", "model": os.environ.get("OPENCLAW_MODEL", "OpenClaw"),
                     "agent_role": role, "run_url": os.environ.get("OPENCLAW_RUN_URL", "local-openclaw-daily")},
    }
    top_z = residual_rows[:3]
    if role == "residual-analyst":
        report.update({
            "market_state": {"residual_dispersion": residual_disp or 0, "crowding_proxy": crowding or 0,
                             "breadth_pct_above_50dma": breadth or 0},
            "alerts": [
                {"level": "warning" if abs(z) >= 2 else "info", "code": "residual_health",
                 "message": f"{s} 对 SPY 日收益残差 60日 z-score={z:.2f}; 仅提示残差偏离，不作方向预测。",
                 "tickers": [s]} for s, z, _ in top_z
            ],
            "contribution": {"type": "risk_alert", "summary": f"用看多清单前 {len(symbols)} 只与 SPY 日线重算残差偏离，标出 {len(top_z)} 个最大偏离。"},
            "notes": "残差=个股日收益对 SPY 日收益的一元滚动回归残差；免费日线近似，不等同完整行业中性协整检验。",
        })
    elif role == "crowding-monitor":
        alert = bool(crowding is not None and crowding > 0.45)
        report.update({
            "market_state": {"crowding_proxy": crowding or 0, "crowding_alert": alert, "breadth_pct_above_50dma": breadth or 0},
            "alerts": [{"level": "warning" if alert else "info", "code": "crowding",
                        "message": f"看多清单前15只 6个月日收益平均相关约 {crowding or 0:.2f}，50日均线上方占比约 {(breadth or 0):.0%}；拥挤只代表尾部同向风险，不是做空信号。",
                        "tickers": symbols[:5]}],
            "contribution": {"type": "risk_alert", "summary": "更新看多清单同质化/拥挤代理，供仓位层做预防性降杠杆参考。"},
            "notes": "拥挤代理=前15只看多标的两两日收益相关均值；免费公开日线口径。",
        })
    elif role == "event-risk":
        report.update({
            "alerts": [{"level": "info", "code": "earnings",
                        "message": "本地公开源未接入完整 PIT 财报日历；对前15只看多标的建议在财报 T±1 暂降单名敞口并复核 SEC/IR 新闻。",
                        "tickers": symbols[:15]}],
            "contribution": {"type": "risk_alert", "summary": "事件风险采用保守标注: 未验证日历不编造日期，只给财报窗口降敞口规则。"},
            "notes": "大盘综述: 当前看多清单广度约 %.0f%%，拥挤代理约 %.2f；事件风险只做回避/降敞口，不做方向 alpha。"
                     % ((breadth or 0) * 100, crowding or 0),
        })
    elif role == "factor-factory":
        report.update({
            "factory_candidates": [
                {"expr": "rank(ts_zscore(close / sma(close, 50) - 1, 20))",
                 "hypothesis": "看多清单中相对50日均线的温和趋势延续可能反映机构缓慢调仓。",
                 "incremental_ic": 0.0, "post_cutoff": True, "pbo": 1.0, "t_stat": 0.0,
                 "passed_gates": False, "decision": "reject",
                 "note": "本轮只有公开日线与规则化看多清单，未完成正交增量 IC、相依 FDR、成本后 IR 和真 holdout；按 R6 拒绝。"}
            ],
            "contribution": {"type": "new_factor", "candidates_proposed": 1, "candidates_accepted": 0,
                             "summary": "提出 1 个可读公式候选，但因六门控证据不足直接 reject，没有上线或 shadow。"},
            "notes": "LLM 只生成假设；证不出截止后净·扣成本增量，结论必须 reject。",
        })
    else:
        report.update({
            "factory_candidates": [
                {"expr": "rank(ts_zscore(close / sma(close, 50) - 1, 20))",
                 "hypothesis": "复核 factor-factory 同名趋势延续候选。",
                 "incremental_ic": 0.0, "post_cutoff": True, "pbo": 1.0, "t_stat": 0.0,
                 "passed_gates": False, "decision": "reject",
                 "note": "红队否决: 未计入完整试验次数、未做风险中性化后增量 IC、未过真 holdout 与成本后 IR。"}
            ],
            "alerts": [{"level": "info", "code": "red-team",
                        "message": "五偏差自查: 当前数据通路不足以排除幸存者/叙事/目标/成本偏差；全部候选维持 reject。",
                        "tickers": []}],
            "contribution": {"type": "new_factor", "summary": "红队复核并否决本轮唯一候选，避免把技术筛选误当新增 alpha。"},
            "notes": "无真 holdout 时不把 CPCV/DSR 写成确定结论；保守拒绝。",
        })
    return report


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


def _add_symbol(uni: dict[str, tuple[str, dict | None]], symbol: str, name: str | None,
                item: dict | None = None) -> None:
    sym = symbol.strip().upper()
    if not sym or ":" not in sym:
        return
    prev_name, prev_item = uni.get(sym, (name or sym.split(":", 1)[1], None))
    merged = dict(prev_item or {})
    if item:
        merged.update(item)
    uni[sym] = (name or prev_name, merged or None)


def _load_watchlist_symbols() -> list[str]:
    data = fl.load_json(WATCHLIST_FILE, {}) if os.path.exists(WATCHLIST_FILE) else {}
    return [str(s).upper() for s in (data.get("symbols") or []) if isinstance(s, str)]


def _load_sa_lp_symbols(limit: int = 8) -> list[tuple[str, str, dict]]:
    data = fl.load_json(SA_LP_FILE, {}) if os.path.exists(SA_LP_FILE) else {}
    positions = data.get("positions") or []
    longs = [p for p in positions if "PUT" not in str(p.get("type", "")).upper()]
    shorts = [p for p in positions if p.get("ticker") == "US:INFY"]
    out = []
    for p in longs[:limit] + shorts[:1]:
        ticker = str(p.get("ticker", "")).upper()
        if not ticker:
            continue
        context = (
            f"SA LP 持仓背景: {p.get('type', 'position')}，主题 {p.get('theme', 'n/a')}，"
            f"13F asof {data.get('asof', 'n/a')}。"
        )
        out.append((ticker, p.get("name") or ticker.split(":", 1)[1], {"source_context": context}))
    return out


def load_universe(top: int, watchlist: str | None, screener_file: str | None) -> list[tuple[str, str, dict | None]]:
    # 每日覆盖范围: feed/watchlist.json symbols 是完整必析池。
    # daily_screener 会把 >=80 清单轮换写入 tier=screener,SA LP 也在 tier=salp;
    # screener/SA 文件这里只用于补充分数、行业和持仓背景,不再额外扩池。
    scr = fl.load_json(screener_file) if screener_file else fetch_json(SCREENER_URL)
    all_items = (scr or {}).get("items", [])
    items = all_items if top <= 0 else all_items[:top]
    screener_by_symbol = {f"US:{it['symbol']}".upper(): it for it in items if it.get("symbol")}
    salp_by_symbol = {sym.upper(): (name, item) for sym, name, item in _load_sa_lp_symbols()}
    uni: dict[str, tuple[str, dict | None]] = {}
    watch_symbols = _load_watchlist_symbols()
    for sym in watch_symbols:
        item = {"source_context": "云端自选池 feed/watchlist.json symbols，Edward/Claude 维护的完整必析全集。"}
        name = None
        if sym in screener_by_symbol:
            item.update(screener_by_symbol[sym])
            name = screener_by_symbol[sym].get("name")
            item["source_context"] = "feed/watchlist.json 必析池；同时属于当日 >=80 v2 看多清单。"
        if sym in salp_by_symbol:
            salp_name, salp_item = salp_by_symbol[sym]
            name = name or salp_name
            item.update(salp_item)
        _add_symbol(uni, sym, name, item)
    # 兼容旧环境: 如果仓库尚无 feed/watchlist.json,仍保留最初的 A 股默认池。
    if not watch_symbols:
        for it in items:
            sym = f"US:{it['symbol']}"
            _add_symbol(uni, sym, it.get("name", it["symbol"]), it)
        for sym, (name, item) in salp_by_symbol.items():
            _add_symbol(uni, sym, name, item)
        for sym, name in DEFAULT_DAILY_STOCK_NOTES:
            _add_symbol(uni, sym, name, {"source_context": "默认 A 股覆盖池。"})
    if watchlist and os.path.exists(watchlist):
        for line in open(watchlist):
            s = line.strip().upper()
            if s and ":" in s:
                _add_symbol(uni, s, s.split(":")[1], {"source_context": f"兼容本地 watchlist 文件 {watchlist}。"})
    return [(s, n, i) for s, (n, i) in uni.items()]


def dispatch_stock(note: dict, mode: str, repo: str, token: str | None):
    rel = oc.stock_note_relpath(note["symbol"])
    if mode == "local":
        fl.save_json(os.path.join(fl.REPO_ROOT, rel), note)
        print(f"[daily] 本地写入 {rel}")
    else:
        oc.put_github_path(note, repo, token, rel, f"openclaw: 个股解读 {note['symbol']} {note['date']}")


def rebuild_stock_note_index() -> None:
    """维护 feed/stock-notes/index.json,方便人工浏览与后续批量消费。"""
    root = os.path.join(fl.FEED, "stock-notes")
    symbols = []
    for fn in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not fn.endswith(".json") or fn in ("index.json", "stance-history.json"):
            continue
        note = fl.load_json(os.path.join(root, fn), {})
        if isinstance(note, dict) and note.get("symbol"):
            symbols.append({"symbol": note.get("symbol"), "date": note.get("date"),
                            "stance": note.get("stance"), "view": note.get("view", "")[:160]})
    fl.save_json(os.path.join(root, "index.json"), {
        "updated_at": fl.now_iso(),
        "note": "每日个股 AI 解读索引。由外部 OpenClaw(stock-analyst 角色)产出,经 feed/stock-notes/<MARKET-CODE>.json 投递。",
        "symbols": symbols,
    })


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


def _winter_pg_dsn() -> str | None:
    """Return the exact non-empty DSN the child loaders would resolve."""
    if "WINTER_PG_DSN" in os.environ:
        return os.environ["WINTER_PG_DSN"] or None

    env_file = Path.home() / ".config/stock-analysis/openclaw.env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "WINTER_PG_DSN":
            value = value.strip().strip('"').strip("'")
            return value or None
    return None


def archive_pg() -> None:
    """Skip when unconfigured; run configured local warehouse jobs fail-fast."""
    dsn = _winter_pg_dsn()
    if dsn is None:
        print("[daily] pg skipped: WINTER_PG_DSN not configured")
        return

    commands = (
        ([sys.executable, "scripts/winter_pg/ingest.py"], "[daily] pg ", None),
        (
            [sys.executable, "scripts/winter_pg/winrate.py", "--if-due"],
            "[daily] winrate ",
            "not due",
        ),
        (
            [sys.executable, "scripts/winter_pg/event_heat.py"],
            "[daily] event-heat ",
            None,
        ),
    )
    for command, prefix, suppressed in commands:
        result = subprocess.run(
            command,
            cwd=fl.REPO_ROOT,
            capture_output=True,
            text=True,
        )
        safe_stdout = (result.stdout or "").replace(dsn, "[REDACTED]")
        safe_stderr = (result.stderr or "").replace(dsn, "[REDACTED]")
        message = (safe_stdout or safe_stderr).strip()
        if message and (suppressed is None or suppressed not in message):
            print(f"{prefix}{message}")
        result.stdout = safe_stdout
        result.stderr = safe_stderr
        result.check_returncode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "github-api", "dispatch"], default="local")
    ap.add_argument("--top", type=int, default=0, help="看多清单取前 N 只(0=全部看多清单;默认全量覆盖 ≥80 清单)")
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
        # 数据源(Yahoo/SEC)在数据中心 IP 上会限流;OPENCLAW_THROTTLE 给每只之间加节流(秒),
        # 默认 0 保持原行为(本机/residential IP 无需节流)。失败的标的最后统一重试一轮补齐覆盖。
        throttle = float(os.environ.get("OPENCLAW_THROTTLE", "0") or "0")
        print(f"[daily] 个股解读 {len(uni)} 只(mode={args.mode}, throttle={throttle}s)")

        def _run(items: list[tuple[str, str, dict | None]]) -> list[tuple[str, str, dict | None]]:
            failed: list[tuple[str, str, dict | None]] = []
            for sym, name, item in items:
                try:
                    note = analyze_stock(sym, name, item)
                    dispatch_stock(note, args.mode, args.repo, token)
                except Exception as e:  # noqa: BLE001
                    failed.append((sym, name, item))
                    print(f"[daily] {sym} 失败: {e}")
                if throttle:
                    time.sleep(throttle)
            return failed

        failed = _run(uni)
        if failed:
            print(f"[daily] 首轮失败 {len(failed)} 只,20s 后重试一轮")
            time.sleep(20)
            failed = _run(failed)
            if failed:
                print(f"[daily] 最终失败 {len(failed)} 只: {[s for s, _, _ in failed]}")
        if args.mode == "local":
            rebuild_stock_note_index()
            scr = fl.load_json(args.screener_file) if args.screener_file else fl.load_json(os.path.join(fl.FEED, "screener", "latest.json"), {})
            write_daily_analysis(scr.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"), uni)

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

    archive_pg()
    print("[daily] 完成。")


if __name__ == "__main__":
    main()
