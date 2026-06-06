"""把完整因子测试体系接到加密因子上(Hyperliquid 永续)。

复用 factor_pipeline 的预处理(Winsorize/Standardize/Neutralize),但中性化对象换成
加密合适的风格:size(log 日均美元成交额)+ BTC-beta(对 BTC 的市场暴露)。
依据研报 §3:加密因子模型 = 市场 + 规模 + 动量(Liu-Tsyvinski-Wu),故中性化掉"市场+规模"。

流程(全程无未来函数,rebalance 日只用 ≤d 数据):
  预处理 -> Rank-IC/IR -> 5 分层单调性 -> 多空(L5-L1)年化/回撤/Sharpe
  -> 无未来函数的"最近一个月(4 周)"滚动样本外验证。
周频 rebalance(step=7)、周持有(H=7):加密动量 1-4 周最强(研报 §3.4)。
"""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np

import crypto_factors as cf
import cryptodata as cd
import factor_pipeline as fp   # 复用 winsorize/standardize/neutralize 思路
import factors_xs as fx

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = 7
H = 7
N_LAYERS = 5


def winsorize(x):
    return fp.winsorize(x, 3.0)


def standardize(x):
    return fp.standardize(x)


def neutralize_cs(x, size, beta):
    """对 [截距 + size + BTC-beta] 做 OLS,取残差并标准化(剔除规模与市场暴露)。"""
    X = np.column_stack([np.ones(len(x)), standardize(size), standardize(beta)])
    b, *_ = np.linalg.lstsq(X, x, rcond=None)
    return standardize(x - X @ b)


def preprocess(raw, size, beta):
    return neutralize_cs(standardize(winsorize(raw)), size, beta)


def build_panel():
    uni = json.load(open(os.path.join(HERE, "crypto_universe.json")))
    panel = {}
    for coin in uni:
        c = cd.load_candles(coin)
        if not c or len(c["close"]) < 120:
            continue
        ts = np.asarray(c["ts"], dtype=np.int64)
        adj = np.asarray(c["close"], dtype=float)
        vol = np.asarray(c["vol"], dtype=float)
        fund = cd.load_funding(coin)
        fs = np.array([fund.get(int(t), (np.nan, np.nan, np.nan))[0] for t in ts])
        pm = np.array([fund.get(int(t), (np.nan, np.nan, np.nan))[2] for t in ts])
        ret = np.concatenate([[np.nan], np.diff(np.log(np.where(adj > 0, adj, np.nan)))])
        panel[coin] = dict(ts=ts, adj=adj, dollar=adj * vol, fs=fs, pm=pm, ret=ret,
                           m={int(t): i for i, t in enumerate(ts)})
    return panel


def btc_ret_at(panel, d):
    p = panel.get("BTC")
    i = p["m"].get(d) if p else None
    return p, i


def cross_section(panel, d, horizon):
    """返回 dict: 每因子 raw 数组 + size + beta + fwd(对齐)。"""
    btc = panel.get("BTC")
    bi = btc["m"].get(d) if btc else None
    if bi is None or bi < 61:
        return None
    btc_r = btc["ret"][bi - 60:bi + 1]
    cols = {f: [] for f in cf.FACTORS}
    size, beta, fwd = [], [], []
    for coin, p in panel.items():
        i = p["m"].get(d)
        if i is None or i + horizon >= len(p["adj"]) or i < 61:
            continue
        fv = cf.compute(p["adj"], i, p["fs"], p["pm"])
        if fv is None or not all(np.isfinite(fv[f]) for f in cf.FACTORS):
            continue
        adv = np.nanmean(p["dollar"][i - 60:i + 1])
        if not np.isfinite(adv) or adv <= 0:
            continue
        # BTC-beta:近 60 日对 BTC 回归斜率
        cr = p["ret"][i - 60:i + 1]
        mask = np.isfinite(cr) & np.isfinite(btc_r)
        if mask.sum() < 30 or np.var(btc_r[mask]) == 0:
            continue
        bta = np.cov(cr[mask], btc_r[mask])[0, 1] / np.var(btc_r[mask])
        for f in cf.FACTORS:
            cols[f].append(fv[f])
        size.append(np.log(adv)); beta.append(bta)
        fwd.append(p["adj"][i + horizon] / p["adj"][i] - 1.0)
    if len(fwd) < 10:
        return None
    out = {f: np.asarray(cols[f]) for f in cf.FACTORS}
    out.update(size=np.asarray(size), beta=np.asarray(beta), fwd=np.asarray(fwd))
    return out


