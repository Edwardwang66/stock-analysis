"""edgar_fundamentals 纯逻辑单测:PIT 切片 / 防重述 / 年度过滤 / 派生比率。

直接 python 运行;不触网(用构造的 companyfacts 夹具)。与 chan/validate 单测同风格。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from edgar_fundamentals import (  # noqa: E402
    _annual,
    derive_ratios,
    extract_pit_fundamentals,
    latest_fact,
    pit_line,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


# ---- _annual:年度区间识别 ----
print("== _annual ==")
ok("年度区间 True", _annual({"start": "2023-01-01", "end": "2023-12-31"}))
ok("季度区间 False", not _annual({"start": "2023-01-01", "end": "2023-03-31"}))
ok("时点量(无 start)True", _annual({"end": "2023-12-31"}))

# ---- latest_fact:PIT + 防重述 ----
print("== latest_fact(时点量)==")
# Assets:两期;早期事实有"首报"和后来 10-K 里的"比较列重述",规则应取首报。
assets_units = [
    {"end": "2022-12-31", "val": 100, "filed": "2023-02-15"},                    # FY22 首报
    {"end": "2022-12-31", "val": 105, "filed": "2024-02-15"},                    # FY23 年报里的比较列(重述)
    {"end": "2023-12-31", "val": 120, "filed": "2024-02-15"},                    # FY23 首报
    {"end": "2024-12-31", "val": 140, "filed": "2025-02-15"},                    # 未来(as_of 之后)
]
f = latest_fact(assets_units, "2024-06-30", flow=False)
ok("PIT 取报告期最新(FY23=120)", f["val"] == 120, f)
ok("剔除 as_of 之后的 FY24", f["end"] == "2023-12-31")

f0 = latest_fact(assets_units, "2023-06-30", flow=False)
ok("早 as_of 只见 FY22 首报=100", f0["val"] == 100, f0)

# 防重述:as_of=2024-06-30 时 FY22 这一期应取首报 100 而非重述 105
fy22 = latest_fact([u for u in assets_units if u["end"] == "2022-12-31"], "2024-06-30", flow=False)
ok("同报告期取首次申报(100 非 105)", fy22["val"] == 100, fy22)

print("== latest_fact(时段量:只认年度)==")
rev_units = [
    {"start": "2023-01-01", "end": "2023-03-31", "val": 25, "filed": "2023-04-30"},   # Q1
    {"start": "2023-01-01", "end": "2023-12-31", "val": 110, "filed": "2024-02-15"},  # FY23 年度
    {"start": "2022-01-01", "end": "2022-12-31", "val": 90, "filed": "2023-02-15"},   # FY22 年度
]
fr = latest_fact(rev_units, "2024-06-30", flow=True)
ok("时段量取最新年度(FY23=110)", fr["val"] == 110, fr)
ok("季度区间被过滤", fr["end"] == "2023-12-31")

# ---- pit_line / extract:回退链 + gross_profit 兜底 ----
print("== pit_line / extract_pit_fundamentals ==")
facts = {"facts": {
    "us-gaap": {
        "Assets": {"units": {"USD": [
            {"end": "2023-12-31", "val": 1000, "filed": "2024-02-15"}]}},
        "Revenues": {"units": {"USD": [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 500, "filed": "2024-02-15"}]}},
        "CostOfRevenue": {"units": {"USD": [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 300, "filed": "2024-02-15"}]}},
        "NetIncomeLoss": {"units": {"USD": [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 80, "filed": "2024-02-15"}]}},
        "StockholdersEquity": {"units": {"USD": [
            {"end": "2023-12-31", "val": 400, "filed": "2024-02-15"}]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            {"start": "2023-01-01", "end": "2023-12-31", "val": 95, "filed": "2024-02-15"}]}},
    },
}}
v, filed = pit_line(facts, "revenue", "2024-06-30")
ok("回退链命中 Revenues=500", v == 500)
ex = extract_pit_fundamentals(facts, "2024-06-30")
ok("gross_profit 兜底=rev-cogs=200", ex["gross_profit"] == 200, ex.get("gross_profit"))
ok("asof_fundamentals=最后申报日", ex["asof_fundamentals"] == "2024-02-15")

# ---- derive_ratios ----
print("== derive_ratios ==")
r = derive_ratios(ex)
ok("gross_profitability=gp/assets=0.2", abs(r["gross_profitability"] - 0.2) < 1e-9, r["gross_profitability"])
ok("roe=ni/eq=0.2", abs(r["roe"] - 0.2) < 1e-9, r["roe"])
ok("accruals=(ni-cfo)/assets=(80-95)/1000", abs(r["accruals_to_assets"] - (-15 / 1000)) < 1e-9)
ok("asset_turnover=rev/assets=0.5", abs(r["asset_turnover"] - 0.5) < 1e-9)

print(f"\nedgar_fundamentals 单测全过:{PASS} 断言")
