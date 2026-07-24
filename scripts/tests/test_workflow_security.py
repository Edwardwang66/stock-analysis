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
GENERATED_FEED_IGNORES = [
    "feed/crypto/**",
    "feed/factory/**",
    "feed/funds/**",
    "feed/health.json",
    "feed/index.json",
    "feed/intraday/**",
    "feed/market/**",
    "feed/reports/**",
    "feed/screener/**",
    "feed/signals/**",
    "feed/stock-notes/**",
    "feed/watchlist.json",
]
TOP_LEVEL_WORKFLOW_KEYS = ["name", "on", "permissions", "concurrency", "jobs"]
JOB_KEYS = ["frontend", "python", "gate"]
FRONTEND_JOB_KEYS = ["name", "runs-on", "strategy", "defaults", "env", "steps"]
PYTHON_JOB_KEYS = ["name", "runs-on", "strategy", "env", "steps"]
GATE_JOB_KEYS = ["name", "if", "needs", "runs-on", "steps"]
EVENT_POLICY_LINES = [
    "  push:",
    "    branches: [main]",
    "    paths-ignore:",
    *[f'      - "{path}"' for path in GENERATED_FEED_IGNORES],
    "  pull_request:",
    "  workflow_dispatch:",
]
CONCURRENCY_LINES = [
    "  group: ci-${{ github.ref }}",
    "  cancel-in-progress: true",
]
FRONTEND_DEFAULTS_LINES = [
    "      run:",
    "        working-directory: frontend",
]
FRONTEND_ENV_LINES = [
    "      # Approved spec still requires Node 20.20.2 even though Node 20 is EOL.",
    '      NEXT_TELEMETRY_DISABLED: "1"',
    "      NEXT_PUBLIC_BASE_PATH: ${{ matrix.base_path }}",
]
PYTHON_ENV_LINES = [
    '      PYTHONDONTWRITEBYTECODE: "1"',
    '      PIP_DISABLE_PIP_VERSION_CHECK: "1"',
]
COMMON_PYTHON_ENTRYPOINTS = [
    "python tests/test_backend.py",
    "python tests/test_api.py",
    "python scripts/tests/test_chan_engine.py",
    "python scripts/tests/test_validate_feed.py",
    "python scripts/tests/test_feed_validation_security.py",
    "python scripts/tests/test_feed_ingress.py",
    "python scripts/tests/test_validate_feed_cli.py",
    "python scripts/tests/test_feed_publication.py",
    "python scripts/tests/test_dependabot_merge_gate.py",
    "python scripts/tests/test_workflow_security.py",
]
LOCK_COMPILE_FLAGS = [
    "--generate-hashes",
    "--allow-unsafe",
    "--no-reuse-hashes",
    "--resolver=backtracking",
    "--no-strip-extras",
    "--no-header",
]
FRONTEND_STRATEGY_LINES = [
    "      fail-fast: false",
    "      matrix:",
    "        include:",
    "          - profile: static",
    "            base_path: /stock-analysis",
    "          - profile: server",
    '            base_path: ""',
]
PYTHON_STRATEGY_LINES = [
    "      fail-fast: false",
    "      matrix:",
    "        include:",
    '          - python_version: "3.11.15"',
    "            lockfile: requirements/ci-py311.txt",
    '          - python_version: "3.12.13"',
    "            lockfile: requirements/ci-py312.txt",
]
PY311_LOCK_REPRODUCTIONS = [
    ("backend/requirements.txt", "backend.txt", "backend/requirements.in"),
    ("scripts/requirements.txt", "scripts.txt", "scripts/requirements.in"),
    (
        "scripts/requirements-winter-pg.txt",
        "winter-pg.txt",
        "scripts/requirements-winter-pg.in",
    ),
    ("backtest/requirements.txt", "backtest.txt", "backtest/requirements.in"),
    (
        "requirements/automation.txt",
        "automation.txt",
        "requirements/automation.in",
    ),
    ("requirements/ci-py311.txt", "ci-py311.txt", "requirements/ci.in"),
]
PY312_LOCK_REPRODUCTIONS = [
    ("requirements/ci-py312.txt", "ci-py312.txt", "requirements/ci.in"),
]
FRONTEND_STEP_BLOCKS = [
    "\n".join(
        [
            "      - uses: actions/checkout@v7",
            "        with:",
            "          persist-credentials: false",
        ]
    ),
    "\n".join(
        [
            "      - uses: actions/setup-node@v7",
            "        with:",
            "          node-version-file: .node-version",
            "          cache: npm",
            "          cache-dependency-path: frontend/package-lock.json",
        ]
    ),
    "\n".join(
        [
            "      - name: Verify exact Node and npm",
            "        run: |",
            '          test "$(node --version)" = "v20.20.2"',
            '          test "$(npm --version)" = "10.8.2"',
        ]
    ),
    "      - run: npm ci",
    "      - run: npm run lint",
    "      - run: npm run typecheck",
    "      - run: npm run test:scripts",
    "\n".join(
        [
            "      - if: matrix.profile == 'static'",
            "        run: npm run build:static",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'static'",
            "        run: npm run smoke:static",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'server'",
            "        run: npm run build:server",
        ]
    ),
    "\n".join(
        [
            "      - if: matrix.profile == 'server'",
            "        run: npm run smoke:server",
        ]
    ),
]


