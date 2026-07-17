#!/usr/bin/env python3
"""Enable Dependabot auto-merge only for a current clean PR with green required checks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from enum import Enum

from feed_lib import reject_json_constant


Runner = Callable[..., subprocess.CompletedProcess[str]]


class MergeDecision(Enum):
    ENABLED = "enabled"
    NOT_READY = "not_ready"


def current_pr_ready(view: object) -> bool:
    return (
        isinstance(view, Mapping)
        and isinstance(view.get("headRefOid"), str)
        and bool(view["headRefOid"].strip())
        and view.get("mergeable") == "MERGEABLE"
        and view.get("mergeStateStatus") == "CLEAN"
    )


def required_checks_successful(checks: object) -> bool:
    if (
        not isinstance(checks, Sequence)
        or isinstance(checks, (str, bytes))
        or not checks
    ):
        return False
    for check in checks:
        if not isinstance(check, Mapping):
            return False
        if not isinstance(check.get("name"), str) or not check["name"].strip():
            return False
        if check.get("state") != "SUCCESS" or check.get("bucket") != "pass":
            return False
    return True


def gate_pull_request(
    *,
    repo: str,
    pr_number: int,
    run: Runner = subprocess.run,
) -> MergeDecision:
    view_command = [
        "gh",
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "headRefOid,mergeable,mergeStateStatus",
    ]
    view_result = run(view_command, capture_output=True, text=True)
    if view_result.returncode != 0:
        raise RuntimeError(
            f"current PR query failed for #{pr_number}: {view_result.stderr.strip()}"
        )
    try:
        view = json.loads(
            view_result.stdout,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"current PR query returned invalid JSON for #{pr_number}"
        ) from exc
    if not current_pr_ready(view):
        print(f"#{pr_number} skipped: current PR is not exactly MERGEABLE and CLEAN")
        return MergeDecision.NOT_READY
    head_sha = view["headRefOid"]

    checks_command = [
        "gh",
        "pr",
        "checks",
        str(pr_number),
        "--repo",
        repo,
        "--required",
        "--json",
        "name,state,bucket",
    ]
    checks_result = run(
        checks_command,
        capture_output=True,
        text=True,
    )
    no_required_checks = "no required checks reported" in checks_result.stderr.lower()
    if checks_result.returncode == 8 or (
        checks_result.returncode == 1 and no_required_checks
    ):
        print(f"#{pr_number} skipped: required checks are absent, pending, or unavailable")
        return MergeDecision.NOT_READY
    if checks_result.returncode != 0:
        raise RuntimeError(
            f"required-check query failed for PR #{pr_number}: "
            f"{checks_result.stderr.strip()}"
        )
    if not checks_result.stdout.strip():
        print(f"#{pr_number} skipped: required-check query returned no data")
        return MergeDecision.NOT_READY
    try:
        checks = json.loads(
            checks_result.stdout,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"required-check query failed for PR #{pr_number}: "
            f"{checks_result.stderr.strip()}"
        ) from exc

    if not required_checks_successful(checks):
        print(
            f"#{pr_number} skipped: required checks are missing, incomplete, "
            "or unsuccessful"
        )
        return MergeDecision.NOT_READY

    merge_command = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--repo",
        repo,
        "--auto",
        "--merge",
        "--match-head-commit",
        head_sha,
    ]
    merge_result = run(
        merge_command,
        capture_output=True,
        text=True,
    )
    if merge_result.returncode != 0:
        raise RuntimeError(
            f"auto-merge enablement failed for PR #{pr_number}: "
            f"{merge_result.stderr.strip()}"
        )
    print(f"#{pr_number}: auto-merge enabled for head {head_sha}")
    return MergeDecision.ENABLED


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        gate_pull_request(
            repo=args.repo,
            pr_number=args.pr,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
