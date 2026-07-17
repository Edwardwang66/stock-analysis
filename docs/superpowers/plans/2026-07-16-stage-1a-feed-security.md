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
- Only the on-PR job may derive Dependabot eligibility, and only from successful `dependabot/fetch-metadata` outputs. The scheduled sweep reconciles every open PR authored by `app/dependabot`; unlabeled legacy or unknown PRs reach the gate and have any active auto-merge request revoked.
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
- Modify: `.github/workflows/dependabot-automerge.yml`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Produces: `dependabot_merge_gate.MergeDecision` with `ENABLED` and `NOT_READY` values.
- Produces: `dependabot_merge_gate.MetadataDecision` with `ELIGIBLE` and `INELIGIBLE` values plus strict `classify_metadata(package_ecosystem: object, update_type: object) -> MetadataDecision`.
- Produces: `required_checks_successful(checks: object) -> bool`.
- Produces: `current_pr_ready(view: object) -> bool` requiring a non-empty `headRefOid`, `mergeable == "MERGEABLE"`, and `mergeStateStatus == "CLEAN"`.
- Produces: exact-label and head-attestation validators that reject malformed shapes and require the newest exact-context status to be a trusted success.
- Produces: `gate_pull_request(*, repo: str, pr_number: int, run=subprocess.run) -> MergeDecision`.
- Produces: `revoke_auto_merge(*, repo: str, pr_number: int, run=subprocess.run) -> bool`, which queries native auto-merge state and disables it only when active.
- CLI: `python scripts/dependabot_merge_gate.py --repo <owner/repo> --pr <number>`.
- Eligibility contract: after `dependabot/fetch-metadata`, the on-PR job synchronizes `dependencies:auto-merge-eligible` plus a head-bound `dependabot/auto-merge-eligible` commit status; npm/pip semver-major PRs remain unlabeled and receive failure status, while permitted updates receive the label and success status. Failure to classify, mutate the label, or post status stops the job.
- Metadata token contract: consume the action outputs exactly as `npm_and_yarn`, `pip`, and `github_actions`. In particular, `npm_and_yarn` and `github_actions` differ from the `.github/dependabot.yml` configuration keys `npm` and `github-actions`; do not normalize or accept the configuration keys as aliases.
- Concurrency contract: all on-PR, scheduled, and manual runs share the top-level group `dependabot-automerge-${{ github.repository }}` with `queue: max`; do not use `cancel-in-progress: true`. GitHub queues at most 100 pending runs in this mode, so the residual overflow risk remains explicit.
- Event contract: the write-capable classifier uses `pull_request_target`, checks `github.event.pull_request.user.login == 'dependabot[bot]'`, and checks out only the explicit base SHA with credentials disabled; no PR-controlled code is executed. At cleanup start and again before eligibility writes, query the current `headRefOid` and compare it to the event head. A failed, empty, or mismatched query imports trusted-base `revoke_auto_merge`, attempts one native revoke, and exits nonzero without adding the label, posting success, or enabling auto-merge; a revoke failure also remains nonzero.
- Sweep contract: list up to 1000 open PRs authored by `app/dependabot` without label prefiltering and request only `number,title`. Every fetched result reaches `gate_pull_request`; unlabeled legacy/unknown PRs are never inferred from their title and are reconciled to inactive auto-merge. Per-PR operational errors are counted while the sweep continues through the fetched set, then make the job fail.
- Reconciliation contract: private `_evaluate_pull_request` performs the current-state decision and the public `gate_pull_request` owns auto-merge reconciliation. `ENABLED` returns without an auto-merge query. `NOT_READY` must confirm auto-merge is inactive or disable it. Any evaluator `RuntimeError` triggers exactly one revoke attempt; if that also fails, the raised error preserves both `primary failure:` and `auto-merge revoke failure:`.
- GitHub CLI contract: current PR state and label are queried with `gh pr view --json headRefOid,mergeable,mergeStateStatus,labels`; the head-bound trusted status and required checks are then queried before any enable mutation.
- Merge contract: the only permitted merge command includes `--auto`, `--merge`, and `--match-head-commit <current headRefOid>`; it is unreachable unless current state is exactly `MERGEABLE`/`CLEAN` and the current required-check set is non-empty and entirely successful.

- [ ] **Step 1: Write the fail-closed gate and reconciliation tests**

Create `scripts/tests/test_dependabot_merge_gate.py` as the executable specification. The complete current file is the authoritative final test implementation; this plan deliberately does not embed a second, partial `FakeRunner` or test-class copy that can drift. Add the tests before the module and cover all of these contracts:

