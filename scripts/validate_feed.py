"""校验并合并 feed 投递 —— OpenClaw / 外部 agent 投递的安全闸门(CI 用)。

把外部投递当作不可信输入对待(投递者 = 任何能向本仓 PR/commit 的人):
  1. JSON 解析 + schema 校验(report.schema.json)。
  2. 签名校验:设了 FEED_HMAC_SECRET 时,openclaw 类报告必须带有效 HMAC 签名,否则拒绝。
  3. 幂等:同 id 已存在则跳过(防重复投递)。
  4. 内容边界:openclaw 投递不得自带 kind=routine 冒充本仓任务;大小/字段数上限防滥用。

用法:
  python scripts/validate_feed.py feed/inbox/*.json                 # 仅校验(CI 默认),失败退出码 1
  python scripts/validate_feed.py --merge feed/inbox/*.json          # 校验通过则并入 feed/reports/ 并重建 index
  python scripts/validate_feed.py --require-signature feed/inbox/*.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_lib as fl  # noqa: E402

MAX_BYTES = 512 * 1024          # 单份投递 ≤512KB
MAX_POSITIONS = 400
MAX_CANDIDATES = 50


def _expand(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        out.extend(sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p])
    return [p for p in out if os.path.isfile(p)]


def check_report(
    report: dict,
    *,
    require_sig: bool,
    secret: str | None,
    size_bytes: int | None = None,
) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if size_bytes is not None and size_bytes > MAX_BYTES:
        return False, [f"文件过大 >{MAX_BYTES} 字节"]

    _, schema_errs = fl.validate_report(report)
    errs.extend(schema_errs)

    if report.get("kind") == "routine":
        errs.append("外部投递不得使用 kind=routine(冒充本仓任务);应为 openclaw 或 manual。")

    book = report.get("book")
    if book is None:
        positions: object = []
    elif not isinstance(book, dict):
        positions = []
        errs.append("book 必须是 JSON object。")
    else:
        positions = book.get("positions", []) or []
    if not isinstance(positions, list):
        errs.append("book.positions 必须是 JSON array。")
    elif len(positions) > MAX_POSITIONS:
        errs.append(f"positions 过多 ({len(positions)}>{MAX_POSITIONS})")

    candidates = report.get("factory_candidates", []) or []
    if not isinstance(candidates, list):
        errs.append("factory_candidates 必须是 JSON array。")
    elif len(candidates) > MAX_CANDIDATES:
        errs.append(f"factory_candidates 过多 (>{MAX_CANDIDATES})")

    must_verify = require_sig or report.get("kind") == "openclaw"
    if must_verify:
        if not secret:
            errs.append("FEED_HMAC_SECRET 未配置，拒绝需要签名的外部投递。")
        elif not fl.verify_signature(report, secret):
            errs.append("HMAC 签名缺失或无效。")

    report_id: str | None
    try:
        report_id = fl.require_report_id(report.get("id"))
    except ValueError:
        report_id = None
    if report_id is not None and fl.has_report(report_id):
        errs.append(f"幂等冲突:报告 id={report_id} 已存在于 feed/reports/(重复投递)。")

    return len(errs) == 0, errs


def check_one(
    path: str,
    require_sig: bool,
    secret: str | None,
) -> tuple[bool, list[str], dict | None]:
    size_bytes = os.path.getsize(path)
    if size_bytes > MAX_BYTES:
        return False, [f"文件过大 >{MAX_BYTES} 字节"], None
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle, parse_constant=fl.reject_json_constant)
    except Exception as exc:  # noqa: BLE001
        return False, [f"JSON 解析失败: {exc}"], None
    if not isinstance(report, dict):
        return False, ["报告顶层必须是 JSON object。"], None

    passed, errs = check_report(
        report,
        require_sig=require_sig,
        secret=secret,
        size_bytes=size_bytes,
    )
    return passed, errs, report if passed else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--merge", action="store_true", help="校验通过则并入 feed/reports/ 并重建 index")
    ap.add_argument("--require-signature", action="store_true")
    args = ap.parse_args()
    secret = os.environ.get("FEED_HMAC_SECRET")

    files = _expand(args.paths)
    if not files:
        print("没有匹配到投递文件(inbox 为空)——通过。")
        return
    all_ok = True
    merged = 0
    for path in files:
        ok, errs, report = check_one(path, args.require_signature, secret)
        tag = "✓" if ok else "✗"
        print(f"{tag} {path}")
        for e in errs:
            print(f"    - {e}")
        if ok and args.merge and report is not None:
            fl.write_report_files(report)
            os.remove(path)
            merged += 1
        all_ok = all_ok and ok
    if args.merge and merged:
        idx = fl.rebuild_index()
        print(f"已并入 {merged} 份投递,feed 现有 {idx['stats']['total_reports']} 份报告。")
    if not all_ok:
        print("\n校验失败:存在无效投递。")
        sys.exit(1)
    print("\n全部投递校验通过。")


if __name__ == "__main__":
    main()
