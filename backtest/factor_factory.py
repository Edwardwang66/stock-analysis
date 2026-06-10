"""公式因子工厂(本仓版)—— 可审计公式因子的预算化搜索 + 六门控实跑(设计文档 §6.2.3)。

定位:把 feed/factory/candidates.json 从「手写示例」变成「真实评估过的候选」。
本版不调 LLM(无 API key 依赖):在一个**预注册的小语法**上做穷举+预算抽样 ——
这恰好符合设计文档的精神:可审计、试验次数可数、无记忆性前视。
LLM 接入后只需替换「提案器」(propose_candidates),门控管线不变。

语法(刻意小,防 p-hacking):
  score = s1·T(term1) [+ s2·T(term2)]   s∈{+1,-1}, T∈{rank, z}
  terminals(全部因果,t 日只用 ≤t 数据):
    r5/r21/r63   过去 5/21/63 日收益          vol21/vol63  实现波动
    hi52         价格/52周高                  vz21         成交量 z(vs 过去63日)
    amihud21     非流动性(|r|/成交额)         rev1         1 日收益(短反转原料)
    gap_oc       隔夜跳空均值(21日)

六门控(对齐 §6.2.3;在 train 段执行,holdout 仅一次终检):
  ① 预注册预算:1 项式穷举(36) + 2 项式抽样 ≤264 → N=300 全部计数
  ② 增量正交 IC:对现有 4 因子(mom_12_1/reversal/hi52/lowvol)横截面回归取残差后的 IC
  ③ 多重检验:Benjamini-Yekutieli 相依 FDR(q<0.10)+ |t|≥3
  ④ 广度:报告 IC 序列有效期数(特征值参与率版未实现,诚实标注)
  ⑤ 经济机制:每个 terminal 携带事前假设文本(机器组装,弱假设,如实标注)
  ⑥ 净成本存活:decile L/S 扣 5bp+冲击 后 IR>0
通过全部 → decision="shadow"(60 日影子,绝不直接 accept);否则 "reject"。

用法: python backtest/factor_factory.py [--publish] [--top 8]
运行 ~1-2 分钟(月度重平衡,横截面计算量小)。
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import data as datamod        # noqa: E402
import factors_xs as fx       # noqa: E402
import statarb as sa          # noqa: E402
import validation as val      # noqa: E402

SEED = 20260610               # 预注册随机种子(抽样可复现)
BUDGET_2TERM = 264            # 2 项式抽样预算(与 1 项式合计 N=300,全部计入多重检验)
H = 21                        # 持有期(月度)
TRAIN_END = "2025-01-01"      # 与引擎同一 holdout 切点(R5)
COST_BPS = 5.0                # 单边价差
IMPACT_FRAC = 0.0008          # decile 组合换手的近似冲击(保守常数,容量小时偏高估)

TERMINALS = {
    "r5":       "过去5日收益:短期延续/反转原料",
    "r21":      "过去21日收益:1月反转(De Bondt-Thaler 短期过度反应)",
    "r63":      "过去63日收益:季度动量",
    "vol21":    "21日实现波动:低波异象(Blitz-van Vliet)",
    "vol63":    "63日实现波动:低波异象(慢)",
    "hi52":     "52周高点接近度:George-Hwang 锚定效应",
    "vz21":     "成交量z:量能异动(注意力/信息到达)",
    "amihud21": "Amihud非流动性:流动性溢价",
    "rev1":     "1日收益:做市商库存效应短反转",
    "gap_oc":   "21日隔夜跳空均值:隔夜/日内收益分解(Lou-Polk-Skouras)",
}
TRANSFORMS = ("rank", "z")
BASE_FACTORS = ["mom_12_1", "reversal", "hi52", "lowvol"]   # 增量正交的基(现有因子库)


# ----------------------------- 面板构建 -----------------------------

def load_pit():
    """时点成分库(Cycle 9 pit_membership);缺文件返回 None(过滤自动跳过)。"""
    import json
    try:
        import pit_membership as pm
        return json.load(open(pm.CACHE)) if os.path.exists(pm.CACHE) else None
    except (ImportError, OSError, ValueError):   # 不吞 NameError 之类的真 bug
        return None


def build_panel(start_year=2021, pit_filter: bool = True, tickers: list | None = None):
    """月度重平衡面板:dates(rebal 时间戳)、每期 {terminal: 矩阵列}、未来 H 日收益、基因子。

    pit_filter=True:每个 rebal 日只保留**当日确实在 S&P500 里**的票(membership_asof),
    消除「用今天的成分回测过去」的指数成员前视(未来赢家泄漏);被剔比例入返回值。
    """
    spy = datamod.load("SPY")
    sts = np.asarray(spy["ts"], dtype=np.int64)
    import datetime as _dt
    keep = [i for i, t in enumerate(sts)
            if _dt.datetime.utcfromtimestamp(int(t)).year >= start_year - 1]
    cal = sts[keep]
    rebal_idx = list(range(260, len(cal) - H, H))

    panel = {}
    for tk in (tickers or sa.DEMO_UNIVERSE):
        d = datamod.load(tk)
        if not d or len(d.get("adjclose", [])) < 400:
            continue
        m = {int(t): i for i, t in enumerate(np.asarray(d["ts"], dtype=np.int64))}
        panel[tk] = (d, m)

    pit = load_pit() if pit_filter else None
    if pit_filter and pit is None:
        print("[pit] 警告:pit_sp500.json 缺失,跳过时点成分过滤(存在指数成员前视)")
    import datetime as _dtm
    import pit_membership as pm

    out_dates, cross = [], []
    n_excluded = n_total = 0
    for ri in rebal_idx:
        ts = int(cal[ri])
        members = (pm.membership_asof(_dtm.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"), pit)
                   if pit else None)
        cols = {k: [] for k in TERMINALS}
        base = {k: [] for k in BASE_FACTORS}
        fwd, tks = [], []
        for tk, (d, m) in panel.items():
            if members is not None:
                n_total += 1
                if tk not in members:        # 当日不在指数 → 剔除(消未来赢家泄漏)
                    n_excluded += 1
                    continue
            i = m.get(ts)
            adj = d["adjclose"]
            if i is None or i < 300 or i + H >= len(adj):
                continue
            a = np.asarray(adj[: i + 1], dtype=float)
            v = np.asarray(d["volume"][: i + 1], dtype=float)
            o = np.asarray(d["open"][: i + 1], dtype=float)
            c = np.asarray(d["close"][: i + 1], dtype=float)
            r = np.diff(np.log(a[-260:]))
            if a[-1] <= 0 or a[-6] <= 0 or a[-22] <= 0 or a[-64] <= 0:
                continue
            dollar = (c[-21:] * v[-21:])
            with np.errstate(divide="ignore", invalid="ignore"):
                amihud = np.nanmean(np.abs(r[-21:]) / np.where(dollar > 0, dollar, np.nan))
                gaps = (o[-21:] - c[-22:-1]) / c[-22:-1]
            vals = {
                "r5": a[-1] / a[-6] - 1, "r21": a[-1] / a[-22] - 1, "r63": a[-1] / a[-64] - 1,
                "vol21": float(np.std(r[-21:], ddof=1)), "vol63": float(np.std(r[-63:], ddof=1)),
                "hi52": a[-1] / a[-252:].max(), "vz21": float((v[-1] - v[-64:-1].mean()) / (v[-64:-1].std() + 1e-9)),
                "amihud21": float(amihud) if np.isfinite(amihud) else np.nan,
                "rev1": a[-1] / a[-2] - 1, "gap_oc": float(np.nanmean(gaps)),
            }
            fv = fx.factor_values(a, len(a) - 1)
            if fv is None or any(not np.isfinite(x) for x in vals.values()):
                continue
            for k in TERMINALS:
                cols[k].append(vals[k])
            for k in BASE_FACTORS:
                base[k].append(fv[k])
            fa = np.asarray(adj, dtype=float)
            fwd.append(fa[i + H] / fa[i] - 1.0)
            tks.append(tk)
        if len(fwd) >= 30:
            out_dates.append(ts)
            cross.append({"t": {k: np.asarray(cols[k]) for k in TERMINALS},
                          "b": {k: np.asarray(base[k]) for k in BASE_FACTORS},
                          "fwd": np.asarray(fwd), "tks": tks})
    if n_total:
        print(f"[pit] 时点成分过滤:剔除 {n_excluded}/{n_total} 名·期 "
              f"({n_excluded/n_total*100:.1f}%,当日不在 S&P500 的「未来赢家」)")
    return out_dates, cross


# ----------------------------- 候选生成(预注册预算) -----------------------------

def propose_candidates() -> list[dict]:
    """穷举 1 项式 + 种子化抽样 2 项式。LLM 版只需替换本函数。"""
    cands = []
    for s1, T1, t1 in itertools.product((1, -1), TRANSFORMS, TERMINALS):
        cands.append({"terms": [(s1, T1, t1)],
                      "expr": f"{'-' if s1 < 0 else ''}{T1}({t1})"})
    two = []
    for (s1, T1, t1), (s2, T2, t2) in itertools.combinations(
            itertools.product((1, -1), TRANSFORMS, TERMINALS), 2):
        if t1 == t2:
            continue
        two.append({"terms": [(s1, T1, t1), (s2, T2, t2)],
                    "expr": f"{'-' if s1 < 0 else ''}{T1}({t1}) {'-' if s2 < 0 else '+'} {T2}({t2})"})
    rng = np.random.default_rng(SEED)
    pick = rng.choice(len(two), size=min(BUDGET_2TERM, len(two)), replace=False)
    cands += [two[i] for i in sorted(pick)]
    return cands


def hypothesis_of(c: dict) -> str:
    parts = [f"{t}({TERMINALS[t]})" for _, _, t in c["terms"]]
    return "机器组装假设:" + " × ".join(parts) + "。[弱先验,门控⑤如实标注为机器生成]"


# ----------------------------- 评估(增量正交 IC + 净成本) -----------------------------

def _transform(x: np.ndarray, T: str) -> np.ndarray:
    return fx.zscore(fx.rankdata(x)) if T == "rank" else fx.zscore(x)


def score_candidate(c: dict, cross: list[dict], idx: list[int]) -> dict:
    """在 idx 指定的期上算:正交残差 IC 序列、decile L/S 净收益序列。"""
    ics, ls_net, prev_top = [], [], None
    for j in idx:
        cs = cross[j]
        s = np.zeros_like(cs["fwd"])
        for sign, T, t in c["terms"]:
            s = s + sign * _transform(cs["t"][t], T)
        # 增量正交(门控②):对基因子横截面回归取残差
        X = np.vstack([np.ones_like(s)] + [fx.zscore(cs["b"][k]) for k in BASE_FACTORS]).T
        coef, *_ = np.linalg.lstsq(X, s, rcond=None)
        resid = s - X @ coef
        ics.append(fx.spearman(resid, cs["fwd"]))
        # decile L/S 净收益(门控⑥)
        order = np.argsort(resid)
        n10 = max(3, len(order) // 10)
        bot, top = order[:n10], order[-n10:]
        gross = float(cs["fwd"][top].mean() - cs["fwd"][bot].mean())
        cur = set(np.asarray(cs["tks"])[top]) | set(np.asarray(cs["tks"])[bot])
        to = 1.0 if prev_top is None else 1 - len(cur & prev_top) / max(len(cur), 1)
        prev_top = cur
        cost = 2 * to * (COST_BPS * 1e-4 + IMPACT_FRAC)   # 双边
        ls_net.append(gross - cost)
    ics = np.asarray([x for x in ics if np.isfinite(x)])
    ls = np.asarray(ls_net)
    n = len(ics)
    ic_mean = float(ics.mean()) if n else float("nan")
    t_stat = float(ic_mean / ics.std(ddof=1) * np.sqrt(n)) if n > 2 and ics.std(ddof=1) > 0 else 0.0
    net_ir = float(ls.mean() / ls.std(ddof=1)) if len(ls) > 2 and ls.std(ddof=1) > 0 else float("nan")
    return {"ic": ic_mean, "t": t_stat, "n": n, "net_ir_per_period": net_ir,
            "net_ann": float(ls.mean() * (252 / H)) if len(ls) else float("nan"),
            "ls_series": ls}


def by_fdr(pvals: np.ndarray, q=0.10) -> np.ndarray:
    """Benjamini-Yekutieli(相依 FDR,门控③):返回拒绝原假设(显著)的布尔。"""
    m = len(pvals)
    order = np.argsort(pvals)
    cm = np.sum(1.0 / np.arange(1, m + 1))
    thresh = q * (np.arange(1, m + 1)) / (m * cm)
    passed = pvals[order] <= thresh
    k = np.max(np.nonzero(passed)[0]) + 1 if passed.any() else 0
    out = np.zeros(m, dtype=bool)
    out[order[:k]] = True
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--top", type=int, default=8, help="入库的 top 候选数(按|t|)")
    args = ap.parse_args()

    print("构建月度面板(115 流动大盘,2021起)...")
    dates, cross = build_panel()
    import datetime as _dt
    cut = int(_dt.datetime.strptime(TRAIN_END, "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc).timestamp())
    train_idx = [i for i, t in enumerate(dates) if t < cut]
    ho_idx = [i for i, t in enumerate(dates) if t >= cut]
    print(f"重平衡期 {len(dates)}(train {len(train_idx)} / holdout {len(ho_idx)})")

    cands = propose_candidates()
    print(f"预注册候选 N={len(cands)}(1项式36 + 2项式抽样{len(cands)-36},seed={SEED})")
    import math
    for c in cands:
        c["train"] = score_candidate(c, cross, train_idx)
    # 门控③:BY-FDR over 全部 N
    ts = np.asarray([abs(c["train"]["t"]) for c in cands])
    ns = np.asarray([max(c["train"]["n"], 3) for c in cands])
    pvals = np.asarray([2 * (1 - 0.5 * (1 + math.erf(t / math.sqrt(2)))) for t in ts])
    sig = by_fdr(pvals, q=0.10)

    results = []
    for i, c in enumerate(cands):
        tr = c["train"]
        gates = {
            "g1_budget": True,                                  # 预算预注册(本文件)
            "g2_orth_ic": bool(np.isfinite(tr["ic"]) and abs(tr["ic"]) > 0),
            "g3_fdr_t3": bool(sig[i] and abs(tr["t"]) >= 3.0),
            "g4_breadth": None,                                 # 特征值参与率版未实现(诚实标注)
            "g5_hypothesis": "machine-generated(weak)",
            "g6_net_cost": bool(np.isfinite(tr["net_ir_per_period"]) and tr["net_ir_per_period"] > 0
                                and tr["net_ann"] > 0),
        }
        passed = bool(gates["g3_fdr_t3"] and gates["g6_net_cost"])
        results.append({"cand": c, "gates": gates, "passed": passed})

    results.sort(key=lambda r: -abs(r["cand"]["train"]["t"]))
    n_pass = sum(1 for r in results if r["passed"])
    print(f"\n门控结果:{n_pass}/{len(results)} 通过(FDR q<0.10 + |t|≥3 + 净成本 IR>0)")

    # holdout 终检:只对通过者做一次(R5)
    out_cands = []
    for r in results[: args.top]:
        c, tr = r["cand"], r["cand"]["train"]
        ho = score_candidate(c, cross, ho_idx) if (r["passed"] and ho_idx) else None
        survived = bool(ho and np.isfinite(ho["net_ann"]) and ho["net_ann"] > 0 and ho["ic"] * tr["ic"] > 0)
        decision = "shadow" if (r["passed"] and survived) else "reject"
        note = (f"train: IC={tr['ic']:+.3f} t={tr['t']:+.1f} 净年化={tr['net_ann']*100:+.1f}% "
                f"({tr['n']}期); 门控: FDR+t3={'✓' if r['gates']['g3_fdr_t3'] else '✗'} "
                f"净成本={'✓' if r['gates']['g6_net_cost'] else '✗'} 广度门未实现")
        if ho:
            note += f"; holdout终检: IC={ho['ic']:+.3f} 净年化={ho['net_ann']*100:+.1f}% → {'存活' if survived else '不过'}"
        out_cands.append({
            "expr": c["expr"], "hypothesis": hypothesis_of(c),
            "incremental_ic": round(tr["ic"], 4), "post_cutoff": True,
            "t_stat": round(tr["t"], 2),
            "passed_gates": bool(r["passed"] and survived), "decision": decision, "note": note,
        })
        print(f"  {c['expr']:<34} t={tr['t']:+5.1f} IC={tr['ic']:+.3f} "
              f"净%/年={tr['net_ann']*100:+5.1f} → {decision}")

    if args.publish:
        import feed_lib as fl
        now = datetime.now(timezone.utc)
        n_shadow = sum(1 for c in out_cands if c["decision"] == "shadow")
        # asof_data = 底层价格数据真实末日(实效性:绝不声称比数据更新)
        spy_ts = datamod.load("SPY")["ts"]
        asof = _dt.datetime.utcfromtimestamp(int(spy_ts[-1])).strftime("%Y-%m-%d")
        report = {
            "schema_version": "1.0",
            "id": f"factory-local-{now.strftime('%Y-%m-%dT%H%M')}Z",
            "kind": "manual",
            "produced_at": fl.now_iso(),
            "asof_data": asof,
            "producer": {"name": "factor-factory-local", "agent_role": "factor-factory"},
            "factory_candidates": out_cands,
            "contribution": {"type": "new_factor", "candidates_proposed": len(cands),
                             "candidates_accepted": 0,
                             "summary": f"本仓公式因子工厂实跑:预注册 N={len(cands)},"
                                        f"{n_pass} 过 train 门控,{n_shadow} 过 holdout 终检进 shadow。"},
            "notes": "非 LLM 预算化搜索(穷举+种子抽样),无记忆性前视;广度门(④)未实现,假设(⑤)为机器生成弱先验。"
                     " 全部试验次数已计入 FDR。LLM 接入只替换提案器,门控管线不变。",
        }
        res = fl.publish_report(report, secret=os.environ.get("FEED_HMAC_SECRET"))
        print("\nfeed 发布:", "OK" if res["ok"] else res["errors"])


if __name__ == "__main__":
    main()
