"""Fail-closed tests for Dependabot required-check gating."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from dependabot_merge_gate import (  # noqa: E402
    AUTOMERGE_ATTESTATION_CONTEXT,
    AUTOMERGE_ELIGIBLE_LABEL,
    MetadataDecision,
    MergeDecision,
    classify_metadata,
    current_pr_ready,
    eligibility_attested,
    gate_pull_request,
    required_checks_successful,
    revoke_auto_merge,
)


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "dependabot_merge_gate.py"
PATCH = "version-update:semver-patch"
MINOR = "version-update:semver-minor"
MAJOR = "version-update:semver-major"
NPM = "npm_and_yarn"
GITHUB_ACTIONS = "github_actions"


class FakeRunner:
    def __init__(
        self,
        checks: object,
        *,
        view: object | None = None,
        view_returncode: int = 0,
        view_stdout: str | None = None,
        view_stderr: str = "",
        statuses: object | None = None,
        statuses_returncode: int = 0,
        statuses_stdout: str | None = None,
        statuses_stderr: str = "",
        checks_returncode: int = 0,
        checks_stdout: str | None = None,
        checks_stderr: str = "",
        merge_returncode: int = 0,
        merge_stderr: str = "",
        auto_merge_request: object | None = None,
        auto_view_returncode: int = 0,
        auto_view_stdout: str | None = None,
        auto_view_stderr: str = "",
        disable_returncode: int = 0,
        disable_stderr: str = "",
    ) -> None:
        self.view = view if view is not None else {
            "headRefOid": "current-abc123",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "labels": [{"name": "dependencies:auto-merge-eligible"}],
        }
        self.view_returncode = view_returncode
        self.view_stdout = view_stdout
        self.view_stderr = view_stderr
        self.statuses = statuses if statuses is not None else [
            {
                "context": "dependabot/auto-merge-eligible",
                "state": "success",
                "creator": {"login": "github-actions[bot]"},
            }
        ]
        self.statuses_returncode = statuses_returncode
        self.statuses_stdout = statuses_stdout
        self.statuses_stderr = statuses_stderr
        self.checks = checks
        self.checks_returncode = checks_returncode
        self.checks_stdout = checks_stdout
        self.checks_stderr = checks_stderr
        self.merge_returncode = merge_returncode
        self.merge_stderr = merge_stderr
        self.auto_merge_request = auto_merge_request
        self.auto_view_returncode = auto_view_returncode
        self.auto_view_stdout = auto_view_stdout
        self.auto_view_stderr = auto_view_stderr
        self.disable_returncode = disable_returncode
        self.disable_stderr = disable_stderr
        self.commands: list[list[str]] = []

    def __call__(
        self,
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[:3] == ["gh", "pr", "view"]:
            if command[command.index("--json") + 1] == "autoMergeRequest":
                return subprocess.CompletedProcess(
                    command,
                    self.auto_view_returncode,
                    stdout=(
                        self.auto_view_stdout
                        if self.auto_view_stdout is not None
                        else json.dumps(
                            {"autoMergeRequest": self.auto_merge_request}
                        )
                    ),
                    stderr=self.auto_view_stderr,
                )
            return subprocess.CompletedProcess(
                command,
                self.view_returncode,
                stdout=(
                    self.view_stdout
                    if self.view_stdout is not None
                    else json.dumps(self.view)
                ),
                stderr=self.view_stderr,
            )
        if command[:2] == ["gh", "api"]:
            return subprocess.CompletedProcess(
                command,
                self.statuses_returncode,
                stdout=(
                    self.statuses_stdout
                    if self.statuses_stdout is not None
                    else json.dumps(self.statuses)
                ),
                stderr=self.statuses_stderr,
            )
        if command[:3] == ["gh", "pr", "checks"]:
            return subprocess.CompletedProcess(
                command,
                self.checks_returncode,
                stdout=(
                    self.checks_stdout
                    if self.checks_stdout is not None
                    else json.dumps(self.checks)
                ),
                stderr=self.checks_stderr,
            )
        if command[:3] == ["gh", "pr", "merge"]:
            if "--disable-auto" in command:
                return subprocess.CompletedProcess(
                    command,
                    self.disable_returncode,
                    stdout="",
                    stderr=self.disable_stderr,
                )
            return subprocess.CompletedProcess(
                command,
                self.merge_returncode,
                stdout="",
                stderr=self.merge_stderr,
            )
        raise AssertionError(f"unexpected command: {command}")

    @property
    def merge_commands(self) -> list[list[str]]:
        return [
            command
            for command in self.commands
            if command[:3] == ["gh", "pr", "merge"]
        ]

    @property
    def check_commands(self) -> list[list[str]]:
        return [
            command
            for command in self.commands
            if command[:3] == ["gh", "pr", "checks"]
        ]

    @property
    def status_commands(self) -> list[list[str]]:
        return [command for command in self.commands if command[:2] == ["gh", "api"]]

    @property
    def disable_commands(self) -> list[list[str]]:
        return [
            command
            for command in self.commands
            if command[:3] == ["gh", "pr", "merge"]
            and "--disable-auto" in command
        ]


class DependabotMergeGateTests(unittest.TestCase):
    def test_metadata_classification_enumerates_repo_supported_pairs(self) -> None:
        expected = {
            (NPM, PATCH): MetadataDecision.ELIGIBLE,
            (NPM, MINOR): MetadataDecision.ELIGIBLE,
            (NPM, MAJOR): MetadataDecision.INELIGIBLE,
            ("pip", PATCH): MetadataDecision.ELIGIBLE,
            ("pip", MINOR): MetadataDecision.ELIGIBLE,
            ("pip", MAJOR): MetadataDecision.INELIGIBLE,
            (GITHUB_ACTIONS, PATCH): MetadataDecision.ELIGIBLE,
            (GITHUB_ACTIONS, MINOR): MetadataDecision.ELIGIBLE,
            (GITHUB_ACTIONS, MAJOR): MetadataDecision.ELIGIBLE,
        }

        for pair, decision in expected.items():
            with self.subTest(pair=pair):
                self.assertEqual(classify_metadata(*pair), decision)

    def test_metadata_classification_rejects_unknown_or_missing_values(self) -> None:
        rejected = [
            ("", PATCH),
            (None, PATCH),
            ("docker", PATCH),
            ("npm", PATCH),
            ("github-actions", PATCH),
            (NPM, ""),
            (NPM, None),
            (NPM, "security-update:semver-patch"),
            (NPM, "version-update:semver-unknown"),
        ]

        for pair in rejected:
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                classify_metadata(*pair)

    def test_metadata_classification_cli_exits_nonzero_for_unknown_pair(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--classify-ecosystem",
                "github-actions",
                "--classify-update-type",
                PATCH,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported Dependabot metadata", result.stderr)

    def test_attestation_requires_latest_exact_success_from_trusted_creator(
        self,
    ) -> None:
        trusted_success = {
            "context": AUTOMERGE_ATTESTATION_CONTEXT,
            "state": "success",
            "creator": {"login": "github-actions[bot]"},
        }
        unrelated = {
            "context": "tests",
            "state": "pending",
            "creator": {"login": "github-actions[bot]"},
        }
        self.assertTrue(eligibility_attested([unrelated, trusted_success]))

        rejected = [
            [],
            {},
            [unrelated],
            [
                {
                    **trusted_success,
                    "state": "pending",
                },
                trusted_success,
            ],
            [{**trusted_success, "state": "failure"}],
            [{**trusted_success, "creator": {"login": "dependabot[bot]"}}],
            [{**trusted_success, "creator": None}],
            [None, trusted_success],
        ]
        for statuses in rejected:
            with self.subTest(statuses=statuses):
                self.assertFalse(eligibility_attested(statuses))

    def test_active_auto_merge_is_revoked_with_native_disable_flag(self) -> None:
        runner = FakeRunner(
            [],
            auto_merge_request={"enabledAt": "2026-07-17T00:00:00Z"},
        )

        revoked = revoke_auto_merge(repo="owner/repo", pr_number=42, run=runner)

        self.assertTrue(revoked)
        self.assertEqual(
            runner.disable_commands,
            [
                [
                    "gh",
                    "pr",
                    "merge",
                    "42",
                    "--repo",
                    "owner/repo",
                    "--disable-auto",
                ]
            ],
        )

    def test_inactive_auto_merge_needs_no_disable_call(self) -> None:
        runner = FakeRunner([], auto_merge_request=None)

        revoked = revoke_auto_merge(repo="owner/repo", pr_number=42, run=runner)

        self.assertFalse(revoked)
        self.assertEqual(runner.disable_commands, [])

    def test_auto_merge_revocation_fails_closed_on_query_or_disable_errors(
        self,
    ) -> None:
        cases = [
            (
                FakeRunner([], auto_view_returncode=1, auto_view_stderr="denied"),
                "query failed",
            ),
            (
                FakeRunner([], auto_view_stdout="{not-json"),
                "invalid JSON",
            ),
            (
                FakeRunner([], auto_view_stdout='{"autoMergeRequest": false}'),
                "malformed",
            ),
            (
                FakeRunner(
                    [],
                    auto_merge_request={"enabledAt": "2026-07-17T00:00:00Z"},
                    disable_returncode=1,
                    disable_stderr="cannot disable",
                ),
                "disable failed",
            ),
        ]
        for runner, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                RuntimeError,
                message,
            ):
                revoke_auto_merge(repo="owner/repo", pr_number=42, run=runner)

    def test_gate_requires_fresh_exact_eligibility_label(self) -> None:
        labels_to_reject: list[object] = [
            [],
            None,
            [{"name": "dependencies:auto-merge-eligible-stale"}],
            [AUTOMERGE_ELIGIBLE_LABEL],
        ]
        for labels in labels_to_reject:
            runner = FakeRunner(
                [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}],
                view={
                    "headRefOid": "current-abc123",
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "labels": labels,
                },
            )

            with self.subTest(labels=labels):
                decision = gate_pull_request(
                    repo="owner/repo",
                    pr_number=42,
                    run=runner,
                )

                self.assertEqual(decision, MergeDecision.NOT_READY)
                self.assertEqual(runner.status_commands, [])
                self.assertEqual(runner.check_commands, [])
                self.assertEqual(runner.merge_commands, [])

    def test_stale_label_without_current_head_attestation_cannot_merge(self) -> None:
        runner = FakeRunner(
            [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}],
            view={
                "headRefOid": "new-head-def456",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "labels": [{"name": AUTOMERGE_ELIGIBLE_LABEL}],
            },
            statuses=[],
        )

        decision = gate_pull_request(repo="owner/repo", pr_number=42, run=runner)

        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(len(runner.status_commands), 1)
        self.assertIn(
            "repos/owner/repo/commits/new-head-def456/statuses?per_page=100",
            runner.status_commands[0],
        )
        self.assertEqual(runner.check_commands, [])
        self.assertEqual(runner.merge_commands, [])

    def test_latest_pending_attestation_overrides_older_success(self) -> None:
        creator = {"login": "github-actions[bot]"}
        runner = FakeRunner(
            [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}],
            statuses=[
                {
                    "context": AUTOMERGE_ATTESTATION_CONTEXT,
                    "state": "pending",
                    "creator": creator,
                },
                {
                    "context": AUTOMERGE_ATTESTATION_CONTEXT,
                    "state": "success",
                    "creator": creator,
                },
            ],
        )

        decision = gate_pull_request(repo="owner/repo", pr_number=42, run=runner)

        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(runner.check_commands, [])
        self.assertEqual(runner.merge_commands, [])

    def test_nonzero_or_invalid_current_view_fails_closed(self) -> None:
        cases = [
            (
                FakeRunner([], view_returncode=1, view_stderr="denied"),
                "query failed",
            ),
            (
                FakeRunner([], view_stdout='{"headRefOid": NaN}'),
                "invalid JSON",
            ),
        ]
        for runner, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                RuntimeError,
                message,
            ):
                gate_pull_request(repo="owner/repo", pr_number=42, run=runner)
            self.assertEqual(runner.merge_commands, [])

    def test_nonzero_or_invalid_attestation_query_fails_closed(self) -> None:
        cases = [
            (
                FakeRunner(
                    [],
                    statuses_returncode=1,
                    statuses_stderr="statuses unavailable",
                ),
                "attestation query failed",
            ),
            (
                FakeRunner([], statuses_stdout="[NaN]"),
                "invalid JSON",
            ),
        ]
        for runner, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                RuntimeError,
                message,
            ):
                gate_pull_request(repo="owner/repo", pr_number=42, run=runner)
            self.assertEqual(runner.check_commands, [])
            self.assertEqual(runner.merge_commands, [])

    def test_nonzero_or_invalid_required_check_query_fails_closed(self) -> None:
        cases = [
            (
                FakeRunner([], checks_returncode=1, checks_stderr="API denied"),
                "query failed",
            ),
            (
                FakeRunner([], checks_stdout="[NaN]"),
                "query failed",
            ),
        ]
        for runner, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                RuntimeError,
                message,
            ):
                gate_pull_request(repo="owner/repo", pr_number=42, run=runner)
            self.assertEqual(runner.merge_commands, [])

    def test_nonzero_merge_enablement_fails_closed(self) -> None:
        runner = FakeRunner(
            [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}],
            merge_returncode=1,
            merge_stderr="merge denied",
        )

        with self.assertRaisesRegex(RuntimeError, "enablement failed"):
            gate_pull_request(repo="owner/repo", pr_number=42, run=runner)
        self.assertEqual(len(runner.merge_commands), 1)

    def test_missing_required_checks_fail_closed(self) -> None:
        self.assertFalse(required_checks_successful([]))

    def test_only_success_pass_bucket_is_accepted(self) -> None:
        rejected = [
            {"state": "SUCCESS", "bucket": "pass"},
            {"name": "", "state": "SUCCESS", "bucket": "pass"},
            {"name": "tests", "state": "PENDING", "bucket": "pending"},
            {"name": "tests", "state": "FAILURE", "bucket": "fail"},
            {"name": "tests", "state": "NEUTRAL", "bucket": "pass"},
            {"name": "tests", "state": "SKIPPED", "bucket": "skipping"},
            {"name": "tests", "state": "CANCELLED", "bucket": "cancel"},
            {"name": "tests", "state": None, "bucket": "pass"},
        ]
        for check in rejected:
            with self.subTest(check=check):
                self.assertFalse(required_checks_successful([check]))

    def test_all_required_checks_must_succeed(self) -> None:
        self.assertTrue(
            required_checks_successful(
                [
                    {"name": "tests", "state": "SUCCESS", "bucket": "pass"},
                    {"name": "build", "state": "SUCCESS", "bucket": "pass"},
                ]
            )
        )
        self.assertFalse(
            required_checks_successful(
                [
                    {"name": "tests", "state": "SUCCESS", "bucket": "pass"},
                    {"name": "build", "state": "PENDING", "bucket": "pending"},
                ]
            )
        )

    def test_current_pr_requires_mergeable_clean_state_and_head(self) -> None:
        self.assertTrue(
            current_pr_ready(
                {
                    "headRefOid": "current-abc123",
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                }
            )
        )
        rejected = [
            {},
            {
                "headRefOid": "",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
            },
            {
                "headRefOid": "abc",
                "mergeable": "UNKNOWN",
                "mergeStateStatus": "CLEAN",
            },
            {
                "headRefOid": "abc",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "BLOCKED",
            },
            {
                "headRefOid": "abc",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": None,
            },
        ]
        for view in rejected:
            with self.subTest(view=view):
                self.assertFalse(current_pr_ready(view))

    def test_successful_checks_still_fail_closed_when_merge_state_is_blocked(
        self,
    ) -> None:
        runner = FakeRunner(
            [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}],
            view={
                "headRefOid": "current-abc123",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "BLOCKED",
            },
        )

        decision = gate_pull_request(repo="owner/repo", pr_number=42, run=runner)

        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(runner.check_commands, [])
        self.assertEqual(runner.merge_commands, [])

    def test_empty_checks_do_not_run_merge(self) -> None:
        runner = FakeRunner([])
        decision = gate_pull_request(
            repo="owner/repo",
            pr_number=42,
            run=runner,
        )
        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(runner.merge_commands, [])

    def test_pending_gh_exit_code_does_not_run_merge(self) -> None:
        runner = FakeRunner(
            [{"name": "tests", "state": "PENDING", "bucket": "pending"}],
            checks_returncode=8,
        )
        decision = gate_pull_request(
            repo="owner/repo",
            pr_number=42,
            run=runner,
        )
        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(runner.merge_commands, [])

    def test_no_required_checks_cli_response_is_not_ready(self) -> None:
        runner = FakeRunner(
            [],
            checks_returncode=1,
            checks_stdout="",
            checks_stderr="no required checks reported on the branch",
        )
        decision = gate_pull_request(
            repo="owner/repo",
            pr_number=42,
            run=runner,
        )
        self.assertEqual(decision, MergeDecision.NOT_READY)
        self.assertEqual(runner.merge_commands, [])

    def test_success_uses_auto_merge_and_head_match(self) -> None:
        runner = FakeRunner(
            [{"name": "tests", "state": "SUCCESS", "bucket": "pass"}]
        )
        decision = gate_pull_request(
            repo="owner/repo",
            pr_number=42,
            run=runner,
        )
        self.assertEqual(decision, MergeDecision.ENABLED)
        self.assertEqual(len(runner.merge_commands), 1)
        command = runner.merge_commands[0]
        self.assertIn("--auto", command)
        self.assertIn("--merge", command)
        self.assertNotIn("--admin", command)
        self.assertEqual(
            command[command.index("--match-head-commit") + 1],
            "current-abc123",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
