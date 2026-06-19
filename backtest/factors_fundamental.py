"""基本面因子 + 下行保护剔除闸 —— LIS L-1/L-2(见 docs/long-term-investment-system.md)。

输入是 scripts/edgar_fundamentals.py 抽取的 PIT 线项 dict(lines:{revenue, assets, ...}),
全部为某财年快照,无未来函数(filed<=as_of)。两期因子额外吃上一财年 prev_lines。

两类输出:
  1) **质量/价值/安全因子**(连续值,进合成打分)—— 多见 ratios,这里补两期类。
  2) **剔除闸**(布尔/分档,下行保护)—— Altman Z''(破产)、Beneish M(盈余操纵)、Piotroski F(质量地板)。
     纪律(research/long-term/accruals-earnings-quality.md):这些是**剔除/降权规则,不是 alpha**;
     金融/REIT/公用事业豁免;阈值沿用文献原值,不在样本内调参。

诚实:M-Score 数据需求高(两期 + PP&E + SG&A + 应收),缺任一输入返回 None(=未知,不据缺失剔除)。
"""
from __future__ import annotations


def _num(d: dict, k: str):
    v = d.get(k)
    return v if isinstance(v, (int, float)) else None


# ============================ 剔除闸 1:Altman Z''(跨行业/新兴市场版)============================
# Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4(无销售项,适合非制造/跨行业)
# 区:>2.6 安全 / 1.1–2.6 灰区 / <1.1 困境。来源:Altman 1995 EM-score。
def altman_z2(lines: dict) -> tuple[float | None, str | None]:
    assets = _num(lines, "assets")
    ca, cl = _num(lines, "current_assets"), _num(lines, "current_liabilities")
    re = _num(lines, "retained_earnings")
    ebit = _num(lines, "operating_income")
    eq = _num(lines, "equity")
    liab = _num(lines, "liabilities")
    if not assets or assets <= 0 or liab is None or liab <= 0:
        return None, None
    if None in (ca, cl, re, ebit, eq):
        return None, None
    x1 = (ca - cl) / assets
    x2 = re / assets
    x3 = ebit / assets
    x4 = eq / liab
    z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    zone = "safe" if z > 2.6 else ("distress" if z < 1.1 else "grey")
    return round(z, 3), zone


# ============================ 剔除闸 2:Piotroski F-Score(0–9 质量地板)============================
# 9 项二元;高分=基本面改善。Piotroski 2000。需本期+上期。
def piotroski_f(cur: dict, prev: dict | None) -> tuple[int | None, dict]:
    if prev is None:
        return None, {}
    def r(d, k):
        return _num(d, k)
    a, ap = r(cur, "assets"), r(prev, "assets")
    ni, nip = r(cur, "net_income"), r(prev, "net_income")
    cfo = r(cur, "cfo")
    rev, revp = r(cur, "revenue"), r(prev, "revenue")
    gp, gpp = r(cur, "gross_profit"), r(prev, "gross_profit")
    ltd, ltdp = r(cur, "lt_debt"), r(prev, "lt_debt")
    ca, cl = r(cur, "current_assets"), r(cur, "current_liabilities")
    cap, clp = r(prev, "current_assets"), r(prev, "current_liabilities")
    sh, shp = r(cur, "shares"), r(prev, "shares")
    if None in (a, ap) or a <= 0 or ap <= 0:
        return None, {}
    pts, det = 0, {}
    roa = ni / a if ni is not None else None
    roap = nip / ap if nip is not None else None
    # 盈利(4)
    det["roa_pos"] = int(roa is not None and roa > 0); pts += det["roa_pos"]
    det["cfo_pos"] = int(cfo is not None and cfo > 0); pts += det["cfo_pos"]
    det["d_roa"] = int(roa is not None and roap is not None and roa > roap); pts += det["d_roa"]
    det["accrual"] = int(cfo is not None and ni is not None and cfo > ni); pts += det["accrual"]
    # 杠杆/流动性(3)
    det["d_lever"] = int(ltd is not None and ltdp is not None and (ltd / a) < (ltdp / ap)); pts += det["d_lever"]
    cr = (ca / cl) if ca is not None and cl else None
    crp = (cap / clp) if cap is not None and clp else None
    det["d_liquid"] = int(cr is not None and crp is not None and cr > crp); pts += det["d_liquid"]
    det["no_dilution"] = int(sh is not None and shp is not None and sh <= shp * 1.01); pts += det["no_dilution"]
    # 经营效率(2)
    gm = (gp / rev) if gp is not None and rev else None
    gmp = (gpp / revp) if gpp is not None and revp else None
    det["d_margin"] = int(gm is not None and gmp is not None and gm > gmp); pts += det["d_margin"]
    at = (rev / a) if rev is not None else None
    atp = (revp / ap) if revp is not None else None
    det["d_turn"] = int(at is not None and atp is not None and at > atp); pts += det["d_turn"]
    return pts, det


