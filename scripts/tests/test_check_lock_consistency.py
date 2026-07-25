"""Tests for the fail-closed cross-lock consistency checker."""
from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check_lock_consistency import (  # noqa: E402
    LOCK_PAIRS,
    LockError,
    check_pair,
    check_repository,
    main,
    parse_lock,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def lock_entry(
    name: str,
    version: str = "1.0",
    *,
    marker: str | None = None,
    hashes: tuple[str, ...] = (HASH_A,),
    via: tuple[str, ...] = (),
) -> str:
    requirement = f"{name}=={version}"
    if marker is not None:
        requirement += f" ; {marker}"
    lines = [requirement + " \\"]
    for index, digest in enumerate(hashes):
        continuation = " \\" if index < len(hashes) - 1 else ""
        lines.append(f"    --hash=sha256:{digest}{continuation}")
    if via:
        lines.append("    # via")
        lines.extend(f"    #   {dependency}" for dependency in via)
    return "\n".join(lines) + "\n"


def write_lock(root: pathlib.Path, relative: str, content: str) -> pathlib.Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def populate_repository(root: pathlib.Path) -> None:
    backend = lock_entry("backend-only")
    scripts = lock_entry("scripts_only")
    backtest = lock_entry("backtest.only")
    write_lock(root, "backend/requirements.txt", backend)
    write_lock(root, "scripts/requirements.txt", scripts)
    write_lock(root, "backtest/requirements.txt", backtest)
    write_lock(root, "requirements/ci-py311.txt", backend + scripts)
    write_lock(root, "requirements/automation.txt", scripts + backtest)


class LockParserTests(unittest.TestCase):
    def test_multiline_hashes_via_comments_and_unsafe_preamble_parse(self) -> None:
        content = (
            "# The following packages are considered to be unsafe in a requirements file:\n"
            "    # an indented whole-line comment is valid while idle\n"
            + lock_entry("pip", "25.2", hashes=(HASH_A, HASH_B), via=("pip-tools",))
            + "\n"
            + lock_entry("setuptools", "83.0.0", via=("pip-tools",))
        )
        with tempfile.TemporaryDirectory() as td:
            path = write_lock(pathlib.Path(td), "lock.txt", content)
            parsed = parse_lock(path)

        self.assertEqual(set(parsed), {"pip", "setuptools"})
        self.assertEqual(parsed["pip"].hashes, frozenset({HASH_A, HASH_B}))
        self.assertEqual(parsed["pip"].version, "25.2")

    def test_names_and_extras_normalize_but_duplicates_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = write_lock(root, "source.txt", lock_entry("Foo_Bar[extra]"))
            target = write_lock(root, "target.txt", lock_entry("foo.bar"))
            self.assertIn("foo-bar", parse_lock(source))
            check_pair(source, target)

            source.write_text(
                lock_entry("Foo_Bar[extra]") + lock_entry("foo.bar"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LockError, "duplicate.*foo-bar"):
                parse_lock(source)

    def test_missing_target_and_version_drift_have_actionable_details(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = write_lock(root, "source.lock", lock_entry("Demo_Pkg", "1.0"))
            target = write_lock(root, "target.lock", lock_entry("other", "1.0"))
            with self.assertRaises(LockError) as missing:
                check_pair(source, target)
            message = str(missing.exception)
            for detail in ("source.lock", "target.lock", "demo-pkg", "1.0", "missing"):
                self.assertIn(detail, message)

            target.write_text(lock_entry("demo.pkg", "2.0"), encoding="utf-8")
            with self.assertRaises(LockError) as drift:
                check_pair(source, target)
            message = str(drift.exception)
            for detail in ("source.lock", "target.lock", "demo-pkg", "1.0", "2.0"):
                self.assertIn(detail, message)

    def test_marker_subset_rules_are_conservative(self) -> None:
        marked = 'python_version == "3.11"'
        cases = (
            (marked, f"  {marked}  ", True),
            (marked, None, True),
            (None, marked, False),
            (marked, 'python_version == "3.12"', False),
            ('platform_release == "A B"', 'platform_release == "A  B"', False),
        )
        for source_marker, target_marker, should_pass in cases:
            with self.subTest(
                source_marker=source_marker,
                target_marker=target_marker,
            ), tempfile.TemporaryDirectory() as td:
                root = pathlib.Path(td)
                source = write_lock(
                    root,
                    "source.txt",
                    lock_entry("demo", marker=source_marker),
                )
                target = write_lock(
                    root,
                    "target.txt",
                    lock_entry("demo", marker=target_marker),
                )
                if should_pass:
                    check_pair(source, target)
                else:
                    with self.assertRaisesRegex(LockError, "marker"):
                        check_pair(source, target)

    def test_marker_literal_may_contain_hash_option_text(self) -> None:
        marker = 'implementation_name == "--hash=sentinel"'
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            source = write_lock(
                root,
                "source.txt",
                lock_entry("demo", marker=marker, hashes=(HASH_A, HASH_B)),
            )
            target = write_lock(
                root,
                "target.txt",
                lock_entry("demo", marker=marker, hashes=(HASH_A, HASH_B)),
            )

            self.assertEqual(parse_lock(source)["demo"].marker, marker)
            check_pair(source, target)

    def test_unsupported_or_ambiguous_syntax_fails_closed(self) -> None:
        malformed = {
            "dangling continuation": (
                f"demo==1.0 \\\n    --hash=sha256:{HASH_A} \\\n",
                "continuation",
            ),
            "comment in hash chain": (
                f"demo==1.0 \\\n    --hash=sha256:{HASH_A} \\\n    # via injected\n"
                f"    --hash=sha256:{HASH_B}\n",
                "comment",
            ),
            "missing hash": ("demo==1.0\n", "hash"),
            "malformed hash": (
                "demo==1.0 \\\n    --hash=sha256:not-a-digest\n",
                "sha-256",
            ),
            "duplicate hash": (
                f"demo==1.0 \\\n    --hash=sha256:{HASH_A} \\\n"
                f"    --hash=sha256:{HASH_A}\n",
                "duplicate",
            ),
            "non-exact specifier": (
                f"demo>=1.0 \\\n    --hash=sha256:{HASH_A}\n",
                "exact",
            ),
            "url": ("demo @ https://example.invalid/demo.whl\n", "unsupported"),
            "include": ("-r other.txt\n", "unsupported"),
            "option": ("--index-url https://example.invalid/simple\n", "unsupported"),
            "editable": ("-e git+https://example.invalid/demo.git\n", "unsupported"),
            "inline comment": (
                f"demo==1.0 # not allowed \\\n    --hash=sha256:{HASH_A}\n",
                "inline comment",
            ),
            "unexpected indent": (
                f"    demo==1.0 \\\n        --hash=sha256:{HASH_A}\n",
                "indented",
            ),
            "unexpected post-hash content": (
                lock_entry("demo") + "    --trusted-host example.invalid\n",
                "indented",
            ),
        }
        for name, (content, hint) in malformed.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                path = write_lock(pathlib.Path(td), "bad.lock", content)
                with self.assertRaises(LockError) as raised:
                    parse_lock(path)
                self.assertIn(hint, str(raised.exception).lower())


class RepositoryContractTests(unittest.TestCase):
    def test_contract_contains_exactly_four_primary_runtime_pairs(self) -> None:
        self.assertEqual(
            LOCK_PAIRS,
            (
                ("backend/requirements.txt", "requirements/ci-py311.txt"),
                ("scripts/requirements.txt", "requirements/ci-py311.txt"),
                ("scripts/requirements.txt", "requirements/automation.txt"),
                ("backtest/requirements.txt", "requirements/automation.txt"),
            ),
        )

    def test_repository_checks_every_pair_and_reports_the_drifting_pair(self) -> None:
        mutations = (
            (
                "backend/requirements.txt",
                "requirements/ci-py311.txt",
                "backend-only",
                lock_entry("scripts_only"),
            ),
            (
                "scripts/requirements.txt",
                "requirements/ci-py311.txt",
                "scripts-only",
                lock_entry("backend-only"),
            ),
            (
                "scripts/requirements.txt",
                "requirements/automation.txt",
                "scripts-only",
                lock_entry("backtest.only"),
            ),
            (
                "backtest/requirements.txt",
                "requirements/automation.txt",
                "backtest-only",
                lock_entry("scripts_only"),
            ),
        )
        for source, target, package, replacement in mutations:
            with self.subTest(source=source, target=target), tempfile.TemporaryDirectory() as td:
                root = pathlib.Path(td)
                populate_repository(root)
                write_lock(root, target, replacement)
                with self.assertRaises(LockError) as raised:
                    check_repository(root)
                message = str(raised.exception)
                for detail in (source, target, package):
                    self.assertIn(detail, message)

    def test_repository_and_cli_success_report_exactly_four_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            populate_repository(root)
            self.assertEqual(check_repository(root), 4)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout),
                contextlib.redirect_stderr(stderr),
            ):
                rc = main(["--root", str(root)])

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "lock consistency OK: 4 subset pairs\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_contract_failure_exits_one_and_argparse_error_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            populate_repository(root)
            write_lock(root, "requirements/ci-py311.txt", lock_entry("backend-only"))
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = main(["--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("scripts/requirements.txt", stderr.getvalue())

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--not-a-real-option"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
