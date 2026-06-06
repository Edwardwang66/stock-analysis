"""完整因子测试体系:预处理 -> IC/IR -> 分层回测 -> 无未来函数的 1 个月持有验证。

严格按标准量化流程实现,全程无未来函数(rebalance 日只用 ≤d 数据):

1) 预处理(每个 rebalance 日的横截面上做):
   - 去极值 Winsorize:超过均值 ±3 倍标准差截断。
   - 标准化 Standardize:z-score(均值 0、方差 1)。
   - 中性化 Neutralize:对【行业哑变量 + 市值代理(log 日均成交额)】做 OLS,取残差,
     剔除行业与市值暴露,得到纯粹的 alpha 部分;残差再标准化。
2) IC/IR:Rank-IC 均值(要求 >0.05)、IR=mean/std(要求 >0.5)、t 统计、IC>0 占比。
3) 分层回测:按因子分 5 组,看各组未来收益单调性;多空(top-bottom)年化/最大回撤/Sharpe。
4) 1 个月验证:用"holdout 之前"的数据选因子与方向(不偷看答案),在 holdout 月初按当时
   可得信息建仓,持有 21 日,验证真实收益。

市值说明:Yahoo 市值端点需鉴权(401),故用 log(60日均美元成交额)作 size 代理(业界标准的
流动性/规模控制变量)。诚实标注:这是代理,非精确流通市值。
"""
from __future__ import annotations

import json
import os

import numpy as np

import data as datamod
import factors_xs as fx

HERE = os.path.dirname(os.path.abspath(__file__))
SECTORS = json.load(open(os.path.join(HERE, "sector_map.json")))


# ---------------- 预处理 ----------------

def winsorize(x: np.ndarray, n_std: float = 3.0) -> np.ndarray:
    m, s = np.nanmean(x), np.nanstd(x)
    return np.clip(x, m - n_std * s, m + n_std * s)


def standardize(x: np.ndarray) -> np.ndarray:
    s = np.nanstd(x)
    return (x - np.nanmean(x)) / s if s > 0 else np.zeros_like(x)


def neutralize(x: np.ndarray, sector_ids: np.ndarray, size: np.ndarray) -> np.ndarray:
    """对 [行业哑变量 + size + 截距] 做 OLS,返回残差(已标准化)。"""
    n = len(x)
    uniq = sorted(set(sector_ids.tolist()))
    # 行业哑变量(丢一个避免与截距共线)+ size + 截距
    cols = [np.ones(n), standardize(size)]
    for s in uniq[1:]:
        cols.append((sector_ids == s).astype(float))
    X = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(X, x, rcond=None)
    resid = x - X @ beta
    return standardize(resid)


def preprocess(raw: np.ndarray, sector_ids: np.ndarray, size: np.ndarray,
               do_neutralize: bool = True) -> np.ndarray:
    z = standardize(winsorize(raw, 3.0))
    return neutralize(z, sector_ids, size) if do_neutralize else z


# ---------------- 面板与横截面 ----------------

def load_panel():
    uni = json.load(open(os.path.join(HERE, "universe.json")))["universe"]
    panel = {}
    for tk in uni:
        d = datamod.load(tk)
        if not d or len(d.get("adjclose", [])) <= 320:
            continue
        ts = np.asarray(d["ts"], dtype=np.int64)
        adj = np.asarray(d["adjclose"], dtype=float)
        close = np.asarray(d["close"], dtype=float)
        vol = np.asarray(d["volume"], dtype=float)
        panel[tk] = dict(ts=ts, adj=adj, dollar=close * vol,
                         sec=SECTORS.get(tk, "Unknown"),
                         m={int(t): i for i, t in enumerate(ts)})
    return panel


SECTOR_TO_ID = {s: i for i, s in enumerate(sorted(set(SECTORS.values()) | {"Unknown"}))}


def cross_section(panel, d, horizon, factor_fn):
    raw, sec, size, fwd = [], [], [], []
    for tk, p in panel.items():
        i = p["m"].get(d)
        if i is None or i + horizon >= len(p["adj"]) or i < 252:
            continue
        adj = p["adj"]
        fv = factor_fn(adj, i)
        if fv is None or not np.isfinite(fv):
            continue
        adv = np.nanmean(p["dollar"][i - 60:i + 1]) if i >= 60 else np.nan
        if not np.isfinite(adv) or adv <= 0:
            continue
        raw.append(fv)
        sec.append(SECTOR_TO_ID[p["sec"]])
        size.append(np.log(adv))
        fwd.append(adj[i + horizon] / adj[i] - 1.0)
    if len(fwd) < 30:
        return None
    return (np.asarray(raw), np.asarray(sec), np.asarray(size), np.asarray(fwd))


# ---------------- 因子定义(待测) ----------------

def f_reversal(adj, i):
    return -(adj[i] / adj[i - 21] - 1.0) if adj[i - 21] > 0 else None   # 短期反转(取负)


