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


def check_one(path: str, require_sig: bool, secret: str | None) -> tuple[bool, list[str], dict | None]:
    errs: list[str] = []
    if os.path.getsize(path) > MAX_BYTES:
        return False, [f"文件过大 >{MAX_BYTES} 字节"], None
    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:  # noqa: BLE001
        return False, [f"JSON 解析失败: {e}"], None

    ok, schema_errs = fl.validate_report(report)
    errs += schema_errs

    # 内容边界
    if report.get("kind") == "routine":
        errs.append("外部投递不得使用 kind=routine(冒充本仓任务);应为 openclaw。")
    pos = (report.get("book", {}) or {}).get("positions", []) or []
    if len(pos) > MAX_POSITIONS:
        errs.append(f"positions 过多 ({len(pos)}>{MAX_POSITIONS})")
    if len(report.get("factory_candidates", []) or []) > MAX_CANDIDATES:
        errs.append(f"factory_candidates 过多 (>{MAX_CANDIDATES})")

    # 签名
    if secret and report.get("kind") == "openclaw":
        if not fl.verify_signature(report, secret):
            errs.append("HMAC 签名缺失或无效(openclaw 投递必须签名)。")
    elif require_sig and not fl.verify_signature(report, secret or ""):
        errs.append("--require-signature 指定但签名无效。")

    # 幂等
    if report.get("id") and fl.has_report(report["id"]):
        errs.append(f"幂等冲突:报告 id={report['id']} 已存在于 feed/reports/(重复投递)。")

    return (len(errs) == 0), errs, (report if len(errs) == 0 else None)


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
