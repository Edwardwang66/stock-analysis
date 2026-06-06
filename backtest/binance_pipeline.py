"""长历史(2017-2026)加密因子测试体系 —— 用 Binance 数据补足样本长度。

相比 crypto_pipeline.py(Hyperliquid 仅 ~2 年、违反 MinBTL),这里用 Binance.vision 的
~8.8 年日线 + ~6.4 年资金费,做完整体系并加一个真正的时间切分样本外:
  - 预处理:Winsorize -> Standardize -> Neutralize(size=log成交额 + BTC-beta)
  - IC/IR、5 分层单调性、多空 L5-L1(年化/回撤/Sharpe)
  - 时间切分 OOS:训练期(<2023)只用于"选因子+定方向"(不偷看);测试期(>=2023)独立验证。
  - 月频 rebalance(step=21)、月持有(H=21)。

诚实声明:宇宙取"当前在交易"的 USDT 对 -> 幸存者偏差(退市币缺失,高估)。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np

import binancedata as bd
import factor_pipeline as fp
import factors_xs as fx

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = 21
H = 21
N_LAYERS = 5
SPLIT_TS = int(dt.datetime(2023, 1, 1, tzinfo=dt.timezone.utc).timestamp())


def build_panel():
    uni = json.load(open(os.path.join(HERE, "binance_universe.json")))
    panel = {}
    for s in uni:
        k = bd.load(s, "1d")
        if not k or len(k["close"]) < 400:
            continue
        ts = np.asarray(k["ts"], dtype=np.int64)
        adj = np.asarray(k["close"], dtype=float)
        qv = np.asarray(k["quote_vol"], dtype=float)
        ret = np.concatenate([[np.nan], np.diff(np.log(np.where(adj > 0, adj, np.nan)))])
        fund = bd.load(s, "funding")
        fmap = {int(t): fs for t, fs in zip(fund.get("ts", []), fund.get("fund_sum", []))} if fund else {}
        fs = np.array([fmap.get(int(t), np.nan) for t in ts])
        panel[s] = dict(ts=ts, adj=adj, qv=qv, ret=ret, fs=fs,
                        m={int(t): i for i, t in enumerate(ts)})
    return panel


def factors(adj, i, fs):
    if i < 65 or adj[i - 60] <= 0 or adj[i - 7] <= 0 or adj[i - 5] <= 0:
        return None
    seg = adj[i - 30:i + 1]
    r = np.log(seg[1:] / seg[:-1])
    vol = float(r.std(ddof=1) * np.sqrt(365))
    fc = np.nanmean(fs[i - 13:i + 1]) if i >= 13 else np.nan
    return {
        "mom_60": adj[i - 5] / adj[i - 60] - 1.0,    # 中期动量(跳过最近5日)
        "reversal_7": adj[i] / adj[i - 7] - 1.0,     # 短期反转
        "vol_30": vol,
        "fund_carry": fc,
    }


SIGN = {"mom_60": +1, "reversal_7": -1, "vol_30": -1, "fund_carry": -1}
FACTORS = list(SIGN.keys())


def cross_section(panel, d, horizon):
    btc = panel["BTCUSDT"]; bi = btc["m"].get(d)
    if bi is None or bi < 61:
        return None
    br = btc["ret"][bi - 60:bi + 1]
    cols = {f: [] for f in FACTORS}; size = []; beta = []; fwd = []
    for s, p in panel.items():
        i = p["m"].get(d)
        if i is None or i + horizon >= len(p["adj"]) or i < 65:
            continue
        fv = factors(p["adj"], i, p["fs"])
        # fund_carry 允许 nan(2019 前无期货),其余因子必须有效
        if fv is None or not all(np.isfinite(fv[f]) for f in ["mom_60", "reversal_7", "vol_30"]):
            continue
        adv = np.nanmean(p["qv"][i - 30:i + 1])
        if not np.isfinite(adv) or adv <= 0:
            continue
        cr = p["ret"][i - 60:i + 1]; mask = np.isfinite(cr) & np.isfinite(br)
        if mask.sum() < 30 or np.var(br[mask]) == 0:
            continue
        bta = np.cov(cr[mask], br[mask])[0, 1] / np.var(br[mask])
        for f in FACTORS:
            cols[f].append(fv[f])
        size.append(np.log(adv)); beta.append(bta); fwd.append(p["adj"][i + horizon] / p["adj"][i] - 1.0)
    if len(fwd) < 12:
        return None
    out = {f: np.asarray(cols[f], dtype=float) for f in FACTORS}
    out.update(size=np.asarray(size), beta=np.asarray(beta), fwd=np.asarray(fwd))
    return out


def neutralize(x, size, beta):
    X = np.column_stack([np.ones(len(x)), fp.standardize(size), fp.standardize(beta)])
    b, *_ = np.linalg.lstsq(X, x, rcond=None)
    return fp.standardize(x - X @ b)


def preprocess(raw, size, beta):
    # fund_carry 可能含 nan -> 用 0 填充(中性后均值0,缺失即中性)
    raw = np.where(np.isfinite(raw), raw, np.nan)
    if np.isnan(raw).any():
        m = np.nanmean(raw); raw = np.where(np.isnan(raw), m if np.isfinite(m) else 0.0, raw)
    return neutralize(fp.standardize(fp.winsorize(raw, 3.0)), size, beta)


def maxdd(c):
    pk = np.maximum.accumulate(c); return float(np.min(c / pk - 1.0)) if len(c) else np.nan


def evaluate(panel, factor, dates, horizon):
    ics, raw_ics, ls = [], [], []
    layers = [[] for _ in range(N_LAYERS)]
    for d in dates:
        cs = cross_section(panel, d, horizon)
        if cs is None:
            continue
        raw = SIGN[factor] * cs[factor]
        proc = preprocess(raw, cs["size"], cs["beta"])
        ics.append(fx.spearman(proc, cs["fwd"])); raw_ics.append(fx.spearman(np.nan_to_num(raw), cs["fwd"]))
        o = np.argsort(proc); bk = np.array_split(o, N_LAYERS)
        for li, b in enumerate(bk):
            layers[li].append(float(cs["fwd"][b].mean()))
        ls.append(float(cs["fwd"][bk[-1]].mean() - cs["fwd"][bk[0]].mean()))
    ics = np.asarray([x for x in ics if np.isfinite(x)]); ls = np.asarray(ls)
    ppy = 252 / horizon
    sd = ics.std(ddof=1) if len(ics) > 1 else 0
    return dict(n=len(ics), ic=float(ics.mean()) if len(ics) else np.nan,
                ir=float(ics.mean()/sd) if sd > 0 else np.nan,
                t=float(ics.mean()/sd*np.sqrt(len(ics))) if sd > 0 else np.nan,
                pos=float((ics>0).mean()) if len(ics) else np.nan,
                raw_ic=float(np.nanmean(raw_ics)) if raw_ics else np.nan,
                layers=[float(np.mean(l)) for l in layers] if all(layers) else [np.nan]*N_LAYERS,
                ann=float(ls.mean()*ppy) if len(ls) else np.nan,
                sharpe=float(ls.mean()/ls.std(ddof=1)*np.sqrt(ppy)) if len(ls)>1 and ls.std(ddof=1)>0 else np.nan,
                dd=maxdd(np.cumprod(1+ls)), win=float((ls>0).mean()) if len(ls) else np.nan)


def mono(layers):
    up = all(layers[i] <= layers[i+1] for i in range(len(layers)-1))
    dn = all(layers[i] >= layers[i+1] for i in range(len(layers)-1))
    return "单调↑" if up else ("单调↓" if dn else "非单调")


def header():
    print(f"{'因子':<12}{'Rank-IC':>9}{'IR':>8}{'t':>7}{'IC>0':>7}{'原始IC':>9}{'单调':>8}"
          f"{'多空年化':>9}{'Sharpe':>8}{'回撤':>7}")
    print("-" * 86)


def row(f, r):
    print(f"{f:<12}{r['ic']:>+9.4f}{r['ir']:>+8.3f}{r['t']:>+7.2f}{r['pos']*100:>6.0f}%"
          f"{r['raw_ic']:>+9.4f}{mono(r['layers']):>8}{r['ann']*100:>+8.1f}%{r['sharpe']:>+8.2f}{r['dd']*100:>+6.0f}%")


def main():
    panel = build_panel()
    ts = panel["BTCUSDT"]["ts"]
    dates = [int(ts[i]) for i in range(65, len(ts), STEP)]
    train = [d for d in dates if d < SPLIT_TS]
    test = [d for d in dates if d >= SPLIT_TS]
    span = lambda L: f"{dt.datetime.utcfromtimestamp(L[0]).date()}~{dt.datetime.utcfromtimestamp(L[-1]).date()}"
    print(f"Binance 长历史:{len(panel)} 币,月频 {len(dates)} 期 ({span(dates)})")
    print(f"训练(选因子) {len(train)} 期 ({span(train)}) | 样本外测试 {len(test)} 期 ({span(test)})")
    print(f"中性化:size + BTC-beta\n")

    print("=" * 86); print("全样本(仅供观察,含选因子用的训练期)"); print("=" * 86); header()
    full = {}
    for f in FACTORS:
        full[f] = evaluate(panel, f, dates, H); row(f, full[f])

    print("\n" + "=" * 86)
    print("训练期(<2023):用于选因子,绝不报为最终结论"); print("=" * 86); header()
    tr = {}
    for f in FACTORS:
        tr[f] = evaluate(panel, f, train, H); row(f, tr[f])
    pick = max(FACTORS, key=lambda f: tr[f]["ir"] if np.isfinite(tr[f]["ir"]) else -9)
    print(f"\n>>> 按训练期 IR 选出 = '{pick}' (IR={tr[pick]['ir']:.3f}),冻结方向。")

    print("\n" + "=" * 86)
    print(f"★ 样本外测试(>=2023,冻结 '{pick}' 后从未参与选择)—— 这才是诚实结论")
    print("=" * 86); header()
    oos = evaluate(panel, pick, test, H); row(pick, oos)
    print(f"\n  样本外 {pick}: Rank-IC={oos['ic']:+.4f}  IR={oos['ir']:+.3f}  "
          f"多空Sharpe={oos['sharpe']:+.2f}  分层{mono(oos['layers'])}")
    print(f"  分层周期收益(L1->L5): " + "  ".join(f"{x*100:+.2f}%" for x in oos["layers"]))
    print(f"  达标判断(IC>0.05/IR>0.5): IC {'✅' if oos['ic']>0.05 else '❌'}  IR {'✅' if oos['ir']>0.5 else '❌'}")


if __name__ == "__main__":
    main()