def expected_reproduction_step(
    name: str,
    version: str,
    rows: list[tuple[str, str, str]],
) -> str:
    compile_flags = " ".join(LOCK_COMPILE_FLAGS)
    lines = [
        f"      - name: {name}",
        f"        if: matrix.python_version == '{version}'",
        "        shell: bash",
        "        run: |",
        "          set -euo pipefail",
        '          tmp="$(mktemp -d)"',
        "          trap 'rm -rf \"$tmp\"' EXIT",
    ]
    lines.extend(
        f'          cp {committed} "$tmp/{temporary}"'
        for committed, temporary, _ in rows
    )
    lines.extend(
        "          python -m piptools compile "
        f'{compile_flags} --output-file="$tmp/{temporary}" {direct_input}'
        for _, temporary, direct_input in rows
    )
    lines.extend(
        f'          cmp "$tmp/{temporary}" {committed}'
        for committed, temporary, _ in rows
    )
    return "\n".join(lines)


PYTHON_STEP_BLOCKS = [
    "\n".join(
        [
            "      - uses: actions/checkout@v7",
            "        with:",
            "          persist-credentials: false",
        ]
    ),
    "\n".join(
        [
            "      - uses: actions/setup-python@v6",
            "        with:",
            "          python-version: ${{ matrix.python_version }}",
            "          cache: pip",
            "          cache-dependency-path: ${{ matrix.lockfile }}",
        ]
    ),
    '      - run: python -m pip install --require-hashes -r "${{ matrix.lockfile }}"',
    "      - run: python -m pip check",
    expected_reproduction_step(
        "Reproduce Python 3.11 locks from direct inputs",
        "3.11.15",
        PY311_LOCK_REPRODUCTIONS,
    ),
    expected_reproduction_step(
        "Reproduce Python 3.12 lock from direct inputs",
        "3.12.13",
        PY312_LOCK_REPRODUCTIONS,
    ),
    "\n".join(
        [
            "      - name: Backend HTTP and data-layer tests",
            "        working-directory: backend",
            "        run: |",
            "          python tests/test_backend.py",
            "          python tests/test_api.py",
        ]
    ),
    "\n".join(
        [
            "      - name: Automation and feed-validation tests",
            "        run: |",
            *[f"          {command}" for command in COMMON_PYTHON_ENTRYPOINTS[2:]],
        ]
    ),
    "\n".join(
        [
            "      - name: Primary-runtime lock consistency",
            "        if: matrix.python_version == '3.11.15'",
            "        run: |",
            "          python scripts/tests/test_check_lock_consistency.py",
            "          python scripts/check_lock_consistency.py --root .",
        ]
    ),
]
GATE_STEP_BLOCKS = [
    "\n".join(
        [
            "      - name: Require every runtime matrix to pass",
            "        env:",
            "          FRONTEND_RESULT: ${{ needs.frontend.result }}",
            "          PYTHON_RESULT: ${{ needs.python.result }}",
            "        run: |",
            '          test "$FRONTEND_RESULT" = success',
            '          test "$PYTHON_RESULT" = success',
        ]
    )
]


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


def top_level_mapping_block(text: str, key: str) -> str:
    """Return one top-level YAML mapping block without parsing YAML."""
    return mapping_block(text, key, indent=0)


