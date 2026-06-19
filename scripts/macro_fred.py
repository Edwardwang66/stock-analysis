#!/usr/bin/env python3
"""FRED 宏观风险拨盘 → feed/macro/latest.json。LIS L-1/L-4(见 docs/long-term-investment-system.md)。

诚实定位(research/long-term/macro-leading-indicators.md):
  宏观择时历史记录差(Goyal-Welch 样本外 R²≈0)。**只做温和风险拨盘,不做择时**。
  连续 risk_dial∈[0,1](1=risk-on),喂给 L-4 总敞口软开关 + 看板,不直接产买卖信号。

数据:FRED `fredgraph.csv?id=SERIES` 端点**无需 API key**(keyless,公开)。
  权重先验:信用 > 曲线 > 金融条件 > 劳动(市场定价类优先于历史回归外推)。
  弃用 ISM/LEI(已从 FRED 下架/版权)。

PIT 注记:本拨盘用**最新值**(风险温度计,非回测信号)。若要回测须改用 ALFRED vintage
  (realtime_start/end)且 Sahm 用 SAHMREALTIME,否则前视污染——见报告 §PIT。

纯评分逻辑(score_* / compute_dial)与抓取分离,可离线单测。仅标准库。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feed" / "macro" / "latest.json"
UA = {"User-Agent": "stock-analysis-dashboard admin@example.com"}

# series_id → 用途。权重见 WEIGHTS。
SERIES = {
    "credit": "BAMLH0A0HYM2",   # ICE BofA US High Yield OAS(信用利差,主驱动)
    "curve": "T10Y3M",          # 10y-3m 期限利差(倒挂=衰退前兆,但滞后)
    "fci": "NFCI",              # Chicago Fed 全国金融条件指数(>0 偏紧)
    "unrate": "UNRATE",         # 失业率(算 Sahm)
}
WEIGHTS = {"credit": 0.40, "curve": 0.25, "fci": 0.20, "labor": 0.15}


# ----------------------------- 纯评分(risk_on=1 好 / risk_off=0 差)-----------------------------

def _lin(x: float, lo: float, hi: float) -> float:
    """把 x 从 [lo,hi] 线性映射到 [0,1] 并截断(lo→0, hi→1)。lo>hi 则反向。"""
    if lo == hi:
        return 0.5
    t = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, t))


def score_credit(oas_pct: float) -> float:
    """HY OAS(百分点):≤3.5% 宽松(1.0)/ ≥6.5% 承压(0.0)。低利差=风险偏好高。"""
    return _lin(oas_pct, 6.5, 3.5)  # 反向:高 OAS→0


def score_curve(t10y3m_pct: float) -> float:
    """期限利差:≥1.0% 正常(1.0)/ ≤-0.5% 深度倒挂(0.0)。倒挂=风险拨低(温和)。"""
    return _lin(t10y3m_pct, -0.5, 1.0)


def score_fci(nfci: float) -> float:
    """NFCI:≤-0.5 宽松(1.0)/ ≥+0.5 收紧(0.0)。"""
    return _lin(nfci, 0.5, -0.5)  # 反向:高 NFCI→0


def sahm_gap(unrate_hist: list[float]) -> float | None:
    """Sahm:近 3 月失业率均值 − 过去 12 月最低。≥0.5 触发衰退信号。需≥12 个月。"""
    if len(unrate_hist) < 12:
        return None
    recent3 = sum(unrate_hist[-3:]) / 3.0
    low12 = min(unrate_hist[-12:])
    return recent3 - low12


def score_labor(sahm: float | None) -> float | None:
    """Sahm gap:≤0 健康(1.0)/ ≥0.5 衰退信号(0.0)。"""
    if sahm is None:
        return None
    return _lin(sahm, 0.5, 0.0)  # 反向:高 gap→0


def compute_dial(credit_oas: float | None, curve: float | None,
                 nfci: float | None, unrate_hist: list[float]) -> dict:
    """合成 risk_dial∈[0,1](可用分项加权平均,权重按可得性归一)。返回 {risk_dial, regime, components}。"""
    comp: dict[str, dict] = {}
    if credit_oas is not None:
        comp["credit"] = {"value": credit_oas, "score": round(score_credit(credit_oas), 3), "w": WEIGHTS["credit"]}
    if curve is not None:
        comp["curve"] = {"value": curve, "score": round(score_curve(curve), 3), "w": WEIGHTS["curve"]}
    if nfci is not None:
        comp["fci"] = {"value": nfci, "score": round(score_fci(nfci), 3), "w": WEIGHTS["fci"]}
    sahm = sahm_gap(unrate_hist)
    ls = score_labor(sahm)
    if ls is not None:
        comp["labor"] = {"value": round(sahm, 3), "score": round(ls, 3), "w": WEIGHTS["labor"]}

    if not comp:
        return {"risk_dial": None, "regime": "unknown", "components": {}}
    wsum = sum(c["w"] for c in comp.values())
    dial = sum(c["score"] * c["w"] for c in comp.values()) / wsum
    regime = "risk_on" if dial >= 0.6 else ("risk_off" if dial <= 0.35 else "neutral")
    return {"risk_dial": round(dial, 3), "regime": regime, "components": comp}


# ----------------------------- 抓取(keyless CSV)-----------------------------

def fetch_series(series_id: str) -> list[tuple[str, float]]:
    """fredgraph.csv:返回 [(date, value)],跳过缺失('.')。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8", "replace")
    out = []
    for line in text.splitlines()[1:]:  # 跳过表头
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), parts[-1].strip()
        if v and v != ".":
            try:
                out.append((d, float(v)))
            except ValueError:
                pass
    return out


def _latest(series: list[tuple[str, float]]) -> tuple[str | None, float | None]:
    return (series[-1][0], series[-1][1]) if series else (None, None)


def main() -> int:
    ap = argparse.ArgumentParser(description="FRED 宏观风险拨盘")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    data, asof = {}, None
    for key, sid in SERIES.items():
        try:
            s = fetch_series(sid)
            data[key] = s
            d, _ = _latest(s)
            if d and (asof is None or d > asof):
                asof = d
            print(f"  {key:7} {sid:14} 末值 {s[-1][1] if s else 'NA'} @ {s[-1][0] if s else 'NA'}")
        except Exception as e:  # noqa: BLE001
            print(f"  {key}: 抓取失败 {e}", file=sys.stderr)
            data[key] = []

    _, credit = _latest(data.get("credit", []))
    _, curve = _latest(data.get("curve", []))
    _, nfci = _latest(data.get("fci", []))
    unrate_hist = [v for _, v in data.get("unrate", [])]

    dial = compute_dial(credit, curve, nfci, unrate_hist)
    doc = {
        "schema_version": "1.0",
        "kind": "macro_risk_dial",
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asof_data": asof,
        "source": "FRED fredgraph.csv (keyless)",
        "note": ("温和风险拨盘,非择时/非投资建议。risk_dial∈[0,1](1=risk-on)。"
                 "用最新值(温度计);回测须改 ALFRED vintage 防前视。"),
        "series": {k: SERIES[k] for k in SERIES},
        **dial,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"写入 {out_path}:risk_dial={dial['risk_dial']} regime={dial['regime']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