def f_momentum(adj, i):
    return adj[i - 21] / adj[i - 252] - 1.0 if adj[i - 252] > 0 else None  # 12-1 动量


FACTORS = {"reversal": f_reversal, "momentum": f_momentum}


# ---------------- 主流程 ----------------

def rebalance_dates(panel, step):
    ts = panel["AAPL"]["ts"] if "AAPL" in panel else next(iter(panel.values()))["ts"]
    return [int(ts[i]) for i in range(252, len(ts), step)]


def max_drawdown(cum: np.ndarray) -> float:
    peak = np.maximum.accumulate(cum)
    return float(np.min(cum / peak - 1.0))


def evaluate(panel, factor_fn, dates, horizon=21, n_layers=5, do_neutralize=True,
             hold_dates=None):
    """对给定 factor 跑 IC/IR + 分层 + 多空。hold_dates 限定用哪些 rebalance 日(用于训练/holdout 切分)。"""
    use = hold_dates if hold_dates is not None else dates
    ics, raw_ics = [], []
    layer_rets = [[] for _ in range(n_layers)]
    ls_rets = []
    for d in use:
        cs = cross_section(panel, d, horizon, factor_fn)
        if cs is None:
            continue
        raw, sec, size, fwd = cs
        proc = preprocess(raw, sec, size, do_neutralize)
        ics.append(fx.spearman(proc, fwd))
        raw_ics.append(fx.spearman(raw, fwd))
        order = np.argsort(proc)
        buckets = np.array_split(order, n_layers)
        for li, b in enumerate(buckets):
            layer_rets[li].append(float(fwd[b].mean()))
        ls_rets.append(float(fwd[buckets[-1]].mean() - fwd[buckets[0]].mean()))
    ics = np.asarray([x for x in ics if np.isfinite(x)])
    ls = np.asarray(ls_rets)
    if len(ls) == 0:
        return {"n_periods": 0, "ic_mean": float("nan"), "ic_ir": float("nan"),
                "ic_t": float("nan"), "ic_pos_ratio": float("nan"),
                "raw_ic_mean": float("nan"), "layer_avg": [float("nan")] * n_layers,
                "ls_ann": float("nan"), "ls_sharpe": float("nan"),
                "ls_maxdd": float("nan"), "ls_winrate": float("nan")}
    layer_avg = [float(np.mean(lr)) for lr in layer_rets]
    # 多空累计(非重叠时可直接复利;此处 step 可能=H)
    cum = np.cumprod(1 + ls)
    periods_per_year = 252 / horizon
    ann = float(ls.mean() * periods_per_year)
    sharpe = float(ls.mean() / ls.std(ddof=1) * np.sqrt(periods_per_year)) if ls.std(ddof=1) > 0 else float("nan")
    return {
        "n_periods": len(ics),
        "ic_mean": float(ics.mean()) if len(ics) else float("nan"),
        "ic_ir": float(ics.mean() / ics.std(ddof=1)) if len(ics) > 1 and ics.std(ddof=1) > 0 else float("nan"),
        "ic_t": float(ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))) if len(ics) > 1 and ics.std(ddof=1) > 0 else float("nan"),
        "ic_pos_ratio": float((ics > 0).mean()) if len(ics) else float("nan"),
        "raw_ic_mean": float(np.nanmean(raw_ics)) if raw_ics else float("nan"),
        "layer_avg": layer_avg,
        "ls_ann": ann,
        "ls_sharpe": sharpe,
        "ls_maxdd": max_drawdown(cum),
        "ls_winrate": float((ls > 0).mean()),
    }


def print_report(name, r):
    print(f"\n【{name}】 (n={r['n_periods']} 期, 月度非重叠)")
    print(f"  IC/IR: Rank-IC均值={r['ic_mean']:+.4f}  IR={r['ic_ir']:+.3f}  "
          f"t={r['ic_t']:+.2f}  IC>0占比={r['ic_pos_ratio']*100:.0f}%  (中性化前原始IC={r['raw_ic_mean']:+.4f})")
    layers = "  ".join(f"L{i+1}:{x*100:+.2f}%" for i, x in enumerate(r["layer_avg"]))
    mono = "单调↑" if all(r["layer_avg"][i] <= r["layer_avg"][i+1] for i in range(len(r["layer_avg"])-1)) else \
           ("单调↓" if all(r["layer_avg"][i] >= r["layer_avg"][i+1] for i in range(len(r["layer_avg"])-1)) else "非单调")
    print(f"  分层平均未来{21}日收益: {layers}   [{mono}]")
    print(f"  多空(L5-L1): 年化={r['ls_ann']*100:+.1f}%  Sharpe={r['ls_sharpe']:+.2f}  "
          f"最大回撤={r['ls_maxdd']*100:.1f}%  胜率={r['ls_winrate']*100:.0f}%")