def mapping_block(text: str, key: str, indent: int) -> str:
    """Return one YAML mapping body at the requested indentation."""
    lines = text.splitlines()
    header = f"{' ' * indent}{key}:"
    starts = [index for index, line in enumerate(lines) if line == header]
    if len(starts) != 1:
        raise AssertionError(
            f"expected one indent-{indent} {key!r} block, found {len(starts)}"
        )
    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        line_indent = len(line) - len(line.lstrip())
        if line.strip() and line_indent <= indent:
            break
        block.append(line)
    return "\n".join(block)


def direct_mapping_keys(text: str, indent: int) -> list[str]:
    """Return every direct mapping key, rejecting unsupported key syntax."""
    key_pattern = re.compile(
        rf"^{' ' * indent}"
        r"(?P<key>[A-Za-z0-9_-]+|\"[^\"]+\"|'[^']+')\s*:"
    )
    keys: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent != indent:
            continue
        match = key_pattern.match(line)
        if match is None:
            keys.append(f"<invalid:{line.strip()}>")
            continue
        key = match.group("key")
        if key[:1] in {'"', "'"} and key[-1:] == key[:1]:
            key = key[1:-1]
        keys.append(key)
    return keys


def workflow_step_blocks(job_block: str) -> list[str]:
    """Return step-local blocks so policy strings cannot satisfy another step."""
    lines = job_block.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^ {6}-(?:\s|$)", line)
    ]
    return [
        "\n".join(lines[start : starts[offset + 1] if offset + 1 < len(starts) else None])
        for offset, start in enumerate(starts)
    ]


def normalized_step_blocks(job_block: str) -> list[str]:
    """Return exact step blocks while ignoring only trailing blank separators."""
    return [block.rstrip() for block in workflow_step_blocks(job_block)]


def only_block_containing(blocks: list[str], marker: str) -> str:
    matches = [block for block in blocks if marker in block]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one block containing {marker!r}, found {len(matches)}"
        )
    return matches[0]


def command_lines(*blocks: str) -> list[str]:
    """Return process-level commands from one or more scoped run-step blocks."""
    commands: list[str] = []
    for block in blocks:
        commands.extend(
            line.strip()
            for line in block.splitlines()
            if line.strip().startswith("python ")
        )
    return commands


def step_if_expressions(step: str) -> list[str]:
    """Return every step-level if expression without matching job-level policy."""
    return [
        match.group(1).strip()
        for match in re.finditer(
            r"(?m)^(?:      - |        )if:\s*(.+)$",
            step,
        )
    ]


def step_run_scripts(step: str) -> list[str]:
    """Return normalized run bodies from exactly one scoped step."""
    return [
        "\n".join(line.strip() for line in script.strip().splitlines())
        for _, script in workflow_run_scripts(step)
    ]


def reproduction_lines(block: str, prefix: str) -> list[str]:
    """Return ordered, normalized shell lines for one reproduction operation."""
    return [
        line.strip()
        for line in block.splitlines()
        if line.strip().startswith(prefix)
    ]


