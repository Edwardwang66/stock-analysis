"""Fail-closed tests for Dependabot required-check gating."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from dependabot_merge_gate import (  # noqa: E402
    MergeDecision,
    current_pr_ready,
    gate_pull_request,
    required_checks_successful,
)


class FakeRunner:
    def __init__(
        self,
        checks: object,
        *,
        view: object | None = None,
        view_returncode: int = 0,
        view_stdout: str | None = None,
        view_stderr: str = "",
        checks_returncode: int = 0,
        checks_stdout: str | None = None,
        checks_stderr: str = "",
    ) -> None:
        self.view = view if view is not None else {
            "headRefOid": "current-abc123",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
        }
        self.view_returncode = view_returncode
        self.view_stdout = view_stdout
        self.view_stderr = view_stderr
        self.checks = checks
        self.checks_returncode = checks_returncode
        self.checks_stdout = checks_stdout
        self.checks_stderr = checks_stderr
        self.commands: list[list[str]] = []

    def __call__(
        self,
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[:3] == ["gh", "pr", "view"]:
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
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
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


class DependabotMergeGateTests(unittest.TestCase):
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
