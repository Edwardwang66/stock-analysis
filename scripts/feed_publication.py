#!/usr/bin/env python3
"""Transitional Stage 1A allowlist for staging current feed writes."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import fcntl

from feed_lib import reject_json_constant


REPO_ROOT = Path(__file__).resolve().parents[1]
FEED_ROOT = REPO_ROOT / "feed"
MANIFEST_ENV = "FEED_PUBLICATION_MANIFEST"
MANIFEST_SCHEMA_VERSION = "1.0"
Runner = Callable[..., subprocess.CompletedProcess[str | bytes]]
IndexEntry = tuple[str, str, int]
IndexEntries = dict[str, tuple[IndexEntry, ...]]


def _roots(
    repo_root: str | os.PathLike[str] | None,
    feed_root: str | os.PathLike[str] | None,
) -> tuple[Path, Path]:
    repo = Path(repo_root if repo_root is not None else REPO_ROOT).resolve()
    feed = Path(feed_root if feed_root is not None else FEED_ROOT).resolve()
    try:
        feed.relative_to(repo)
    except ValueError as exc:
        raise ValueError("feed root must be inside repository root") from exc
    return repo, feed


def _publication_path_kind(path: Path) -> str:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        raise ValueError(f"publication path cannot be inspected: {path}") from exc
    if stat.S_ISLNK(mode):
        raise ValueError(f"publication path must not be a symlink: {path}")
    if not stat.S_ISREG(mode):
        raise ValueError(f"publication path must name a regular file: {path}")
    return "regular"


def _normalize_feed_path(
    path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str] | None,
    feed_root: str | os.PathLike[str] | None,
) -> str:
    repo, feed = _roots(repo_root, feed_root)
    candidate = Path(path)
    absolute = candidate if candidate.is_absolute() else repo / candidate
    _publication_path_kind(absolute)
    try:
        resolved = absolute.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"publication path cannot be resolved: {path}") from exc
    try:
        resolved.relative_to(feed)
    except ValueError as exc:
        raise ValueError(f"publication path is outside feed root: {path}") from exc
    if resolved == feed:
        raise ValueError("publication path must name a file, not the feed root")
    return resolved.relative_to(repo).as_posix()


def _manifest_path(path: str | os.PathLike[str] | None) -> Path | None:
    configured = path if path is not None else os.environ.get(MANIFEST_ENV)
    return Path(configured) if configured else None


def _literal_git_environment(index_file: Path | None = None) -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment["GIT_LITERAL_PATHSPECS"] = "1"
    if index_file is not None:
        environment["GIT_INDEX_FILE"] = str(index_file)
    return environment


def _output_bytes(output: str | bytes | None) -> bytes:
    if output is None:
        return b""
    if isinstance(output, bytes):
        return output
    return os.fsencode(output)


def _git_diagnostic(result: subprocess.CompletedProcess[str | bytes]) -> str:
    diagnostic = os.fsdecode(_output_bytes(result.stderr)).strip()
    return diagnostic or "no diagnostic output"


def _git_directory(repo: Path) -> Path:
    marker = repo / ".git"
    if marker.is_dir():
        return marker.resolve()
    try:
        marker_text = marker.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"repository has no readable .git directory: {repo}") from exc
    line = marker_text.rstrip("\r\n")
    if "\n" in line or "\r" in line or not line.startswith("gitdir: "):
        raise ValueError(f"repository has an invalid .git file: {repo}")
    configured = Path(line.removeprefix("gitdir: "))
    git_dir = (configured if configured.is_absolute() else repo / configured).resolve()
    if not git_dir.is_dir():
        raise ValueError(f"repository git directory does not exist: {git_dir}")
    return git_dir


def _git_command(repo: Path, git_dir: Path, *arguments: str) -> list[str]:
    return [
        "git",
        f"--git-dir={git_dir}",
        f"--work-tree={repo}",
        *arguments,
    ]


def _run_git_checked(
    run: Runner,
    command: list[str],
    *,
    repo: Path,
    environment: dict[str, str],
    operation: str,
) -> subprocess.CompletedProcess[str | bytes]:
    try:
        result = run(
            command,
            cwd=str(repo),
            check=True,
            capture_output=True,
            env=environment,
        )
    except subprocess.CalledProcessError as exc:
        failed = subprocess.CompletedProcess(
            exc.cmd,
            exc.returncode,
            stdout=exc.stdout,
            stderr=exc.stderr,
        )
        raise ValueError(
            f"{operation} failed with exit {exc.returncode}: {_git_diagnostic(failed)}"
        ) from exc
    if result.returncode != 0:
        raise ValueError(
            f"{operation} failed with exit {result.returncode}: {_git_diagnostic(result)}"
        )
    return result


def _parse_index_entries(output: str | bytes | None) -> IndexEntries:
    payload = _output_bytes(output)
    if not payload:
        return {}
    if not payload.endswith(b"\0"):
        raise ValueError("git ls-files returned a non-NUL-terminated index listing")
    entries: dict[str, list[IndexEntry]] = {}
    for record in payload[:-1].split(b"\0"):
        try:
            metadata, raw_path = record.split(b"\t", 1)
            raw_mode, raw_oid, raw_stage = metadata.split(b" ")
            entry = (
                raw_mode.decode("ascii"),
                raw_oid.decode("ascii"),
                int(raw_stage.decode("ascii")),
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("git ls-files returned an invalid index entry") from exc
        entries.setdefault(os.fsdecode(raw_path), []).append(entry)
    return {
        path: tuple(sorted(path_entries, key=lambda item: item[2]))
        for path, path_entries in entries.items()
    }


def _read_index_entries(
    repo: Path,
    git_dir: Path,
    index_file: Path,
    run: Runner,
) -> IndexEntries:
    result = _run_git_checked(
        run,
        _git_command(repo, git_dir, "ls-files", "--stage", "-z"),
        repo=repo,
        environment=_literal_git_environment(index_file),
        operation="git index listing",
    )
    return _parse_index_entries(result.stdout)


def _regular_index_entry(entries: tuple[IndexEntry, ...] | None) -> bool:
    return bool(
        entries
        and len(entries) == 1
        and entries[0][2] == 0
        and entries[0][0] in {"100644", "100755"}
    )


def load_manifest_paths(
    manifest_path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str] | None = None,
    feed_root: str | os.PathLike[str] | None = None,
) -> tuple[str, ...]:
    manifest = Path(manifest_path)
    try:
        data = json.loads(
            manifest.read_text(encoding="utf-8"),
            parse_constant=reject_json_constant,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"publication manifest is unreadable: {manifest}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("publication manifest schema_version must be 1.0")
    raw_paths = data.get("paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        raise ValueError("publication manifest contains no paths")

    normalized: set[str] = set()
    for raw_path in raw_paths:
        if not isinstance(raw_path, str):
            raise ValueError("publication manifest paths must be strings")
        canonical = _normalize_feed_path(
            raw_path,
            repo_root=repo_root,
            feed_root=feed_root,
        )
        if canonical != raw_path:
            raise ValueError(f"publication path is not canonical: {raw_path}")
        normalized.add(canonical)
    return tuple(sorted(normalized))


def record_written_path(
    path: str | os.PathLike[str],
    *,
    manifest_path: str | os.PathLike[str] | None = None,
    repo_root: str | os.PathLike[str] | None = None,
    feed_root: str | os.PathLike[str] | None = None,
) -> None:
    manifest = _manifest_path(manifest_path)
    if manifest is None:
        return
    canonical = _normalize_feed_path(
        path,
        repo_root=repo_root,
        feed_root=feed_root,
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    lock_path = manifest.with_name(f".{manifest.name}.lock")
    with lock_path.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        temporary_name: str | None = None
        try:
            existing: set[str] = set()
            if manifest.exists():
                existing.update(
                    load_manifest_paths(
                        manifest,
                        repo_root=repo_root,
                        feed_root=feed_root,
                    )
                )
            existing.add(canonical)
            payload = {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "paths": sorted(existing),
            }
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=manifest.parent,
                prefix=f".{manifest.name}.",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
                temporary_name = handle.name
            os.replace(temporary_name, manifest)
        finally:
            if temporary_name is not None and os.path.exists(temporary_name):
                os.unlink(temporary_name)
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def record_tracked_deletion(
    path: str | os.PathLike[str],
    *,
    manifest_path: str | os.PathLike[str] | None = None,
    repo_root: str | os.PathLike[str] | None = None,
    feed_root: str | os.PathLike[str] | None = None,
    run: Runner = subprocess.run,
) -> bool:
    manifest = _manifest_path(manifest_path)
    if manifest is None:
        return False
    repo, _ = _roots(repo_root, feed_root)
    canonical = _normalize_feed_path(
        path,
        repo_root=repo_root,
        feed_root=feed_root,
    )
    if (repo / canonical).exists():
        raise ValueError(f"deleted publication path still exists: {canonical}")
    git_dir = _git_directory(repo)
    tracked = run(
        _git_command(
            repo,
            git_dir,
            "ls-files",
            "--error-unmatch",
            "--full-name",
            "--stage",
            "-z",
            "--",
            canonical,
        ),
        cwd=str(repo),
        capture_output=True,
        env=_literal_git_environment(),
    )
    if tracked.returncode == 1:
        return False
    if tracked.returncode != 0:
        raise ValueError(
            f"git ls-files failed with exit {tracked.returncode}: {_git_diagnostic(tracked)}"
        )
    tracked_entries = _parse_index_entries(tracked.stdout)
    if set(tracked_entries) != {canonical} or not _regular_index_entry(
        tracked_entries.get(canonical)
    ):
        raise ValueError(
            "deleted publication path did not resolve to one exact tracked regular file: "
            f"{canonical}"
        )
    if _publication_path_kind(repo / canonical) != "missing":
        raise ValueError(f"deleted publication path appeared during proof: {canonical}")
    record_written_path(
        canonical,
        manifest_path=manifest,
        repo_root=repo_root,
        feed_root=feed_root,
    )
    return True


def stage_recorded_paths(
    manifest_path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str] | None = None,
    feed_root: str | os.PathLike[str] | None = None,
    run: Runner = subprocess.run,
) -> tuple[str, ...]:
    repo, _ = _roots(repo_root, feed_root)
    recorded = load_manifest_paths(
        manifest_path,
        repo_root=repo_root,
        feed_root=feed_root,
    )
    git_dir = _git_directory(repo)
    index_path = git_dir / "index"
    lock_path = git_dir / "index.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"git index is locked: {lock_path}") from exc
    os.close(lock_fd)

    temporary_index: Path | None = None
    temporary_lock: Path | None = None
    committed = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=git_dir,
            prefix=".feed-publication-index.",
        )
        os.close(descriptor)
        temporary_index = Path(temporary_name)
        temporary_lock = Path(temporary_name + ".lock")
        if _publication_path_kind(index_path) == "regular":
            shutil.copyfile(index_path, temporary_index)
            shutil.copymode(index_path, temporary_index)
        else:
            temporary_index.unlink()

        before = _read_index_entries(repo, git_dir, temporary_index, run)
        initial_kinds: dict[str, str] = {}
        for relative_path in recorded:
            kind = _publication_path_kind(repo / relative_path)
            if kind == "missing" and not _regular_index_entry(before.get(relative_path)):
                raise ValueError(
                    f"publication path is not an existing or tracked regular file: {relative_path}"
                )
            initial_kinds[relative_path] = kind

        _run_git_checked(
            run,
            _git_command(repo, git_dir, "add", "-A", "--", *recorded),
            repo=repo,
            environment=_literal_git_environment(temporary_index),
            operation="git add",
        )
        after = _read_index_entries(repo, git_dir, temporary_index, run)
        changed_paths = {
            path
            for path in before.keys() | after.keys()
            if before.get(path) != after.get(path)
        }
        unexpected = sorted(changed_paths - set(recorded))
        if unexpected:
            raise ValueError(f"git add staged unrecorded paths: {', '.join(unexpected)}")

        for relative_path, initial_kind in initial_kinds.items():
            final_kind = _publication_path_kind(repo / relative_path)
            if final_kind != initial_kind:
                raise ValueError(f"publication path changed type during staging: {relative_path}")
            final_entries = after.get(relative_path)
            if final_kind == "regular" and not _regular_index_entry(final_entries):
                raise ValueError(
                    f"publication path was not staged as a regular file: {relative_path}"
                )
            if final_kind == "missing" and final_entries is not None:
                raise ValueError(f"tracked publication deletion was not staged: {relative_path}")

        worktree_check = run(
            _git_command(repo, git_dir, "diff-files", "--quiet", "--", *recorded),
            cwd=str(repo),
            capture_output=True,
            env=_literal_git_environment(temporary_index),
        )
        if worktree_check.returncode != 0:
            if worktree_check.returncode == 1:
                raise ValueError("publication paths changed while staging")
            raise ValueError(
                "git worktree verification failed with exit "
                f"{worktree_check.returncode}: {_git_diagnostic(worktree_check)}"
            )

        os.replace(temporary_index, lock_path)
        temporary_index = None
        os.replace(lock_path, index_path)
        committed = True
    finally:
        if temporary_index is not None and temporary_index.exists():
            temporary_index.unlink()
        if temporary_lock is not None and temporary_lock.exists():
            temporary_lock.unlink()
        if not committed and lock_path.exists():
            lock_path.unlink()
    return recorded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    stage_parser = subparsers.add_parser("stage")
    stage_parser.add_argument("manifest")
    args = parser.parse_args(argv)
    try:
        staged = stage_recorded_paths(args.manifest)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"feed publication staging failed: {exc}", file=sys.stderr)
        return 1
    print("staged feed paths:")
    for path in staged:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
