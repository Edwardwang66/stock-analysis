from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
FENCE_LINE_RE = re.compile(r"^ {0,12}(`{3,}|~{3,})(.*)$")
LIST_ITEM_RE = re.compile(r"^( *)(?:[-+*]|\d+[.)])[ \t]+")
INLINE_CODE_RE = re.compile(r"(`+)([^`\n]+?)\1")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAINTAINED_STATUSES = {
    "Current",
    "Current compatibility page",
    "Accepted",
    "Accepted implementation plan",
    "Accepted; target architecture, not current implementation",
}
HISTORICAL_STATUS = "Historical research snapshot; not maintained"
ARCHIVED_STATUS = "Archived; not current implementation guidance"
ENV_PATTERNS = (
    re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),
    re.compile(r"os\.(?:getenv|environ\.get)\([\"']([A-Z][A-Z0-9_]*)[\"']"),
    re.compile(r"os\.environ\[[\"']([A-Z][A-Z0-9_]*)[\"']\]"),
    re.compile(r"\$\{\{\s*(?:vars|secrets)\.([A-Z][A-Z0-9_]*)\s*\}\}"),
)
INDIRECT_ENV_RE = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*["\']([A-Z][A-Z0-9_]*)["\']', re.MULTILINE)
SHELL_PLATFORM_ENV_RE = re.compile(
    r"\$(?:\{)?((?:GITHUB|RUNNER)_[A-Z][A-Z0-9_]*)(?:\})?"
)
SIMPLE_INLINE_ENV_RE = re.compile(
    r"^([A-Z][A-Z0-9_]*)=[A-Za-z0-9_./:+,@%-]+$"
)
DEPLOYMENT_ENV_KEY_RE = re.compile(
    r"(?m)^\s*-\s+key:\s*([A-Z][A-Z0-9_]*)\s*$"
)
DOCKER_ENV_RE = re.compile(r"(?m)^ENV\s+([A-Z][A-Z0-9_]*)=")
DOCKER_ENV_FLAG_RE = re.compile(
    r"(?:^|[ \t])(?:--env|-e)[ \t]+([A-Z][A-Z0-9_]*)(?:=|\b)"
)
JS_ENV_BLOCK_RE = re.compile(r"\benv\s*:\s*\{(.*?)\}", re.DOTALL)
JS_ENV_OBJECT_KEY_RE = re.compile(
    r"(?:^|,)\s*([A-Z][A-Z0-9_]*)\s*:", re.MULTILINE
)
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
JOB_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "check_all_tracked_markdown",
        "archive_date",
        "runtime_contract",
        "maintained_documents",
        "historical_documents",
        "archived_documents",
        "classification_exemptions",
        "environment_document",
        "platform_environment_names",
        "workflow_inventory_document",
        "verified_commands",
    }
)
RUNTIME_KEYS = frozenset(
    {"node", "npm", "python_primary", "python_compatibility"}
)
EXPECTED_ARCHIVE_DATE = "2026-07-24"
EXPECTED_RUNTIME_CONTRACT = {
    "node": "20.20.2",
    "npm": "10.8.2",
    "python_primary": "3.11.15",
    "python_compatibility": ["3.12.13"],
}
ENTRYPOINT_COMMAND_KEYS = frozenset(
    {"document", "cwd", "command", "kind", "runtime"}
)
CI_COMMAND_KEYS = ENTRYPOINT_COMMAND_KEYS | {"workflow", "job"}


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message} [{self.code}]"


class ConfigError(ValueError):
    """Fail-closed documentation manifest error."""


def reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_config_constant(value: str) -> None:
    raise ConfigError(f"non-standard JSON constant is forbidden: {value}")


def require_exact_keys(value: Any, expected: frozenset[str], label: str) -> dict:
    if type(value) is not dict:
        raise ConfigError(f"{label} must be an object")
    actual = frozenset(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ConfigError(f"{label} keys mismatch; missing={missing}, unknown={unknown}")
    return value


def require_unique_strings(value: Any, label: str) -> list[str]:
    if type(value) is not list:
        raise ConfigError(f"{label} must be a list")
    if any(type(item) is not str or not item for item in value):
        raise ConfigError(f"{label} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ConfigError(f"{label} contains duplicates")
    return value


def canonical_repo_path(
    root: Path,
    raw: Any,
    label: str,
    *,
    suffix: str | None = None,
    directory: bool = False,
) -> Path:
    if type(raw) is not str or not raw or "\\" in raw:
        raise ConfigError(f"{label} must be non-empty POSIX-relative text")
    if raw == ".":
        if not directory:
            raise ConfigError(f"{label} must name a file, not the repository root")
        try:
            resolved_root = root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ConfigError("repository root is unavailable") from exc
        if not resolved_root.is_dir():
            raise ConfigError("repository root is not a directory")
        return root
    pure = PurePosixPath(raw)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
    ):
        raise ConfigError(f"{label} is not a canonical repository-relative path: {raw}")
    if suffix is not None and pure.suffix != suffix:
        raise ConfigError(f"{label} must end in {suffix}: {raw}")
    candidate = root.joinpath(*pure.parts)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ConfigError(f"{label} does not resolve: {raw}") from exc
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ConfigError(f"{label} escapes the repository: {raw}")
    if directory and not resolved.is_dir():
        raise ConfigError(f"{label} is not a directory: {raw}")
    if not directory and not resolved.is_file():
        raise ConfigError(f"{label} is not a regular file: {raw}")
    return candidate


def validate_exemption(root: Path, raw: str) -> None:
    if (
        "\\" in raw
        or "**" in raw
        or "?" in raw
        or "[" in raw
        or "]" in raw
        or raw.count("*") != 1
    ):
        raise ConfigError(f"invalid classification exemption: {raw}")
    pure = PurePosixPath(raw)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
        or pure.name != "*.md"
    ):
        raise ConfigError(f"invalid classification exemption: {raw}")
    parent = pure.parent.as_posix()
    if parent == ".":
        if not root.resolve(strict=True).is_dir():
            raise ConfigError("repository root is unavailable")
    else:
        canonical_repo_path(root, parent, "classification exemption parent", directory=True)


