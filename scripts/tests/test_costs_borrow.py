"""costs 借券费/做空可行性单测:borrow_rate_proxy / shortable_mask / borrow_cost_daily / borrow_drag_annual。

直接 python 运行(需 numpy)。
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backtest"))

from costs import (  # noqa: E402
    BORROW_TIERS,
    borrow_cost_daily,
    borrow_drag_annual,
    borrow_rate_proxy,
    shortable_mask,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


print("== borrow_rate_proxy ==")
adv = np.array([100e6, 20e6, 5e6, 1e6, 0.3e6])  # 大→微
rate = borrow_rate_proxy(adv)
ok("大盘 $100M → 0.3%", abs(rate[0] - 0.003) < 1e-9, rate[0])
ok("$20M → 1%", abs(rate[1] - 0.010) < 1e-9)
ok("$5M → 3%", abs(rate[2] - 0.030) < 1e-9)
ok("$1M → 8%", abs(rate[3] - 0.080) < 1e-9)
ok("微盘 $0.3M → nan(不可做空)", np.isnan(rate[4]))
ok("借券率单调:越冷门越贵", rate[0] < rate[1] < rate[2] < rate[3])

print("== shortable_mask ==")
m = shortable_mask(adv)
ok("前四可做空", m[:4].all())
ok("微盘不可做空", not m[4])

print("== borrow_cost_daily ==")
# 两只各 |w|=0.5,大盘 0.3% + 小盘 8% → 年化 (0.5*0.003+0.5*0.08)=0.0415;日=/252
w = np.array([0.5, 0.5])
adv2 = np.array([100e6, 1e6])
daily = borrow_cost_daily(w, adv2)
ok("日借券成本=年化/252", abs(daily - (0.5 * 0.003 + 0.5 * 0.080) / 252) < 1e-12, daily)
# 不可做空者按最贵档惩罚
daily_micro = borrow_cost_daily(np.array([1.0]), np.array([0.3e6]))
ok("不可做空按最贵档计", abs(daily_micro - BORROW_TIERS[-1][1] / 252) < 1e-12, daily_micro)

print("== borrow_drag_annual ==")
# 空头簿:大盘 -0.4(GC)、小盘 -0.3($1M,8%)、微盘 -0.3(不可做空)
sw = np.array([-0.4, -0.3, -0.3])
advs = np.array([200e6, 1e6, 0.2e6])
d = borrow_drag_annual(sw, advs)
ok("n_short=3", d["n_short"] == 3)
ok("n_unshortable=1(微盘)", d["n_unshortable"] == 1)
# 不可做空权重占比 = 0.3/1.0 = 0.3
ok("不可做空权重占比=0.3", abs(d["unshortable_frac"] - 0.3) < 1e-9, d["unshortable_frac"])
# 年化 = 0.4*0.003 + 0.3*0.08 + 0.3*0.08(微盘按最贵) = 0.0012+0.024+0.024=0.0492
ok("年化借券成本", abs(d["ann_borrow_cost"] - (0.4 * 0.003 + 0.3 * 0.08 + 0.3 * 0.08)) < 1e-9, d["ann_borrow_cost"])
ok("空簿为空 → 0", borrow_drag_annual(np.zeros(3), advs)["ann_borrow_cost"] == 0.0)
# 小盘空头簿借券拖累应远高于大盘
big = borrow_drag_annual(np.array([-0.5, -0.5]), np.array([200e6, 100e6]))
small = borrow_drag_annual(np.array([-0.5, -0.5]), np.array([3e6, 1e6]))
ok("小盘借券拖累 >> 大盘", small["ann_borrow_cost"] > 5 * big["ann_borrow_cost"],
   (small["ann_borrow_cost"], big["ann_borrow_cost"]))

print(f"\ncosts(借券)单测全过:{PASS} 断言")
