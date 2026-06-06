"""走向前(walk-forward)样本外回测 —— 杜绝数据窥探/未来函数。

针对上一版"在同一段数据上既选阈值又报正确率"的 in-sample 作弊问题,这里做严格隔离:

  1. 时间切分:按自然年滚动。测试年 Y 的所有判断,只允许用 Y 之前的数据来拟合。
  2. Embargo(隔离带):标签是"未来 H 日收益",训练段末尾样本的标签窗口会探入测试段。
     因此训练样本必须满足  entry_date + H < test_start,否则丢弃(purged)。
  3. 两套"因子产出方式"都做样本外:
       A) TQM 阈值:在训练段网格搜索最优阈值 -> 冻结 -> 只在测试段评估。
       B) 逻辑回归:在训练段用 [trend,mom,qual,rsi] 拟合 P(涨) -> 冻结 -> 测试段预测。
  4. 同时打印 训练集(in-sample) 与 测试集(out-of-sample) 指标,差距即"窥探溢价"。

样本外正确率 = 测试段真实可达的水平。这才是诚实的数字。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression

import data as datamod
import factors

HERE = os.path.dirname(os.path.abspath(__file__))
DAY = 86400


def build_samples(horizon: int, sample_every: int = 3):
    """汇集全市场 (特征, 标签, 时间) 池。特征均为 t 时刻可得,无未来函数。"""
    uni = json.load(open(os.path.join(HERE, "universe.json")))
    feats, fwd, tss = [], [], []
    for tk in uni["universe"]:
        d = datamod.load(tk)
        if not d or len(d.get("adjclose", [])) <= horizon + 260:
            continue
        px = np.asarray(d["adjclose"], dtype=float)
        ts = np.asarray(d["ts"], dtype=np.int64)
        t = factors.trend(px)
        m = factors.momentum(px)
        q = factors.quality(px)
        r = factors.rsi(px)
        fr = np.full_like(px, np.nan)
        fr[:-horizon] = px[horizon:] / px[:-horizon] - 1.0
        for i in range(0, len(px), sample_every):
            if np.isnan(t[i]) or np.isnan(m[i]) or np.isnan(q[i]) or np.isnan(r[i]) or np.isnan(fr[i]):
                continue
            feats.append((t[i], m[i], q[i], r[i]))
            fwd.append(fr[i])
            tss.append(int(ts[i]))
    X = np.asarray(feats, dtype=float)
    y = np.asarray(fwd, dtype=float)
    t = np.asarray(tss, dtype=np.int64)
    order = np.argsort(t)
    return X[order], y[order], t[order]


def year_start(y: int) -> int:
    return int(dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp())


# ---- 策略 A:TQM 阈值,训练段网格搜索 ----
GRID = [(tm, mm, qm, rm)
        for tm in (1.0,)
        for mm in (0.0, 0.05, 0.10, 0.15, 0.20)
        for qm in (0.0, 0.5, 1.0, 1.5)
        for rm in (75.0, 80.0, 90.0)]


def tqm_mask(X, p):
    return (X[:, 0] >= p[0]) & (X[:, 1] >= p[1]) & (X[:, 2] >= p[2]) & (X[:, 3] < p[3])


def metrics(mask, y):
    n = int(mask.sum())
    if n == 0:
        return n, float("nan"), float("nan")
    sel = y[mask]
    return n, float((sel > 0).mean()), float(sel.mean())


def run(horizon: int = 63, test_years=(2021, 2022, 2023, 2024, 2025)):
    print(f"构建样本池 H={horizon} ...")
    X, y, t = build_samples(horizon)
    print(f"样本数 {len(y):,}  时间跨度 "
          f"{dt.datetime.utcfromtimestamp(t[0]).date()} ~ "
          f"{dt.datetime.utcfromtimestamp(t[-1]).date()}\n")

    embargo = int(horizon * 1.5 * DAY)   # 隔离带:覆盖标签前瞻窗口
    rows_a, rows_b = [], []

    for Y in test_years:
        ts_start, ts_end = year_start(Y), year_start(Y + 1)
        test = (t >= ts_start) & (t < ts_end)
        # 训练:测试开始前,且其标签窗口不探入测试段(embargo)
        train = t < (ts_start - embargo)
        if test.sum() < 50 or train.sum() < 500:
            continue
        Xtr, ytr = X[train], y[train]
        Xte, yte = X[test], y[test]

        # --- A) TQM 阈值:训练段挑期望最高的参数,冻结后测试 ---
        best_p, best_obj = None, -1e9
        for p in GRID:
            n, hr, exp = metrics(tqm_mask(Xtr, p), ytr)
            if n >= 200 and exp > best_obj:   # 训练样本足够才考虑
                best_obj, best_p = exp, p
        ntr, hrtr, _ = metrics(tqm_mask(Xtr, best_p), ytr)
        nte, hrte, expte = metrics(tqm_mask(Xte, best_p), yte)
        rows_a.append((Y, best_p, ntr, hrtr, nte, hrte, expte))

        # --- B) 逻辑回归:训练拟合 P(涨),阈值取训练段 70 分位,测试段评估 ---
        clf = LogisticRegression(max_iter=1000, C=1.0)
        clf.fit(Xtr, (ytr > 0).astype(int))
        ptr = clf.predict_proba(Xtr)[:, 1]
        thr = np.quantile(ptr, 0.85)          # 只取最高信心的 15%
        ntr_b, hrtr_b, _ = metrics(ptr >= thr, ytr)
        pte = clf.predict_proba(Xte)[:, 1]
        nte_b, hrte_b, expte_b = metrics(pte >= thr, yte)
        rows_b.append((Y, ntr_b, hrtr_b, nte_b, hrte_b, expte_b))

    print("=== 策略A:TQM 阈值(训练段网格搜索 -> 冻结 -> 样本外测试) ===")
    print(f"{'测试年':>6} {'选中参数(mom,qual,rsi)':>22} {'训练正确率':>9} {'样本外正确率':>11} {'样本外期望':>9}")
    for Y, p, ntr, hrtr, nte, hrte, expte in rows_a:
        print(f"{Y:>6} {str((p[1],p[2],p[3])):>22} "
              f"{hrtr*100:>8.1f}% {hrte*100:>10.1f}% {expte*100:>8.1f}%  (n={nte})")
    _pool(rows_a, "A", idx_n=4, idx_hr=5)

    print("\n=== 策略B:逻辑回归 P(涨)(训练拟合 -> 冻结 -> 样本外测试) ===")
    print(f"{'测试年':>6} {'训练正确率':>9} {'样本外正确率':>11} {'样本外期望':>9}")
    for Y, ntr, hrtr, nte, hrte, expte in rows_b:
        print(f"{Y:>6} {hrtr*100:>8.1f}% {hrte*100:>10.1f}% {expte*100:>8.1f}%  (n={nte})")
    _pool(rows_b, "B", idx_n=3, idx_hr=4)


def _pool(rows, name, idx_n, idx_hr):
    tot = sum(r[idx_n] for r in rows)
    if tot == 0:
        return
    w = sum(r[idx_n] * r[idx_hr] for r in rows) / tot
    print(f"  -> 策略{name} 合并样本外正确率(按笔数加权) = {w*100:.1f}%  (共 {tot} 笔)")


if __name__ == "__main__":
    run()
