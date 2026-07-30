"""deep_research(深度研究引擎)单测:立题降级、对抗验证、数值防护、发布路径与不覆盖既有面板。

直接 python 运行;全部在临时 feed 根上做,不触碰仓库 feed/。
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys_path = str(pathlib.Path(__file__).resolve().parents[1])
import sys  # noqa: E402

if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

import deep_research as dr  # noqa: E402
import feed_lib as fl  # noqa: E402
import feed_publication as publication  # noqa: E402

REAL_FEED = pathlib.Path(fl.REPO_ROOT) / "feed"

# 夹具日期必须相对「今天」生成:stale-evidence 反驳器按墙上时钟算龄期,
# 写死日期的夹具会在几天后自己过期,让本套件在某个日历日突然变红。
TODAY = datetime.now(timezone.utc).date()


def day_str(back: int) -> str:
    return (TODAY - timedelta(days=back)).isoformat()


def write(path: pathlib.Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def routine_report(day: int, *, asof: str, produced: str, suffix: str = "") -> dict:
    """一份可复现的引擎报告;数值按 day 变化,便于检验趋势与相关性不是常数。"""
    net_sharpe = -0.30 + 0.002 * day
    return {
        "schema_version": "1.0",
        "id": f"routine-{asof}T{2300 + day % 50:04d}{suffix}Z",
        "kind": "routine",
        "produced_at": produced,
        "asof_data": asof,
        "producer": {"name": "github-actions-routine", "agent_role": "engine"},
        "market_state": {
            "regime": "risk_on",
            "spy_above_200dma": True,
            "spy_vol_20d_annual": 0.12 + 0.001 * day,
            "breadth_pct_above_50dma": 0.60 + 0.002 * (day % 7),
            "residual_dispersion": 0.01,
            "crowding_proxy": 0.08 + 0.001 * day,
            "crowding_alert": False,
        },
        "engine": {
            "name": "flowB",
            "period": {"start": "2021-01-04", "end": asof, "trading_days": 1000 + day},
            "gross": {"sharpe": 0.10 + 0.001 * day, "ann_return": 0.003 + 0.0001 * day},
            "net": {"sharpe": net_sharpe, "ann_return": -0.008, "max_drawdown": -0.07},
            "cost_drag_ann": 0.011 + 0.0002 * day,
            "turnover": {"avg_daily": 0.07, "ann_2way": 19.0 + 0.1 * day},
            "train": {"sharpe": -0.19 - 0.001 * day, "n_days": 1000},
            "holdout": {"sharpe": -0.42 - 0.002 * day, "n_days": 393, "start": "2025-01-01"},
            "deflated_sharpe": {"dsr": 0.0003, "p_value": 0.9996, "n_trials": 200},
            "equity_curve": [{"d": asof, "v": 1.0}],
            "verdict": "净口径不可交易",
        },
        "alerts": [{"level": "info", "code": "cointegration_breaker",
                    "message": "60 只标的触发协整断裂熔断(Hurst/半衰期/极端 s),已自动排除。",
                    "tickers": ["ABT", "ACN", "ADI"]}],
        "contribution": {"type": "signal_refresh", "summary": "刷新做多做空簿"},
    }


def build_feed(root: pathlib.Path, *, days: int = 25, with_notes: bool = True) -> str:
    """造一棵最小但连贯的 feed 树。返回最新报告 id。"""
    latest_id = ""
    newest = day_str(1)
    for day in range(days):
        asof = day_str(days - day)          # 最新一期是「昨天」,最旧是 days 天前
        produced = f"{asof}T23:{30 + day % 20:02d}:00Z"
        report = routine_report(day, asof=asof, produced=produced)
        latest_id = report["id"]
        write(root / "reports" / f"{report['id']}.json", report)
    # 同一 asof 的第二份(更早的 produced_at):engine_days() 必须按 produced_at 去重
    duplicate = routine_report(0, asof=newest, produced=f"{newest}T21:00:00Z", suffix="a")
    write(root / "reports" / f"{duplicate['id']}.json", duplicate)
    for day in range(6):
        asof = day_str(6 - day)
        write(root / "reports" / f"factory-local-{asof}T2330Z.json", {
            "schema_version": "1.0", "id": f"factory-local-{asof}T2330Z",
            "kind": "routine", "produced_at": f"{asof}T23:30:00Z", "asof_data": asof,
            "producer": {"name": "factor-factory-local", "agent_role": "factor-factory"},
            "contribution": {"type": "new_factor", "candidates_proposed": 300,
                             "candidates_accepted": 0, "summary": "工厂实跑"},
        })
    dormant = day_str(50)
    write(root / "reports" / f"openclaw-red-team-{dormant}T2334Z.json", {
        "schema_version": "1.0", "id": f"openclaw-red-team-{dormant}T2334Z", "kind": "openclaw",
        "produced_at": f"{dormant}T23:34:06Z", "asof_data": dormant,
        "producer": {"name": "openclaw-agent:red-team", "agent_role": "red-team"},
    })

    write(root / "market" / "state.json", {
        "updated_at": f"{day_str(1)}T23:30:34Z", "asof_data": day_str(1),
        "source_report": latest_id, "regime": "risk_on", "spy_above_200dma": True,
        "spy_vol_20d_annual": 0.12 + 0.001 * (days - 1),
        "breadth_pct_above_50dma": 0.60 + 0.002 * ((days - 1) % 7),
        "residual_dispersion": 0.01, "crowding_proxy": 0.08 + 0.001 * (days - 1),
        "crowding_alert": False,
    })
    write(root / "market" / "history.json",
          [{"date": day_str(1), "at": f"{day_str(1)}T23:38:34+00:00",
            "indices": {"^GSPC": {"close": 7316.15, "change_pct": -2.43}},
            "fng": {"value": 29, "label": "Fear"}}])
    write(root / "signals" / "latest.json", {
        "updated_at": f"{day_str(1)}T23:30:34Z", "source_report": latest_id, "asof": day_str(1),
        "n_long": 2, "n_short": 3, "gross_leverage": 0.06, "net_exposure": -0.01,
        "positions": [
            {"ticker": "ABT", "side": "SHORT", "weight": -0.01, "s_score": 1.1,
             "halflife_days": 6.7, "kappa": 26.0, "hurst": 0.61, "sector": "Health Care"},
            {"ticker": "AVGO", "side": "SHORT", "weight": -0.02, "s_score": 1.7,
             "halflife_days": 8.4, "kappa": 20.8, "hurst": 0.44, "sector": "Information Technology"},
            {"ticker": "T", "side": "SHORT", "weight": -0.01, "s_score": 1.2,
             "halflife_days": 12.4, "kappa": 14.1, "hurst": 0.42, "sector": "Communication Services"},
            {"ticker": "MU", "side": "LONG", "weight": 0.01, "s_score": -1.4,
             "halflife_days": 4.1, "kappa": 41.0, "hurst": 0.31, "sector": "Information Technology"},
            {"ticker": "NVDA", "side": "LONG", "weight": 0.01, "s_score": -1.9,
             "halflife_days": 3.2, "kappa": 54.1, "hurst": 0.22, "sector": "Information Technology"},
        ],
    })
    write(root / "signals" / "rs-ranks.json",
          {"date": day_str(1), "ranks": {f"T{i}": {"rs": i, "w52pos": i} for i in range(1, 61)}})
    write(root / "screener" / "latest.json", {
        "date": day_str(1), "generated_at": f"{day_str(1)}T23:30:33+00:00", "threshold": 80,
        "universe_size": 60, "scanned": 60, "count": 2,
        "items": [{"symbol": "T1", "score": 85, "price": 10.0, "change_pct": 1.0}],
    })
    write(root / "screener" / "scores.json",
          {"date": day_str(1), "scores": {f"T{i}": 100 - i for i in range(1, 61)}})
    write(root / "factory" / "candidates.json", {
        "updated_at": f"{day_str(1)}T23:30:43Z",
        "candidates": [{"expr": f"z(f{i})", "hypothesis": "机器组装假设", "t_stat": 1.5,
                        "incremental_ic": 0.01, "passed_gates": False, "decision": "reject"}
                       for i in range(30)],
    })
    write(root / "crypto" / "state.json", {
        "updated_at": f"{day_str(1)}T23:00:00Z", "source": "hyperliquid",
        "crypto": {"n_perps": 100, "n_liquid": 40, "pct_positive_funding": 0.6,
                   "total_oi_usd": 1e9, "crowding_flag": False,
                   "funding_extremes": [{"coin": "SMALL", "funding_apr": 4.0, "oi_usd": 9.5e6},
                                        {"coin": "BTC", "funding_apr": 0.1, "oi_usd": 2.1e9}]},
        "venues": {"n_compared": 232, "n_dislocated": 72, "threshold_apr": 0.1, "top": []},
        "errors": [],
    })
    write(root / "intraday" / "latest.json", {
        "at": f"{day_str(1)}T14:56:22+00:00", "pool_size": 130, "quoted": 130,
        "producer": "actions", "summary": {"up": 52, "down": 78, "median_pct": -0.55},
        "events": [], "snapshot": [],
    })
    if with_notes:
        write(root / "stock-notes" / "index.json", {
            "updated_at": f"{day_str(1)}T01:00:00Z", "note": "测试",
            "symbols": [{"symbol": f"US:S{i}", "date": day_str(1) if i < 20 else day_str(9),
                         "stance": "看多"} for i in range(40)],
        })
        write(root / "stock-notes" / "stance-history.json",
              [{"date": day_str(d),
                "stances": {f"US:S{i}": ("看多" if (i + d) % 3 else "中性") for i in range(40)}}
               for d in range(9, 0, -1)])
    write(root / "index.json", {
        "schema_version": "1.0", "updated_at": f"{day_str(1)}T23:30:44Z",
        "freshness": {"last_report_at": f"{day_str(1)}T23:30:44Z", "stale": False},
        "latest": {"report": f"reports/{latest_id}.json"},
        "stats": {"total_reports": 500, "by_kind": {"routine": 500}, "by_producer": {},
                  "last_24h": 3, "last_7d": 10},
        "timeline": {}, "reports": [{"id": latest_id}], "contributions": [],
    })
    write(root / "health.json", {"checked_at": f"{day_str(1)}T23:40:00Z", "ok": True,
                                 "critical": 0, "warn": 1, "issues": [], "sources": {}})
    return latest_id


class DeepResearchTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name)
        self.feed = self.repo / "feed"
        self.latest_id = build_feed(self.feed)
        # schema 从真实仓库拷入,保证测的是将要发布的那份契约
        (self.feed / "schema").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_FEED / "schema" / "research.schema.json",
                        self.feed / "schema" / "research.schema.json")
        self.patches = [
            mock.patch.object(fl, "FEED", str(self.feed)),
            mock.patch.object(fl, "REPO_ROOT", str(self.repo)),
            mock.patch.object(dr, "RESEARCH_SCHEMA_PATH",
                              str(self.feed / "schema" / "research.schema.json")),
        ]
        for patch in self.patches:
            patch.start()
        self.addCleanup(self._stop)

    def _stop(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def brief(self, **kwargs) -> dict:
        options = {"roles": dr.ROLES, "workers": 4, "report_limit": 120, "quiet": True}
        options.update(kwargs)
        return dr.run(options["roles"], options["workers"], options["report_limit"], options["quiet"])


class TestPipeline(DeepResearchTestCase):
    def test_run_produces_schema_valid_brief(self):
        brief = self.brief()
        ok, errors = dr.validate_brief(brief)
        self.assertTrue(ok, msg=str(errors))
        self.assertEqual(brief["kind"], "deep-research")
        self.assertEqual(brief["producer"]["method"], "deterministic-no-llm")
        self.assertEqual(brief["schema_version"], "1.0")
        self.assertGreaterEqual(len(brief["questions"]), 10)
        self.assertGreater(len(brief["findings"]), 0)
        self.assertEqual(brief["run"]["lenses_failed"], 0)

    def test_every_question_declares_dependencies_and_test(self):
        for question in self.brief()["questions"]:
            self.assertTrue(question["needs"], msg=question["id"])
            self.assertTrue(question["test"], msg=question["id"])
            self.assertTrue(question["triggered_by"], msg=question["id"])
            self.assertIn(question["role"], dr.ROLES)

    def test_findings_are_confirmed_only_and_counts_agree(self):
        brief = self.brief()
        self.assertTrue(all(c["verdict"] == "confirmed" for c in brief["findings"]))
        self.assertTrue(all(c["verdict"] != "confirmed" for c in brief["refuted"]))
        self.assertEqual(brief["verdicts"]["confirmed"], len(brief["findings"]))
        self.assertEqual(brief["verdicts"]["refuted"] + brief["verdicts"]["unverified"],
                         len(brief["refuted"]))

    def test_every_claim_carries_sourced_evidence(self):
        brief = self.brief()
        for c in brief["findings"]:
            self.assertTrue(c["evidence"], msg=c["id"])
            for item in c["evidence"]:
                self.assertTrue(item["artifact"], msg=c["id"])
                self.assertTrue(item["field"], msg=c["id"])
                self.assertIsNotNone(item["value"], msg=f"{c['id']} 证据取值不得为 None")

    def test_claim_ids_are_unique_and_stable_under_reordering(self):
        first, second = self.brief(), self.brief()
        ids = [c["id"] for c in first["findings"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([c.get("metric") for c in first["findings"]],
                         [c.get("metric") for c in second["findings"]])

    def test_id_minute_and_produced_at_share_one_clock_read(self):
        """id 的分钟必须与 produced_at 同源:分两次读时钟,跨一个 UTC 分钟就会不一致。

        用 patch 掉 fl.now_iso 来证明 produced_at 不是第二次读取的产物 —— 修复前它正是。
        """
        with mock.patch.object(fl, "now_iso", return_value="1999-01-01T00:00:00Z"):
            brief = self.brief()
        self.assertNotEqual(brief["produced_at"], "1999-01-01T00:00:00Z")
        produced = brief["produced_at"]
        self.assertEqual(brief["id"], f"deep-research-{produced[:13]}{produced[14:16]}Z")
        self.assertLessEqual(brief["asof_data"], produced[:10])   # today 也来自同一次读取

    def test_output_is_independent_of_thread_count(self):
        """并发只是取证的实现细节:线程完成顺序不得泄漏进简报,否则简报不可复现。"""
        def normalize(brief: dict) -> str:
            copy = json.loads(json.dumps(brief))
            for key in ("produced_at", "id", "asof_data"):
                copy.pop(key, None)
            for key in ("duration_ms", "workers"):
                copy["run"].pop(key, None)
            return json.dumps(copy, ensure_ascii=False, sort_keys=True)

        shapes = {normalize(self.brief(workers=w)) for w in (1, 3, 8)}
        self.assertEqual(len(shapes), 1, msg="不同并发度产出了不同简报")

    def test_role_filter_reports_disabled_questions(self):
        brief = self.brief(roles=("engine",))
        self.assertEqual(brief["run"]["roles"], ["engine"])
        self.assertTrue(all(c["role"] == "engine" for c in brief["findings"]))
        disabled = [q for q in brief["open_questions"] if q["reason"] == "role-disabled"]
        self.assertTrue(disabled)

    def test_missing_artifact_degrades_to_open_question(self):
        os.remove(self.feed / "signals" / "latest.json")
        brief = self.brief()
        reasons = {q["id"]: q for q in brief["open_questions"]}
        self.assertIn("q-book-mean-reversion", reasons)
        self.assertEqual(reasons["q-book-mean-reversion"]["reason"], "missing-input")
        self.assertTrue(any("signals/latest.json" in m
                            for m in reasons["q-book-mean-reversion"]["missing"]))
        self.assertEqual(brief["run"]["lenses_failed"], 0)
        self.assertGreater(brief["coverage"]["artifacts_missing"], 0)
        ok, errors = dr.validate_brief(brief)
        self.assertTrue(ok, msg=str(errors))

    def test_absent_date_fields_degrade_instead_of_raising(self):
        """选股系面板都没有 date 时必须降级为 missing-input,不能抛 IndexError。"""
        for rel in ("screener/latest.json", "signals/rs-ranks.json", "screener/scores.json"):
            path = self.feed / rel
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.pop("date", None)
            write(path, payload)
        brief = self.brief()
        self.assertEqual(brief["run"]["lenses_failed"], 0)
        reasons = {q["id"]: q["reason"] for q in brief["open_questions"]}
        self.assertEqual(reasons.get("q-screener-date-skew"), "missing-input")

    def test_lens_exception_is_isolated_and_recorded(self):
        broken = {"id": "q-broken", "role": "risk", "title": "坏 lens", "needs": ["x"],
                  "test": "t", "triggered_by": "t",
                  "fn": lambda corpus: (_ for _ in ()).throw(RuntimeError("boom"))}
        with mock.patch.object(dr, "LENSES", dr.LENSES + [broken]):
            brief = self.brief()
        self.assertEqual(brief["run"]["lenses_failed"], 1)
        errored = [q for q in brief["open_questions"] if q["reason"] == "lens-error"]
        self.assertEqual([q["id"] for q in errored], ["q-broken"])
        self.assertGreater(len(brief["findings"]), 0)

    def test_no_open_question_is_silently_dropped(self):
        brief = self.brief()
        answered = {q["id"] for q in brief["questions"] if q["answered"]}
        unanswered = {q["id"] for q in brief["questions"] if not q["answered"]}
        recorded = {q["id"] for q in brief["open_questions"]}
        self.assertTrue(unanswered <= recorded)
        self.assertFalse(answered & recorded)


class TestRefuters(DeepResearchTestCase):
    def synth(self, **kwargs) -> dict:
        base = {"role": "risk", "question": "q", "statement": "s",
                "evidence": (dr.ev("feed/x.json", "f", 1.0, day_str(1)),)}
        base.update(kwargs)
        return dr.claim(base.pop("role"), base.pop("question"), base.pop("statement"), **base)

    def test_missing_evidence_refutes(self):
        empty = self.synth(evidence=())
        null = self.synth(evidence=(dr.ev("feed/x.json", "f", None, day_str(1)),))
        dr.verify([empty, null], day_str(0))
        self.assertEqual(empty["verdict"], "refuted")
        self.assertEqual(null["verdict"], "refuted")
        self.assertIn("missing-evidence", {r["code"] for r in null["refutations"]})

    def test_absent_marker_is_valid_evidence(self):
        c = self.synth(evidence=(dr.ev("feed/x.json", "candidates[].pbo", "absent", day_str(1)),))
        dr.verify([c], day_str(0))
        self.assertEqual(c["verdict"], "confirmed")

    def test_insufficient_sample_refutes(self):
        c = self.synth(n=4, min_n=10)
        dr.verify([c], day_str(0))
        self.assertEqual(c["verdict"], "refuted")
        self.assertIn("insufficient-sample", {r["code"] for r in c["refutations"]})

    def test_within_noise_band_refutes(self):
        weak = self.synth(value=0.2, noise_band=0.3)
        strong = self.synth(value=0.9, noise_band=0.3)
        dr.verify([weak, strong], day_str(0))
        self.assertEqual(weak["verdict"], "refuted")
        self.assertEqual(strong["verdict"], "confirmed")

    def test_stale_evidence_is_unverified_not_refuted(self):
        c = self.synth(evidence=(dr.ev("feed/x.json", "f", 1.0, "2020-01-01"),), max_age_days=10.0)
        dr.verify([c], day_str(0))
        self.assertEqual(c["verdict"], "unverified")
        self.assertEqual({r["code"] for r in c["refutations"]}, {"stale-evidence"})

    def test_future_asof_refutes(self):
        c = self.synth(evidence=(dr.ev("feed/x.json", "f", 1.0, "2099-01-01"),), max_age_days=None)
        dr.verify([c], day_str(0))
        self.assertEqual(c["verdict"], "refuted")
        self.assertIn("future-asof", {r["code"] for r in c["refutations"]})

    def test_contradictory_claims_refute_each_other(self):
        up = self.synth(metric="m.same", value=1.0, direction="up")
        down = self.synth(metric="m.same", value=-1.0, direction="down")
        alone = self.synth(metric="m.other", value=1.0, direction="up")
        dr.verify([up, down, alone], day_str(0))
        self.assertEqual(up["verdict"], "refuted")
        self.assertEqual(down["verdict"], "refuted")
        self.assertEqual(alone["verdict"], "confirmed")

    def test_clean_claim_is_confirmed(self):
        c = self.synth(n=50, min_n=10, value=0.9, noise_band=0.3)
        dr.verify([c], day_str(0))
        self.assertEqual(c["verdict"], "confirmed")
        self.assertEqual(c["refutations"], [])

    def test_alerts_only_come_from_confirmed_claims(self):
        brief = self.brief()
        statements = {c["statement"] for c in brief["findings"]}
        for alert in brief["alerts"]:
            self.assertIn(alert["message"], statements)
            self.assertIn(alert["level"], ("warning", "critical"))


class TestNumericGuards(DeepResearchTestCase):
    def test_num_rejects_nonfinite(self):
        self.assertIsNone(dr._num(float("nan")))
        self.assertIsNone(dr._num(float("inf")))
        self.assertIsNone(dr._num("abc"))
        self.assertIsNone(dr._num(None))
        self.assertEqual(dr._num(1 / 3, 4), 0.3333)

    def test_spearman_degenerate_returns_none_not_nan(self):
        self.assertIsNone(dr.spearman([1.0, 2.0], [1.0, 2.0]))
        self.assertIsNone(dr.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]))
        self.assertIsNone(dr.spearman([1.0, 2.0, 3.0], [1.0, 2.0]))
        self.assertEqual(dr.spearman([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0)
        self.assertEqual(dr.spearman([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]), -1.0)

    def test_spearman_handles_ties(self):
        rho = dr.spearman([1.0, 1.0, 2.0, 3.0], [1.0, 2.0, 2.0, 4.0])
        self.assertIsNotNone(rho)
        self.assertGreater(rho, 0.0)

    def test_ols_slope_guards(self):
        self.assertIsNone(dr.ols_slope([1.0, 2.0]))
        self.assertEqual(dr.ols_slope([1.0, 2.0, 3.0, 4.0]), 1.0)
        self.assertEqual(dr.ols_slope([5.0, 5.0, 5.0]), 0.0)

    def test_brief_is_json_serializable_without_nan(self):
        brief = self.brief()
        payload = fl.json_file_bytes(brief).decode("utf-8")
        self.assertNotIn("NaN", payload)
        self.assertNotIn("Infinity", payload)
        json.loads(payload, parse_constant=fl.reject_json_constant)

    def test_engine_days_deduplicates_same_asof_keeping_latest(self):
        corpus = dr.Corpus(report_limit=120)
        days = corpus.engine_days()
        asofs = [d["asof_data"] for d in days]
        self.assertEqual(len(asofs), len(set(asofs)))
        self.assertEqual(asofs, sorted(asofs))
        # 夹具为最新一天写了两份(23:xx 与 21:00);必须保留 produced_at 更大的那份
        newest = days[-1]
        self.assertEqual(newest["asof_data"], day_str(1))
        self.assertGreater(newest["produced_at"], f"{day_str(1)}T21:00:00Z")

    def _claim(self, brief: dict, qid: str) -> dict | None:
        for bucket in ("findings", "refuted"):
            for c in brief.get(bucket) or []:
                if c.get("question") == qid:
                    return c
        return None

    def _repoint_book_at_an_older_report(self) -> tuple[str, str]:
        """把簿指向一份更旧的报告,并让新旧两份的熔断名单给出不同答案。

        返回 (簿的来源报告 id, 更新的报告 id)。
        """
        older_id = ""
        for path in sorted((self.feed / "reports").glob("routine-*.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("asof_data") == day_str(3) and not report["id"].endswith("aZ"):
                report["alerts"] = [{"level": "info", "code": "cointegration_breaker",
                                     "message": "熔断", "tickers": ["ABT", "AVGO"]}]
                write(path, report)
                older_id = report["id"]
        self.assertTrue(older_id, "夹具里没有 asof=T-3 的 routine 报告")
        for path in sorted((self.feed / "reports").glob("routine-*.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("asof_data") == day_str(1):
                report["alerts"] = [{"level": "info", "code": "cointegration_breaker",
                                     "message": "熔断", "tickers": ["ZZZ"]}]
                write(path, report)
        book = json.loads((self.feed / "signals" / "latest.json").read_text(encoding="utf-8"))
        book["source_report"] = older_id
        write(self.feed / "signals" / "latest.json", book)
        return older_id, self.latest_id

    def test_breaker_lens_follows_the_book_source_report_not_the_newest_run(self):
        """簿与报告是两个独立写手。簿停在上一班时,必须拿它自报的那一班比对,

        否则就把 A 轮的熔断名单算到 B 轮的簿头上 —— 结论里的报告 id 会是假归因。
        """
        older_id, newest_id = self._repoint_book_at_an_older_report()
        self.assertNotEqual(older_id, newest_id)
        claim = self._claim(self.brief(), "q-book-vs-breaker")
        self.assertIsNotNone(claim, "熔断 lens 没有出结论")
        # 旧报告名单 ABT/AVGO 与簿有 2 只交集;最新报告名单 ZZZ 与簿交集为 0。
        # 读错来源就会得到 0,并在文案里写上最新报告的 id。
        self.assertEqual(claim["value"], 2)
        self.assertTrue(claim["statement"].startswith(f"簿自报来源报告 {older_id},"),
                        msg=claim["statement"])
        # 更新的那一班只能作为「簿尚未跟到」的注记出现,不能成为被归因的来源
        self.assertIn(f"更晚还有一份引擎报告 {newest_id}", claim["statement"])
        artifacts = [e["artifact"] for e in claim["evidence"]]
        self.assertIn(f"feed/reports/{older_id}.json", artifacts)
        self.assertNotIn(f"feed/reports/{newest_id}.json", artifacts)

    def test_breaker_lens_degrades_when_the_book_source_report_is_unusable(self):
        for bad in (None, "../../etc/passwd", f"routine-{day_str(400)}T2330Z"):
            with self.subTest(source=bad):
                book = json.loads((self.feed / "signals" / "latest.json").read_text(encoding="utf-8"))
                if bad is None:
                    book.pop("source_report", None)
                else:
                    book["source_report"] = bad
                write(self.feed / "signals" / "latest.json", book)
                brief = self.brief()
                self.assertEqual(brief["run"]["lenses_failed"], 0)
                reasons = {q["id"]: q["reason"] for q in brief["open_questions"]}
                self.assertEqual(reasons.get("q-book-vs-breaker"), "missing-input")

    def test_fixture_dates_are_relative_so_the_suite_cannot_expire(self):
        """夹具最新证据必须落在默认时效上限内,否则本套件会在某个日历日自己变红。"""
        self.assertLess(dr._age_days(f"{day_str(1)}T23:30:00Z"), 10.0)
        brief = self.brief()
        stale = [c for c in brief["refuted"]
                 if any(r["code"] == "stale-evidence" for r in c["refutations"])]
        self.assertEqual(stale, [], msg="夹具证据已超时,说明日期又被写死了")


class TestPublish(DeepResearchTestCase):
    def test_brief_only_writes_brief_and_index(self):
        brief = self.brief()
        self.assertEqual(dr.publish(brief, brief_only=True, quiet=True), 0)
        path = self.feed / "research" / f"{brief['id']}.json"
        self.assertTrue(path.exists())
        index = json.loads((self.feed / "research" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["stats"]["total_briefs"], 1)
        self.assertEqual(index["latest"]["id"], brief["id"])
        self.assertEqual(index["briefs"][0]["path"], f"research/{brief['id']}.json")
        self.assertFalse((self.feed / "reports" / f"{brief['id']}.json").exists())

    def test_full_publish_adds_report_without_clobbering_panels(self):
        market_before = (self.feed / "market" / "state.json").read_bytes()
        book_before = (self.feed / "signals" / "latest.json").read_bytes()
        brief = self.brief()
        self.assertEqual(dr.publish(brief, brief_only=False, quiet=True), 0)
        report = json.loads((self.feed / "reports" / f"{brief['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(report["kind"], "routine")
        self.assertNotIn("market_state", report)
        self.assertNotIn("book", report)
        self.assertNotIn("factory_candidates", report)
        self.assertEqual(report["producer"]["name"], "deep-research-engine")
        self.assertEqual((self.feed / "market" / "state.json").read_bytes(), market_before)
        self.assertEqual((self.feed / "signals" / "latest.json").read_bytes(), book_before)

    def test_report_alerts_mirror_brief_alerts(self):
        brief = self.brief()
        dr.publish(brief, brief_only=False, quiet=True)
        report = json.loads((self.feed / "reports" / f"{brief['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(report["alerts"], brief["alerts"])
        expected = "risk_alert" if brief["alerts"] else "no_change"
        self.assertEqual(report["contribution"]["type"], expected)

    def test_index_summary_caps_at_max_index_briefs(self):
        brief = self.brief()
        dr.publish(brief, brief_only=True, quiet=True)
        template = json.loads((self.feed / "research" / f"{brief['id']}.json").read_text(encoding="utf-8"))
        for i in range(fl.MAX_INDEX_BRIEFS + 3):
            clone = dict(template)
            clone["id"] = f"deep-research-2026-06-{(i % 28) + 1:02d}T{i:04d}Z"
            clone["produced_at"] = f"2026-06-{(i % 28) + 1:02d}T{i % 24:02d}:00:00Z"
            write(self.feed / "research" / f"{clone['id']}.json", clone)
        index = dr.rebuild_research_index()
        self.assertGreater(index["stats"]["total_briefs"], fl.MAX_INDEX_BRIEFS)
        self.assertEqual(len(index["briefs"]), fl.MAX_INDEX_BRIEFS)

    def test_index_latest_equals_first_brief_summary(self):
        """latest 与 briefs[0] 必须逐字段一致 —— 前端与 alert_scan 都按 latest 挑,
        两者一旦分歧就会出现看板与自动化指向不同简报。"""
        first = self.brief()
        dr.publish(first, brief_only=True, quiet=True)
        template = json.loads((self.feed / "research" / f"{first['id']}.json").read_text(encoding="utf-8"))
        for i in range(3):                       # 再塞几份,确保排序参与进来
            clone = dict(template)
            clone["id"] = f"deep-research-2026-06-{i + 1:02d}T{i:04d}Z"
            clone["produced_at"] = f"2026-06-{i + 1:02d}T0{i}:00:00Z"
            write(self.feed / "research" / f"{clone['id']}.json", clone)
        index = dr.rebuild_research_index()
        self.assertEqual(index["latest"], index["briefs"][0])
        self.assertEqual(index["latest"]["id"], first["id"])   # produced_at 最大的那份

    def test_index_ignores_foreign_json(self):
        brief = self.brief()
        dr.publish(brief, brief_only=True, quiet=True)
        write(self.feed / "research" / "not-a-brief.json", {"hello": "world"})
        index = dr.rebuild_research_index()
        self.assertEqual(index["stats"]["total_briefs"], 1)

    def test_index_survives_a_malformed_brief(self):
        """一份坏简报不得把整个族索引卡死 —— 索引是 feed 唯一的族入口。"""
        brief = self.brief()
        dr.publish(brief, brief_only=True, quiet=True)
        for name, payload in (
            ("broken-no-verdicts.json", {"id": "deep-research-broken-1", "kind": "deep-research",
                                         "produced_at": f"{day_str(0)}T00:00:00Z"}),
            ("broken-bad-id.json", {"id": "../escape", "kind": "deep-research",
                                    "produced_at": f"{day_str(0)}T00:00:00Z", "verdicts": {}}),
            ("broken-root-list.json", [1, 2, 3]),
            ("broken-null-produced.json", {"id": "deep-research-broken-2", "kind": "deep-research",
                                           "produced_at": None, "verdicts": {}}),
        ):
            write(self.feed / "research" / name, payload)
        index = dr.rebuild_research_index()
        self.assertEqual(index["stats"]["total_briefs"], 1)
        self.assertEqual(index["latest"]["id"], brief["id"])

    def test_claims_omit_uninformative_optional_keys(self):
        brief = self.brief()
        for c in brief["findings"] + brief["refuted"]:
            for key in ("n", "noise_band", "max_age_days", "min_n", "severity",
                        "direction", "unit", "cites"):
                if key in c:
                    self.assertIsNotNone(c[key], msg=f"{c['id']}.{key} 不该以 null 形式存在")
            self.assertNotEqual(c.get("severity"), "none")
            self.assertNotEqual(c.get("direction"), "none")
            self.assertNotEqual(c.get("unit"), "none")

    def test_signature_round_trips_when_secret_is_set(self):
        brief = self.brief()
        with mock.patch.dict(os.environ, {"FEED_HMAC_SECRET": "测试-secret"}, clear=False):
            self.assertEqual(dr.publish(brief, brief_only=True, quiet=True), 0)
        stored = json.loads((self.feed / "research" / f"{brief['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["signature"]["alg"], "HMAC-SHA256")
        self.assertTrue(fl.verify_signature(stored, "测试-secret"))
        self.assertFalse(fl.verify_signature(stored, "wrong"))

    def test_publication_manifest_records_written_paths(self):
        manifest = self.repo / "manifest.json"
        (self.repo / ".git").mkdir(exist_ok=True)
        brief = self.brief()
        with mock.patch.dict(os.environ, {"FEED_PUBLICATION_MANIFEST": str(manifest)}, clear=False), \
                mock.patch.object(publication, "REPO_ROOT", self.repo), \
                mock.patch.object(publication, "FEED_ROOT", self.feed):
            self.assertEqual(dr.publish(brief, brief_only=True, quiet=True), 0)
        recorded = json.loads(manifest.read_text(encoding="utf-8"))["paths"]
        self.assertIn(f"feed/research/{brief['id']}.json", recorded)
        self.assertIn("feed/research/index.json", recorded)
        self.assertTrue(all(not p.startswith("/") and ".." not in p for p in recorded))

    def test_research_path_rejects_escaping_ids(self):
        for bad in ("../../etc/passwd", "a/b", "short", "x" * 200, ""):
            with self.assertRaises(ValueError, msg=bad):
                fl.research_path(bad)
        good = fl.research_path("deep-research-2026-07-30T0512Z")
        self.assertEqual(pathlib.Path(good).parent, (self.feed / "research").resolve())

    def test_validate_brief_rejects_unverified_finding(self):
        brief = self.brief()
        brief["findings"][0] = dict(brief["findings"][0], verdict="refuted")
        ok, errors = dr.validate_brief(brief)
        self.assertFalse(ok, msg=str(errors))

    def test_validate_brief_rejects_llm_provenance_claim(self):
        brief = self.brief()
        brief["producer"]["method"] = "llm"
        ok, _ = dr.validate_brief(brief)
        self.assertFalse(ok)

    def test_required_field_fallback_runs_without_jsonschema(self):
        real_import = __import__

        def blocked(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        brief = self.brief()
        with mock.patch("builtins.__import__", side_effect=blocked):
            ok, errors = dr.validate_brief(brief)
            self.assertTrue(ok, msg=str(errors))
            broken = dict(brief)
            broken.pop("verdicts")
            bad_ok, bad_errors = dr.validate_brief(broken)
            self.assertFalse(bad_ok)
            self.assertTrue(any("verdicts" in e for e in bad_errors))


class TestFallbackValidator(DeepResearchTestCase):
    """定时 workflow 不装依赖,走的就是退化校验 —— 它必须挡住简报能撒的谎。"""

    def assert_rejected(self, mutate, needle: str):
        brief = self.brief()
        mutate(brief)
        ok, errors = dr._validate_brief_fallback(brief)
        self.assertFalse(ok, msg="退化校验放过了应当拒收的简报")
        self.assertTrue(any(needle in e for e in errors), msg=f"{needle} 不在 {errors}")

    def test_clean_brief_passes(self):
        ok, errors = dr._validate_brief_fallback(self.brief())
        self.assertTrue(ok, msg=str(errors))

    def test_rejects_llm_provenance(self):
        self.assert_rejected(lambda b: b["producer"].__setitem__("method", "llm"), "deterministic-no-llm")

    def test_rejects_unconfirmed_finding(self):
        self.assert_rejected(lambda b: b["findings"][0].__setitem__("verdict", "unverified"),
                             "findings 不允许")

    def test_rejects_confirmed_claim_inside_refuted(self):
        def mutate(b):
            if not b["refuted"]:
                b["refuted"].append(dict(b["findings"][0]))
            b["refuted"][0]["verdict"] = "confirmed"
        self.assert_rejected(mutate, "refuted 不允许")

    def test_rejects_verdict_count_mismatch(self):
        self.assert_rejected(lambda b: b["verdicts"].__setitem__("confirmed", 999), "不一致")

    def test_rejects_duplicate_claim_id(self):
        self.assert_rejected(lambda b: b["findings"][1].__setitem__("id", b["findings"][0]["id"]),
                             "重复")

    def test_rejects_unknown_role(self):
        self.assert_rejected(lambda b: b["findings"][0].__setitem__("role", "oracle"), "role 非法")

    def test_rejects_evidence_without_source(self):
        self.assert_rejected(lambda b: b["findings"][0]["evidence"].__setitem__(0, {"value": 1}),
                             "证据缺 artifact/field")

    def test_rejects_future_asof(self):
        self.assert_rejected(lambda b: b.__setitem__("asof_data", "2099-01-01"),
                             "不得晚于 produced_at")

    def test_rejects_malformed_asof(self):
        self.assert_rejected(lambda b: b.__setitem__("asof_data", "yesterday"), "YYYY-MM-DD")

    def test_rejects_non_finite_number(self):
        self.assert_rejected(lambda b: b["findings"][0].__setitem__("value", float("inf")),
                             "非法 JSON 数值")

    def test_asof_data_is_the_newest_evidence_date_not_the_run_date(self):
        brief = self.brief()
        dates = [item["asof"][:10] for c in brief["findings"] + brief["refuted"]
                 for item in (c.get("evidence") or []) if item.get("asof")]
        self.assertEqual(brief["asof_data"], max(d for d in dates if d <= day_str(0)))
        self.assertLessEqual(brief["asof_data"], brief["produced_at"][:10])


class TestAlertScan(DeepResearchTestCase):
    """告警扫描是 workflow 开 Issue 的唯一依据:读不到必须与「读到但无 critical」区分开。"""

    def scan(self) -> list[str]:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = dr.alert_scan()
        self.assertEqual(code, 0, msg="扫描不得让已完成发布的任务变红")
        lines = buffer.getvalue().splitlines()
        self.assertEqual(len(lines), 4, msg=f"必须恰好四行,实得 {lines}")
        return lines

    def test_missing_index_is_not_reported_as_no_alerts(self):
        status, count, _, _ = self.scan()
        self.assertEqual(status, "no-index")
        self.assertEqual(count, "0")

    def test_empty_index_reports_no_brief(self):
        write(self.feed / "research" / "index.json",
              {"schema_version": "1.0", "updated_at": f"{day_str(0)}T00:00:00Z",
               "latest": None, "briefs": []})
        self.assertEqual(self.scan()[0], "no-brief")

    def test_dangling_latest_path_reports_unreadable_not_clean(self):
        write(self.feed / "research" / "index.json",
              {"latest": {"path": "research/gone.json"}, "briefs": []})
        self.assertEqual(self.scan()[0], "no-brief")

    def test_corrupt_index_is_reported(self):
        (self.feed / "research").mkdir(parents=True, exist_ok=True)
        (self.feed / "research" / "index.json").write_text("{not json", encoding="utf-8")
        self.assertTrue(self.scan()[0].startswith("unreadable-index:"))

    def test_published_brief_without_critical_reports_zero(self):
        brief = self.brief()
        brief["alerts"] = [a for a in brief["alerts"] if a["level"] != "critical"]
        dr.publish(brief, brief_only=True, quiet=True)
        status, count, brief_id, message = self.scan()
        self.assertEqual(status, "ok")
        self.assertEqual(count, "0")
        self.assertEqual(brief_id, brief["id"])
        self.assertEqual(message, "")

    def test_critical_alert_message_is_collapsed_to_one_line(self):
        brief = self.brief()
        brief["alerts"] = [{"level": "critical", "code": "x",
                            "message": 'a "quoted" `tick` $VAR\nsecond line\ttab', "tickers": []}]
        dr.publish(brief, brief_only=True, quiet=True)
        status, count, brief_id, message = self.scan()
        self.assertEqual((status, count, brief_id), ("ok", "1", brief["id"]))
        self.assertEqual(message, 'a "quoted" `tick` $VAR second line tab')

    def test_latest_wins_over_briefs_list(self):
        first = self.brief()
        dr.publish(first, brief_only=True, quiet=True)
        index = fl.load_json(str(self.feed / "research" / "index.json"))
        index["briefs"] = [{"path": "research/decoy.json", "id": "deep-research-decoy"}]
        write(self.feed / "research" / "index.json", index)
        write(self.feed / "research" / "decoy.json",
              {"id": "deep-research-decoy", "kind": "deep-research",
               "alerts": [{"level": "critical", "message": "decoy"}]})
        self.assertEqual(self.scan()[2], first["id"])


class TestCliResolution(DeepResearchTestCase):
    def test_roles_resolution_prefers_flag_then_env(self):
        with mock.patch.dict(os.environ, {"DEEP_RESEARCH_ROLES": "risk"}, clear=False):
            self.assertEqual(dr._resolve_roles(None), ("risk",))
            self.assertEqual(dr._resolve_roles("engine,risk"), ("engine", "risk"))
        with mock.patch.dict(os.environ, {"DEEP_RESEARCH_ROLES": ""}, clear=False):
            self.assertEqual(dr._resolve_roles(None), dr.ROLES)

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(SystemExit):
            dr._resolve_roles("not-a-role")

    def test_workers_resolution_clamps_and_degrades(self):
        with mock.patch.dict(os.environ, {"DEEP_RESEARCH_WORKERS": "3"}, clear=False):
            self.assertEqual(dr._resolve_workers(None), 3)
        with mock.patch.dict(os.environ, {"DEEP_RESEARCH_WORKERS": "abc"}, clear=False):
            self.assertEqual(dr._resolve_workers(None), dr.DEFAULT_WORKERS)
        with mock.patch.dict(os.environ, {"DEEP_RESEARCH_WORKERS": ""}, clear=False):
            self.assertEqual(dr._resolve_workers(None), dr.DEFAULT_WORKERS)
        self.assertEqual(dr._resolve_workers(0), 1)
        self.assertEqual(dr._resolve_workers(9999), dr.MAX_WORKERS)

    def test_roles_are_repository_vocabulary(self):
        import openclaw_client  # noqa: PLC0415  只在此断言词表一致性

        self.assertTrue(set(openclaw_client.ROLES) <= set(dr.ROLES) | {"factor-factory"})
        for role in openclaw_client.ROLES:
            self.assertIn(role, dr.ROLES, msg=f"{role} 不在 deep_research.ROLES 里")


if __name__ == "__main__":
    unittest.main(verbosity=2)
