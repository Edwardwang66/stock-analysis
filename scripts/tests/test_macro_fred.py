"""macro_fred 纯评分单测:分项映射 / Sahm / 拨盘加权 / regime 分档 / 缺失归一。

直接 python 运行;不触网。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from macro_fred import (  # noqa: E402
    compute_dial,
    sahm_gap,
    score_credit,
    score_curve,
    score_fci,
    score_labor,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


print("== 分项评分(risk_on=1 好)==")
ok("低 OAS(3.0%)→ 高分", score_credit(3.0) == 1.0)
ok("高 OAS(7%)→ 低分", score_credit(7.0) == 0.0)
ok("OAS 单调:利差越宽分越低", score_credit(4.0) > score_credit(5.5))

ok("陡曲线(1.5)→ 1.0", score_curve(1.5) == 1.0)
ok("深倒挂(-1)→ 0.0", score_curve(-1.0) == 0.0)
ok("倒挂比正常分低", score_curve(-0.3) < score_curve(0.8))

ok("宽松 NFCI(-0.8)→ 1.0", score_fci(-0.8) == 1.0)
ok("收紧 NFCI(0.8)→ 0.0", score_fci(0.8) == 0.0)

print("== Sahm ==")
# 12 月失业率,最低 3.5,近 3 月均值 4.2 → gap 0.7 ≥0.5 触发
hist = [3.5, 3.5, 3.6, 3.7, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3]
g = sahm_gap(hist)
ok("Sahm gap = 4.2-3.5 = 0.7", abs(g - 0.7) < 1e-9, g)
ok("Sahm 0.7 → labor 低分", score_labor(g) == 0.0)
flat = [3.5] * 12
ok("平稳失业 → gap 0 → 高分", score_labor(sahm_gap(flat)) == 1.0)
ok("不足 12 月 → None", sahm_gap([3.5] * 6) is None)
ok("labor None 透传", score_labor(None) is None)

print("== compute_dial ==")
# 全好:低 OAS、陡曲线、宽松 FCI、平稳就业 → dial≈1, risk_on
good = compute_dial(3.0, 1.5, -0.8, [3.5] * 12)
ok("全好 → risk_dial≈1", good["risk_dial"] > 0.95, good["risk_dial"])
ok("全好 → regime risk_on", good["regime"] == "risk_on")
# 全差 → dial≈0, risk_off
bad = compute_dial(7.0, -1.0, 0.8, [3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 4.0, 4.2, 4.4])
ok("全差 → risk_dial 低", bad["risk_dial"] < 0.15, bad["risk_dial"])
ok("全差 → regime risk_off", bad["regime"] == "risk_off")
# 缺失分项:只给 credit,权重归一仍可算
partial = compute_dial(3.0, None, None, [])
ok("仅 credit 可得 → 仍出 dial", partial["risk_dial"] == 1.0, partial)
ok("仅 credit → components 只 1 项", set(partial["components"]) == {"credit"})
ok("全缺 → None", compute_dial(None, None, None, [])["risk_dial"] is None)

# 权重:credit 权重最大,翻转 credit 对 dial 影响应大于翻转 labor
base = compute_dial(5.0, 0.5, 0.0, [3.5] * 12)
flip_credit = compute_dial(3.0, 0.5, 0.0, [3.5] * 12)
flip_labor = compute_dial(5.0, 0.5, 0.0, [3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.5, 3.8, 4.0, 4.2])
ok("credit 权重 > labor 权重(对 dial 影响)",
   abs(flip_credit["risk_dial"] - base["risk_dial"]) > abs(flip_labor["risk_dial"] - base["risk_dial"]))

print(f"\nmacro_fred 单测全过:{PASS} 断言")
