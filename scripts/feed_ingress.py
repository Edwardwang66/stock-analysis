#!/usr/bin/env python3
"""Validate a repository_dispatch report before creating an inbox file."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import feed_lib as fl
from validate_feed import check_report


class SubmissionRejected(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def receive_dispatch(
    report: dict,
    *,
    secret: str | None,
    inbox_dir: str | os.PathLike[str] | None = None,
) -> str:
    if not isinstance(report, dict):
        raise SubmissionRejected(["报告顶层必须是 JSON object。"])
    encoded = fl.json_file_bytes(report)
    passed, errors = check_report(
        report,
        require_sig=True,
        secret=secret,
        size_bytes=len(encoded),
    )
    if not passed:
        raise SubmissionRejected(errors)

    destination = fl.inbox_path(report.get("id"), inbox_dir=inbox_dir)
    fl.save_json_exclusive(
        destination,
        report,
        encoded=encoded,
        record_publication=False,
    )
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path-output", required=True)
    args = parser.parse_args(argv)

    raw_payload = os.environ.get("PAYLOAD")
    if raw_payload is None:
        print("PAYLOAD 未配置，拒绝 dispatch。", file=sys.stderr)
        return 2
    try:
        report = json.loads(raw_payload, parse_constant=fl.reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"PAYLOAD JSON 解析失败: {exc}", file=sys.stderr)
        return 1

    try:
        destination = receive_dispatch(
            report,
            secret=os.environ.get("FEED_HMAC_SECRET"),
        )
    except (SubmissionRejected, FileExistsError, ValueError) as exc:
        print(f"dispatch 投递拒绝: {exc}", file=sys.stderr)
        return 1

    output = Path(args.path_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(destination + "\n", encoding="utf-8")
    print(f"收到并暂存投递: {Path(destination).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
