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
