"""feed/ 情报馈送的共享读写 / 校验 / 签名库。

被三方复用:
  - scripts/run_routine.py    : 本仓 GitHub Actions 例行任务写报告。
  - scripts/openclaw_client.py : 外部 OpenClaw agent 投递报告(参考实现)。
  - scripts/validate_feed.py   : CI 校验 inbox 投递(schema + 签名)。

设计:feed/ 是「静态网页不断接受」的单一真相源 —— 都是 JSON,GitHub raw / Pages 直接可取。
无第三方强依赖;若安装了 jsonschema 则做完整 schema 校验,否则退化为必填字段校验。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(REPO_ROOT, "feed")
SCHEMA_PATH = os.path.join(FEED, "schema", "report.schema.json")

REPORT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{6,80}$")

MAX_INDEX_REPORTS = 60        # index.json 中保留的最近报告条数
MAX_INDEX_BRIEFS = 60         # research/index.json 中保留的最近简报摘要条数
MAX_CONTRIB = 80              # 贡献日志保留条数
STALE_HOURS = 36             # 超过此时长无更新 -> 看板标「陈旧」


# ----------------------------- 基础 IO -----------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant is forbidden: {value}")


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_json_constant)


def json_file_bytes(obj: object) -> bytes:
    text = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
        allow_nan=False,
    ) + "\n"
    return text.encode("utf-8")


def record_publication_path(path: str | os.PathLike[str]) -> None:
    """Record a successfully closed feed artifact when publication is configured."""
    if not os.environ.get("FEED_PUBLICATION_MANIFEST"):
        return
    from feed_publication import record_written_path

    record_written_path(path)


def save_json(path: str, obj: object) -> None:
    payload = json_file_bytes(obj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)
    record_publication_path(path)


def canonical_json(obj: object) -> str:
    """用于签名的确定性严格 JSON 序列化。"""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


# ----------------------------- 签名(HMAC)-----------------------------

def sign_report(report: dict, secret: str, key_id: str = "default") -> dict:
    """对去除 signature 字段后的报告做 HMAC-SHA256,写回 report['signature']。"""
    body = {k: v for k, v in report.items() if k != "signature"}
    mac = hmac.new(secret.encode(), canonical_json(body).encode(), hashlib.sha256).hexdigest()
    report["signature"] = {"alg": "HMAC-SHA256", "key_id": key_id, "value": mac}
    return report


def verify_signature(report: dict, secret: str) -> bool:
    sig = report.get("signature")
    if not isinstance(sig, dict) or sig.get("alg") != "HMAC-SHA256":
        return False
    body = {k: v for k, v in report.items() if k != "signature"}
    expect = hmac.new(secret.encode(), canonical_json(body).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, str(sig.get("value", "")))


# ----------------------------- 校验 -----------------------------

def validate_report(report: dict) -> tuple[bool, list[str]]:
    """优先用 jsonschema 全量校验;无则退化为必填字段 + 取值域检查。"""
    try:
        import jsonschema  # type: ignore
        schema = load_json(SCHEMA_PATH)
        v = jsonschema.Draft7Validator(schema)
        errs = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(report)]
        return (len(errs) == 0, errs)
    except ImportError:
        errs = []
        for k in ("schema_version", "id", "kind", "produced_at", "producer", "asof_data"):
            if k not in report:
                errs.append(f"缺少必填字段: {k}")
        if report.get("schema_version") != "1.0":
            errs.append("schema_version 必须为 '1.0'")
        if report.get("kind") not in ("routine", "openclaw", "manual"):
            errs.append("kind 取值非法")
        if not isinstance(report.get("producer"), dict) or "name" not in report.get("producer", {}):
            errs.append("producer.name 缺失")
        try:
            require_report_id(report.get("id"))
        except ValueError as exc:
            errs.append(str(exc))
        return (len(errs) == 0, errs)


# ----------------------------- 写入 feed -----------------------------

def require_report_id(value: object) -> str:
    if not isinstance(value, str) or REPORT_ID_RE.fullmatch(value) is None:
        raise ValueError("report id must match ^[A-Za-z0-9._:-]{6,80}$")
    return value


def artifact_json_path(root: str | os.PathLike[str], artifact_id: object) -> str:
    report_id = require_report_id(artifact_id)
    approved_root = Path(root).resolve()
    destination = (approved_root / f"{report_id}.json").resolve()
    if destination.parent != approved_root:
        raise ValueError("resolved artifact path escaped its approved root")
    return str(destination)


def _feed_child_root(name: str) -> Path:
    feed_root = Path(FEED).resolve()
    child_root = (feed_root / name).resolve()
    if child_root.parent != feed_root:
        raise ValueError(f"resolved feed/{name} root escaped feed")
    return child_root


def inbox_path(
    report_id: object,
    inbox_dir: str | os.PathLike[str] | None = None,
) -> str:
    root = Path(inbox_dir) if inbox_dir is not None else _feed_child_root("inbox")
    return artifact_json_path(root, report_id)


def save_json_exclusive(
    path: str | os.PathLike[str],
    obj: object,
    *,
    encoded: bytes | None = None,
    record_publication: bool = True,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json_file_bytes(obj)
    if encoded is not None and encoded != serialized:
        raise ValueError("encoded JSON does not match the strict serialization of obj")
    payload = serialized if encoded is None else encoded
    with destination.open("xb") as handle:
        handle.write(payload)
    if record_publication:
        record_publication_path(destination)


def report_path(report_id: str) -> str:
    return artifact_json_path(_feed_child_root("reports"), report_id)


def research_path(brief_id: str) -> str:
    """深度研究简报路径(feed/research/<id>.json),与 report_path 同一 id 与路径包含约束。"""
    return artifact_json_path(_feed_child_root("research"), brief_id)


def write_report_files(report: dict) -> str:
    """落盘 report 文件,并刷新 signals/latest、market/state、factory/candidates。"""
    path = report_path(report["id"])
    save_json(path, report)
    if report.get("book"):
        save_json(os.path.join(FEED, "signals", "latest.json"),
                  {"updated_at": report["produced_at"], "source_report": report["id"],
                   **report["book"]})
    if report.get("market_state"):
        save_json(os.path.join(FEED, "market", "state.json"),
                  {"updated_at": report["produced_at"], "asof_data": report.get("asof_data"),
                   "source_report": report["id"], **report["market_state"]})
    cands = report.get("factory_candidates") or []
    if cands:
        store = load_json(os.path.join(FEED, "factory", "candidates.json"),
                          {"updated_at": None, "candidates": []})
        for c in cands:
            c = {**c, "_source": report["id"], "_at": report["produced_at"]}
            store["candidates"].insert(0, c)
        store["candidates"] = store["candidates"][:120]
        store["updated_at"] = report["produced_at"]
        save_json(os.path.join(FEED, "factory", "candidates.json"), store)
    return path


def _report_summary(report: dict) -> dict:
    eng = report.get("engine", {}) or {}
    net = eng.get("net", {}) or {}
    contrib = report.get("contribution", {}) or {}
    return {
        "id": report["id"],
        "kind": report["kind"],
        "produced_at": report["produced_at"],
        "asof_data": report.get("asof_data"),
        "producer": (report.get("producer", {}) or {}).get("name"),
        "agent_role": (report.get("producer", {}) or {}).get("agent_role"),
        "net_sharpe": net.get("sharpe"),
        "verdict": eng.get("verdict"),
        "n_alerts": len(report.get("alerts", []) or []),
        "n_candidates": len(report.get("factory_candidates", []) or []),
        "contribution_type": contrib.get("type"),
        "contribution_summary": contrib.get("summary"),
        "path": f"reports/{os.path.basename(report_path(report['id']))}",
    }


def _days_since(date_str: str | None) -> float | None:
    if not date_str:
        return None
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).total_seconds() / 86400.0
    except ValueError:
        return None


def _artifact_freshness() -> dict:
    """逐数据面板的实际新鲜度(直接读文件,不信报告自报)——看板①区与审计共用。"""
    out = {}
    def _put(key, path, *fields):
        d = load_json(os.path.join(FEED, path))
        if d is None:
            out[key] = {"exists": False}
            return
        if isinstance(d, list):
            d = d[-1] if d else {}
        val = next((d.get(f) for f in fields if isinstance(d, dict) and d.get(f)), None)
        out[key] = {"exists": True, "asof": val,
                    "age_days": round(_days_since(str(val)), 2) if val else None}
    _put("signals_book", "signals/latest.json", "asof")
    _put("market_state", "market/state.json", "asof_data", "updated_at")
    _put("screener", "screener/latest.json", "date")
    _put("rs_ranks", "signals/rs-ranks.json", "date")
    _put("stock_notes", "stock-notes/index.json", "updated_at")
    _put("intraday", "intraday/latest.json", "at")
    _put("market_history", "market/history.json", "at", "date")
    _put("funds_13f", "funds/situational-awareness.json", "filed")
    _put("crypto_state", "crypto/state.json", "updated_at")
    _put("research", "research/index.json", "updated_at")
    return out


def rebuild_index() -> dict:
    """扫描 feed/reports/ 重建 index.json(CI 合并投递后调用,保证看板一致)。"""
    rdir = os.path.join(FEED, "reports")
    reports = []
    for fn in os.listdir(rdir) if os.path.isdir(rdir) else []:
        if fn.endswith(".json"):
            r = load_json(os.path.join(rdir, fn))
            if r and "id" in r:
                reports.append(r)
    reports.sort(key=lambda r: r.get("produced_at", ""), reverse=True)

    summaries = [_report_summary(r) for r in reports[:MAX_INDEX_REPORTS]]
    by_kind: dict[str, int] = {}
    by_producer: dict[str, int] = {}
    last_24h = last_7d = 0
    for r in reports:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        pn = (r.get("producer", {}) or {}).get("name", "unknown")
        by_producer[pn] = by_producer.get(pn, 0) + 1
        age = _days_since(r.get("produced_at"))
        if age is not None and age <= 1:
            last_24h += 1
        if age is not None and age <= 7:
            last_7d += 1

    # 日级时间线(看板「何时获得多少信息」)
    timeline: dict[str, int] = {}
    for r in reports:
        day = (r.get("produced_at") or "")[:10]
        if day:
            timeline[day] = timeline.get(day, 0) + 1

    # 贡献日志
    contributions = []
    for r in reports:
        c = r.get("contribution")
        if c:
            contributions.append({"at": r["produced_at"], "producer": (r.get("producer", {}) or {}).get("name"),
                                  "id": r["id"], **c})
    contributions = contributions[:MAX_CONTRIB]

    latest = reports[0] if reports else None
    latest_engine = next((r for r in reports if r.get("engine")), latest)
    age_hours = (_days_since(latest["produced_at"]) * 24) if latest else None
    # 实效性:market_data_asof 只取最近「带引擎数据」的报告 ——
    # factory/study/openclaw 的 asof 语义不同,混用会虚报数据新鲜度(审计 2026-06-10)。
    data_age_days = _days_since((latest_engine or {}).get("asof_data")) if latest_engine else None
    index = {
        "schema_version": "1.0",
        "updated_at": now_iso(),
        "freshness": {
            "last_report_at": latest["produced_at"] if latest else None,
            "market_data_asof": (latest_engine or {}).get("asof_data") if latest_engine else None,
            "report_age_hours": round(age_hours, 2) if age_hours is not None else None,
            "data_age_days": round(data_age_days, 2) if data_age_days is not None else None,
            "stale": (age_hours is not None and age_hours > STALE_HOURS),
            "sources": _artifact_freshness(),
        },
        "latest": {
            "report": f"reports/{os.path.basename(report_path(latest_engine['id']))}" if latest_engine else None,
            "signals": "signals/latest.json",
            "market": "market/state.json",
            "factory": "factory/candidates.json",
            "net_sharpe": ((latest_engine.get("engine", {}) or {}).get("net", {}) or {}).get("sharpe") if latest_engine else None,
            "verdict": (latest_engine.get("engine", {}) or {}).get("verdict") if latest_engine else None,
        },
        "stats": {
            "total_reports": len(reports),
            "by_kind": by_kind,
            "by_producer": by_producer,
            "last_24h": last_24h,
            "last_7d": last_7d,
        },
        "timeline": dict(sorted(timeline.items())),
        "reports": summaries,
        "contributions": contributions,
    }
    save_json(os.path.join(FEED, "index.json"), index)
    return index


def publish_report(report: dict, secret: str | None = None) -> dict:
    """校验 -> (可选签名) -> 落盘 -> 重建 index。返回 {ok, errors, path, index}。"""
    if secret:
        sign_report(report, secret)
    ok, errs = validate_report(report)
    if not ok:
        return {"ok": False, "errors": errs, "path": None}
    path = write_report_files(report)
    idx = rebuild_index()
    return {"ok": True, "errors": [], "path": path, "index_stats": idx["stats"]}


def has_report(report_id: str) -> bool:
    """幂等:同 id 报告是否已存在(防 OpenClaw 重复投递)。"""
    return os.path.exists(report_path(report_id))
