#!/usr/bin/env python3
"""LIS L-5 验证 harness:LongScore 对未来收益的预测力裁决(见 docs/long-term-investment-system.md §7)。

在宣称任何 alpha 前,LongScore 必须过这关。本脚本在**历史多个 as_of 时点**重建 PIT 面板:
  - companyfacts 含全历史 → 每票只抓一次(缓存),在每个 as_of 离线切片(filed<=as_of,无前视)。
  - 价格走 backtest/data.py 缓存;未来 1 年收益 = price(as_of+1y)/price(as_of)-1。
  - 每期算 Rank-IC(Spearman(LongScore, fwd_ret))+ 分位价差;跨期聚合 IC 均值/ICIR/t。

诚实裁决(房子纪律):
  - **NDX100 是当前成分 → 强幸存者偏差**(IC 系统性偏高)。无 PIT 成分史前,这是上界不是真值。
  - 年度重叠极小但**有效期数极少**(~8),t 统计虚高;Deflated Sharpe 对小样本惩罚重。
  - 无交易成本、无退市票。**IC 显著 ≠ 净·扣成本可盈利**。结论只作方向参考,不据此宣称 alpha。

用法:
  python backtest/study_longscore.py --universe scripts/ndx100.json --start 2016 --end 2023
  python backtest/study_longscore.py --tickers AAPL,MSFT,... --start 2017 --end 2023 --no-value
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backtest"))

import edgar_fundamentals as ef  # noqa: E402
import data as pricedata  # noqa: E402
from factors_fundamental import exclusion_screen  # noqa: E402
from factors_value import value_factors, price_asof  # noqa: E402
from factors_xs import spearman, rankdata  # noqa: E402
import numpy as np  # noqa: E402

CACHE = ROOT / "backtest" / "edgar_cache"
QUALITY_FACTORS = {"gross_profitability": +1, "cash_op_to_assets": +1, "roic": +1, "roe": +1,
                   "net_margin": +1, "accruals_to_assets": -1, "piotroski_f": +1}
VALUE_FACTORS = {"earnings_yield": +1, "ebit_ev": +1, "fcf_ev": +1, "book_to_price": +1,
                 "shareholder_yield": +1}


# ----------------------------- companyfacts 磁盘缓存 -----------------------------

def cached_facts(ticker: str, cik: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{cik}.json"
    if p.exists() and p.stat().st_size > 100:
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            pass
    try:
        facts = ef.fetch_companyfacts(cik)
        p.write_text(json.dumps(facts))
        time.sleep(0.12)
        return facts
    except Exception as e:  # noqa: BLE001
        print(f"  ! {ticker} companyfacts 失败 {e}", file=sys.stderr)
        return None


# ----------------------------- 纯逻辑:横截面 z + IC -----------------------------

def xs_z(col: list[float | None], direction: int) -> list[float | None]:
    present = [v for v in col if v is not None]
    if len(present) < 5:
        return [None] * len(col)
    m = sum(present) / len(present)
    sd = (sum((v - m) ** 2 for v in present) / (len(present) - 1)) ** 0.5
    if sd == 0:
        return [0.0 if v is not None else None for v in col]
    return [None if v is None else max(-3.0, min(3.0, (v - m) / sd * direction)) for v in col]


def composite(feats: list[dict], factors: dict) -> list[float | None]:
    """对一组名的 features 算 bucket 合成分(各因子 rank-z 等权,≥2 个有效)。"""
    zmat = {f: xs_z([x.get(f) for x in feats], d) for f, d in factors.items()}
    out = []
    for i in range(len(feats)):
        zs = [zmat[f][i] for f in factors if zmat[f][i] is not None]
        out.append(sum(zs) / len(zs) if len(zs) >= 2 else None)
    return out


def rank_ic(scores: list[float | None], fwd: list[float | None]) -> float | None:
    """Spearman(score, fwd_ret),只用两者都非缺失的名。"""
    xs = [(s, f) for s, f in zip(scores, fwd) if s is not None and f is not None]
    if len(xs) < 8:
        return None
    a = np.array([x[0] for x in xs]); b = np.array([x[1] for x in xs])
    return spearman(a, b)


def neutralize(scores: list[float | None], controls: list[list[float | None]]) -> list[float | None]:
    """横截面把 scores 对 controls(各一列)做 OLS,返回残差(正交化分);
    只在 scores 与全部 controls 均非缺失的名上回归,其余 None。用于测对动量/规模的增量。"""
    nC = len(controls)
    idx = [i for i in range(len(scores))
           if scores[i] is not None and all(controls[c][i] is not None for c in range(nC))]
    if len(idx) < 10:
        return [None] * len(scores)
    y = np.array([scores[i] for i in idx], dtype=float)
    cols = [np.ones(len(idx))]
    for c in range(nC):
        v = np.array([controls[c][i] for i in idx], dtype=float)
        sd = v.std(ddof=1)
        cols.append((v - v.mean()) / sd if sd > 0 else np.zeros(len(idx)))
    X = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    out: list[float | None] = [None] * len(scores)
    for k, i in enumerate(idx):
        out[i] = float(resid[k])
    return out


def quintile_spread(scores: list[float | None], fwd: list[float | None]) -> float | None:
    """顶 quintile 平均未来收益 − 底 quintile(分层单调性的粗测)。"""
    xs = [(s, f) for s, f in zip(scores, fwd) if s is not None and f is not None]
    if len(xs) < 10:
        return None
    xs.sort(key=lambda t: t[0])
    k = max(1, len(xs) // 5)
    bot = sum(f for _, f in xs[:k]) / k
    top = sum(f for _, f in xs[-k:]) / k
    return top - bot


# ----------------------------- 面板构建(单 as_of)-----------------------------

def panel_at(as_of: str, tickers: list[str], facts_map: dict, with_value: bool) -> list[dict]:
    feats = []
    for t in tickers:
        facts = facts_map.get(t)
        if not facts:
            continue
        try:
            cur, prev = ef.extract_two_year(facts, as_of)
            if cur.get("period_end") is None:
                continue
            ratios = ef.derive_ratios(cur)
            screen = exclusion_screen(cur, prev)
            row = {"ticker": t, "exclude": screen["exclude"]}
            for f in QUALITY_FACTORS:
                row[f] = ratios.get(f) if f in ratios else screen["scores"].get(f)
            if with_value:
                sh, _, _ = ef.shares_outstanding(facts, as_of)
                bars = pricedata.load(t)
                px = price_asof(bars, as_of)
                vf = value_factors({**cur, "shares": sh}, px)
                for f in VALUE_FACTORS:
                    row[f] = vf.get(f)
                # 正交化控制项:价格动量(12-1)+ 规模(log 市值)
                a = date.fromisoformat(as_of)
                p_skip = price_asof(bars, date.fromordinal(a.toordinal() - 30).isoformat())
                p_12 = price_asof(bars, date.fromordinal(a.toordinal() - 365).isoformat())
                row["_mom"] = (p_skip / p_12 - 1.0) if p_skip and p_12 and p_12 > 0 else None
                mc = vf.get("market_cap")
                row["_size"] = (float(np.log(mc)) if mc and mc > 0 else None)
            feats.append(row)
        except Exception:  # noqa: BLE001
            continue
    return feats


def fwd_returns(tickers_in_panel: list[str], as_of: str, horizon_days: int = 365) -> dict:
    a = date.fromisoformat(as_of)
    fut_s = date.fromordinal(a.toordinal() + horizon_days).isoformat()
    out = {}
    for t in tickers_in_panel:
        bars = pricedata.load(t)
        p0 = price_asof(bars, as_of)
        p1 = price_asof(bars, fut_s)
        # 要求 p1 来自 as_of 之后(避免 as_of 晚于数据末尾时 p0==p1)
        if p0 and p1 and p1 != p0:
            out[t] = p1 / p0 - 1.0
    return out


# ----------------------------- 主流程 -----------------------------

def load_universe(arg: str) -> list[str]:
    p = Path(arg)
    if p.exists():
        d = json.loads(p.read_text())
        return [str(x).split(":")[-1].upper() for x in (d if isinstance(d, list) else d.get("tickers", []))]
    return [t.strip().upper() for t in arg.split(",") if t.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="LongScore 验证 harness")
    ap.add_argument("--tickers")
    ap.add_argument("--universe")
    ap.add_argument("--start", type=int, default=2016)
    ap.add_argument("--end", type=int, default=2023)
    ap.add_argument("--month", default="06-30", help="每年 as_of 月日")
    ap.add_argument("--no-value", action="store_true")
    ap.add_argument("--force-prices", action="store_true",
                    help="强制重下 10y 行情(首跑或缓存只有浅历史时需要)")
    ap.add_argument("--out", default=str(ROOT / "feed" / "longterm" / "validation.json"))
    ap.add_argument("--md", default=None)
    args = ap.parse_args()
    with_value = not args.no_value

    tickers = load_universe(args.universe or args.tickers or "")
    if not tickers:
        print("需要 --tickers 或 --universe", file=sys.stderr)
        return 2

    print(f"映射 CIK + 抓取/缓存 companyfacts({len(tickers)} 名)…")
    tmap = ef.load_ticker_cik_map()
    facts_map = {}
    for i, t in enumerate(tickers):
        cik = tmap.get(t)
        if cik:
            f = cached_facts(t, cik)
            if f:
                facts_map[t] = f
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(tickers)}")
    print(f"  companyfacts 就绪 {len(facts_map)}/{len(tickers)}")

    if with_value:
        print(f"下载行情(10y,用于市值 + 未来收益;force={args.force_prices})…")
        pricedata.fetch_universe(tickers, range_="10y", workers=10, force=args.force_prices)

    as_ofs = [f"{y}-{args.month}" for y in range(args.start, args.end + 1)]
    periods = []
    for as_of in as_ofs:
        feats = panel_at(as_of, tickers, facts_map, with_value)
        if len(feats) < 10:
            print(f"  {as_of}: 面板太小({len(feats)}),跳过")
            continue
        names = [f["ticker"] for f in feats]
        fwd = fwd_returns(names, as_of)
        fwd_list = [fwd.get(f["ticker"]) for f in feats]
        n_fwd = sum(1 for x in fwd_list if x is not None)
        if n_fwd < 10:
            print(f"  {as_of}: 未来收益太少({n_fwd}),跳过(可能超出行情区间)")
            continue
        qz = composite(feats, QUALITY_FACTORS)
        vz = composite(feats, VALUE_FACTORS) if with_value else [None] * len(feats)
        # LongScore = 各 bucket 等权
        long_s = []
        for i in range(len(feats)):
            bs = [b for b in (qz[i], vz[i]) if b is not None]
            long_s.append(sum(bs) / len(bs) if bs else None)
        # 对动量(12-1)+ 规模正交化后的 LongScore 增量 IC
        ic_orth = None
        if with_value:
            mom = [f.get("_mom") for f in feats]
            size = [f.get("_size") for f in feats]
            long_orth = neutralize(long_s, [mom, size])
            ic_orth = rank_ic(long_orth, fwd_list)
        rec = {
            "as_of": as_of, "n": len(feats), "n_fwd": n_fwd,
            "ic_long": rank_ic(long_s, fwd_list),
            "ic_long_orth": ic_orth,
            "ic_quality": rank_ic(qz, fwd_list),
            "ic_value": rank_ic(vz, fwd_list) if with_value else None,
            "qspread_long": quintile_spread(long_s, fwd_list),
            "mean_fwd": float(np.nanmean([x for x in fwd_list if x is not None])),
        }
        periods.append(rec)
        print(f"  {as_of}: n={rec['n']} IC_long={_f(rec['ic_long'])} "
              f"IC_⊥(动量/规模){_f(rec['ic_long_orth'])} "
              f"IC_Q={_f(rec['ic_quality'])} IC_V={_f(rec['ic_value'])} "
              f"Q5-Q1={_f(rec['qspread_long'])} mkt={rec['mean_fwd']:+.1%}")

    summary = _aggregate(periods)
    doc = {
        "schema_version": "1.0", "kind": "longscore_validation",
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "universe_size": len(tickers), "with_value": with_value,
        "as_of_grid": as_ofs, "n_periods": len(periods),
        "caveats": [
            "NDX/给定 universe 为当前成分→幸存者偏差,IC 偏高(上界非真值)",
            "有效期数极少(~8),t 统计虚高;无 Deflated Sharpe 级别样本",
            "无交易成本/退市票;IC 显著≠净·扣成本可盈利",
            "未对现有因子(HML/RMW/UMD)正交化(下一步)",
        ],
        "periods": periods, "summary": summary,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"\n写入 {args.out}")
    _print_summary(summary)
    if args.md:
        Path(args.md).write_text(_markdown(doc), encoding="utf-8")
        print(f"写入 {args.md}")
    return 0


def _f(x):
    return "—" if x is None else f"{x:+.3f}"


def _aggregate(periods: list[dict]) -> dict:
    def stats(key):
        vals = [p[key] for p in periods if p.get(key) is not None]
        if len(vals) < 2:
            return {"mean": None, "std": None, "icir": None, "t": None, "n": len(vals),
                    "hit": None}
        m = float(np.mean(vals)); sd = float(np.std(vals, ddof=1))
        icir = m / sd if sd > 0 else None
        t = (m / sd * (len(vals) ** 0.5)) if sd > 0 else None
        hit = float(np.mean([1.0 if v > 0 else 0.0 for v in vals]))
        return {"mean": m, "std": sd, "icir": icir, "t": t, "n": len(vals), "hit": hit}
    return {"ic_long": stats("ic_long"), "ic_long_orth": stats("ic_long_orth"),
            "ic_quality": stats("ic_quality"),
            "ic_value": stats("ic_value"), "qspread_long": stats("qspread_long")}


def _print_summary(s: dict):
    print("=" * 56)
    for k, lbl in [("ic_long", "LongScore IC"), ("ic_long_orth", "  ⊥动量/规模"),
                   ("ic_quality", "Quality IC"),
                   ("ic_value", "Value IC"), ("qspread_long", "Q5-Q1 spread")]:
        st = s[k]
        if st["mean"] is None:
            print(f"  {lbl:14} 样本不足")
            continue
        print(f"  {lbl:14} mean={st['mean']:+.4f} std={st['std']:.4f} "
              f"ICIR={_f(st['icir'])} t={_f(st['t'])} hit={st['hit']:.0%} (n={st['n']})")
    print("=" * 56)
    ic = s["ic_long"]
    if ic["t"] is not None:
        verdict = ("方向为正但样本不足以宣称显著" if abs(ic["t"]) < 2
                   else "IC t>2,但须警惕幸存者偏差+小样本;下一步正交化与净成本检验")
        print(f"  诚实裁决:{verdict}")


def _markdown(doc: dict) -> str:
    s = doc["summary"]; ic = s["ic_long"]
    lines = [f"# LongScore 验证研究({doc['n_periods']} 期)", "",
             f"> universe {doc['universe_size']} 名 · 价值腿 {'开' if doc['with_value'] else '关'} · "
             f"as_of 网格 {doc['as_of_grid'][0]}…{doc['as_of_grid'][-1]}", "",
             "## 聚合 IC", "", "| 指标 | mean | std | ICIR | t | 命中 | n |",
             "|---|---|---|---|---|---|---|"]
    for k, lbl in [("ic_long", "LongScore"), ("ic_long_orth", "LongScore⊥动量/规模"),
                   ("ic_quality", "Quality"),
                   ("ic_value", "Value"), ("qspread_long", "Q5-Q1")]:
        st = s[k]
        if st["mean"] is None:
            lines.append(f"| {lbl} | 样本不足 | | | | | |")
        else:
            lines.append(f"| {lbl} | {st['mean']:+.4f} | {st['std']:.4f} | {_f(st['icir'])} | "
                         f"{_f(st['t'])} | {st['hit']:.0%} | {st['n']} |")
    lines += ["", "## 逐期", "", "| as_of | n | IC_long | IC_Q | IC_V | Q5-Q1 | mkt |",
              "|---|---|---|---|---|---|---|"]
    for p in doc["periods"]:
        lines.append(f"| {p['as_of']} | {p['n']} | {_f(p['ic_long'])} | {_f(p['ic_quality'])} | "
                     f"{_f(p['ic_value'])} | {_f(p['qspread_long'])} | {p['mean_fwd']:+.1%} |")
    # 关键发现(从各 bucket 符号自动推导,诚实不粉饰)
    findings = []
    q, v = s["ic_quality"], s["ic_value"]
    if q["mean"] is not None:
        findings.append(f"质量腿 IC={q['mean']:+.3f}(t={_f(q['t'])},命中 {q['hit']:.0%})"
                        + ("——弱正,不显著。" if 0 <= q["mean"] < 0.05 or (q["t"] and abs(q["t"]) < 2)
                           else "。"))
    if v["mean"] is not None:
        if v["mean"] < 0:
            findings.append(f"**价值腿 IC={v['mean']:+.3f} 为负**——在该(成长/科技重)universe 里价值倾斜"
                            f"**反而拖累**(命中仅 {v['hit']:.0%}),印证调研:价值在成长指数里失效;"
                            f"按 universe 调 bucket 权重或对该 universe 关价值腿。")
        else:
            findings.append(f"价值腿 IC={v['mean']:+.3f}(t={_f(v['t'])})。")
    qs = s["qspread_long"]
    if qs["mean"] is not None and qs["mean"] < 0:
        findings.append(f"**Q5−Q1 价差={qs['mean']:+.3f} 为负**——综合分未能单调分选收益,合成有效性存疑。")
    lines += ["", "## 关键发现(自动)", ""]
    for f in findings:
        lines.append(f"- {f}")
    lines += ["", "## 诚实警告(必读)", ""]
    for c in doc["caveats"]:
        lines.append(f"- {c}")
    sig = ic["t"] is not None and abs(ic["t"]) >= 2
    lines += ["", f"**诚实裁决**:LongScore IC mean={_f(ic['mean'])} t={_f(ic['t'])} —— "
              + ("t≥2 但仍受幸存者偏差/小样本污染,须经对现有因子正交化 + 净·扣成本检验才可信。" if sig
                 else "**未达统计显著(|t|<2)**,叠加幸存者偏差与小样本,**不能宣称 alpha**。")
              + " 当前 `/longterm` 仅候选展示。下一步:① PIT 成分史消幸存者偏差 ② 对 HML/RMW/UMD 正交化 "
              + "③ 净·扣成本组合回测(2022 入 holdout)。", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