- Metadata classification enumerates only the nine repository-supported action-output pairs: `npm_and_yarn` and `pip` patch/minor are eligible and major is ineligible; `github_actions` patch/minor/major are eligible. Missing values, unknown ecosystems/update types, and configuration-key aliases such as `npm` or `github-actions` raise or exit nonzero.
- PR readiness rejects malformed data, an empty head, and every state other than exactly `MERGEABLE` plus `CLEAN`. An exact eligibility label and the newest exact-context success status from `github-actions[bot]` on that current head are both required.
- Required checks are a non-empty sequence whose every item has a non-empty name, `state == "SUCCESS"`, and `bucket == "pass"`. Empty output, pending exit code 8, GitHub's explicit “no required checks” response, malformed/non-finite JSON, failed queries, pending, skipped, neutral, cancelled, and failed checks all fail closed.
- The only enabling mutation is native auto-merge with `--auto --merge --match-head-commit <current headRefOid>`; it is never reached for a blocked PR, a stale/malformed label or attestation, or missing/non-successful checks.
- `revoke_auto_merge` queries `autoMergeRequest`, makes no disable call when inactive, and uses the native `--disable-auto` command exactly once when active. Query, parse, shape, or disable errors raise.
- Public `gate_pull_request` reconciles every `NOT_READY` result by querying/revoking auto-merge. Every evaluator `RuntimeError`, including view, attestation, checks, or enable failures, triggers exactly one revoke attempt; a second failure preserves one `primary failure:` and one `auto-merge revoke failure:` in the raised error. `ENABLED` does not perform a redundant auto-merge query.
- Tests exercise strict metadata classification through the CLI and exercise merge-gate behavior directly through the injected `gate_pull_request` function.

- [ ] **Step 2: Run the test to verify the gate module is absent**

At this red-test point, before creating the module, run:

```bash
python3 scripts/tests/test_dependabot_merge_gate.py
```

Expected: exit code 1 with `ModuleNotFoundError: No module named 'dependabot_merge_gate'`.

- [ ] **Step 3: Implement the fail-closed gate and public reconciliation wrapper**

Create `scripts/dependabot_merge_gate.py` against the interfaces and test contract above. The complete current repository file `scripts/dependabot_merge_gate.py`, together with `scripts/tests/test_dependabot_merge_gate.py`, is the authoritative final implementation; do not substitute an abbreviated inline copy from this plan.

The implementation must preserve this control flow:

1. `classify_metadata` accepts only the exact `dependabot/fetch-metadata` tokens listed in Step 1 and emits only `eligible` or `ineligible`; unknown or missing input fails closed.
2. Private `_evaluate_pull_request` strictly parses GitHub JSON with `reject_json_constant`, reads `headRefOid,mergeable,mergeStateStatus,labels`, requires the exact eligibility label, then reads statuses for that head and accepts only the newest exact attestation context when it is a success created by `github-actions[bot]`.
3. Only after those checks does it request native required checks. Any absent, unavailable, malformed, incomplete, or unsuccessful set returns `NOT_READY`; other operational failures raise.
4. The only enable command is `gh pr merge ... --auto --merge --match-head-commit <current headRefOid>`.
5. `revoke_auto_merge` strictly queries `autoMergeRequest` and, only when active, calls `gh pr merge ... --disable-auto`; query, parse, shape, and disable failures raise.
6. Public `gate_pull_request` owns reconciliation: `NOT_READY` always calls `revoke_auto_merge`; any evaluator `RuntimeError` gets one revoke attempt before re-raising; a revoke failure preserves both failures without recursion; `ENABLED` returns directly.
7. The CLI keeps classification mode separate from gate mode, requires `--repo` and `--pr` for gating, and exits nonzero on operational or classification errors.

- [ ] **Step 4: Run gate tests and compile the module**

```bash
python3 scripts/tests/test_dependabot_merge_gate.py
python3 -m py_compile scripts/dependabot_merge_gate.py
```

Expected: the entire current gate suite exits 0 and ends with `OK`; no fixed test count is part of this contract. Compilation exits 0 with no output. The suite must demonstrate the fail-closed and reconciliation behaviors from Step 1, not merely the successful merge path.

- [ ] **Step 5: Replace the on-PR direct fallback with the tested gate**

Replace the `pull_request` trigger with the write-capable trusted-base event, and update both job guards:

