"""factors_fundamental 单测:Altman Z'' / Piotroski F / Beneish M / 组合剔除闸。

直接 python 运行。用构造样本核对公式;阈值与分档按文献原值。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backtest"))

from factors_fundamental import (  # noqa: E402
    altman_z2,
    beneish_m,
    exclusion_screen,
    piotroski_f,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


# ---- Altman Z'' ----
print("== Altman Z'' ==")
# 一家稳健公司:WC/A=0.3, RE/A=0.5, EBIT/A=0.15, Eq/Liab=2.0
strong = {"assets": 1000, "current_assets": 500, "current_liabilities": 200,
          "retained_earnings": 500, "operating_income": 150, "equity": 600, "liabilities": 300}
z, zone = altman_z2(strong)
# 6.56*0.3 + 3.26*0.5 + 6.72*0.15 + 1.05*2.0 = 1.968+1.63+1.008+2.1 = 6.706
ok("Z'' 数值正确", abs(z - 6.706) < 1e-2, z)
ok("Z''>2.6 → safe", zone == "safe")

distress = {"assets": 1000, "current_assets": 150, "current_liabilities": 400,
            "retained_earnings": -300, "operating_income": -50, "equity": 50, "liabilities": 950}
z2, zone2 = altman_z2(distress)
ok("困境公司 → distress", zone2 == "distress", (z2, zone2))
ok("缺数据返回 None", altman_z2({"assets": 0})[0] is None)

# ---- Piotroski F ----
print("== Piotroski F ==")
prev = {"assets": 1000, "net_income": 50, "revenue": 800, "gross_profit": 300,
        "lt_debt": 300, "current_assets": 400, "current_liabilities": 300, "shares": 100}
cur = {"assets": 1100, "net_income": 90, "cfo": 120, "revenue": 950, "gross_profit": 400,
       "lt_debt": 250, "current_assets": 500, "current_liabilities": 300, "shares": 100}
f, det = piotroski_f(cur, prev)
# roa_pos1 cfo_pos1 d_roa(0.0818>0.05)1 accrual(120>90)1 d_lever(0.227<0.30)1
# d_liquid(1.667>1.333)1 no_dilution1 d_margin(0.421>0.375)1 d_turn(0.864>0.80)1 = 9
ok("健康公司 F=9", f == 9, (f, det))
ok("缺上期返回 None", piotroski_f(cur, None)[0] is None)

weak_prev = {"assets": 1000, "net_income": 100, "revenue": 900, "gross_profit": 400,
             "lt_debt": 100, "current_assets": 500, "current_liabilities": 200, "shares": 100}
weak_cur = {"assets": 1200, "net_income": -50, "cfo": -30, "revenue": 700, "gross_profit": 200,
            "lt_debt": 300, "current_assets": 300, "current_liabilities": 400, "shares": 130}
fw, _ = piotroski_f(weak_cur, weak_prev)
ok("恶化公司 F 低(≤1)", fw <= 1, fw)

# ---- Beneish M ----
print("== Beneish M ==")
# 干净公司:各项指数≈1、应计低 → M 应明显 < -1.78
clean_prev = {"revenue": 1000, "receivables": 100, "gross_profit": 400, "assets": 2000,
              "current_assets": 600, "ppe_net": 800, "dep_amort": 100, "sga": 150,
              "lt_debt": 400, "current_liabilities": 300}
clean_cur = {"revenue": 1050, "receivables": 105, "gross_profit": 420, "assets": 2050,
             "current_assets": 620, "ppe_net": 820, "dep_amort": 105, "sga": 158,
             "lt_debt": 400, "current_liabilities": 300, "net_income": 120, "cfo": 150}
m, flag = beneish_m(clean_cur, clean_prev)
ok("干净公司 M<-1.78(不触发)", m < -1.78 and flag is False, (m, flag))

# 操纵样本:应收暴增 + 毛利恶化 + 高应计(NI>>CFO)
manip_cur = {"revenue": 1400, "receivables": 400, "gross_profit": 350, "assets": 2050,
             "current_assets": 700, "ppe_net": 700, "dep_amort": 80, "sga": 120,
             "lt_debt": 600, "current_liabilities": 350, "net_income": 300, "cfo": 50}
mm, mflag = beneish_m(manip_cur, clean_prev)
ok("操纵样本 M 升高且触发", mm > -1.78 and mflag is True, (mm, mflag))
ok("缺数据 M 返回 None", beneish_m({"revenue": 1}, clean_prev)[0] is None)

# ---- 组合剔除闸(双确认纪律)----
print("== exclusion_screen ==")
sc_ok = exclusion_screen(clean_cur, clean_prev)
ok("干净公司不剔除", sc_ok["exclude"] is False, sc_ok["reasons"])

# manip_cur:M 红旗 + 高应计(NI=300,CFO=50,assets=2050 → 应计 0.122>0.10)→ 双确认硬剔除
sc_bad = exclusion_screen(manip_cur, clean_prev)
ok("操纵+高应计 → 硬剔除", sc_bad["exclude"] is True, sc_bad["reasons"])

# 高增长假阳性:M 红旗但盈余有现金背书(低应计)→ 仅软标记不剔除
growth_cur = {**manip_cur, "net_income": 300, "cfo": 320}  # CFO≈NI,应计为负
sc_growth = exclusion_screen(growth_cur, clean_prev)
ok("M 红旗但现金背书 → 不硬剔除", sc_growth["exclude"] is False, sc_growth)
ok("→ 落入软标记", any("假阳性" in s for s in sc_growth["flags"]), sc_growth["flags"])

# 破产仍硬剔除(单条件)
sc_distress = exclusion_screen(distress, clean_prev)
ok("破产风险 → 硬剔除", sc_distress["exclude"] is True, sc_distress["reasons"])

sc_exempt = exclusion_screen(distress, clean_prev, sector="Financials")
ok("金融业豁免", sc_exempt["exempt"] is True and sc_exempt["exclude"] is False)

print(f"\nfactors_fundamental 单测全过:{PASS} 断言")
