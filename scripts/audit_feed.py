"""feed 数据实效性 + 连贯性审计 —— 把「不连贯/陈旧」变成机器可查的硬规则。

逐项检查(级别: critical / warn / info):
  实效性(每个数据面板有自己的 SLA):
    - 引擎簿 asof 落后引擎数据末日 → critical(显示「当前簿」却是旧仓位)
    - market_state / screener / stock-notes / rs-ranks / intraday 超龄 → warn
    - 13F:季度报告期+135天仍未见新 filing → warn(Q1 截止 5/15)
  连贯性(跨文件交叉核对):
    - index.latest.report / signals.source_report / market.source_report 指向的报告必须存在
    - 报告 asof_data 不得晚于 produced_at(不许声称未来数据)
    - 引擎报告: asof_data == engine.period.end == equity_curve 末点日期
    - screener latest/scores/rs-ranks 三者日期一致
    - stock-notes index 里的 symbol 文件必须存在,且 ≥70% 覆盖到最新日期
    - 捆绑快照 public/feed/index.json 落后 feed/ 超 7 天 → info(部署时会刷新,仅提示)

产出: feed/health.json(看板/watchdog 消费) + 控制台表格;有 critical 时退出码 1。
用法: python scripts/audit_feed.py [--write]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402

ROOT = fl.REPO_ROOT
NOW = datetime.now(timezone.utc)

issues: list[dict] = []


def flag(level: str, code: str, msg: str):
    issues.append({"level": level, "code": code, "message": msg})


def _age_days(s) -> float | None:
    return fl._days_since(str(s)) if s else None


def _j(path):
    return fl.load_json(os.path.join(fl.FEED, path))


def check_engine_coherence():
    idx = _j("index.json")
    sig = _j("signals/latest.json")
    mkt = _j("market/state.json")
    if not idx:
        flag("critical", "index-missing", "feed/index.json 缺失")
        return
    # 指向的报告存在性
    for label, ref in [("index.latest.report", (idx.get("latest") or {}).get("report")),
                       ("signals.source_report", (sig or {}).get("source_report")),
                       ("market.source_report", (mkt or {}).get("source_report"))]:
        if ref:
            p = ref if ref.startswith("reports/") else f"reports/{ref}.json"
            if not p.endswith(".json"):
                p += ".json"
            if not os.path.exists(os.path.join(fl.FEED, p)):
                flag("critical", "dangling-ref", f"{label} 指向不存在的报告: {ref}")
    # 引擎报告内部连贯性
    rep_path = (idx.get("latest") or {}).get("report")
    rep = _j(rep_path) if rep_path else None
    if rep and rep.get("engine"):
        eng = rep["engine"]
        period_end = (eng.get("period") or {}).get("end")
        ec = eng.get("equity_curve") or []
        if period_end and rep.get("asof_data") and rep["asof_data"] != period_end:
            flag("warn", "asof-mismatch",
                 f"引擎报告 asof_data={rep['asof_data']} ≠ period.end={period_end}")
        if ec and period_end and ec[-1].get("d") != period_end:
            flag("warn", "equity-curve-tail",
                 f"净值曲线末点 {ec[-1].get('d')} ≠ period.end={period_end}")
        if sig and period_end and sig.get("asof"):
            lag = (datetime.strptime(period_end, "%Y-%m-%d")
                   - datetime.strptime(sig["asof"], "%Y-%m-%d")).days
            if lag > 1:
                flag("critical", "book-lag",
                     f"持仓簿 asof={sig['asof']} 落后引擎数据末日 {period_end} 共 {lag} 天(应在最后一根 bar 上构簿)")
        if rep.get("produced_at") and rep.get("asof_data"):
            if rep["asof_data"] > rep["produced_at"][:10]:
                flag("critical", "future-asof", f"报告声称 asof_data={rep['asof_data']} 晚于生成时间(未来数据)")
    # 全部报告:asof 不得超前 produced_at
    rdir = os.path.join(fl.FEED, "reports")
    for fn in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        r = _j(f"reports/{fn}")
        if r and r.get("asof_data") and r.get("produced_at") and r["asof_data"] > r["produced_at"][:10]:
            flag("warn", "future-asof", f"{fn}: asof_data={r['asof_data']} > produced_at 日期")


def check_freshness():
    src = fl._artifact_freshness()
    SLA = {  # (warn天数, critical天数);None=只查存在性
        "signals_book": (3, 6), "market_state": (3, 6), "screener": (2, 5),
        "crypto_state": (0.5, 2),
        "rs_ranks": (2, 5), "stock_notes": (2, 5), "intraday": (2, 5),
        "market_history": (3, 7), "funds_13f": (135, 200),
        "research": (4, 9),   # 深度研究:工作日每晚一班,跨周末最长 3 天 -> warn 4d / critical 9d
    }
    for key, lim in SLA.items():
        s = src.get(key, {})
        if not s.get("exists"):
            flag("warn", "missing-artifact", f"feed 缺少 {key}(前端已引用,将渲染为空)")
            continue
        age = s.get("age_days")
        if age is None:
            flag("info", "no-date", f"{key} 无可解析日期字段")
        elif age > lim[1]:
            flag("critical", "stale", f"{key} 已 {age:.1f} 天未更新(SLA {lim[1]}d)")
        elif age > lim[0]:
            flag("warn", "aging", f"{key} 已 {age:.1f} 天未更新(SLA {lim[0]}d)")


def check_screener_coherence():
    latest, scores = _j("screener/latest.json"), _j("screener/scores.json")
    rs = _j("signals/rs-ranks.json")
    dates = {"screener/latest": (latest or {}).get("date"),
             "screener/scores": (scores or {}).get("date"),
             "signals/rs-ranks": (rs or {}).get("date")}
    seen = {v for v in dates.values() if v}
    if len(seen) > 1:
        flag("warn", "screener-date-skew", f"screener 系日期不一致: {dates}")


def check_stock_notes():
    ni = _j("stock-notes/index.json")
    if not ni:
        return
    syms = ni.get("symbols", [])
    missing = []
    by_date: dict[str, int] = {}
    for s in syms:
        by_date[s.get("date", "?")] = by_date.get(s.get("date", "?"), 0) + 1
        f = s.get("symbol", "").replace(":", "-")
        if f and not os.path.exists(os.path.join(fl.FEED, "stock-notes", f"{f}.json")):
            missing.append(s.get("symbol"))
    if missing:
        flag("warn", "notes-dangling", f"stock-notes index 引用但文件缺失: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    if by_date:
        newest = max(d for d in by_date if d != "?")
        cov = by_date.get(newest, 0) / max(1, len(syms))
        if cov < 0.7:
            flag("info", "notes-partial",
                 f"stock-notes 最新日 {newest} 覆盖率 {cov*100:.0f}%(分布 {dict(sorted(by_date.items()))})")


def check_research_coherence():
    """深度研究简报:索引指向的简报必须存在,且简报不得声称未来数据、不得把被驳结论放进 findings。"""
    idx = _j("research/index.json")
    if not idx:
        return
    latest = idx.get("latest") or {}
    briefs = idx.get("briefs") or []
    head = briefs[0] if briefs and isinstance(briefs[0], dict) else {}
    refs = [latest.get("path")] + [b.get("path") for b in briefs[:10] if isinstance(b, dict)]
    for ref in [r for r in refs if r]:
        if not os.path.exists(os.path.join(fl.FEED, ref)):
            flag("critical", "research-dangling", f"research/index.json 指向不存在的简报: {ref}")
    # latest 与 briefs[0] 必须是同一份:alert_scan()、/intel 面板都按 latest 挑最新简报,
    # 一旦它与排序后的列表头分歧,自动化与看板就会指向不同的运行,而这里正是该发现它的地方。
    if latest.get("path") and head.get("path") and latest["path"] != head["path"]:
        flag("critical", "research-latest-drift",
             f"research/index.json 的 latest({latest.get('id')})与 briefs[0]"
             f"({head.get('id')})不是同一份简报,消费方会各挑各的")
    # 选取规则与 alert_scan() / 前端保持一致:latest 优先,briefs[0] 兜底 ——
    # 否则 latest 缺失时语义检查会静默跳过,而消费方仍在读 briefs[0]。
    ref = latest.get("path") or head.get("path")
    brief = _j(ref) if ref else None
    if not brief:
        return
    if brief.get("produced_at") and brief.get("asof_data") \
            and brief["asof_data"] > brief["produced_at"][:10]:
        flag("critical", "future-asof",
             f"简报 {brief.get('id')} 声称 asof_data={brief['asof_data']} 晚于生成时间(未来数据)")
    bad = [c.get("id") for c in (brief.get("findings") or []) if c.get("verdict") != "confirmed"]
    if bad:
        flag("critical", "research-unverified-finding",
             f"简报 {brief.get('id')} 的 findings 含未通过对抗验证的结论: {bad[:5]}")
    if (brief.get("run") or {}).get("lenses_failed"):
        flag("warn", "research-partial",
             f"简报 {brief.get('id')} 有 {brief['run']['lenses_failed']} 个 lens 失败,"
             f"本轮取证不完整,不能按完整覆盖解读")


def check_bundled_snapshot():
    pub = fl.load_json(os.path.join(ROOT, "frontend", "public", "feed", "index.json"))
    cur = _j("index.json")
    if pub and cur:
        lag = _age_days(pub.get("updated_at"))
        if lag and lag > 7:
            flag("info", "bundle-drift",
                 f"捆绑快照 public/feed 落后 {lag:.1f} 天(部署时 CI 会刷新;raw 远端为主源,仅提示)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="写 feed/health.json")
    args = ap.parse_args()

    check_engine_coherence()
    check_freshness()
    check_screener_coherence()
    check_stock_notes()
    check_research_coherence()
    check_bundled_snapshot()

    n_crit = sum(1 for i in issues if i["level"] == "critical")
    n_warn = sum(1 for i in issues if i["level"] == "warn")
    print(f"feed 审计 @ {NOW.strftime('%Y-%m-%d %H:%M UTC')}  critical={n_crit} warn={n_warn} info={len(issues)-n_crit-n_warn}")
    for i in issues:
        mark = {"critical": "✗", "warn": "⚠", "info": "·"}[i["level"]]
        print(f"  {mark} [{i['code']}] {i['message']}")
    if not issues:
        print("  ✓ 全部检查通过")

    if args.write:
        health = {
            "checked_at": fl.now_iso(),
            "ok": n_crit == 0,
            "critical": n_crit, "warn": n_warn,
            "issues": issues,
            "sources": fl._artifact_freshness(),
        }
        fl.save_json(os.path.join(fl.FEED, "health.json"), health)
        print(f"已写 feed/health.json (ok={health['ok']})")
    sys.exit(1 if n_crit else 0)


if __name__ == "__main__":
    main()