def validate_command_contract(
    root: Path,
    maintained: set[str],
    item: Any,
) -> dict:
    if type(item) is not dict:
        raise ConfigError("verified command must be an object")
    kind = item.get("kind")
    if type(kind) is not str:
        raise ConfigError("verified command kind must be a string")
    expected = CI_COMMAND_KEYS if kind == "ci" else ENTRYPOINT_COMMAND_KEYS
    if kind not in {"ci", "entrypoint"}:
        raise ConfigError(f"invalid command kind: {kind}")
    require_exact_keys(item, expected, "verified command")
    runtime = item["runtime"]
    if type(runtime) is not str:
        raise ConfigError("verified command runtime must be a string")
    if runtime not in {"node", "python"}:
        raise ConfigError(f"invalid command runtime: {runtime}")
    document = item["document"]
    canonical_repo_path(root, document, "command document", suffix=".md")
    if document not in maintained:
        raise ConfigError(f"command document is not maintained: {document}")
    canonical_repo_path(root, item["cwd"], "command cwd", directory=True)
    command = item["command"]
    if type(command) is not str or not command or "\n" in command or "\r" in command:
        raise ConfigError("verified command must be one non-empty line")
    if "$(" in command or "`" in command:
        raise ConfigError(f"verified command contains command substitution: {command}")
    try:
        lexer = shlex.shlex(
            command,
            posix=True,
            punctuation_chars=";&|<>()",
        )
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        raise ConfigError(f"verified command is not shell-parseable: {command}") from exc
    if not tokens or any(
        token and all(character in ";&|<>()" for character in token)
        for token in tokens
    ):
        raise ConfigError(f"verified command is not one simple process: {command}")
    expected_program = "npm" if runtime == "node" else "python"
    if tokens[0] != expected_program:
        raise ConfigError(
            f"{runtime} command must begin with {expected_program}: {command}"
        )
    if kind == "ci":
        workflow = item["workflow"]
        workflow_path = canonical_repo_path(root, workflow, "command workflow")
        pure = PurePosixPath(workflow)
        if (
            pure.parts[:2] != (".github", "workflows")
            or pure.suffix not in {".yml", ".yaml"}
            or not workflow_path.is_file()
        ):
            raise ConfigError(f"CI workflow is outside .github/workflows: {workflow}")
        job = item["job"]
        if type(job) is not str or JOB_NAME_RE.fullmatch(job) is None:
            raise ConfigError(f"invalid CI job name: {job}")
    return item


def load_config(root: Path, path: Path) -> dict:
    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ConfigError(f"configuration path does not resolve: {path}") from exc
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ConfigError(f"configuration path escapes the repository: {path}")
    try:
        data = json.loads(
            resolved_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_object,
            parse_constant=reject_config_constant,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"configuration is unreadable: {path}") from exc
    data = require_exact_keys(data, TOP_LEVEL_KEYS, "docs verification manifest")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigError("docs verification schema_version must be integer 1")
    if type(data["check_all_tracked_markdown"]) is not bool:
        raise ConfigError("check_all_tracked_markdown must be Boolean")
    archive_date = data["archive_date"]
    if type(archive_date) is not str:
        raise ConfigError("archive_date must be an ISO date string")
    try:
        parsed_date = date.fromisoformat(archive_date)
    except ValueError as exc:
        raise ConfigError("archive_date must be YYYY-MM-DD") from exc
    if parsed_date.isoformat() != archive_date:
        raise ConfigError("archive_date must be canonical YYYY-MM-DD")
    if archive_date != EXPECTED_ARCHIVE_DATE:
        raise ConfigError(
            f"archive_date must equal the Stage 1C archive date "
            f"{EXPECTED_ARCHIVE_DATE}"
        )

    runtime = require_exact_keys(
        data["runtime_contract"], RUNTIME_KEYS, "runtime_contract"
    )
    for name in ("node", "npm", "python_primary"):
        if type(runtime[name]) is not str or VERSION_RE.fullmatch(runtime[name]) is None:
            raise ConfigError(f"runtime_contract.{name} must be an exact patch version")
    compatibility = require_unique_strings(
        runtime["python_compatibility"], "runtime_contract.python_compatibility"
    )
    if not compatibility or any(VERSION_RE.fullmatch(value) is None for value in compatibility):
        raise ConfigError("python_compatibility must contain exact patch versions")
    if runtime["python_primary"] in compatibility:
        raise ConfigError("python primary runtime may not also be compatibility-only")
    if runtime != EXPECTED_RUNTIME_CONTRACT:
        raise ConfigError(
            "runtime_contract must equal the approved exact Node/npm/Python matrix"
        )

    category_names = (
        "maintained_documents",
        "historical_documents",
        "archived_documents",
    )
    categories = {
        name: require_unique_strings(data[name], name) for name in category_names
    }
    for name, values in categories.items():
        for value in values:
            canonical_repo_path(root, value, name, suffix=".md")
    all_category_paths = [value for values in categories.values() for value in values]
    if len(all_category_paths) != len(set(all_category_paths)):
        raise ConfigError("document status arrays must be mutually exclusive")

    exemptions = require_unique_strings(
        data["classification_exemptions"], "classification_exemptions"
    )
    for pattern in exemptions:
        validate_exemption(root, pattern)

    maintained = set(categories["maintained_documents"])
    for name in ("environment_document", "workflow_inventory_document"):
        value = data[name]
        if value is not None:
            canonical_repo_path(root, value, name, suffix=".md")
            if value not in maintained:
                raise ConfigError(f"{name} must name a maintained document")

    environment_names = require_unique_strings(
        data["platform_environment_names"], "platform_environment_names"
    )
    if any(ENV_NAME_RE.fullmatch(value) is None for value in environment_names):
        raise ConfigError("platform_environment_names contains an invalid name")

    commands = data["verified_commands"]
    if type(commands) is not list:
        raise ConfigError("verified_commands must be a list")
    normalized_commands: set[str] = set()
    for item in commands:
        validated = validate_command_contract(root, maintained, item)
        encoded = json.dumps(validated, ensure_ascii=False, sort_keys=True)
        if encoded in normalized_commands:
            raise ConfigError("verified_commands contains a duplicate contract")
        normalized_commands.add(encoded)
    return data


def yaml_without_inline_comment(value: str) -> str:
    single_quoted = False
    double_quoted = False
    index = 0
    while index < len(value):
        character = value[index]
        if single_quoted:
            if character == "'" and index + 1 < len(value) and value[index + 1] == "'":
                index += 2
                continue
            if character == "'":
                single_quoted = False
        elif double_quoted:
            if character == '"' and (
                index == 0 or value[index - 1] != "\\"
            ):
                double_quoted = False
        elif character == "'":
            single_quoted = True
        elif character == '"':
            double_quoted = True
        elif character == "#" and (
            index == 0 or value[index - 1].isspace()
        ):
            return value[:index].rstrip()
        index += 1
    return value.rstrip()


def yaml_structure_line(line: str) -> tuple[int, str] | None:
    indent = len(line) - len(line.lstrip(" "))
    content = yaml_without_inline_comment(line[indent:]).rstrip()
    if not content:
        return None
    return indent, content


def yaml_scalar_text(value: str) -> str:
    value = yaml_without_inline_comment(value).strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
        return value[1:-1]
    return value


