"""Tests for the transitional Stage 1A feed publication allowlist."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from feed_publication import (  # noqa: E402
    load_manifest_paths,
    record_tracked_deletion,
    record_written_path,
    stage_recorded_paths,
)


class FakeRunner:
    def __init__(self, tracked_paths: set[str] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.tracked_paths = tracked_paths or set()

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[:2] == ["git", "ls-files"]:
            path = command[-1]
            if path in self.tracked_paths:
                return subprocess.CompletedProcess(command, 0, stdout=path + "\n", stderr="")
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not tracked")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


class FeedPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = pathlib.Path(self.temp.name) / "repo"
        self.feed = self.repo / "feed"
        self.feed.mkdir(parents=True)
        self.manifest = pathlib.Path(self.temp.name) / "publication.json"

    def test_manifest_records_exact_repo_relative_feed_path(self) -> None:
        target = self.feed / "index.json"
        target.write_text("{}\n", encoding="utf-8")

        record_written_path(
            target,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        self.assertEqual(
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            ),
            ("feed/index.json",),
        )

    def test_record_rejects_path_outside_feed(self) -> None:
        outside = self.repo / "README.md"
        outside.write_text("sentinel\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "outside feed root"):
            record_written_path(
                outside,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )

    def test_tampered_manifest_cannot_stage_parent_path(self) -> None:
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": ["../AGENTS.md"]}),
            encoding="utf-8",
        )
        runner = FakeRunner()

        with self.assertRaises(ValueError):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=runner,
            )

        self.assertEqual(runner.commands, [])

    def test_manifest_rejects_existing_feed_directory(self) -> None:
        reports = self.feed / "reports"
        reports.mkdir()
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": ["feed/reports"]}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "regular file"):
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )

    def test_stage_uses_only_sorted_manifest_paths(self) -> None:
        report = self.feed / "reports" / "openclaw-safe-id.json"
        report.parent.mkdir(parents=True)
        report.write_text("{}\n", encoding="utf-8")
        index = self.feed / "index.json"
        index.write_text("{}\n", encoding="utf-8")
        for target in (report, index):
            record_written_path(
                target,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )
        runner = FakeRunner()

        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertEqual(staged, ("feed/index.json", "feed/reports/openclaw-safe-id.json"))
        self.assertEqual(
            runner.commands[-1],
            [
                "git",
                "add",
                "-A",
                "--",
                "feed/index.json",
                "feed/reports/openclaw-safe-id.json",
            ],
        )

    def test_exact_tracked_deletion_can_be_staged(self) -> None:
        deleted = "feed/reports/openclaw-deleted-id.json"
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": [deleted]}),
            encoding="utf-8",
        )
        runner = FakeRunner({deleted})

        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertEqual(staged, (deleted,))
        self.assertEqual(runner.commands[-1], ["git", "add", "-A", "--", deleted])

    def test_tracked_deletion_is_recorded_only_after_exact_git_proof(self) -> None:
        deleted = "feed/inbox/openclaw-tracked-id.json"
        runner = FakeRunner({deleted})

        recorded = record_tracked_deletion(
            self.repo / deleted,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertTrue(recorded)
        self.assertEqual(
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            ),
            (deleted,),
        )
        self.assertEqual(
            runner.commands,
            [["git", "ls-files", "--error-unmatch", "--full-name", "--", deleted]],
        )

    def test_untracked_deletion_is_not_recorded(self) -> None:
        deleted = "feed/inbox/openclaw-dispatch-temporary-id.json"
        runner = FakeRunner()

        recorded = record_tracked_deletion(
            self.repo / deleted,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertFalse(recorded)
        self.assertFalse(self.manifest.exists())

    def test_manifest_rejects_nonstandard_json_constants(self) -> None:
        self.manifest.write_text(
            '{"schema_version":"1.0","paths":["feed/index.json"],"extra":NaN}',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "manifest is unreadable"):
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )

    def test_missing_untracked_manifest_path_fails_closed(self) -> None:
        missing = "feed/reports/openclaw-never-written-id.json"
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": [missing]}),
            encoding="utf-8",
        )
        runner = FakeRunner()

        with self.assertRaisesRegex(ValueError, "not an existing or tracked file"):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=runner,
            )

        self.assertFalse(any(command[:2] == ["git", "add"] for command in runner.commands))

    def test_empty_manifest_fails_closed(self) -> None:
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": []}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "no paths"):
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
