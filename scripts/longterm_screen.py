#!/usr/bin/env python3
"""长期腿质量筛选 → feed/longterm/longscore.json。LIS L-2/L-3 最小切片(见 docs/long-term-investment-system.md)。

链路:EDGAR PIT 两期面板(edgar_fundamentals)→ 派生质量/安全比率 + 三剔除闸(factors_fundamental)
      → 横截面 rank-z 合成 QualityScore(integrated 骨架,等权)→ 硬剔除闸过滤 → 排序输出。

诚实边界(本切片只有质量+安全,**没有价值**):
  - 价值因子(E/P、EBIT/EV、股东收益)需 join 行情市值,留 L-2 价格层;此处先把"不依赖价格"的腿落地。
  - QualityScore 不是 alpha 承诺:见 research/long-term/quality-moat-factors.md。上线前须过 7 关验证
    (PIT/Deflated Sharpe/CSCV-PBO/t>3/2022 holdout/正交增量/净·扣成本)。本脚本只产**候选清单**,不下单。

纯逻辑(score_panel / xs_zscore)与网络抓取分离,可离线单测。仅标准库。

用法:
  python scripts/longterm_screen.py --universe scripts/ndx100.json --as-of 2024-12-31
  python scripts/longterm_screen.py --tickers AAPL,MSFT,NVDA,GOOGL --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backtest"))

OUT = ROOT / "feed" / "longterm" / "longscore.json"

# 质量/安全因子:(特征键, 方向)。方向 +1=越大越好,-1=越小越好(合成前取负)。
# 价值腿(需价格)不在此处。来源见 quality-moat / accruals / compounders 报告。
QUALITY_FACTORS: dict[str, int] = {
    "gross_profitability": +1,   # Novy-Marx 毛利率
    "cash_op_to_assets": +1,     # 现金型经营利润(吞并应计)
    "roic": +1,                  # 投入资本回报
    "roe": +1,                   # 股东回报
    "net_margin": +1,            # 净利率
    "accruals_to_assets": -1,    # 应计(越低越好)
    "piotroski_f": +1,           # 基本面改善地板(0-9)
}


# ----------------------------- 纯逻辑:横截面合成(无 numpy)-----------------------------

def _mean_std(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, var ** 0.5


def xs_zscore(values: list[float | None], direction: int, clip: float = 3.0) -> list[float | None]:
    """横截面 z-score:对非缺失值标准化,按方向取号,截尾 ±clip。缺失保持 None。"""
    present = [v for v in values if v is not None]
    if len(present) < 3:
        return [None] * len(values)
    m, s = _mean_std(present)
    if s == 0:
        return [0.0 if v is not None else None for v in values]
    out: list[float | None] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        z = (v - m) / s * direction
        out.append(max(-clip, min(clip, z)))
    return out


def score_panel(features: list[dict]) -> list[dict]:
    """features:每名一个 dict(含 QUALITY_FACTORS 各键 + 'ticker' + 'exclude' + 'reasons'/'flags')。
    返回带 z 分解 + quality_score + rank 的副本,按 quality_score 降序(剔除项排末尾)。"""
    n = len(features)
    zmat: dict[str, list] = {}
    for fac, direction in QUALITY_FACTORS.items():
        col = [f.get(fac) for f in features]
        zmat[fac] = xs_zscore(col, direction)
    out = []
    for i, f in enumerate(features):
        zs = {fac: zmat[fac][i] for fac in QUALITY_FACTORS}
        avail = [z for z in zs.values() if z is not None]
        score = sum(avail) / len(avail) if len(avail) >= 2 else None  # 等权,≥2 个因子才有效
        out.append({**f, "z": {k: (round(v, 3) if v is not None else None) for k, v in zs.items()},
                    "quality_score": round(score, 4) if score is not None else None,
                    "n_factors": len(avail)})
    # 排序:未剔除且有分的在前(分高优先);剔除/无分的沉底
    def key(r):
        excluded = r.get("exclude", False) or r.get("quality_score") is None
        return (excluded, -(r.get("quality_score") or -99))
    out.sort(key=key)
    for rank, r in enumerate(out, 1):
        r["rank"] = rank
    return out


# ----------------------------- 网络:构建面板 -----------------------------

def build_features(tickers: list[str], as_of: str) -> tuple[list[dict], list[str]]:
    import edgar_fundamentals as ef
    from factors_fundamental import exclusion_screen

    tmap = ef.load_ticker_cik_map()
    feats, missing = [], []
    for i, t in enumerate(tickers):
        cik = tmap.get(t)
        if not cik:
            missing.append(t)
            continue
        try:
            facts = ef.fetch_companyfacts(cik)
            cur, prev = ef.extract_two_year(facts, as_of)
            ratios = ef.derive_ratios(cur)
            screen = exclusion_screen(cur, prev)
            row = {"ticker": t, "cik": cik, "period_end": cur.get("period_end"),
                   "exclude": screen["exclude"], "reasons": screen["reasons"],
                   "flags": screen["flags"], "scores": screen["scores"]}
            for fac in QUALITY_FACTORS:
                row[fac] = ratios.get(fac) if fac in ratios else screen["scores"].get(fac)
            feats.append(row)
            print(f"  [{i+1}/{len(tickers)}] {t} ✓ excl={screen['exclude']}")
        except Exception as e:  # noqa: BLE001
            print(f"  {t}: 失败 {e}", file=sys.stderr)
            missing.append(t)
        time.sleep(0.12)
    return feats, missing


def load_universe(arg: str) -> list[str]:
    p = Path(arg)
    if p.exists():
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return [str(x).split(":")[-1].upper() for x in data]
        if isinstance(data, dict):
            return [str(x).split(":")[-1].upper() for x in data.get("tickers", data.keys())]
    return [t.strip().upper() for t in arg.split(",") if t.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="长期腿质量筛选")
    ap.add_argument("--tickers")
    ap.add_argument("--universe")
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--top", type=int, default=0, help="只输出前 N(0=全部)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    tickers = load_universe(args.universe or args.tickers or "")
    if not tickers:
        print("需要 --tickers 或 --universe", file=sys.stderr)
        return 2

    print(f"映射 + 抓取 {len(tickers)} 名 …")
    feats, missing = build_features(tickers, args.as_of)
    ranked = score_panel(feats)
    if args.top:
        keep_excl = [r for r in ranked if r.get("exclude")]
        ranked = ranked[:args.top] + keep_excl

    n_excl = sum(1 for r in ranked if r.get("exclude"))
    doc = {
        "schema_version": "1.0",
        "kind": "longterm_quality_screen",
        "as_of": args.as_of,
        "note": ("质量+安全合成(无价值腿,价值需价格层 join)。横截面 rank-z 等权 integrated 合成。"
                 "候选清单,非下单信号,非投资建议;上线前须过 7 关验证。"),
        "factors": list(QUALITY_FACTORS),
        "universe_size": len(tickers),
        "n_scored": sum(1 for r in ranked if r.get("quality_score") is not None),
        "n_excluded": n_excl,
        "missing": missing,
        "rows": ranked,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"写入 {out_path}:{doc['n_scored']} 有分 / {n_excl} 剔除 / 缺 {len(missing)}")
    # 顶部预览
    for r in ranked[:10]:
        if r.get("quality_score") is not None and not r.get("exclude"):
            print(f"  #{r['rank']:2} {r['ticker']:6} Q={r['quality_score']:+.3f} (n={r['n_factors']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
