"""价值因子(需价格)—— LIS L-2 价值腿(见 docs/long-term-investment-system.md)。

价值因子依赖市值/企业价值,故必须 join 行情。PIT 纪律:
  - 基本面用 filed<=as_of(edgar_fundamentals 已保证);
  - 价格用 as_of 当日或之前最近一个交易日的**原始收盘**(非复权:市值=原价×当时在外股数)。

符号统一为"越大=越便宜=预期收益越高"(便于与质量腿合成)。来源见
research/long-term/value-investing-frameworks.md / shareholder-yield-buybacks.md / dcf-intrinsic-value-automation.md。

纯函数,可离线单测(price_asof 吃列式 bars dict)。
"""
from __future__ import annotations

from datetime import date


def _num(d: dict, k: str):
    v = d.get(k)
    return v if isinstance(v, (int, float)) else None


def price_asof(bars: dict, as_of: str) -> float | None:
    """列式 bars(data.load():{'ts':[...],'close':[...]})中,as_of 当日或之前最近交易日的原始收盘。"""
    ts, close = bars.get("ts"), bars.get("close")
    if not ts or not close:
        return None
    try:
        cutoff = int(__import__("calendar").timegm(date.fromisoformat(as_of).timetuple())) + 86399
    except ValueError:
        return None
    best = None
    for t, c in zip(ts, close):
        if t <= cutoff and c and c > 0:
            best = c  # ts 升序,最后一个 <=cutoff 即目标
    return best


def market_cap(lines: dict, price: float | None) -> float | None:
    sh = _num(lines, "shares")
    if price is None or sh is None or price <= 0 or sh <= 0:
        return None
    return price * sh


def enterprise_value(lines: dict, mcap: float | None) -> float | None:
    if mcap is None or mcap <= 0:
        return None
    debt = (_num(lines, "lt_debt") or 0) + (_num(lines, "debt_current") or 0)
    cash = _num(lines, "cash") or 0
    ev = mcap + debt - cash
    return ev if ev > 0 else None


def value_factors(lines: dict, price: float | None) -> dict:
    """计算价值腿因子(越大越便宜)。缺价格/分母非法 → 该项 None。"""
    mcap = market_cap(lines, price)
    ev = enterprise_value(lines, mcap)
    ni = _num(lines, "net_income")
    ebit = _num(lines, "operating_income")
    eq = _num(lines, "equity")
    div = _num(lines, "dividends_paid") or 0
    bb = _num(lines, "buybacks") or 0
    iss = _num(lines, "stock_issued") or 0
    cfo, capex = _num(lines, "cfo"), _num(lines, "capex")
    fcf = (cfo - abs(capex)) if cfo is not None and capex is not None else None

    out: dict = {"market_cap": mcap, "enterprise_value": ev}
    out["earnings_yield"] = (ni / mcap) if ni is not None and mcap else None       # E/P
    out["ebit_ev"] = (ebit / ev) if ebit is not None and ev else None              # EBIT/EV(Magic Formula 腿)
    out["fcf_ev"] = (fcf / ev) if fcf is not None and ev else None                 # FCF/EV
    out["book_to_price"] = (eq / mcap) if eq is not None and mcap else None         # B/P
    # 净股东收益(Net Payout Yield = 股息+回购−增发)/市值;股本法吸收 SBC 见研究报告
    out["shareholder_yield"] = ((div + bb - iss) / mcap) if mcap else None
    return out


# 价值腿因子方向(全部 +1:越大越便宜越好)
VALUE_FACTORS = {
    "earnings_yield": +1,
    "ebit_ev": +1,
    "fcf_ev": +1,
    "book_to_price": +1,
    "shareholder_yield": +1,
}