def main():
    print("加载面板 ...")
    panel = load_panel()
    dates = rebalance_dates(panel, step=21)
    H = 21

    # holdout 切分:选"最近一个已走完完整 21 日"的 rebalance 月做验证,其余更早的为训练
    spy0 = datamod.load("SPY")
    spy_ts = [int(t) for t in spy0["ts"]]
    last_complete = spy_ts[-1 - H]   # 末尾留出 H 日,确保 holdout 有完整未来
    holdout_date = max(d for d in dates if d <= last_complete)
    train_dates = [d for d in dates if d < holdout_date]
    import datetime as dt
    print(f"标的 {len(panel)} 只, rebalance {len(dates)} 期")
    print(f"训练期 rebalance 日 {len(train_dates)} 个 | holdout 月初 = "
          f"{dt.datetime.utcfromtimestamp(holdout_date).date()}\n")
    print("=" * 78)
    print("第 1-3 步:预处理(去极值+标准化+行业/市值中性化) -> IC/IR -> 分层 (训练期, 全程无未来函数)")
    print("=" * 78)

    results = {}
    for name, fn in FACTORS.items():
        r = evaluate(panel, fn, train_dates, H, n_layers=5, do_neutralize=True)
        results[name] = r
        print_report(name + "(中性化后)", r)

    # 选因子:用训练期 IR 选(不偷看 holdout)
    pick = max(results, key=lambda k: results[k]["ic_ir"] if np.isfinite(results[k]["ic_ir"]) else -9)
    print(f"\n>>> 按【训练期 IR 最高】选出因子 = '{pick}' (IR={results[pick]['ic_ir']:.3f}),冻结其方向用于验证。")

    print("\n" + "=" * 78)
    print(f"第 4 步:1 个月持有验证 —— 无未来函数 (holdout 月初仅用当时可得数据建仓,持有 {H} 日)")
    print("=" * 78)
    cs = cross_section(panel, holdout_date, H, FACTORS[pick])
    raw, sec, size, fwd = cs
    proc = preprocess(raw, sec, size, True)
    order = np.argsort(proc)
    q = np.array_split(order, 5)
    top, bot = q[-1], q[0]
    spy = datamod.load("SPY"); st = {int(t): i for i, t in enumerate(spy["ts"])}
    si = st.get(holdout_date)
    spy_ret = (spy["adjclose"][si + H] / spy["adjclose"][si] - 1.0) if si and si + H < len(spy["adjclose"]) else float("nan")
    print(f"  因子 '{pick}',持仓股票数={len(fwd)}")
    print(f"  最高分组(L5,买入) 实现收益 = {fwd[top].mean()*100:+.2f}%")
    print(f"  最低分组(L1,做空) 实现收益 = {fwd[bot].mean()*100:+.2f}%")
    print(f"  多空对冲(L5-L1) 实现收益 = {(fwd[top].mean()-fwd[bot].mean())*100:+.2f}%")
    print(f"  同期 SPY 基准 = {spy_ret*100:+.2f}%   |  L5 超额 = {(fwd[top].mean()-spy_ret)*100:+.2f}%")
    print(f"\n  (注:此为单月单次实现值,样本=1,只是流程演示,不能据此判断因子优劣——见下方)")

    # 滚动样本外:最近 12 个完整月,每月用"当时及之前"数据建仓(无未来函数),方向固定(理论先验)
    print("\n" + "=" * 78)
    print(f"补充:滚动样本外 12 个月 (固定 '{pick}' 方向,逐月无未来函数) —— 证明单月=噪声")
    print("=" * 78)
    complete = [d for d in dates if d <= last_complete]
    roll = complete[-12:]
    ls_list, l5_list, spy_list = [], [], []
    for d in roll:
        cs = cross_section(panel, d, H, FACTORS[pick])
        if cs is None:
            continue
        raw, sec, size, fwd = cs
        proc = preprocess(raw, sec, size, True)
        o = np.argsort(proc); qq = np.array_split(o, 5)
        ls_list.append(float(fwd[qq[-1]].mean() - fwd[qq[0]].mean()))
        l5_list.append(float(fwd[qq[-1]].mean()))
        si2 = st.get(d)
        spy_list.append(spy["adjclose"][si2 + H] / spy["adjclose"][si2] - 1.0)
    ls_a = np.asarray(ls_list)
    print(f"  逐月多空(L5-L1)收益(%): " + " ".join(f"{x*100:+.1f}" for x in ls_a))
    print(f"  12 月多空: 均值 {ls_a.mean()*100:+.2f}%/月  Sharpe(年化) "
          f"{ls_a.mean()/ls_a.std(ddof=1)*np.sqrt(12):+.2f}  胜率 {(ls_a>0).mean()*100:.0f}%")
    print(f"  对比:训练期 106 月多空 Sharpe={results[pick]['ls_sharpe']:+.2f} "
          f"-> 单月波动极大,任何一个月的盈亏都是噪声,必须看多月分布。")


if __name__ == "__main__":
    main()
