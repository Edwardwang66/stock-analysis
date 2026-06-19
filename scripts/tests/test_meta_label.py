"""meta_label 单测:逻辑回归学习 / AUC 正确性 / purged K 折去重叠 / cv_auc。

直接 python 运行(需 numpy)。
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backtest"))

from meta_label import LogitMeta, auc, cv_auc, purged_kfold  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


rng = np.random.default_rng(0)

# ---- AUC 正确性 ----
print("== auc ==")
ok("完美分类 AUC=1", abs(auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.8, 0.9])) - 1.0) < 1e-9)
ok("完全反向 AUC=0", abs(auc(np.array([0, 0, 1, 1]), np.array([0.9, 0.8, 0.2, 0.1])) - 0.0) < 1e-9)
ok("随机≈0.5", abs(auc(np.array([0, 1, 0, 1]), np.array([0.5, 0.5, 0.5, 0.5])) - 0.5) < 1e-9)
ok("单类返回 nan", np.isnan(auc(np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3]))))

# ---- LogitMeta 学习可分信号 ----
print("== LogitMeta ==")
n = 400
X = rng.normal(size=(n, 3))
# 真关系:特征 0 正相关、特征 1 负相关
logit = 1.5 * X[:, 0] - 1.2 * X[:, 1] + 0.3 * rng.normal(size=n)
y = (logit > 0).astype(float)
m = LogitMeta(l2=0.1, lr=0.3, n_iter=3000).fit(X, y)
p = m.predict_proba(X)
ok("样本内 AUC 高(学到信号)", auc(y, p) > 0.9, auc(y, p))
ok("系数符号:特征0正", m.w[1] > 0)
ok("系数符号:特征1负", m.w[2] < 0)
ok("纯噪声特征系数小", abs(m.w[3]) < abs(m.w[1]))
ok("概率在[0,1]", p.min() >= 0 and p.max() <= 1)

# ---- purged_kfold 去重叠 ----
print("== purged_kfold ==")
t = np.arange(100, dtype=float)         # 事件时间 0..99
folds = purged_kfold(t, horizon=5, k=5, embargo=2)
ok("5 折", len(folds) == 5)
for train, test in folds:
    t0, t1 = t[test].min(), t[test].max() + 5
    # 训练样本标签窗口不得与测试窗口[t0,t1+embargo]重叠
    bad = [i for i in train if (t[i] + 5 >= t0 and t[i] <= t1 + 2)]
    ok(f"折[{int(t[test].min())}..{int(t[test].max())}] 无泄漏", len(bad) == 0, bad[:3])
    break
# 训练集不含测试索引
tr0, te0 = folds[2]
ok("train/test 不相交", len(set(tr0.tolist()) & set(te0.tolist())) == 0)

# ---- cv_auc:OOS 仍能识别真信号但低于样本内 ----
print("== cv_auc ==")
tev = np.arange(n, dtype=float)
res = cv_auc(X, y, tev, horizon=3, k=5, embargo=1, l2=0.1, lr=0.3, n_iter=1500)
ok("OOS AUC 显著>0.5", res["oos_auc"] > 0.8, res["oos_auc"])
ok("打分覆盖大部分样本", res["n_scored"] > n * 0.6)
ok("各折 AUC 都>0.5", all(a > 0.5 for a in res["fold_aucs"]))

# 纯噪声标签 → OOS AUC≈0.5(单次有抽样波动,故跨多次取均值更稳健)
noise_aucs = []
for seed in range(6):
    r = np.random.default_rng(100 + seed)
    Xn = r.normal(size=(n, 3))
    yn = r.integers(0, 2, size=n).astype(float)
    res2 = cv_auc(Xn, yn, np.arange(n, dtype=float), horizon=3, k=5, l2=1.0, lr=0.2, n_iter=600)
    if np.isfinite(res2["oos_auc"]):
        noise_aucs.append(res2["oos_auc"])
mean_noise = float(np.mean(noise_aucs))
ok("噪声标签多次 OOS AUC 均值≈0.5(诚实,不假装有信号)", abs(mean_noise - 0.5) < 0.06,
   f"mean={mean_noise:.3f} of {noise_aucs}")

print(f"\nmeta_label 单测全过:{PASS} 断言")
