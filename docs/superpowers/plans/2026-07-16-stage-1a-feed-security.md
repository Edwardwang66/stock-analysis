# Stage 1A Feed Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the known feed-ingress and Dependabot fail-open paths, and replace every broad `git add feed/` with a temporary, exact publication allowlist.

**Architecture:** External feed payloads are parsed as strict JSON and validated in memory before any path is derived or file is written. A small transitional publication module records exact durable feed writes and proven tracked deletions, while explicitly excluding repository-dispatch's temporary inbox file; this is a Stage 1A Git-staging control, not the Stage 3 atomic artifact manifest or final publisher. Dependabot merge eligibility is stamped from `dependabot/fetch-metadata` into a dedicated label, then a tested Python gate re-reads current PR merge state and requires a non-empty set of successful required checks before enabling native auto-merge.

**Tech Stack:** Python 3.11/3.12 standard library, existing `jsonschema` validation, GitHub Actions YAML, GitHub CLI (`gh`), `unittest`-style executable test scripts.

## Global Constraints

- Treat every file arriving through `feed/inbox/` and every `repository_dispatch` report as external input, regardless of the payload's self-declared `kind`.
- External input requires a configured, non-empty `FEED_HMAC_SECRET` and a valid HMAC-SHA256 signature. Missing configuration and invalid signatures both fail closed.
- Report IDs must match `^[A-Za-z0-9._:-]{6,80}$`; invalid IDs are rejected, never sanitized or rewritten.
- Resolve every ID-derived destination and prove its parent is the approved inbox or reports directory before writing.
- Dispatch writes use exclusive creation and must not replace an existing inbox file.
- Python's non-standard JSON constants `NaN`, `Infinity`, and `-Infinity` are invalid at every feed/manifest ingress; signing and writing non-finite floats also fail before a file is created.
- A requested validation glob that matches no regular files exits non-zero; an empty input set is never a successful validation.
- Repository-dispatch's exclusively created `feed/inbox/*.json` is temporary validation input and is never recorded as a publication. A removed inbox path is recorded only when `git ls-files --error-unmatch` proves that exact canonical path was tracked before deletion.
- At Stage 1A completion, no workflow may stage the `feed` root or a wildcard feed pathspec, including `feed`, `feed/`, `./feed/`, `feed/*`, continuations, or `git -C . add` variants. Stage 1A stages only exact paths recorded in the temporary publication allowlist; Task 3's temporary broad commands are removed in Task 5 before the final gate.
- The Stage 1A publication allowlist controls Git staging only. It does not add reader manifests, atomic artifact replacement, previous-manifest fallback, data-branch transport, or the final Stage 3 publisher.
- Dependabot sees zero required checks, missing fields, pending checks, neutral checks, skipped checks, cancelled checks, failed checks, stale/unknown eligibility, or any current PR state other than `mergeable=MERGEABLE` plus `mergeStateStatus=CLEAN` as not mergeable.
- Only the on-PR job may derive Dependabot eligibility, and only from successful `dependabot/fetch-metadata` outputs. The scheduled sweep processes Dependabot PRs carrying the exact `dependencies:auto-merge-eligible` label; unlabeled legacy or unknown PRs fail closed.
- Dependabot uses `gh pr merge --auto --merge --match-head-commit`; direct merge fallback and `--admin` are forbidden.
- Preserve the user's untracked `AGENTS.md`; every `git add` command below names only files owned by its task.
- Use only standard-library dependencies for the new security tests and helper modules.

---

### Task 1: Add strict JSON, report-ID, path, exclusive-write, and HMAC primitives

**Files:**
- Create: `scripts/tests/test_feed_validation_security.py`
- Modify: `scripts/feed_lib.py:13-20, 41-45, 74-100`
- Modify: `scripts/validate_feed.py:31-71`

**Interfaces:**
- Produces: `feed_lib.reject_json_constant(value: str) -> NoReturn`
- Produces: `feed_lib.require_report_id(value: object) -> str`
- Produces: `feed_lib.artifact_json_path(root: str | os.PathLike[str], artifact_id: object) -> str`
- Produces: `feed_lib.inbox_path(report_id: object, inbox_dir: str | os.PathLike[str] | None = None) -> str`
- Produces: `feed_lib.json_file_bytes(obj: object) -> bytes`
- Produces: `feed_lib.save_json_exclusive(path: str | os.PathLike[str], obj: object, *, encoded: bytes | None = None, record_publication: bool = True) -> None`
- Changes: `feed_lib.load_json`, `canonical_json`, `save_json`, `json_file_bytes`, and `save_json_exclusive` reject non-standard/non-finite JSON values; serialization uses `allow_nan=False`.
- Produces: `validate_feed.check_report(report: dict, *, require_sig: bool, secret: str | None, size_bytes: int | None = None) -> tuple[bool, list[str]]`
- Preserves: `validate_feed.check_one(path, require_sig, secret) -> tuple[bool, list[str], dict | None]`
- Preserves: `feed_lib.report_path(report_id) -> str`, but changes invalid-ID behavior from sanitization to `ValueError`.

- [ ] **Step 1: Write the failing strict-JSON and validation-security tests**

Create `scripts/tests/test_feed_validation_security.py` with this complete content:

```python
"""Security regression tests for feed ID, path, write, and HMAC rules."""
from __future__ import annotations

import json
import math
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import feed_lib as fl  # noqa: E402
from validate_feed import check_one, check_report  # noqa: E402


SECRET = "stage-1a-test-secret"


def mk_report(**overrides: object) -> dict:
    report = {
        "schema_version": "1.0",
        "id": "openclaw-stage1a-security-test",
        "kind": "openclaw",
        "produced_at": "2026-07-16T00:00:00Z",
        "asof_data": "2026-07-16",
        "producer": {"name": "security-test"},
    }
    report.update(overrides)
    return report


class FeedValidationSecurityTests(unittest.TestCase):
    def test_report_id_rejects_traversal_instead_of_sanitizing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = pathlib.Path(td) / "feed" / "inbox"
            inbox.mkdir(parents=True)
            victim = inbox.parent / "index.json"
            victim.write_text('{"sentinel":true}\n', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "report id"):
                fl.artifact_json_path(inbox, "../index")

            self.assertEqual(victim.read_text(encoding="utf-8"), '{"sentinel":true}\n')
            self.assertEqual(list(inbox.iterdir()), [])

    def test_exclusive_write_does_not_replace_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "inbox" / "openclaw-safe-id.json"
            fl.save_json_exclusive(target, {"first": True})

            with self.assertRaises(FileExistsError):
                fl.save_json_exclusive(target, {"second": True})

            self.assertEqual(
                json.loads(
                    target.read_text(encoding="utf-8"),
                    parse_constant=fl.reject_json_constant,
                ),
                {"first": True},
            )

    def test_default_inbox_root_cannot_be_a_symlink_outside_feed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            feed = root / "feed"
            outside = root / "outside"
            feed.mkdir()
            outside.mkdir()
            (feed / "inbox").symlink_to(outside, target_is_directory=True)

            with mock.patch.object(fl, "FEED", str(feed)):
                with self.assertRaisesRegex(ValueError, "escaped feed"):
                    fl.inbox_path("openclaw-safe-id")

    def test_openclaw_fails_closed_when_secret_is_missing(self) -> None:
        with mock.patch.object(fl, "has_report", return_value=False):
            passed, errors = check_report(
                mk_report(),
                require_sig=False,
                secret=None,
            )

        self.assertFalse(passed)
        self.assertTrue(any("FEED_HMAC_SECRET" in error for error in errors), errors)

    def test_external_manual_kind_cannot_bypass_signature(self) -> None:
        with mock.patch.object(fl, "has_report", return_value=False):
            passed, errors = check_report(
                mk_report(kind="manual", id="manual-stage1a-security-test"),
                require_sig=True,
                secret=SECRET,
            )

        self.assertFalse(passed)
        self.assertTrue(any("HMAC" in error for error in errors), errors)

    def test_valid_signature_still_passes(self) -> None:
        report = fl.sign_report(mk_report(), SECRET)
        with mock.patch.object(fl, "has_report", return_value=False):
            passed, errors = check_report(
                report,
                require_sig=True,
                secret=SECRET,
            )

        self.assertTrue(passed, errors)

    def test_malformed_nested_types_return_errors_instead_of_crashing(self) -> None:
        cases = (
            {"book": "not-an-object"},
            {"factory_candidates": 1},
            {"signature": "not-an-object"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), mock.patch.object(
                fl, "has_report", return_value=False
            ):
                report = mk_report(**overrides)
                passed, errors = check_report(
                    report,
                    require_sig=True,
                    secret=SECRET,
                )
                self.assertFalse(passed)
                self.assertTrue(errors)

    def test_file_validation_rejects_nonstandard_json_constants(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant), tempfile.TemporaryDirectory() as td:
                path = pathlib.Path(td) / "report.json"
                path.write_text(
                    '{"schema_version":"1.0","id":"openclaw-json-test",'
                    '"kind":"openclaw","produced_at":"2026-07-16T00:00:00Z",'
                    '"asof_data":"2026-07-16","producer":{"name":"test"},'
                    f'"metric":{constant}}}',
                    encoding="utf-8",
                )

                passed, errors, report = check_one(path, True, SECRET)

                self.assertFalse(passed)
                self.assertIsNone(report)
                self.assertTrue(any("JSON" in error for error in errors), errors)

    def test_signing_and_writing_reject_non_finite_numbers_before_creation(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as td:
                target = pathlib.Path(td) / "feed" / "bad.json"
                report = mk_report(metric=value)

                with self.assertRaises(ValueError):
                    fl.sign_report(dict(report), SECRET)
                with self.assertRaises(ValueError):
                    fl.json_file_bytes(report)
                with self.assertRaises(ValueError):
                    fl.save_json(str(target), report)
                with self.assertRaises(ValueError):
                    fl.save_json_exclusive(target, report)
                with self.assertRaises(ValueError):
                    fl.save_json_exclusive(target, report, encoded=b"{}\n")

                self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the new test to verify it fails for missing interfaces**

Run:

```bash
python3 scripts/tests/test_feed_validation_security.py
```

Expected: exit code 1 with an import error for `check_report` or an attribute error for `artifact_json_path`; the current production code does not expose these strict interfaces.

- [ ] **Step 3: Add strict ID and exclusive-write helpers to `feed_lib.py`**

Add `re`, `NoReturn`, and `Path` imports, put the strict JSON/ID helpers beside the existing path constants, and replace `load_json`, `save_json`, `canonical_json`, the current sanitizing `report_path`, and the new serialization helpers with the versions shown here. Serialize before opening a destination so a non-finite value cannot leave a partial file.

```python
import re
from pathlib import Path
from typing import NoReturn


