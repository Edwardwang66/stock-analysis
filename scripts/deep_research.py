#!/usr/bin/env python3
"""Deep Research 引擎 —— 把 feed/ 里已有的确定性证据自动立题、并发取证、对抗验证,产出可审计研究简报。

流程(四段,全部确定性;不调用 LLM、不访问网络):
  ① 立题     题库写在代码里(每个 lens 一题),按「依赖在场」逐题接纳;
             缺输入的问题降级为 open_question(记原因与缺哪个字段),不静默丢弃。
             这一步是筛选,不是生成:题目本身只随代码变。
  ② 并发取证 每题派给一个委员会角色 lens(engine / residual-analyst / crowding-monitor /
             event-risk / factor-factory / risk),stdlib ThreadPoolExecutor 并发跑;
             每条结论必须带证据链(工件 + 字段 + 取值 + asof),数值必须有来源(R6)。
  ③ 对抗验证 red-team 对每条结论逐条跑确定性反驳器:missing-evidence / insufficient-sample /
             stale-evidence / within-noise-band / future-asof / contradicted。
             只有 confirmed 进 findings;refuted 与 unverified 全量留档,不删证。
  ④ 合成     简报 + 未答问题 + 下一步动作 + 逐工件覆盖度台账。

产出:
  feed/research/<id>.json     研究简报(schema: feed/schema/research.schema.json,可选 HMAC 签名)
  feed/research/index.json    简报索引 + 未答问题滚动清单(/intel「深度研究」卡片数据源)
  feed 报告(kind=routine)     只带 alerts + contribution + notes(刻意不带 market_state / book,
                              以免覆盖引擎写的 feed/market/state.json 与 feed/signals/latest.json)

用法: python scripts/deep_research.py [--publish] [--brief-only] [--roles engine,risk]
                                      [--workers 8] [--report-limit 120] [--quiet]
环境变量: DEEP_RESEARCH_WORKERS 覆盖并发数;DEEP_RESEARCH_ROLES 覆盖角色白名单(逗号分隔,空=全部);
          FEED_HMAC_SECRET 设置则签名;FEED_PUBLICATION_MANIFEST 设置则记录写入路径供 stager 暂存。
设计:纯 stdlib;任何 lens 失败只丢该题(记 lens-error),不影响其余;confirmed 只意味着
     「对已记录数据的可复现计算成立」,不是分析正确性证明,也不是投资建议。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402

TAG = "[dr]"

# 委员会角色词表 —— 全部取自仓库既有用法:scripts/openclaw_client.py 的 ROLES、
# feed/schema/report.schema.json 的 producer.agent_role 描述,以及 routine/factory 报告的实际取值。
ROLES = (
    "engine",
    "residual-analyst",
    "crowding-monitor",
    "event-risk",
    "factor-factory",
    "risk",
    "red-team",
)
VERIFIER_ROLE = "red-team"

DEFAULT_WORKERS = 8
MAX_WORKERS = 32
DEFAULT_REPORT_LIMIT = 120
MAX_ALERTS = 12
MAX_NEXT_ACTIONS = 20

FATAL_REFUTATIONS = frozenset(
    {"missing-evidence", "insufficient-sample", "within-noise-band", "future-asof", "contradicted"}
)

# 工件 -> (feed 相对路径, 权威时间字段候选)。本仓没有统一的 asof 字段名,必须逐族声明。
ARTIFACTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "index": ("index.json", ("updated_at",)),
    "health": ("health.json", ("checked_at",)),
    "market_state": ("market/state.json", ("asof_data", "updated_at")),
    "market_history": ("market/history.json", ("date",)),
    "signals_book": ("signals/latest.json", ("asof",)),
    "rs_ranks": ("signals/rs-ranks.json", ("date",)),
    "chan_stats": ("signals/chan-stats.json", ("generated_at",)),
    "screener": ("screener/latest.json", ("date",)),
    "screener_scores": ("screener/scores.json", ("date",)),
    "screener_history": ("screener/history.json", ("date",)),
    "notes_index": ("stock-notes/index.json", ("updated_at",)),
    "stance_history": ("stock-notes/stance-history.json", ("date",)),
    "candidates": ("factory/candidates.json", ("updated_at",)),
    "funds": ("funds/situational-awareness.json", ("asof",)),
    "crypto": ("crypto/state.json", ("updated_at",)),
    "intraday": ("intraday/latest.json", ("at",)),
    "overnight": ("intraday/overnight.json", ("date",)),
}

REPORT_PREFIXES = ("routine-", "factory-local-", "hl-monitor-", "openclaw-")

# 龄期超过此天数的工件会进入 next_actions(与 audit_feed.py 的 SLA 同量级,但这里只提建议不判 critical)。
AGING_DAYS = 3.0
QUARTERLY_KEYS = frozenset({"funds"})

NOTES = (
    "确定性引擎:未调用任何 LLM 或外部服务,不访问网络,只对仓库内已记录的 feed 工件做可复现计算"
    "(deterministic logic and does not require an external LLM provider)。"
    "confirmed 表示「计算在已记录数据上成立」,不表示分析正确、不表示门控通过、不构成投资建议;"
    "schema 校验不批准研究语义。refuted / unverified 全量留档,缺答案的问题写进 open_questions。"
    "注意 stale-evidence 反驳器按运行时刻算龄期:同一份 feed 在更晚的日期重跑,时效相关的裁决"
    "会变(其余反驳器与所有数值都只取决于 feed 内容)。"
    "所有结论只描述本仓自由公开数据(存在生存者偏差与不完整),铁律(R6):LLM 是研究放大器、不决策;"
    "数值必须有来源;不编造。"
)


# ----------------------------- 数值 / 统计工具(纯 stdlib)-----------------------------

def _num(x: object, nd: int = 6) -> float | None:
    """转成 JSON 可写的有限浮点;NaN/inf/非数一律 None(fl.save_json 用 allow_nan=False)。"""
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return round(v, nd)


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman 秩相关(含并列均秩);样本 <3 或任一侧无方差时返回 None,绝不返回 nan。"""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return None
    return _num(num / (dx * dy), 4)


def ols_slope(ys: list[float]) -> float | None:
    """以 0..n-1 为自变量的最小二乘斜率(每期变化量);样本 <3 返回 None。"""
    n = len(ys)
    if n < 3:
        return None
    xs = list(range(n))
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return _num(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den, 6)


def _date_of(value: object) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    head = value[:10]
    return head if re.fullmatch(r"\d{4}-\d{2}-\d{2}", head) else None


