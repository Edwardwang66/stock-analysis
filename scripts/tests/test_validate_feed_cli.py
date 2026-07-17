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

    def test_only_untrusted_checkout_explicitly_allows_pr_head(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "feed-validate.yml").read_text(
            encoding="utf-8"
        )
        unsafe_input = "allow-unsafe-pr-checkout: true"
        trusted_block = workflow.split(
            "- name: Checkout trusted base validator", 1
        )[1].split("- name: Checkout untrusted submission as data only", 1)[0]
        head_block = workflow.split(
            "- name: Checkout untrusted submission as data only", 1
        )[1].split("- uses: actions/setup-python@v6", 1)[0]

        self.assertEqual(workflow.count(unsafe_input), 1)
        self.assertNotIn(unsafe_input, trusted_block)
        self.assertIn(unsafe_input, head_block)

    def test_pr_and_push_use_strict_inbox_enumeration(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "feed-validate.yml").read_text(
            encoding="utf-8"
        )
        pr_block = workflow.split(
            "- name: Validate signed PR inbox files with trusted code", 1
        )[1].split("\n\n  publish:", 1)[0]
        push_block = workflow.split("- name: Merge signed push submission", 1)[
            1
        ].split("- name: Receive and merge signed dispatch submission", 1)[0]
        strict_checks = (
            'if ! find "$inbox" -mindepth 1 -print0 > "$entry_list"; then',
            "find 无法完整枚举 feed/inbox，拒绝校验。",
            "files=()",
            "invalid=0",
            "while IFS= read -r -d '' entry; do",
            'relative="${entry#"$inbox"/}"',
            'name="${entry##*/}"',
            '[[ "$relative" == */* || "$name" == .* || ! -f "$entry" || -L "$entry" || "$name" != *.json ]]',
            "invalid=1",
            'done < "$entry_list"',
            "if (( invalid != 0 )); then",
            "if (( ${#files[@]} == 0 )); then",
        )

        for label, block, inbox in (
            ("pr", pr_block, 'inbox="$GITHUB_WORKSPACE/submission/feed/inbox"'),
            ("push", push_block, 'inbox="feed/inbox"'),
        ):
            with self.subTest(path=label):
                self.assertIn(inbox, block)
                for check in strict_checks:
                    self.assertIn(check, block)
                self.assertNotIn("mapfile", block)
                self.assertNotIn("< <(", block)
                self.assertNotIn("shopt -s nullglob", block)
                self.assertNotIn("files=(feed/inbox/*.json)", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