REPORT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{6,80}$")


def reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant is forbidden: {value}")


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, parse_constant=reject_json_constant)


def json_file_bytes(obj: object) -> bytes:
    text = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
        allow_nan=False,
    ) + "\n"
    return text.encode("utf-8")


def save_json(path: str, obj: object) -> None:
    payload = json_file_bytes(obj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)


def canonical_json(obj: object) -> str:
    """用于签名的确定性严格 JSON 序列化。"""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def require_report_id(value: object) -> str:
    if not isinstance(value, str) or REPORT_ID_RE.fullmatch(value) is None:
        raise ValueError("report id must match ^[A-Za-z0-9._:-]{6,80}$")
    return value


def artifact_json_path(root: str | os.PathLike[str], artifact_id: object) -> str:
    report_id = require_report_id(artifact_id)
    approved_root = Path(root).resolve()
    destination = (approved_root / f"{report_id}.json").resolve()
    if destination.parent != approved_root:
        raise ValueError("resolved artifact path escaped its approved root")
    return str(destination)


def _feed_child_root(name: str) -> Path:
    feed_root = Path(FEED).resolve()
    child_root = (feed_root / name).resolve()
    if child_root.parent != feed_root:
        raise ValueError(f"resolved feed/{name} root escaped feed")
    return child_root


def inbox_path(
    report_id: object,
    inbox_dir: str | os.PathLike[str] | None = None,
) -> str:
    root = Path(inbox_dir) if inbox_dir is not None else _feed_child_root("inbox")
    return artifact_json_path(root, report_id)


def save_json_exclusive(
    path: str | os.PathLike[str],
    obj: object,
    *,
    encoded: bytes | None = None,
    record_publication: bool = True,
) -> None:
    # Task 5 wires record_publication to the transitional publication recorder.
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json_file_bytes(obj)
    if encoded is not None and encoded != serialized:
        raise ValueError("encoded JSON does not match the strict serialization of obj")
    payload = serialized if encoded is None else encoded
    with destination.open("xb") as handle:
        handle.write(payload)


def report_path(report_id: str) -> str:
    return artifact_json_path(_feed_child_root("reports"), report_id)
```

In the `ImportError` fallback inside `validate_report`, add strict ID validation before returning:

```python
        try:
            require_report_id(report.get("id"))
        except ValueError as exc:
            errs.append(str(exc))
```

Also make `verify_signature` total over untrusted JSON values before it accesses signature fields:

```python
    sig = report.get("signature")
    if not isinstance(sig, dict) or sig.get("alg") != "HMAC-SHA256":
        return False
```

- [ ] **Step 4: Refactor payload validation into `check_report` and make HMAC failure closed**

In `scripts/validate_feed.py`, add the following function and replace `check_one` with this complete implementation:

```python
def check_report(
    report: dict,
    *,
    require_sig: bool,
    secret: str | None,
    size_bytes: int | None = None,
) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if size_bytes is not None and size_bytes > MAX_BYTES:
        return False, [f"文件过大 >{MAX_BYTES} 字节"]

    _, schema_errs = fl.validate_report(report)
    errs.extend(schema_errs)

    if report.get("kind") == "routine":
        errs.append("外部投递不得使用 kind=routine(冒充本仓任务);应为 openclaw 或 manual。")

    book = report.get("book")
    if book is None:
        positions: object = []
    elif not isinstance(book, dict):
        positions = []
        errs.append("book 必须是 JSON object。")
    else:
        positions = book.get("positions", []) or []
    if not isinstance(positions, list):
        errs.append("book.positions 必须是 JSON array。")
    elif len(positions) > MAX_POSITIONS:
        errs.append(f"positions 过多 ({len(positions)}>{MAX_POSITIONS})")

    candidates = report.get("factory_candidates", []) or []
    if not isinstance(candidates, list):
        errs.append("factory_candidates 必须是 JSON array。")
    elif len(candidates) > MAX_CANDIDATES:
        errs.append(f"factory_candidates 过多 (>{MAX_CANDIDATES})")

    must_verify = require_sig or report.get("kind") == "openclaw"
    if must_verify:
        if not secret:
            errs.append("FEED_HMAC_SECRET 未配置，拒绝需要签名的外部投递。")
        elif not fl.verify_signature(report, secret):
            errs.append("HMAC 签名缺失或无效。")

    report_id: str | None
    try:
        report_id = fl.require_report_id(report.get("id"))
    except ValueError:
        report_id = None
    if report_id is not None and fl.has_report(report_id):
        errs.append(f"幂等冲突:报告 id={report_id} 已存在于 feed/reports/(重复投递)。")

    return len(errs) == 0, errs


def check_one(
    path: str,
    require_sig: bool,
    secret: str | None,
) -> tuple[bool, list[str], dict | None]:
    size_bytes = os.path.getsize(path)
    if size_bytes > MAX_BYTES:
        return False, [f"文件过大 >{MAX_BYTES} 字节"], None
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle, parse_constant=fl.reject_json_constant)
    except Exception as exc:  # noqa: BLE001
        return False, [f"JSON 解析失败: {exc}"], None
    if not isinstance(report, dict):
        return False, ["报告顶层必须是 JSON object。"], None

    passed, errs = check_report(
        report,
        require_sig=require_sig,
        secret=secret,
        size_bytes=size_bytes,
    )
    return passed, errs, report if passed else None
```

- [ ] **Step 5: Run the focused and existing feed tests**

Run:

```bash
python3 scripts/tests/test_feed_validation_security.py
```

Expected: `Ran 9 tests` and `OK`; the non-finite signing/writing test leaves no target file behind.

Run:

```bash
python3 scripts/tests/test_validate_feed.py
```

Expected: all existing 13 assertions print as passed and the process exits 0.

- [ ] **Step 6: Commit the validated primitives**

```bash
git add scripts/feed_lib.py scripts/validate_feed.py scripts/tests/test_feed_validation_security.py
git diff --cached --check
git commit -m "fix(feed): fail closed on invalid ids and signatures"
```

Expected: one commit containing only the three named files.

---

### Task 2: Add a validate-before-write dispatch ingress

**Files:**
- Create: `scripts/feed_ingress.py`
- Create: `scripts/tests/test_feed_ingress.py`

**Interfaces:**
- Consumes: `validate_feed.check_report(...)` from Task 1.
- Consumes: `feed_lib.inbox_path(...)` and `feed_lib.save_json_exclusive(...)` from Task 1.
- Ingress contract: dispatch payload parsing rejects `NaN`, `Infinity`, and `-Infinity`, and the temporary inbox creation passes `record_publication=False`.
- Produces: `feed_ingress.SubmissionRejected(errors: list[str])`
- Produces: `feed_ingress.receive_dispatch(report: dict, *, secret: str | None, inbox_dir: str | os.PathLike[str] | None = None) -> str`
- Produces CLI: `python scripts/feed_ingress.py --path-output <file>`, reading `PAYLOAD` and `FEED_HMAC_SECRET` from the environment.

- [ ] **Step 1: Write strict-JSON, traversal, and overwrite regression tests**

Create `scripts/tests/test_feed_ingress.py`:

```python
"""Repository-dispatch ingress regression tests."""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import feed_lib as fl  # noqa: E402
import validate_feed  # noqa: E402
from feed_ingress import SubmissionRejected, main as ingress_main, receive_dispatch  # noqa: E402