def yaml_direct_value(
    lines: list[str],
    start: int,
    end: int,
    indent: int,
    key: str,
) -> tuple[int, str] | None:
    pattern = re.compile(rf"{re.escape(key)}:\s*(.*)")
    for index in range(start, end):
        parsed = yaml_structure_line(lines[index])
        if parsed is None or parsed[0] != indent:
            continue
        match = pattern.fullmatch(parsed[1])
        if match:
            return index, yaml_scalar_text(match.group(1))
    return None


def yaml_block_end(
    lines: list[str],
    start: int,
    end: int,
    parent_indent: int,
) -> int:
    for index in range(start, end):
        parsed = yaml_structure_line(lines[index])
        if parsed is not None and parsed[0] <= parent_indent:
            return index
    return end


def yaml_condition_is_false(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip()
    if normalized.startswith("${{") and normalized.endswith("}}"):
        normalized = normalized[3:-2].strip()
    return normalized.lower() == "false"


def actions_python_matrix(
    lines: list[str],
    job_start: int,
    job_end: int,
) -> list[str]:
    strategy = yaml_direct_value(lines, job_start + 1, job_end, 4, "strategy")
    if strategy is None or strategy[1]:
        return []
    strategy_end = yaml_block_end(lines, strategy[0] + 1, job_end, 4)
    matrix = yaml_direct_value(
        lines, strategy[0] + 1, strategy_end, 6, "matrix"
    )
    if matrix is None or matrix[1]:
        return []
    matrix_end = yaml_block_end(lines, matrix[0] + 1, strategy_end, 6)
    include = yaml_direct_value(
        lines, matrix[0] + 1, matrix_end, 8, "include"
    )
    if include is None or include[1]:
        return []
    include_end = yaml_block_end(lines, include[0] + 1, matrix_end, 8)
    item_starts = [
        index
        for index in range(include[0] + 1, include_end)
        if (
            (parsed := yaml_structure_line(lines[index])) is not None
            and parsed[0] == 10
            and parsed[1].startswith("- ")
        )
    ]
    versions: list[str] = []
    for offset, item_start in enumerate(item_starts):
        item_end = (
            item_starts[offset + 1]
            if offset + 1 < len(item_starts)
            else include_end
        )
        parsed = yaml_structure_line(lines[item_start])
        assert parsed is not None
        opener = parsed[1][2:].strip()
        match = re.fullmatch(r"python_version:\s*(.+)", opener)
        if match:
            versions.append(yaml_scalar_text(match.group(1)))
            continue
        value = yaml_direct_value(
            lines, item_start + 1, item_end, 12, "python_version"
        )
        if value is not None:
            versions.append(value[1])
    return versions


def actions_step_value(
    lines: list[str],
    step_start: int,
    step_end: int,
    key: str,
) -> tuple[int, int, str] | None:
    parsed = yaml_structure_line(lines[step_start])
    assert parsed is not None
    opener = parsed[1][2:].strip()
    match = re.fullmatch(rf"{re.escape(key)}:\s*(.*)", opener)
    if match:
        return step_start, 6, yaml_scalar_text(match.group(1))
    direct = yaml_direct_value(lines, step_start + 1, step_end, 8, key)
    if direct is None:
        return None
    return direct[0], 8, direct[1]


def actions_step_inputs(
    lines: list[str],
    step_start: int,
    step_end: int,
) -> dict[str, str]:
    with_entry = actions_step_value(lines, step_start, step_end, "with")
    if with_entry is None or with_entry[2]:
        return {}
    with_end = yaml_block_end(lines, with_entry[0] + 1, step_end, with_entry[1])
    inputs: dict[str, str] = {}
    for index in range(with_entry[0] + 1, with_end):
        parsed = yaml_structure_line(lines[index])
        if parsed is None or parsed[0] != with_entry[1] + 2:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_-]+):\s*(.*)", parsed[1])
        if match:
            inputs[match.group(1)] = yaml_scalar_text(match.group(2))
    return inputs


def actions_step_run_lines(
    lines: list[str],
    step_start: int,
    step_end: int,
) -> list[str]:
    run_entry = actions_step_value(lines, step_start, step_end, "run")
    if run_entry is None:
        return []
    run_index, run_indent, value = run_entry
    if value[:1] not in {"|", ">"}:
        return [value] if value else []
    result: list[str] = []
    for index in range(run_index + 1, step_end):
        candidate = lines[index]
        stripped = candidate.lstrip(" ")
        indent = len(candidate) - len(stripped)
        if stripped and indent <= run_indent:
            break
        command = candidate.strip()
        if command and not command.startswith("#"):
            result.append(command)
    return result


def actions_steps(
    lines: list[str],
    job_start: int,
    job_end: int,
) -> list[dict[str, Any]]:
    steps_entry = yaml_direct_value(lines, job_start + 1, job_end, 4, "steps")
    if steps_entry is None or steps_entry[1]:
        return []
    steps_end = yaml_block_end(lines, steps_entry[0] + 1, job_end, 4)
    step_starts = [
        index
        for index in range(steps_entry[0] + 1, steps_end)
        if (
            (parsed := yaml_structure_line(lines[index])) is not None
            and parsed[0] == 6
            and parsed[1].startswith("- ")
        )
    ]
    result: list[dict[str, Any]] = []
    for offset, step_start in enumerate(step_starts):
        step_end = (
            step_starts[offset + 1]
            if offset + 1 < len(step_starts)
            else steps_end
        )
        uses_entry = actions_step_value(lines, step_start, step_end, "uses")
        condition_entry = actions_step_value(lines, step_start, step_end, "if")
        result.append(
            {
                "uses": uses_entry[2] if uses_entry is not None else None,
                "with": actions_step_inputs(lines, step_start, step_end),
                "run_lines": actions_step_run_lines(
                    lines, step_start, step_end
                ),
                "disabled": yaml_condition_is_false(
                    condition_entry[2] if condition_entry is not None else None
                ),
            }
        )
    return result


