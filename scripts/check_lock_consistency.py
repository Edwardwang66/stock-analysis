#!/usr/bin/env python3
"""Fail-closed consistency checks for the repository's primary Python locks."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import pathlib
import re
import sys
from collections.abc import Sequence


LOCK_PAIRS = (
    ("backend/requirements.txt", "requirements/ci-py311.txt"),
    ("scripts/requirements.txt", "requirements/ci-py311.txt"),
    ("scripts/requirements.txt", "requirements/automation.txt"),
    ("backtest/requirements.txt", "requirements/automation.txt"),
)

_NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_NAME_RE = re.compile(rf"^{_NAME_PATTERN}$")
_NORMALIZE_RE = re.compile(r"[-_.]+")
_HEADER_RE = re.compile(
    rf"^(?P<name>{_NAME_PATTERN})"
    rf"(?:\[(?P<extras>[^]]+)\])?"
    r"==(?P<version>[^\s;#\\]+)"
    r"(?:[ \t]*;(?P<marker>.*))?$"
)
_HASH_RE = re.compile(
    r"^[ \t]+--hash=sha256:(?P<digest>[0-9A-Fa-f]{64})"
    r"(?P<continuation>[ \t]+\\)?[ \t]*$"
)


class LockError(ValueError):
    """A lock cannot be parsed or violates the fixed subset contract."""


@dataclass(frozen=True)
class LockEntry:
    """One validated exact requirement from a compiled hash lock."""

    name: str
    version: str
    marker: str | None
    hashes: frozenset[str]
    line: int


def _normalize_name(name: str) -> str:
    return _NORMALIZE_RE.sub("-", name).lower()


def _location(path: pathlib.Path, line: int) -> str:
    return f"{path}:{line}"


def _parse_header(path: pathlib.Path, line_number: int, line: str) -> tuple[str, str, str | None]:
    location = _location(path, line_number)
    if "#" in line:
        raise LockError(f"{location}: inline comments are unsupported")
    if not re.search(r"[ \t]+\\[ \t]*$", line):
        if "==" in line:
            raise LockError(f"{location}: exact requirement is missing its hash continuation")
        raise LockError(f"{location}: unsupported requirement syntax; expected an exact == entry")

    header = re.sub(r"[ \t]+\\[ \t]*$", "", line)
    match = _HEADER_RE.fullmatch(header)
    if match is None:
        raise LockError(f"{location}: unsupported requirement syntax; expected an exact == entry")

    version = match.group("version")
    if any(character in version for character in "*<>=~@/"):
        raise LockError(f"{location}: version must use one exact == value")

    extras = match.group("extras")
    if extras is not None:
        normalized_extras: set[str] = set()
        for extra in extras.split(","):
            if _NAME_RE.fullmatch(extra) is None:
                raise LockError(f"{location}: invalid extra name {extra!r}")
            normalized_extra = _normalize_name(extra)
            if normalized_extra in normalized_extras:
                raise LockError(f"{location}: duplicate normalized extra {normalized_extra!r}")
            normalized_extras.add(normalized_extra)

    marker_text = match.group("marker")
    marker = marker_text.strip() if marker_text is not None else None
    if marker == "":
        raise LockError(f"{location}: empty environment marker is unsupported")

    return _normalize_name(match.group("name")), version, marker


def parse_lock(path: pathlib.Path | str) -> dict[str, LockEntry]:
    """Parse a pip-tools hash lock using a physical-line state machine."""

    lock_path = pathlib.Path(path)
    try:
        lines = lock_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise LockError(f"{lock_path}: cannot read lock: {exc}") from exc

    entries: dict[str, LockEntry] = {}
    state = "idle"
    pending_name = ""
    pending_version = ""
    pending_marker: str | None = None
    pending_line = 0
    pending_hashes: set[str] = set()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if state == "hashes":
            if stripped == "":
                raise LockError(
                    f"{_location(lock_path, line_number)}: blank line interrupts hash continuation"
                )
            if line.lstrip().startswith("#"):
                raise LockError(
                    f"{_location(lock_path, line_number)}: comment interrupts hash continuation"
                )
            hash_match = _HASH_RE.fullmatch(line)
            if hash_match is None:
                raise LockError(
                    f"{_location(lock_path, line_number)}: malformed SHA-256 hash continuation"
                )
            digest = hash_match.group("digest").lower()
            if digest in pending_hashes:
                raise LockError(
                    f"{_location(lock_path, line_number)}: duplicate SHA-256 hash {digest}"
                )
            pending_hashes.add(digest)
            if hash_match.group("continuation") is not None:
                continue

            if pending_name in entries:
                first_line = entries[pending_name].line
                raise LockError(
                    f"{_location(lock_path, pending_line)}: duplicate normalized package "
                    f"{pending_name!r}; first declared on line {first_line}"
                )
            entries[pending_name] = LockEntry(
                name=pending_name,
                version=pending_version,
                marker=pending_marker,
                hashes=frozenset(pending_hashes),
                line=pending_line,
            )
            state = "after-entry"
            continue

        if state == "after-entry":
            if stripped == "":
                state = "idle"
                continue
            if line.lstrip().startswith("#"):
                continue
            if line[0].isspace():
                raise LockError(
                    f"{_location(lock_path, line_number)}: unexpected indented content after hash entry"
                )
            state = "idle"

        if stripped == "" or line.lstrip().startswith("#"):
            continue
        if line[0].isspace():
            raise LockError(f"{_location(lock_path, line_number)}: unexpected indented content")

        pending_name, pending_version, pending_marker = _parse_header(
            lock_path, line_number, line
        )
        pending_line = line_number
        pending_hashes = set()
        state = "hashes"

    if state == "hashes":
        raise LockError(
            f"{_location(lock_path, pending_line)}: dangling hash continuation at end of file"
        )
    return entries


def check_pair(source: pathlib.Path | str, target: pathlib.Path | str) -> None:
    """Require every source package to exist compatibly in the target lock."""

    source_path = pathlib.Path(source)
    target_path = pathlib.Path(target)
    source_entries = parse_lock(source_path)
    target_entries = parse_lock(target_path)

    for name, source_entry in source_entries.items():
        target_entry = target_entries.get(name)
        if target_entry is None:
            raise LockError(
                f"{source_path} -> {target_path}: target missing package "
                f"{name}=={source_entry.version}"
            )
        if source_entry.version != target_entry.version:
            raise LockError(
                f"{source_path} -> {target_path}: version drift for package {name}: "
                f"source={source_entry.version}, target={target_entry.version}"
            )

        source_marker = source_entry.marker
        target_marker = target_entry.marker
        if target_marker is None:
            continue
        if source_marker is None or source_marker != target_marker:
            raise LockError(
                f"{source_path} -> {target_path}: marker mismatch for package {name}: "
                f"source={source_marker!r}, target={target_marker!r}"
            )


def check_repository(root: pathlib.Path | str) -> int:
    """Check the fixed primary-runtime subset pairs below a repository root."""

    root_path = pathlib.Path(root)
    for source, target in LOCK_PAIRS:
        check_pair(root_path / source, root_path / target)
    return len(LOCK_PAIRS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check fixed primary-runtime Python lock subset invariants."
    )
    parser.add_argument(
        "--root",
        default=".",
        type=pathlib.Path,
        help="repository root (default: current directory)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        checked = check_repository(args.root)
    except LockError as exc:
        print(f"lock consistency FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"lock consistency OK: {checked} subset pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