def _age_days(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    age = fl._days_since(value)
    return None if age is None else round(age, 2)


def _dig(obj: object, *path: str) -> object:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


# ----------------------------- 证据 / 结论 / 反驳 -----------------------------

def ev(artifact: str, field: str, value: object = None, asof: object = None) -> dict:
    """一条证据。value 缺失请显式写 "absent" —— None 会被 missing-evidence 反驳器判为无证据。"""
    if isinstance(value, float):
        value = _num(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)[:200]
    return {"artifact": artifact, "field": field, "value": value,
            "asof": asof if isinstance(asof, str) else None}


def claim(
    role: str,
    question: str,
    statement: str,
    *,
    metric: str | None = None,
    value: object = None,
    unit: str = "none",
    direction: str = "none",
    n: int | None = None,
    min_n: int = 0,
    noise_band: float | None = None,
    max_age_days: float | None = 10.0,
    severity: str = "none",
    cites: tuple[str, ...] = (),
    evidence: tuple[dict, ...] = (),
) -> dict:
    if isinstance(value, float):
        value = _num(value)
    out: dict = {
        "id": "",
        "role": role,
        "question": question,
        "statement": statement,
        "unit": unit,
        "direction": direction,
        "n": n,
        "min_n": min_n,
        "noise_band": _num(noise_band) if noise_band is not None else None,
        "max_age_days": _num(max_age_days) if max_age_days is not None else None,
        "severity": severity,
        "cites": list(cites),
        "evidence": list(evidence),
        "verdict": "confirmed",
        "refutations": [],
    }
    if metric is not None:
        out["metric"] = metric
    out["value"] = value
    # 省掉没有信息的可选键(schema 只要求 id/role/statement/verdict):
    # 每个简报 30+ 条结论,写满 null 会把工件体积撑大一倍而不增加任何可读信息。
    for key in ("n", "noise_band", "max_age_days"):
        if out[key] is None:
            del out[key]
    if out["min_n"] == 0:
        del out["min_n"]
    if out["severity"] == "none":
        del out["severity"]
    if out["direction"] == "none":
        del out["direction"]
    if out["unit"] == "none":
        del out["unit"]
    if not out["cites"]:
        del out["cites"]
    return out


def _refute_one(c: dict, today: str) -> list[dict]:
    refs: list[dict] = []
    evidence = c.get("evidence") or []
    if not evidence:
        refs.append({"code": "missing-evidence", "message": "结论未给出任何证据条目"})
    for item in evidence:
        if item.get("value") is None:
            refs.append({
                "code": "missing-evidence",
                "message": f"证据 {item.get('artifact')}:{item.get('field')} 取值缺失",
            })
            break
    min_n = c.get("min_n") or 0
    if min_n and isinstance(c.get("n"), int) and c["n"] < min_n:
        refs.append({"code": "insufficient-sample", "message": f"样本 n={c['n']} < 门槛 {min_n}"})
    band = c.get("noise_band")
    value = c.get("value")
    if band is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
        if abs(float(value)) < float(band):
            refs.append({
                "code": "within-noise-band",
                "message": f"|{_num(value)}| < 噪声带 {band},不足以与「无效应」区分",
            })
    for item in evidence:
        asof = _date_of(item.get("asof"))
        if asof and asof > today:
            refs.append({
                "code": "future-asof",
                "message": f"证据 {item.get('artifact')} 声称 asof={asof} 晚于今日 {today}",
            })
            break
    cap = c.get("max_age_days")
    if cap is not None:
        ages = [a for a in (_age_days(item.get("asof")) for item in evidence) if a is not None]
        if ages and max(ages) > float(cap):
            refs.append({
                "code": "stale-evidence",
                "message": f"最旧证据已 {max(ages)} 天,超过本结论声明的 {cap} 天时效上限",
            })
    return refs


def verify(claims: list[dict], today: str) -> list[dict]:
    """red-team 阶段:逐条反驳 + 跨条互相矛盾检测,写回 verdict / refutations。"""
    by_metric: dict[str, list[dict]] = {}
    for c in claims:
        c["refutations"] = _refute_one(c, today)
        metric = c.get("metric")
        if metric:
            by_metric.setdefault(metric, []).append(c)
    for metric, group in by_metric.items():
        directions = {c.get("direction") for c in group if c.get("direction") in ("up", "down")}
        if len(directions) > 1:
            for c in group:
                c["refutations"].append({
                    "code": "contradicted",
                    "message": f"同一度量 {metric} 上存在方向相反的结论,双方一并判反驳",
                })
    for c in claims:
        codes = {r["code"] for r in c["refutations"]}
        if codes & FATAL_REFUTATIONS:
            c["verdict"] = "refuted"
        elif codes:
            c["verdict"] = "unverified"
        else:
            c["verdict"] = "confirmed"
    return claims


# ----------------------------- 语料(只读 feed/)-----------------------------

class LensSkipped(Exception):
    """lens 无法运行:缺输入或样本不足。降级为 open_question,不当成失败。"""

    def __init__(self, reason: str, missing: tuple[str, ...] = (), detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.missing = list(missing)
        self.detail = detail


class Corpus:
    """一次运行的只读语料 + 逐工件覆盖度台账。"""

    def __init__(self, report_limit: int = DEFAULT_REPORT_LIMIT) -> None:
        self.report_limit = max(1, report_limit)
        self._data: dict[str, object] = {}
        self.provenance: list[dict] = []
        self.reports: dict[str, list[dict]] = {p: [] for p in REPORT_PREFIXES}
        self.reports_scanned = 0
        self._load_artifacts()
        self._load_reports()

    # -- 读取 --------------------------------------------------------------
    def _load_artifacts(self) -> None:
        for key, (rel, fields) in ARTIFACTS.items():
            entry: dict = {"key": key, "path": f"feed/{rel}", "exists": False,
                           "asof": None, "age_days": None}
            try:
                data = fl.load_json(os.path.join(fl.FEED, rel))
            except Exception as exc:  # noqa: BLE001  单个工件损坏不应中断整轮取证
                data = None
                entry["error"] = f"{type(exc).__name__}: {exc}"
                print(f"  ! {rel}: {exc}", file=sys.stderr)
            if data is not None:
                self._data[key] = data
                entry["exists"] = True
                entry["asof"] = self._asof(data, fields)
                entry["age_days"] = _age_days(entry["asof"])
            self.provenance.append(entry)

    @staticmethod
    def _asof(data: object, fields: tuple[str, ...]) -> str | None:
        head = data[-1] if isinstance(data, list) and data else data
        if not isinstance(head, dict):
            return None
        for field in fields:
            value = head.get(field)
            if isinstance(value, str) and value:
                return value
        return None

    def _load_reports(self) -> None:
        rdir = os.path.join(fl.FEED, "reports")
        try:
            names = sorted(os.listdir(rdir))
        except OSError as exc:
            print(f"  ! feed/reports 无法枚举: {exc}", file=sys.stderr)
            return
        for prefix in REPORT_PREFIXES:
            group = [n for n in names if n.startswith(prefix) and n.endswith(".json")]
            for name in group[-self.report_limit:]:
                try:
                    report = fl.load_json(os.path.join(rdir, name))
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! reports/{name}: {exc}", file=sys.stderr)
                    continue
                if not isinstance(report, dict):
                    continue
                engine = report.get("engine")
                if isinstance(engine, dict):
                    engine.pop("equity_curve", None)   # 350 点净值曲线本轮不用,尽早释放
                report["_file"] = f"feed/reports/{name}"
                self.reports[prefix].append(report)
                self.reports_scanned += 1
            self.reports[prefix].sort(key=lambda r: str(r.get("produced_at") or ""))

    # -- 访问 --------------------------------------------------------------
    def get(self, key: str) -> object:
        return self._data.get(key)

    def require(self, *keys: str) -> tuple:
        missing = [f"feed/{ARTIFACTS[k][0]}" for k in keys if k not in self._data]
        if missing:
            raise LensSkipped("missing-input", tuple(missing),
                              "取证所需工件不可读:" + ", ".join(missing))
        return tuple(self._data[k] for k in keys)

    def prov(self, key: str) -> dict:
        for entry in self.provenance:
            if entry["key"] == key:
                return entry
        return {"key": key, "path": "?", "exists": False, "asof": None, "age_days": None}

    def asof(self, key: str) -> str | None:
        return self.prov(key).get("asof")

    def engine_days(self) -> list[dict]:
        """按 asof_data 去重的引擎报告(同日多份取 produced_at 最大),升序。

        必须去重:同一 asof_data 会有多份 routine 报告,net.sharpe 只在末位小数不同,
        直接拿全量做时间序列会把「同日重复」当成「多期观测」。
        """
        best: dict[str, dict] = {}
        for report in self.reports["routine-"]:
            engine = report.get("engine")
            asof = _date_of(report.get("asof_data"))
            if not isinstance(engine, dict) or not asof:
                continue
            prior = best.get(asof)
            if prior is None or str(report.get("produced_at") or "") > str(prior.get("produced_at") or ""):
                best[asof] = report
        return [best[k] for k in sorted(best)]

    def latest_engine(self) -> dict | None:
        days = self.engine_days()
        return days[-1] if days else None


# ----------------------------- lens 注册 -----------------------------

LENSES: list[dict] = []


def lens(*, qid: str, role: str, title: str, needs: tuple[str, ...], test: str, triggered_by: str):
    def deco(fn):
        LENSES.append({"id": qid, "role": role, "title": title, "needs": list(needs),
                       "test": test, "triggered_by": triggered_by, "fn": fn})
        return fn
    return deco


# ---- engine:净·扣成本是唯一计价货币(R4)-------------------------------------

@lens(
    qid="q-cost-vs-signal",
    role="engine",
    title="毛口径有信号而净·扣成本为负,是成本吃掉了信号吗?",
    needs=("feed/reports/routine-*.json:engine.gross.sharpe",
           "feed/reports/routine-*.json:engine.net.sharpe",
           "feed/reports/routine-*.json:engine.cost_drag_ann",
           "feed/reports/routine-*.json:engine.turnover.ann_2way"),
    test="统计 gross.sharpe>0 且 net.sharpe<=0 的交易日占比;算最新一期盈亏平衡成本 = gross.ann_return - net.ann_return;"
         "并对 turnover.ann_2way 与 cost_drag_ann 做 Spearman(机械关系应接近 1)。",
    triggered_by="feed/reports 存在带 engine 段的 routine 报告。",
)
def lens_cost_vs_signal(corpus: Corpus) -> list[dict]:
    days = corpus.engine_days()
    if not days:
        raise LensSkipped("missing-input", ("feed/reports/routine-*.json:engine",),
                          "没有任何带 engine 段的 routine 报告。")
    q = "q-cost-vs-signal"
    out: list[dict] = []

    flips = 0
    graded = 0
    turns: list[float] = []
    drags: list[float] = []
    for report in days:
        gross = _num(_dig(report, "engine", "gross", "sharpe"))
        net = _num(_dig(report, "engine", "net", "sharpe"))
        if gross is not None and net is not None:
            graded += 1                       # 分母只数两个口径都读到的日子
            if gross > 0 >= net:
                flips += 1
        turn = _dig(report, "engine", "turnover", "ann_2way")
        drag = _dig(report, "engine", "cost_drag_ann")
        if isinstance(turn, (int, float)) and isinstance(drag, (int, float)):
            turns.append(float(turn))         # 相关性用原值,不先舍入(舍入会造人为并列)
            drags.append(float(drag))
    if not graded:
        raise LensSkipped("missing-input", ("feed/reports/routine-*.json:engine.net.sharpe",),
                          "没有任何一期同时带毛/净 Sharpe。")
    share = _num(flips / graded)
    latest = days[-1]
    lf = latest["_file"]
    la = _date_of(latest.get("asof_data"))
    out.append(claim(
        "engine", q,
        f"{graded} 个同时带毛/净口径的去重交易日中有 {flips} 日(占 {share:.0%})毛 Sharpe 为正"
        f"而净·扣成本 Sharpe ≤ 0"
        + (":这些日子的问题不是没有信号,而是信号扛不住成本(R4 净口径为唯一计价货币)。"
           if flips else
           ":本段样本上没有出现「毛正净负」的日子,成本没有在这段区间里翻转结论(R4)。"),
        metric="engine.sharpe.gross_positive_net_nonpositive.share",
        value=share, unit="fraction", direction="none", n=graded, min_n=10,
        severity="warning" if (share or 0) >= 0.5 else "info", cites=("R4",),
        evidence=(ev(lf, "engine.gross.sharpe", _dig(latest, "engine", "gross", "sharpe"), la),
                  ev(lf, "engine.net.sharpe", _dig(latest, "engine", "net", "sharpe"), la)),
        max_age_days=None,
    ))

    gross_ret = _num(_dig(latest, "engine", "gross", "ann_return"))
    net_ret = _num(_dig(latest, "engine", "net", "ann_return"))
    if gross_ret is not None and net_ret is not None:
        out.append(claim(
            "engine", q,
            f"最新一期({la})的成本负担 = 毛年化 {gross_ret:+.4f} − 净年化 {net_ret:+.4f} = "
            f"{gross_ret - net_ret:.4f}(年化分数),报告自报 cost_drag_ann="
            f"{_num(_dig(latest, 'engine', 'cost_drag_ann'))}。",
            metric="engine.cost.breakeven_ann",
            value=gross_ret - net_ret, unit="fraction", direction="none", n=None,
            severity="info", cites=("R4",),
            evidence=(ev(lf, "engine.gross.ann_return", gross_ret, la),
                      ev(lf, "engine.net.ann_return", net_ret, la),
                      ev(lf, "engine.cost_drag_ann", _dig(latest, "engine", "cost_drag_ann"), la)),
        ))

    rho = spearman(turns, drags)
    if rho is not None:
        out.append(claim(
            "engine", q,
            f"Spearman(turnover.ann_2way, cost_drag_ann)={rho:+.3f}(n={len(turns)}):"
            + ("成本项与换手强同向,与「成本随换手放大」一致;这是秩相关,不是因果证明。"
               if rho >= 0.7 else
               "成本项与换手同向但不强,单看换手不足以解释成本。" if rho > 0 else
               "成本项与换手不同向,把成本当换手的函数解读会出错。"),
            metric="engine.turnover_vs_cost.spearman",
            value=rho, unit="ratio", direction="up" if rho > 0 else "down",
            n=len(turns), min_n=10, noise_band=0.3, severity="info", cites=("R4",),
            evidence=(ev(lf, "engine.turnover.ann_2way", turns[-1], la),
                      ev(lf, "engine.cost_drag_ann", drags[-1], la)),
            max_age_days=None,
        ))
    return out


@lens(
    qid="q-holdout-degradation",
    role="engine",
    title="train 到真 holdout 的衰减在扩大还是收敛?",
    needs=("feed/reports/routine-*.json:engine.train.sharpe",
           "feed/reports/routine-*.json:engine.holdout.sharpe"),
    test="按 asof 去重后取 holdout.sharpe − train.sharpe 序列,报最新差值与最小二乘斜率(每期变化)。",
    triggered_by="routine 报告同时带 engine.train 与 engine.holdout 段。",
)
def lens_holdout_degradation(corpus: Corpus) -> list[dict]:
    q = "q-holdout-degradation"
    gaps: list[float] = []
    rows: list[dict] = []
    for report in corpus.engine_days():
        train = _num(_dig(report, "engine", "train", "sharpe"))
        hold = _num(_dig(report, "engine", "holdout", "sharpe"))
        if train is None or hold is None:
            continue
        gaps.append(hold - train)
        rows.append(report)
    if len(gaps) < 3:
        raise LensSkipped("insufficient-sample", ("feed/reports/routine-*.json:engine.holdout.sharpe",),
                          f"只有 {len(gaps)} 期同时带 train 与 holdout,无法给趋势。")
    latest, la = rows[-1], _date_of(rows[-1].get("asof_data"))
    lf = latest["_file"]
    slope = ols_slope(gaps)
    out = [claim(
        "engine", q,
        f"最新一期 holdout 相对 train 的 Sharpe 差为 {gaps[-1]:+.4f}"
        f"(train {_num(_dig(latest, 'engine', 'train', 'sharpe'))} → holdout "
        f"{_num(_dig(latest, 'engine', 'holdout', 'sharpe'))});"
        f"holdout 起点 {_dig(latest, 'engine', 'holdout', 'start')} 是回顾式指定的切点,"
        f"按 R5 不能当预注册真 holdout 解读。",
        metric="engine.holdout_minus_train.latest",
        value=gaps[-1], unit="ratio", direction="down" if gaps[-1] < 0 else "up",
        n=len(gaps), min_n=3, severity="info", cites=("R5",),
        evidence=(ev(lf, "engine.train.sharpe", _dig(latest, "engine", "train", "sharpe"), la),
                  ev(lf, "engine.holdout.sharpe", _dig(latest, "engine", "holdout", "sharpe"), la),
                  ev(lf, "engine.holdout.start", _dig(latest, "engine", "holdout", "start"), la)),
        max_age_days=None,
    )]
    if slope is not None:
        out.append(claim(
            "engine", q,
            f"该差值在 {len(gaps)} 期上的最小二乘斜率为 {slope:+.6f}/期:"
            f"{'衰减在扩大' if slope < 0 else '衰减在收敛'},但窗口只有 {len(gaps)} 期,不能外推。",
            metric="engine.holdout_minus_train.slope",
            value=slope, unit="ratio", direction="down" if slope < 0 else "up",
            n=len(gaps), min_n=10, noise_band=0.0005, severity="info", cites=("R5",),
            evidence=(ev(lf, "engine.holdout.sharpe", _num(_dig(latest, "engine", "holdout", "sharpe")), la),
                      ev(rows[0]["_file"], "engine.holdout.sharpe",
                         _num(_dig(rows[0], "engine", "holdout", "sharpe")),
                         _date_of(rows[0].get("asof_data")))),
            max_age_days=None,
        ))
    return out


@lens(
    qid="q-dsr-falsification",
    role="engine",
    title="DSR 过拟合校验是否已经否掉了引擎自己?",
    needs=("feed/reports/routine-*.json:engine.deflated_sharpe.dsr",
           "feed/reports/routine-*.json:engine.deflated_sharpe.p_value",
           "feed/reports/routine-*.json:engine.deflated_sharpe.n_trials"),
    test="统计 dsr<0.05 且 p_value>0.95 的期数占比;并检查 n_trials 是否在候选账本增长时保持常数。",
    triggered_by="routine 报告带 engine.deflated_sharpe 段。",
)
def lens_dsr(corpus: Corpus) -> list[dict]:
    q = "q-dsr-falsification"
    hits = 0
    trials: set[int] = set()
    rows: list[dict] = []
    for report in corpus.engine_days():
        dsr = _num(_dig(report, "engine", "deflated_sharpe", "dsr"))
        pval = _num(_dig(report, "engine", "deflated_sharpe", "p_value"))
        if dsr is None or pval is None:
            continue
        rows.append(report)
        if dsr < 0.05 and pval > 0.95:
            hits += 1
        nt = _dig(report, "engine", "deflated_sharpe", "n_trials")
        if isinstance(nt, int):
            trials.add(nt)
    if not rows:
        raise LensSkipped("missing-input", ("feed/reports/routine-*.json:engine.deflated_sharpe",),
                          "没有报告带 deflated_sharpe 段。")
    latest, la = rows[-1], _date_of(rows[-1].get("asof_data"))
    lf = latest["_file"]
    share = _num(hits / len(rows))
    out = [claim(
        "engine", q,
        f"{len(rows)} 期中有 {hits} 期(占 {share:.0%})满足 dsr<0.05"
        f"(报告里 p_value 与 dsr 互补,两者是同一个判据的两面,不是两次独立检验),最新一期 dsr="
        f"{_num(_dig(latest, 'engine', 'deflated_sharpe', 'dsr'))}"
        + (":DSR 口径下引擎的 Sharpe 与「零真实技巧」不可区分。" if hits == len(rows) else
           f":其中 {len(rows) - hits} 期没有被 DSR 否掉,不能说该口径「一直」否定引擎。" if hits else
           ":本段样本上 DSR 没有否掉任何一期,这条否证在当前数据上不成立。"),
        metric="engine.dsr.falsified.share",
        value=share, unit="fraction", direction="none", n=len(rows), min_n=10,
        severity="warning" if (share or 0) >= 0.9 else "info", cites=("R5", "§6.7"),
        evidence=(ev(lf, "engine.deflated_sharpe.dsr", _dig(latest, "engine", "deflated_sharpe", "dsr"), la),
                  ev(lf, "engine.deflated_sharpe.p_value", _dig(latest, "engine", "deflated_sharpe", "p_value"), la)),
        max_age_days=None,
    )]
    cands = corpus.get("candidates")
    n_cands = len((cands or {}).get("candidates") or []) if isinstance(cands, dict) else 0
    if trials:
        out.append(claim(
            "engine", q,
            f"n_trials 在这 {len(rows)} 期上取 {len(trials)} 个不同值 {sorted(trials)},"
            f"而候选账本当前留存 {n_cands} 条"
            + (":试验次数是写死的常数,不随实际搜索预算变化" if len(trials) == 1 else
               ":试验次数在期间发生过变化,跨期比较 DSR 时必须按各期自己的 n_trials 解读")
            + "(门控① 要求预注册搜索空间与试验次数全部计数)。",
            metric="engine.dsr.n_trials.distinct",
            value=len(trials), unit="count", direction="flat", n=len(rows), min_n=10,
            severity="info", cites=("门控①",),
            evidence=(ev(lf, "engine.deflated_sharpe.n_trials",
                         _dig(latest, "engine", "deflated_sharpe", "n_trials"), la),
                      ev("feed/factory/candidates.json", "candidates.length", n_cands,
                         corpus.asof("candidates"))),
            max_age_days=None,
        ))
    return out


# ---- residual-analyst:残差 / 协整健康度 --------------------------------------

@lens(
    qid="q-book-mean-reversion",
    role="residual-analyst",
    title="当前持仓簿是否真的建立在均值回归上?",
    needs=("feed/signals/latest.json:positions[].hurst",
           "feed/signals/latest.json:positions[].halflife_days"),
    test="统计 hurst>=0.5(非均值回归)的仓位数与其占毛杠杆的比重;并给出半衰期分布分位。",
    triggered_by="feed/signals/latest.json 存在且带 positions。",
)
def lens_book_mean_reversion(corpus: Corpus) -> list[dict]:
    (book,) = corpus.require("signals_book")
    positions = book.get("positions") if isinstance(book, dict) else None
    if not isinstance(positions, list) or not positions:
        raise LensSkipped("missing-input", ("feed/signals/latest.json:positions",), "持仓簿为空。")
    q = "q-book-mean-reversion"
    asof = book.get("asof")
    hursts = [(p, _num(p.get("hurst"))) for p in positions if isinstance(p, dict)]
    graded = [(p, h) for p, h in hursts if h is not None]
    if not graded:
        raise LensSkipped("missing-input", ("feed/signals/latest.json:positions[].hurst",),
                          "仓位没有 hurst 字段。")
    # 分母用「全簿毛杠杆」而不是「有 hurst 那部分的毛杠杆」,否则会把占比放大。
    book_gross = sum(abs(_num(p.get("weight")) or 0.0) for p in positions if isinstance(p, dict))
    trending = [(p, h) for p, h in graded if h >= 0.5]
    trend_gross = sum(abs(_num(p.get("weight")) or 0.0) for p, _ in trending)
    share = _num(len(trending) / len(graded))
    weight_share = _num(trend_gross / book_gross) if book_gross > 0 else None
    worst = max(graded, key=lambda item: item[1])
    out = [claim(
        "residual-analyst", q,
        f"{len(graded)} 个有 hurst 的仓位里 {len(trending)} 个(占已评级仓位的 {share:.0%})hurst≥0.5,"
        f"即按自身指标不具备均值回归性"
        + (f",占全簿毛杠杆的 {weight_share:.0%};" if weight_share is not None else ";")
        + f"hurst 最高的是 {worst[0].get('ticker')}({worst[1]})。"
        + ("残差套利簿的前提是回归,这部分敞口的前提不成立(R2:协整断裂后不得按「会回归」加仓)。"
           if trending else
           "全簿都在 hurst<0.5 一侧,均值回归前提在这一期成立(R2)。"),
        metric="book.hurst_ge_0_5.share",
        value=share, unit="fraction", direction="none", n=len(graded), min_n=10,
        severity="warning" if (share or 0) >= 0.5 else "info", cites=("R2",),
        evidence=(ev("feed/signals/latest.json", f"positions[{worst[0].get('ticker')}].hurst",
                     worst[1], asof),
                  ev("feed/signals/latest.json", "positions.length", len(positions), asof),
                  ev("feed/signals/latest.json", "positions[].weight.abs_sum",
                     _num(book_gross), asof)),
    )]
    halflives = sorted(h for h in (_num(p.get("halflife_days")) for p in positions
                                   if isinstance(p, dict)) if h is not None)
    if len(halflives) >= 5:
        median = _num(statistics.median(halflives))
        out.append(claim(
            "residual-analyst", q,
            f"半衰期中位数 {median} 天(区间 {halflives[0]}–{halflives[-1]}):"
            f"这决定了簿的自然持有期,任何按更长周期解读该簿的结论都与半衰期不一致。",
            metric="book.halflife_days.median",
            value=median, unit="days", direction="none", n=len(halflives), min_n=5,
            severity="info",
            evidence=(ev("feed/signals/latest.json", "positions[].halflife_days.median", median, asof),),
        ))
    return out


@lens(
    qid="q-book-identity",
    role="residual-analyst",
    title="簿自报的毛杠杆 / 净敞口能从仓位权重复算出来吗?",
    needs=("feed/signals/latest.json:gross_leverage",
           "feed/signals/latest.json:net_exposure",
           "feed/signals/latest.json:positions[].weight"),
    test="用 sum(|weight|) 与 sum(weight) 复算,与自报值比最大绝对偏差。",
    triggered_by="feed/signals/latest.json 同时有自报口径与逐仓权重。",
)
def lens_book_identity(corpus: Corpus) -> list[dict]:
    (book,) = corpus.require("signals_book")
    positions = [p for p in (book.get("positions") or []) if isinstance(p, dict)]
    weights = [_num(p.get("weight")) for p in positions]
    if not positions or any(w is None for w in weights):
        raise LensSkipped("missing-input", ("feed/signals/latest.json:positions[].weight",),
                          "仓位权重缺失,无法复算口径。")
    asof = book.get("asof")
    recomputed_gross = _num(sum(abs(w) for w in weights))  # type: ignore[arg-type]
    recomputed_net = _num(sum(weights))                    # type: ignore[arg-type]
    stated_gross = _num(book.get("gross_leverage"))
    stated_net = _num(book.get("net_exposure"))
    if stated_gross is None or stated_net is None:
        raise LensSkipped("missing-input", ("feed/signals/latest.json:gross_leverage",),
                          "簿没有自报毛杠杆 / 净敞口。")
    diff = _num(max(abs(recomputed_gross - stated_gross), abs(recomputed_net - stated_net)))
    reproduced = (diff or 0.0) <= 0.005
    n_long = sum(1 for w in weights if w > 0)
    n_short = sum(1 for w in weights if w < 0)
    count_ok = (n_long == book.get("n_long") and n_short == book.get("n_short"))
    return [claim(
        "residual-analyst", "q-book-identity",
        (f"簿口径可复算:sum(|w|)={recomputed_gross} vs 自报 {stated_gross}、sum(w)={recomputed_net} "
         f"vs 自报 {stated_net},最大偏差 {diff};多空计数 {n_long}/{n_short} "
         f"{'与自报一致' if count_ok else '与自报不一致'}。"
         if reproduced else
         f"簿口径复算不上:sum(|w|)={recomputed_gross} vs 自报 {stated_gross}、sum(w)={recomputed_net} "
         f"vs 自报 {stated_net},最大偏差 {diff} 超过 0.005;看板显示的杠杆与逐仓权重不是同一口径。"),
        metric="book.identity.max_abs_diff",
        value=diff, unit="fraction", direction="none", n=len(positions), min_n=5,
        severity="info" if reproduced else "critical",
        evidence=(ev("feed/signals/latest.json", "gross_leverage", stated_gross, asof),
                  ev("feed/signals/latest.json", "net_exposure", stated_net, asof),
                  ev("feed/signals/latest.json", "positions[].weight.abs_sum", recomputed_gross, asof)),
    )]


@lens(
    qid="q-book-vs-breaker",
    role="residual-analyst",
    title="被熔断排除的标的有没有仍留在簿里?",
    needs=("feed/signals/latest.json:source_report",
           "feed/signals/latest.json:positions[].ticker",
           "feed/reports/routine-*.json:alerts[cointegration_breaker].tickers"),
    test="按簿自报的 source_report 定位它那一次运行的报告(不是最新报告),取该报告 "
         "cointegration_breaker 告警的 tickers 与簿内 ticker 求交集;并从告警文案解析自报总数,"
         "算出这次实际核对了名单的百分之几 —— tickers 是被截断的,交集只在公布子集上成立。",
    triggered_by="feed/signals/latest.json 带 source_report,且该报告带 cointegration_breaker 告警。",
)
def lens_book_vs_breaker(corpus: Corpus) -> list[dict]:
    (book,) = corpus.require("signals_book")
    # 必须按簿自报的 source_report 取报告,不能用 latest_engine():簿与报告是两个独立写手,
    # 簿可能仍停在上一班,此时拿最新报告的熔断名单去比对,等于把 A 轮的名单算到 B 轮的簿头上
    # ——「同一份报告」的措辞会变成假归因。两者恰好相同只是常态,不是不变量。
    source = book.get("source_report") if isinstance(book, dict) else None
    if not isinstance(source, str) or not source:
        raise LensSkipped("missing-input", ("feed/signals/latest.json:source_report",),
                          "簿没有 source_report,无法确定它是哪一次运行的产物。")
    try:
        path = fl.report_path(source)
    except ValueError as exc:
        raise LensSkipped("missing-input", ("feed/signals/latest.json:source_report",),
                          f"source_report 不是合法报告 id: {exc}") from exc
    origin = fl.load_json(path)
    if not isinstance(origin, dict):
        raise LensSkipped("missing-input", (f"feed/reports/{source}.json",),
                          f"簿指向的报告 {source} 不可读,无法在同一次运行内比对。")
    breaker = None
    for alert in origin.get("alerts") or []:
        if isinstance(alert, dict) and alert.get("code") == "cointegration_breaker":
            breaker = alert
            break
    if breaker is None:
        raise LensSkipped("missing-input", (f"feed/reports/{source}.json:alerts[cointegration_breaker]",),
                          f"簿的来源报告 {source} 没有协整断裂告警。")
    listed = [t for t in (breaker.get("tickers") or []) if isinstance(t, str)]
    weights = {p.get("ticker"): _num(p.get("weight")) for p in (book.get("positions") or [])
               if isinstance(p, dict)}
    overlap = sorted(t for t in listed if t in weights)
    residual = _num(sum(abs(weights[t] or 0.0) for t in overlap))
    la = _date_of(origin.get("asof_data"))
    # tickers 被生产方硬截断(run_routine.py: br[:10]),全名单在 feed 里任何地方都没有留存 ——
    # 唯一还活着的总数在告警文案里。解析它,好把「这次核对了名单的百分之几」说成数字而不是含糊其辞;
    # 解析不到就退回 None,只讲已公布子集,绝不假装覆盖了全名单。
    declared = None
    match = re.match(r"\s*(\d+)\s*只标的触发", str(breaker.get("message") or ""))
    if match:
        parsed = int(match.group(1))
        if parsed >= len(listed):        # 自报总数小于已公布条数说明文案与数组对不上,不可信,不用
            declared = parsed
    truncated = declared is not None and declared > len(listed)
    coverage = _num(len(listed) / declared) if declared else None
    # 截断是按字母序取前 10(br[:10],br 本身按 ticker 排序),所以可见子集连随机样本都不是:
    # 0 交集既不能推广成全名单已清空,也不能拿来估交集率。
    scope = (f"这次只核对了名单的 {len(listed)}/{declared} 只"
             f"({coverage:.0%};告警数组被生产方截断,余下 {declared - len(listed)} 只在 feed 里没有留存),"
             f"且截断取的是字母序靠前的一段、不是随机样本"
             if truncated else
             f"核对覆盖了告警自报的全部 {len(listed)} 只" if declared is not None else
             f"告警文案没有给出可解析的总数,无从判断这 {len(listed)} 只是不是全名单")
    newest = corpus.latest_engine()
    newest_id = newest.get("id") if isinstance(newest, dict) else None
    # 比对本身仍然成立(两侧同源),但簿不是最新一班时读者该知道:结论描述的是那一班的状态。
    lag_note = ("" if not newest_id or newest_id == source else
                f"(注:更晚还有一份引擎报告 {newest_id},簿尚未跟到它,"
                f"本结论只描述 {source} 那一班的状态。)")
    return [claim(
        "residual-analyst", "q-book-vs-breaker",
        (f"簿自报来源报告 {source},该报告公布的 {len(listed)} 只熔断标的里没有一只带权重留在这份簿 —— "
         f"但{scope}。"
         + (f"所以这个 0 只覆盖名单的 {coverage:.0%},不能读成「簿里没有熔断标的」:"
            f"余下那 {declared - len(listed)} 只无从核对。"
            if truncated else "")
         if not overlap else
         f"簿自报来源报告 {source},该报告的熔断名单与这份簿有 {len(overlap)} 只交集 {overlap},"
         f"仍带 {residual} 的毛权重。熔断的设计意图是「立即标记平仓,禁止持有等待」(R2),"
         f"而簿是经 aim 平滑收敛出来的,只按 trade_rate 走一部分,因此被熔断的标的会带残余权重继续出现。"
         f"这不是数据损坏,但把 signals/latest.json 读成「已排除熔断标的」的消费方会读错。"
         + (f"另外,{scope},所以真实交集只会比这 {len(overlap)} 只更多、不会更少。"
            if truncated else f"另外,{scope}。")) + lag_note,
        # 度量名点明「只在公布子集上」:光看数字的消费方不会把 0 误当成全名单清零。
        metric="book.breaker_overlap.published_subset.count",
        value=len(overlap), unit="count", direction="none",
        n=len(listed), min_n=1, severity="warning" if overlap else "info", cites=("R2",),
        evidence=(ev("feed/signals/latest.json", "source_report", source, book.get("asof")),
                  ev(f"feed/reports/{source}.json", "alerts[cointegration_breaker].tickers.length",
                     len(listed), la),
                  ev(f"feed/reports/{source}.json", "alerts[cointegration_breaker].message.declared_total",
                     declared if declared is not None else "absent", la),
                  ev("feed/signals/latest.json", "positions[].ticker.count", len(weights), book.get("asof")),
                  ev("feed/signals/latest.json",
                     f"positions[{overlap[0]}].weight" if overlap else "positions[].weight",
                     weights.get(overlap[0]) if overlap else "absent", book.get("asof"))),
    )]


# ---- crowding-monitor:拥挤是尾部风险信号(R7)---------------------------------

@lens(
    qid="q-crowding-signal",
    role="crowding-monitor",
    title="拥挤代理有没有在动,它的告警阈值被行使过吗?",
    needs=("feed/reports/routine-*.json:market_state.crowding_proxy",
           "feed/reports/routine-*.json:market_state.crowding_alert",
           "feed/reports/routine-*.json:market_state.breadth_pct_above_50dma"),
    test="取去重后的 crowding_proxy 序列给最新值与斜率;统计 crowding_alert=true 的期数;"
         "并对 crowd[t] 与 breadth[t+1]-breadth[t] 做 Spearman 看有无领先性。",
    triggered_by="routine 报告带 market_state 段。",
)
def lens_crowding(corpus: Corpus) -> list[dict]:
    q = "q-crowding-signal"
    crowd: list[float] = []
    breadth: list[float] = []
    rows: list[dict] = []
    fired = 0
    for report in corpus.engine_days():
        cp = _dig(report, "market_state", "crowding_proxy")
        bp = _dig(report, "market_state", "breadth_pct_above_50dma")
        if not isinstance(cp, (int, float)) or isinstance(cp, bool) or not math.isfinite(cp):
            continue
        rows.append(report)
        crowd.append(float(cp))               # 序列不预舍入:_num 的 6 位舍入会造人为并列
        breadth.append(float(bp) if isinstance(bp, (int, float)) and not isinstance(bp, bool)
                       and math.isfinite(bp) else math.nan)
        if _dig(report, "market_state", "crowding_alert") is True:
            fired += 1
    if len(crowd) < 3:
        raise LensSkipped("insufficient-sample", ("feed/reports/routine-*.json:market_state.crowding_proxy",),
                          f"只有 {len(crowd)} 期拥挤代理观测。")
    latest, la = rows[-1], _date_of(rows[-1].get("asof_data"))
    lf = latest["_file"]
    out = [claim(
        "crowding-monitor", q,
        f"拥挤代理(universe 近 60 日收益的平均两两相关,不是残差相关)最新 {_num(crowd[-1], 4)},"
        f"{len(crowd)} 期区间 {_num(min(crowd), 4)}–{_num(max(crowd), 4)},"
        f"crowding_alert 触发 {fired}/{len(crowd)} 期"
        + (":告警阈值在这段样本上从未被行使,因此「未告警」不能当成「不拥挤」的证据(R7)。"
           if fired == 0 else
           ":阈值被行使过,跨期比较拥挤读数时要把已告警的期单独看(R7)。"),
        metric="market_state.crowding_alert.fired.count",
        value=fired, unit="count", direction="none", n=len(crowd), min_n=10,
        severity="info", cites=("R7",),
        evidence=(ev(lf, "market_state.crowding_proxy", _num(crowd[-1], 4), la),
                  ev(lf, "market_state.crowding_alert", _dig(latest, "market_state", "crowding_alert"), la)),
        max_age_days=None,
    )]
    pairs_x, pairs_y = [], []
    for i in range(len(crowd) - 1):
        if math.isfinite(breadth[i]) and math.isfinite(breadth[i + 1]):
            pairs_x.append(crowd[i])
            pairs_y.append(breadth[i + 1] - breadth[i])
    rho = spearman(pairs_x, pairs_y)
    if rho is not None:
        out.append(claim(
            "crowding-monitor", q,
            f"拥挤对次日广度变化的 Spearman={rho:+.3f}(n={len(pairs_x)}):"
            + (f"相关性落在 ±0.3 的噪声带内,本样本不足以说拥挤有领先性 —— 这条结论会被"
               f"within-noise-band 反驳器判为不成立,不得当择时信号用。" if abs(rho) < 0.3 else
               f"相关性出了 ±0.3 噪声带,但这仍只是本仓这段样本上的相关,不是因果,也不构成择时信号。")
            + "(R7:拥挤是尾部风险信号,不是做空信号。)",
            metric="market_state.crowding_leads_breadth.spearman",
            value=rho, unit="ratio", direction="up" if rho > 0 else "down",
            n=len(pairs_x), min_n=20, noise_band=0.3, severity="info", cites=("R7",),
            evidence=(ev(lf, "market_state.crowding_proxy", _num(crowd[-1], 4), la),
                      ev(lf, "market_state.breadth_pct_above_50dma",
                         _num(breadth[-1], 4) if math.isfinite(breadth[-1]) else None, la)),
            max_age_days=None,
        ))
    return out


@lens(
    qid="q-crypto-crowding",
    role="crowding-monitor",
    title="衍生品拥挤旗标与资金费错位阈值有区分度吗?",
    needs=("feed/crypto/state.json:crypto.crowding_flag",
           "feed/crypto/state.json:venues.n_dislocated",
           "feed/crypto/state.json:venues.n_compared"),
    test="算 n_dislocated/n_compared 错位占比与 threshold_apr;对照 crowding_flag 与 pct_positive_funding;"
         "并检查 errors 是否为空(非空则本快照不完整)。",
    triggered_by="feed/crypto/state.json 存在且带 venues 段。",
)
def lens_crypto_crowding(corpus: Corpus) -> list[dict]:
    (state,) = corpus.require("crypto")
    venues = state.get("venues") if isinstance(state, dict) else None
    crypto = state.get("crypto") if isinstance(state, dict) else None
    if not isinstance(venues, dict) or not isinstance(crypto, dict):
        raise LensSkipped("missing-input", ("feed/crypto/state.json:venues",), "快照缺 venues / crypto 段。")
    compared = venues.get("n_compared")
    dislocated = venues.get("n_dislocated")
    if not isinstance(compared, int) or not compared or not isinstance(dislocated, int):
        raise LensSkipped("insufficient-sample", ("feed/crypto/state.json:venues.n_compared",),
                          "对比样本为空。")
    asof = state.get("updated_at")
    share = _num(dislocated / compared)
    errors = state.get("errors") or []
    out = [claim(
        "crowding-monitor", "q-crypto-crowding",
        f"跨场资金费错位占比 {dislocated}/{compared}={share:.0%},阈值 threshold_apr="
        f"{_num(venues.get('threshold_apr'))}"
        + (f";这个比例下「错位」筛出的是常态而不是异常,当异常信号用会一直亮。" if (share or 0) >= 0.2
           else f";这个比例下「错位」还算少数事件。")
        + f"crowding_flag={crypto.get('crowding_flag')} 由另一套判据得出,与该占比并不同源。",
        metric="crypto.venues.dislocated.share",
        value=share, unit="fraction", direction="none", n=compared, min_n=30,
        severity="info", cites=("R7",),
        evidence=(ev("feed/crypto/state.json", "venues.n_dislocated", dislocated, asof),
                  ev("feed/crypto/state.json", "venues.n_compared", compared, asof),
                  ev("feed/crypto/state.json", "crypto.crowding_flag", crypto.get("crowding_flag"), asof)),
        max_age_days=3.0,
    )]
    extremes = crypto.get("funding_extremes") or []
    if isinstance(extremes, list) and extremes:
        oi = [( _num(_dig(x, "oi_usd")) or 0.0, x.get("coin")) for x in extremes if isinstance(x, dict)]
        oi = [t for t in oi if t[0] > 0]
        if oi:
            smallest = min(oi)
            largest = max(oi)
            spread = _num(largest[0] / smallest[0]) if smallest[0] > 0 else None
            out.append(claim(
                "crowding-monitor", "q-crypto-crowding",
                f"资金费极值榜 {len(extremes)} 个币的未平仓量跨越 ${smallest[0]:,.0f}"
                f"({smallest[1]})到 ${largest[0]:,.0f}({largest[1]})"
                + (f",相差 {spread:,.0f} 倍:" if spread else ":")
                + f"榜上名次由资金费排序、与规模无关,所以把整张榜当全市场拥挤读数会把"
                f"小合约的流动性噪声与大合约的仓位拥挤混为一谈。",
                metric="crypto.funding_extremes.min_oi_usd",
                value=smallest[0], unit="usd", direction="none",
                n=len(extremes), min_n=3, severity="info",
                evidence=(ev("feed/crypto/state.json",
                             f"crypto.funding_extremes[{smallest[1]}].oi_usd", smallest[0], asof),),
                max_age_days=3.0,
            ))
    if errors:
        out.append(claim(
            "crowding-monitor", "q-crypto-crowding",
            f"本快照 errors 非空({len(errors)} 条),按 hyperliquid_monitor 的逐键回退设计,"
            f"部分小节可能仍是上一轮的旧值,顶层 updated_at 的新鲜度不代表每个小节新鲜。",
            metric="crypto.errors.count",
            value=len(errors), unit="count", direction="none", n=None,
            severity="warning",
            evidence=(ev("feed/crypto/state.json", "errors.length", len(errors), asof),),
            max_age_days=3.0,
        ))
    return out


# ---- event-risk:事件只用于回避,不做方向 -------------------------------------

@lens(
    qid="q-stance-churn",
    role="event-risk",
    title="个股解读的立场翻转有多频繁,多少是真翻转、多少只是覆盖变化?",
    needs=("feed/stock-notes/stance-history.json:stances",),
    test="对相邻快照取键交集后统计翻转数,得 flip_rate;成员进出单独统计,不混进翻转率。",
    triggered_by="feed/stock-notes/stance-history.json 有 ≥2 个快照。",
)
def lens_stance_churn(corpus: Corpus) -> list[dict]:
    (history,) = corpus.require("stance_history")
    snaps = [s for s in history if isinstance(s, dict) and isinstance(s.get("stances"), dict)] \
        if isinstance(history, list) else []
    if len(snaps) < 2:
        raise LensSkipped("insufficient-sample", ("feed/stock-notes/stance-history.json",),
                          f"只有 {len(snaps)} 个立场快照。")
    flips = 0
    compared = 0
    churn = 0
    worst: tuple[int, str] = (0, "")
    for prev, cur in zip(snaps, snaps[1:]):
        a, b = prev["stances"], cur["stances"]
        shared = set(a) & set(b)
        compared += len(shared)
        pair_flips = sum(1 for k in shared if a[k] != b[k])
        flips += pair_flips
        churn += len(set(a) ^ set(b))
        if pair_flips > worst[0]:
            worst = (pair_flips, f"{prev.get('date')}→{cur.get('date')}")
    if not compared:
        raise LensSkipped("insufficient-sample", ("feed/stock-notes/stance-history.json:stances",),
                          "相邻快照没有任何同标的可对照。")
    rate = _num(flips / compared)
    last = snaps[-1]
    return [claim(
        "event-risk", "q-stance-churn",
        f"{len(snaps)} 个快照、{len(snaps) - 1} 对相邻快照共 {compared} 次同标的对照中,"
        f"真翻转 {flips} 次(flip_rate {rate:.1%}),最集中的一对是 {worst[1]}({worst[0]} 次);"
        f"快照不是逐日的,所以这是「相邻快照之间」而不是「一天之内」的变化。"
        f"另有 {churn} 次是覆盖名单进出,已单独计,不计入翻转率 —— 否则覆盖变化会被读成观点变化。",
        metric="stance.flip_rate",
        value=rate, unit="fraction", direction="none", n=compared, min_n=50,
        severity="info",
        evidence=(ev("feed/stock-notes/stance-history.json", "snapshots.length", len(snaps),
                     last.get("date")),
                  ev("feed/stock-notes/stance-history.json", "stances.length",
                     len(last.get("stances") or {}), last.get("date"))),
        max_age_days=5.0,
    )]


@lens(
    qid="q-intraday-vs-regime",
    role="event-risk",
    title="盘中广度与日线 regime 判定是否互相矛盾?",
    needs=("feed/intraday/latest.json:summary.up",
           "feed/intraday/latest.json:summary.down",
           "feed/market/state.json:regime"),
    test="算盘中上涨占比 up/(up+down),与 market_state.regime、breadth_pct_above_50dma 对照;"
         "并核对 pool_size == quoted(报价覆盖完整性)。",
    triggered_by="feed/intraday/latest.json 与 feed/market/state.json 同时存在。",
)
def lens_intraday_vs_regime(corpus: Corpus) -> list[dict]:
    intraday, market = corpus.require("intraday", "market_state")
    summary = intraday.get("summary") if isinstance(intraday, dict) else None
    if not isinstance(summary, dict):
        raise LensSkipped("missing-input", ("feed/intraday/latest.json:summary",), "盘中快照缺 summary。")
    up, down = summary.get("up"), summary.get("down")
    if not isinstance(up, int) or not isinstance(down, int) or (up + down) == 0:
        raise LensSkipped("insufficient-sample", ("feed/intraday/latest.json:summary.up",),
                          "盘中涨跌家数为空。")
    at = intraday.get("at")
    regime = market.get("regime")
    breadth = _num(market.get("breadth_pct_above_50dma"))
    up_share = _num(up / (up + down))
    contradiction = regime == "risk_on" and (up_share or 0) < 0.45
    out = [claim(
        "event-risk", "q-intraday-vs-regime",
        (f"盘中上涨占比 {up}/{up + down}={up_share:.0%},而日线 regime 判为 {regime}、"
         f"广度 {breadth}:两个口径当前互相矛盾。它们本来就不是同一测度(盘内快照 vs 50 日均线以上占比),"
         f"看板并列展示时必须标注,否则会被读成同一事实的两次确认。"
         if contradiction else
         f"盘中上涨占比 {up}/{up + down}={up_share:.0%},与日线 regime={regime}、广度 {breadth} 方向一致,"
         f"但两者仍是不同测度,一致不构成互相验证。"),
        metric="intraday.up_share",
        value=up_share, unit="fraction", direction="none", n=up + down, min_n=30,
        severity="warning" if contradiction else "info",
        evidence=(ev("feed/intraday/latest.json", "summary.up", up, at),
                  ev("feed/intraday/latest.json", "summary.down", down, at),
                  ev("feed/market/state.json", "regime", regime, corpus.asof("market_state")),
                  ev("feed/market/state.json", "breadth_pct_above_50dma", breadth,
                     corpus.asof("market_state"))),
        max_age_days=5.0,
    )]
    pool, quoted = intraday.get("pool_size"), intraday.get("quoted")
    if isinstance(pool, int) and isinstance(quoted, int):
        gap = pool - quoted
        out.append(claim(
            "event-risk", "q-intraday-vs-regime",
            (f"盘中池 {pool} 只全部取到报价(quoted={quoted}),这条广度读数没有报价缺口。"
             if gap == 0 else
             f"盘中池 {pool} 只但只取到 {quoted} 只报价,缺 {gap} 只:上面的涨跌占比是在"
             f"不完整样本上算的,不能当全池广度。"),
            metric="intraday.pool_minus_quoted",
            value=gap, unit="count", direction="none", n=pool, min_n=10,
            severity="info" if gap == 0 else "warning",
            evidence=(ev("feed/intraday/latest.json", "pool_size", pool, at),
                      ev("feed/intraday/latest.json", "quoted", quoted, at)),
            max_age_days=5.0,
        ))
    return out


# ---- factor-factory:六门控(§6.2.3)-----------------------------------------

@lens(
    qid="q-factory-gates",
    role="factor-factory",
    title="因子工厂的候选有没有真的过自己的门控?",
    needs=("feed/factory/candidates.json:candidates[].decision",
           "feed/factory/candidates.json:candidates[].passed_gates",
           "feed/factory/candidates.json:candidates[].t_stat"),
    test="统计 decision=='accept' 与 passed_gates 为真的条数、|t_stat| 最大值(对照门控③ t≳3)、"
         "以及带 pbo 字段的条数(门控① 的可查证据)。",
    triggered_by="feed/factory/candidates.json 非空。",
)
def lens_factory_gates(corpus: Corpus) -> list[dict]:
    (store,) = corpus.require("candidates")
    cands = [c for c in (store.get("candidates") or []) if isinstance(c, dict)] \
        if isinstance(store, dict) else []
    if not cands:
        raise LensSkipped("missing-input", ("feed/factory/candidates.json:candidates",), "候选账本为空。")
    q = "q-factory-gates"
    asof = store.get("updated_at")
    accepted = sum(1 for c in cands if c.get("decision") == "accept")
    passed = sum(1 for c in cands if c.get("passed_gates") is True)
    shadow = sum(1 for c in cands if c.get("decision") == "shadow")
    tstats = [abs(t) for t in (_num(c.get("t_stat")) for c in cands) if t is not None]
    with_pbo = sum(1 for c in cands if c.get("pbo") is not None)
    max_t = _num(max(tstats)) if tstats else None
    out = [claim(
        "factor-factory", q,
        f"账本留存 {len(cands)} 条候选:accept {accepted} 条、shadow {shadow} 条、passed_gates 为真 "
        f"{passed} 条。"
        + ("当前搜索空间里没有任何候选过门,因此账本里不存在可上线因子。"
           if accepted == 0 and passed == 0 else
           f"有候选过了门(passed_gates {passed} / accept {accepted}):按 R3,过门控只能进 60 日影子,"
           f"accept 直接上线是违规,需要人工复核这 {accepted} 条的 decision 来源。"),
        metric="factory.accepted.count",
        value=accepted, unit="count", direction="none", n=len(cands), min_n=20,
        severity="info" if accepted == 0 else "critical", cites=("R3", "门控①"),
        evidence=(ev("feed/factory/candidates.json", "candidates.length", len(cands), asof),
                  ev("feed/factory/candidates.json", "candidates[].decision==accept", accepted, asof),
                  ev("feed/factory/candidates.json", "candidates[].passed_gates==true", passed, asof)),
        max_age_days=5.0,
    )]
    if max_t is not None:
        out.append(claim(
            "factor-factory", q,
            f"账本内 |t_stat| 最大为 {max_t},门控③ 要求相依 FDR 后 |t|≳3:"
            + (f"最好的候选离门槛还差 {_num(3 - max_t)},不是「差一点」而是量级不足。"
               if max_t < 3 else
               f"已有候选达到或超过该门槛(超出 {_num(max_t - 3)}),门控③ 不再是这批候选的瓶颈,"
               f"需要看其余门控。"),
            metric="factory.t_stat.max_abs",
            value=max_t, unit="ratio", direction="none", n=len(tstats), min_n=20,
            severity="info", cites=("门控③",),
            evidence=(ev("feed/factory/candidates.json", "candidates[].t_stat.max_abs", max_t, asof),),
            max_age_days=5.0,
        ))
    out.append(claim(
        "factor-factory", q,
        f"{len(cands)} 条候选里有 {with_pbo} 条带 pbo 字段:门控① 的 PBO(CSCV)证据在留存账本里"
        + ("完全不可查,因此「过门控」这件事无法从 feed 侧独立复核" if with_pbo == 0 else
           "只有部分可查,缺 pbo 的那些无法从 feed 侧独立复核" if with_pbo < len(cands) else
           "逐条可查,门控① 的证据链在 feed 侧是完整的")
        + "(schema 不校验门控语义,可查不等于通过)。",
        metric="factory.pbo_present.count",
        value=with_pbo, unit="count", direction="none", n=len(cands), min_n=20,
        severity="warning" if with_pbo == 0 else "info", cites=("门控①",),
        evidence=(ev("feed/factory/candidates.json", "candidates[].pbo",
                     "absent" if with_pbo == 0 else with_pbo, asof),),
        max_age_days=5.0,
    ))
    return out


@lens(
    qid="q-factory-funnel",
    role="factor-factory",
    title="工厂提出了多少候选,最终留在账本里的有多少?",
    needs=("feed/reports/factory-local-*.json:contribution.candidates_proposed",
           "feed/factory/candidates.json:candidates"),
    test="累加各期 contribution.candidates_proposed,与账本留存条数比,得暴露率。",
    triggered_by="存在 factory-local 报告且账本非空。",
)
def lens_factory_funnel(corpus: Corpus) -> list[dict]:
    (store,) = corpus.require("candidates")
    reports = corpus.reports["factory-local-"]
    if not reports:
        raise LensSkipped("missing-input", ("feed/reports/factory-local-*.json",), "没有工厂报告。")
    proposed = 0
    counted = 0
    for report in reports:
        value = _dig(report, "contribution", "candidates_proposed")
        if isinstance(value, int):
            proposed += value
            counted += 1
    if proposed <= 0:
        raise LensSkipped("insufficient-sample", ("feed/reports/factory-local-*.json:contribution.candidates_proposed",),
                          "报告未记录提出数。")
    kept = len((store.get("candidates") or [])) if isinstance(store, dict) else 0
    share = _num(kept / proposed)
    last = reports[-1]
    return [claim(
        "factor-factory", "q-factory-funnel",
        f"{counted} 期工厂报告累计提出 {proposed} 条候选,账本当前只留存 {kept} 条(暴露率 {share:.2%}),"
        f"且账本按 120 条截断。看板上看到的候选数不是搜索规模,试验次数必须从报告侧读"
        f"(门控① 要求全部计数)。",
        metric="factory.kept_over_proposed.share",
        value=share, unit="fraction", direction="none", n=counted, min_n=5,
        severity="info", cites=("门控①",),
        evidence=(ev(last["_file"], "contribution.candidates_proposed",
                     _dig(last, "contribution", "candidates_proposed"), _date_of(last.get("asof_data"))),
                  ev("feed/factory/candidates.json", "candidates.length", kept,
                     corpus.asof("candidates"))),
        max_age_days=None,
    )]


# ---- risk:覆盖度 / 时效 -------------------------------------------------------

@lens(
    qid="q-freshness-gaps",
    role="risk",
    title="哪些工件已经旧到不该再被当前结论引用?",
    needs=("feed/health.json:sources", "feed/index.json:freshness"),
    test=f"逐工件比 age_days 与 {AGING_DAYS} 天建议线(13F 按季度豁免),并对照 health.json 的 critical/warn 计数。",
    triggered_by="覆盖度台账里至少有一个可解析 asof 的工件。",
)
def lens_freshness(corpus: Corpus) -> list[dict]:
    dated = [p for p in corpus.provenance
             if p.get("exists") and p.get("age_days") is not None and p["key"] not in QUARTERLY_KEYS]
    undated = [p for p in corpus.provenance
               if p.get("exists") and p.get("age_days") is None]
    aging = [p for p in dated if p["age_days"] > AGING_DAYS]
    missing = [p for p in corpus.provenance if not p.get("exists")]
    health = corpus.get("health")
    out: list[dict] = []
    oldest = max(aging, key=lambda p: p["age_days"]) if aging else None
    undated_note = (f"另有 {len(undated)} 个工件没有可解析的日期字段"
                    f"({', '.join(p['path'] for p in undated[:3])}),它们的龄期未知、"
                    f"不能当成新鲜。" if undated else "")
    out.append(claim(
        "risk", "q-freshness-gaps",
        (f"{len(dated)} 个可判龄期的工件里有 {len(aging)} 个超过 {AGING_DAYS} 天建议线,"
         f"最旧的是 {oldest['path']}({oldest['age_days']} 天);"
         f"引用它们的结论时效上限必须相应放宽,否则会把旧事实当现状。"
         if aging else
         f"{len(dated)} 个可判龄期的工件都在 {AGING_DAYS} 天建议线内(13F 按季度豁免),"
         f"这些工件的时效前提成立。") + undated_note,
        metric="feed.aging_artifacts.count",
        value=len(aging), unit="count", direction="none",
        n=len(dated), min_n=5,
        severity="warning" if len(aging) >= 3 else "info",
        evidence=tuple(
            [ev(p["path"], "asof", p.get("asof") or "absent", p.get("asof")) for p in aging[:4]]
            or [ev("feed/index.json", "freshness.sources", len(corpus.provenance),
                   corpus.asof("index"))]
        ),
        max_age_days=None,
    ))
    if missing:
        out.append(claim(
            "risk", "q-freshness-gaps",
            f"{len(missing)} 个工件读不到({', '.join(p['path'] for p in missing[:5])}):"
            f"引擎不会对读不到的工件做任何推断,相关问题一律降级为 open_question。",
            metric="feed.missing_artifacts.count",
            value=len(missing), unit="count", direction="none",
            n=len(corpus.provenance), min_n=1, severity="warning",
            evidence=tuple(ev(p["path"], "exists", False, None) for p in missing[:5]),
            max_age_days=None,
        ))
    crit = health.get("critical") if isinstance(health, dict) else None
    if isinstance(health, dict) and isinstance(crit, int):
        warn = health.get("warn")
        out.append(claim(
            "risk", "q-freshness-gaps",
            f"feed/health.json 自报 ok={health.get('ok')}、critical={crit}、warn={warn}"
            f"(checked_at {health.get('checked_at')}):ok 只表示没有 critical,不是完整性或正确性证明。",
            metric="feed.health.critical.count",
            value=crit, unit="count", direction="none",
            n=None, severity="critical" if crit > 0 else "info",
            evidence=(ev("feed/health.json", "critical", crit, health.get("checked_at")),
                      ev("feed/health.json", "warn", warn, health.get("checked_at")),
                      ev("feed/health.json", "ok", health.get("ok"), health.get("checked_at"))),
            max_age_days=5.0,
        ))
    return out


@lens(
    qid="q-notes-coverage",
    role="risk",
    title="个股解读的最新日覆盖率够不够支撑横截面结论?",
    needs=("feed/stock-notes/index.json:symbols[].date",),
    test="算最新日期的 symbol 占全部 symbol 的比例,并给出日期分布。",
    triggered_by="feed/stock-notes/index.json 存在且 symbols 非空。",
)
def lens_notes_coverage(corpus: Corpus) -> list[dict]:
    (index,) = corpus.require("notes_index")
    symbols = [s for s in (index.get("symbols") or []) if isinstance(s, dict)] \
        if isinstance(index, dict) else []
    if not symbols:
        raise LensSkipped("missing-input", ("feed/stock-notes/index.json:symbols",), "解读索引为空。")
    by_date: dict[str, int] = {}
    for item in symbols:
        by_date[str(item.get("date"))] = by_date.get(str(item.get("date")), 0) + 1
    newest = max(by_date)
    share = _num(by_date[newest] / len(symbols))
    spread = len(by_date)
    return [claim(
        "risk", "q-notes-coverage",
        f"{len(symbols)} 份个股解读分布在 {spread} 个日期上,最新日 {newest} 只覆盖 "
        f"{by_date[newest]} 份({share:.0%})。任何「全体个股当前立场」的横截面结论实际上是"
        f"跨日期拼接,必须按日期分层看,否则会把过期解读当今天的观点。",
        metric="stock_notes.newest_date.coverage",
        value=share, unit="fraction", direction="none", n=len(symbols), min_n=30,
        severity="warning" if (share or 0) < 0.6 else "info",
        evidence=(ev("feed/stock-notes/index.json", "symbols.length", len(symbols),
                     index.get("updated_at")),
                  ev("feed/stock-notes/index.json", f"symbols[date=={newest}].count",
                     by_date[newest], newest)),
        max_age_days=5.0,
    )]


@lens(
    qid="q-screener-date-skew",
    role="risk",
    title="选股系三个面板的日期与覆盖是否一致?",
    needs=("feed/screener/latest.json:date", "feed/signals/rs-ranks.json:date",
           "feed/screener/scores.json:date"),
    test="比三者 date 是否一致;并对 scores 与 rs-ranks 的键集合求交集看覆盖缺口。",
    triggered_by="选股 latest 与 rs-ranks 同时存在。",
)
def lens_screener_skew(corpus: Corpus) -> list[dict]:
    latest, ranks = corpus.require("screener", "rs_ranks")
    scores = corpus.get("screener_scores")
    dates = {"screener/latest": latest.get("date"), "signals/rs-ranks": ranks.get("date")}
    if isinstance(scores, dict):
        dates["screener/scores"] = scores.get("date")
    distinct = sorted({v for v in dates.values() if v})
    if not distinct:
        raise LensSkipped("missing-input", ("feed/screener/latest.json:date",),
                          "选股系面板都没有可读的 date 字段。")
    out = [claim(
        "risk", "q-screener-date-skew",
        (f"选股系日期一致({distinct[0]}),三个面板可以横向对照。"
         if len(distinct) == 1 else
         f"选股系日期不一致 {dates}:把它们放在同一屏对照会把不同交易日的横截面当同一天。"),
        metric="screener.date_skew.distinct",
        value=len(distinct), unit="count", direction="none", n=len(dates), min_n=2,
        severity="info" if len(distinct) <= 1 else "warning",
        evidence=tuple(ev(f"feed/{k}.json", "date", v, v) for k, v in dates.items()),
        max_age_days=5.0,
    )]
    rank_map = ranks.get("ranks") if isinstance(ranks, dict) else None
    score_map = (scores or {}).get("scores") if isinstance(scores, dict) else None
    if isinstance(rank_map, dict) and isinstance(score_map, dict) and rank_map and score_map:
        shared = set(rank_map) & set(score_map)
        union = set(rank_map) | set(score_map)
        cover = _num(len(shared) / len(union))
        xs, ys = [], []
        for key in sorted(shared):
            score = score_map.get(key)
            entry = rank_map.get(key)
            # rs-ranks 的值是对象 {rs,r63,...},不是标量 —— 取 rs 名次本身。
            rank = entry.get("rs") if isinstance(entry, dict) else entry
            if (isinstance(score, (int, float)) and not isinstance(score, bool)
                    and isinstance(rank, (int, float)) and not isinstance(rank, bool)):
                xs.append(float(score))
                ys.append(float(rank))
        rho = spearman(xs, ys)
        out.append(claim(
            "risk", "q-screener-date-skew",
            f"技术评分与 RS 排名的键集合交集 {len(shared)}/{len(union)}(覆盖 {(cover or 0):.1%}),"
            + (f"两者在 {len(xs)} 个可配对标的上的 Spearman(score, rs 名次)={rho:+.3f};"
               f"rs 名次越小越强,所以负相关才代表「评分高的 RS 也强」,"
               f"当前符号{'与该方向一致' if rho < 0 else '与该方向相反,两栏在打架'}。"
               if rho is not None else
               f"可配对样本 {len(xs)} 个,不足以算相关(需要 ≥3 且两侧都有方差),因此本次不给相关性。")
            + "覆盖缺口意味着看板两栏并非同一宇宙。",
            metric="screener.score_vs_rs.coverage",
            value=cover, unit="fraction", direction="none", n=len(union), min_n=50,
            severity="info",
            evidence=(ev("feed/screener/scores.json", "scores.length", len(score_map),
                         (scores or {}).get("date")),
                      ev("feed/signals/rs-ranks.json", "ranks.length", len(rank_map),
                         ranks.get("date"))),
            max_age_days=5.0,
        ))
    return out


# ---- red-team:溯源 / 截断 / 委员会活跃度 --------------------------------------

@lens(
    qid="q-provenance-consistency",
    role="red-team",
    title="市场状态面板与它自报的来源报告一致吗?",
    needs=("feed/market/state.json:source_report", "feed/reports/*.json:market_state"),
    test="按 source_report 定位报告,逐一比对 7 个 market_state 标量;不一致的键全部点名。",
    triggered_by="feed/market/state.json 带 source_report。",
)
def lens_provenance(corpus: Corpus) -> list[dict]:
    (market,) = corpus.require("market_state")
    source = market.get("source_report") if isinstance(market, dict) else None
    if not isinstance(source, str) or not source:
        raise LensSkipped("missing-input", ("feed/market/state.json:source_report",),
                          "面板没有 source_report。")
    try:
        path = fl.report_path(source)
    except ValueError as exc:
        raise LensSkipped("missing-input", ("feed/market/state.json:source_report",),
                          f"source_report 不是合法报告 id: {exc}") from exc
    report = fl.load_json(path)
    if not isinstance(report, dict):
        return [claim(
            "red-team", "q-provenance-consistency",
            f"feed/market/state.json 指向的报告 {source} 不存在:看板显示的市场状态没有可回溯来源。",
            metric="provenance.market_state.dangling",
            value=True, unit="none", direction="none", n=None, severity="critical",
            evidence=(ev("feed/market/state.json", "source_report", source,
                         corpus.asof("market_state")),
                      ev(f"feed/reports/{source}.json", "exists", "absent", None)),
            max_age_days=None,
        )]
    fields = ("regime", "spy_above_200dma", "spy_vol_20d_annual", "breadth_pct_above_50dma",
              "residual_dispersion", "crowding_proxy", "crowding_alert")
    origin = report.get("market_state") or {}
    # 两侧都缺的键不算「一致」—— 那是无从比对,必须单列,否则空对空会被读成溯源闭合。
    comparable = [f for f in fields if f in market and f in origin]
    absent = [f for f in fields if f not in market or f not in origin]
    mismatched = [f for f in comparable if market.get(f) != origin.get(f)]
    return [claim(
        "red-team", "q-provenance-consistency",
        (f"面板与来源报告 {source} 在 {len(comparable)}/{len(fields)} 个可比对的市场状态标量上一致"
         + (f";另有 {len(absent)} 个键 {absent} 至少一侧缺失,无从比对,不计入一致。"
            if absent else ",溯源链在这 7 个键上闭合。")
         if not mismatched else
         f"面板与来源报告 {source} 在 {len(mismatched)} 个键上不一致 {mismatched}"
         + (f"(另有 {len(absent)} 个键无从比对)" if absent else "")
         + ":看板读数不能按该报告复核。"),
        metric="provenance.market_state.mismatched.count",
        value=len(mismatched), unit="count", direction="none",
        n=len(comparable), min_n=1, severity="info" if not mismatched else "critical",
        evidence=(ev("feed/market/state.json", "source_report", source, corpus.asof("market_state")),
                  ev(f"feed/reports/{source}.json", "market_state.regime", origin.get("regime"),
                     _date_of(report.get("asof_data")))),
        max_age_days=None,
    )]


@lens(
    qid="q-truncation-audit",
    role="red-team",
    title="看板上的清单有多少是被截断后仍以完整清单示人的?",
    needs=("feed/reports/routine-*.json:alerts[].tickers", "feed/index.json:reports"),
    test="从告警文案里解析声明的标的数,与 tickers 数组长度比;再比 index.json 的 reports 长度与 stats.total_reports。",
    triggered_by="最新 routine 报告带 alerts,且 index.json 带 stats。",
)
def lens_truncation(corpus: Corpus) -> list[dict]:
    (index,) = corpus.require("index")
    out: list[dict] = []
    latest = corpus.latest_engine()
    if latest is not None:
        la = _date_of(latest.get("asof_data"))
        for alert in latest.get("alerts") or []:   # 逐条审计,不在第一条就停
            if not isinstance(alert, dict):
                continue
            match = re.search(r"(\d+)\s*只标的", str(alert.get("message") or ""))
            listed = [t for t in (alert.get("tickers") or []) if isinstance(t, str)]
            if not match:
                continue
            declared = int(match.group(1))
            if declared > len(listed):
                out.append(claim(
                    "red-team", "q-truncation-audit",
                    f"告警 {alert.get('code')} 文案声明 {declared} 只标的,tickers 数组只带 "
                    f"{len(listed)} 只:看板照 tickers 渲染会少显示 {declared - len(listed)} 只,"
                    f"这不是数据缺失而是刻意截断,消费方必须知道。",
                    metric=f"alerts.{alert.get('code') or 'unknown'}.tickers.truncated.count",
                    value=declared - len(listed), unit="count", direction="none",
                    n=declared, min_n=1, severity="warning",
                    evidence=(ev(latest["_file"], f"alerts[{alert.get('code')}].message",
                                 str(alert.get("message"))[:80], la),
                              ev(latest["_file"], f"alerts[{alert.get('code')}].tickers.length",
                                 len(listed), la)),
                    max_age_days=None,
                ))
    listed_reports = index.get("reports") if isinstance(index, dict) else None
    total = _dig(index, "stats", "total_reports")
    if isinstance(listed_reports, list) and isinstance(total, int) and total > len(listed_reports):
        out.append(claim(
            "red-team", "q-truncation-audit",
            f"feed/index.json 只列出最近 {len(listed_reports)} 份报告,而 stats.total_reports="
            f"{total}:任何基于 index.reports 的统计都是近端窗口统计,不是全量;"
            f"feed/ 也没有任何裁剪机制,历史只增不减。",
            metric="index.reports.window",
            value=len(listed_reports), unit="count", direction="none",
            n=total, min_n=1, severity="info",
            evidence=(ev("feed/index.json", "reports.length", len(listed_reports),
                         corpus.asof("index")),
                      ev("feed/index.json", "stats.total_reports", total, corpus.asof("index"))),
            max_age_days=None,
        ))
    if not out:
        raise LensSkipped("insufficient-sample", ("feed/index.json:stats.total_reports",),
                          "没有可查的截断点。")
    return out


@lens(
    qid="q-committee-dormancy",
    role="red-team",
    title="外部 agent 委员会还在投递吗?",
    needs=("feed/reports/openclaw-*.json:produced_at",),
    test="取 openclaw-* 报告的最新 produced_at 龄期与角色分布。",
    triggered_by="feed/reports 存在 openclaw-* 报告。",
)
def lens_committee_dormancy(corpus: Corpus) -> list[dict]:
    reports = corpus.reports["openclaw-"]
    if not reports:
        raise LensSkipped("missing-input", ("feed/reports/openclaw-*.json",),
                          "没有任何外部 agent 投递。")
    newest = max(reports, key=lambda r: str(r.get("produced_at") or ""))
    age = _age_days(newest.get("produced_at"))
    roles = sorted({str(_dig(r, "producer", "agent_role")) for r in reports})
    if age is None:
        raise LensSkipped("missing-input", ("feed/reports/openclaw-*.json:produced_at",),
                          "最新投递没有可解析的 produced_at,无法算龄期。")
    return [claim(
        "red-team", "q-committee-dormancy",
        f"外部 agent 委员会最近一次投递是 {newest.get('produced_at')}(已 {age} 天),"
        f"留档 {len(reports)} 份、覆盖 {len(roles)} 个角色 {roles}。"
        + (f"按 30 天口径委员会已休眠,看板上的角色词表是历史留档而不是活跃产能;"
           f"本引擎是确定性替代,不是委员会本身。" if age > 30 else
           f"委员会在 30 天口径内仍有投递,角色词表对应的是活跃产能;"
           f"本引擎与它并存,不是它的替代。"),
        metric="committee.last_submission.age_days",
        value=age, unit="days", direction="none", n=len(reports), min_n=1,
        severity="warning" if age > 30 else "info",
        evidence=(ev(newest["_file"], "produced_at", newest.get("produced_at"),
                     _date_of(newest.get("asof_data"))),
                  ev("feed/reports/openclaw-*.json", "count", len(reports), None)),
        max_age_days=None,
    )]


# ----------------------------- 编排 -----------------------------

def _run_lens(spec: dict, corpus: Corpus) -> tuple[dict, list[dict], dict | None, str | None]:
    """跑一个 lens。返回 (题目, 结论, open_question, 错误)。"""
    try:
        claims = spec["fn"](corpus) or []
        return spec, claims, None, None
    except LensSkipped as skipped:
        return spec, [], {"id": spec["id"], "title": spec["title"], "reason": skipped.reason,
                          "missing": skipped.missing, "detail": skipped.detail or str(skipped)}, None
    except Exception as exc:  # noqa: BLE001  单个 lens 失败不应影响其余取证
        return spec, [], {"id": spec["id"], "title": spec["title"], "reason": "lens-error",
                          "missing": [], "detail": f"{type(exc).__name__}: {exc}"}, str(exc)


def run(roles: tuple[str, ...], workers: int, report_limit: int, quiet: bool) -> dict:
    started = time.monotonic()
    # 整份简报只读一次时钟:id 的分钟、produced_at、today(future-asof 判据与 asof_data 上界)
    # 必须同源。分两次读的话,跨过一个 UTC 分钟就会出现 id 的分钟与 produced_at 不一致,
    # 跨过午夜还会让 today 落在前一天。运行耗时另有 run.duration_ms 记录。
    now = datetime.now(timezone.utc)
    produced_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    today = now.strftime("%Y-%m-%d")
    if not quiet:
        print(f"{TAG} 载入 feed 语料(report-limit={report_limit}) ...")
    corpus = Corpus(report_limit=report_limit)

    active = [spec for spec in LENSES if spec["role"] in roles]
    skipped_roles = [spec for spec in LENSES if spec["role"] not in roles]
    if not quiet:
        print(f"{TAG} 立题 {len(active)} 个 · 角色 {','.join(roles)} · 并发 {workers}")

    questions: list[dict] = []
    claims: list[dict] = []
    open_questions: list[dict] = []
    lens_errors = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run_lens, spec, corpus): spec for spec in active}
        for future in as_completed(futures):
            spec, produced, unanswered, error = future.result()
            questions.append({"id": spec["id"], "role": spec["role"], "title": spec["title"],
                              "needs": spec["needs"], "test": spec["test"],
                              "triggered_by": spec["triggered_by"], "answered": False})
            claims.extend(produced)
            if unanswered is not None:
                open_questions.append(unanswered)
            if error is not None:
                lens_errors += 1
                print(f"  ! lens {spec['id']}: {error}", file=sys.stderr)

    for spec in skipped_roles:
        open_questions.append({"id": spec["id"], "title": spec["title"], "reason": "role-disabled",
                               "missing": [], "detail": f"角色 {spec['role']} 未在本次 --roles 白名单内。"})

    claims.sort(key=lambda c: (c["question"], c.get("metric") or "", c["statement"]))
    for i, item in enumerate(claims, start=1):
        item["id"] = f"c{i:02d}"
    verify(claims, today)

    findings = [c for c in claims if c["verdict"] == "confirmed"]
    refuted = [c for c in claims if c["verdict"] != "confirmed"]
    answered = {c["question"] for c in findings}
    for question in questions:
        question["answered"] = question["id"] in answered
    known = {q["id"] for q in open_questions}
    for question in questions:
        if not question["answered"] and question["id"] not in known:
            reason = "all-claims-refuted" if any(c["question"] == question["id"] for c in refuted) \
                else "insufficient-sample"
            open_questions.append({"id": question["id"], "title": question["title"],
                                   "reason": reason, "missing": [],
                                   "detail": "本题产出的结论全部未通过对抗验证。" if reason == "all-claims-refuted"
                                             else "本题没有产出任何结论。"})
    questions.sort(key=lambda q: q["id"])
    open_questions.sort(key=lambda q: q["id"])

    alerts = _build_alerts(findings)
    brief_id = f"deep-research-{now.strftime('%Y-%m-%dT%H%M')}Z"
    read = sum(1 for p in corpus.provenance if p.get("exists"))
    # asof_data = 实际取证到的最新证据日期(不是运行日),与 feed 其它族的 asof 语义一致。
    evidence_dates = [d for d in (_date_of(item.get("asof"))
                                  for c in claims for item in (c.get("evidence") or []))
                      if d and d <= today]
    asof_data = max(evidence_dates) if evidence_dates else today
    brief = {
        "schema_version": "1.0",
        "id": brief_id,
        "kind": "deep-research",
        "produced_at": produced_at,
        "asof_data": asof_data,
        "producer": {
            "name": "deep-research-engine",
            "agent_role": VERIFIER_ROLE,
            "method": "deterministic-no-llm",
            "run_url": os.environ.get("GITHUB_RUN_URL", ""),
        },
        "run": {
            "workers": workers,
            "roles": list(roles),
            "questions_derived": len(questions),
            "lenses_run": len(active),
            "lenses_failed": lens_errors,
            "reports_scanned": corpus.reports_scanned,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
        "questions": questions,
        "findings": findings,
        "refuted": refuted,
        "verdicts": {
            "confirmed": len(findings),
            "refuted": sum(1 for c in refuted if c["verdict"] == "refuted"),
            "unverified": sum(1 for c in refuted if c["verdict"] == "unverified"),
        },
        "open_questions": open_questions,
        "next_actions": _build_next_actions(corpus, findings, open_questions),
        "alerts": alerts,
        "coverage": {
            "artifacts": corpus.provenance,
            "artifacts_read": read,
            "artifacts_missing": len(corpus.provenance) - read,
        },
        "notes": NOTES,
    }
    return brief


def _alert_code(c: dict) -> str:
    metric = str(c.get("metric") or c.get("question") or "claim")
    code = re.sub(r"[^a-z0-9]+", "-", metric.lower()).strip("-")
    return code[:60] or "deep-research"


def _build_alerts(findings: list[dict]) -> list[dict]:
    order = {"critical": 0, "warning": 1}
    graded = [c for c in findings if c.get("severity") in order]
    graded.sort(key=lambda c: (order[c["severity"]], c["id"]))
    return [{"level": c["severity"], "code": _alert_code(c),
             "message": c["statement"], "tickers": []} for c in graded[:MAX_ALERTS]]


def _build_next_actions(corpus: Corpus, findings: list[dict], open_questions: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for entry in corpus.provenance:
        if not entry.get("exists"):
            actions.append({"priority": "high", "action": f"补齐或修复 {entry['path']}",
                            "because": "工件读不到,依赖它的问题本轮无法立题。"})
        elif entry["key"] not in QUARTERLY_KEYS and (entry.get("age_days") or 0) > AGING_DAYS:
            actions.append({
                "priority": "medium",
                "action": f"刷新 {entry['path']}(已 {entry['age_days']} 天)",
                "because": f"超过 {AGING_DAYS} 天建议线,引用它的结论会被 stale-evidence 反驳。",
            })
    for c in findings:
        if c.get("severity") == "critical":
            actions.append({"priority": "high", "action": f"复核结论 {c['id']}:{c.get('metric')}",
                            "because": c["statement"][:160]})
    for question in open_questions:
        if question["reason"] == "missing-input" and question.get("missing"):
            actions.append({
                "priority": "low",
                "action": f"为 {question['id']} 补齐输入:{', '.join(question['missing'][:3])}",
                "because": "缺输入的问题不会被推断,只会一直留在 open_questions。",
            })
    deduped: list[dict] = []
    seen: set[str] = set()
    for action in actions:
        if action["action"] in seen:
            continue
        seen.add(action["action"])
        deduped.append(action)
    rank = {"high": 0, "medium": 1, "low": 2}
    deduped.sort(key=lambda a: (rank[a["priority"]], a["action"]))
    return deduped[:MAX_NEXT_ACTIONS]


def _clip(text: str, limit: int = 200) -> str:
    """按句号裁剪到 limit 内,避免摘要断在半句上。"""
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = max(head.rfind("。"), head.rfind(";"))
    return (head[:cut + 1] if cut >= 60 else head.rstrip() + "…")


def headline(brief: dict) -> str:
    for level in ("critical", "warning"):
        for c in brief["findings"]:
            if c.get("severity") == level:
                return _clip(c["statement"])
    counts = brief["verdicts"]
    return (f"{counts['confirmed']} 条结论通过对抗验证,{counts['refuted']} 条被反驳、"
            f"{counts['unverified']} 条无法判定。")


# ----------------------------- 校验 / 发布 -----------------------------

RESEARCH_SCHEMA_PATH = os.path.join(fl.FEED, "schema", "research.schema.json")


def validate_brief(brief: dict) -> tuple[bool, list[str]]:
    """优先用 jsonschema 全量校验;缺该库时退化为必填字段 + 取值域检查(与 feed_lib 同一策略)。"""
    try:
        import jsonschema  # type: ignore

        schema = fl.load_json(RESEARCH_SCHEMA_PATH)
        if schema is None:
            return False, [f"缺少 schema: {RESEARCH_SCHEMA_PATH}"]
        validator = jsonschema.Draft7Validator(schema)
        errors = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(brief)]
        return (not errors, errors)
    except ImportError:
        return _validate_brief_fallback(brief)


def _validate_brief_fallback(brief: dict) -> tuple[bool, list[str]]:
    """无 jsonschema 时的退化校验。

    定时 workflow 不装任何依赖(它刻意不跑 pip install),所以生产路径走的就是这一条。
    因此这里必须覆盖「简报能撒的谎」而不只是必填字段:kind/method 供述、findings 的
    verdict 纪律、裁决计数与数组是否自洽、每条结论的必备键与证据形状、以及所有数值有限。
    """
    errs: list[str] = []
    for key in ("schema_version", "id", "kind", "produced_at", "producer", "asof_data",
                "findings", "verdicts"):
        if key not in brief:
            errs.append(f"缺少必填字段: {key}")
    if brief.get("schema_version") != "1.0":
        errs.append("schema_version 必须为 '1.0'")
    if brief.get("kind") != "deep-research":
        errs.append("kind 必须为 'deep-research'")
    producer = brief.get("producer")
    if not isinstance(producer, dict) or not producer.get("name"):
        errs.append("producer.name 缺失")
    elif producer.get("method") != "deterministic-no-llm":
        errs.append("producer.method 必须为 'deterministic-no-llm'(不得声称 LLM 参与)")
    try:
        fl.require_report_id(brief.get("id"))
    except ValueError as exc:
        errs.append(str(exc))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(brief.get("asof_data") or "")):
        errs.append("asof_data 必须是 YYYY-MM-DD")
    if str(brief.get("asof_data") or "") > str(brief.get("produced_at") or "")[:10]:
        errs.append("asof_data 不得晚于 produced_at 的日期部分")

    findings = brief.get("findings")
    refuted = brief.get("refuted", [])
    if not isinstance(findings, list) or not isinstance(refuted, list):
        errs.append("findings 与 refuted 必须是数组")
        return (False, errs)
    seen: set[str] = set()
    for group, allowed in (("findings", {"confirmed"}), ("refuted", {"refuted", "unverified"})):
        for c in brief.get(group) or []:
            if not isinstance(c, dict):
                errs.append(f"{group} 的元素必须是 object")
                continue
            if c.get("verdict") not in allowed:
                errs.append(f"{group} 不允许 verdict={c.get('verdict')!r}(允许 {sorted(allowed)})")
            for key in ("id", "role", "statement"):
                if not c.get(key):
                    errs.append(f"{group} 的结论缺 {key}")
            if c.get("id") in seen:
                errs.append(f"结论 id 重复: {c.get('id')}")
            seen.add(str(c.get("id")))
            if c.get("role") not in ROLES:
                errs.append(f"结论 role 非法: {c.get('role')!r}")
            for item in c.get("evidence") or []:
                if not isinstance(item, dict) or not item.get("artifact") or not item.get("field"):
                    errs.append(f"结论 {c.get('id')} 的证据缺 artifact/field")
                    break
    verdicts = brief.get("verdicts")
    if not isinstance(verdicts, dict) or any(
            not isinstance(verdicts.get(k), int) for k in ("confirmed", "refuted", "unverified")):
        errs.append("verdicts 必须给出 confirmed/refuted/unverified 三个整数")
    else:
        if verdicts["confirmed"] != len(findings):
            errs.append(f"verdicts.confirmed={verdicts['confirmed']} 与 findings 长度 "
                        f"{len(findings)} 不一致")
        others = verdicts["refuted"] + verdicts["unverified"]
        if others != len(refuted):
            errs.append(f"verdicts.refuted+unverified={others} 与 refuted 长度 {len(refuted)} 不一致")
    try:
        fl.json_file_bytes(brief)          # allow_nan=False:非有限浮点在这里就暴露
    except ValueError as exc:
        errs.append(f"简报含非法 JSON 数值: {exc}")
    return (not errs, errs)


