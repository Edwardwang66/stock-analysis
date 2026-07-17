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
