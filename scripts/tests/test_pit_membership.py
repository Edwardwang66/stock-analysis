"""pit_membership PIT 过滤逻辑单测:membership_asof / ever_in_index / make_pit_filter。

直接 python 运行;不触网(构造 db 夹具)。核心验证:消前视性成员偏差 + NDX-only 不误杀。
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backtest"))

from pit_membership import ever_in_index, make_pit_filter, membership_asof  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


# AAA 于 2020-06-01 加入(替下 CCC);BBB 一直在;DDD 从未在 S&P500(NDX-only)
db = {
    "current": {"AAA": "Tech", "BBB": "Fin"},
    "changes": [{"date": "2020-06-01", "added": "AAA", "removed": "CCC"}],
}

print("== ever_in_index ==")
ever = ever_in_index(db)
ok("曾在指数 = {AAA,BBB,CCC}", ever == {"AAA", "BBB", "CCC"}, ever)
ok("DDD 不在 ever", "DDD" not in ever)

print("== membership_asof ==")
m2019 = membership_asof("2019-01-01", db)
ok("2019:AAA 还没加入", "AAA" not in m2019)
ok("2019:CCC 仍在", "CCC" in m2019)
ok("2019:BBB 在", "BBB" in m2019)
m2021 = membership_asof("2021-01-01", db)
ok("2021:AAA 已在", "AAA" in m2021)
ok("2021:CCC 已移除", "CCC" not in m2021)

print("== make_pit_filter ==")
allowed = make_pit_filter(db)
# 前视性偏差:AAA 在加入前(2019)不应入选
ok("AAA@2019 → 不允许(消前视)", allowed("AAA", "2019-01-01") is False)
ok("AAA@2021 → 允许", allowed("AAA", "2021-01-01") is True)
# 退出的 CCC:在其仍是成分时允许,移除后不允许
ok("CCC@2019 → 允许(当时是成分)", allowed("CCC", "2019-01-01") is True)
ok("CCC@2021 → 不允许(已移除)", allowed("CCC", "2021-01-01") is False)
# NDX-only 的 DDD:无变更史 → 始终允许(诚实不误杀)
ok("DDD@2019 → 允许(无 S&P500 史不过滤)", allowed("DDD", "2019-01-01") is True)
ok("DDD@2021 → 允许", allowed("DDD", "2021-01-01") is True)
# 归一化:带点/横杠的 ticker 也能匹配
db2 = {"current": {"BRK.B": "Fin"}, "changes": []}
allow2 = make_pit_filter(db2)
ok("BRK-B 匹配 BRK.B(归一化)", allow2("BRK-B", "2021-01-01") is True)

print(f"\npit_membership 单测全过:{PASS} 断言")