def actions_workflow_jobs(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    jobs_index = next(
        (
            index
            for index, line in enumerate(lines)
            if yaml_structure_line(line) == (0, "jobs:")
        ),
        None,
    )
    if jobs_index is None:
        return []
    jobs_end = yaml_block_end(lines, jobs_index + 1, len(lines), 0)
    job_starts: list[tuple[int, str]] = []
    for index in range(jobs_index + 1, jobs_end):
        parsed = yaml_structure_line(lines[index])
        if parsed is None or parsed[0] != 2:
            continue
        match = re.fullmatch(r"([A-Za-z0-9_-]+):", parsed[1])
        if match:
            job_starts.append((index, match.group(1)))
    result: list[dict[str, Any]] = []
    for offset, (job_start, name) in enumerate(job_starts):
        job_end = (
            job_starts[offset + 1][0]
            if offset + 1 < len(job_starts)
            else jobs_end
        )
        condition = yaml_direct_value(
            lines, job_start + 1, job_end, 4, "if"
        )
        result.append(
            {
                "name": name,
                "disabled": yaml_condition_is_false(
                    condition[1] if condition is not None else None
                ),
                "python_versions": actions_python_matrix(
                    lines, job_start, job_end
                ),
                "steps": actions_steps(lines, job_start, job_end),
            }
        )
    return result


def actions_active_run_lines(jobs: list[dict[str, Any]]) -> list[str]:
    return [
        line
        for job in jobs
        if not job["disabled"]
        for step in job["steps"]
        if not step["disabled"]
        for line in step["run_lines"]
    ]


def check_runtime_contract(root: Path, contract: dict) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    expected_python_matrix = [
        contract["python_primary"],
        *contract["python_compatibility"],
    ]

    def read_text(relative: str) -> str | None:
        try:
            return (root / relative).read_text(encoding="utf-8")
        except OSError:
            errors.append(
                Diagnostic(
                    relative,
                    1,
                    "missing-runtime-contract-source",
                    "runtime contract source is missing or unreadable",
                )
            )
            return None

    node_version = read_text(".node-version")
    if node_version is not None and node_version.strip() != contract["node"]:
        errors.append(
            Diagnostic(
                ".node-version",
                1,
                "node-runtime-drift",
                f"expected exact Node {contract['node']}",
            )
        )
    python_version = read_text(".python-version")
    if (
        python_version is not None
        and python_version.strip() != contract["python_primary"]
    ):
        errors.append(
            Diagnostic(
                ".python-version",
                1,
                "python-runtime-drift",
                f"expected exact primary Python {contract['python_primary']}",
            )
        )

    backend_runtime = read_text("backend/runtime.txt")
    if (
        backend_runtime is not None
        and backend_runtime.strip() != f"python-{contract['python_primary']}"
    ):
        errors.append(
            Diagnostic(
                "backend/runtime.txt",
                1,
                "backend-runtime-drift",
                f"expected python-{contract['python_primary']}",
            )
        )
    dockerfile = read_text("backend/Dockerfile")
    expected_from = f"FROM python:{contract['python_primary']}-slim"
    if dockerfile is not None and re.search(
        rf"(?m)^{re.escape(expected_from)}\s*$", dockerfile
    ) is None:
        errors.append(
            Diagnostic(
                "backend/Dockerfile",
                1,
                "docker-runtime-drift",
                f"expected exact base image declaration {expected_from}",
            )
        )
    render = read_text("render.yaml")
    render_versions = (
        re.findall(
            r'''(?m)^[ \t]*-[ \t]+key:[ \t]*PYTHON_VERSION[ \t]*(?:#.*)?\n'''
            r'''[ \t]+value:[ \t]*["']?([^"'#\s]+)["']?[ \t]*(?:#.*)?$''',
            render,
        )
        if render is not None
        else []
    )
    if render is not None and render_versions != [contract["python_primary"]]:
        errors.append(
            Diagnostic(
                "render.yaml",
                1,
                "render-runtime-drift",
                "Render PYTHON_VERSION must match python_primary exactly",
            )
        )

    package_text = read_text("frontend/package.json")
    if package_text is not None:
        try:
            package = json.loads(
                package_text,
                object_pairs_hook=reject_duplicate_object,
                parse_constant=reject_config_constant,
            )
        except (ConfigError, json.JSONDecodeError) as exc:
            errors.append(
                Diagnostic(
                    "frontend/package.json",
                    1,
                    "invalid-runtime-package-json",
                    str(exc),
                )
            )
        else:
            engines = package.get("engines") if type(package) is dict else None
            package_manager = (
                package.get("packageManager") if type(package) is dict else None
            )
            expected_package_manager = f"npm@{contract['npm']}"
            if (
                package_manager != expected_package_manager
                or type(engines) is not dict
                or engines.get("node") != contract["node"]
                or engines.get("npm") != contract["npm"]
            ):
                errors.append(
                    Diagnostic(
                        "frontend/package.json",
                        1,
                        "package-runtime-drift",
                        "packageManager and engines must match runtime_contract exactly",
                    )
                )

    workflow_text = read_text(".github/workflows/tests.yml")
    if workflow_text is not None:
        workflow_jobs = actions_workflow_jobs(workflow_text)
        run_lines = actions_active_run_lines(workflow_jobs)
        assertions = (
            f'test "$(node --version)" = "v{contract["node"]}"',
            f'test "$(npm --version)" = "{contract["npm"]}"',
        )
        for assertion in assertions:
            if assertion not in run_lines:
                errors.append(
                    Diagnostic(
                        ".github/workflows/tests.yml",
                        1,
                        "workflow-runtime-assertion-drift",
                        f"missing exact assertion: {assertion}",
                    )
                )
        matrix_candidates = [
            job["python_versions"]
            for job in workflow_jobs
            if not job["disabled"] and job["python_versions"]
        ]
        if matrix_candidates != [expected_python_matrix]:
            errors.append(
                Diagnostic(
                    ".github/workflows/tests.yml",
                    1,
                    "python-runtime-matrix-drift",
                    "Python matrix must exactly match primary then compatibility runtimes",
                )
            )

    deploy_text = read_text(".github/workflows/deploy-pages.yml")
    if deploy_text is not None:
        deploy_jobs = actions_workflow_jobs(deploy_text)
        deploy_run_lines = actions_active_run_lines(deploy_jobs)
        required_deploy_assertions = (
            f'test "$(node --version)" = "v{contract["node"]}"',
            f'test "$(npm --version)" = "{contract["npm"]}"',
        )
        for required in required_deploy_assertions:
            if required not in deploy_run_lines:
                errors.append(
                    Diagnostic(
                        ".github/workflows/deploy-pages.yml",
                        1,
                        "deployment-runtime-drift",
                        f"missing exact runtime contract line: {required}",
                    )
                )

    for workflow in workflow_files(root):
        try:
            text = workflow.read_text(encoding="utf-8")
        except OSError:
            errors.append(
                Diagnostic(
                    workflow.relative_to(root).as_posix(),
                    1,
                    "unreadable-workflow-runtime",
                    "tracked workflow is unreadable",
                )
            )
            continue
        for job in actions_workflow_jobs(text):
            if job["disabled"]:
                continue
            for step in job["steps"]:
                if step["disabled"] or step["uses"] is None:
                    continue
                action = step["uses"].split("@", 1)[0]
                inputs = step["with"]
                if action == "actions/setup-python":
                    allowed = (
                        inputs.get("python-version-file")
                        in {".python-version", "trusted/.python-version"}
                        or (
                            workflow.name == "tests.yml"
                            and inputs.get("python-version")
                            == "${{ matrix.python_version }}"
                            and job["python_versions"]
                            == expected_python_matrix
                        )
                    )
                    if not allowed:
                        errors.append(
                            Diagnostic(
                                workflow.relative_to(root).as_posix(),
                                1,
                                "workflow-python-runtime-drift",
                                "setup-python must use the repository pin, trusted checkout pin, or exact tested matrix",
                            )
                        )
                elif (
                    action == "actions/setup-node"
                    and inputs.get("node-version-file") != ".node-version"
                ):
                    errors.append(
                        Diagnostic(
                            workflow.relative_to(root).as_posix(),
                            1,
                            "workflow-node-runtime-drift",
                            "setup-node must use the repository .node-version pin",
                        )
                    )
    return errors


def github_slug(text: str) -> str:
    value = re.sub(r"<[^>]+>", "", text).strip().lower()
    value = re.sub(r"[^\w\-\u4e00-\u9fff ]", "", value)
    return re.sub(r"\s", "-", value)


def heading_slugs(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    result: set[str] = set()
    text = mask_fenced_code(path.read_text(encoding="utf-8"))
    heading_text = INLINE_CODE_RE.sub(lambda match: match.group(2).strip(), text)
    for heading in HEADING_RE.findall(heading_text):
        base = github_slug(heading)
        suffix = counts.get(base, 0)
        counts[base] = suffix + 1
        result.add(base if suffix == 0 else f"{base}-{suffix}")
    return result


def mask_fenced_code(text: str) -> str:
    result: list[str] = []
    open_character: str | None = None
    minimum_length = 0
    container_indent = 0
    active_list_indents: list[int] = []
    consecutive_blank_lines = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        newline = line[len(body):]
        match = FENCE_LINE_RE.fullmatch(body)
        if open_character is None:
            leading_indent = len(body) - len(body.lstrip(" "))
            list_match = LIST_ITEM_RE.match(body)
            parent_candidates = [
                indent for indent in active_list_indents if indent <= leading_indent
            ]
            parent_indent = max(parent_candidates, default=0)
            list_marker_is_structural = bool(
                list_match and leading_indent - parent_indent <= 3
            )
            if not body.strip():
                consecutive_blank_lines += 1
                if consecutive_blank_lines >= 2:
                    active_list_indents.clear()
            elif list_marker_is_structural:
                consecutive_blank_lines = 0
                content_indent = list_match.end()
                while active_list_indents and active_list_indents[-1] >= content_indent:
                    active_list_indents.pop()
                active_list_indents.append(content_indent)
            else:
                consecutive_blank_lines = 0
                while active_list_indents and leading_indent < active_list_indents[-1]:
                    active_list_indents.pop()
            eligible_containers = [
                indent for indent in active_list_indents if indent <= leading_indent
            ]
            candidate_container = max(eligible_containers, default=0)
            is_fence_position = leading_indent - candidate_container <= 3
            if match and is_fence_position:
                fence = match.group(1)
                remainder = match.group(2)
                if fence[0] == "`" and "`" in remainder:
                    result.append(line)
                else:
                    open_character = fence[0]
                    minimum_length = len(fence)
                    container_indent = candidate_container
                    result.append(" " * len(body) + newline)
            else:
                result.append(line)
            continue

        result.append(" " * len(body) + newline)
        if match:
            fence = match.group(1)
            remainder = match.group(2)
            if (
                fence[0] == open_character
                and len(fence) >= minimum_length
                and not remainder.strip()
                and len(body) - len(body.lstrip(" ")) - container_indent <= 3
            ):
                open_character = None
                minimum_length = 0
                container_indent = 0
    return "".join(result)


def prose_only(text: str) -> str:
    def mask(match: re.Match[str]) -> str:
        return " " * len(match.group(0))

    return INLINE_CODE_RE.sub(mask, mask_fenced_code(text))


def check_local_links(root: Path, files: list[Path]) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    root = root.resolve()
    for source in files:
        source = source.resolve()
        text = source.read_text(encoding="utf-8")
        prose = prose_only(text)
        for match in LINK_RE.finditer(prose):
            raw = match.group(1).strip()
            if raw.startswith("<") and raw.endswith(">"):
                raw = raw[1:-1]
            parsed = urlsplit(raw)
            if parsed.scheme in {"http", "https", "mailto"} or parsed.netloc:
                continue
            line = text.count("\n", 0, match.start()) + 1
            relative = unquote(parsed.path)
            target = source if not relative else (source.parent / relative)
            target = target.resolve()
            if root not in target.parents and target != root:
                errors.append(Diagnostic(str(source.relative_to(root)), line, "link-outside-root", raw))
                continue
            if not target.exists():
                errors.append(Diagnostic(str(source.relative_to(root)), line, "missing-link-target", raw))
                continue
            fragment = unquote(parsed.fragment)
            if fragment and target.suffix.lower() == ".md" and fragment not in heading_slugs(target):
                errors.append(Diagnostic(str(source.relative_to(root)), line, "missing-link-fragment", f"missing #{fragment} in {relative or source.name}"))
    return errors


def check_metadata(
    root: Path,
    maintained: list[str],
    historical: list[str],
    archived: list[str],
    archive_date: str = EXPECTED_ARCHIVE_DATE,
) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    for relative in maintained:
        path = root / relative
        if not path.exists():
            errors.append(Diagnostic(relative, 1, "missing-maintained-document", "maintained document does not exist"))
            continue
        text = path.read_text(encoding="utf-8")
        fence_masked_lines = mask_fenced_code(text).splitlines()
        header_lines = fence_masked_lines[:12]
        nonblank_lines = [(index, line) for index, line in enumerate(header_lines) if line.strip()]
        title_is_valid = bool(nonblank_lines and re.fullmatch(r"# (?!#)\S.*", nonblank_lines[0][1]))
        if not title_is_valid:
            errors.append(Diagnostic(relative, 1, "invalid-title", "first nonblank line must be an H1 title"))
        status_positions = [(index, line) for index, line in enumerate(header_lines) if line.startswith("> **Status:** ")]
        status_lines = [line for _, line in status_positions]
        if not status_lines:
            errors.append(Diagnostic(relative, 1, "missing-status", "maintained document needs Status"))
        elif len(status_lines) != 1 or status_lines[0].removeprefix("> **Status:** ") not in MAINTAINED_STATUSES:
            errors.append(Diagnostic(relative, 1, "invalid-status", "maintained Status must be one exact allowed value"))
        scope_positions = [(index, line) for index, line in enumerate(header_lines) if line.startswith("> **Scope:** ")]
        scope_lines = [line for _, line in scope_positions]
        if len(scope_lines) != 1 or not scope_lines[0].removeprefix("> **Scope:** ").strip():
            errors.append(Diagnostic(relative, 1, "missing-scope", "maintained document needs Scope"))
        verified_positions = [(index, line) for index, line in enumerate(header_lines) if line.startswith("> **Last verified commit:**")]
        verified_lines = [line for _, line in verified_positions]
        match = re.fullmatch(r"> \*\*Last verified commit:\*\* `([0-9a-f]+)`", verified_lines[0]) if len(verified_lines) == 1 else None
        if match is None or not SHA_RE.fullmatch(match.group(1)):
            errors.append(Diagnostic(relative, 1, "missing-verified-commit", "maintained document needs a Git SHA"))
        if any(
            line.startswith(("> **Status:**", "> **Scope:**", "> **Last verified commit:**"))
            for line in fence_masked_lines[12:]
        ):
            errors.append(Diagnostic(relative, 1, "metadata-not-in-header", "metadata must appear in the first 12 lines"))
        if (
            title_is_valid
            and len(status_positions) == len(scope_positions) == len(verified_positions) == 1
            and not (
                nonblank_lines[0][0]
                < status_positions[0][0]
                < scope_positions[0][0]
                < verified_positions[0][0]
                and verified_positions[0][0] == scope_positions[0][0] + 1
            )
        ):
            errors.append(Diagnostic(relative, 1, "invalid-metadata-order", "header order must be H1, Status, Scope, immediately followed by Last verified commit"))
        if match and SHA_RE.fullmatch(match.group(1)):
            sha = match.group(1)
            exists = subprocess.run(
                ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
            ) if exists.returncode == 0 else None
            if exists.returncode != 0 or ancestor is None or ancestor.returncode != 0:
                errors.append(Diagnostic(relative, 1, "unresolvable-verified-commit", f"{sha} is not a commit reachable from HEAD"))
    for relative, status, status_code, scope_code, is_archived in (
        *[
            (
                value,
                HISTORICAL_STATUS,
                "missing-historical-status",
                "missing-historical-scope",
                False,
            )
            for value in historical
        ],
        *[
            (
                value,
                ARCHIVED_STATUS,
                "missing-archived-status",
                "missing-archived-scope",
                True,
            )
            for value in archived
        ],
    ):
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        fence_masked_lines = mask_fenced_code(text).splitlines()
        header_lines = fence_masked_lines[:12]
        nonblank_lines = [(index, line) for index, line in enumerate(header_lines) if line.strip()]
        title_is_valid = bool(nonblank_lines and re.fullmatch(r"# (?!#)\S.*", nonblank_lines[0][1]))
        if not title_is_valid:
            errors.append(Diagnostic(relative, 1, "invalid-title", "first nonblank line must be an H1 title"))
        status_positions = [(index, line) for index, line in enumerate(header_lines) if line.startswith("> **Status:** ")]
        status_lines = [line for _, line in status_positions]
        if status_lines != [f"> **Status:** {status}"]:
            errors.append(Diagnostic(relative, 1, status_code, f"document needs exact Status: {status}"))
        scope_positions = [(index, line) for index, line in enumerate(header_lines) if line.startswith("> **Scope:** ")]
        scope_lines = [line for _, line in scope_positions]
        if len(scope_lines) != 1 or not scope_lines[0].removeprefix("> **Scope:** ").strip():
            errors.append(Diagnostic(relative, 1, scope_code, "document needs Scope in the first 12 lines"))
        archived_positions = [
            (index, line)
            for index, line in enumerate(header_lines)
            if line.startswith("> **Archived on:**")
        ]
        if is_archived and not archived_positions:
            errors.append(
                Diagnostic(
                    relative,
                    1,
                    "missing-archive-date",
                    f"archived document needs Archived on: {archive_date}",
                )
            )
        elif is_archived and [line for _, line in archived_positions] != [
            f"> **Archived on:** {archive_date}"
        ]:
            errors.append(
                Diagnostic(
                    relative,
                    1,
                    "invalid-archive-date",
                    f"Archived on must equal {archive_date}",
                )
            )
        if any(
            line.startswith(("> **Status:**", "> **Scope:**", "> **Archived on:**"))
            for line in fence_masked_lines[12:]
        ):
            errors.append(Diagnostic(relative, 1, "metadata-not-in-header", "metadata must appear in the first 12 lines"))
        ordered = (
            title_is_valid
            and len(status_positions) == len(scope_positions) == 1
            and nonblank_lines[0][0] < status_positions[0][0] < scope_positions[0][0]
        )
        if is_archived:
            ordered = (
                ordered
                and len(archived_positions) == 1
                and archived_positions[0][0] == scope_positions[0][0] + 1
            )
        if (
            title_is_valid
            and not ordered
        ):
            expected = (
                "H1, Status, Scope, immediately followed by Archived on"
                if is_archived
                else "H1, Status, Scope"
            )
            errors.append(
                Diagnostic(
                    relative,
                    1,
                    "invalid-metadata-order",
                    f"header order must be {expected}",
                )
            )
    return errors


def stamp_documents(root: Path, maintained: list[str], sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("stamp requires a full 40-character Git SHA")
    line = f"> **Last verified commit:** `{sha}`"
    for relative in maintained:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        masked_lines = mask_fenced_code(text).splitlines(keepends=True)
        header_lines = masked_lines[:12]
        scope_indices = [
            index
            for index, candidate in enumerate(header_lines)
            if re.fullmatch(
                r"> \*\*Scope:\*\* .+",
                candidate.rstrip("\r\n"),
            )
        ]
        if len(scope_indices) != 1:
            raise ValueError(
                f"{relative} has no unique Scope line in its header for stamping"
            )
        scope_index = scope_indices[0]
        verified_index = scope_index + 1
        has_verified_line = (
            verified_index < len(header_lines)
            and re.fullmatch(
                r"> \*\*Last verified commit:\*\* `[^`]+`",
                header_lines[verified_index].rstrip("\r\n"),
            )
            is not None
        )
        if has_verified_line:
            index = verified_index
            body = lines[index].rstrip("\r\n")
            lines[index] = line + lines[index][len(body):]
        else:
            index = scope_index
            body = lines[index].rstrip("\r\n")
            newline = lines[index][len(body):] or "\n"
            if not lines[index][len(body):]:
                lines[index] += newline
            lines.insert(index + 1, line + newline)
        path.write_text("".join(lines), encoding="utf-8")


def workflow_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", ".github/workflows"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    directory = PurePosixPath(".github/workflows")
    relative_paths = [
        PurePosixPath(value)
        for value in result.stdout.splitlines()
        if value
    ]
    return [
        root.joinpath(*relative.parts)
        for relative in sorted(relative_paths)
        if relative.parent == directory and relative.suffix in {".yml", ".yaml"}
    ]


def yaml_environment_names(text: str) -> set[str]:
    names: set[str] = set()
    env_indent: int | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped == "env:":
            env_indent = indent
            continue
        if env_indent is None:
            continue
        if stripped and indent <= env_indent:
            env_indent = None
            continue
        match = re.match(r"([A-Z][A-Z0-9_]+):", stripped)
        if match:
            names.add(match.group(1))
    return names


def yaml_run_lines(text: str) -> list[str]:
    """Return executable, non-comment shell lines from YAML run scalars."""
    lines = text.splitlines()
    result: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*?)\s*$", line)
        if not match:
            index += 1
            continue
        base_indent = len(match.group(1))
        value = match.group(2)
        if value not in {"|", "|-", "|+", ">", ">-", ">+"}:
            if value and not value.lstrip().startswith("#"):
                result.append(value.strip())
            index += 1
            continue
        index += 1
        while index < len(lines):
            candidate = lines[index]
            stripped = candidate.lstrip()
            indent = len(candidate) - len(stripped)
            if stripped and indent <= base_indent:
                break
            if stripped and not stripped.startswith("#"):
                result.append(stripped)
            index += 1
    return result


def shell_inline_environment_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        try:
            tokens = shlex.split(line, comments=True, posix=True)
        except ValueError:
            continue
        assignments: list[str] = []
        index = 0
        while index < len(tokens):
            match = SIMPLE_INLINE_ENV_RE.fullmatch(tokens[index])
            if not match:
                break
            assignments.append(match.group(1))
            index += 1
        if assignments and index < len(tokens) and tokens[index] not in {"&&", "||", ";", "|"}:
            names.update(assignments)
    return names


def discover_environment_names(root: Path, platform_names: list[str]) -> set[str]:
    names = set(platform_names)
    paths: list[Path] = []
    for directory_name in ("frontend", "backend", "scripts", "backtest"):
        directory = root / directory_name
        if directory.exists():
            paths.extend(directory.rglob("*"))
    paths.extend(workflow_files(root))
    render_config = root / "render.yaml"
    if render_config.is_file():
        paths.append(render_config)
    for path in paths:
        if not path.is_file() or (
            path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".mjs", ".yml", ".yaml", ".sh"}
            and path.name not in {"Dockerfile", "run-python311"}
        ):
            continue
        if any(part in {"node_modules", ".next", "out", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        is_workflow = path.suffix.lower() in {".yml", ".yaml"}
        patterns = ENV_PATTERNS[-1:] if is_workflow else ENV_PATTERNS[:-1]
        for pattern in patterns:
            names.update(pattern.findall(text))
        if is_workflow:
            names.update(yaml_environment_names(text))
            shell = "\n".join(yaml_run_lines(text)).replace("\\\n", " ")
            names.update(SHELL_PLATFORM_ENV_RE.findall(shell))
            names.update(shell_inline_environment_names(shell))
            names.update(DOCKER_ENV_FLAG_RE.findall(shell))
            if path == render_config:
                names.update(DEPLOYMENT_ENV_KEY_RE.findall(text))
        elif path.name == "Dockerfile":
            names.update(DOCKER_ENV_RE.findall(text))
        elif path.suffix.lower() == ".sh" or path.name == "run-python311":
            shell = text.replace("\\\n", " ")
            names.update(SHELL_PLATFORM_ENV_RE.findall(shell))
            names.update(shell_inline_environment_names(shell))
            names.update(DOCKER_ENV_FLAG_RE.findall(shell))
        else:
            if path.suffix.lower() in {".js", ".mjs", ".ts", ".tsx"}:
                for block in JS_ENV_BLOCK_RE.findall(text):
                    names.update(JS_ENV_OBJECT_KEY_RE.findall(block))
            for constant, value in INDIRECT_ENV_RE.findall(text):
                if f"os.environ.get({constant}" in text or f"process.env[{constant}" in text:
                    names.add(value)
    return names


def check_environment_document(root: Path, names: set[str], relative: str) -> list[Diagnostic]:
    path = root / relative
    if not path.exists():
        return [Diagnostic(relative, 1, "missing-environment-document", "configuration document does not exist")]
    text = path.read_text(encoding="utf-8")
    return [
        Diagnostic(relative, 1, "undocumented-environment", f"`{name}` is used but not documented")
        for name in sorted(names)
        if f"`{name}`" not in text
    ]


def yaml_scalar(value: str) -> str:
    try:
        tokens = shlex.split(value, comments=True, posix=True)
    except ValueError:
        return value.strip().strip("\"'")
    return tokens[0] if len(tokens) == 1 else value.strip().strip("\"'")


def yaml_job_default_working_directory(text: str) -> str:
    defaults_indent: int | None = None
    run_indent: int | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        if defaults_indent is None:
            if stripped == "defaults:":
                defaults_indent = indent
            continue
        if indent <= defaults_indent:
            defaults_indent = None
            run_indent = None
            continue
        if run_indent is None:
            if stripped == "run:":
                run_indent = indent
            continue
        if indent <= run_indent:
            run_indent = None
            continue
        match = re.fullmatch(r"working-directory:\s*(.+)", stripped)
        if match:
            return yaml_scalar(match.group(1))
    return "."


def yaml_step_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks: list[list[str]] = []
    steps_indent: int | None = None
    step_indent: int | None = None
    current: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if steps_indent is None:
            if stripped == "steps:":
                steps_indent = indent
            continue
        if stripped and indent <= steps_indent:
            break
        if stripped.startswith("- "):
            if step_indent is None:
                step_indent = indent
            if indent == step_indent:
                if current:
                    blocks.append(current)
                current = [line]
                continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)
    return ["\n".join(block) for block in blocks]


def yaml_ci_run_records(job_text: str) -> list[tuple[str, str]]:
    default_cwd = yaml_job_default_working_directory(job_text)
    records: list[tuple[str, str]] = []
    for block in yaml_step_blocks(job_text):
        step_cwd = default_cwd
        for line in block.splitlines():
            match = re.fullmatch(r"\s*working-directory:\s*(.+)", line)
            if match:
                step_cwd = yaml_scalar(match.group(1))
                break
        records.extend((command, step_cwd) for command in yaml_run_lines(block))
    return records


def normalize_cwd(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/") or "."


def check_command_contracts(root: Path, contracts: list[dict]) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    package = root / "frontend" / "package.json"
    scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {}) if package.exists() else {}
    for item in contracts:
        document = root / item["document"]
        command = item["command"]
        documented_lines = document.read_text(encoding="utf-8").splitlines() if document.exists() else []
        if command not in documented_lines:
            errors.append(Diagnostic(item["document"], 1, "missing-documented-command", command))
        try:
            tokens = shlex.split(command)
        except ValueError:
            errors.append(Diagnostic(item["document"], 1, "invalid-command", command))
            continue
        if tokens[:2] == ["npm", "run"] and len(tokens) == 3 and tokens[2] not in scripts:
            errors.append(Diagnostic("frontend/package.json", 1, "missing-npm-script", tokens[2]))
        cwd = root / item["cwd"]
        if not cwd.is_dir():
            errors.append(Diagnostic(item["document"], 1, "missing-command-cwd", item["cwd"]))
        if len(tokens) == 2 and tokens[0] == "python" and tokens[1].endswith(".py") and not (cwd / tokens[1]).is_file():
            errors.append(Diagnostic(item["document"], 1, "missing-python-entrypoint", tokens[1]))
        if tokens[:4] == ["python", "-m", "pip", "install"] and "-r" in tokens:
            if "--require-hashes" not in tokens:
                errors.append(Diagnostic(item["document"], 1, "unhashed-pip-install", command))
            requirement_index = tokens.index("-r") + 1
            if requirement_index >= len(tokens) or not (cwd / tokens[requirement_index]).is_file():
                errors.append(Diagnostic(item["document"], 1, "missing-requirements-file", command))
        if item.get("kind") == "ci":
            workflow_name = item.get("workflow")
            job_name = item.get("job")
            if not isinstance(workflow_name, str) or not isinstance(job_name, str):
                errors.append(Diagnostic(item["document"], 1, "missing-ci-location", command))
                continue
            workflow = root / workflow_name
            text = workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
            job_match = re.search(
                rf"(?ms)^  {re.escape(job_name)}:\s*\n(.*?)(?=^  [A-Za-z0-9_-]+:\s*\n|\Z)",
                text,
            )
            job_text = job_match.group(1) if job_match else ""
            records = yaml_ci_run_records(job_text)
            command_cwds = [normalize_cwd(cwd) for candidate, cwd in records if candidate == command]
            if not command_cwds:
                errors.append(Diagnostic(".github/workflows", 1, "command-not-in-ci", command))
            elif normalize_cwd(item["cwd"]) not in command_cwds:
                errors.append(Diagnostic(".github/workflows", 1, "command-wrong-ci-cwd", f"{command} runs in {command_cwds}, not {item['cwd']}"))
    return errors


def workflow_inventory_rows(text: str) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if not cells:
            continue
        match = re.fullmatch(r"`([^`]+\.ya?ml)`", cells[0])
        if match:
            rows.append((match.group(1), cells))
    return rows


def check_workflow_inventory(root: Path, relative: str) -> list[Diagnostic]:
    path = root / relative
    if not path.exists():
        return [Diagnostic(relative, 1, "missing-workflow-inventory", "workflow inventory does not exist")]
    text = path.read_text(encoding="utf-8")
    rows = workflow_inventory_rows(text)
    actual = {workflow.name for workflow in workflow_files(root)}
    counts: dict[str, int] = {}
    errors: list[Diagnostic] = []
    for name, cells in rows:
        counts[name] = counts.get(name, 0) + 1
        if len(cells) != 8 or any(not cell for cell in cells):
            errors.append(Diagnostic(relative, 1, "invalid-workflow-row", f"{name} needs exactly eight non-empty columns"))
        if name not in actual:
            errors.append(Diagnostic(relative, 1, "stale-workflow-row", f"{name} has no workflow file"))
    for name in sorted(actual):
        if counts.get(name, 0) == 0:
            errors.append(Diagnostic(relative, 1, "undocumented-workflow", name))
        elif counts[name] > 1:
            errors.append(Diagnostic(relative, 1, "duplicate-workflow-row", name))
    return errors


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / value for value in result.stdout.splitlines() if value]


def check_classification(root: Path, config: dict, files: list[Path]) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    categories = {
        "maintained": set(config["maintained_documents"]),
        "historical": set(config["historical_documents"]),
        "archived": set(config["archived_documents"]),
    }
    exemptions = config["classification_exemptions"]
    for path in files:
        relative = path.relative_to(root).as_posix()
        memberships = [name for name, values in categories.items() if relative in values]
        relative_path = PurePosixPath(relative)
        exemption_matches = [
            pattern
            for pattern in exemptions
            if relative_path.parent == PurePosixPath(pattern).parent
            and fnmatch.fnmatchcase(relative_path.name, PurePosixPath(pattern).name)
        ]
        if len(memberships) + len(exemption_matches) == 0:
            errors.append(Diagnostic(relative, 1, "unclassified-markdown", "tracked Markdown needs one status or generated-artifact exemption"))
        if len(memberships) + len(exemption_matches) > 1:
            errors.append(Diagnostic(relative, 1, "overlapping-document-status", "tracked Markdown has multiple statuses or exemptions"))
    return errors


def check_repository(root: Path, config_path: Path) -> list[Diagnostic]:
    config = load_config(root, config_path)
    maintained = config["maintained_documents"]
    historical = config["historical_documents"]
    archived = config["archived_documents"]
    tracked = tracked_markdown(root)
    files = (
        tracked
        if config["check_all_tracked_markdown"]
        else [root / value for value in maintained]
    )
    errors = check_local_links(root, files)
    errors.extend(
        check_metadata(
            root,
            maintained,
            historical,
            archived,
            config["archive_date"],
        )
    )
    errors.extend(check_runtime_contract(root, config["runtime_contract"]))
    if config["check_all_tracked_markdown"]:
        errors.extend(check_classification(root, config, tracked))
    environment_document = config["environment_document"]
    if environment_document:
        names = discover_environment_names(
            root, config["platform_environment_names"]
        )
        errors.extend(check_environment_document(root, names, environment_document))
    workflow_document = config["workflow_inventory_document"]
    if workflow_document:
        errors.extend(check_workflow_inventory(root, workflow_document))
    errors.extend(check_command_contracts(root, config["verified_commands"]))
    return sorted(set(errors))


def stamp_current(
    root: Path,
    config_path: Path,
    documents: list[str] | None = None,
) -> str:
    config = load_config(root, config_path)
    maintained = config["maintained_documents"]
    selected = documents if documents else maintained
    unknown = sorted(set(selected) - set(maintained))
    if unknown:
        raise ValueError(f"cannot stamp non-maintained documents: {unknown}")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    stamp_documents(root, selected, sha)
    return sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="docs/verification.json")
    parser.add_argument("--stamp-current", action="store_true")
    parser.add_argument("--document", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        config_path = canonical_repo_path(
            ROOT,
            args.config,
            "--config",
            suffix=".json",
        )
        config = load_config(ROOT, config_path)
        if args.stamp_current:
            print(
                "stamped documentation baseline: "
                f"{stamp_current(ROOT, config_path, args.document or None)}"
            )
            return 0
        errors = check_repository(ROOT, config_path)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"documentation configuration error: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error.render(), file=sys.stderr)
        return 1
    print(
        "docs check passed: "
        f"{len(tracked_markdown(ROOT))} markdown files, "
        f"{len(config['maintained_documents'])} maintained documents, "
        f"{len(workflow_files(ROOT))} workflows, "
        f"{len(config['verified_commands'])} verified commands"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
