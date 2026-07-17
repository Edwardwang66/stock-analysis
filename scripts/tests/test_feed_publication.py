"""Tests for the transitional Stage 1A feed publication allowlist."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

import fcntl

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import feed_lib as fl  # noqa: E402
import feed_ingress  # noqa: E402
import feed_publication as publication  # noqa: E402
import openclaw_daily  # noqa: E402
from feed_publication import (  # noqa: E402
    load_manifest_paths,
    record_tracked_deletion,
    record_written_path,
    stage_recorded_paths,
)
import validate_feed  # noqa: E402


class FakeRunner:
    def __init__(self, tracked_paths: set[str] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.tracked_paths = tracked_paths or set()

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if "ls-files" in command:
            path = command[-1]
            if path in self.tracked_paths:
                terminator = "\0" if "-z" in command else "\n"
                if "--stage" in command:
                    output = f"100644 {'0' * 40} 0\t{path}{terminator}"
                else:
                    output = path + terminator
                return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not tracked")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.kwargs: list[dict[str, object]] = []

    def __call__(
        self, command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        self.commands.append(command)
        self.kwargs.append(dict(kwargs))
        return subprocess.run(command, **kwargs)  # type: ignore[arg-type]


class FeedPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = pathlib.Path(self.temp.name) / "repo"
        self.feed = self.repo / "feed"
        self.feed.mkdir(parents=True)
        self.manifest = pathlib.Path(self.temp.name) / "publication.json"

    def _init_repo(self, repo: pathlib.Path | None = None) -> pathlib.Path:
        target = repo if repo is not None else self.repo
        subprocess.run(
            ["git", "init", "-q"],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )
        return target

    def _commit_all(
        self,
        repo: pathlib.Path | None = None,
        *,
        message: str = "seed",
    ) -> pathlib.Path:
        target = self._init_repo(repo)
        subprocess.run(
            ["git", "add", "-A"],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Codex",
                "-c",
                "user.email=codex@example.invalid",
                "commit",
                "-qm",
                message,
            ],
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        )
        return target

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

    def test_concurrent_manifest_writers_serialize_and_merge_paths(self) -> None:
        targets = (self.feed / "first.json", self.feed / "second.json")
        for target in targets:
            target.write_text("{}\n", encoding="utf-8")
        lock_path = self.manifest.with_name(f".{self.manifest.name}.lock")
        lock_path.touch()
        started = [threading.Event(), threading.Event()]
        errors: list[BaseException] = []

        def writer(target: pathlib.Path, signal: threading.Event) -> None:
            signal.set()
            try:
                record_written_path(
                    target,
                    manifest_path=self.manifest,
                    repo_root=self.repo,
                    feed_root=self.feed,
                )
            except BaseException as exc:  # pragma: no cover - thread handoff
                errors.append(exc)

        threads = [
            threading.Thread(target=writer, args=(target, signal))
            for target, signal in zip(targets, started)
        ]
        with lock_path.open("a+b") as held_lock:
            fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX)
            for thread in threads:
                thread.start()
            for signal in started:
                self.assertTrue(signal.wait(timeout=1))
            for thread in threads:
                thread.join(timeout=0.2)
            waited_for_lock = all(thread.is_alive() for thread in threads)
            fcntl.flock(held_lock.fileno(), fcntl.LOCK_UN)
        for thread in threads:
            thread.join(timeout=2)

        self.assertTrue(waited_for_lock, "concurrent writers bypassed the manifest lock")
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            ),
            ("feed/first.json", "feed/second.json"),
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
        self._init_repo()
        runner = RecordingRunner()

        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertEqual(staged, ("feed/index.json", "feed/reports/openclaw-safe-id.json"))
        add_commands = [command for command in runner.commands if "add" in command]
        self.assertEqual(len(add_commands), 1)
        self.assertEqual(
            add_commands[0][-5:],
            [
                "add",
                "-A",
                "--",
                "feed/index.json",
                "feed/reports/openclaw-safe-id.json",
            ],
        )

    def test_stage_treats_recorded_git_metachar_path_as_literal(self) -> None:
        reports = self.feed / "reports"
        reports.mkdir()
        literal = reports / "report[1].json"
        sibling = reports / "report1.json"
        literal.write_text("literal before\n", encoding="utf-8")
        sibling.write_text("sibling before\n", encoding="utf-8")
        self._commit_all()
        literal.write_text("literal after\n", encoding="utf-8")
        sibling.write_text("sibling after\n", encoding="utf-8")
        record_written_path(
            literal,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, ["feed/reports/report[1].json"])

    def test_git_operations_ignore_hostile_repository_routing_environment(self) -> None:
        target = self.feed / "index.json"
        target.write_text("before\n", encoding="utf-8")
        self._commit_all()
        target.write_text("after\n", encoding="utf-8")
        record_written_path(
            target,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        hostile = pathlib.Path(self.temp.name) / "hostile"
        hostile_target = hostile / "feed" / "index.json"
        hostile_target.parent.mkdir(parents=True)
        hostile_target.write_text("hostile\n", encoding="utf-8")
        self._commit_all(hostile, message="hostile seed")
        hostile_environment = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.worktree",
            "GIT_CONFIG_VALUE_0": str(hostile),
            "GIT_DIR": str(hostile / ".git"),
            "GIT_LITERAL_PATHSPECS": "0",
            "GIT_WORK_TREE": str(hostile),
            "GIT_INDEX_FILE": str(hostile / ".git" / "index"),
        }

        with mock.patch.dict(os.environ, hostile_environment, clear=False):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        hostile_cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=hostile,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, ["feed/index.json"])
        self.assertEqual(hostile_cached, [])

    def test_toctou_directory_swap_leaves_real_index_unchanged(self) -> None:
        target = self.feed / "recorded.json"
        target.write_text("before\n", encoding="utf-8")
        self._commit_all()
        target.write_text("recorded after\n", encoding="utf-8")
        record_written_path(
            target,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )
        mutated = False

        def swapping_runner(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            nonlocal mutated
            if "add" in command and not mutated:
                target.unlink()
                target.mkdir()
                (target / "unrecorded.json").write_text("unexpected\n", encoding="utf-8")
                mutated = True
            return subprocess.run(command, **kwargs)  # type: ignore[arg-type]

        with self.assertRaisesRegex(ValueError, "unrecorded|changed|regular file"):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=swapping_runner,
            )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, [])

    def test_nonzero_add_result_is_rejected_without_real_index_change(self) -> None:
        target = self.feed / "recorded.json"
        target.write_text("before\n", encoding="utf-8")
        self._commit_all()
        target.write_text("after\n", encoding="utf-8")
        record_written_path(
            target,
            manifest_path=self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        def nonchecking_runner(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            if "add" in command:
                return subprocess.CompletedProcess(
                    command,
                    7,
                    stdout=b"",
                    stderr=b"simulated add failure\n",
                )
            return subprocess.run(command, **kwargs)  # type: ignore[arg-type]

        with self.assertRaisesRegex(ValueError, "git add failed.*simulated add failure"):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=nonchecking_runner,
            )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, [])

    def test_tracked_metachar_deletion_uses_literal_git_proof(self) -> None:
        reports = self.feed / "reports"
        reports.mkdir()
        literal = reports / "report[1].json"
        sibling = reports / "report1.json"
        literal.write_text("literal before\n", encoding="utf-8")
        sibling.write_text("sibling before\n", encoding="utf-8")
        self._commit_all()
        literal.unlink()
        sibling.write_text("sibling after\n", encoding="utf-8")

        try:
            recorded = record_tracked_deletion(
                literal,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )
        except ValueError as exc:
            self.fail(f"literal tracked deletion was rejected: {exc}")
        self.assertTrue(recorded)
        stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(cached, ["feed/reports/report[1].json"])

    def test_unicode_newline_deletion_uses_nul_safe_git_output(self) -> None:
        target = self.feed / "reports" / "报告\nline.json"
        target.parent.mkdir()
        target.write_text("before\n", encoding="utf-8")
        self._commit_all()
        target.unlink()

        try:
            recorded = record_tracked_deletion(
                target,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )
        except ValueError as exc:
            self.fail(f"NUL-safe tracked deletion proof failed: {exc}")
        self.assertTrue(recorded)
        stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
            cwd=self.repo,
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        self.assertEqual(cached, ["feed/reports/报告\nline.json".encode(), b""])

    def test_exact_tracked_deletion_can_be_staged(self) -> None:
        deleted = "feed/reports/openclaw-deleted-id.json"
        target = self.repo / deleted
        target.parent.mkdir(parents=True)
        target.write_text("before\n", encoding="utf-8")
        self._commit_all()
        target.unlink()
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": [deleted]}),
            encoding="utf-8",
        )
        runner = RecordingRunner()

        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
            run=runner,
        )

        self.assertEqual(staged, (deleted,))
        add_commands = [command for command in runner.commands if "add" in command]
        self.assertEqual(len(add_commands), 1)
        self.assertEqual(add_commands[0][-4:], ["add", "-A", "--", deleted])

    def test_tracked_deletion_is_recorded_only_after_exact_git_proof(self) -> None:
        deleted = "feed/inbox/openclaw-tracked-id.json"
        self._init_repo()
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
        self.assertEqual(len(runner.commands), 1)
        self.assertEqual(
            runner.commands[0][-7:],
            [
                "ls-files",
                "--error-unmatch",
                "--full-name",
                "--stage",
                "-z",
                "--",
                deleted,
            ],
        )

    def test_untracked_deletion_is_not_recorded(self) -> None:
        deleted = "feed/inbox/openclaw-dispatch-temporary-id.json"
        self._init_repo()
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

    def test_tracked_deletion_surfaces_fatal_git_error(self) -> None:
        deleted = self.feed / "fatal.json"
        self._init_repo()

        def fatal_runner(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(
                command,
                128,
                stdout=b"",
                stderr=b"fatal: corrupt index\n",
            )

        with self.assertRaisesRegex(ValueError, "fatal: corrupt index"):
            record_tracked_deletion(
                deleted,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=fatal_runner,
            )
        self.assertFalse(self.manifest.exists())

    def test_self_loop_symlink_is_rejected_before_git_proof(self) -> None:
        symlink = self.feed / "loop.json"
        symlink.symlink_to(symlink.name)
        runner = FakeRunner({"feed/loop.json"})

        try:
            record_tracked_deletion(
                symlink,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=runner,
            )
        except ValueError as exc:
            self.assertRegex(str(exc), "symlink")
        except Exception as exc:  # pragma: no cover - RED diagnostic
            self.fail(f"symlink escaped controlled validation: {type(exc).__name__}: {exc}")
        else:
            self.fail("self-loop symlink was accepted as a deletion")
        self.assertEqual(runner.commands, [])
        self.assertFalse(self.manifest.exists())

    def test_broken_existing_symlinks_and_special_files_are_rejected(self) -> None:
        target = self.feed / "target.json"
        target.write_text("{}\n", encoding="utf-8")
        existing_symlink = self.feed / "existing-link.json"
        existing_symlink.symlink_to(target.name)
        broken_symlink = self.feed / "broken-link.json"
        broken_symlink.symlink_to("missing.json")
        fifo = self.feed / "special.fifo"
        os.mkfifo(fifo)
        runner = FakeRunner()

        for invalid in (existing_symlink, broken_symlink, fifo):
            with self.subTest(path=invalid.name):
                with self.assertRaisesRegex(ValueError, "symlink|regular file"):
                    record_tracked_deletion(
                        invalid,
                        manifest_path=self.manifest,
                        repo_root=self.repo,
                        feed_root=self.feed,
                        run=runner,
                    )

        self.assertEqual(runner.commands, [])
        self.assertFalse(self.manifest.exists())

    def test_deleted_tracked_symlink_is_not_a_regular_file_deletion(self) -> None:
        target = self.feed / "target.json"
        target.write_text("{}\n", encoding="utf-8")
        symlink = self.feed / "tracked-link.json"
        symlink.symlink_to(target.name)
        self._commit_all()
        symlink.unlink()

        with self.assertRaisesRegex(ValueError, "tracked regular file"):
            record_tracked_deletion(
                symlink,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )
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
        self._init_repo()
        runner = RecordingRunner()

        with self.assertRaisesRegex(ValueError, "not an existing or tracked regular file"):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=runner,
            )

        self.assertFalse(any("add" in command for command in runner.commands))

    def test_staging_surfaces_fatal_git_proof_error(self) -> None:
        missing = "feed/reports/fatal.json"
        self.manifest.write_text(
            json.dumps({"schema_version": "1.0", "paths": [missing]}),
            encoding="utf-8",
        )
        self._init_repo()

        def fatal_runner(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(
                command,
                128,
                stdout=b"",
                stderr=b"fatal: unreadable index\n",
            )

        with self.assertRaisesRegex(ValueError, "fatal: unreadable index"):
            stage_recorded_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
                run=fatal_runner,
            )

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

    def test_cli_returns_one_without_traceback_for_bad_manifest(self) -> None:
        script = pathlib.Path(__file__).resolve().parents[1] / "feed_publication.py"

        result = subprocess.run(
            [sys.executable, str(script), "stage", str(self.manifest)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("feed publication staging failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_feed_lib_write_records_path_when_manifest_is_configured(self) -> None:
        target = self.feed / "market" / "state.json"
        with mock.patch.object(publication, "REPO_ROOT", self.repo), mock.patch.object(
            publication, "FEED_ROOT", self.feed
        ), mock.patch.dict(
            os.environ,
            {publication.MANIFEST_ENV: str(self.manifest)},
            clear=False,
        ):
            fl.save_json(str(target), {"updated_at": "2026-07-16T00:00:00Z"})

        self.assertEqual(
            load_manifest_paths(
                self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            ),
            ("feed/market/state.json",),
        )

    def test_feed_lib_write_without_manifest_does_not_import_publication(self) -> None:
        real_import = __import__

        def reject_publication_import(
            name: str, *args: object, **kwargs: object
        ) -> object:
            if name == "feed_publication":
                raise AssertionError("unconfigured write imported feed_publication")
            return real_import(name, *args, **kwargs)

        cases = (
            ("unset", {}),
            ("empty", {publication.MANIFEST_ENV: ""}),
        )
        for label, environment in cases:
            with self.subTest(manifest=label):
                target = self.feed / "market" / f"{label}.json"
                with mock.patch.dict(
                    os.environ, environment, clear=True
                ), mock.patch(
                    "builtins.__import__", side_effect=reject_publication_import
                ):
                    fl.save_json(str(target), {"manifest": label})

                self.assertEqual(
                    json.loads(
                        target.read_text(encoding="utf-8"),
                        parse_constant=fl.reject_json_constant,
                    ),
                    {"manifest": label},
                )

    def test_dispatch_create_merge_stage_excludes_temporary_inbox(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        inbox = self.feed / "inbox"
        inbox.mkdir()
        report = {
            "schema_version": "1.0",
            "id": "openclaw-dispatch-lifecycle-test",
            "kind": "openclaw",
            "produced_at": "2026-07-16T00:00:00Z",
            "asof_data": "2026-07-16",
            "producer": {"name": "dispatch-lifecycle-test"},
        }

        with mock.patch.object(publication, "REPO_ROOT", self.repo), mock.patch.object(
            publication, "FEED_ROOT", self.feed
        ), mock.patch.object(fl, "FEED", str(self.feed)), mock.patch.dict(
            os.environ,
            {publication.MANIFEST_ENV: str(self.manifest)},
            clear=False,
        ), mock.patch.object(
            feed_ingress,
            "check_report",
            return_value=(True, []),
        ), mock.patch.object(
            validate_feed,
            "check_one",
            return_value=(True, [], report),
        ):
            dispatch_path = feed_ingress.receive_dispatch(
                report,
                secret="dispatch-lifecycle-secret",
                inbox_dir=inbox,
            )
            self.assertFalse(
                self.manifest.exists(),
                "temporary dispatch creation must not publish its inbox path",
            )

            rc = validate_feed.main(
                ["--merge", "--require-signature", dispatch_path]
            )

        self.assertEqual(rc, 0)
        recorded = load_manifest_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )
        self.assertNotIn("feed/inbox/openclaw-dispatch-lifecycle-test.json", recorded)
        self.assertIn("feed/reports/openclaw-dispatch-lifecycle-test.json", recorded)
        self.assertIn("feed/index.json", recorded)

        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )
        self.assertEqual(staged, recorded)
        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertNotIn("feed/inbox/openclaw-dispatch-lifecycle-test.json", cached)
        self.assertEqual(cached, list(recorded))

    def test_tracked_inbox_deletion_is_recorded_and_staged(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        tracked = self.feed / "inbox" / "openclaw-tracked-delete-test.json"
        tracked.parent.mkdir()
        tracked.write_text("{}\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "--", "feed/inbox/openclaw-tracked-delete-test.json"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=stage-1a-test",
                "-c",
                "user.email=stage-1a@example.invalid",
                "commit",
                "-q",
                "-m",
                "seed tracked inbox",
            ],
            cwd=self.repo,
            check=True,
        )
        tracked.unlink()

        self.assertTrue(
            record_tracked_deletion(
                tracked,
                manifest_path=self.manifest,
                repo_root=self.repo,
                feed_root=self.feed,
            )
        )
        staged = stage_recorded_paths(
            self.manifest,
            repo_root=self.repo,
            feed_root=self.feed,
        )

        self.assertEqual(staged, ("feed/inbox/openclaw-tracked-delete-test.json",))
        status = subprocess.run(
            ["git", "diff", "--cached", "--name-status"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(status, ["D\tfeed/inbox/openclaw-tracked-delete-test.json"])

    def test_openclaw_analysis_records_markdown_after_successful_close(self) -> None:
        class TrackingWriter:
            def __init__(self) -> None:
                self.closed = False

            def __enter__(self) -> "TrackingWriter":
                return self

            def write(self, text: str) -> int:
                return len(text)

            def __exit__(self, *args: object) -> None:
                self.closed = True

        writer = TrackingWriter()
        missing = self.repo / "missing.json"
        out = self.feed / "screener" / "analysis-2026-07-16.md"
        out.parent.mkdir()
        with mock.patch.object(fl, "FEED", str(self.feed)), mock.patch.object(
            fl, "REPO_ROOT", str(self.repo)
        ), mock.patch.object(
            openclaw_daily, "WATCHLIST_FILE", str(missing)
        ), mock.patch.object(
            openclaw_daily, "SA_LP_FILE", str(missing)
        ), mock.patch(
            "builtins.open", return_value=writer
        ), mock.patch.object(
            fl, "record_publication_path"
        ) as recorder:
            recorder.side_effect = lambda path: self.assertTrue(writer.closed)

            openclaw_daily.write_daily_analysis("2026-07-16", [])

        recorder.assert_called_once_with(str(out))

    def test_openclaw_analysis_does_not_record_failed_markdown_write(self) -> None:
        class FailingWriter:
            def __enter__(self) -> "FailingWriter":
                return self

            def write(self, text: str) -> int:
                raise OSError("simulated Markdown write failure")

            def __exit__(self, *args: object) -> None:
                return None

        missing = self.repo / "missing.json"
        (self.feed / "screener").mkdir()
        with mock.patch.object(fl, "FEED", str(self.feed)), mock.patch.object(
            fl, "REPO_ROOT", str(self.repo)
        ), mock.patch.object(
            openclaw_daily, "WATCHLIST_FILE", str(missing)
        ), mock.patch.object(
            openclaw_daily, "SA_LP_FILE", str(missing)
        ), mock.patch(
            "builtins.open", return_value=FailingWriter()
        ), mock.patch.object(
            fl, "record_publication_path"
        ) as recorder:
            with self.assertRaisesRegex(OSError, "simulated Markdown write failure"):
                openclaw_daily.write_daily_analysis("2026-07-16", [])

        recorder.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