def brief_summary(brief: dict) -> dict:
    return {
        "id": brief["id"],
        "produced_at": brief["produced_at"],
        "asof_data": brief.get("asof_data"),
        "headline": headline(brief),
        "n_questions": len(brief.get("questions") or []),
        "n_findings": len(brief.get("findings") or []),
        "confirmed": brief["verdicts"]["confirmed"],
        "refuted": brief["verdicts"]["refuted"],
        "unverified": brief["verdicts"]["unverified"],
        "n_alerts": len(brief.get("alerts") or []),
        "path": f"research/{os.path.basename(fl.research_path(brief['id']))}",
    }


def rebuild_research_index() -> dict:
    """扫描 feed/research/ 重建 index.json;与 rebuild_index() 同策略:只截断索引视图,不删工件。"""
    rdir = os.path.join(fl.FEED, "research")
    briefs: list[dict] = []
    for name in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        if not name.endswith(".json") or name == "index.json":
            continue
        try:
            doc = fl.load_json(os.path.join(rdir, name))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! research/{name}: {exc}", file=sys.stderr)
            continue
        if not (isinstance(doc, dict) and doc.get("id") and doc.get("kind") == "deep-research"):
            continue
        try:
            summaries_probe = brief_summary(doc)
        except Exception as exc:  # noqa: BLE001  一份坏简报不得把整个族索引卡死
            print(f"  ! research/{name} 摘要失败,跳过: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        briefs.append((doc, summaries_probe))
    briefs.sort(key=lambda pair: str(pair[0].get("produced_at") or ""), reverse=True)

    by_role: dict[str, int] = {}
    last_7d = 0
    for doc, _ in briefs:
        for c in doc.get("findings") or []:
            role = str(c.get("role") or "unknown")
            by_role[role] = by_role.get(role, 0) + 1
        age = fl._days_since(doc.get("produced_at"))
        if age is not None and age <= 7:
            last_7d += 1
    latest = briefs[0][0] if briefs else None
    index = {
        "schema_version": "1.0",
        "updated_at": fl.now_iso(),
        "note": "scripts/deep_research.py 产出的深度研究简报索引。确定性引擎,未调用 LLM;"
                "confirmed 只表示对已记录数据的可复现计算成立,不构成投资建议。"
                f"最多保留 {fl.MAX_INDEX_BRIEFS} 条摘要,简报文件本身不裁剪。",
        "latest": briefs[0][1] if briefs else None,
        "stats": {"total_briefs": len(briefs), "by_role": by_role, "last_7d": last_7d},
        "briefs": [summary for _, summary in briefs[:fl.MAX_INDEX_BRIEFS]],
        "open_questions": (latest.get("open_questions") or []) if latest else [],
    }
    fl.save_json(os.path.join(fl.FEED, "research", "index.json"), index)
    return index


def alert_scan() -> int:
    """扫描已发布的最新简报里的 critical 告警,给 workflow 打印四行机器可读结果。

    输出(固定四行,便于 shell 用 sed -n Np 取):
      1 status   ok / no-index / no-brief / unreadable
      2 count    critical 告警条数(status!=ok 时为 0)
      3 id       简报 id
      4 message  首条 critical 告警文案(压成单行)
    「读不到」与「读到了但没有 critical」必须区分:告警链路不能因为读不到就静默报平安。
    退出码恒为 0 —— 简报此时已经发布,调用方按 status 决定怎么处理。
    """
    def emit(status: str, count: int = 0, brief_id: str = "", message: str = "") -> int:
        print(status)
        print(count)
        print(brief_id)
        print(" ".join(str(message).split()))
        return 0

    index_path = os.path.join(fl.FEED, "research", "index.json")
    try:
        index = fl.load_json(index_path)
    except Exception as exc:  # noqa: BLE001
        return emit(f"unreadable-index:{type(exc).__name__}")
    if not isinstance(index, dict):
        return emit("no-index")
    # 唯一真相源是 latest;briefs[0] 只作兜底,避免与前端/索引对「哪份最新」产生分歧。
    candidate = index.get("latest") or (index.get("briefs") or [None])[0]
    relative = (candidate or {}).get("path") if isinstance(candidate, dict) else None
    if not isinstance(relative, str) or not relative:
        return emit("no-brief")
    try:
        brief = fl.load_json(os.path.join(fl.FEED, relative.lstrip("/")))
    except Exception as exc:  # noqa: BLE001
        return emit(f"unreadable-brief:{type(exc).__name__}")
    if not isinstance(brief, dict):
        return emit("no-brief")
    critical = [a for a in (brief.get("alerts") or [])
                if isinstance(a, dict) and a.get("level") == "critical"]
    return emit("ok", len(critical), str(brief.get("id") or ""),
                critical[0].get("message", "") if critical else "")


def companion_report(brief: dict) -> dict:
    """简报的配套 feed 报告(kind=routine)。

    刻意不带 market_state / book:feed_lib.write_report_files 会用它们覆盖
    feed/market/state.json 与 feed/signals/latest.json,那是引擎的面板。
    """
    counts = brief["verdicts"]
    return {
        "schema_version": "1.0",
        "id": brief["id"],
        "kind": "routine",
        "produced_at": brief["produced_at"],
        "asof_data": brief["asof_data"],
        "producer": {"name": "deep-research-engine", "agent_role": VERIFIER_ROLE,
                     "run_url": os.environ.get("GITHUB_RUN_URL", "")},
        "alerts": brief["alerts"],
        "contribution": {
            "type": "risk_alert" if brief["alerts"] else "no_change",
            "summary": f"深度研究:立题 {len(brief['questions'])},confirmed {counts['confirmed']} / "
                       f"refuted {counts['refuted']} / unverified {counts['unverified']};"
                       f"{headline(brief)}",
        },
        "notes": f"确定性深度研究简报 research/{brief['id']}.json 的告警摘要。{NOTES}",
    }


def publish(brief: dict, *, brief_only: bool, quiet: bool) -> int:
    secret = os.environ.get("FEED_HMAC_SECRET")
    if secret:
        fl.sign_report(brief, secret)
    ok, errors = validate_brief(brief)
    if not ok:
        print(f"{TAG} 简报未通过 schema 校验:", errors[:8], file=sys.stderr)
        return 1
    # 两份工件要么一起发,要么一份都不发:配套报告必须在写任何文件之前就校验完。
    # 否则报告校验失败时,简报与索引已经落盘,退出码 1 收不回已写的文件 ——
    # 消费方会看到一份没有配套报告的简报。sign_report 先剥掉 signature 再算 HMAC,
    # 所以这里签一次、publish_report 里再签一次结果相同,不会因重复签名而失效。
    report = None
    if not brief_only:
        report = companion_report(brief)
        if secret:
            fl.sign_report(report, secret)
        report_ok, report_errors = fl.validate_report(report)
        if not report_ok:
            print(f"{TAG} 配套报告校验失败,简报与索引均未落盘:{report_errors}", file=sys.stderr)
            return 1

    path = fl.research_path(brief["id"])
    fl.save_json(path, brief)
    index = rebuild_research_index()
    if not quiet:
        print(f"{TAG} 已写 {os.path.relpath(path, fl.REPO_ROOT)}"
              f"(索引 {index['stats']['total_briefs']} 份)")
    if brief_only:
        return 0

    result = fl.publish_report(report, secret=secret)
    if not result["ok"]:   # 已预校验过,走到这里说明是落盘阶段出的问题
        print(f"{TAG} 配套报告发布失败:{result['errors']}", file=sys.stderr)
        return 1
    if not quiet:
        critical = [a for a in brief["alerts"] if a["level"] == "critical"]
        print(f"{TAG} 已发布配套报告 {report['id']}(critical {len(critical)} 条)"
              f" · feed 统计 {result['index_stats']}")
    return 0


# ----------------------------- CLI -----------------------------

def _resolve_roles(raw: str | None) -> tuple[str, ...]:
    text = (raw if raw is not None else os.environ.get("DEEP_RESEARCH_ROLES", "")) or ""
    wanted = [part.strip() for part in text.split(",") if part.strip()]
    if not wanted:
        return ROLES
    unknown = [r for r in wanted if r not in ROLES]
    if unknown:
        raise SystemExit(f"{TAG} 未知角色 {unknown};可选 {list(ROLES)}")
    return tuple(r for r in ROLES if r in wanted)


def _resolve_workers(raw: int | None) -> int:
    if raw is None:
        env = os.environ.get("DEEP_RESEARCH_WORKERS", "").strip()
        try:
            raw = int(env) if env else DEFAULT_WORKERS
        except ValueError:
            print(f"  ! DEEP_RESEARCH_WORKERS={env!r} 不是整数,回退 {DEFAULT_WORKERS}", file=sys.stderr)
            raw = DEFAULT_WORKERS
    return max(1, min(MAX_WORKERS, raw))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="写 feed/research/ 与配套 routine 报告")
    ap.add_argument("--brief-only", action="store_true", help="与 --publish 同用:只写简报与索引,不发报告")
    ap.add_argument("--roles", default=None, help="角色白名单,逗号分隔(默认全部)")
    ap.add_argument("--workers", type=int, default=None, help=f"并发 lens 线程数(默认 {DEFAULT_WORKERS})")
    ap.add_argument("--report-limit", type=int, default=DEFAULT_REPORT_LIMIT,
                    help=f"每种前缀最多读取的历史报告数(默认 {DEFAULT_REPORT_LIMIT})")
    ap.add_argument("--quiet", action="store_true", help="只打印错误")
    ap.add_argument("--alert-scan", action="store_true",
                    help="只扫描已发布最新简报的 critical 告警,打印四行 status/count/id/message")
    args = ap.parse_args()

    if args.alert_scan:
        return alert_scan()

    roles = _resolve_roles(args.roles)
    workers = _resolve_workers(args.workers)
    brief = run(roles, workers, args.report_limit, args.quiet)

    if brief["coverage"]["artifacts_read"] == 0:
        print(f"{TAG} 一个 feed 工件都读不到,拒绝产出空简报。", file=sys.stderr)
        return 1

    counts = brief["verdicts"]
    if not args.quiet:
        print(f"{TAG} 结论 confirmed {counts['confirmed']} · refuted {counts['refuted']} · "
              f"unverified {counts['unverified']} · 未答 {len(brief['open_questions'])} · "
              f"告警 {len(brief['alerts'])} · {brief['run']['duration_ms']}ms")
        for c in brief["findings"][:8]:
            mark = {"critical": "✗", "warning": "⚠"}.get(c.get("severity", ""), "·")
            print(f"  {mark} [{c['role']}] {c['statement'][:150]}")
        for c in brief["refuted"][:5]:
            codes = ",".join(r["code"] for r in c["refutations"])
            print(f"  ✗被驳 [{c['role']}] {c['statement'][:90]} ({codes})")
        for action in brief["next_actions"][:5]:
            print(f"  → [{action['priority']}] {action['action']}")

    if not args.publish:
        ok, errors = validate_brief(brief)
        if not ok:
            print(f"{TAG} 简报未通过 schema 校验:", errors[:8], file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"{TAG} 未加 --publish,未写任何文件(schema 校验通过)。")
        return 0
    return publish(brief, brief_only=args.brief_only, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
