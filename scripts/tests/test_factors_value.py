"""factors_value 单测:price_asof / 市值 / EV / 价值因子。不触网。"""
import calendar
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backtest"))

from factors_value import (  # noqa: E402
    enterprise_value,
    market_cap,
    price_asof,
    value_factors,
)

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


def _ts(d):
    return calendar.timegm(date.fromisoformat(d).timetuple())


print("== price_asof ==")
bars = {"ts": [_ts("2024-06-25"), _ts("2024-06-26"), _ts("2024-06-27"), _ts("2024-07-01")],
        "close": [100.0, 101.0, 102.0, 105.0]}
ok("取 as_of 当日收盘", price_asof(bars, "2024-06-27") == 102.0)
ok("as_of 落周末→取之前最近", price_asof(bars, "2024-06-29") == 102.0)
ok("as_of 早于全部→None", price_asof(bars, "2024-06-01") is None)
ok("as_of 晚于全部→取最后", price_asof(bars, "2024-12-31") == 105.0)
ok("空 bars→None", price_asof({}, "2024-06-27") is None)

print("== market_cap / EV ==")
lines = {"shares": 1_000_000, "lt_debt": 200.0, "debt_current": 50.0, "cash": 100.0,
         "net_income": 50_000_000.0, "operating_income": 80_000_000.0, "equity": 300_000_000.0,
         "dividends_paid": 10_000_000.0, "buybacks": 20_000_000.0, "stock_issued": 5_000_000.0,
         "cfo": 90_000_000.0, "capex": 15_000_000.0}
mc = market_cap(lines, 100.0)
ok("市值=价×股数=1e8", mc == 100_000_000.0, mc)
ev = enterprise_value(lines, mc)
ok("EV=市值+债-现=1e8+250-100", ev == 100_000_000.0 + 250.0 - 100.0, ev)
ok("缺价格→市值 None", market_cap(lines, None) is None)
ok("负 EV(净现金巨多)→None", enterprise_value({"lt_debt": 0, "debt_current": 0, "cash": 2e8}, 1e8) is None)

print("== value_factors ==")
vf = value_factors(lines, 100.0)
ok("earnings_yield=ni/mcap=0.5", abs(vf["earnings_yield"] - 0.5) < 1e-9, vf["earnings_yield"])
ok("book_to_price=eq/mcap=3.0", abs(vf["book_to_price"] - 3.0) < 1e-9)
# shareholder_yield=(10+20-5)e6/1e8=0.25
ok("shareholder_yield=净回报/市值=0.25", abs(vf["shareholder_yield"] - 0.25) < 1e-9, vf["shareholder_yield"])
# fcf=(90-15)e6=75e6; ebit_ev=80e6/(~1e8); 仅验证正负与存在
ok("ebit_ev 存在且>0", vf["ebit_ev"] > 0)
ok("fcf_ev 存在且>0", vf["fcf_ev"] > 0)
ok("缺价格→因子 None", value_factors(lines, None)["earnings_yield"] is None)

print(f"\nfactors_value 单测全过:{PASS} 断言")
