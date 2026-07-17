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
AUTOMERGE_ELIGIBLE_LABEL = "dependencies:auto-merge-eligible"
AUTOMERGE_ATTESTATION_CONTEXT = "dependabot/auto-merge-eligible"
TRUSTED_ATTESTATION_CREATOR = "github-actions[bot]"


class MetadataDecision(Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class MergeDecision(Enum):
    ENABLED = "enabled"
    NOT_READY = "not_ready"


def classify_metadata(
    package_ecosystem: object,
    update_type: object,
) -> MetadataDecision:
    supported = {
        ("npm", "version-update:semver-patch"): MetadataDecision.ELIGIBLE,
        ("npm", "version-update:semver-minor"): MetadataDecision.ELIGIBLE,
        ("npm", "version-update:semver-major"): MetadataDecision.INELIGIBLE,
        ("pip", "version-update:semver-patch"): MetadataDecision.ELIGIBLE,
        ("pip", "version-update:semver-minor"): MetadataDecision.ELIGIBLE,
        ("pip", "version-update:semver-major"): MetadataDecision.INELIGIBLE,
        ("github-actions", "version-update:semver-patch"): MetadataDecision.ELIGIBLE,
        ("github-actions", "version-update:semver-minor"): MetadataDecision.ELIGIBLE,
        ("github-actions", "version-update:semver-major"): MetadataDecision.ELIGIBLE,
    }
    try:
        return supported[(package_ecosystem, update_type)]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "unsupported Dependabot metadata: "
            f"ecosystem={package_ecosystem!r}, update_type={update_type!r}"
        ) from exc


def current_pr_ready(view: object) -> bool:
    return (
        isinstance(view, Mapping)
        and isinstance(view.get("headRefOid"), str)
        and bool(view["headRefOid"].strip())
        and view.get("mergeable") == "MERGEABLE"
        and view.get("mergeStateStatus") == "CLEAN"
    )


def eligibility_label_present(view: object) -> bool:
    if not isinstance(view, Mapping):
        return False
    labels = view.get("labels")
    if not isinstance(labels, Sequence) or isinstance(labels, (str, bytes)):
        return False
    names: set[str] = set()
    for label in labels:
        if not isinstance(label, Mapping):
            return False
        name = label.get("name")
        if not isinstance(name, str):
            return False
        names.add(name)
    return AUTOMERGE_ELIGIBLE_LABEL in names


def eligibility_attested(statuses: object) -> bool:
    if not isinstance(statuses, Sequence) or isinstance(statuses, (str, bytes)):
        return False
    # GitHub's commit-status endpoint returns newest first, so the first exact
    # context is the current head's authoritative eligibility attestation.
    for status in statuses:
        if not isinstance(status, Mapping):
            return False
        context = status.get("context")
        if not isinstance(context, str):
            return False
        if context != AUTOMERGE_ATTESTATION_CONTEXT:
            continue
        creator = status.get("creator")
        return (
            status.get("state") == "success"
            and isinstance(creator, Mapping)
            and creator.get("login") == TRUSTED_ATTESTATION_CREATOR
        )
    return False


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


def revoke_auto_merge(
    *,
    repo: str,
    pr_number: int,
    run: Runner = subprocess.run,
) -> bool:
    view_command = [
        "gh",
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "autoMergeRequest",
    ]
    view_result = run(view_command, capture_output=True, text=True)
    if view_result.returncode != 0:
        raise RuntimeError(
            f"auto-merge query failed for #{pr_number}: {view_result.stderr.strip()}"
        )
    try:
        view = json.loads(
            view_result.stdout,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"auto-merge query returned invalid JSON for #{pr_number}"
        ) from exc
    if not isinstance(view, Mapping) or "autoMergeRequest" not in view:
        raise RuntimeError(f"auto-merge query returned malformed data for #{pr_number}")
    auto_merge_request = view["autoMergeRequest"]
    if auto_merge_request is None:
        return False
    if not isinstance(auto_merge_request, Mapping):
        raise RuntimeError(f"auto-merge query returned malformed data for #{pr_number}")

    disable_command = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--repo",
        repo,
        "--disable-auto",
    ]
    disable_result = run(disable_command, capture_output=True, text=True)
    if disable_result.returncode != 0:
        raise RuntimeError(
            f"auto-merge disable failed for #{pr_number}: "
            f"{disable_result.stderr.strip()}"
        )
    print(f"#{pr_number}: active auto-merge request disabled")
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
        "headRefOid,mergeable,mergeStateStatus,labels",
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
    if not eligibility_label_present(view):
        print(f"#{pr_number} skipped: current eligibility label is absent or malformed")
        return MergeDecision.NOT_READY

    attestation_command = [
        "gh",
        "api",
        "--method",
        "GET",
        f"repos/{repo}/commits/{head_sha}/statuses?per_page=100",
    ]
    attestation_result = run(
        attestation_command,
        capture_output=True,
        text=True,
    )
    if attestation_result.returncode != 0:
        raise RuntimeError(
            f"eligibility attestation query failed for PR #{pr_number}: "
            f"{attestation_result.stderr.strip()}"
        )
    try:
        statuses = json.loads(
            attestation_result.stdout,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"eligibility attestation query returned invalid JSON for PR #{pr_number}"
        ) from exc
    if not eligibility_attested(statuses):
        print(
            f"#{pr_number} skipped: current head lacks a trusted successful "
            "eligibility attestation"
        )
        return MergeDecision.NOT_READY

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
    parser.add_argument("--repo")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--classify-ecosystem")
    parser.add_argument("--classify-update-type")
    args = parser.parse_args(argv)

    classification_requested = (
        args.classify_ecosystem is not None
        or args.classify_update_type is not None
    )
    if classification_requested:
        if args.repo is not None or args.pr is not None:
            parser.error("classification cannot be combined with --repo or --pr")
        try:
            decision = classify_metadata(
                args.classify_ecosystem,
                args.classify_update_type,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(decision.value)
        return 0

    if args.repo is None or args.pr is None:
        parser.error("--repo and --pr are required for merge gating")
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
