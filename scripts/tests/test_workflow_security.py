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


if __name__ == "__main__":
    unittest.main(verbosity=2)
