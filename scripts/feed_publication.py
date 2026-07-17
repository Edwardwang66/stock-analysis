#!/usr/bin/env python3
"""Transitional Stage 1A allowlist for staging current feed writes."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from feed_lib import reject_json_constant


REPO_ROOT = Path(__file__).resolve().parents[1]
FEED_ROOT = REPO_ROOT / "feed"
MANIFEST_ENV = "FEED_PUBLICATION_MANIFEST"
MANIFEST_SCHEMA_VERSION = "1.0"
Runner = Callable[..., subprocess.CompletedProcess[str]]


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


def _normalize_feed_path(
    path: str | os.PathLike[str],
    *,
    repo_root: str | os.PathLike[str] | None,
    feed_root: str | os.PathLike[str] | None,
) -> str:
    repo, feed = _roots(repo_root, feed_root)
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else repo / candidate).resolve()
    try:
        resolved.relative_to(feed)
    except ValueError as exc:
        raise ValueError(f"publication path is outside feed root: {path}") from exc
    if resolved == feed:
        raise ValueError("publication path must name a file, not the feed root")
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"publication path must name a regular file: {path}")
    return resolved.relative_to(repo).as_posix()


def _manifest_path(path: str | os.PathLike[str] | None) -> Path | None:
    configured = path if path is not None else os.environ.get(MANIFEST_ENV)
    return Path(configured) if configured else None


def _literal_git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for variable in ("GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"):
        environment.pop(variable, None)
    environment["GIT_LITERAL_PATHSPECS"] = "1"
    return environment


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
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
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
    tracked = run(
        ["git", "ls-files", "--error-unmatch", "--full-name", "--", canonical],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=_literal_git_environment(),
    )
    if tracked.returncode != 0:
        return False
    if tracked.stdout.splitlines() != [canonical]:
        raise ValueError(
            f"deleted publication path did not resolve to one exact tracked file: {canonical}"
        )
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
    stageable: list[str] = []
    for relative_path in recorded:
        absolute_path = repo / relative_path
        if absolute_path.is_file():
            stageable.append(relative_path)
            continue
        if absolute_path.exists():
            raise ValueError(f"publication path is not a regular file: {relative_path}")
        tracked = run(
            ["git", "ls-files", "--error-unmatch", "--full-name", "--", relative_path],
            cwd=str(repo),
            capture_output=True,
            text=True,
            env=_literal_git_environment(),
        )
        tracked_paths = tracked.stdout.splitlines()
        if tracked.returncode == 0 and tracked_paths == [relative_path]:
            stageable.append(relative_path)
            continue
        if tracked.returncode == 0:
            raise ValueError(f"publication path did not resolve to one exact tracked file: {relative_path}")
        raise ValueError(f"publication path is not an existing or tracked file: {relative_path}")
    if not stageable:
        raise ValueError("publication manifest contains no existing or tracked paths")
    run(
        ["git", "add", "-A", "--", *stageable],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
        env=_literal_git_environment(),
    )
    return tuple(stageable)


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
