"""longterm_screen 纯逻辑单测:横截面 z 合成 / 排序 / 剔除沉底 / 缺失处理。

直接 python 运行;不触网。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from longterm_screen import score_panel, xs_zscore  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


# ---- xs_zscore ----
print("== xs_zscore ==")
z = xs_zscore([1.0, 2.0, 3.0, 4.0, 5.0], +1)
ok("均值居中(中位=0)", abs(z[2]) < 1e-9, z)
ok("方向 + 单调升", z[0] < z[4])
zneg = xs_zscore([1.0, 2.0, 3.0, 4.0, 5.0], -1)
ok("方向 - 反号", zneg[0] > zneg[4])
ok("截尾 ±3", all(-3.0 <= v <= 3.0 for v in z))
ok("缺失保持 None", xs_zscore([1.0, None, 3.0, 5.0, 7.0], +1)[1] is None)
ok("样本<3 全 None", xs_zscore([1.0, 2.0], +1) == [None, None])

# ---- score_panel ----
print("== score_panel ==")
# 三名:A 全面高、B 中、C 低且被剔除
panel = [
    {"ticker": "A", "gross_profitability": 0.5, "cash_op_to_assets": 0.3, "roic": 0.4,
     "roe": 0.3, "net_margin": 0.25, "accruals_to_assets": -0.04, "piotroski_f": 8, "exclude": False},
    {"ticker": "B", "gross_profitability": 0.3, "cash_op_to_assets": 0.18, "roic": 0.2,
     "roe": 0.18, "net_margin": 0.15, "accruals_to_assets": 0.0, "piotroski_f": 6, "exclude": False},
    {"ticker": "C", "gross_profitability": 0.1, "cash_op_to_assets": 0.05, "roic": 0.05,
     "roe": 0.05, "net_margin": 0.05, "accruals_to_assets": 0.2, "piotroski_f": 2, "exclude": False},
    {"ticker": "D", "gross_profitability": 0.4, "cash_op_to_assets": 0.25, "roic": 0.3,
     "roe": 0.25, "net_margin": 0.2, "accruals_to_assets": -0.02, "piotroski_f": 7, "exclude": True,
     "reasons": ["破产风险"]},
]
ranked = score_panel(panel)
by_t = {r["ticker"]: r for r in ranked}
ok("A 质量分最高", by_t["A"]["quality_score"] > by_t["B"]["quality_score"] > by_t["C"]["quality_score"])
ok("A 排第 1", by_t["A"]["rank"] == 1)
ok("被剔除的 D 沉底(rank 最大)", by_t["D"]["rank"] == len(ranked))
ok("D 仍算出分(只是沉底)", by_t["D"]["quality_score"] is not None)
ok("z 分解齐全", set(by_t["A"]["z"]) == set(
    ["gross_profitability", "cash_op_to_assets", "roic", "roe", "net_margin",
     "accruals_to_assets", "piotroski_f"]))

# 缺失因子(<2 可用)→ 无分
sparse = [
    {"ticker": "X", "gross_profitability": 0.3, "exclude": False},
    {"ticker": "Y", "roic": 0.2, "exclude": False},
    {"ticker": "Z", "roe": 0.1, "exclude": False},
]
rs = score_panel(sparse)
ok("单因子名 → quality_score None", all(r["quality_score"] is None for r in rs))

print(f"\nlongterm_screen 单测全过:{PASS} 断言")
