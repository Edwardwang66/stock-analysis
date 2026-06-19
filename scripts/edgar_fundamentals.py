#!/usr/bin/env python3
"""EDGAR XBRL → 点时(PIT)基本面面板。LIS v0.1 的 L0 数据底座(见 docs/long-term-investment-system.md)。

为什么:EDGAR 是唯一真·免费·PIT·可重分发的基本面源(见 research/long-term/free-fundamental-data-landscape.md)。
每条 XBRL 事实自带 `filed` 申报日 → 用 `filed <= as_of` 切片即可还原"当时能看到什么",避免重述泄漏/前视。

设计:
  - **纯函数**(extract_pit_fundamentals / latest_fact / 派生比率)与网络抓取分离,纯逻辑可离线单测。
  - 仅标准库(urllib/json),复用 funds_13f.py 的 SEC User-Agent + ≤10 req/s 惯例。
  - 输出 feed/longterm/fundamentals.json:{as_of, universe, rows:[{ticker, cik, asof_fundamentals, ...线项}]}。

PIT 纪律(research/long-term/sec-edgar-xbrl-fundamentals.md):
  - 只取 `filed <= as_of` 的事实;同一报告期(end)取**最早 filed**(首次申报,防重述)。
  - 损益/现金流为时段量(有 start),只认年度区间(end-start ≈ 365d);资产负债为时点量(无 start)。
  - 比较列泄漏:晚 filing 里携带的旧 end 事实(常无 frame 标记)会被"最早 filed"规则自然滤掉。

用法:
  python scripts/edgar_fundamentals.py --tickers AAPL,MSFT --as-of 2024-06-30
  python scripts/edgar_fundamentals.py --universe scripts/ndx100.json --as-of 2024-06-30
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feed" / "longterm" / "fundamentals.json"
UA = {"User-Agent": "stock-analysis-dashboard admin@example.com"}  # SEC 要求带可联系 UA
RATE_S = 0.12  # ≤10 req/s

# us-gaap 标签回退链:不同公司/年代标签碎片化,按优先级取第一个存在的。
# 方向:全部为 USD 金额(shares 例外)。来源见 sec-edgar-xbrl / quality-moat / accruals 报告字段表。
TAGS: dict[str, list[str]] = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "lt_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "debt_current": ["DebtCurrent", "LongTermDebtCurrent"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "dep_amort": ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
                  "DepreciationAndAmortization"],
    "interest_expense": ["InterestExpense", "InterestAndDebtExpense"],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "stock_issued": ["ProceedsFromIssuanceOfCommonStock"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "ebit": ["OperatingIncomeLoss"],  # EBIT 近似 = 经营利润
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "ppe_net": ["PropertyPlantAndEquipmentNet"],
    "sga": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
}
# dei 命名空间(在外股数)
DEI_TAGS = {"shares": ["EntityCommonStockSharesOutstanding"]}

# 时段量(损益/现金流,有 start);其余为时点量(资产负债表)。
FLOW_KEYS = {"revenue", "cogs", "gross_profit", "operating_income", "net_income", "cfo",
             "capex", "dep_amort", "interest_expense", "dividends_paid", "buybacks",
             "stock_issued", "ebit", "sga"}


# ----------------------------- 网络抓取(薄封装)-----------------------------

def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def load_ticker_cik_map() -> dict[str, str]:
    """company_tickers.json:ticker(大写)→ 补零 10 位 CIK。"""
    data = json.loads(_get("https://www.sec.gov/files/company_tickers.json"))
    out = {}
    for row in data.values():
        out[row["ticker"].upper()] = f"{int(row['cik_str']):010d}"
    return out


def fetch_companyfacts(cik: str) -> dict:
    return json.loads(_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"))


# ----------------------------- 纯逻辑(可离线单测)-----------------------------

def _annual(fact: dict) -> bool:
    """时段量是否为年度区间(end-start ≈ 350~380 天)。无 start 的时点量直接 True。"""
    s, e = fact.get("start"), fact.get("end")
    if not s or not e:
        return True
    try:
        from datetime import date
        d = (date.fromisoformat(e) - date.fromisoformat(s)).days
    except ValueError:
        return False
    return 350 <= d <= 380


def latest_fact(units: list[dict], as_of: str, flow: bool) -> dict | None:
    """PIT 取值:filed<=as_of 中,选报告期最新(end 最大)的事实;
    同 end 取最早 filed(首次申报,防重述);时段量只认年度区间。"""
    cands = [f for f in units if f.get("filed") and f["filed"] <= as_of and f.get("end")]
    if flow:
        cands = [f for f in cands if _annual(f)]
    if not cands:
        return None
    max_end = max(f["end"] for f in cands)               # 报告期最新
    same_end = [f for f in cands if f["end"] == max_end]
    same_end.sort(key=lambda f: f["filed"])              # 同报告期取首次申报(防重述)
    return same_end[0]


def _concept_units(facts: dict, ns: str, tag: str) -> list[dict] | None:
    node = facts.get("facts", {}).get(ns, {}).get(tag)
    if not node:
        return None
    units = node.get("units", {})
    # 取 USD(金额)或 shares
    for key in ("USD", "shares", "USD/shares"):
        if key in units:
            return units[key]
    # 退而取第一个单位
    return next(iter(units.values()), None)


def pit_line(facts: dict, key: str, as_of: str) -> tuple[float | None, str | None]:
    """按回退链取某线项的 PIT 值与其 filed 日。返回 (val, filed)。"""
    flow = key in FLOW_KEYS
    if key in DEI_TAGS:
        ns, tags = "dei", DEI_TAGS[key]
    else:
        ns, tags = "us-gaap", TAGS.get(key, [])
    for tag in tags:
        units = _concept_units(facts, ns, tag)
        if not units:
            continue
        f = latest_fact(units, as_of, flow)
        if f is not None and f.get("val") is not None:
            return float(f["val"]), f.get("filed")
    return None, None


def annual_period_ends(facts: dict, as_of: str) -> list[str]:
    """从年度损益事实(net_income 优先,revenue 兜底)取 filed<=as_of 的不同财年末,降序。"""
    for key in ("net_income", "revenue"):
        for tag in TAGS[key]:
            units = _concept_units(facts, "us-gaap", tag)
            if not units:
                continue
            ends = sorted({f["end"] for f in units
                           if _annual(f) and f.get("filed") and f["filed"] <= as_of and f.get("end")},
                          reverse=True)
            if ends:
                return ends
    return []


def _days(a: str, b: str) -> int:
    from datetime import date
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def fact_near_end(units: list[dict], end: str, as_of: str, tol: int) -> dict | None:
    """取 end 落在目标财年末 ±tol 天内、filed<=as_of 的事实;同 end 取首次申报(防重述)。"""
    cands = [f for f in units if f.get("end") and f.get("filed") and f["filed"] <= as_of
             and _days(f["end"], end) <= tol]
    if not cands:
        return None
    cands.sort(key=lambda f: (_days(f["end"], end), f["filed"]))  # 最近财年末 + 首次申报
    return cands[0]


def lines_at_end(facts: dict, end: str, as_of: str) -> dict:
    """取某财年末(end)的全部线项快照(PIT)。财务三表精确对齐(±10d),在外股数容差±100d。"""
    out: dict = {}
    for key in list(TAGS) + list(DEI_TAGS):
        ns, tags = ("dei", DEI_TAGS[key]) if key in DEI_TAGS else ("us-gaap", TAGS.get(key, []))
        tol = 100 if key == "shares" else 10
        val = None
        for tag in tags:
            units = _concept_units(facts, ns, tag)
            if not units:
                continue
            f = fact_near_end(units, end, as_of, tol)
            if f is not None and f.get("val") is not None:
                val = float(f["val"])
                break
        out[key] = val
    if out.get("gross_profit") is None and out.get("revenue") is not None and out.get("cogs") is not None:
        out["gross_profit"] = out["revenue"] - out["cogs"]
    out["period_end"] = end
    return out


def _latest_val(units: list[dict], as_of: str) -> tuple[str, float] | None:
    """filed<=as_of 中 end 最新的事实 → (end, val)(不限年度;用于股数时点取最新)。"""
    ff = [f for f in units if f.get("end") and f.get("filed") and f["filed"] <= as_of and f.get("val") is not None]
    if not ff:
        return None
    f = max(ff, key=lambda x: x["end"])
    return f["end"], float(f["val"])


def shares_outstanding(facts: dict, as_of: str, max_stale_days: int = 550) -> tuple[float | None, str | None, str | None]:
    """市值用在外股数(防拆股错配 + 多股权类汇总)。返回 (shares, end, source)。

    没有单一可靠标签:dei 对部分公司陈旧(Visa 仅 2010)、us-gaap CSO 可能只到上一年报(拆股前,如 NVDA)。
    策略:从多标签各取候选,**选 end 最新**(最近=拆股已调整、最贴当前),recency 闸过滤,
    同 end 取更完整来源(CSO 跨类汇总 > 加权股数 > dei 封面)。全失败 → None(宁缺勿错)。"""
    cands: list[tuple[str, float, str, int]] = []  # (end, shares, source, priority[小=优先])
    # CSO:时点,跨股权类在最新 end 汇总(去重同值)
    u = _concept_units(facts, "us-gaap", "CommonStockSharesOutstanding")
    if u:
        ff = [f for f in u if f.get("end") and f.get("filed") and f["filed"] <= as_of and f.get("val")]
        if ff:
            le = max(f["end"] for f in ff)
            seen, tot = set(), 0.0
            for f in ff:
                if f["end"] == le and f["val"] not in seen:
                    seen.add(f["val"])
                    tot += float(f["val"])
            if tot > 0:
                cands.append((le, tot, "us-gaap:CommonStockSharesOutstanding", 0))
    # 加权稀释/基本股数(总额,已含各类;取 end 最新,不限年度)
    for tag in ("WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"):
        u = _concept_units(facts, "us-gaap", tag)
        if u:
            r = _latest_val(u, as_of)
            if r:
                cands.append((r[0], r[1], "us-gaap:" + tag, 1))
    # dei 封面(单类/可能不全,优先级最低但常最新)
    u = _concept_units(facts, "dei", "EntityCommonStockSharesOutstanding")
    if u:
        r = _latest_val(u, as_of)
        if r:
            cands.append((r[0], r[1], "dei:EntityCommonStockSharesOutstanding", 2))

    cands = [c for c in cands if _days(c[0], as_of) <= max_stale_days]
    if not cands:
        return None, None, None
    max_end = max(c[0] for c in cands)
    top = sorted((c for c in cands if c[0] == max_end), key=lambda c: c[3])
    return top[0][1], top[0][0], top[0][2]


def extract_two_year(facts: dict, as_of: str) -> tuple[dict, dict | None]:
    """返回(本财年, 上一财年)两期对齐快照,供 Piotroski F / Beneish M 两期因子用。
    上一财年不可得时返回 None(两期因子降级为 None,不据缺失数据剔除)。"""
    ends = annual_period_ends(facts, as_of)
    if not ends:
        return extract_pit_fundamentals(facts, as_of), None
    cur = lines_at_end(facts, ends[0], as_of)
    prev = lines_at_end(facts, ends[1], as_of) if len(ends) >= 2 else None
    return cur, prev


def extract_pit_fundamentals(facts: dict, as_of: str) -> dict:
    """抽取一家公司在 as_of 时点可见的关键线项(PIT)。缺失为 None。"""
    out: dict = {}
    max_filed = None
    for key in list(TAGS) + list(DEI_TAGS):
        val, filed = pit_line(facts, key, as_of)
        out[key] = val
        if filed and (max_filed is None or filed > max_filed):
            max_filed = filed
    # gross_profit 缺则用 revenue-cogs 兜底
    if out.get("gross_profit") is None and out.get("revenue") is not None and out.get("cogs") is not None:
        out["gross_profit"] = out["revenue"] - out["cogs"]
    out["asof_fundamentals"] = max_filed  # 该公司基本面"最后申报日"(看板新鲜度用)
    return out


def derive_ratios(f: dict) -> dict:
    """从线项派生**不依赖价格**的基本面比率/因子(价格相关如 E/P 在因子层 join 行情时算)。
    全部为"越大越好"前已按方向处理;原始比率保留,符号在因子合成层定。"""
    def g(k):
        v = f.get(k)
        return v if isinstance(v, (int, float)) else None

    assets, eq, rev = g("assets"), g("equity"), g("revenue")
    gp, ni, oi = g("gross_profit"), g("net_income"), g("operating_income")
    cfo, capex, da = g("cfo"), g("capex"), g("dep_amort")
    lt, dc, cash = g("lt_debt"), g("debt_current"), g("cash")
    r: dict = {}
    # 质量:毛利率(Novy-Marx)、现金型经营利润、ROIC、ROE、资产周转
    r["gross_profitability"] = (gp / assets) if gp is not None and assets else None
    # 现金型经营利润 ≈ (经营利润 + 折旧摊销 - 应计) / 资产;简化用 CFO 近似经营现金质量
    r["cash_op_to_assets"] = ((cfo) / assets) if cfo is not None and assets else None
    invested = None
    if eq is not None:
        invested = eq + (lt or 0) + (dc or 0) - (cash or 0)
    r["roic"] = (oi / invested) if oi is not None and invested and invested > 0 else None
    r["roe"] = (ni / eq) if ni is not None and eq and eq > 0 else None
    r["asset_turnover"] = (rev / assets) if rev is not None and assets else None
    r["net_margin"] = (ni / rev) if ni is not None and rev else None
    # 杠杆 / 安全
    r["debt_to_assets"] = ((lt or 0) + (dc or 0)) / assets if assets else None
    r["debt_to_equity"] = ((lt or 0) + (dc or 0)) / eq if eq and eq > 0 else None
    # 现金流质量:应计(净利-经营现金流,越低越好) / 自由现金流
    if ni is not None and cfo is not None and assets:
        r["accruals_to_assets"] = (ni - cfo) / assets  # 越低越好(取负进合成)
    else:
        r["accruals_to_assets"] = None
    if cfo is not None and capex is not None:
        r["fcf"] = cfo - abs(capex)  # capex 申报通常为正流出
    else:
        r["fcf"] = None
    # 股东现金回报(美元额,因子层除以市值得收益率)
    r["dividends_paid"] = g("dividends_paid")
    r["buybacks"] = g("buybacks")
    r["stock_issued"] = g("stock_issued")
    # 再投资率(复利数学 g=ROIC×再投资率;用留存近似)
    if ni and ni > 0:
        payout = (abs(g("dividends_paid") or 0)) / ni
        r["reinvestment_rate"] = max(0.0, 1.0 - payout)
    else:
        r["reinvestment_rate"] = None
    return r


# ----------------------------- 组装 + CLI -----------------------------

def build_row(ticker: str, cik: str, facts: dict, as_of: str) -> dict:
    lines = extract_pit_fundamentals(facts, as_of)
    ratios = derive_ratios(lines)
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "asof_fundamentals": lines.get("asof_fundamentals"),
        "lines": {k: lines.get(k) for k in TAGS if lines.get(k) is not None},
        "ratios": {k: v for k, v in ratios.items() if v is not None},
    }


def load_universe(arg: str) -> list[str]:
    p = Path(arg)
    if p.exists():
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return [str(x).split(":")[-1].upper() for x in data]
        if isinstance(data, dict):
            return [str(x).split(":")[-1].upper() for x in data.get("tickers", data.keys())]
    return [t.strip().upper() for t in arg.split(",") if t.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="EDGAR PIT 基本面面板构建")
    ap.add_argument("--tickers", help="逗号分隔,如 AAPL,MSFT")
    ap.add_argument("--universe", help="JSON 文件路径(list 或 {tickers:[]})")
    ap.add_argument("--as-of", required=True, help="PIT 截止日 YYYY-MM-DD(只取 filed<=此日的事实)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    tickers = load_universe(args.universe or args.tickers or "")
    if not tickers:
        print("需要 --tickers 或 --universe", file=sys.stderr)
        return 2

    print(f"映射 ticker→CIK …")
    tmap = load_ticker_cik_map()
    rows, missing = [], []
    for i, t in enumerate(tickers):
        cik = tmap.get(t)
        if not cik:
            missing.append(t)
            continue
        try:
            facts = fetch_companyfacts(cik)
            rows.append(build_row(t, cik, facts, args.as_of))
            print(f"  [{i+1}/{len(tickers)}] {t} CIK{cik} ✓")
        except Exception as e:  # noqa: BLE001
            print(f"  {t}: 抓取失败 {e}", file=sys.stderr)
            missing.append(t)
        time.sleep(RATE_S)

    doc = {
        "schema_version": "1.0",
        "source": "SEC EDGAR XBRL companyfacts",
        "as_of": args.as_of,
        "note": "PIT:仅含 filed<=as_of 的事实;同报告期取最早申报防重述。非投资建议。",
        "universe_size": len(tickers),
        "n_resolved": len(rows),
        "missing": missing,
        "rows": rows,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    print(f"写入 {out_path}({len(rows)}/{len(tickers)} 家;缺 {len(missing)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