```yaml
on:
  pull_request_target:
    types: [opened, synchronize, reopened]
  schedule:
    - cron: "45 */6 * * *"
  workflow_dispatch:

concurrency:
  group: dependabot-automerge-${{ github.repository }}
  queue: max

jobs:
  on-pr:
    if: >-
      github.event_name == 'pull_request_target'
      && github.event.pull_request.user.login == 'dependabot[bot]'
  sweep:
    if: github.event_name != 'pull_request_target'
```

Update the workflow's opening “两层” comment to describe `pull_request_target` metadata classification/labeling and a full scheduled reconciliation sweep; remove any statement that the sweep derives version eligibility from a PR title. Do not check out the Dependabot head under `pull_request_target`; every executable file in this job comes from the base SHA. Add read permission for required-check data plus the issue-label and commit-status write scopes, while preserving the existing write scopes needed to enable auto-merge. Also define the workflow-wide eligibility label and head-bound attestation context:

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
  checks: read
  statuses: write

env:
  AUTOMERGE_ELIGIBLE_LABEL: dependencies:auto-merge-eligible
  AUTOMERGE_ATTESTATION_CONTEXT: dependabot/auto-merge-eligible
```

In `.github/workflows/dependabot-automerge.yml`, make the `on-pr` steps exactly:

```yaml
    steps:
      - name: Checkout trusted base gate
        uses: actions/checkout@v7
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          persist-credentials: false
      - name: 清理旧资格并撤销 auto-merge
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: |
          if [ -z "$HEAD_SHA" ]; then
            echo "pull_request_target 未提供 head SHA，拒绝清理。" >&2
            exit 1
          fi

          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python3 - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝旧事件写入。" >&2
            exit 1
          fi

          cleanup_failed=0
          current_labels="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json labels --jq '.labels[].name'
          )" || cleanup_failed=1
          if grep -Fxq "$AUTOMERGE_ELIGIBLE_LABEL" <<<"$current_labels"; then
            gh pr edit "$PR_NUMBER" --repo "$REPO" \
              --remove-label "$AUTOMERGE_ELIGIBLE_LABEL" \
              || cleanup_failed=1
          fi

          python3 - "$REPO" "$PR_NUMBER" <<'PY' || cleanup_failed=1
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY

          gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
            -f state=pending \
            -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
            -f description="Dependabot auto-merge eligibility is being reclassified" \
            --silent \
            || cleanup_failed=1

          if [ "$cleanup_failed" -ne 0 ]; then
            echo "旧资格清理或 auto-merge 撤销失败，拒绝继续分类。" >&2
            exit 1
          fi

          gh label create "$AUTOMERGE_ELIGIBLE_LABEL" \
            --repo "$REPO" \
            --color "0E8A16" \
            --description "Dependabot update classified by fetch-metadata for guarded auto-merge" \
            --force
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
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          UPDATE_TYPE: ${{ steps.meta.outputs.update-type }}
          PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}
        run: |
          current_head=""
          head_query_failed=0
          current_head="$(
            gh pr view "$PR_NUMBER" --repo "$REPO" --json headRefOid --jq '.headRefOid // empty'
          )" || head_query_failed=1
          if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] || [ "$current_head" != "$HEAD_SHA" ]; then
            python3 - "$REPO" "$PR_NUMBER" <<'PY'
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import revoke_auto_merge

          revoke_auto_merge(repo=sys.argv[1], pr_number=int(sys.argv[2]))
          PY
            echo "事件 head 已过期或当前 head 查询失败；已撤销 auto-merge，拒绝资格写入。" >&2
            exit 1
          fi

          classification="$(
            python3 scripts/dependabot_merge_gate.py \
              --classify-ecosystem "$PACKAGE_ECOSYSTEM" \
              --classify-update-type "$UPDATE_TYPE"
          )"
          eligible=false
          case "$classification" in
            eligible)
              gh pr edit "$PR_NUMBER" --repo "$REPO" \
                --add-label "$AUTOMERGE_ELIGIBLE_LABEL"
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=success \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is eligible for guarded auto-merge" \
                --silent
              eligible=true
              ;;
            ineligible)
              gh api --method POST "repos/$REPO/statuses/$HEAD_SHA" \
                -f state=failure \
                -f context="$AUTOMERGE_ATTESTATION_CONTEXT" \
                -f description="Dependabot update is outside guarded auto-merge policy" \
                --silent
              ;;
            *)
              echo "分类器返回未知结果: $classification" >&2
              exit 1
              ;;
          esac

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

The order above is security-sensitive. Trusted-base checkout disables persisted credentials. Cleanup first requires a non-empty event `HEAD_SHA` and compares it to a freshly queried current head; a failed, empty, or mismatched query attempts trusted-base native revocation and exits nonzero, and a revocation failure also exits nonzero. For a matching head, label query/removal, native revocation, and a head-bound pending status form one fail-closed cleanup: any query, removal, revoke, or status failure stops before label creation and metadata classification. The label definition itself must then be created successfully.