class WorkflowSecurityTests(unittest.TestCase):
    def assert_required_job_is_fail_closed(self, job: str) -> None:
        self.assertNotRegex(
            job,
            r"(?m)^\s+(?:-\s+)?"
            r"(?:continue-on-error|\"continue-on-error\"|'continue-on-error')\s*:",
        )
        self.assertNotIn("|| true", job)

    def assert_reproduction_is_exact(
        self,
        block: str,
        rows: list[tuple[str, str, str]],
    ) -> None:
        self.assertEqual(
            reproduction_lines(block, "cp "),
            [
                f'cp {committed} "$tmp/{temporary}"'
                for committed, temporary, _ in rows
            ],
        )
        compile_flags = " ".join(LOCK_COMPILE_FLAGS)
        self.assertEqual(
            reproduction_lines(block, "python -m piptools compile "),
            [
                "python -m piptools compile "
                f'{compile_flags} --output-file="$tmp/{temporary}" {direct_input}'
                for _, temporary, direct_input in rows
            ],
        )
        self.assertEqual(
            reproduction_lines(block, "cmp "),
            [
                f'cmp "$tmp/{temporary}" {committed}'
                for committed, temporary, _ in rows
            ],
        )

    def test_tests_workflow_event_policy_is_scoped_and_exact(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        events = top_level_mapping_block(text, "on")
        jobs = top_level_mapping_block(text, "jobs")
        push = mapping_block(events, "push", indent=2)
        pull_request = mapping_block(events, "pull_request", indent=2)
        paths_ignore = mapping_block(push, "paths-ignore", indent=4)
        permissions = top_level_mapping_block(text, "permissions")
        concurrency = top_level_mapping_block(text, "concurrency")

        self.assertEqual(direct_mapping_keys(text, 0), TOP_LEVEL_WORKFLOW_KEYS)
        self.assertEqual(direct_mapping_keys(jobs, 2), JOB_KEYS)
        self.assertEqual(events.splitlines(), EVENT_POLICY_LINES)
        self.assertIn("    branches: [main]", push)
        self.assertEqual(
            paths_ignore.splitlines(),
            [f'      - "{path}"' for path in GENERATED_FEED_IGNORES],
        )
        self.assertEqual(pull_request.strip(), "")
        self.assertEqual(permissions.splitlines(), ["  contents: read"])
        self.assertEqual(concurrency.splitlines(), CONCURRENCY_LINES)
        for covered_path in ("feed/inbox/**", "feed/schema/**", "feed/README.md"):
            self.assertNotIn(covered_path, paths_ignore)

    def test_tests_workflow_frontend_matrix_and_steps_are_scoped(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        frontend = mapping_block(jobs, "frontend", indent=2)
        strategy = mapping_block(frontend, "strategy", indent=4)
        defaults = mapping_block(frontend, "defaults", indent=4)
        env = mapping_block(frontend, "env", indent=4)
        steps = normalized_step_blocks(frontend)

        self.assert_required_job_is_fail_closed(frontend)
        self.assertEqual(direct_mapping_keys(frontend, 4), FRONTEND_JOB_KEYS)
        self.assertEqual(strategy.splitlines(), FRONTEND_STRATEGY_LINES)
        self.assertEqual(defaults.splitlines(), FRONTEND_DEFAULTS_LINES)
        self.assertEqual(env.splitlines(), FRONTEND_ENV_LINES)
        self.assertEqual(steps, FRONTEND_STEP_BLOCKS)
        self.assertEqual(
            re.findall(
                r"(?m)^          - profile: ([^\n]+)\n"
                r"            base_path: ([^\n]+)$",
                frontend,
            ),
            [("static", "/stock-analysis"), ("server", '""')],
        )
        self.assertIn("      NEXT_PUBLIC_BASE_PATH: ${{ matrix.base_path }}", frontend)

        checkout = only_block_containing(steps, "uses: actions/checkout@v7")
        self.assertIn("persist-credentials: false", checkout)
        setup_node = only_block_containing(steps, "uses: actions/setup-node@v7")
        self.assertIn("node-version-file: .node-version", setup_node)
        self.assertIn("cache-dependency-path: frontend/package-lock.json", setup_node)

        versions = only_block_containing(steps, "name: Verify exact Node and npm")
        self.assertIn('test "$(node --version)" = "v20.20.2"', versions)
        self.assertIn('test "$(npm --version)" = "10.8.2"', versions)
        common_steps = [checkout, setup_node, versions]
        for command in (
            "npm ci",
            "npm run lint",
            "npm run typecheck",
            "npm run test:scripts",
        ):
            command_step = only_block_containing(steps, f"- run: {command}")
            self.assertRegex(
                command_step,
                rf"(?m)^      - run: {re.escape(command)}$",
            )
            common_steps.append(command_step)
        for step in common_steps:
            self.assertEqual(step_if_expressions(step), [], step)

        for profile, command in (
            ("static", "npm run build:static"),
            ("static", "npm run smoke:static"),
            ("server", "npm run build:server"),
            ("server", "npm run smoke:server"),
        ):
            profile_step = only_block_containing(steps, f"run: {command}")
            self.assertEqual(
                step_if_expressions(profile_step),
                [f"matrix.profile == '{profile}'"],
                (profile, command),
            )
            self.assertEqual(step_run_scripts(profile_step), [command])

    def test_tests_workflow_python_matrix_locks_and_entrypoints_are_scoped(
        self,
    ) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        python_job = mapping_block(jobs, "python", indent=2)
        strategy = mapping_block(python_job, "strategy", indent=4)
        env = mapping_block(python_job, "env", indent=4)
        steps = normalized_step_blocks(python_job)

        self.assert_required_job_is_fail_closed(python_job)
        self.assertEqual(direct_mapping_keys(python_job, 4), PYTHON_JOB_KEYS)
        self.assertEqual(strategy.splitlines(), PYTHON_STRATEGY_LINES)
        self.assertEqual(env.splitlines(), PYTHON_ENV_LINES)
        self.assertEqual(steps, PYTHON_STEP_BLOCKS)
        python_rows = re.findall(
            r'(?m)^          - python_version: "([^"]+)"\n'
            r"            lockfile: ([^\n]+)$",
            python_job,
        )
        self.assertEqual(
            python_rows,
            [
                ("3.11.15", "requirements/ci-py311.txt"),
                ("3.12.13", "requirements/ci-py312.txt"),
            ],
        )
        checkout = only_block_containing(steps, "uses: actions/checkout@v7")
        self.assertIn("persist-credentials: false", checkout)
        setup_python = only_block_containing(steps, "uses: actions/setup-python@v6")
        self.assertIn("python-version: ${{ matrix.python_version }}", setup_python)
        install = only_block_containing(
            steps,
            'python -m pip install --require-hashes -r "${{ matrix.lockfile }}"',
        )
        self.assertNotIn("--upgrade", install)
        self.assertEqual(
            step_run_scripts(install),
            ['python -m pip install --require-hashes -r "${{ matrix.lockfile }}"'],
        )
        pip_check = only_block_containing(steps, "run: python -m pip check")
        self.assertEqual(step_run_scripts(pip_check), ["python -m pip check"])

        reproduce_311 = only_block_containing(
            steps, "name: Reproduce Python 3.11 locks from direct inputs"
        )
        reproduce_312 = only_block_containing(
            steps, "name: Reproduce Python 3.12 lock from direct inputs"
        )
        self.assertEqual(
            step_if_expressions(reproduce_311),
            ["matrix.python_version == '3.11.15'"],
        )
        self.assertEqual(
            step_if_expressions(reproduce_312),
            ["matrix.python_version == '3.12.13'"],
        )
        self.assert_reproduction_is_exact(reproduce_311, PY311_LOCK_REPRODUCTIONS)
        self.assert_reproduction_is_exact(reproduce_312, PY312_LOCK_REPRODUCTIONS)
        for block, expected_compile_count in (
            (reproduce_311, 6),
            (reproduce_312, 1),
        ):
            compile_lines = [
                line.strip()
                for line in block.splitlines()
                if "piptools compile" in line
            ]
            self.assertEqual(len(compile_lines), expected_compile_count)
            self.assertNotIn("--upgrade", block)
            self.assertLess(block.index("\n          cp "), block.index("piptools compile"))
            for compile_line in compile_lines:
                for flag in LOCK_COMPILE_FLAGS:
                    self.assertIn(flag, compile_line)

        backend_tests = only_block_containing(
            steps, "name: Backend HTTP and data-layer tests"
        )
        automation_tests = only_block_containing(
            steps, "name: Automation and feed-validation tests"
        )
        self.assertEqual(
            re.findall(
                r"(?m)^        working-directory:\s*(\S.*?)\s*$",
                backend_tests,
            ),
            ["backend"],
        )
        for step in (
            checkout,
            setup_python,
            install,
            pip_check,
            backend_tests,
            automation_tests,
        ):
            self.assertEqual(step_if_expressions(step), [], step)
        self.assertEqual(
            command_lines(backend_tests, automation_tests),
            COMMON_PYTHON_ENTRYPOINTS,
        )
        primary_locks = only_block_containing(
            steps, "name: Primary-runtime lock consistency"
        )
        self.assertEqual(
            step_if_expressions(primary_locks),
            ["matrix.python_version == '3.11.15'"],
        )
        primary_commands = command_lines(primary_locks)
        self.assertEqual(
            primary_commands,
            [
                "python scripts/tests/test_check_lock_consistency.py",
                "python scripts/check_lock_consistency.py --root .",
            ],
        )
        expanded_process_entrypoints = (
            len(python_rows)
            * len(command_lines(backend_tests, automation_tests))
            + len(primary_commands)
        )
        self.assertEqual(expanded_process_entrypoints, 22)

    def test_tests_workflow_stable_gate_requires_both_matrices(self) -> None:
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        jobs = top_level_mapping_block(text, "jobs")
        gate = mapping_block(jobs, "gate", indent=2)
        steps = normalized_step_blocks(gate)

        self.assert_required_job_is_fail_closed(gate)
        self.assertEqual(direct_mapping_keys(gate, 4), GATE_JOB_KEYS)
        self.assertEqual(steps, GATE_STEP_BLOCKS)
        self.assertEqual(
            re.findall(r"(?m)^    name:\s*(.+)$", gate),
            ["Tests (单元测试闸门)"],
        )
        self.assertEqual(
            re.findall(r"(?m)^    if:\s*(.+)$", gate),
            ["${{ always() }}"],
        )
        self.assertEqual(
            re.findall(r"(?m)^    needs:\s*(.+)$", gate),
            ["[frontend, python]"],
        )
        requirement = only_block_containing(
            steps, "name: Require every runtime matrix to pass"
        )
        self.assertEqual(step_if_expressions(requirement), [], requirement)
        self.assertIn("FRONTEND_RESULT: ${{ needs.frontend.result }}", requirement)
        self.assertIn("PYTHON_RESULT: ${{ needs.python.result }}", requirement)
        self.assertIn('test "$FRONTEND_RESULT" = success', requirement)
        self.assertIn('test "$PYTHON_RESULT" = success', requirement)
        self.assertEqual(
            step_run_scripts(requirement),
            [
                'test "$FRONTEND_RESULT" = success\n'
                'test "$PYTHON_RESULT" = success'
            ],
        )

    def test_required_job_fail_closed_recognizes_quoted_keys(self) -> None:
        for line in (
            "    continue-on-error: false",
            '    "continue-on-error": false',
            "    'continue-on-error': false",
            '      - "continue-on-error": false',
        ):
            with self.subTest(line=line):
                with self.assertRaises(AssertionError):
                    self.assert_required_job_is_fail_closed(line)

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

    def test_dependabot_serializes_all_runs_with_a_top_level_queue(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")

        concurrency = top_level_mapping_block(workflow, "concurrency")

        self.assertIn("  group: dependabot-automerge-${{ github.repository }}", concurrency)
        self.assertIn("  queue: max", concurrency)
        self.assertNotRegex(workflow, r"(?m)^\s*cancel-in-progress:\s*true\s*$")

    def test_dependabot_sweep_reconciles_every_open_dependabot_pr(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        sweep = workflow[workflow.index("  sweep:") :]
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
        self.assertIn("--author 'app/dependabot' --state open", sweep)
        self.assertIn("--limit 1000", sweep)
        self.assertIn("--json number,title", sweep)
        self.assertNotIn("--label", sweep)
        self.assertNotIn("labels", sweep)
        self.assertNotIn("eligibility_label", sweep)
        self.assertNotIn("continue", sweep)
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

    def test_dependabot_stale_event_guards_precede_all_eligibility_writes(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "dependabot-automerge.yml"
        ).read_text(encoding="utf-8")
        query = "--json headRefOid --jq '.headRefOid // empty'"
        mismatch = (
            'if [ "$head_query_failed" -ne 0 ] || [ -z "$current_head" ] '
            '|| [ "$current_head" != "$HEAD_SHA" ]; then'
        )
        self.assertEqual(workflow.count(query), 2)
        self.assertEqual(workflow.count(mismatch), 2)

        cleanup = workflow.index("- name: 清理旧资格并撤销 auto-merge")
        cleanup_guard = workflow.index(mismatch, cleanup)
        cleanup_revoke = workflow.index(
            "from dependabot_merge_gate import revoke_auto_merge",
            cleanup_guard,
        )
        cleanup_exit = workflow.index("exit 1", cleanup_revoke)
        remove_label = workflow.index('--remove-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        pending = workflow.index("-f state=pending")
        eligibility = workflow.index("- name: 根据 metadata 同步 auto-merge 资格标签")
        eligibility_guard = workflow.index(mismatch, eligibility)
        eligibility_revoke = workflow.index(
            "from dependabot_merge_gate import revoke_auto_merge",
            eligibility_guard,
        )
        eligibility_exit = workflow.index("exit 1", eligibility_revoke)
        add_label = workflow.index('--add-label "$AUTOMERGE_ELIGIBLE_LABEL"')
        success = workflow.index("-f state=success")

        self.assertLess(cleanup, cleanup_guard)
        self.assertLess(cleanup_guard, cleanup_revoke)
        self.assertLess(cleanup_revoke, cleanup_exit)
        self.assertLess(cleanup_exit, remove_label)
        self.assertLess(cleanup_exit, pending)
        self.assertLess(eligibility, eligibility_guard)
        self.assertLess(eligibility_guard, eligibility_revoke)
        self.assertLess(eligibility_revoke, eligibility_exit)
        self.assertLess(eligibility_exit, add_label)
        self.assertLess(eligibility_exit, success)

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
        revoke = workflow.index("revoke_auto_merge(", remove_label)
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