# ============================ 剔除闸 3:Beneish M-Score(盈余操纵)============================
# M = -4.84 +0.92·DSRI +0.528·GMI +0.404·AQI +0.892·SGI +0.115·DEPI
#       -0.172·SGAI +4.679·TATA -0.327·LVGI
# M > -1.78 → 疑似操纵(Beneish 1999)。需两期 + 应收 + PP&E + SG&A。
def beneish_m(cur: dict, prev: dict | None) -> tuple[float | None, bool | None]:
    if prev is None:
        return None, None
    def r(d, k):
        return _num(d, k)
    rev, revp = r(cur, "revenue"), r(prev, "revenue")
    rec, recp = r(cur, "receivables"), r(prev, "receivables")
    gp, gpp = r(cur, "gross_profit"), r(prev, "gross_profit")
    a, ap = r(cur, "assets"), r(prev, "assets")
    ca, cap = r(cur, "current_assets"), r(prev, "current_assets")
    ppe, ppep = r(cur, "ppe_net"), r(prev, "ppe_net")
    dep, depp = r(cur, "dep_amort"), r(prev, "dep_amort")
    sga, sgap = r(cur, "sga"), r(prev, "sga")
    ni, cfo = r(cur, "net_income"), r(cur, "cfo")
    ltd, ltdp = r(cur, "lt_debt"), r(prev, "lt_debt")
    cl, clp = r(cur, "current_liabilities"), r(prev, "current_liabilities")
    need = [rev, revp, rec, recp, gp, gpp, a, ap, ca, cap, ppe, ppep, dep, depp, sga, sgap, ni, cfo]
    if any(v is None for v in need) or 0 in (rev, revp, a, ap):
        return None, None
    try:
        dsri = (rec / rev) / (recp / revp)
        gmi = (gpp / revp) / (gp / rev)
        aqi_c = 1 - (ca + ppe) / a
        aqi_p = 1 - (cap + ppep) / ap
        aqi = aqi_c / aqi_p if aqi_p else 1.0
        sgi = rev / revp
        depi = (depp / (depp + ppep)) / (dep / (dep + ppe))
        sgai = (sga / rev) / (sgap / revp)
        tata = (ni - cfo) / a
        lev_c = ((ltd or 0) + (cl or 0)) / a
        lev_p = ((ltdp or 0) + (clp or 0)) / ap
        lvgi = lev_c / lev_p if lev_p else 1.0
    except ZeroDivisionError:
        return None, None
    m = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
    return round(m, 3), (m > -1.78)


# ============================ 组合剔除闸 ============================
# 金融/REIT/公用事业:这些指标不适用,豁免(默认按 sector 字符串判断)。
EXEMPT_SECTORS = {"Financials", "Financial Services", "Real Estate", "Utilities", "金融", "房地产", "公用事业"}


# 应计阈值:NI 超过 CFO 达资产的此比例 → 盈余未被现金背书(双确认用)。
ACCRUAL_HI = 0.10


def _accruals_to_assets(cur: dict) -> float | None:
    ni, cfo, a = _num(cur, "net_income"), _num(cur, "cfo"), _num(cur, "assets")
    if ni is None or cfo is None or not a or a <= 0:
        return None
    return (ni - cfo) / a


def exclusion_screen(cur: dict, prev: dict | None, sector: str | None = None) -> dict:
    """汇总三闸 → 硬剔除(exclude)/ 软标记(flags)。返回 {exclude, reasons, flags, scores}。

    纪律(research/long-term/accruals-earnings-quality.md):
      - **硬剔除**:破产风险(Altman distress)或 **双确认操纵**(Beneish M 红旗 *且* 高应计)。
      - **软标记**(不自动剔除,供复核/降权):单独 M 红旗、F≤1、灰区。
    为什么双确认:M-Score 对高增长股有系统性假阳性(SGI 项)——如 NVDA 爆发增长会触发 M,
      但其盈余被真实经营现金背书(低应计),不应剔除。要求"红旗 + 盈余无现金背书"才硬杀。
    缺数据=不剔除(未知不等于坏)。"""
    if sector and sector in EXEMPT_SECTORS:
        return {"exclude": False, "exempt": True, "reasons": [], "flags": [], "scores": {}}
    z, zone = altman_z2(cur)
    f, _f_det = piotroski_f(cur, prev)
    m, m_flag = beneish_m(cur, prev)
    accr = _accruals_to_assets(cur)
    reasons, flags = [], []
    # 硬剔除
    if zone == "distress":
        reasons.append(f"Altman Z''={z}<1.1 破产风险")
    if m_flag is True and accr is not None and accr > ACCRUAL_HI:
        reasons.append(f"Beneish M={m}>-1.78 且高应计({accr:.2f}>{ACCRUAL_HI}):盈余无现金背书")
    # 软标记
    if m_flag is True and not (accr is not None and accr > ACCRUAL_HI):
        flags.append(f"Beneish M={m} 红旗但盈余有现金背书(疑高增长假阳性),仅标记")
    if f is not None and f <= 1:
        flags.append(f"Piotroski F={f}≤1 基本面弱")
    if zone == "grey":
        flags.append(f"Altman Z''={z} 灰区")
    return {
        "exclude": len(reasons) > 0,
        "exempt": False,
        "reasons": reasons,
        "flags": flags,
        "scores": {"altman_z2": z, "altman_zone": zone, "piotroski_f": f,
                   "beneish_m": m, "beneish_flag": m_flag, "accruals_to_assets": accr},
    }
