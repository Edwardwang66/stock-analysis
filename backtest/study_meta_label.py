"""Meta-labeling 研究:OU/s-score 特征能否预测「这次残差反转下注会不会赚」(待办 L2)。

López de Prado meta-labeling:主模型(statarb 残差反转,s>0 做空/s<0 做多)给**方向**;
副模型(meta_label.LogitMeta)用**入场时可得特征**预测 P(这笔赚),用于**下注/过滤**(不改方向)。

流程:
  1. 复用 statarb.load_market + residual_signal,在每个 rebalance 日对每名算 OU 信号。
  2. 入场候选 = |s_score| ≥ s_open。特征 = [|s|, halflife, kappa, hurst, sigma_eq, |beta_mkt|, sigma_d]。
  3. 标签 = 该下注未来 H 日是否赚:bet=sign(-s);残差未来收益 ≈ name_fwd − beta_mkt·spy_fwd;
     label = 1 if bet·residual_fwd > 0。
  4. purged K 折(按 rebalance 日为事件时间,horizon=H 消重叠)→ OOS AUC。

诚实:这只评估**可预测性(AUC)**,不等于净·扣成本能盈利;主信号在免费数据上净 alpha≈0/负
(见 README_statarb),故先验上 meta-label 大概率只搬移噪声。AUC≤0.5 → 诚实否定,不接入。

用法:python backtest/study_meta_label.py [--start-year 2018] [--step 5] [--horizon 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import statarb as sa  # noqa: E402
import meta_label as ml  # noqa: E402

FEATURES = ["abs_s", "halflife", "kappa", "hurst", "sigma_eq", "abs_beta", "sigma_d"]


def collect(dates, spy_ret, sector_ret, names, p, step: int, horizon: int):
    """扫描 rebalance 日,收集入场候选的 (特征, 标签, 事件时间)。"""
    X, y, tev = [], [], []
    n = len(dates)
    ks = list(range(p.window + 1, n - horizon, step))
    for k in ks:
        spy_fwd = float(np.nansum(spy_ret[k + 1:k + 1 + horizon]))
        for tk, nm in names.items():
            sig = sa.residual_signal(nm["ret"], spy_ret, sector_ret.get(nm["etf"], spy_ret), k, p)
            if sig is None:
                continue
            s = sig["s_score"]
            if not np.isfinite(s) or abs(s) < p.s_open:
                continue
            hl, hu = sig["halflife_days"], sig["hurst"]
            if not np.isfinite(hl) or not np.isfinite(hu):
                continue
            # 入场时可得特征
            win = nm["ret"][max(1, k - p.window + 1):k + 1]
            win = win[np.isfinite(win)]
            sigma_d = float(np.std(win)) if len(win) > 5 else 0.02
            feat = [abs(s), hl, sig["kappa"], hu, sig["sigma_eq"],
                    abs(sig.get("beta_mkt", 0.0)), sigma_d]
            if not all(np.isfinite(v) for v in feat):
                continue
            # 未来残差收益(代理:剔市场 beta);bet = 反转方向
            name_fwd = float(np.nansum(nm["ret"][k + 1:k + 1 + horizon]))
            resid_fwd = name_fwd - sig.get("beta_mkt", 0.0) * spy_fwd
            bet = -np.sign(s)
            pnl = bet * resid_fwd
            X.append(feat)
            y.append(1.0 if pnl > 0 else 0.0)
            tev.append(float(k))
    return np.array(X), np.array(y), np.array(tev)


def main() -> int:
    ap = argparse.ArgumentParser(description="Meta-labeling 研究")
    ap.add_argument("--start-year", type=int, default=2018)
    ap.add_argument("--step", type=int, default=5)
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "feed", "longterm", "meta_label.json"))
    args = ap.parse_args()

    p = sa.StatArbParams()
    tickers = sa.DEMO_UNIVERSE if hasattr(sa, "DEMO_UNIVERSE") else None
    print("加载市场 ...")
    dates, spy_ret, sector_ret, names = sa.load_market(tickers, args.start_year)
    print(f"标的 {len(names)} 只, {len(dates)} 日")

    X, y, tev = collect(dates, spy_ret, sector_ret, names, p, args.step, args.horizon)
    print(f"入场候选样本 {len(y)}(正类 {int(y.sum())} / {y.mean()*100:.1f}%)")
    if len(y) < 100 or len(np.unique(y)) < 2:
        print("样本不足或单类,无法评估")
        return 1

    res = ml.cv_auc(X, y, tev, horizon=float(args.horizon), k=5, embargo=float(args.horizon),
                    l2=1.0, lr=0.2, n_iter=1500)
    # 单因子参照:仅 |s| 的 AUC(看 meta 模型相对单特征是否有增量)
    auc_abs_s = ml.auc(y, -X[:, 0])  # |s| 越大反转越强?方向未知,取两向较大
    auc_abs_s = max(auc_abs_s, 1 - auc_abs_s)

    base_rate = float(y.mean())
    verdict = ("AUC≤0.52,与抛硬币无异 → 诚实否定,meta-label 不接入下注层"
               if not np.isfinite(res["oos_auc"]) or res["oos_auc"] <= 0.52
               else "AUC>0.52,有弱可预测性;但须再过净·扣成本下注回测才可接入")
    out = {
        "schema_version": "1.0", "kind": "meta_label_study",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "features": FEATURES, "n_samples": int(len(y)), "base_rate": base_rate,
        "horizon_days": args.horizon, "step": args.step,
        "oos_auc": res["oos_auc"], "fold_aucs": res["fold_aucs"], "n_scored": res["n_scored"],
        "auc_single_abs_s": float(auc_abs_s),
        "verdict": verdict,
        "caveats": [
            "残差未来收益用市场 beta 代理(未含行业 ETF beta),标签有近似",
            "可预测性(AUC)≠净·扣成本可盈利;主信号本身净 alpha≈0/负",
            "purged K 折已消重叠标签泄漏;但 universe 为当前成分(幸存者偏差)",
        ],
    }
    op = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(op), exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("=" * 56)
    print(f"  OOS AUC = {res['oos_auc']:.4f}  (各折 {[round(a,3) for a in res['fold_aucs']]})")
    print(f"  单特征 |s| AUC = {auc_abs_s:.4f}  | 基率(正类占比) = {base_rate:.3f}")
    print(f"  诚实裁决:{verdict}")
    print("=" * 56)
    print(f"写入 {op}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