SECRET = "stage-1a-ingress-secret"


def mk_report(**overrides: object) -> dict:
    report = {
        "schema_version": "1.0",
        "id": "openclaw-stage1a-ingress-test",
        "kind": "openclaw",
        "produced_at": "2026-07-16T00:00:00Z",
        "asof_data": "2026-07-16",
        "producer": {"name": "ingress-test"},
    }
    report.update(overrides)
    return report


class FeedIngressTests(unittest.TestCase):
    def test_traversal_cannot_overwrite_feed_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            feed = pathlib.Path(td) / "feed"
            inbox = feed / "inbox"
            inbox.mkdir(parents=True)
            victim = feed / "index.json"
            victim.write_text('{"sentinel":true}\n', encoding="utf-8")
            report = fl.sign_report(mk_report(id="../index"), SECRET)

            with mock.patch.object(fl, "has_report", return_value=False):
                with self.assertRaises(SubmissionRejected):
                    receive_dispatch(report, secret=SECRET, inbox_dir=inbox)

            self.assertEqual(victim.read_text(encoding="utf-8"), '{"sentinel":true}\n')
            self.assertEqual(list(inbox.iterdir()), [])

    def test_missing_secret_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = pathlib.Path(td) / "feed" / "inbox"
            inbox.mkdir(parents=True)

            with mock.patch.object(fl, "has_report", return_value=False):
                with self.assertRaisesRegex(SubmissionRejected, "FEED_HMAC_SECRET"):
                    receive_dispatch(mk_report(), secret=None, inbox_dir=inbox)

            self.assertEqual(list(inbox.iterdir()), [])

    def test_existing_inbox_file_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = pathlib.Path(td) / "feed" / "inbox"
            inbox.mkdir(parents=True)
            target = inbox / "openclaw-stage1a-ingress-test.json"
            target.write_text("sentinel\n", encoding="utf-8")
            report = fl.sign_report(mk_report(), SECRET)

            with mock.patch.object(fl, "has_report", return_value=False):
                with self.assertRaises(FileExistsError):
                    receive_dispatch(report, secret=SECRET, inbox_dir=inbox)

            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel\n")

    def test_valid_signed_report_is_created_inside_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = pathlib.Path(td) / "feed" / "inbox"
            report = fl.sign_report(mk_report(), SECRET)

            with mock.patch.object(fl, "has_report", return_value=False):
                path = receive_dispatch(report, secret=SECRET, inbox_dir=inbox)

            self.assertEqual(pathlib.Path(path).parent, inbox.resolve())
            self.assertTrue(pathlib.Path(path).is_file())

    def test_size_limit_uses_exact_bytes_that_would_be_written(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = pathlib.Path(td) / "feed" / "inbox"
            report = fl.sign_report(mk_report(), SECRET)
            compact_size = len(fl.canonical_json(report).encode("utf-8"))
            encoded_size = len(fl.json_file_bytes(report))
            self.assertGreater(encoded_size, compact_size)

            with mock.patch.object(fl, "has_report", return_value=False), mock.patch.object(
                validate_feed, "MAX_BYTES", compact_size
            ):
                with self.assertRaisesRegex(SubmissionRejected, "文件过大"):
                    receive_dispatch(report, secret=SECRET, inbox_dir=inbox)

            self.assertFalse(inbox.exists())

    def test_cli_rejects_nonstandard_json_constants(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant), tempfile.TemporaryDirectory() as td:
                output = pathlib.Path(td) / "dispatch-path.txt"
                stderr = io.StringIO()
                with mock.patch.dict(
                    os.environ,
                    {"PAYLOAD": f'{{"metric":{constant}}}', "FEED_HMAC_SECRET": SECRET},
                    clear=False,
                ), contextlib.redirect_stderr(stderr):
                    rc = ingress_main(["--path-output", str(output)])

                self.assertEqual(rc, 1)
                self.assertIn("PAYLOAD JSON 解析失败", stderr.getvalue())
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the ingress test to verify it fails before the module exists**

Run:

```bash
python3 scripts/tests/test_feed_ingress.py
```

Expected: exit code 1 with `ModuleNotFoundError: No module named 'feed_ingress'`.

- [ ] **Step 3: Implement the dedicated ingress module**

Create `scripts/feed_ingress.py`:

```python
#!/usr/bin/env python3
"""Validate a repository_dispatch report before creating an inbox file."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import feed_lib as fl
from validate_feed import check_report


class SubmissionRejected(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def receive_dispatch(
    report: dict,
    *,
    secret: str | None,
    inbox_dir: str | os.PathLike[str] | None = None,
) -> str:
    if not isinstance(report, dict):
        raise SubmissionRejected(["报告顶层必须是 JSON object。"])
    encoded = fl.json_file_bytes(report)
    passed, errors = check_report(
        report,
        require_sig=True,
        secret=secret,
        size_bytes=len(encoded),
    )
    if not passed:
        raise SubmissionRejected(errors)

    destination = fl.inbox_path(report.get("id"), inbox_dir=inbox_dir)
    fl.save_json_exclusive(
        destination,
        report,
        encoded=encoded,
        record_publication=False,
    )
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path-output", required=True)
    args = parser.parse_args(argv)

    raw_payload = os.environ.get("PAYLOAD")
    if raw_payload is None:
        print("PAYLOAD 未配置，拒绝 dispatch。", file=sys.stderr)
        return 2
    try:
        report = json.loads(raw_payload, parse_constant=fl.reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"PAYLOAD JSON 解析失败: {exc}", file=sys.stderr)
        return 1

    try:
        destination = receive_dispatch(
            report,
            secret=os.environ.get("FEED_HMAC_SECRET"),
        )
    except (SubmissionRejected, FileExistsError, ValueError) as exc:
        print(f"dispatch 投递拒绝: {exc}", file=sys.stderr)
        return 1

    output = Path(args.path_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(destination + "\n", encoding="utf-8")
    print(f"收到并暂存投递: {Path(destination).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the ingress tests and byte-compile the new module**

Run:

```bash
python3 scripts/tests/test_feed_ingress.py
```

Expected: `Ran 6 tests` and `OK`; each non-standard JSON constant is rejected during payload parsing, before validation or inbox creation.

Run:

```bash
python3 -m py_compile scripts/feed_ingress.py
```

Expected: no output and exit code 0.

- [ ] **Step 5: Commit the ingress module**

```bash
git add scripts/feed_ingress.py scripts/tests/test_feed_ingress.py
git diff --cached --check
git commit -m "fix(feed): validate dispatch before writing inbox"
```

Expected: one commit containing the ingress implementation and its regression tests.

---

### Task 3: Make zero-match validation fail and wire every external entry point through strict validation

**Files:**
- Create: `scripts/tests/test_validate_feed_cli.py`
- Modify: `scripts/validate_feed.py:74-109`
- Modify: `.github/workflows/feed-validate.yml:37-97`
- Modify: `.github/workflows/tests.yml:5-10, 36-39`

**Interfaces:**
- Consumes: `feed_ingress.py --path-output` from Task 2.
- Changes: `validate_feed._expand(paths: list[str]) -> tuple[list[str], list[str]]` returns regular files and every requested literal/glob with no regular-file match.
- Changes: `validate_feed.main(argv: list[str] | None = None) -> int` returns 0 on success, 1 on invalid input, and 2 when any requested input is missing or unmatched.
- Workflow contract: PR, push, and repository dispatch all pass `--require-signature`.

- [ ] **Step 1: Add CLI and workflow regression tests**

Create `scripts/tests/test_validate_feed_cli.py`:

```python
"""CLI and workflow regression tests for strict feed validation."""
from __future__ import annotations

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_feed import main as validate_main  # noqa: E402


class ValidateFeedCliTests(unittest.TestCase):
    def test_unmatched_glob_returns_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pattern = str(pathlib.Path(td) / "inbox" / "*.json")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = validate_main([pattern])

        self.assertEqual(rc, 2)
        self.assertIn("没有匹配到投递文件", stderr.getvalue())

    def test_one_valid_file_does_not_hide_an_unmatched_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            valid = root / "valid.json"
            valid.write_text("{}\n", encoding="utf-8")
            missing_glob = str(root / "missing" / "*.json")
            missing_literal = str(root / "missing.json")
            for missing in (missing_glob, missing_literal):
                with self.subTest(missing=missing):
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        rc = validate_main([str(valid), missing])
                    self.assertEqual(rc, 2)
                    self.assertIn(missing, stderr.getvalue())

    def test_workflow_requires_signatures_on_all_external_paths(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "feed-validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(workflow.count("--require-signature"), 3)
        self.assertNotIn("inbox 为空,通过", workflow)
        self.assertIn("python scripts/feed_ingress.py --path-output", workflow)
        self.assertNotIn('fl.save_json(os.path.join(fl.FEED, "inbox"', workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("path: trusted", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn("path: submission", workflow)
        self.assertGreaterEqual(workflow.count("persist-credentials: false"), 2)
        self.assertIn('PYTHONPATH="$GITHUB_WORKSPACE/trusted/scripts"', workflow)
        self.assertNotIn("github.event_name == 'pull_request'", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the tests to verify current zero-match and workflow behavior fail**

Run:

```bash
python3 scripts/tests/test_validate_feed_cli.py
```

Expected: exit code 1. The zero-match assertion receives `None` instead of 2, and the workflow assertions find no strict ingress command.

- [ ] **Step 3: Give `_expand` and `validate_feed.main` explicit per-input exit semantics**

Replace `_expand`, `main`, and the module entry point in `scripts/validate_feed.py` with:

```python
def _expand(paths: list[str]) -> tuple[list[str], list[str]]:
    files: list[str] = []
    missing: list[str] = []
    for requested in paths:
        candidates = (
            sorted(glob.glob(requested))
            if any(char in requested for char in "*?[")
            else [requested]
        )
        matches = [candidate for candidate in candidates if os.path.isfile(candidate)]
        if not matches:
            missing.append(requested)
        files.extend(matches)
    return list(dict.fromkeys(files)), missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="校验通过则并入 feed/reports/ 并重建 index",
    )
    parser.add_argument("--require-signature", action="store_true")
    args = parser.parse_args(argv)
    secret = os.environ.get("FEED_HMAC_SECRET")

    files, missing = _expand(args.paths)
    if missing:
        for requested in missing:
            print(f"没有匹配到投递文件: {requested}", file=sys.stderr)
        return 2
    if not files:
        print("没有可校验的普通文件，拒绝空校验。", file=sys.stderr)
        return 2

    all_ok = True
    merged = 0
    for path in files:
        passed, errors, report = check_one(path, args.require_signature, secret)
        tag = "✓" if passed else "✗"
        print(f"{tag} {path}")
        for error in errors:
            print(f"    - {error}")
        if passed and args.merge and report is not None:
            fl.write_report_files(report)
            os.remove(path)
            merged += 1
        all_ok = all_ok and passed

    if args.merge and merged:
        index = fl.rebuild_index()
        print(f"已并入 {merged} 份投递,feed 现有 {index['stats']['total_reports']} 份报告。")
    if not all_ok:
        print("\n校验失败:存在无效投递。", file=sys.stderr)
        return 1
    print("\n全部投递校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Isolate PR data from trusted validation code and keep publication fail-closed**

Replace `.github/workflows/feed-validate.yml` with the complete workflow below. The `pull_request_target` job runs only the base commit's validator and dependency file, checks out the PR head as inert data in a second directory, has read-only repository permission, and never executes a file from the submission checkout. The publishing job is the only job with write permission. Task 5 later replaces its two temporary broad staging commands.

```yaml
name: Feed validate (OpenClaw 投递校验闸门)

on:
  push:
    branches: [main]
    paths: ["feed/inbox/**"]
  pull_request_target:
    types: [opened, synchronize, reopened]
    paths: ["feed/inbox/**"]
  repository_dispatch:
    types: [openclaw-report]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: feed-validate-${{ github.event_name }}
  cancel-in-progress: false

jobs:
  pr-validate:
    if: github.event_name == 'pull_request_target'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout trusted base validator
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          path: trusted
          persist-credentials: false
      - name: Checkout untrusted submission as data only
        uses: actions/checkout@v7
        with:
          repository: ${{ github.event.pull_request.head.repo.full_name }}
          ref: ${{ github.event.pull_request.head.sha }}
          path: submission
          persist-credentials: false
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Install trusted validator dependencies
        run: python -m pip install -r trusted/scripts/requirements.txt
      - name: Validate signed PR inbox files with trusted code
        env:
          FEED_HMAC_SECRET: ${{ secrets.FEED_HMAC_SECRET }}
        run: |
          mapfile -d '' files < <(find "$GITHUB_WORKSPACE/submission/feed/inbox" -maxdepth 1 -type f -name '*.json' -print0)
          if (( ${#files[@]} == 0 )); then
            echo "PR 没有可校验的 feed/inbox JSON 普通文件。" >&2
            exit 1
          fi
          PYTHONPATH="$GITHUB_WORKSPACE/trusted/scripts" \
            python "$GITHUB_WORKSPACE/trusted/scripts/validate_feed.py" \
              --require-signature "${files[@]}"

  publish:
    if: github.event_name == 'push' || github.event_name == 'repository_dispatch'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: python -m pip install -r scripts/requirements.txt
      - name: Merge signed push submission
        if: github.event_name == 'push'
        env:
          FEED_HMAC_SECRET: ${{ secrets.FEED_HMAC_SECRET }}
        run: |
          shopt -s nullglob
          files=(feed/inbox/*.json)
          if (( ${#files[@]} == 0 )); then
            echo "feed/inbox/*.json 没有匹配文件，拒绝空合并。" >&2
            exit 1
          fi
          python scripts/validate_feed.py --merge --require-signature "${files[@]}"
          git config user.name "feed-validate[bot]"
          git config user.email "actions@github.com"
          git add feed/
          if ! git diff --cached --quiet; then
            git commit -m "openclaw: 并入 push 投递 ($(date -u +%Y-%m-%dT%H:%MZ))"
            pushed=0
            for i in 1 2 3 4; do
              if git pull --rebase origin main && git push; then pushed=1; break; fi
              if [ "$i" -lt 4 ]; then sleep $((2**i)); fi
            done
            if [ "$pushed" -ne 1 ]; then echo "push 重试耗尽。" >&2; exit 1; fi
          fi
      - name: Receive and merge signed dispatch submission
        if: github.event_name == 'repository_dispatch'
        env:
          FEED_HMAC_SECRET: ${{ secrets.FEED_HMAC_SECRET }}
          PAYLOAD: ${{ toJson(github.event.client_payload.report) }}
        run: |
          dispatch_path_file="$RUNNER_TEMP/dispatch-path.txt"
          python scripts/feed_ingress.py --path-output "$dispatch_path_file"
          dispatch_path="$(<"$dispatch_path_file")"
          python scripts/validate_feed.py --merge --require-signature "$dispatch_path"
          git config user.name "feed-validate[bot]"
          git config user.email "actions@github.com"
          git add feed/
          if ! git diff --cached --quiet; then
            git commit -m "openclaw: 并入投递 ($(date -u +%Y-%m-%dT%H:%MZ))"
            pushed=0
            for i in 1 2 3 4; do
              if git pull --rebase origin main && git push; then pushed=1; break; fi
              if [ "$i" -lt 4 ]; then sleep $((2**i)); fi
            done
            if [ "$pushed" -ne 1 ]; then echo "push 重试耗尽。" >&2; exit 1; fi
          fi
```

Fork PR policy is explicit: only a valid signed inbox JSON is supportable. The fork never receives the secret or a write token; unsigned submissions fail closed. If repository policy disables `pull_request_target` for forks, external agents must use the signed `repository_dispatch` path instead. Never replace this design with `pull_request_target` plus execution of PR scripts.

- [ ] **Step 5: Add the new tests and workflow file to the Python CI gate**

Extend both `push.paths` and `pull_request.paths` in `.github/workflows/tests.yml` to:

```yaml
    paths:
      - "backend/**"
      - "scripts/**"
      - ".github/workflows/tests.yml"
      - ".github/workflows/feed-validate.yml"
```

Extend the scripts test step to:

```yaml
      - name: scripts 引擎与安全单测
        run: |
          python scripts/tests/test_chan_engine.py
          python scripts/tests/test_validate_feed.py
          python scripts/tests/test_feed_validation_security.py
          python scripts/tests/test_feed_ingress.py
          python scripts/tests/test_validate_feed_cli.py
```

- [ ] **Step 6: Run the CLI, ingress, and existing feed tests**

```bash
python3 scripts/tests/test_validate_feed_cli.py
python3 scripts/tests/test_feed_ingress.py
python3 scripts/tests/test_feed_validation_security.py
python3 scripts/tests/test_validate_feed.py
```

Expected: every command exits 0; the two unittest files report `OK`, and the legacy feed test reports all 13 assertions passed.

- [ ] **Step 7: Commit strict workflow ingress and empty-input behavior**

```bash
git add scripts/validate_feed.py scripts/tests/test_validate_feed_cli.py .github/workflows/feed-validate.yml .github/workflows/tests.yml
git diff --cached --check
git commit -m "fix(feed): reject empty external validation"
```

Expected: the commit contains only CLI semantics, workflow ingress wiring, and CI coverage. The two temporary `git add feed/` lines remain visible and are removed by Task 5.

---

### Task 4: Build the temporary publication allowlist module

**Files:**
- Create: `scripts/feed_publication.py`
- Create: `scripts/tests/test_feed_publication.py`

**Interfaces:**
- Consumes: `feed_lib.reject_json_constant(...)` from Task 1.
- Produces: `feed_publication.record_written_path(path, *, manifest_path=None, repo_root=None, feed_root=None) -> None`
- Produces: `feed_publication.record_tracked_deletion(path, *, manifest_path=None, repo_root=None, feed_root=None, run=subprocess.run) -> bool`
- Produces: `feed_publication.load_manifest_paths(manifest_path, *, repo_root=None, feed_root=None) -> tuple[str, ...]`
- Produces: `feed_publication.stage_recorded_paths(manifest_path, *, repo_root=None, feed_root=None, run=subprocess.run) -> tuple[str, ...]`
- Produces CLI: `python scripts/feed_publication.py stage <manifest>`.
- Manifest schema: `{"schema_version":"1.0","paths":["feed/..."]}`.

- [ ] **Step 1: Write strict-manifest, containment, deletion, and exact-staging tests**

Create `scripts/tests/test_feed_publication.py`:

```python
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
```

- [ ] **Step 2: Run the publication test to verify the module is absent**

```bash
python3 scripts/tests/test_feed_publication.py
```

Expected: exit code 1 with `ModuleNotFoundError: No module named 'feed_publication'`.

- [ ] **Step 3: Implement normalized containment, atomic allowlist recording, and exact staging**

Create `scripts/feed_publication.py`:

```python
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
```

- [ ] **Step 4: Run the allowlist tests and compile the module**

```bash
python3 scripts/tests/test_feed_publication.py
python3 -m py_compile scripts/feed_publication.py
```

Expected: the test reports `Ran 11 tests` and `OK`; compilation has no output and exits 0. The deletion tests prove that only one exact `git ls-files --error-unmatch` result can enter the manifest.

- [ ] **Step 5: Commit the isolated publication allowlist**

```bash
git add scripts/feed_publication.py scripts/tests/test_feed_publication.py
git diff --cached --check
git commit -m "feat(feed): add exact publication staging allowlist"
```

Expected: the module and its focused tests form one self-contained commit; no workflow uses it yet.

---

### Task 5: Record current feed writes and eliminate every broad feed staging command

**Files:**
- Create: `scripts/tests/test_workflow_security.py`
- Modify: `scripts/feed_lib.py:15-20, 41-45, save_json_exclusive from Task 1`
- Modify: `scripts/validate_feed.py:94-101`
- Modify: `scripts/preipo_history.py:9-16, 48`
- Verify: `scripts/feed_ingress.py` keeps `record_publication=False` for temporary dispatch creation
- Modify: `.github/workflows/feed-validate.yml:27-97`
- Modify: `.github/workflows/alpha-routine.yml:28-79`
- Modify: `.github/workflows/hyperliquid-monitor.yml:21-48`
- Modify: `.github/workflows/monthly-studies.yml:20-55`
- Modify: `.github/workflows/tests.yml:5-10, 36-43`
- Modify: `scripts/tests/test_feed_publication.py`

**Interfaces:**
- Consumes: `feed_publication.record_written_path`, `record_tracked_deletion`, and `stage_recorded_paths` from Task 4.
- Environment contract: feed-producing jobs set `FEED_PUBLICATION_MANIFEST=/tmp/feed-publication-${{ github.run_id }}.json`.
- Write contract: `feed_lib.save_json` records a path only after a successful write; `save_json_exclusive` does the same only when `record_publication=True`. The recorder import is lazy so `feed_publication` can reuse Task 1's strict JSON parser without a module cycle.
- Dispatch contract: `feed_ingress.receive_dispatch` creates its temporary inbox path with `record_publication=False`; the later merge records durable report/index writes but not that untracked inbox deletion.
- Delete contract: after successful removal, `validate_feed` calls `record_tracked_deletion`; only an exact successful `git ls-files --error-unmatch` proof records the missing path for `git add -A`.
- Workflow contract: all five current uses of the standalone `feed/` Git pathspec—including the mixed `git add docs/study-*.md feed/ ...` line—are replaced by `python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"`. Static checks reject root and wildcard variants across inline/block `run`, shell continuations, and `git -C . add`.

- [ ] **Step 1: Add integration and workflow assertions before changing production code**

Append the following three methods to `FeedPublicationTests` in `scripts/tests/test_feed_publication.py`. Add these exact imports to the existing import sections:

```python
import os
import subprocess
from unittest import mock

import feed_lib as fl  # noqa: E402
import feed_ingress  # noqa: E402
import feed_publication as publication  # noqa: E402
import validate_feed  # noqa: E402
```

Then add the test methods:

```python
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
```

Create `scripts/tests/test_workflow_security.py`:

```python
"""Static regression checks for security-sensitive workflows."""
from __future__ import annotations

import pathlib
import re
import shlex
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SHELL_CONTROL = {";", "&&", "||", "|", "&", "(", ")"}


def workflow_run_scripts(text: str) -> list[tuple[int, str]]:
    """Extract inline and block-scalar run scripts without a YAML dependency."""
    lines = text.splitlines()
    scripts: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        match = re.match(
            r"^(?P<indent>\s*)(?:-\s*)?run:\s*(?P<body>.*)$",
            lines[index],
        )
        if match is None:
            index += 1
            continue
        start = index + 1
        body = match.group("body").strip()
        if body in {"|", "|-", "|+", ">", ">-", ">+"}:
            base_indent = len(match.group("indent"))
            block: list[str] = []
            index += 1
            while index < len(lines):
                line = lines[index]
                indentation = len(line) - len(line.lstrip())
                if line.strip() and indentation <= base_indent:
                    break
                block.append(line[base_indent + 1 :])
                index += 1
            script = "\n".join(block)
            if body.startswith(">"):
                script = " ".join(part.strip() for part in block)
            scripts.append((start, script))
            continue
        try:
            unquoted = shlex.split(body)
        except ValueError:
            unquoted = []
        scripts.append((start, unquoted[0] if len(unquoted) == 1 else body))
        index += 1
    return scripts


def git_add_pathspecs(script: str) -> list[str]:
    """Return pathspec-like arguments from git add, including git -C DIR add."""
    logical = re.sub(r"\\\r?\n[ \t]*", " ", script)
    pathspecs: list[str] = []
    for line in logical.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        try:
            tokens = list(lexer)
        except ValueError:
            continue
        for cursor, token in enumerate(tokens):
            if token != "git":
                continue
            command = cursor + 1
            while command < len(tokens) and tokens[command] == "-C":
                command += 2
            if command >= len(tokens) or tokens[command] != "add":
                continue
            argument = command + 1
            while argument < len(tokens) and tokens[argument] not in SHELL_CONTROL:
                pathspecs.append(tokens[argument])
                argument += 1
    return pathspecs


def is_broad_feed_pathspec(pathspec: str) -> bool:
    candidate = pathspec
    if candidate.startswith(":(") and ")" in candidate:
        candidate = candidate.split(")", 1)[1]
    elif candidate.startswith(":/"):
        candidate = candidate[2:]
    while candidate.startswith("./"):
        candidate = candidate[2:]
    while candidate.endswith("/."):
        candidate = candidate[:-2]
    if candidate.rstrip("/") == "feed":
        return True
    return candidate.startswith("feed/") and any(
        wildcard in candidate for wildcard in "*?["
    )


def broad_feed_adds(text: str) -> list[tuple[int, str]]:
    offenders: list[tuple[int, str]] = []
    for line_number, script in workflow_run_scripts(text):
        for pathspec in git_add_pathspecs(script):
            if is_broad_feed_pathspec(pathspec):
                offenders.append((line_number, pathspec))
    return offenders


class WorkflowSecurityTests(unittest.TestCase):
    def test_broad_staging_detector_covers_yaml_shell_and_pathspec_variants(self) -> None:
        dangerous = {
            "inline root": "steps:\n  - run: git add feed\n",
            "block slash": "steps:\n  - run: |\n      git add ./feed/\n",
            "wildcard": "steps:\n  - run: git add feed/*\n",
            "quoted wildcard": "steps:\n  - run: git add 'feed/**'\n",
            "inline quoted": 'steps:\n  - run: "git add feed/**"\n',
            "continuation and chdir": (
                "steps:\n  - run: |\n      git \\\n"
                "        -C . \\\n"
                "        add \\\n"
                "        ./feed/\n"
            ),
        }
        for name, workflow in dangerous.items():
            with self.subTest(name=name):
                self.assertTrue(broad_feed_adds(workflow))

        exact = "steps:\n  - run: git -C . add -A -- feed/index.json feed/reports/id.json\n"
        self.assertEqual(broad_feed_adds(exact), [])

    def test_no_workflow_stages_feed_root_or_wildcard_pathspec(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        offenders = []
        paths = [*workflows.glob("*.yml"), *workflows.glob("*.yaml")]
        for path in paths:
            for number, pathspec in broad_feed_adds(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.name}:{number}:{pathspec}")
        self.assertEqual(offenders, [])

    def test_feed_publishers_use_the_allowlist_stager(self) -> None:
        expected_counts = {
            "feed-validate.yml": 2,
            "alpha-routine.yml": 1,
            "hyperliquid-monitor.yml": 1,
            "monthly-studies.yml": 1,
        }
        for filename, expected_count in expected_counts.items():
            text = (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
            self.assertEqual(
                text.count('python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"'),
                expected_count,
                filename,
            )

    def test_feed_publishers_fail_when_push_retries_are_exhausted(self) -> None:
        for filename in (
            "feed-validate.yml",
            "alpha-routine.yml",
            "hyperliquid-monitor.yml",
            "monthly-studies.yml",
        ):
            text = (ROOT / ".github" / "workflows" / filename).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("git pull --rebase origin main || true", text, filename)
            self.assertIn('if [ "$pushed" -ne 1 ]', text, filename)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run the tests to verify recording and workflow assertions fail**

```bash
python3 scripts/tests/test_feed_publication.py
python3 scripts/tests/test_workflow_security.py
```

Expected: both commands exit 1. `feed_lib` does not yet record durable writes, the dispatch lifecycle cannot produce the exact stage set, and the workflow test reports all five current root pathspecs, including `monthly-studies.yml`. The detector's synthetic inline/block/continuation cases already pass.

- [ ] **Step 3: Instrument successful JSON writes and inbox deletions**

In `scripts/feed_lib.py`, use a lazy recorder import to avoid a `feed_lib`/`feed_publication` import cycle. Call it only after each file handle closes successfully, and honor Task 1's `record_publication` switch:

```python
def _record_written_path(path: str | os.PathLike[str]) -> None:
    from feed_publication import record_written_path

    record_written_path(path)


def save_json(path: str, obj: object) -> None:
    payload = json_file_bytes(obj)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)
    _record_written_path(path)


def save_json_exclusive(
    path: str | os.PathLike[str],
    obj: object,
    *,
    encoded: bytes | None = None,
    record_publication: bool = True,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json_file_bytes(obj)
    if encoded is not None and encoded != serialized:
        raise ValueError("encoded JSON does not match the strict serialization of obj")
    payload = serialized if encoded is None else encoded
    with destination.open("xb") as handle:
        handle.write(payload)
    if record_publication:
        _record_written_path(destination)
```

In `scripts/validate_feed.py`, import the tracked-deletion recorder and invoke it directly after `os.remove(path)`. A push-delivered tracked inbox file is recorded for deletion staging; repository-dispatch's untracked temporary file returns `False` and never enters the manifest:

```python
from feed_publication import record_tracked_deletion  # noqa: E402
```

```python
        if passed and args.merge and report is not None:
            fl.write_report_files(report)
            os.remove(path)
            record_tracked_deletion(path)
            merged += 1
```

- [ ] **Step 4: Make Pre-IPO reads strict and route its write through the recorded feed writer**

In `scripts/preipo_history.py`, add the import, make both existing `json.loads` calls use Task 1's strict constant hook, and replace the raw `Path.write_text` call:

```python
import feed_lib as fl
```

```python
        st = json.loads(
            STATE.read_text(),
            parse_constant=fl.reject_json_constant,
        )
```

```python
        hist = json.loads(
            OUT.read_text(),
            parse_constant=fl.reject_json_constant,
        )
```

```python
    fl.save_json(str(OUT), hist)
    print(f"preipo-history: +1 → {len(hist)} 点({len(marks)} 标的)")
```

This retains the same JSON value while allowing the Hyperliquid workflow to record the exact history path.

- [ ] **Step 5: Configure and use the allowlist in feed validation**

Add this job-level environment to `.github/workflows/feed-validate.yml`:

```yaml
  publish:
    runs-on: ubuntu-latest
    env:
      FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json
```

Replace each of the two exact `git add feed/` lines with:

```yaml
          python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
```

- [ ] **Step 6: Configure and use the allowlist in Alpha routine**

Add this job-level environment to `.github/workflows/alpha-routine.yml`:

```yaml
  run:
    runs-on: ubuntu-latest
    env:
      FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json
```

Replace its broad staging line with:

```yaml
          python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
```

Replace the retry body after its commit with the following fail-closed block:

```yaml
            pushed=0
            for i in 1 2 3 4; do
              if git pull --rebase origin main && git push; then pushed=1; break; fi
              if [ "$i" -lt 4 ]; then sleep $((2**i)); fi
            done
            if [ "$pushed" -ne 1 ]; then echo "push 重试耗尽。" >&2; exit 1; fi
```

The manifest accumulates exact paths across both `run_routine.py` and the optional factor-factory process because both use `feed_lib.save_json`.

- [ ] **Step 7: Configure and use the allowlist in Hyperliquid monitor**

Add this job-level environment to `.github/workflows/hyperliquid-monitor.yml`:

```yaml
  monitor:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json
```

Replace its broad staging line with:

```yaml
          python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
```

Remove `git pull --rebase origin main || true` and replace the retry body after its commit with the same fail-closed block from Step 6.

The manifest now includes the crypto state, generated report/index files, and Pre-IPO history path without staging unrelated feed files.

- [ ] **Step 8: Configure Monthly studies for exact feed staging and fail-closed push**

Add this job-level environment to `.github/workflows/monthly-studies.yml`:

```yaml
  studies:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    env:
      FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json
```

Replace the mixed broad command with two scoped commands:

```yaml
          python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
          git add -- docs/study-*.md backtest/sp600_universe.json
```

Remove `git pull --rebase origin main || true` and replace its retry body with the same fail-closed block from Step 6. The study scripts publish feed JSON through `feed_lib`, so their exact feed files are already present in the publication allowlist; the remaining `git add` names only non-feed research artifacts.

- [ ] **Step 9: Add publication and workflow tests to CI triggers**

Add these entries to both `push.paths` and `pull_request.paths` in `.github/workflows/tests.yml`:

```yaml
      - ".github/workflows/alpha-routine.yml"
      - ".github/workflows/hyperliquid-monitor.yml"
      - ".github/workflows/monthly-studies.yml"
```

Append these commands to the scripts test step:

```yaml
          python scripts/tests/test_feed_publication.py
          python scripts/tests/test_workflow_security.py
```

- [ ] **Step 10: Run exact publication and workflow verification**

```bash
python3 scripts/tests/test_feed_publication.py
python3 scripts/tests/test_workflow_security.py
rg -n -U -P 'git(?:[^\r\n\\]|\\\r?\n[ \t]*){0,160}\badd\b(?:[^\r\n\\]|\\\r?\n[ \t]*){0,400}[ \t]+(?:--[ \t]+)?(?:\./)?feed(?:/?(?=[ \t;&|]|$)|/[^\s;&|]*[*?\[])' .github/workflows
```

Expected: `test_feed_publication.py` reports `Ran 14 tests` and `OK`, `test_workflow_security.py` reports `OK`, and `rg` prints no matches and exits 1. The shared threat set includes inline/block `run`, backslash continuations, `git -C . add`, feed-root variants, and wildcard feed pathspecs while allowing exact file paths.

Run the existing feed tests once more:

```bash
python3 scripts/tests/test_validate_feed.py
python3 scripts/tests/test_feed_ingress.py
```

Expected: both exit 0. No test creates or modifies a canonical repository feed artifact.

- [ ] **Step 11: Commit transitional publication integration**

```bash
git add scripts/feed_lib.py scripts/validate_feed.py scripts/preipo_history.py scripts/tests/test_feed_publication.py scripts/tests/test_workflow_security.py .github/workflows/feed-validate.yml .github/workflows/alpha-routine.yml .github/workflows/hyperliquid-monitor.yml .github/workflows/monthly-studies.yml .github/workflows/tests.yml
git diff --cached --check
git commit -m "fix(feed): stage only recorded publication paths"
```

Expected: the commit removes all broad feed staging. Its manifest remains explicitly transitional and is not exposed to feed readers.

---

### Task 6: Label eligible Dependabot PRs and gate current merge state plus required checks

**Files:**
- Create: `scripts/dependabot_merge_gate.py`
- Create: `scripts/tests/test_dependabot_merge_gate.py`
- Modify: `scripts/tests/test_workflow_security.py`
- Modify: `.github/workflows/dependabot-automerge.yml:1-82`
- Modify: `.github/workflows/tests.yml:5-10, 36-45`

**Interfaces:**
- Produces: `dependabot_merge_gate.MergeDecision` with `ENABLED` and `NOT_READY` values.
- Produces: `required_checks_successful(checks: object) -> bool`.
- Produces: `current_pr_ready(view: object) -> bool` requiring a non-empty `headRefOid`, `mergeable == "MERGEABLE"`, and `mergeStateStatus == "CLEAN"`.
- Produces: `gate_pull_request(*, repo: str, pr_number: int, run=subprocess.run) -> MergeDecision`.
- CLI: `python scripts/dependabot_merge_gate.py --repo <owner/repo> --pr <number>`.
- Eligibility contract: after `dependabot/fetch-metadata`, the on-PR job synchronizes `dependencies:auto-merge-eligible`; npm/pip semver-major PRs are unlabeled, while permitted updates receive the label. Failure to classify or label stops the job.
- Metadata token contract: consume the action outputs exactly as `npm_and_yarn`, `pip`, and `github_actions`. In particular, `npm_and_yarn` and `github_actions` differ from the `.github/dependabot.yml` configuration keys `npm` and `github-actions`; do not normalize or accept the configuration keys as aliases.
- Event contract: the write-capable classifier uses `pull_request_target`, checks `github.event.pull_request.user.login == 'dependabot[bot]'`, and checks out only the explicit base SHA with credentials disabled; no PR-controlled code is executed.
- Sweep contract: list only open PRs authored by `app/dependabot` and carrying the exact eligibility label. Unlabeled legacy/unknown PRs are never inferred from their title.
- GitHub CLI contract: current PR state is queried with `gh pr view --json headRefOid,mergeable,mergeStateStatus`; required checks are then queried with `gh pr checks --required --json name,state,bucket`.
- Merge contract: the only permitted merge command includes `--auto`, `--merge`, and `--match-head-commit <current headRefOid>`; it is unreachable unless current state is exactly `MERGEABLE`/`CLEAN` and the current required-check set is non-empty and entirely successful.

- [ ] **Step 1: Write the required-check and command-construction tests**

Create `scripts/tests/test_dependabot_merge_gate.py`:

```python
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

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
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
        return [command for command in self.commands if command[:3] == ["gh", "pr", "merge"]]

    @property
    def check_commands(self) -> list[list[str]]:
        return [command for command in self.commands if command[:3] == ["gh", "pr", "checks"]]


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
            {"headRefOid": "", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"},
            {"headRefOid": "abc", "mergeable": "UNKNOWN", "mergeStateStatus": "CLEAN"},
            {"headRefOid": "abc", "mergeable": "MERGEABLE", "mergeStateStatus": "BLOCKED"},
            {"headRefOid": "abc", "mergeable": "MERGEABLE", "mergeStateStatus": None},
        ]
        for view in rejected:
            with self.subTest(view=view):
                self.assertFalse(current_pr_ready(view))

    def test_successful_checks_still_fail_closed_when_merge_state_is_blocked(self) -> None:
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
```

- [ ] **Step 2: Run the test to verify the gate module is absent**

```bash
python3 scripts/tests/test_dependabot_merge_gate.py
```

Expected: exit code 1 with `ModuleNotFoundError: No module named 'dependabot_merge_gate'`.

- [ ] **Step 3: Implement the fail-closed gate**

Create `scripts/dependabot_merge_gate.py`:

```python
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
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)) or not checks:
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
        raise RuntimeError(f"current PR query returned invalid JSON for #{pr_number}") from exc
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
        print(
            f"#{pr_number} skipped: required checks are absent, pending, or unavailable"
        )
        return MergeDecision.NOT_READY
    if checks_result.returncode != 0:
        raise RuntimeError(
            f"required-check query failed for PR #{pr_number}: {checks_result.stderr.strip()}"
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
            f"required-check query failed for PR #{pr_number}: {checks_result.stderr.strip()}"
        ) from exc

    if not required_checks_successful(checks):
        print(f"#{pr_number} skipped: required checks are missing, incomplete, or unsuccessful")
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
            f"auto-merge enablement failed for PR #{pr_number}: {merge_result.stderr.strip()}"
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
```

- [ ] **Step 4: Run gate tests and compile the module**

```bash
python3 scripts/tests/test_dependabot_merge_gate.py
python3 -m py_compile scripts/dependabot_merge_gate.py
```

Expected: the test reports `Ran 9 tests` and `OK`; compilation exits 0 with no output. The successful-check/`BLOCKED` regression makes no `gh pr checks` or `gh pr merge` call.

- [ ] **Step 5: Replace the on-PR direct fallback with the tested gate**

Replace the `pull_request` trigger with the write-capable trusted-base event, and update both job guards:

```yaml
on:
  pull_request_target:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: "45 */6 * * *"
  workflow_dispatch:

jobs:
  on-pr:
    if: >-
      github.event_name == 'pull_request_target'
      && github.event.pull_request.user.login == 'dependabot[bot]'
  sweep:
    if: github.event_name != 'pull_request_target'
```

Update the workflow's opening “两层” comment to describe `pull_request_target` metadata classification/labeling and a label-only scheduled sweep; remove any statement that the sweep derives version eligibility from a PR title. Do not check out the Dependabot head under `pull_request_target`; every executable file in this job comes from the base SHA. Add read permission for required-check data plus the issue-label write scope, while preserving the existing write scopes needed to enable auto-merge. Also define the one workflow-wide eligibility label:

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
  checks: read

env:
  AUTOMERGE_ELIGIBLE_LABEL: dependencies:auto-merge-eligible
```

In `.github/workflows/dependabot-automerge.yml`, make the `on-pr` steps exactly:

```yaml
    steps:
      - name: Checkout trusted base gate
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          persist-credentials: false
      - name: 先清除旧 auto-merge 资格标签
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          gh label create "$AUTOMERGE_ELIGIBLE_LABEL" \
            --repo "$REPO" \
            --color "0E8A16" \
            --description "Dependabot update classified by fetch-metadata for guarded auto-merge" \
            --force
          current_labels="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json labels --jq '.labels[].name'
          )"
          if grep -Fxq "$AUTOMERGE_ELIGIBLE_LABEL" <<<"$current_labels"; then
            gh pr edit "$PR_NUMBER" --repo "$REPO" \
              --remove-label "$AUTOMERGE_ELIGIBLE_LABEL"
          fi
      - name: 取 dependabot 元数据
        id: meta
        uses: dependabot/fetch-metadata@v3
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
      - name: 根据 metadata 同步 auto-merge 资格标签
        id: eligibility
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          UPDATE_TYPE: ${{ steps.meta.outputs.update-type }}
          PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}
        run: |
          eligible=false
          if [ -z "$PACKAGE_ECOSYSTEM" ]; then
            echo "fetch-metadata 未返回 package-ecosystem，拒绝分类。" >&2
            exit 1
          fi
          case "$UPDATE_TYPE" in
            version-update:semver-patch|version-update:semver-minor)
              eligible=true
              ;;
            version-update:semver-major)
              if [ "$PACKAGE_ECOSYSTEM" = "github_actions" ]; then
                eligible=true
              fi
              ;;
            *)
              echo "未知 update-type=$UPDATE_TYPE，拒绝分类。" >&2
              exit 1
              ;;
          esac

          if [ "$eligible" = "true" ]; then
            gh pr edit "$PR_NUMBER" --repo "$REPO" \
              --add-label "$AUTOMERGE_ELIGIBLE_LABEL"
          fi
          echo "eligible=$eligible" >> "$GITHUB_OUTPUT"
      - name: 检查 required checks 后启用 auto-merge
        if: steps.eligibility.outputs.eligible == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          python3 scripts/dependabot_merge_gate.py \
            --repo "$REPO" \
            --pr "$PR_NUMBER"
```

The first write-capable step removes any prior eligibility label, so a metadata failure, unknown output, or later labeling failure leaves the PR ineligible. Only after `fetch-metadata` succeeds may classification add the label; an ineligible major update remains explicitly unlabeled. Every label create/edit failure stops the job, so the gate never runs on an unclassified PR. There is no `|| gh pr merge` fallback. If checks have not registered yet, the gate exits safely without merging and the scheduled sweep can revisit only the labeled PR.

- [ ] **Step 6: Replace sweep check heuristics and direct merge with the same gate**

Replace the entire `sweep.steps` block with:

```yaml
    steps:
      - uses: actions/checkout@v7
      - name: 清扫存量 dependabot PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          gh pr list --repo "$REPO" --author 'app/dependabot' --state open \
            --label "$AUTOMERGE_ELIGIBLE_LABEL" \
            --json number,title,labels > /tmp/prs.json
          python3 - <<'PY'
          import json
          import os
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import MergeDecision, gate_pull_request
          from feed_lib import reject_json_constant

          with open("/tmp/prs.json", encoding="utf-8") as handle:
              prs = json.load(handle, parse_constant=reject_json_constant)
          repo = os.environ["REPO"]
          eligibility_label = os.environ["AUTOMERGE_ELIGIBLE_LABEL"]
          operational_errors = 0
          print(f"带可靠资格标签的开放 dependabot PR: {len(prs)}")
          for pr in prs:
              number = pr["number"]
              title = pr["title"]
              labels = {label["name"] for label in pr.get("labels", [])}
              if eligibility_label not in labels:
                  print(f"  #{number} 跳过(资格标签缺失): {title}")
                  continue
              try:
                  decision = gate_pull_request(
                      repo=repo,
                      pr_number=number,
                  )
              except RuntimeError as exc:
                  operational_errors += 1
                  print(f"  #{number} gate error: {exc}", file=sys.stderr)
                  continue
              print(f"  #{number} {decision.value}: {title}")
          if operational_errors:
              raise SystemExit(1)
          PY
```

The sweep contains no title/version heuristic and does not infer eligibility for old PRs. It asks GitHub only for labeled Dependabot PRs, verifies the label again in parsed output, and delegates fresh `headRefOid`/`mergeable`/`mergeStateStatus` plus required-check reads to the gate. An empty required-check result or any state other than `MERGEABLE`/`CLEAN` cannot merge.

- [ ] **Step 7: Extend workflow static checks for Dependabot**

Append these methods to `WorkflowSecurityTests` in `scripts/tests/test_workflow_security.py`:

```python
    def test_dependabot_has_no_direct_merge_fallback(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("|| gh pr merge --merge", workflow)
        self.assertNotIn("statusCheckRollup", workflow)
        self.assertNotIn("--admin", workflow)
        self.assertIn("dependabot_merge_gate.py", workflow)
        self.assertIn("checks: read", workflow)
        self.assertIn("issues: write", workflow)

    def test_dependabot_sweep_requires_metadata_eligibility_label(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        label = "dependencies:auto-merge-eligible"
        self.assertIn("dependabot/fetch-metadata@v3", workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertNotIn("\n  pull_request:\n", workflow)
        self.assertIn("github.event.pull_request.user.login == 'dependabot[bot]'", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn(f"AUTOMERGE_ELIGIBLE_LABEL: {label}", workflow)
        self.assertIn('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"', workflow)
        self.assertIn('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"', workflow)
        self.assertIn('--label "$AUTOMERGE_ELIGIBLE_LABEL"', workflow)
        self.assertIn("steps.eligibility.outputs.eligible == 'true'", workflow)
        self.assertNotIn("major_match", workflow)
        self.assertNotIn("re.search", workflow)
        self.assertLess(
            workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
            workflow.index("dependabot/fetch-metadata@v3"),
        )
        self.assertLess(
            workflow.index("dependabot/fetch-metadata@v3"),
            workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
        )
        self.assertLess(
            workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"'),
            workflow.index("python3 scripts/dependabot_merge_gate.py"),
        )

    def test_dependabot_gate_requires_current_clean_state_and_native_checks(self) -> None:
        gate = (ROOT / "scripts" / "dependabot_merge_gate.py").read_text(encoding="utf-8")
        self.assertIn("view_command = [", gate)
        self.assertIn('"view",', gate)
        self.assertIn('"headRefOid,mergeable,mergeStateStatus"', gate)
        self.assertIn('view.get("mergeable") == "MERGEABLE"', gate)
        self.assertIn('view.get("mergeStateStatus") == "CLEAN"', gate)
        self.assertIn('"--required"', gate)
        self.assertIn('"--auto"', gate)
        self.assertIn('"--match-head-commit"', gate)
        self.assertNotIn("--head-sha", gate)
```

- [ ] **Step 8: Add Dependabot workflow and tests to CI coverage**

Add this entry to both `push.paths` and `pull_request.paths` in `.github/workflows/tests.yml`:

```yaml
      - ".github/workflows/dependabot-automerge.yml"
```

Append this command to the scripts security test step:

```yaml
          python scripts/tests/test_dependabot_merge_gate.py
```

- [ ] **Step 9: Run the Dependabot and workflow security suite**

```bash
python3 scripts/tests/test_dependabot_merge_gate.py
python3 scripts/tests/test_workflow_security.py
```

Expected: both report `OK` and exit 0.

Run:

```bash
rg -n '\|\| gh pr merge --merge|statusCheckRollup|--admin|major_match|re\.search|--head-sha' .github/workflows/dependabot-automerge.yml scripts/dependabot_merge_gate.py
```

Expected: no matches and exit code 1. Separately, the static test proves the metadata action precedes label assignment, the sweep filters on the exact label, and the gate contains the current-state query.

- [ ] **Step 10: Commit the Dependabot gate**

```bash
git add scripts/dependabot_merge_gate.py scripts/tests/test_dependabot_merge_gate.py scripts/tests/test_workflow_security.py .github/workflows/dependabot-automerge.yml .github/workflows/tests.yml
git diff --cached --check
git commit -m "fix(ci): require successful checks for Dependabot merge"
```

Expected: one commit containing the gate, workflow integration, and regression coverage.

---

### Task 7: Run the complete Stage 1A security verification

**Files:**
- Verify: `scripts/feed_lib.py`
- Verify: `scripts/validate_feed.py`
- Verify: `scripts/feed_ingress.py`
- Verify: `scripts/feed_publication.py`
- Verify: `scripts/dependabot_merge_gate.py`
- Verify: `.github/workflows/feed-validate.yml`
- Verify: `.github/workflows/alpha-routine.yml`
- Verify: `.github/workflows/hyperliquid-monitor.yml`
- Verify: `.github/workflows/monthly-studies.yml`
- Verify: `.github/workflows/dependabot-automerge.yml`
- Verify: `.github/workflows/tests.yml`

**Interfaces:**
- Verifies every interface and workflow contract established by Tasks 1–6.
- Produces no new code and no additional commit when all checks pass.

- [ ] **Step 1: Run every focused security test independently**

```bash
python3 scripts/tests/test_feed_validation_security.py
python3 scripts/tests/test_feed_ingress.py
python3 scripts/tests/test_validate_feed_cli.py
python3 scripts/tests/test_feed_publication.py
python3 scripts/tests/test_dependabot_merge_gate.py
python3 scripts/tests/test_workflow_security.py
```

Expected: each command exits 0 and reports `OK`.

- [ ] **Step 2: Run the existing Python regression tests**

```bash
python3 scripts/tests/test_validate_feed.py
python3 scripts/tests/test_chan_engine.py
```

Expected: feed validation prints all 13 existing assertions as passed; Chan prints all 24 existing assertions as passed.

- [ ] **Step 3: Compile all modified and new Python modules**

```bash
python3 -m py_compile scripts/feed_lib.py scripts/validate_feed.py scripts/feed_ingress.py scripts/feed_publication.py scripts/dependabot_merge_gate.py scripts/preipo_history.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Prove the dangerous workflow patterns are absent**

```bash
rg -n -U -P 'git(?:[^\r\n\\]|\\\r?\n[ \t]*){0,160}\badd\b(?:[^\r\n\\]|\\\r?\n[ \t]*){0,400}[ \t]+(?:--[ \t]+)?(?:\./)?feed(?:/?(?=[ \t;&|]|$)|/[^\s;&|]*[*?\[])' .github/workflows
rg -n 'git pull --rebase origin main \|\| true' .github/workflows/feed-validate.yml .github/workflows/alpha-routine.yml .github/workflows/hyperliquid-monitor.yml .github/workflows/monthly-studies.yml
rg -n '\|\| gh pr merge --merge|statusCheckRollup|--admin|major_match|re\.search|--head-sha' .github/workflows/dependabot-automerge.yml scripts/dependabot_merge_gate.py
```

Expected: all three commands print no matches and exit 1. The first PCRE mirrors the static detector's root/wildcard threat set across continuations and `git -C`; `test_workflow_security.py` additionally exercises inline/block YAML forms and proves each publisher exits non-zero after four failed push attempts.

- [ ] **Step 5: Verify diff hygiene and owned-file scope**

```bash
git diff --check
git status --short
```

Expected: `git diff --check` has no output. `git status --short` shows no uncommitted implementation files; the pre-existing untracked `AGENTS.md` remains untracked and unchanged.

- [ ] **Step 6: Review the Stage 1A/Stage 3 boundary**

Confirm from the diff that:

```text
Stage 1A present:
- validate-before-write external ingress
- strict JSON constants at file, dispatch, manifest, signing, and writing boundaries
- strict report ID and resolved-root checks
- exclusive inbox creation
- dispatch temporary inbox exclusion plus exact tracked-deletion proof
- missing/invalid HMAC fail-closed behavior
- zero-match validation failure
- exact temporary Git staging allowlist
- metadata-derived Dependabot eligibility label
- current `MERGEABLE`/`CLEAN` plus non-empty required-check Dependabot gate

Stage 3 intentionally absent:
- canonical reader-facing feed manifest
- run-ID staging directories for every producer
- atomic artifact replacement transaction
- manifest-written-last publication
- previous-complete-manifest fallback
- dedicated data branch transport
```

Expected: no Stage 3 behavior is claimed or partially exposed as a stable reader contract.