Only after cleanup may `fetch-metadata` run. The eligibility step repeats the same current-head stale-event guard before any classification write. The Python classifier receives the action's ecosystem and update type verbatim and accepts only the explicitly enumerated production pairs; patch/minor is never a shell fail-open rule for an arbitrary ecosystem. An eligible result adds the label and then posts success to the event head; an ineligible result posts failure to that head and leaves the label absent. Unknown classifier output, label/status failure, or failed revocation exits before a successful `GITHUB_OUTPUT`; only a completed eligible path writes `eligible=true` and reaches the gate. There is no direct merge fallback. If checks are not ready, the public gate reconciles auto-merge to inactive, and the unfiltered scheduled sweep revisits every open Dependabot PR.

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
            --limit 1000 \
            --json number,title > /tmp/prs.json
          python3 - <<'PY'
          import json
          import os
          import sys

          sys.path.insert(0, "scripts")
          from dependabot_merge_gate import gate_pull_request
          from feed_lib import reject_json_constant

          with open("/tmp/prs.json", encoding="utf-8") as handle:
              prs = json.load(handle, parse_constant=reject_json_constant)
          repo = os.environ["REPO"]
          operational_errors = 0
          print(f"开放 dependabot PR: {len(prs)}")
          for pr in prs:
              number = pr["number"]
              title = pr["title"]
              try:
                  decision = gate_pull_request(
                      repo=repo,
                      pr_number=number,
                  )
              except RuntimeError as exc:
                  operational_errors += 1
                  print(f"  #{number} gate error: {exc}", file=sys.stderr)
              else:
                  print(f"  #{number} {decision.value}: {title}")
          if operational_errors:
              raise SystemExit(1)
          PY
```

The sweep contains no title/version heuristic and does not infer eligibility for old PRs. It asks GitHub for every open Dependabot PR in the fetched set (up to the platform's 1000-result request limit) and delegates fresh label, `headRefOid`/`mergeable`/`mergeStateStatus`, attestation, and required-check reads to the public gate. An empty required-check result or any state other than `MERGEABLE`/`CLEAN` cannot merge, and any active auto-merge request is revoked for `NOT_READY`. A per-PR operational error is reported without skipping the rest of the fetched set, and any accumulated error makes the sweep job exit nonzero.

- [ ] **Step 7: Extend workflow static checks for Dependabot**

Extend `WorkflowSecurityTests` in `scripts/tests/test_workflow_security.py`. The complete current file is the authoritative final static suite; keep these assertions together rather than copying a reduced inline method set from this plan:

- No direct merge fallback, `statusCheckRollup`, `--admin`, or `--head-sha`; the workflow has `checks: read`, `issues: write`, and `statuses: write`.
- One top-level `dependabot-automerge-${{ github.repository }}` concurrency group uses `queue: max` and never `cancel-in-progress: true`.
- The trusted-base `pull_request_target` job uses the Dependabot actor guard, explicit base SHA, and `persist-credentials: false`.
- The sweep requests `number,title` for every open `app/dependabot` PR up to `--limit 1000`, has no label prefilter or title/version inference, and sends every fetched PR to `gate_pull_request`.
- Exactly two current-head queries and stale-event guards occur before their corresponding writes; each guard imports `revoke_auto_merge` and exits before label or success-status mutation.
- Cleanup and eligibility ordering is enforced: remove label, revoke, pending status, metadata, strict classification, add label, success status, then gate. Failure status for ineligible metadata, `HEAD_SHA`, and the exact attestation context are present.
- Cleanup tracks label-query/removal, native revoke, and pending-status failures and exits before classification. The gate requires the current label, current-head trusted attestation, exact merge state, non-empty successful required checks, native `--disable-auto` reconciliation, and head-matched native auto-merge.

- [ ] **Step 8: Add Dependabot workflow and tests to CI coverage**

Ensure both `push.paths` and `pull_request.paths` in `.github/workflows/tests.yml` cover every workflow file, so later changes cannot bypass the static suite:

```yaml
      - ".github/workflows/**"
```

Ensure the scripts security test step runs the authoritative gate suite:

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

Expected: no matches and exit code 1. Separately, the authoritative static suite proves the top-level queue, both stale-event revoke/exit guards, cleanup/revoke/pending and classification/status ordering, the unfiltered full sweep, and current-head attestation plus public reconciliation in the gate.

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
