# Stage 1C Truth-First Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the repository's stale product narrative with a verifiable, truth-first entry point and a small authoritative documentation system that distinguishes current behavior, accepted target architecture, historical research, and archived pre-refactor plans.

**Architecture:** A machine-readable documentation contract in `docs/verification.json` identifies maintained, historical, and archived documents. A standard-library checker validates metadata, local links, environment-variable coverage, documented commands, and workflow inventory; the root and subsystem READMEs then link to focused current-state pages while compatibility pages preserve old documentation URLs.

**Tech Stack:** Markdown, JSON, Python 3.11 standard library, Docker, Git, GitHub Actions, existing Node 20/npm and Python verification commands from Stage 1B.

## Global Constraints

- Stage 1A security fixes and Stage 1B reproducible CI must be complete before this plan starts. Documentation must describe their merged behavior, not the pre-fix behavior.
- Stage 1B owns public verification command names. This plan must use exactly: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build:static`, `npm run smoke:static`, `npm run build:server`, `npm run smoke:server`, plus the existing direct Python test commands.
- Node.js 20 and Python 3.11 are the documented primary runtimes. Python 3.12 compatibility may be mentioned only if Stage 1B actually verifies it.
- Static and server profiles receive equal documentation prominence, but current differences must remain explicit until Stage 2 proves semantic parity.
- Do not claim that current quote, OHLCV, or analysis results are same-source or semantically identical across profiles.
- Deterministic interactive technical analysis is rule-based. OpenClaw notes and hypothesis-factory content are externally generated AI artifacts delivered through the feed; do not describe the whole product as either “all AI” or “entirely non-LLM.”
- Do not hard-code workflow counts, file counts, refresh counts, transient backtest results, or dated iteration summaries in the root README.
- Do not present TanStack Query, Zustand, Tailwind/shadcn, JWT, Redis, PostgreSQL/TimescaleDB, S3, Celery, RAG, DataGateway, analysis-core, stock_core, or manifest publication as current unless the implementation exists at the Stage 1C baseline.
- Every Current or Accepted document declares `Status`, `Scope`, and `Last verified commit`. Historical and Archived pages declare that they are not current implementation guidance.
- `Last verified commit` is never typed as a placeholder. `python scripts/check_docs.py --stamp-current` obtains the exact value from `git rev-parse HEAD` and inserts it into every maintained document.
- The stamping command runs before documentation commits, so the recorded commit is the code baseline that was reviewed, not a self-referential documentation commit.
- Preserve existing user-facing documentation URLs with short compatibility pages whenever a current file is moved.
- Documentation and checker code use only repository files and recorded facts; the checker and its unit tests perform no network calls. The reused Stage 1B acceptance gates still require Docker image, npm, and PyPI registry access unless those artifacts are already cached.
- Repository-local documentation commands run through `scripts/run-python311`, which uses the exact `python:3.11.15-bookworm` container and the mounted worktree's Git history. Direct `python scripts/check_docs.py` remains the public command for users already inside the pinned Python environment and for CI.
- Frontend and dependency-bearing Python acceptance commands reuse Stage 1B's exact Node 20 and Python container gates; do not claim verification from the host's unrelated Node/Python versions.
- Keep the untracked `AGENTS.md` out of every commit.

---

## File Map

### Create

- `docs/README.md` — documentation status catalog and navigation authority.
- `docs/current-architecture.md` — implemented pre-refactor system and known boundaries.
- `docs/configuration.md` — complete current configuration and secret inventory.
- `docs/deployment-matrix.md` — current static/server deployment variants and limitations.
- `docs/operations/workflows.md` — workflow triggers, permissions, writers, and recovery.
- `docs/data-contracts/feed.md` — current feed artifact families and validation scope.
- `docs/research/index.md` — research and backtest catalog without transient results.
- `docs/rfcs/target-architecture.md` — accepted target summary; explicitly not current.
- `docs/archive/iteration-log.md` — frozen historical iteration log.
- `docs/archive/pre-refactor/roadmap.md` — frozen obsolete roadmap.
- `docs/archive/pre-refactor/deploy-backend.md` — frozen prior backend deployment guide.
- `docs/archive/pre-refactor/data-model-api.md` — frozen mixed current/future API proposal.
- `docs/archive/pre-refactor/endpoints.md` — frozen endpoint probe snapshot.
- `docs/archive/pre-refactor/working-apis.md` — frozen dated upstream probe results.
- `docs/archive/pre-refactor/need-to-fix-2026-06-10.md` — frozen old debt list.
- `docs/archive/pre-refactor/optimization-2026-06.md` — frozen optimization narrative.
- `docs/archive/pre-refactor/positioning.md` — frozen product positioning draft.
- `docs/archive/pre-refactor/cost-estimate-2026-06.md` — frozen dated cost estimate.
- `docs/archive/pre-refactor/self-improving-alpha-loop.md` — frozen prior operations narrative.
- `docs/archive/pre-refactor/backtest-features.md` — frozen pre-refactor feature inventory.
- `backtest/README_tqm.md` — historical TQM study currently occupying `backtest/README.md`.
- `docs/verification.json` — machine-readable documentation contract.
- `scripts/check_docs.py` — standard-library checker and metadata stamper.
- `scripts/run-python311` — repository-local exact-Python wrapper for documentation implementation and verification.
- `scripts/tests/test_check_docs.py` — offline unit and repository integration tests.
- `.github/workflows/docs.yml` — focused documentation contract CI.

### Rewrite

- `README.md` — truth-first product entry point.
- `backend/README.md` — FastAPI subsystem operation, routes, providers, and limits.
- `feed/README.md` — concise feed subsystem entry point.
- `backtest/README.md` — backtest subsystem entry point and research navigation.
- `docs/compliance.md` — current repository policy, licensing caveats, and non-advice scope.
- `docs/openclaw-integration.md` — maintained external-agent contract and trusted submission paths.
- `docs/openclaw-stock-notes.md` — maintained stock-note contract, preserving its active prompt anchor.
- `docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md` — mark the approved program design Accepted.
- `docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md`
- `docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md`
- `docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md`
- Every `routines/*.md` active playbook — add Current metadata and keep links on maintained authorities.

### Move, then replace old path with a compatibility page

- `docs/architecture.md` → `docs/rfcs/target-architecture.md`.
- `docs/iteration-log.md` → `docs/archive/iteration-log.md`.
- `docs/roadmap.md` → `docs/archive/pre-refactor/roadmap.md`.
- `docs/deploy-backend.md` → `docs/archive/pre-refactor/deploy-backend.md`.
- `docs/data-model-api.md` → `docs/archive/pre-refactor/data-model-api.md`.
- `docs/endpoints.md` → `docs/archive/pre-refactor/endpoints.md`.
- `docs/working-apis.md` → `docs/archive/pre-refactor/working-apis.md`.
- `docs/need-to-fix.md` → `docs/archive/pre-refactor/need-to-fix-2026-06-10.md`.
- `docs/optimization-2026-06.md` → `docs/archive/pre-refactor/optimization-2026-06.md`.
- `docs/positioning.md` → `docs/archive/pre-refactor/positioning.md`.
- `docs/cost-estimate.md` → `docs/archive/pre-refactor/cost-estimate-2026-06.md`.
- `docs/self-improving-alpha-loop.md` → `docs/archive/pre-refactor/self-improving-alpha-loop.md`.
- `backtest/FEATURES.md` → `docs/archive/pre-refactor/backtest-features.md`, then recreate `backtest/FEATURES.md` as a compatibility page.

### Preserve in place and classify as historical research

- `docs/hyperliquid-integration.md`.
- `docs/survivorship-bias-data-sources.md`.
- Every `docs/study-*.md` file.
- `backtest/README_binance.md`.
- `backtest/README_crypto.md`.
- `backtest/README_crypto_pipeline.md`.
- `backtest/README_pipeline.md`.
- `backtest/README_statarb.md`.
- `backtest/README_xs.md`.
- `research/ai-agents-skills-market-scan.md`.
- `research/quant-factor-deep-research.md`.

## Shared Interfaces

### Documentation metadata

Maintained documents begin with an H1 title followed, in order, by Status and Scope. The checker requires the H1 to be the first nonblank line and requires `Last verified commit` immediately after Scope for maintained pages. For example, `docs/current-architecture.md` begins with:

```markdown
> **Status:** Current
> **Scope:** Implemented repository architecture before the contract-first refactor.
```

The required `Last verified commit` line is added immediately after Scope by `python scripts/check_docs.py --stamp-current`; the plan never supplies a stand-in value. The only maintained Status values are `Current`, `Current compatibility page`, `Accepted`, `Accepted implementation plan`, and `Accepted; target architecture, not current implementation`. Historical pages use exactly `Historical research snapshot; not maintained`; archived pages use exactly `Archived; not current implementation guidance`. Status and Scope must be literal metadata lines in the first 12 lines; body prose cannot satisfy them. Historical and archived pages do not participate in current-command or environment checks.

### Checker command line

```text
python scripts/check_docs.py
python scripts/check_docs.py --stamp-current
python scripts/check_docs.py --stamp-current --document docs/current-architecture.md
python scripts/check_docs.py --config docs/verification.json
```

- Default mode returns 0 only when the complete contract passes.
- `--stamp-current` runs `git rev-parse HEAD`, inserts or replaces the metadata line for every maintained document, prints the stamped SHA, and performs no other content rewrite. Repeated `--document` arguments restrict stamping to the named maintained slice so focused commits do not dirty older documents.
- All diagnostics use `path:line: message`; validation failure returns 1 and configuration/usage failure returns 2.

### Verification manifest

`docs/verification.json` owns these keys:

```json
{
  "schema_version": 1,
  "check_all_tracked_markdown": true,
  "maintained_documents": [],
  "historical_documents": [],
  "archived_documents": [],
  "classification_exemptions": ["feed/screener/*.md", "frontend/public/feed/screener/*.md"],
  "environment_document": "docs/configuration.md",
  "platform_environment_names": ["PORT", "GITHUB_TOKEN", "GH_TOKEN", "GITHUB_REPOSITORY", "GITHUB_RUN_URL", "GITHUB_OUTPUT", "GITHUB_WORKSPACE", "RUNNER_TEMP"],
  "workflow_inventory_document": "docs/operations/workflows.md",
  "verified_commands": []
}
```

Every verified CI command object contains `document`, `cwd`, `command`, `kind`, `workflow`, and `job`; entrypoint-only commands omit `workflow` and `job`. For CI entries, the checker requires an exact non-comment `run` line inside the named job and proves that the matching step's `working-directory`, or its job-level `defaults.run.working-directory`, equals `cwd`; mere appearance elsewhere is insufficient. The checker requires every tracked Markdown path to appear in exactly one status array or match exactly one declared generated-artifact exemption. Task 7 installs the complete final manifest listed there rather than leaving array population to implementer judgment.

### Controlled Stage 1B acceptance gates

Every later instruction to run the **Node gate** means this exact repository-root command from Stage 1B Task 2 Step 6:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --tmpfs /workspace/frontend/node_modules:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace/frontend \
  node:20.20.2-bookworm-slim \
  sh -lc 'npm ci && npm run lint && npm run typecheck && NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run build:static && NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run smoke:static && env -u NEXT_PUBLIC_BASE_PATH npm run build:server && env -u NEXT_PUBLIC_BASE_PATH npm run smoke:server'
test -f frontend/app/api/quote/route.ts
test -f frontend/app/api/ohlcv/route.ts
git diff --exit-code -- frontend/app/api/quote/route.ts frontend/app/api/ohlcv/route.ts
test -f frontend/.next/BUILD_ID
```

Every later instruction to run the **Python 3.11 gate** means this exact repository-root command from Stage 1B's final acceptance gate. It installs only the committed hash lock into a temporary venv, regenerates all six 3.11 locks to a temporary directory, and executes the complete primary-runtime suite without root-owned worktree artifacts:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15-slim \
  sh -lc '
    set -eu
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backend.txt" backend/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/scripts.txt" scripts/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/winter-pg.txt" scripts/requirements-winter-pg.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backtest.txt" backtest/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/automation.txt" requirements/automation.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py311.txt" requirements/ci.in
    cmp "$tmp/backend.txt" backend/requirements.txt
    cmp "$tmp/scripts.txt" scripts/requirements.txt
    cmp "$tmp/winter-pg.txt" scripts/requirements-winter-pg.txt
    cmp "$tmp/backtest.txt" backtest/requirements.txt
    cmp "$tmp/automation.txt" requirements/automation.txt
    cmp "$tmp/ci-py311.txt" requirements/ci-py311.txt
    (cd backend && /tmp/venv/bin/python tests/test_backend.py)
    (cd backend && /tmp/venv/bin/python tests/test_api.py)
    /tmp/venv/bin/python scripts/tests/test_chan_engine.py
    /tmp/venv/bin/python scripts/tests/test_validate_feed.py
    /tmp/venv/bin/python scripts/tests/test_feed_validation_security.py
    /tmp/venv/bin/python scripts/tests/test_feed_ingress.py
    /tmp/venv/bin/python scripts/tests/test_validate_feed_cli.py
    /tmp/venv/bin/python scripts/tests/test_feed_publication.py
    /tmp/venv/bin/python scripts/tests/test_dependabot_merge_gate.py
    /tmp/venv/bin/python scripts/tests/test_workflow_security.py
  '
```

Do not shorten either gate to host `npm`/`python`, and do not omit the lock-regeneration comparisons when a task says to run a gate.

---

### Task 1: Add the Documentation Contract Checker and Stamping Primitive

**Files:**
- Create: `scripts/check_docs.py`
- Create: `scripts/run-python311`
- Create: `scripts/tests/test_check_docs.py`
- Create: `docs/verification.json`
- Modify: `docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md:1-6`
- Modify: `docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md:1-4`
- Modify: `docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md:1-4`
- Modify: `docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md:1-4`

**Interfaces:**
- Consumes: Git tracked files, Markdown text, `frontend/package.json`, `.github/workflows/*.yml`, `.github/workflows/*.yaml`, and the JSON manifest described above.
- Produces: `check_repository(root, config_path) -> list[Diagnostic]`, `stamp_current(root, config_path) -> str`, and the three CLI invocations in Shared Interfaces.

- [ ] **Step 1: Add and prove the exact local Python wrapper**

Create executable `scripts/run-python311`:

```sh
#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
exec docker run --rm --init \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$repo_root:/workspace" \
  --workdir /workspace \
  python:3.11.15-bookworm "$@"
```

Run:

```bash
chmod +x scripts/run-python311
scripts/run-python311 python -c 'import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version'
scripts/run-python311 git --version
```

Expected: the exact Python assertion passes and Git is available inside the same container, which is required by metadata stamping and ancestor checks.

- [ ] **Step 2: Write failing unit tests for links, metadata, stamping, environments, commands, and workflows**

Create `scripts/tests/test_check_docs.py` with standard-library `unittest`. The tests must construct isolated temporary repositories or call focused pure functions. Include these assertions verbatim in the corresponding tests:

```python
import sys
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_docs import (
    check_classification,
    check_command_contracts,
    check_environment_document,
    check_local_links,
    check_metadata,
    check_workflow_inventory,
    discover_environment_names,
    github_slug,
    stamp_documents,
)


class DocumentationChecks(TestCase):
    def test_missing_local_link_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            errors = check_local_links(root, [page])
            self.assertTrue(any("docs/missing.md" in item.message for item in errors))

    def test_external_link_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("[site](https://example.com/path)\n", encoding="utf-8")
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_fenced_code_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("```markdown\n[example](missing.md)\n```\n", encoding="utf-8")
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_four_backtick_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "````markdown\n```bash\n[example](missing.md)\n```\n````\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_indented_list_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n   ```markdown\n   [example](missing.md)\n   ```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_link_inside_deeply_nested_list_fence_is_ignored(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n     ```markdown\n     [example](missing.md)\n     ```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_local_links(root, [page]), [])

    def test_four_space_indented_backticks_do_not_open_a_fence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "    ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_indented_code_list_marker_does_not_create_list_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "    - code, not a list\n      ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_two_blank_lines_end_inferred_list_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "1. Example\n\n\n    ```\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_backtick_in_backtick_fence_info_does_not_open_a_fence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "```bad`info\n[outside](missing.md)\n```\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_longer_fence_closes_the_code_block(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "```markdown\n[inside](ignored.md)\n````\n[outside](missing.md)\n",
                encoding="utf-8",
            )
            errors = check_local_links(root, [page])
            self.assertTrue(any("missing.md" in item.message for item in errors))

    def test_missing_heading_fragment_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text("[section](guide.md#absent)\n", encoding="utf-8")
            target.write_text("# Present\n", encoding="utf-8")
            errors = check_local_links(root, [page, target])
            self.assertTrue(any("#absent" in item.message for item in errors))

    def test_heading_inside_fenced_code_is_not_an_anchor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text("[fake](guide.md#fake)\n", encoding="utf-8")
            target.write_text("```markdown\n# Fake\n```\n# Real\n", encoding="utf-8")
            errors = check_local_links(root, [page, target])
            self.assertTrue(any("#fake" in item.message for item in errors))

    def test_inline_code_text_is_preserved_in_heading_anchor(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            target = root / "guide.md"
            page.write_text(
                "[role](guide.md#1-residual-analyst--残差)\n", encoding="utf-8"
            )
            target.write_text(
                "## 1. `residual-analyst` — 残差\n", encoding="utf-8"
            )
            self.assertEqual(check_local_links(root, [page, target]), [])

    def test_maintained_document_requires_all_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text("# Project\n\n> **Status:** Current\n", encoding="utf-8")
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertEqual({item.code for item in errors}, {"missing-scope", "missing-verified-commit"})

    def test_metadata_requires_an_h1_as_the_first_nonblank_line(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-title" for item in errors))

    def test_metadata_requires_canonical_header_order(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Scope:** Test.\n> **Status:** Current\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-metadata-order" for item in errors))

    def test_verified_commit_must_immediately_follow_scope(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                "Intervening prose.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-metadata-order" for item in errors))

    def test_stamping_uses_exact_git_sha_argument(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test repository.\n",
                encoding="utf-8",
            )
            sha = "1" * 40
            stamp_documents(root, ["README.md"], sha)
            self.assertIn(f"> **Last verified commit:** `{sha}`", page.read_text(encoding="utf-8"))

    def test_metadata_sha_must_resolve_to_an_ancestor_commit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'f' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(
                any(item.code == "unresolvable-verified-commit" for item in errors)
            )

    def test_existing_non_ancestor_commit_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Docs Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "docs@example.test"], cwd=root, check=True)
            (root / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)
            tree = subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            unrelated = subprocess.run(
                ["git", "commit-tree", tree],
                cwd=root,
                check=True,
                input="unrelated\n",
                capture_output=True,
                text=True,
            ).stdout.strip()
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{unrelated}`\n",
                encoding="utf-8",
            )

            errors = check_metadata(root, ["README.md"], [], [])

            self.assertTrue(
                any(item.code == "unresolvable-verified-commit" for item in errors)
            )

    def test_metadata_must_be_in_document_header(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n" + "\n" * 15
                + "> **Status:** Current\n> **Scope:** Late.\n"
                + f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "metadata-not-in-header" for item in errors))

    def test_metadata_example_inside_fence_is_not_late_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n"
                + "context\n" * 10
                + "```markdown\n> **Status:** Current\n> **Scope:** Example.\n```\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertFalse(any(item.code == "metadata-not-in-header" for item in errors))

    def test_maintained_status_must_be_an_exact_allowed_header_value(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "README.md"
            page.write_text(
                "# Project\n\n> **Status:** Current-ish\n> **Scope:** Test.\n"
                f"> **Last verified commit:** `{'1' * 40}`\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, ["README.md"], [], [])
            self.assertTrue(any(item.code == "invalid-status" for item in errors))

    def test_historical_and_archived_words_in_body_do_not_count_as_metadata(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical = root / "historical.md"
            archived = root / "archived.md"
            historical.write_text(
                "# Old study\n\nThis body discusses Historical results.\n",
                encoding="utf-8",
            )
            archived.write_text(
                "# Old plan\n\nThis body says it was Archived.\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, [], ["historical.md"], ["archived.md"])
            self.assertTrue(any(item.code == "missing-historical-status" for item in errors))
            self.assertTrue(any(item.code == "missing-archived-status" for item in errors))

    def test_conflicting_historical_status_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "historical.md"
            page.write_text(
                "# Study\n\n"
                "> **Status:** Historical research snapshot; not maintained\n"
                "> **Status:** Current\n"
                "> **Scope:** Test.\n",
                encoding="utf-8",
            )
            errors = check_metadata(root, [], ["historical.md"], [])
            self.assertTrue(any(item.code == "missing-historical-status" for item in errors))

    def test_unknown_environment_name_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "docs" / "configuration.md"
            doc.parent.mkdir()
            doc.write_text("# Configuration\n\n`KNOWN_NAME`\n", encoding="utf-8")
            errors = check_environment_document(root, {"KNOWN_NAME", "MISSING_NAME"}, "docs/configuration.md")
            self.assertTrue(any("MISSING_NAME" in item.message for item in errors))

    def test_indirect_and_yaml_environment_names_are_discovered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "feed_publication.py").write_text(
                'MANIFEST_ENV = "FEED_PUBLICATION_MANIFEST"\n'
                'value = os.environ.get(MANIFEST_ENV)\n',
                encoding="utf-8",
            )
            (scripts / "run-python311").write_text(
                "docker run --env HOME=/tmp/home python:3.11.15-bookworm python\n",
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "feed.yaml").write_text(
                "jobs:\n  test:\n    env:\n      PAYLOAD: value\n",
                encoding="utf-8",
            )
            (root / "backend").mkdir()
            (root / "backend" / "Dockerfile").write_text(
                "ENV PORT=8000\n", encoding="utf-8"
            )
            (root / "render.yaml").write_text(
                "services:\n  - envVars:\n      - key: PYTHON_VERSION\n"
                "        value: '3.11.15'\n",
                encoding="utf-8",
            )
            names = discover_environment_names(root, [])
            self.assertTrue(
                {"FEED_PUBLICATION_MANIFEST", "PAYLOAD", "PORT", "PYTHON_VERSION", "HOME"}
                <= names
            )

    def test_workflow_shell_environment_names_are_discovered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "docs.yml").write_text(
                "jobs:\n  docs:\n    steps:\n      - run: |\n"
                "          echo ok >> \"$GITHUB_OUTPUT\"\n"
                "          cd \"${GITHUB_WORKSPACE}\"\n"
                "          test -d \"$RUNNER_TEMP\"\n"
                "          LOCAL_ONLY=value\n"
                "          echo \"$LOCAL_ONLY\"\n"
                "          THRESH=\"${{ github.event.inputs.threshold }}\"\n"
                "          EXIST=$(gh issue list --limit 1)\n"
                "          PYTHONPATH=. \\\n"
                "            python scripts/check_docs.py\n",
                encoding="utf-8",
            )
            names = discover_environment_names(root, [])
            self.assertTrue(
                {"GITHUB_OUTPUT", "GITHUB_WORKSPACE", "RUNNER_TEMP", "PYTHONPATH"}
                <= names
            )
            self.assertTrue({"LOCAL_ONLY", "THRESH", "EXIST"}.isdisjoint(names))

    def test_missing_npm_script_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text('{"scripts":{"lint":"eslint ."}}', encoding="utf-8")
            page = root / "README.md"
            page.write_text("```bash\nnpm run build:static\n```\n", encoding="utf-8")
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run build:static", "kind": "entrypoint"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any("build:static" in item.message for item in errors))

    def test_ci_command_missing_from_workflows_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text('{"scripts":{"lint":"eslint ."}}', encoding="utf-8")
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "name: Tests\njobs:\n  frontend:\n    steps: []\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("```bash\nnpm run lint\n```\n", encoding="utf-8")
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run lint", "kind": "ci", "workflow": ".github/workflows/tests.yml", "job": "frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_in_wrong_workflow_is_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps: []\n", encoding="utf-8"
            )
            (workflows / "deploy.yml").write_text(
                "jobs:\n  deploy:\n    steps:\n      - run: npm run lint\n", encoding="utf-8"
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_in_comment_or_step_name_is_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps:\n"
                "      - name: npm run lint\n"
                "        run: |\n          # npm run lint\n          echo skipped\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-not-in-ci" for item in errors))

    def test_ci_command_honors_job_default_working_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    defaults:\n      run:\n"
                "        working-directory: frontend\n    steps:\n"
                "      - run: npm run lint\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"}]
            self.assertEqual(check_command_contracts(root, contracts), [])

    def test_ci_command_in_wrong_working_directory_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            (root / "frontend" / "package.json").write_text(
                '{"scripts":{"lint":"next lint"}}', encoding="utf-8"
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps:\n      - run: npm run lint\n"
                "        working-directory: backend\n",
                encoding="utf-8",
            )
            page = root / "README.md"
            page.write_text("\nnpm run lint\n", encoding="utf-8")
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "command-wrong-ci-cwd" for item in errors))

    def test_unhashed_pip_install_contract_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            backend = root / "backend"
            backend.mkdir()
            (backend / "requirements.txt").write_text("package==1 --hash=sha256:abc\n", encoding="utf-8")
            page = backend / "README.md"
            command = "python -m pip install -r requirements.txt"
            page.write_text(f"\n{command}\n", encoding="utf-8")
            contracts = [{"document":"backend/README.md","cwd":"backend","command":command,"kind":"entrypoint"}]
            errors = check_command_contracts(root, contracts)
            self.assertTrue(any(item.code == "unhashed-pip-install" for item in errors))

    def test_workflow_missing_from_inventory_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text("# Workflows\n", encoding="utf-8")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("tests.yml" in item.message for item in errors))

    def test_yaml_workflow_is_also_inventoried(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "guard.yaml").write_text("name: Guard\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text("# Workflows\n", encoding="utf-8")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("guard.yaml" in item.message for item in errors))

    def test_workflow_basename_in_prose_is_not_an_inventory_row(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\nThe `tests.yml` workflow runs tests.\n",
                encoding="utf-8",
            )
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("tests.yml" in item.message for item in errors))

    def test_workflow_inventory_rejects_duplicates_stale_rows_and_wrong_columns(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\n"
                "| Workflow | Purpose | Trigger | Command | Target | Permissions | Concurrency | Configuration |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| `tests.yml` | tests | PR | command | none | read | ci | none |\n"
                "| `tests.yml` | duplicate | PR | command | none | read | ci | none |\n"
                "| `removed.yaml` | stale | PR | command | none | read | ci | none |\n"
                "| `short.yml` | too few | PR |\n",
                encoding="utf-8",
            )
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            codes = {item.code for item in errors}
            self.assertTrue(
                {"duplicate-workflow-row", "stale-workflow-row", "invalid-workflow-row"}
                <= codes
            )

    def test_github_slug_preserves_double_space_as_double_hyphen(self):
        self.assertEqual(
            github_slug("1. 商业化 AI 股票分析平台 / SaaS"),
            "1-商业化-ai-股票分析平台--saas",
        )

    def test_markdown_categories_are_exclusive_and_complete(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.md"
            b = root / "generated" / "b.md"
            b.parent.mkdir()
            a.write_text("# A\n", encoding="utf-8")
            b.write_text("# B\n", encoding="utf-8")
            config = {
                "maintained_documents": ["a.md"],
                "historical_documents": ["a.md"],
                "archived_documents": [],
                "classification_exemptions": ["generated/*.md"],
            }
            errors = check_classification(root, config, [a, b])
            self.assertTrue(any(item.code == "overlapping-document-status" for item in errors))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the new tests and confirm the module is absent**

Run:

```bash
scripts/run-python311 python scripts/tests/test_check_docs.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.check_docs'`.

- [ ] **Step 4: Implement the standard-library checker**

Implement `scripts/check_docs.py` with these exact public types and functions:

```python
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
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


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message} [{self.code}]"


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("docs verification schema_version must be 1")
    return data


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


def check_metadata(root: Path, maintained: list[str], historical: list[str], archived: list[str]) -> list[Diagnostic]:
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
    for relative, status, status_code, scope_code in (
        *[(value, HISTORICAL_STATUS, "missing-historical-status", "missing-historical-scope") for value in historical],
        *[(value, ARCHIVED_STATUS, "missing-archived-status", "missing-archived-scope") for value in archived],
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
        if any(line.startswith(("> **Status:**", "> **Scope:**")) for line in fence_masked_lines[12:]):
            errors.append(Diagnostic(relative, 1, "metadata-not-in-header", "metadata must appear in the first 12 lines"))
        if (
            title_is_valid
            and len(status_positions) == len(scope_positions) == 1
            and not nonblank_lines[0][0] < status_positions[0][0] < scope_positions[0][0]
        ):
            errors.append(Diagnostic(relative, 1, "invalid-metadata-order", "header order must be H1, Status, Scope"))
    return errors


def stamp_documents(root: Path, maintained: list[str], sha: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("stamp requires a full 40-character Git SHA")
    line = f"> **Last verified commit:** `{sha}`"
    for relative in maintained:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if re.search(r"^> \*\*Last verified commit:\*\* `[^`]+`$", text, re.MULTILINE):
            text = re.sub(r"^> \*\*Last verified commit:\*\* `[^`]+`$", line, text, count=1, flags=re.MULTILINE)
        else:
            text, count = re.subn(r"^(> \*\*Scope:\*\* .+)$", rf"\1\n{line}", text, count=1, flags=re.MULTILINE)
            if count != 1:
                raise ValueError(f"{relative} has no Scope line for stamping")
        path.write_text(text, encoding="utf-8")


def workflow_files(root: Path) -> list[Path]:
    directory = root / ".github" / "workflows"
    return sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])


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
        "maintained": set(config.get("maintained_documents", [])),
        "historical": set(config.get("historical_documents", [])),
        "archived": set(config.get("archived_documents", [])),
    }
    exemptions = config.get("classification_exemptions", [])
    for path in files:
        relative = path.relative_to(root).as_posix()
        memberships = [name for name, values in categories.items() if relative in values]
        exemption_matches = [pattern for pattern in exemptions if fnmatch.fnmatchcase(relative, pattern)]
        if len(memberships) + len(exemption_matches) == 0:
            errors.append(Diagnostic(relative, 1, "unclassified-markdown", "tracked Markdown needs one status or generated-artifact exemption"))
        if len(memberships) + len(exemption_matches) > 1:
            errors.append(Diagnostic(relative, 1, "overlapping-document-status", "tracked Markdown has multiple statuses or exemptions"))
    return errors


def check_repository(root: Path, config_path: Path) -> list[Diagnostic]:
    config = load_config(config_path)
    maintained = config.get("maintained_documents", [])
    historical = config.get("historical_documents", [])
    archived = config.get("archived_documents", [])
    tracked = tracked_markdown(root)
    files = tracked if config.get("check_all_tracked_markdown") else [root / value for value in maintained]
    errors = check_local_links(root, files)
    errors.extend(check_metadata(root, maintained, historical, archived))
    if config.get("check_all_tracked_markdown"):
        errors.extend(check_classification(root, config, tracked))
    environment_document = config.get("environment_document")
    if environment_document:
        names = discover_environment_names(root, config.get("platform_environment_names", []))
        errors.extend(check_environment_document(root, names, environment_document))
    workflow_document = config.get("workflow_inventory_document")
    if workflow_document:
        errors.extend(check_workflow_inventory(root, workflow_document))
    errors.extend(check_command_contracts(root, config.get("verified_commands", [])))
    return sorted(set(errors))


def stamp_current(
    root: Path,
    config_path: Path,
    documents: list[str] | None = None,
) -> str:
    config = load_config(config_path)
    maintained = config.get("maintained_documents", [])
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
    config_path = ROOT / args.config
    try:
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
    config = load_config(config_path)
    print(
        "docs check passed: "
        f"{len(tracked_markdown(ROOT))} markdown files, "
        f"{len(config.get('maintained_documents', []))} maintained documents, "
        f"{len(workflow_files(ROOT))} workflows, "
        f"{len(config.get('verified_commands', []))} verified commands"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Add the bootstrap verification manifest**

Create `docs/verification.json` with the approved program design and its three accepted execution plans under the initial maintained contract. Full-repository link checking and operational checks remain disabled until the later content tasks populate their authoritative pages:

```json
{
  "schema_version": 1,
  "check_all_tracked_markdown": false,
  "maintained_documents": [
    "docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md",
    "docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md",
    "docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md",
    "docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md"
  ],
  "historical_documents": [],
  "archived_documents": [],
  "classification_exemptions": [
    "feed/screener/*.md",
    "frontend/public/feed/screener/*.md"
  ],
  "environment_document": null,
  "platform_environment_names": [],
  "workflow_inventory_document": null,
  "verified_commands": []
}
```

- [ ] **Step 6: Mark the approved program design Accepted and stamp it**

Change the design header to:

```markdown
# Stock Analysis 个人研究工作台整体重构设计

> **Status:** Accepted
> **Scope:** Repository-wide architecture, migration, testing, security, and documentation program design.
```

Keep its Date and Baseline commit fields below the metadata. Add the same header pattern to each plan with `Status: Accepted implementation plan` and a Scope naming its Stage 1 slice. Then run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current
```

Expected: `stamped documentation baseline:` followed by the exact 40-character SHA printed by `git rev-parse HEAD`.

- [ ] **Step 7: Run unit and bootstrap integration checks**

Run:

```bash
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: unittest reports `OK`; checker begins with `docs check passed:`; `git diff --check` prints nothing.

- [ ] **Step 8: Commit the checker primitive**

```bash
git add scripts/run-python311 scripts/check_docs.py scripts/tests/test_check_docs.py docs/verification.json docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md
git diff --cached --check
git commit -m "test(docs): add documentation contract checker"
```

Expected: one commit containing only the checker, tests, bootstrap manifest, and accepted design metadata.

---

### Task 2: Separate Current Architecture, Accepted Target, and Archived Plans

**Files:**
- Create: `docs/README.md`
- Create: `docs/current-architecture.md`
- Move/Rewrite: `docs/architecture.md` → `docs/rfcs/target-architecture.md`
- Create: `docs/architecture.md`
- Move: `docs/iteration-log.md` → `docs/archive/iteration-log.md`
- Create: `docs/iteration-log.md`
- Move: `docs/roadmap.md` → `docs/archive/pre-refactor/roadmap.md`
- Create: `docs/roadmap.md`
- Modify: `docs/verification.json`

**Interfaces:**
- Consumes: accepted program design, actual paths in `frontend/`, `backend/`, `feed/`, `.github/workflows/`, `scripts/`, and `backtest/`.
- Produces: one current-state authority, one accepted target summary, a documentation catalog, and compatibility routes for three old URLs.

- [ ] **Step 1: Record the exact code baseline being documented**

Run:

```bash
git status --short
git rev-parse HEAD
```

Expected: status shows no tracked changes and may show only `?? AGENTS.md`; `git rev-parse HEAD` prints one 40-character SHA. Do not copy it manually into files; the stamping command performs that action after the manifest is updated.

- [ ] **Step 2: Move the historical files without rewriting their history**

Run:

```bash
mkdir -p docs/rfcs docs/archive/pre-refactor
git mv docs/architecture.md docs/rfcs/target-architecture.md
git mv docs/iteration-log.md docs/archive/iteration-log.md
git mv docs/roadmap.md docs/archive/pre-refactor/roadmap.md
```

Expected: Git records three renames and no deletion of historical content.

- [ ] **Step 3: Rewrite `docs/rfcs/target-architecture.md` as the accepted target summary**

Use these exact sections and claims:

```markdown
# Target Architecture: One Product, Two Runtime Profiles

> **Status:** Accepted; target architecture, not current implementation
> **Scope:** Target boundaries and migration invariants for the repository-wide refactor.

## Decision
## Goals and non-goals
## Static and server profiles
## Contract authority
## DataGateway and adapter boundaries
## Deterministic analysis authority
## Python research boundary
## Feed publisher and manifest target
## Security and observability invariants
## Migration stages and retirement gates
## Differences from the current system
## Full program design
```

State that JSON Schema, generated models, DataGateway, analysis-core, stock_core, and atomic manifest publication are targets. Link `../current-architecture.md` for present behavior and `../superpowers/specs/2026-07-16-stock-analysis-refactor-design.md` for the complete decision.

- [ ] **Step 4: Create `docs/current-architecture.md` from verified repository facts**

Use these exact sections:

```markdown
# Current Architecture

> **Status:** Current
> **Scope:** Implemented repository architecture before the contract-first refactor.

## System boundary
## Current runtime variants
### GitHub Pages static export
### Vercel Edge-assisted frontend
### Frontend with optional FastAPI
## Current interactive data paths
## Frontend pages and responsibilities
## FastAPI routes, providers, cache, and bar store
## Git-backed feed and scheduled producers
## Research and backtest subsystem
## State and persistence
## Current trust boundaries
## Known duplication and semantic drift
## Current limitations
## Target architecture
```

Record these facts without upgrade language:

- The system has Next.js UI, optional FastAPI, repository-backed feed publication, and Python research/automation.
- The catalog has US, CN, HK, CRYPTO, JP, KR, DE, GB, plus IDX; capability depth varies by source and market.
- Stage 1B's static builder copies the complete frontend into a private temporary tree, removes `app/api` only from that copy, and leaves the tracked frontend plus bundled feed untouched; the server/Vercel build retains quote and OHLCV route handlers.
- Current frontend source selection is concentrated in `frontend/lib/datasource.ts` but still spans FastAPI, Edge, raw feed, browser sources, and browser cache.
- The Edge base is not purely configuration-driven: absent `NEXT_PUBLIC_EDGE_BASE` and a same-origin `*.vercel.app` host, current code falls back to the hard-coded `https://stock-analysis-ten-phi.vercel.app` deployment.
- Quote and OHLCV requests have distinct source chains. Quotes use fresh memory/browser cache, optional FastAPI for non-index symbols, Edge for non-crypto symbols, a fresh live snapshot when at least three stock quotes remain, direct Binance/Yahoo paths, then a bounded stale quote. OHLCV uses fresh browser cache, Edge first for every market including crypto, optional FastAPI for non-index symbols, direct Binance/Yahoo paths, then a bounded stale bar series.
- Deterministic analysis has duplicate TypeScript and Python implementations.
- Backend persistence is SQLite by default; PostgreSQL is optional Winter tooling, not a base runtime requirement.
- Feed artifacts have multiple writers and uneven schema coverage; atomic manifests are not current behavior.

- [ ] **Step 5: Create `docs/README.md` and compatibility pages**

`docs/README.md` contains these sections:

```markdown
# Documentation

> **Status:** Current
> **Scope:** Status catalog and navigation for maintained, target, historical, and archived documentation.

## Start here
## Current system
## Configuration, deployment, operations, and contracts
## Research
## Accepted design and RFCs
## Historical snapshots
## Archived pre-refactor material
## Documentation maintenance rules
```

Create `docs/architecture.md` with:

```markdown
# Architecture documentation moved

> **Status:** Current compatibility page
> **Scope:** Preserve the former architecture URL and direct readers to current and target architecture authorities.

This path is not current implementation guidance.

- Current implementation: [`current-architecture.md`](current-architecture.md)
- Accepted target: [`rfcs/target-architecture.md`](rfcs/target-architecture.md)
```

Create `docs/roadmap.md` with:

```markdown
# Roadmap documentation moved

> **Status:** Current compatibility page
> **Scope:** Preserve the former roadmap URL and direct readers to the accepted migration program and archived roadmap.

This path is not current implementation guidance.

- Accepted migration program: [`superpowers/specs/2026-07-16-stock-analysis-refactor-design.md`](superpowers/specs/2026-07-16-stock-analysis-refactor-design.md)
- Historical roadmap: [`archive/pre-refactor/roadmap.md`](archive/pre-refactor/roadmap.md)
```

Create `docs/iteration-log.md` with:

```markdown
# Iteration log moved

> **Status:** Current compatibility page
> **Scope:** Preserve the former iteration-log URL and direct readers to the historical record and maintained documentation catalog.

This path is not current implementation guidance.

- Historical iteration log: [`archive/iteration-log.md`](archive/iteration-log.md)
- Maintained documentation catalog: [`README.md`](README.md)
```

- [ ] **Step 6: Add Archived metadata to moved historical pages**

Insert immediately below each title:

```markdown
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-16
```

Add one sentence linking the current replacement. Do not rewrite the archived body.

- [ ] **Step 7: Expand the manifest, stamp, and validate this slice**

Add the following paths to `maintained_documents`:

```json
[
  "docs/README.md",
  "docs/current-architecture.md",
  "docs/architecture.md",
  "docs/roadmap.md",
  "docs/iteration-log.md",
  "docs/rfcs/target-architecture.md"
]
```

Retain the design and three plan paths already present from Task 1. Add the two moved history files to `archived_documents`. Then run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current \
  --document docs/README.md \
  --document docs/current-architecture.md \
  --document docs/architecture.md \
  --document docs/roadmap.md \
  --document docs/iteration-log.md \
  --document docs/rfcs/target-architecture.md
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: stamping prints the exact baseline SHA; checker passes; whitespace check prints nothing.

- [ ] **Step 8: Commit the architecture/documentation topology**

```bash
git add docs/README.md docs/current-architecture.md docs/architecture.md docs/roadmap.md docs/iteration-log.md docs/rfcs/target-architecture.md docs/archive/iteration-log.md docs/archive/pre-refactor/roadmap.md docs/verification.json
git diff --cached --check
git commit -m "docs: separate current architecture from target design"
```

Expected: one reviewable commit containing current architecture, target architecture, archives, and compatibility pages only.

---

### Task 3: Document Configuration, Deployment, Workflows, and Feed Contracts

**Files:**
- Create: `docs/configuration.md`
- Create: `docs/deployment-matrix.md`
- Create: `docs/operations/workflows.md`
- Create: `docs/data-contracts/feed.md`
- Move the nine stale operational/planning documents identified below to their exact `docs/archive/pre-refactor/` paths
- Recreate compatibility pages at each moved old path
- Modify: `docs/compliance.md`
- Modify: `docs/openclaw-integration.md`
- Modify: `docs/openclaw-stock-notes.md`
- Modify: `routines/daily-alpha-routine.md`
- Modify: `routines/methodology.md`
- Modify: `routines/openclaw-agent-prompts.md`
- Modify: `routines/openclaw-daily-tasks.md`
- Modify: `routines/winter-inbox.md`
- Modify: `docs/verification.json`

**Interfaces:**
- Consumes: Stage 1A fail-closed behavior, Stage 1B commands, actual environment lookups, workflow YAML, backend routes, feed JSON paths, and `frontend/lib/feed.ts`.
- Produces: four operational authorities consumed by root and subsystem READMEs and by the checker.

- [ ] **Step 1: Move stale operational and planning documents into the pre-refactor archive**

Run:

```bash
mkdir -p docs/operations docs/data-contracts
git mv docs/deploy-backend.md docs/archive/pre-refactor/deploy-backend.md
git mv docs/data-model-api.md docs/archive/pre-refactor/data-model-api.md
git mv docs/endpoints.md docs/archive/pre-refactor/endpoints.md
git mv docs/working-apis.md docs/archive/pre-refactor/working-apis.md
git mv docs/need-to-fix.md docs/archive/pre-refactor/need-to-fix-2026-06-10.md
git mv docs/optimization-2026-06.md docs/archive/pre-refactor/optimization-2026-06.md
git mv docs/positioning.md docs/archive/pre-refactor/positioning.md
git mv docs/cost-estimate.md docs/archive/pre-refactor/cost-estimate-2026-06.md
git mv docs/self-improving-alpha-loop.md docs/archive/pre-refactor/self-improving-alpha-loop.md
```

Expected: every source path is absent until its compatibility page is created; every destination preserves Git history.

- [ ] **Step 2: Write `docs/configuration.md` with a complete categorized inventory**

Use these exact sections:

```markdown
# Configuration

> **Status:** Current
> **Scope:** User-settable, secret, and platform-provided configuration used by current code and workflows.

## Configuration rules
## Frontend build-time variables
## Backend cache and storage variables
## GitHub repository Variables
## Feed and OpenClaw secrets and options
## Intraday and Winter options
## Platform-provided variables
## Defaults and fallback behavior
## Local examples
## Secret handling
## Verification
```

Document every name below in backticks, with columns for owner, required/optional, default, secret status, and consumers:

```text
NEXT_PUBLIC_BASE_PATH
NEXT_PUBLIC_API_BASE
NEXT_PUBLIC_EDGE_BASE
NEXT_PUBLIC_FEED_BASE
NEXT_BUILD_PROFILE
STATIC_FEED_SOURCE
SMOKE_PORT
NEXT_TELEMETRY_DISABLED
NODE_ENV
CACHE_DB
STORE_DB
CACHE_STALE_GRACE
CACHE_MAX_ENTRIES
API_BASE
AUTOMERGE_ELIGIBLE_LABEL
EDGE_BASE
FEED_HMAC_SECRET
GITHUB_TOKEN
GH_TOKEN
GITHUB_REPOSITORY
GITHUB_RUN_URL
GITHUB_OUTPUT
GITHUB_WORKSPACE
RUNNER_TEMP
HOME
OPENCLAW_MODEL
OPENCLAW_RUN_URL
OPENCLAW_BRANCH
OPENCLAW_REPO
OPENCLAW_TOKEN
OPENCLAW_WATCHLIST
OPENCLAW_THROTTLE
PACKAGE_ECOSYSTEM
INTRADAY_OUT
INTRADAY_PRODUCER
WINTER_PG_DSN
WINTER_INTRADAY_LATEST
PORT
FEED_PUBLICATION_MANIFEST
PAYLOAD
REPO
PR_NUMBER
REPORT
UPDATE_TYPE
PYTHONDONTWRITEBYTECODE
PYTHONUNBUFFERED
PIP_DISABLE_PIP_VERSION_CHECK
PYTHONPATH
PYTHON_VERSION
```

Separate user-facing configuration from internal build/workflow plumbing. `NEXT_BUILD_PROFILE`, `STATIC_FEED_SOURCE`, `SMOKE_PORT`, `NEXT_TELEMETRY_DISABLED`, `NODE_ENV`, `FEED_PUBLICATION_MANIFEST`, `PAYLOAD`, `REPO`, `PR_NUMBER`, `REPORT`, `AUTOMERGE_ELIGIBLE_LABEL`, `PACKAGE_ECOSYSTEM`, `UPDATE_TYPE`, `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `PIP_DISABLE_PIP_VERSION_CHECK`, `PYTHONPATH`, the container-local `HOME`, and Render's pinned `PYTHON_VERSION` are internal execution contracts, not settings most users should export. Distinguish origins precisely: `PORT`, `GITHUB_OUTPUT`, `GITHUB_WORKSPACE`, `GITHUB_REPOSITORY`, and `RUNNER_TEMP` are runner/platform values; `GITHUB_TOKEN` and `GH_TOKEN` are explicitly mapped into workflow environments; and current `GITHUB_RUN_URL` is composed by the workflow from GitHub context rather than injected automatically. State that an unset endpoint disables or changes an adapter according to current code; document the hard-coded Edge default and do not promise the Stage 2 explicit-profile behavior. Do not retain `VERCEL`, `PR_URL`, or the unused `HEAD_SHA` name from pre-Stage-1B prose: the explicit build profile and hardened Dependabot workflow do not consume them.

- [ ] **Step 3: Write `docs/deployment-matrix.md` around two primary profiles and current variants**

Use these exact sections:

```markdown
# Deployment Matrix

> **Status:** Current
> **Scope:** Supported current deployment variants, commands, dependencies, and limitations.

## Profile model
## Static profile
### Local development
### GitHub Pages
### Optional Edge adapter
## Server profile
### Local Next.js and FastAPI
### Hosted frontend and hosted FastAPI
## Vercel Edge-assisted variant
## Capability and degradation matrix
## Build and smoke-test commands
## Configuration matrix
## Health checks
## Rollback
## Current gaps before semantic parity
```

Static and server receive equal table columns. Explicitly state that the common UI exists today but semantic parity is a Stage 2 acceptance target. Include the exact, distinct quote and OHLCV fallback chains recorded in Task 2, including the hard-coded Edge default; a configured FastAPI base does not imply that every request actually uses FastAPI. Describe Render/Docker/Railway/Fly only through files that exist in the repository; do not claim a hosted FastAPI instance exists.

- [ ] **Step 4: Write `docs/operations/workflows.md` as a complete basename inventory**

Use these sections:

```markdown
# Workflow Operations

> **Status:** Current
> **Scope:** GitHub Actions triggers, permissions, generated artifacts, writers, and recovery procedures.

## Operating model
## Workflow inventory
## Feed writers and ownership
## Branch and commit behavior
## Required Variables and Secrets
## Manual dispatch and rerun
## Watchdogs and freshness checks
## Failure diagnosis
## Security and rollback invariants
## Change checklist
## Current limitations
```

The inventory table has exactly one row per `.github/workflows/*.yml` or `.github/workflows/*.yaml`, no stale rows, and exactly eight non-empty cells per row: basename in backticks, purpose, trigger, command/entry point, write or deploy target, permissions, concurrency group, and configuration. Do not place the row count in prose.

- [ ] **Step 5: Write `docs/data-contracts/feed.md` from current artifact families**

Use these sections:

```markdown
# Feed Data Contracts

> **Status:** Current
> **Scope:** Current repository-backed feed artifacts, report schema, validation, consumers, and known limitations.

## Transport and consumers
## Artifact families
## Report schema v1.0
## Producer and consumer ownership
## External submission authentication
## ID, path, size, and idempotency rules
## Index and freshness semantics
## Raw feed and bundled snapshot fallback
## Validation and publication commands
## Current schema coverage
## Current publication limitations
## Target manifest publisher
```

The artifact table must cover `index.json`, `health.json`, `watchlist.json`, `reports/`, `signals/`, `market/`, `factory/`, `screener/`, `stock-notes/`, `intraday/`, `crypto/`, and `funds/`. State plainly that only report artifacts currently use `feed/schema/report.schema.json`; do not claim every feed JSON is schema-validated. Describe Stage 1A HMAC/path fixes as current only after verifying their tests.

- [ ] **Step 6: Rewrite `docs/compliance.md` and create compatibility pages**

`docs/compliance.md` becomes Current and contains only:

- personal research and self-hosting scope;
- upstream licensing and redistribution caveats;
- estimation/latency disclosure;
- AI artifact labeling;
- secret handling;
- non-investment-advice statement;
- a statement that commercial use requires independent legal and data-license review.

Do not make jurisdiction-specific legal conclusions. Add this header below the title of every file moved in Step 1:

```markdown
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-16
```

Each moved old path then gets a short Current compatibility page with `Status`, `Scope`, and these exact link destinations:

| Compatibility path | Archived source | Current authority |
|---|---|---|
| `docs/deploy-backend.md` | `archive/pre-refactor/deploy-backend.md` | `deployment-matrix.md` |
| `docs/data-model-api.md` | `archive/pre-refactor/data-model-api.md` | `current-architecture.md` and `../backend/README.md` |
| `docs/endpoints.md` | `archive/pre-refactor/endpoints.md` | `current-architecture.md` and `configuration.md` |
| `docs/working-apis.md` | `archive/pre-refactor/working-apis.md` | `current-architecture.md` |
| `docs/need-to-fix.md` | `archive/pre-refactor/need-to-fix-2026-06-10.md` | `current-architecture.md` |
| `docs/optimization-2026-06.md` | `archive/pre-refactor/optimization-2026-06.md` | `current-architecture.md` |
| `docs/positioning.md` | `archive/pre-refactor/positioning.md` | `README.md` |
| `docs/cost-estimate.md` | `archive/pre-refactor/cost-estimate-2026-06.md` | `README.md` |
| `docs/self-improving-alpha-loop.md` | `archive/pre-refactor/self-improving-alpha-loop.md` | `operations/workflows.md` and `research/index.md` |

Because `docs/research/index.md` is created in Task 4, the `self-improving-alpha-loop.md` compatibility page initially links `docs/README.md`; Task 4 replaces that link with `research/index.md` before full-link validation is enabled.

Rewrite `docs/openclaw-integration.md` and `docs/openclaw-stock-notes.md` in place as maintained contracts instead of archiving them: active routines depend on these paths and anchors. Preserve the literal `### 1.2 调度(Orchestrator)` heading in the integration document and the literal `### stock-analyst 角色 prompt(交给你的 OpenClaw)` heading in the stock-note document so existing links keep the GitHub slugs `#12-调度orchestrator` and `#stock-analyst-角色-prompt交给你的-openclaw`. Limit both documents to implemented submission modes, authentication, schemas, failure behavior, and authority links; move aspirational prose into the accepted target RFC rather than inventing new current behavior.

Add Current metadata to every `routines/*.md` playbook listed under Files and repair its authority links without changing task semantics. `routines/openclaw-agent-prompts.md` must continue to resolve the integration document's section 1.2 anchor, and `routines/openclaw-daily-tasks.md` must continue to resolve the stock-analyst prompt anchor.

- [ ] **Step 7: Update manifest categories and run the operational document gate**

Add the four new authority pages, `docs/compliance.md`, the nine compatibility paths from the table above, both maintained OpenClaw contracts, and all five active routine playbooks to maintained documents. Add every moved destination to archived documents. Set:

```json
"environment_document": "docs/configuration.md",
"platform_environment_names": [
  "PORT",
  "GITHUB_TOKEN",
  "GH_TOKEN",
  "GITHUB_REPOSITORY",
  "GITHUB_RUN_URL",
  "GITHUB_OUTPUT",
  "GITHUB_WORKSPACE",
  "RUNNER_TEMP"
],
"workflow_inventory_document": "docs/operations/workflows.md"
```

Run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current \
  --document docs/configuration.md \
  --document docs/deployment-matrix.md \
  --document docs/operations/workflows.md \
  --document docs/data-contracts/feed.md \
  --document docs/compliance.md \
  --document docs/deploy-backend.md \
  --document docs/data-model-api.md \
  --document docs/endpoints.md \
  --document docs/working-apis.md \
  --document docs/need-to-fix.md \
  --document docs/optimization-2026-06.md \
  --document docs/positioning.md \
  --document docs/cost-estimate.md \
  --document docs/self-improving-alpha-loop.md \
  --document docs/openclaw-integration.md \
  --document docs/openclaw-stock-notes.md \
  --document routines/daily-alpha-routine.md \
  --document routines/methodology.md \
  --document routines/openclaw-agent-prompts.md \
  --document routines/openclaw-daily-tasks.md \
  --document routines/winter-inbox.md
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: checker passes with every discovered environment name and workflow basename documented; whitespace check prints nothing.

- [ ] **Step 8: Commit the operational authorities**

```bash
git add docs/configuration.md docs/deployment-matrix.md docs/operations/workflows.md docs/data-contracts/feed.md docs/compliance.md docs/archive/pre-refactor/deploy-backend.md docs/archive/pre-refactor/data-model-api.md docs/archive/pre-refactor/endpoints.md docs/archive/pre-refactor/working-apis.md docs/archive/pre-refactor/need-to-fix-2026-06-10.md docs/archive/pre-refactor/optimization-2026-06.md docs/archive/pre-refactor/positioning.md docs/archive/pre-refactor/cost-estimate-2026-06.md docs/archive/pre-refactor/self-improving-alpha-loop.md docs/deploy-backend.md docs/data-model-api.md docs/endpoints.md docs/working-apis.md docs/need-to-fix.md docs/optimization-2026-06.md docs/positioning.md docs/cost-estimate.md docs/self-improving-alpha-loop.md docs/openclaw-integration.md docs/openclaw-stock-notes.md routines/daily-alpha-routine.md routines/methodology.md routines/openclaw-agent-prompts.md routines/openclaw-daily-tasks.md routines/winter-inbox.md docs/verification.json
git diff --cached --check
git commit -m "docs: document configuration and operations"
```

Expected: one commit with operational authorities, archives, compatibility pages, and manifest changes; no runtime code.

---

### Task 4: Build the Research Index and a Truthful Backtest Entry Point

**Files:**
- Create: `docs/research/index.md`
- Move: `backtest/README.md` → `backtest/README_tqm.md`
- Create: `backtest/README.md`
- Move: `backtest/FEATURES.md` → `docs/archive/pre-refactor/backtest-features.md`
- Create: `backtest/FEATURES.md`
- Modify: every preserved historical file listed in File Map
- Modify: `docs/study-pbo-2026-06-10.md:19`
- Modify: `docs/study-pbo-2026-07-02.md:19`
- Modify: `docs/self-improving-alpha-loop.md`
- Modify: `docs/verification.json`

**Interfaces:**
- Consumes: existing backtest scripts, requirements, study reports, and research caveats.
- Produces: a stable subsystem entry point and one catalog that distinguishes executable research from dated result snapshots.

- [ ] **Step 1: Move the TQM study out of the subsystem README slot**

Run:

```bash
mkdir -p docs/research
git mv backtest/README.md backtest/README_tqm.md
git mv backtest/FEATURES.md docs/archive/pre-refactor/backtest-features.md
```

Expected: Git records both renames, preserving the TQM study body and the pre-refactor feature inventory.

- [ ] **Step 2: Create the new `backtest/README.md`**

Use these exact sections:

```markdown
# Backtest and Research

> **Status:** Current
> **Scope:** Installation, entry points, outputs, and limitations for the Python research subsystem.

## Scope
## Requirements and installation
## Data and cache boundaries
## Entry-point matrix
## Outputs
## Minimal offline verification
## Research catalog
## Reproducibility rules
## Known limitations
```

The entry-point matrix identifies each actual script, whether it requires network/cache, and its result document. Do not reproduce Sharpe, hit-rate, or return values in this README.

Create `backtest/FEATURES.md` as a short Current compatibility page pointing to `backtest/README.md`, `docs/research/index.md`, and the archived inventory at `../docs/archive/pre-refactor/backtest-features.md`. Add Archived metadata to the moved inventory without rewriting its body.

- [ ] **Step 3: Create `docs/research/index.md`**

Use these exact sections:

```markdown
# Research Index

> **Status:** Current
> **Scope:** Catalog of repository research methods, executable entry points, dated findings, and methodological limitations.

## How to read research status
## Backtest subsystem
## Equity factor and walk-forward studies
## Statistical arbitrage
## Crypto and Hyperliquid studies
## PBO, PIT, survivorship, and downshift studies
## Dated research snapshots
## External market scan
## Reproduction policy
## Shared limitations
## Adding a study
```

Every catalog row includes date, method, code entry point, requirements file, data/cache dependency, result document, and the strongest known limitation. Results remain in their dated source documents.

Include both `research/ai-agents-skills-market-scan.md` and `research/quant-factor-deep-research.md` in the dated-snapshot catalog. Update `docs/self-improving-alpha-loop.md` so its current-research link now targets `research/index.md`, while its archived source link remains intact.

- [ ] **Step 4: Classify preserved research pages and repair the two malformed links**

Add this metadata after each historical research title:

```markdown
> **Status:** Historical research snapshot; not maintained
> **Scope:** Dated research result preserved for methodology and provenance, not current product behavior.
```

In both PBO study files, replace the malformed link-like text with:

```markdown
`[3,40]`（宽半衰期带）
```

Expected: the phrase is no longer parsed as a link to a nonexistent local file.

- [ ] **Step 5: Expand the manifest, stamp, and verify research navigation**

Add `backtest/README.md`, `backtest/FEATURES.md`, and `docs/research/index.md` to maintained documents. Add every preserved dated research page—including both files under `research/`—and `backtest/README_tqm.md` to historical documents. Add `docs/archive/pre-refactor/backtest-features.md` to archived documents. Run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current \
  --document backtest/README.md \
  --document backtest/FEATURES.md \
  --document docs/research/index.md \
  --document docs/self-improving-alpha-loop.md
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: checker passes; both malformed-link diagnostics are absent.

- [ ] **Step 6: Commit the research documentation split**

```bash
git add backtest/README.md backtest/FEATURES.md backtest/README_tqm.md backtest/README_binance.md backtest/README_crypto.md backtest/README_crypto_pipeline.md backtest/README_pipeline.md backtest/README_statarb.md backtest/README_xs.md docs/archive/pre-refactor/backtest-features.md docs/research/index.md docs/self-improving-alpha-loop.md docs/study-downshift-2026-06-10.md docs/study-downshift-2026-07-02.md docs/study-overnight-gap-2026-06-10.md docs/study-pbo-2026-06-10.md docs/study-pbo-2026-07-02.md docs/study-pit-bite-2026-06-10.md docs/study-pit-membership-2026-06-10.md docs/hyperliquid-integration.md docs/survivorship-bias-data-sources.md research/ai-agents-skills-market-scan.md research/quant-factor-deep-research.md docs/verification.json
git diff --cached --check
git commit -m "docs: separate research guides from result snapshots"
```

Expected: one commit with no research algorithm changes or regenerated results.

---

### Task 5: Rewrite Backend and Feed Subsystem READMEs

**Files:**
- Modify: `backend/README.md`
- Modify: `feed/README.md`
- Modify: `docs/verification.json`

**Interfaces:**
- Consumes: current FastAPI routes/providers/models, Stage 1A feed security behavior, configuration authority, deployment matrix, workflow operations, and feed contract.
- Produces: concise subsystem guides linked by the root README.

- [ ] **Step 1: Rewrite `backend/README.md` from code-visible behavior**

Use these exact sections:

```markdown
# FastAPI Market Data Service

> **Status:** Current
> **Scope:** Optional server-profile market-data, cache, OHLCV, and compatibility-analysis service.

## Role and optionality
## Requirements and installation
## Run locally
## Test locally
## Configuration
## API routes
## Providers and market coverage
## SQLite cache and bar store
## Deployment
## Current limitations
```

List `/api/v1/health`, `/api/v1/cache`, `/api/v1/search`, `/api/v1/quotes`, `/api/v1/ohlcv`, `/api/v1/analysis`, `/api/v1/moneyflow`, `/api/v1/chips`, and `/api/v1/chan`. Document the actual symbol format and request limits from code. Remove the claim that Python analysis is kept identical to frontend analysis; state that compatibility endpoints remain duplicated until Stage 3. Label money-flow and chip-distribution outputs as OHLCV/K-line-derived estimates rather than exchange-reported position or order-flow truth. State that the SEC-based fundamental path is US-only.

- [ ] **Step 2: Rewrite `feed/README.md` as a concise subsystem entry point**

Use these exact sections:

```markdown
# Repository Feed

> **Status:** Current
> **Scope:** Entry point for repository-backed generated artifacts and their consumers.

## Role
## Artifact families
## Producers and consumers
## Report validation
## Validate locally
## Publication entry points
## Freshness and fallback
## Current limitations
## Authoritative documentation
```

State explicitly that report schema coverage does not extend to every artifact family, writers are not yet consolidated, and `frontend/public/feed` is a bundled fallback snapshot.

- [ ] **Step 3: Register commands in the verification manifest**

Add these exact command contracts. For every `kind: ci` entry, the checker requires the exact command inside the named workflow and job rather than accepting it anywhere in Actions YAML:

```json
[
  {"document":"backend/README.md","cwd":"backend","command":"python -m pip install --require-hashes -r requirements.txt","kind":"entrypoint"},
  {"document":"backend/README.md","cwd":"backend","command":"python tests/test_backend.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"backend/README.md","cwd":"backend","command":"python tests/test_api.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_validate_feed.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_validation_security.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_ingress.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_validate_feed_cli.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_publication.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_workflow_security.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"}
]
```

- [ ] **Step 4: Stamp and run subsystem documentation checks**

Add both READMEs to maintained documents, then run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current \
  --document backend/README.md \
  --document feed/README.md
scripts/run-python311 python scripts/check_docs.py
```

Then, from the repository root, execute the exact **Python 3.11 gate** in Shared Interfaces without modification. Expected: the documentation checker passes; the lock files reproduce exactly; all eight feed/security/engine scripts pass; both backend scripts print their all-passed summaries. This step must not use host Python.

- [ ] **Step 5: Commit subsystem documentation**

```bash
git add backend/README.md feed/README.md docs/verification.json
git diff --cached --check
git commit -m "docs: rewrite backend and feed guides"
```

Expected: one commit containing only two subsystem guides and their contract registration.

---

### Task 6: Replace the Root README with the Truth-First Product Entry Point

**Files:**
- Modify: `README.md`
- Modify: `docs/verification.json`

**Interfaces:**
- Consumes: all authorities created in Tasks 2–5 and the Stage 1B command interface.
- Produces: the single repository entry point for product scope, runtime selection, quick starts, limitations, and navigation.

- [ ] **Step 1: Write the root README with the approved product position**

Use this exact section order:

```markdown
# Stock Analysis — 个人多市场研究工作台

> **Status:** Current
> **Scope:** Repository entry point, runtime selection, verified quick start, and product limitations.

面向个人研究与自托管的多市场行情、技术分析和自动化情报工作台。

## 它是什么 / 不是什么
## 当前能力
## 选择运行模式
## 快速开始
### Static profile
### Server profile
### 验证安装
## 页面与能力地图
## 市场与数据能力
## 数据来源、时效与估算口径
## Feed 与自动化
## 研究与回测
## 部署
## 仓库结构
## 文档导航
## 已知限制
## 安全、合规与非投资建议
```

The opening scope states: personal research, self-hosting, no brokerage execution, no multi-user authentication, no guaranteed real-time data, and no investment advice.

- [ ] **Step 2: Add a four-state capability matrix**

Use `Implemented`, `Optional`, `External`, and `Planned` as the only status values. Record:

- Implemented: Next.js UI routes, eight market groups plus indexes, quote/OHLCV adapters, local watchlist/alerts/portfolio, rule-based technical panels, Git-backed feed consumption, research/backtest code.
- Optional: FastAPI, Vercel Edge routes, hosted backend, Winter/PostgreSQL projection.
- External: public market providers, OpenClaw generation, Hyperliquid, GitHub Actions scheduling, hosting platforms.
- Planned: generated cross-language contracts, explicit DataGateway profiles, shared deterministic analysis-core, stock_core, staged atomic feed manifests, full semantic parity CI.

Every row includes a limitation or authority link. Market catalog coverage must not be described as equal provider depth.

The page map lists exactly these eleven implemented routes and no planned screens: `/`, `/symbol`, `/desk`, `/screener`, `/tracker`, `/intel`, `/reports`, `/portfolio`, `/alerts`, `/sources`, and `/help`.

- [ ] **Step 3: Document two equal profiles without claiming current parity**

Use a side-by-side table for Static and Server with rows for prerequisites, primary data path, optional adapters, persistence, deployment variants, build command, smoke command, and current limitations. State:

- Static: Node 20, GitHub Pages/local static build, feed and browser-safe sources, optional configured Edge adapter.
- Server: Node 20 plus Python 3.11, same frontend with FastAPI, SQLite cache/bar store, optional hosted deployment.
- Shared semantic parity is the accepted target; current source order and analysis duplication remain documented gaps.

The matrix and data-source section must also expose the current hidden coupling: when neither `NEXT_PUBLIC_EDGE_BASE` nor same-origin Vercel applies, the frontend uses the hard-coded Edge deployment. Show the distinct quote and OHLCV source chains from `docs/current-architecture.md`; do not compress them into a fictitious single data layer.

State these user-visible limits prominently:

- watchlist, price alerts, and paper portfolio are stored in this browser's `localStorage` and do not sync across devices;
- price alerts poll and notify only while a relevant page remains open/visible; there is no background push service;
- only the Binance crypto path consumes true trade/order-book data; stock money-flow and chip distribution are estimates derived from K-line price/volume history;
- SEC EDGAR fundamentals are US-only;
- provider freshness, CORS proxies, cached snapshots, and stale fallbacks vary by market and runtime profile.

- [ ] **Step 4: Use only Stage 1B public verification commands**

The validation block contains exactly:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build:static
npm run smoke:static
npm run build:server
npm run smoke:server
cd ..
```

The Python block contains exactly the existing direct tests:

```bash
cd backend
python tests/test_backend.py
python tests/test_api.py
cd ..
python scripts/tests/test_chan_engine.py
python scripts/tests/test_validate_feed.py
```

Quick-start development commands may additionally use the existing `npm run dev` and `python -m uvicorn app.main:app --reload --port 8000`; mark them as long-running entry points rather than CI verification.

- [ ] **Step 5: Remove stale and unsafe claims**

Confirm the rewritten file contains none of these strings:

```text
P1 MVP 编码中
全程非 LLM
三者同源一致
全站单一报价数据层
17 个 GitHub Actions
13 个定时任务
```

Do not copy Cycle 1–11 narratives, OpenClaw round counts, dated “new feature” lists, or backtest metrics into another README section.

- [ ] **Step 6: Register root commands, stamp, and verify**

Add `README.md` to maintained documents. Register every documented release command against the workflow/job that actually executes it, and register long-running local commands as entry points:

```json
[
  {"document":"README.md","cwd":"frontend","command":"npm ci","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run typecheck","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run build:static","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run smoke:static","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run build:server","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run smoke:server","kind":"ci","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"backend","command":"python tests/test_backend.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":"backend","command":"python tests/test_api.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":".","command":"python scripts/tests/test_chan_engine.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":".","command":"python scripts/tests/test_validate_feed.py","kind":"ci","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":"frontend","command":"npm run dev","kind":"entrypoint"},
  {"document":"README.md","cwd":"backend","command":"python -m uvicorn app.main:app --reload --port 8000","kind":"entrypoint"}
]
```

Run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current --document README.md
scripts/run-python311 python scripts/check_docs.py
! rg -n "P1 MVP 编码中|全程非 LLM|三者同源一致|全站单一报价数据层|17 个 GitHub Actions|13 个定时任务" README.md
git diff --check
```

Expected: checker passes; the negated `rg` succeeds only because the underlying search returns 1 with no matches; whitespace check prints nothing.

- [ ] **Step 7: Execute every documented release command**

From the repository root, execute the exact **Node gate** and then the exact **Python 3.11 gate** in Shared Interfaces, without modification. The Node gate invokes every documented frontend release command; the Python gate invokes every documented Python release command and the additional Stage 1A security suite. Expected: deterministic installs succeed; lint and typecheck exit 0; both builds exit 0; both smoke suites report success; lock regeneration matches; and all ten Python test invocations pass. This step must not use host Node or Python.

- [ ] **Step 8: Commit the root README independently**

```bash
git add README.md docs/verification.json
git diff --cached --check
git commit -m "docs: replace README with truth-first guide"
```

Expected: one reviewable commit focused on product narrative, runtime choice, commands, and navigation.

---

### Task 7: Enable Full-Repository Documentation CI

**Files:**
- Modify: `docs/verification.json`
- Modify: `scripts/tests/test_check_docs.py`
- Create: `.github/workflows/docs.yml`
- Modify: `docs/operations/workflows.md`

**Interfaces:**
- Consumes: complete Stage 1C documentation tree and checker.
- Produces: a required offline guard for Markdown, command, environment, and workflow drift.

- [ ] **Step 1: Add the real-repository integration test**

Append this test to `DocumentationChecks`:

```python
    def test_repository_documentation_contract_passes(self):
        root = Path(__file__).resolve().parents[2]
        from scripts.check_docs import check_repository

        errors = check_repository(root, root / "docs" / "verification.json")
        self.assertEqual([item.render() for item in errors], [])

```

- [ ] **Step 2: Turn on all tracked-Markdown link validation**

Replace the manifest's classification portion with this complete list; do not infer or omit paths at implementation time:

```json
{
  "check_all_tracked_markdown": true,
  "maintained_documents": [
    "README.md",
    "backend/README.md",
    "backtest/README.md",
    "backtest/FEATURES.md",
    "feed/README.md",
    "docs/README.md",
    "docs/current-architecture.md",
    "docs/architecture.md",
    "docs/roadmap.md",
    "docs/iteration-log.md",
    "docs/rfcs/target-architecture.md",
    "docs/configuration.md",
    "docs/deployment-matrix.md",
    "docs/operations/workflows.md",
    "docs/data-contracts/feed.md",
    "docs/research/index.md",
    "docs/compliance.md",
    "docs/deploy-backend.md",
    "docs/data-model-api.md",
    "docs/endpoints.md",
    "docs/working-apis.md",
    "docs/need-to-fix.md",
    "docs/optimization-2026-06.md",
    "docs/positioning.md",
    "docs/cost-estimate.md",
    "docs/self-improving-alpha-loop.md",
    "docs/openclaw-integration.md",
    "docs/openclaw-stock-notes.md",
    "docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md",
    "docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md",
    "docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md",
    "docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md",
    "routines/daily-alpha-routine.md",
    "routines/methodology.md",
    "routines/openclaw-agent-prompts.md",
    "routines/openclaw-daily-tasks.md",
    "routines/winter-inbox.md"
  ],
  "historical_documents": [
    "backtest/README_tqm.md",
    "backtest/README_binance.md",
    "backtest/README_crypto.md",
    "backtest/README_crypto_pipeline.md",
    "backtest/README_pipeline.md",
    "backtest/README_statarb.md",
    "backtest/README_xs.md",
    "docs/hyperliquid-integration.md",
    "docs/survivorship-bias-data-sources.md",
    "docs/study-downshift-2026-06-10.md",
    "docs/study-downshift-2026-07-02.md",
    "docs/study-overnight-gap-2026-06-10.md",
    "docs/study-pbo-2026-06-10.md",
    "docs/study-pbo-2026-07-02.md",
    "docs/study-pit-bite-2026-06-10.md",
    "docs/study-pit-membership-2026-06-10.md",
    "research/ai-agents-skills-market-scan.md",
    "research/quant-factor-deep-research.md"
  ],
  "archived_documents": [
    "docs/archive/iteration-log.md",
    "docs/archive/pre-refactor/roadmap.md",
    "docs/archive/pre-refactor/deploy-backend.md",
    "docs/archive/pre-refactor/data-model-api.md",
    "docs/archive/pre-refactor/endpoints.md",
    "docs/archive/pre-refactor/working-apis.md",
    "docs/archive/pre-refactor/need-to-fix-2026-06-10.md",
    "docs/archive/pre-refactor/optimization-2026-06.md",
    "docs/archive/pre-refactor/positioning.md",
    "docs/archive/pre-refactor/cost-estimate-2026-06.md",
    "docs/archive/pre-refactor/self-improving-alpha-loop.md",
    "docs/archive/pre-refactor/backtest-features.md"
  ],
  "classification_exemptions": [
    "feed/screener/*.md",
    "frontend/public/feed/screener/*.md"
  ]
}
```

Merge these keys with the environment, workflow, and command fields accumulated in earlier tasks. The checker must prove each tracked Markdown path belongs to exactly one status array or exactly one generated-artifact exemption, with no overlaps and no unmatched paths.

- [ ] **Step 3: Run the integration test and repair only genuine documentation defects**

Run:

```bash
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
```

Expected: both commands exit 0. If a legacy relative link broke because its file moved, update the link to its exact new relative destination or to the compatibility page; do not disable that file or add a blanket ignore.

- [ ] **Step 4: Create focused documentation CI**

Create `.github/workflows/docs.yml`:

```yaml
name: Documentation checks

on:
  push:
    branches: [main]
  pull_request: {}
  workflow_dispatch: {}

permissions:
  contents: read

concurrency:
  group: docs-${{ github.ref }}
  cancel-in-progress: true

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
      - name: Unit tests
        run: python scripts/tests/test_check_docs.py
      - name: Repository documentation contract
        run: python scripts/check_docs.py
```

There are deliberately no `paths` filters on either `push` or `pull_request`: changes to source-level environment lookups, workflow files with either `.yml` or `.yaml`, package commands, or runtime pins can invalidate documentation even when no Markdown file changed. `fetch-depth: 0` is mandatory because metadata validation must resolve and prove ancestry for older stamped commits, not merely the pull request tip.

After creating the workflow, append this regression to `DocumentationChecks` so the test is never run before its fixture exists:

```python
    def test_docs_workflow_fetches_full_history_for_ancestor_checks(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" / "docs.yml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            workflow,
            r"(?m)^      - uses: actions/checkout@v7\n"
            r"        with:\n"
            r"          fetch-depth: 0$",
        )
```

- [ ] **Step 5: Add `docs.yml` to the workflow inventory and restamp maintained docs**

Add a row for `.github/workflows/docs.yml` describing its triggers, read-only permission, no generated artifacts, concurrency group, and commands. Then run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: stamping prints the current 40-character baseline; unittest reports `OK`; checker reports all documentation checks passed; whitespace check prints nothing.

- [ ] **Step 6: Inspect scope and commit the guard**

Run:

```bash
git status --short
git diff --stat
```

Expected: only the documentation contract, its tests, documentation workflow, workflow inventory, metadata stamps, and link repairs from this task are modified; `AGENTS.md` remains untracked.

Before the commit, run `git diff --name-only` and stage each additional historical or archived Markdown path repaired in Step 3 by its exact printed path. Do not use `git add docs` or `git add .`; the cached whitespace gate below must run only after those exact additions.

Commit:

```bash
git add docs/verification.json scripts/check_docs.py scripts/tests/test_check_docs.py .github/workflows/docs.yml README.md backend/README.md backtest/README.md backtest/FEATURES.md feed/README.md docs/README.md docs/current-architecture.md docs/architecture.md docs/roadmap.md docs/iteration-log.md docs/rfcs/target-architecture.md docs/configuration.md docs/deployment-matrix.md docs/operations/workflows.md docs/data-contracts/feed.md docs/research/index.md docs/compliance.md docs/deploy-backend.md docs/data-model-api.md docs/endpoints.md docs/working-apis.md docs/need-to-fix.md docs/optimization-2026-06.md docs/positioning.md docs/cost-estimate.md docs/self-improving-alpha-loop.md docs/openclaw-integration.md docs/openclaw-stock-notes.md docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md routines/daily-alpha-routine.md routines/methodology.md routines/openclaw-agent-prompts.md routines/openclaw-daily-tasks.md routines/winter-inbox.md
git diff --cached --check
git commit -m "test(docs): enforce truth-first documentation"
```

Expected: the final Stage 1C commit introduces the CI guard and no runtime behavior change.

---

### Task 8: Final Stage 1C Verification and Handoff

**Files:**
- Verify only; no planned file changes.

**Interfaces:**
- Consumes: all Stage 1C commits.
- Produces: evidence that documentation is internally consistent and every published command remains executable.

- [ ] **Step 1: Run the complete offline documentation gate from repository root**

```bash
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/check_docs.py
git diff --check
```

Expected: unittest reports `OK`; checker starts with `docs check passed:` and reports no diagnostics; whitespace check prints nothing.

- [ ] **Step 2: Re-run the exact frontend release matrix documented in README**

From the repository root, execute the exact **Node gate** in Shared Interfaces without modification. Expected: all seven npm commands exit 0, both smoke commands report successful route checks, the App Router handlers remain present, and verification leaves them unchanged.

- [ ] **Step 3: Re-run the exact Python commands documented in README**

From the repository root, execute the exact **Python 3.11 gate** in Shared Interfaces without modification. Expected: all six Python 3.11 locks reproduce exactly, every documented Python command exits 0, and the complete ten-invocation primary-runtime suite passes without creating root-owned worktree files.

- [ ] **Step 4: Confirm repository and documentation status**

```bash
git status --short --branch
git log --oneline -8
```

Expected: branch has no tracked changes; only the pre-existing untracked `AGENTS.md` may remain; recent history shows the focused Stage 1C commits from this plan.

- [ ] **Step 5: Hand off the completed documentation baseline**

Report:

- the exact baseline SHA shown in maintained document metadata;
- the root README path;
- the current architecture and target RFC paths;
- documentation checker and CI paths;
- all commands executed and their pass status;
- any historical page intentionally retained rather than promoted to Current.

Do not claim Stage 2 contracts, DataGateway, analysis-core, or dual-runtime semantic parity are implemented.