def rebalance_dates(panel, step):
    ts = panel["BTC"]["ts"]
    return [int(ts[i]) for i in range(70, len(ts), step)]


def maxdd(cum):
    peak = np.maximum.accumulate(cum)
    return float(np.min(cum / peak - 1.0)) if len(cum) else float("nan")


def evaluate(panel, factor, dates, horizon, neutral=True):
    ics, raw_ics, ls = [], [], []
    layers = [[] for _ in range(N_LAYERS)]
    for d in dates:
        cs = cross_section(panel, d, horizon)
        if cs is None:
            continue
        raw = cf.SIGN[factor] * cs[factor]
        proc = preprocess(raw, cs["size"], cs["beta"]) if neutral else standardize(winsorize(raw))
        ics.append(fx.spearman(proc, cs["fwd"]))
        raw_ics.append(fx.spearman(raw, cs["fwd"]))
        o = np.argsort(proc); bk = np.array_split(o, N_LAYERS)
        for li, b in enumerate(bk):
            layers[li].append(float(cs["fwd"][b].mean()))
        ls.append(float(cs["fwd"][bk[-1]].mean() - cs["fwd"][bk[0]].mean()))
    ics = np.asarray([x for x in ics if np.isfinite(x)])
    ls = np.asarray(ls)
    ppy = 365 / horizon
    return dict(
        n=len(ics),
        ic=float(ics.mean()) if len(ics) else np.nan,
        ir=float(ics.mean() / ics.std(ddof=1)) if len(ics) > 1 and ics.std(ddof=1) > 0 else np.nan,
        t=float(ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))) if len(ics) > 1 and ics.std(ddof=1) > 0 else np.nan,
        pos=float((ics > 0).mean()) if len(ics) else np.nan,
        raw_ic=float(np.nanmean(raw_ics)) if raw_ics else np.nan,
        layers=[float(np.mean(l)) for l in layers],
        ann=float(ls.mean() * ppy), sharpe=float(ls.mean() / ls.std(ddof=1) * np.sqrt(ppy)) if ls.std(ddof=1) > 0 else np.nan,
        dd=maxdd(np.cumprod(1 + ls)), win=float((ls > 0).mean()) if len(ls) else np.nan,
    )


