"""Static regression checks for security-sensitive workflows."""
from __future__ import annotations

import pathlib
import re
import shlex
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SHELL_CONTROL = {";", "&&", "||", "|", "&", "(", ")"}
BLOCK_SCALAR_HEADER = re.compile(
    r"^(?P<style>[|>])(?:(?:[+-][1-9]?|[1-9][+-]?))?(?:[ \t]+#.*)?$"
)


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
        block_header = BLOCK_SCALAR_HEADER.fullmatch(body)
        if block_header is not None:
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
            if block_header.group("style") == ">":
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
    def test_workflow_scan_ci_triggers_on_every_workflow_change(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )

        self.assertEqual(text.count('      - ".github/workflows/**"'), 2)
        self.assertEqual(
            re.findall(r'^\s+- "\.github/workflows/[^*\"]+"$', text, re.MULTILINE),
            [],
        )

    def test_broad_staging_detector_covers_yaml_shell_and_pathspec_variants(self) -> None:
        dangerous = {
            "inline root": "steps:\n  - run: git add feed\n",
            "block slash": "steps:\n  - run: |\n      git add ./feed/\n",
            "wildcard": "steps:\n  - run: git add feed/*\n",
            "quoted wildcard": "steps:\n  - run: git add 'feed/**'\n",
            "inline quoted": 'steps:\n  - run: "git add feed/**"\n',
            "literal comment": (
                "steps:\n  - run: | # shell\n      git add feed\n"
            ),
            "literal indent then chomp": (
                "steps:\n  - run: |2-\n      git add feed\n"
            ),
            "literal chomp then indent": (
                "steps:\n  - run: |-2\n      git add feed\n"
            ),
            "folded comment and keep": (
                "steps:\n  - run: >+ # folded shell\n      git add feed\n"
            ),
            "folded indent then chomp": (
                "steps:\n  - run: >2+\n      git add feed\n"
            ),
            "folded chomp then indent": (
                "steps:\n  - run: >-2\n      git add feed\n"
            ),
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

        inline = 'steps:\n  - run: "echo inline | sed s/x/y/"\n'
        self.assertEqual(
            workflow_run_scripts(inline),
            [(2, "echo inline | sed s/x/y/")],
        )

        for header in ("|22", "|+-", ">0-", "|#not-a-comment"):
            with self.subTest(malformed_header=header):
                malformed = f"steps:\n  - run: {header}\n      git add feed\n"
                self.assertEqual(workflow_run_scripts(malformed), [(2, header)])

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
            "openclaw-notes.yml": 1,
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
        self.assertIn("statuses: write", workflow)

    def test_dependabot_sweep_requires_metadata_eligibility_label(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        label = "dependencies:auto-merge-eligible"
        self.assertIn("dependabot/fetch-metadata@v3", workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertNotIn("\n  pull_request:\n", workflow)
        self.assertIn(
            "github.event.pull_request.user.login == 'dependabot[bot]'", workflow
        )
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
            workflow.index('--pr "$PR_NUMBER"'),
        )

    def test_dependabot_metadata_policy_uses_head_bound_attestation(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        required = (
            "revoke_auto_merge(",
            "-f state=pending",
            "--classify-ecosystem",
            '--add-label "$AUTOMERGE_ELIGIBLE_LABEL"',
            "-f state=success",
        )
        for marker in required:
            self.assertIn(marker, workflow)
        metadata = workflow.index("dependabot/fetch-metadata@v3")
        remove_label = workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        revoke = workflow.index("revoke_auto_merge(")
        pending = workflow.index("-f state=pending")
        classify = workflow.index("--classify-ecosystem")
        add_label = workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        success = workflow.index("-f state=success")

        self.assertIn(
            "AUTOMERGE_ATTESTATION_CONTEXT: dependabot/auto-merge-eligible",
            workflow,
        )
        self.assertIn("HEAD_SHA: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn(
            "PACKAGE_ECOSYSTEM: ${{ steps.meta.outputs.package-ecosystem }}",
            workflow,
        )
        self.assertIn('--classify-ecosystem "$PACKAGE_ECOSYSTEM"', workflow)
        self.assertIn("--classify-update-type", workflow)
        self.assertIn("-f state=failure", workflow)
        self.assertIn('"repos/$REPO/statuses/$HEAD_SHA"', workflow)
        self.assertLess(remove_label, revoke)
        self.assertLess(revoke, pending)
        self.assertLess(pending, metadata)
        self.assertLess(metadata, classify)
        self.assertLess(classify, add_label)
        self.assertLess(add_label, success)
        self.assertLess(success, workflow.index("--pr \"$PR_NUMBER\""))

    def test_dependabot_cleanup_revokes_active_auto_merge_fail_closed(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        gate = (ROOT / "scripts" / "dependabot_merge_gate.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("cleanup_failed=0", workflow)
        self.assertIn("from dependabot_merge_gate import revoke_auto_merge", workflow)
        self.assertIn('if [ "$cleanup_failed" -ne 0 ]; then', workflow)
        self.assertIn('"--disable-auto"', gate)
        self.assertNotIn("--admin", gate)

    def test_dependabot_gate_requires_current_clean_state_and_native_checks(
        self,
    ) -> None:
        gate = (ROOT / "scripts" / "dependabot_merge_gate.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("view_command = [", gate)
        self.assertIn('"view",', gate)
        self.assertIn('"headRefOid,mergeable,mergeStateStatus,labels"', gate)
        self.assertIn('view.get("mergeable") == "MERGEABLE"', gate)
        self.assertIn('view.get("mergeStateStatus") == "CLEAN"', gate)
        self.assertIn("statuses?per_page=100", gate)
        self.assertIn("eligibility_attested(statuses)", gate)
        self.assertIn('TRUSTED_ATTESTATION_CREATOR = "github-actions[bot]"', gate)
        self.assertIn('"--required"', gate)
        self.assertIn('"--auto"', gate)
        self.assertIn('"--match-head-commit"', gate)
        self.assertNotIn("--head-sha", gate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
