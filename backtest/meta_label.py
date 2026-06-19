"""Meta-labeling(L2 下注层)—— López de Prado《Advances in Financial ML》ch.3。

分离**方向**与**下注大小**:主模型(如 statarb s-score)给方向;副模型(本模块的逻辑回归)用
入场时可得特征预测「这一次信号会不会赚」P∈[0,1],再用 P 过滤/缩放下注。**副模型不改方向**(R6 精神:
不让模型决策方向,只调注码),且必须**净·扣成本 + purged OOS** 才算数,否则只是又一层过拟合。

纯 numpy(无 sklearn/scipy):
  - LogitMeta : L2 正则逻辑回归(标准化 + 截距 + 批量梯度下降),fit/predict_proba。
  - purged_kfold : 时序 purged + embargo K 折(消重叠标签窗口泄漏)。
  - auc : Mann-Whitney 排名 AUC(无 scipy)。
  - cv_auc : 跑 purged CV,返回 OOS 概率 + 折内 AUC(诚实评估)。

诚实:meta-label 在弱主信号上通常只搬移噪声;上线前必须证明 OOS AUC>0.5 且**净·扣成本下注后** Sharpe 提升。
"""
from __future__ import annotations

import numpy as np


# ----------------------------- 逻辑回归(numpy)-----------------------------

class LogitMeta:
    """L2 正则逻辑回归。标准化在内部做(fit 存均值/方差,predict 复用)。"""

    def __init__(self, l2: float = 1.0, lr: float = 0.1, n_iter: int = 2000):
        self.l2 = float(l2)
        self.lr = float(lr)
        self.n_iter = int(n_iter)
        self.w = None          # 含截距:w[0]=bias
        self.mu = None
        self.sd = None

    def _stdz(self, X: np.ndarray, fit: bool) -> np.ndarray:
        if fit:
            self.mu = X.mean(axis=0)
            self.sd = X.std(axis=0)
            self.sd[self.sd == 0] = 1.0
        return (X - self.mu) / self.sd

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogitMeta":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        Z = self._stdz(X, fit=True)
        n, d = Z.shape
        A = np.column_stack([np.ones(n), Z])   # 截距列
        w = np.zeros(d + 1)
        for _ in range(self.n_iter):
            p = _sigmoid(A @ w)
            grad = A.T @ (p - y) / n
            grad[1:] += self.l2 * w[1:] / n     # L2 不正则截距
            w -= self.lr * grad
        self.w = w
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        Z = (X - self.mu) / self.sd
        A = np.column_stack([np.ones(len(Z)), Z])
        return _sigmoid(A @ self.w)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


# ----------------------------- 评估 -----------------------------

def auc(y: np.ndarray, p: np.ndarray) -> float:
    """Mann-Whitney 排名 AUC。y∈{0,1}。退化(单类)返回 nan。"""
    y = np.asarray(y).ravel()
    p = np.asarray(p).ravel()
    pos = p[y == 1]
    neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # 排名法:所有正样本秩之和 → U 统计
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p), dtype=float)
    ranks[order] = np.arange(1, len(p) + 1)
    # 处理并列:同值取平均秩
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    csum = np.cumsum(counts)
    start = csum - counts
    avg = (start + csum + 1) / 2.0
    ranks = avg[inv]
    r_pos = ranks[y == 1].sum()
    n_pos, n_neg = len(pos), len(neg)
    u = r_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


# ----------------------------- Purged K 折 -----------------------------

def purged_kfold(t_event: np.ndarray, horizon: float, k: int = 5, embargo: float = 0.0):
    """时序 purged + embargo K 折(LdP）。t_event:各样本事件时间(同序,升序最佳);
    horizon:标签窗口长度(与 t_event 同单位)。返回 [(train_idx, test_idx), ...]。

    purge:训练样本的标签窗口 [t, t+horizon] 与测试窗口重叠则剔除;embargo:测试块后再禁一段。"""
    t = np.asarray(t_event, dtype=float)
    n = len(t)
    idx = np.arange(n)
    folds = np.array_split(idx, k)
    out = []
    for f in folds:
        if len(f) == 0:
            continue
        test = f
        t0, t1 = t[test].min(), t[test].max() + horizon
        emb = embargo
        # 训练 = 标签窗口不与 [t0, t1+emb] 重叠的样本
        train = np.array([i for i in idx if i not in set(test.tolist())
                          and not (t[i] + horizon >= t0 and t[i] <= t1 + emb)], dtype=int)
        out.append((train, test))
    return out


def cv_auc(X: np.ndarray, y: np.ndarray, t_event: np.ndarray, horizon: float,
           k: int = 5, embargo: float = 0.0, **logit_kw) -> dict:
    """purged CV:每折训练 LogitMeta、在测试折出概率,聚合 OOS AUC。返回 {oos_auc, fold_aucs, oos_p}。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    oos_p = np.full(len(y), np.nan)
    fold_aucs = []
    for train, test in purged_kfold(t_event, horizon, k, embargo):
        if len(train) < 10 or len(np.unique(y[train])) < 2:
            continue
        m = LogitMeta(**logit_kw).fit(X[train], y[train])
        p = m.predict_proba(X[test])
        oos_p[test] = p
        fold_aucs.append(auc(y[test], p))
    mask = ~np.isnan(oos_p)
    return {
        "oos_auc": auc(y[mask], oos_p[mask]) if mask.sum() > 0 else float("nan"),
        "fold_aucs": [float(a) for a in fold_aucs if np.isfinite(a)],
        "n_scored": int(mask.sum()),
        "oos_p": oos_p,
    }