def main():
    panel = build_panel()
    dates = rebalance_dates(panel, STEP)
    print(f"加密 universe {len(panel)} 币, 周频 rebalance {len(dates)} 期, 持有 {H} 日")
    print(f"中性化对象: size(log日均成交额) + BTC-beta  (剔除'市场+规模'暴露)\n")
    print("=" * 92)
    print(f"{'因子':<12}{'Rank-IC':>9}{'IR':>8}{'t':>7}{'IC>0':>7}{'原始IC':>9}"
          f"{'分层单调':>10}{'多空年化':>9}{'Sharpe':>8}{'回撤':>8}")
    print("-" * 92)
    res = {}
    for f in cf.FACTORS + ["composite"]:
        if f == "composite":
            r = eval_composite(panel, dates, H)
        else:
            r = evaluate(panel, f, dates, H, neutral=True)
        res[f] = r
        mono = monolabel(r["layers"])
        print(f"{f:<12}{r['ic']:>+9.4f}{r['ir']:>+8.3f}{r['t']:>+7.2f}{r['pos']*100:>6.0f}%"
              f"{r['raw_ic']:>+9.4f}{mono:>10}{r['ann']*100:>+8.1f}%{r['sharpe']:>+8.2f}{r['dd']*100:>+7.0f}%")
    print("=" * 92)

    # 分层明细(最佳因子)
    best = max((f for f in cf.FACTORS), key=lambda f: res[f]["ir"] if np.isfinite(res[f]["ir"]) else -9)
    print(f"\n最佳因子(训练全期 IR 最高)= '{best}'  分层平均周收益(L1低->L5高):")
    print("   " + "  ".join(f"L{i+1}:{x*100:+.2f}%" for i, x in enumerate(res[best]["layers"])))

    # 无未来函数:最近 4 周(≈1 个月)滚动样本外验证
    print("\n" + "=" * 92)
    print(f"无未来函数验证:最近 4 周(≈1 月)滚动样本外,固定 '{best}' 方向逐周建仓持有 {H} 日")
    print("=" * 92)
    spy = None  # 加密无 SPY,用 BTC 作市场基准
    btc = panel["BTC"]
    complete = [d for d in dates if (btc["m"].get(d) is not None and btc["m"][d] + H < len(btc["adj"]))]
    recent = complete[-4:]
    rows = []
    for d in recent:
        cs = cross_section(panel, d, H)
        if cs is None:
            continue
        proc = preprocess(cf.SIGN[best] * cs[best], cs["size"], cs["beta"])
        o = np.argsort(proc); bk = np.array_split(o, N_LAYERS)
        lsret = float(cs["fwd"][bk[-1]].mean() - cs["fwd"][bk[0]].mean())
        bi = btc["m"][d]; btc_r = btc["adj"][bi + H] / btc["adj"][bi] - 1.0
        rows.append((d, lsret, float(cs["fwd"][bk[-1]].mean()), btc_r))
    for d, ls, l5, br in rows:
        print(f"  {dt.datetime.utcfromtimestamp(d).date()}: 多空(L5-L1) {ls*100:+.2f}%  "
              f"L5买入 {l5*100:+.2f}%  BTC基准 {br*100:+.2f}%")
    lsm = np.array([r[1] for r in rows])
    print(f"\n  最近 4 周多空: 均值 {lsm.mean()*100:+.2f}%/周  胜率 {(lsm>0).mean()*100:.0f}%  (样本=4,仅演示)")
    print(f"  对比全期: '{best}' 多空 Sharpe={res[best]['sharpe']:+.2f}, IR={res[best]['ir']:+.3f}")
    print("  诚实提醒:4 周样本同样太小;且币数仅 ~15-20,5 分层每层 3-4 币,噪声大。")


def eval_composite(panel, dates, horizon):
    """等权合成(各因子中性化后 z-score 求和)的 IC/IR/分层/多空。"""
    ics, ls = [], []
    layers = [[] for _ in range(N_LAYERS)]
    for d in dates:
        cs = cross_section(panel, d, horizon)
        if cs is None:
            continue
        s = np.zeros_like(cs["fwd"])
        for f in cf.FACTORS:
            s = s + preprocess(cf.SIGN[f] * cs[f], cs["size"], cs["beta"])
        ics.append(fx.spearman(s, cs["fwd"]))
        o = np.argsort(s); bk = np.array_split(o, N_LAYERS)
        for li, b in enumerate(bk):
            layers[li].append(float(cs["fwd"][b].mean()))
        ls.append(float(cs["fwd"][bk[-1]].mean() - cs["fwd"][bk[0]].mean()))
    ics = np.asarray([x for x in ics if np.isfinite(x)]); ls = np.asarray(ls)
    ppy = 365 / horizon
    return dict(n=len(ics), ic=float(ics.mean()), ir=float(ics.mean()/ics.std(ddof=1)) if ics.std(ddof=1)>0 else np.nan,
                t=float(ics.mean()/ics.std(ddof=1)*np.sqrt(len(ics))) if ics.std(ddof=1)>0 else np.nan,
                pos=float((ics>0).mean()), raw_ic=np.nan, layers=[float(np.mean(l)) for l in layers],
                ann=float(ls.mean()*ppy), sharpe=float(ls.mean()/ls.std(ddof=1)*np.sqrt(ppy)) if ls.std(ddof=1)>0 else np.nan,
                dd=maxdd(np.cumprod(1+ls)), win=float((ls>0).mean()))


def monolabel(layers):
    up = all(layers[i] <= layers[i+1] for i in range(len(layers)-1))
    dn = all(layers[i] >= layers[i+1] for i in range(len(layers)-1))
    return "单调↑" if up else ("单调↓" if dn else "非单调")


if __name__ == "__main__":
    main()
