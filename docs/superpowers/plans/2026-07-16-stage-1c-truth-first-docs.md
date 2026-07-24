# Stage 1C Truth-First Documentation Implementation Plan

> **Status:** Accepted implementation plan
> **Scope:** Stage 1C truth-first documentation implementation slice.
> **Last verified commit:** `806ea6515c22af521929b1e485c37cf754cd0c27`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the repository's stale product narrative with a verifiable, truth-first entry point and a small authoritative documentation system that distinguishes current behavior, accepted target architecture, historical research, and archived pre-refactor plans.

**Architecture:** A machine-readable documentation contract in `docs/verification.json` identifies maintained, historical, and archived documents. A standard-library checker validates metadata, local links, environment-variable coverage, documented commands, and workflow inventory; the root and subsystem READMEs then link to focused current-state pages while compatibility pages preserve old documentation URLs.

**Tech Stack:** Markdown, JSON, Python 3.11 standard library, Docker, Git, GitHub Actions, existing Node 20/npm and Python verification commands from Stage 1B.

## Global Constraints

- Stage 1A security fixes and Stage 1B reproducible CI must be complete before this plan starts. Documentation must describe their merged behavior, not the pre-fix behavior.
- Stage 1B owns public verification command names. This plan must use exactly: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test:scripts`, `npm run build:static`, `npm run smoke:static`, `npm run build:server`, `npm run smoke:server`, plus the existing direct Python test commands.
- The exact runtime contract is Node.js `20.20.2`, npm `10.8.2`, Python `3.11.15` primary, and Python `3.12.13` compatibility. Product prose may use the shorter Node 20 / Python 3.11 family names, but every installation, deployment, CI, and verification contract must retain the exact patch versions.
- Static and server profiles receive equal documentation prominence, but current differences must remain explicit until Stage 2 proves semantic parity.
- Do not claim that current quote, OHLCV, or analysis results are same-source or semantically identical across profiles.
- Deterministic interactive technical analysis, the Actions stock-note fallback, and the current local formula-factor factory are rule-based or deterministic and do not call an LLM. Feed provenance is mixed: externally submitted OpenClaw narrative/agent artifacts may be AI-generated, while local factory candidates and fallback notes may be non-LLM. Classify each artifact from its producer, model, and source-report metadata; do not describe the whole product as either “all AI” or “entirely non-LLM.” The factor-factory LLM proposer remains Planned.
- Do not hard-code workflow counts, file counts, refresh counts, transient backtest results, or dated iteration summaries in the root README.
- Do not present TanStack Query, Zustand, Tailwind/shadcn, JWT, Redis, PostgreSQL/TimescaleDB, S3, Celery, RAG, DataGateway, analysis-core, stock_core, or reader-facing atomic manifest publication as current unless the implementation exists at the Stage 1C baseline.
- `FEED_PUBLICATION_MANIFEST` is the current Stage 1A workflow-local Git-staging allowlist. It is not a reader-facing snapshot manifest, completeness contract, manifest-written-last transaction, or previous-complete-snapshot fallback.
- Every Current or Accepted document declares `Status`, `Scope`, and `Last verified commit`. Historical and Archived pages declare that they are not current implementation guidance.
- `Last verified commit` is never typed as a placeholder. `python scripts/check_docs.py --stamp-current` obtains the exact value from `git rev-parse HEAD` and inserts it into every maintained document.
- The stamping command runs before documentation commits, so the recorded commit is the code baseline that was reviewed, not a self-referential documentation commit.
- Preserve existing user-facing documentation URLs with short compatibility pages whenever a current file is moved.
- Documentation and checker code use only repository files and recorded facts; the checker and its unit tests perform no network calls. The reused Stage 1B acceptance gates still require Docker image, npm, and PyPI registry access unless those artifacts are already cached.
- Repository-local documentation commands run through `scripts/run-python311`, which uses the full exact `python:3.11.15` image, proves Git is available, and proves the mounted worktree runs under the non-root host UID/GID. Direct `python scripts/check_docs.py` remains the public command for users already inside the pinned Python environment and for CI.
- Docker or Colima must be able to bind-read/write the checkout root. `scripts/run-python311` fails with an actionable file-sharing error when the checkout itself is invisible to the daemon; it does not implement a risky mirror-and-writeback fallback. For a Docker-visible linked worktree whose `.git` file points outside the shared root, the wrapper copies Git metadata into a mode-`0700` temporary directory inside that worktree, overlays a read-only gitfile/common-directory view in the container, and removes the snapshot on success, ordinary failure, or handled HUP/INT/TERM. Stage 1C runs in the established Docker-visible `/private/tmp` worktree and proves the primary-checkout layout separately with a temporary standalone clone nested under that same visible worktree anchor; it does not reconfigure or restart Colima.
- Frontend and dependency-bearing Python acceptance commands reuse Stage 1B's exact Node `20.20.2` / npm `10.8.2`, full Python `3.11.15`, and full Python `3.12.13` container gates; do not claim verification from the host's unrelated Node/Python versions.
- Current Vercel behavior must be split into three facts: the Next quote/OHLCV route implementation is Implemented; the hard-coded hosted deployment attempted by default is External; and a custom `NEXT_PUBLIC_EDGE_BASE` or self-owned hosted deployment is Optional. There is no supported current configuration that disables the hard-coded Edge attempt entirely.
- Keep the untracked `AGENTS.md` and `.superpowers/` scratch tree out of every commit.

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
- `scripts/tests/test_workflow_security.py` — extend the closed Python-job policy for the focused documentation workflow.
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

### Move, then recreate old path as a current entry point

- `backtest/README.md` → `backtest/README_tqm.md`, then recreate `backtest/README.md` as the maintained backtest subsystem entry point.

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
  "archive_date": "2026-07-24",
  "runtime_contract": {
    "node": "20.20.2",
    "npm": "10.8.2",
    "python_primary": "3.11.15",
    "python_compatibility": ["3.12.13"]
  },
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

The top-level key set is exact and closed: no key may be missing or added. JSON duplicate keys and non-standard numeric constants fail before schema validation. `schema_version` is the non-Boolean integer `1`; `check_all_tracked_markdown` is Boolean; `archive_date` is the exact Stage 1C archive date `2026-07-24`; and `runtime_contract` has exactly the four keys shown above. Arrays contain unique values, the three document categories are mutually exclusive, and every repository path is canonical POSIX-relative text that resolves inside the repository without a symlink escape. Classification exemptions may use one terminal `*.md` component but may not use `**`, `?`, `[]`, backslashes, absolute paths, `.` segments, or `..` segments; the terminal `*` matches only a direct child filename and never crosses `/`.

Every verified CI command object contains exactly `document`, `cwd`, `command`, `kind`, `runtime`, `workflow`, and `job`; entrypoint-only commands contain exactly the first five keys. `kind` is only `ci` or `entrypoint`, and `runtime` is only `node` or `python`. Node commands begin with `npm`; Python commands begin with `python`; CI workflow paths remain inside `.github/workflows/` and end in `.yml` or `.yaml`; entrypoints may not smuggle in `workflow` or `job`. For CI entries, the checker requires an exact non-comment `run` line inside the named job and proves that the matching step's `working-directory`, or its job-level `defaults.run.working-directory`, equals `cwd`; mere appearance elsewhere is insufficient. The checker cross-checks the runtime contract against `.node-version`, `.python-version`, `frontend/package.json`, `backend/runtime.txt`, `backend/Dockerfile`, `render.yaml`, the exact runtime assertions/matrix in `.github/workflows/tests.yml`, the Pages deployment assertions, and every tracked production `setup-python` pin. Workflow inventory is likewise derived from tracked `git ls-files` output, so untracked scratch YAML cannot become documentation policy. The checker requires every tracked Markdown path to appear in exactly one status array or match exactly one declared generated-artifact exemption. Task 7 installs the complete final manifest listed there rather than leaving array population to implementer judgment.

### Controlled Stage 1B acceptance gates

Every later instruction to run the **Node gate** means this exact repository-root command. It runs as the non-root host identity, asserts the exact toolchain, executes `npm ci` plus seven npm scripts, and proves the build left protected source, the lock, generated declarations, and private publication state unchanged:

```bash
expected_uid=$(id -u)
expected_gid=$(id -g)
test "$expected_uid" -ne 0

docker run --rm \
  --user "$expected_uid:$expected_gid" \
  --env EXPECTED_UID="$expected_uid" \
  --env EXPECTED_GID="$expected_gid" \
  --env HOME=/tmp/home \
  --tmpfs /tmp/home:rw,exec,mode=1777 \
  --tmpfs /workspace/frontend/node_modules:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace/frontend \
  node:20.20.2-bookworm-slim \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    test "$(node --version)" = "v20.20.2"
    test "$(npm --version)" = "10.8.2"
    npm ci
    npm run lint
    npm run typecheck
    npm run test:scripts
    NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run build:static
    NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run smoke:static
    env -u NEXT_PUBLIC_BASE_PATH npm run build:server
    env -u NEXT_PUBLIC_BASE_PATH npm run smoke:server
  '

test -f frontend/app/api/quote/route.ts
test -f frontend/app/api/ohlcv/route.ts
test -f frontend/.next/BUILD_ID
test "$(shasum -a 256 frontend/package-lock.json | awk '{print $1}')" = "97875c90208b25596cae8ea55482f4c38295aba18b77287f4a11e32208b563d1"
git diff --exit-code HEAD -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts
test -z "$(git status --porcelain=v1 --untracked-files=all -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts)"
test -z "$(find frontend -maxdepth 1 \( -name '.out-stage-*' -o -name '.out-backup-*' -o -name '.out-publish.lock*' \) -print -quit)"
git diff --check
```

Every later instruction to run the **Python 3.11 gate** means this exact repository-root command. It uses the full Git-capable image, proves the exact non-root identity before creating a venv, installs only the committed hash lock, seeds all six temporary outputs from their committed locks, fetches authoritative hashes without upgrading reviewed pins, and executes ten common entry points plus the two primary-only lock-consistency entry points:

```bash
expected_uid=$(id -u)
expected_gid=$(id -g)
test "$expected_uid" -ne 0

docker run --rm \
  --user "$expected_uid:$expected_gid" \
  --env EXPECTED_UID="$expected_uid" \
  --env EXPECTED_GID="$expected_gid" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --tmpfs /tmp/home:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(python --version 2>&1)" = "Python 3.11.15"
    git --version >/dev/null
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    cp backend/requirements.txt "$tmp/backend.txt"
    cp scripts/requirements.txt "$tmp/scripts.txt"
    cp scripts/requirements-winter-pg.txt "$tmp/winter-pg.txt"
    cp backtest/requirements.txt "$tmp/backtest.txt"
    cp requirements/automation.txt "$tmp/automation.txt"
    cp requirements/ci-py311.txt "$tmp/ci-py311.txt"
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backend.txt" backend/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/scripts.txt" scripts/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/winter-pg.txt" scripts/requirements-winter-pg.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backtest.txt" backtest/requirements.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/automation.txt" requirements/automation.in
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py311.txt" requirements/ci.in
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
    /tmp/venv/bin/python scripts/tests/test_check_lock_consistency.py
    /tmp/venv/bin/python scripts/check_lock_consistency.py --root .
  '
```

Every later instruction to run the **Python 3.12 gate** means this exact repository-root command. It uses the full Git-capable compatibility image, seeds and byte-compares the one compatibility lock, and executes the same ten common entry points:

```bash
expected_uid=$(id -u)
expected_gid=$(id -g)
test "$expected_uid" -ne 0

docker run --rm \
  --user "$expected_uid:$expected_gid" \
  --env EXPECTED_UID="$expected_uid" \
  --env EXPECTED_GID="$expected_gid" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --tmpfs /tmp/home:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13 \
  sh -lc '
    set -eu
    test "$(python --version 2>&1)" = "Python 3.12.13"
    git --version >/dev/null
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py312.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    cp requirements/ci-py312.txt "$tmp/ci-py312.txt"
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
    cmp "$tmp/ci-py312.txt" requirements/ci-py312.txt
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

Do not shorten any gate to host `npm`/`python`, substitute a `-slim` Python image, omit the copy-first lock seeds, omit `--allow-unsafe` or `--no-reuse-hashes`, or omit any lock comparison. The exact acceptance total is eight npm process invocations, six Python 3.11 lock comparisons plus one Python 3.12 lock comparison, twelve Python 3.11 process entry points plus ten Python 3.12 process entry points, and therefore twenty-two expanded Python process entry points across the runtime matrix.

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
expected_uid=$(id -u)
expected_gid=$(id -g)
snapshot_root=
snapshot_gitfile=

cleanup() {
  if [ -n "$snapshot_root" ] && [ -d "$snapshot_root" ]; then
    rm -rf "$snapshot_root"
  fi
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if [ "$expected_uid" -eq 0 ]; then
  echo "scripts/run-python311 refuses to mount the worktree as root" >&2
  exit 1
fi

if [ -f "$repo_root/.git" ]; then
  git_dir=$(git -C "$repo_root" rev-parse --path-format=absolute --git-dir)
  git_common_dir=$(git -C "$repo_root" rev-parse --path-format=absolute --git-common-dir)
  case "$git_dir" in
    "$git_common_dir"/*)
      git_dir_relative=${git_dir#"$git_common_dir"/}
      ;;
    *)
      echo "scripts/run-python311 could not relate the worktree Git directory to its common directory" >&2
      exit 1
      ;;
  esac

  umask 077
  snapshot_root=$(mktemp -d "$repo_root/.run-python311-git.XXXXXX")
  mkdir "$snapshot_root/common"
  cp -R "$git_common_dir/." "$snapshot_root/common/"
  snapshot_name=${snapshot_root##*/}
  snapshot_gitfile="$snapshot_root/gitfile"
  printf 'gitdir: /workspace/%s/common/%s\n' \
    "$snapshot_name" "$git_dir_relative" > "$snapshot_gitfile"
elif [ ! -d "$repo_root/.git" ]; then
  echo "scripts/run-python311 requires a Git worktree" >&2
  exit 1
fi

run_container() {
  if [ -n "$snapshot_gitfile" ]; then
    docker run --rm --init \
      --user "$expected_uid:$expected_gid" \
      --env EXPECTED_UID="$expected_uid" \
      --env EXPECTED_GID="$expected_gid" \
      --env HOME=/tmp/home \
      --env PYTHONDONTWRITEBYTECODE=1 \
      --tmpfs /tmp/home:rw,exec,mode=1777 \
      --volume "$repo_root:/workspace" \
      --volume "$snapshot_gitfile:/workspace/.git:ro" \
      --volume "$snapshot_root/common:/workspace/${snapshot_root##*/}/common:ro" \
      --workdir /workspace \
      python:3.11.15 \
      sh -lc '
        set -eu
        if [ ! -f /workspace/.python-version ] || [ ! -d /workspace/scripts ]; then
          echo "scripts/run-python311: Docker cannot read the checkout root; configure Docker/Colima file sharing for this path" >&2
          exit 1
        fi
        test "$(python --version 2>&1)" = "Python 3.11.15"
        git --version >/dev/null
        test "$(id -u)" = "$EXPECTED_UID"
        test "$(id -g)" = "$EXPECTED_GID"
        test "$(id -u)" -ne 0
        git config --global --add safe.directory /workspace
        test "$(git rev-parse --show-toplevel)" = "/workspace"
        exec "$@"
      ' sh "$@"
  else
    docker run --rm --init \
      --user "$expected_uid:$expected_gid" \
      --env EXPECTED_UID="$expected_uid" \
      --env EXPECTED_GID="$expected_gid" \
      --env HOME=/tmp/home \
      --env PYTHONDONTWRITEBYTECODE=1 \
      --tmpfs /tmp/home:rw,exec,mode=1777 \
      --volume "$repo_root:/workspace" \
      --workdir /workspace \
      python:3.11.15 \
      sh -lc '
        set -eu
        if [ ! -f /workspace/.python-version ] || [ ! -d /workspace/scripts ]; then
          echo "scripts/run-python311: Docker cannot read the checkout root; configure Docker/Colima file sharing for this path" >&2
          exit 1
        fi
        test "$(python --version 2>&1)" = "Python 3.11.15"
        git --version >/dev/null
        test "$(id -u)" = "$EXPECTED_UID"
        test "$(id -g)" = "$EXPECTED_GID"
        test "$(id -u)" -ne 0
        git config --global --add safe.directory /workspace
        test "$(git rev-parse --show-toplevel)" = "/workspace"
        exec "$@"
      ' sh "$@"
  fi
}

if run_container "$@"; then
  status=0
else
  status=$?
fi
exit "$status"
```

Run:

```bash
set -eu
chmod +x scripts/run-python311
scripts/run-python311 python -c 'import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version'
scripts/run-python311 git --version
scripts/run-python311 sh -c 'test "$(id -u)" -ne 0'
host_head=$(git rev-parse HEAD)
test "$(scripts/run-python311 git rev-parse HEAD)" = "$host_head"
test "$(scripts/run-python311 git ls-files '*.md' | wc -l | tr -d ' ')" = "$(git ls-files '*.md' | wc -l | tr -d ' ')"
scripts/run-python311 sh -c '
  set -eu
  tmp=$(mktemp -d)
  trap "rm -rf \"$tmp\"" EXIT
  cd "$tmp"
  git init -q
  printf "probe\n" > sample.txt
  git add sample.txt
  test "$(git ls-files)" = "sample.txt"
  test -z "${GIT_DIR:-}"
  test -z "${GIT_WORK_TREE:-}"
'
run_result=0
scripts/run-python311 sh -c 'exit 7' || run_result=$?
test "$run_result" -eq 7
test -z "$(find . -maxdepth 1 -name '.run-python311-git.*' -print -quit)"
```

Expected: the linked-worktree regression that previously failed now resolves the exact host `HEAD`; tracked Markdown inventory is identical; the command runs as the non-root host UID/GID; an unrelated temporary repository remains independent; status `7` is propagated exactly; and no `.run-python311-git.*` snapshot remains. The copied snapshot is private on the host and overlaid read-only in the container. A daemon that cannot see the checkout root fails before Git discovery with the exact file-sharing diagnostic above. Step 9 proves the same wrapper from a Docker-visible primary checkout with a real `.git` directory.

- [ ] **Step 2: Write failing unit tests for links, metadata, stamping, environments, commands, and workflows**

Create `scripts/tests/test_check_docs.py` with standard-library `unittest`. The tests must construct isolated temporary repositories or call focused pure functions. Include these assertions verbatim in the corresponding tests:

```python
import contextlib
import io
import json
import sys
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_docs import (
    ConfigError,
    check_classification,
    check_command_contracts,
    check_environment_document,
    check_local_links,
    check_metadata,
    check_runtime_contract,
    check_workflow_inventory,
    discover_environment_names,
    github_slug,
    load_config,
    main as check_docs_main,
    stamp_documents,
)


class DocumentationChecks(TestCase):
    @staticmethod
    def track(root: Path, *relative_paths: str) -> None:
        if not (root / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "add", "--", *relative_paths],
            cwd=root,
            check=True,
        )

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
                "docker run --env HOME=/tmp/home python:3.11.15 python\n",
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
            frontend_scripts = root / "frontend" / "scripts"
            frontend_scripts.mkdir(parents=True)
            (frontend_scripts / "smoke-server.mjs").write_text(
                'spawn("node", [], {env: {...process.env, NODE_ENV: "production"}})\n',
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/feed.yaml")
            names = discover_environment_names(root, [])
            self.assertTrue(
                {
                    "FEED_PUBLICATION_MANIFEST",
                    "PAYLOAD",
                    "PORT",
                    "PYTHON_VERSION",
                    "HOME",
                    "NODE_ENV",
                }
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
            self.track(root, ".github/workflows/docs.yml")
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
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run build:static", "kind": "entrypoint", "runtime": "node"}]
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
            contracts = [{"document": "README.md", "cwd": "frontend", "command": "npm run lint", "kind": "ci", "runtime": "node", "workflow": ".github/workflows/tests.yml", "job": "frontend"}]
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
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
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
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
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
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
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
            contracts = [{"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"}]
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
            contracts = [{"document":"backend/README.md","cwd":"backend","command":command,"kind":"entrypoint","runtime":"python"}]
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
            self.track(root, ".github/workflows/tests.yml")
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
            self.track(root, ".github/workflows/guard.yaml")
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
            self.track(root, ".github/workflows/tests.yml")
            errors = check_workflow_inventory(root, "docs/operations/workflows.md")
            self.assertTrue(any("tests.yml" in item.message for item in errors))

    def test_untracked_workflow_scratch_is_not_part_of_inventory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text("name: Tests\n", encoding="utf-8")
            (workflows / "scratch.yml").write_text(
                "name: Untracked scratch\n", encoding="utf-8"
            )
            inventory = root / "docs" / "operations" / "workflows.md"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "# Workflows\n\n"
                "| Workflow | Purpose | Trigger | Command | Target | Permissions | Concurrency | Configuration |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| `tests.yml` | tests | PR | command | none | read | ci | none |\n",
                encoding="utf-8",
            )
            self.track(root, ".github/workflows/tests.yml")
            self.assertEqual(
                check_workflow_inventory(root, "docs/operations/workflows.md"),
                [],
            )

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
            self.track(root, ".github/workflows/tests.yml")
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

    def test_classification_exemptions_match_direct_children_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "feed" / "screener" / "direct.md"
            nested = root / "feed" / "screener" / "nested" / "child.md"
            nested.parent.mkdir(parents=True)
            direct.write_text("# Direct\n", encoding="utf-8")
            nested.write_text("# Nested\n", encoding="utf-8")
            config = {
                "maintained_documents": [],
                "historical_documents": [],
                "archived_documents": [],
                "classification_exemptions": ["feed/screener/*.md"],
            }
            errors = check_classification(root, config, [direct, nested])
            self.assertFalse(any(item.path == "feed/screener/direct.md" for item in errors))
            self.assertTrue(
                any(
                    item.path == "feed/screener/nested/child.md"
                    and item.code == "unclassified-markdown"
                    for item in errors
                )
            )

    def _write_valid_config(self, root: Path) -> Path:
        (root / "docs").mkdir(exist_ok=True)
        (root / "docs" / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (root / "feed" / "screener").mkdir(parents=True, exist_ok=True)
        (root / "frontend" / "public" / "feed" / "screener").mkdir(
            parents=True, exist_ok=True
        )
        config = {
            "schema_version": 1,
            "check_all_tracked_markdown": False,
            "archive_date": "2026-07-24",
            "runtime_contract": {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            },
            "maintained_documents": ["docs/plan.md"],
            "historical_documents": [],
            "archived_documents": [],
            "classification_exemptions": [
                "feed/screener/*.md",
                "frontend/public/feed/screener/*.md",
            ],
            "environment_document": None,
            "platform_environment_names": [],
            "workflow_inventory_document": None,
            "verified_commands": [],
        }
        path = root / "docs" / "verification.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_config_loader_rejects_duplicate_keys_and_nonstandard_constants(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            for raw in (
                '{"schema_version":1,"schema_version":1}',
                '{"schema_version":1,"value":NaN}',
                '{"schema_version":1,"value":Infinity}',
            ):
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_rejects_missing_unknown_wrong_type_and_duplicates(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            cases = []

            missing = json.loads(json.dumps(base))
            missing.pop("verified_commands")
            cases.append(("missing-key", missing))

            unknown = json.loads(json.dumps(base))
            unknown["unknown"] = True
            cases.append(("unknown-key", unknown))

            boolean_schema = json.loads(json.dumps(base))
            boolean_schema["schema_version"] = True
            cases.append(("boolean-schema", boolean_schema))

            wrong_boolean = json.loads(json.dumps(base))
            wrong_boolean["check_all_tracked_markdown"] = "false"
            cases.append(("wrong-boolean", wrong_boolean))

            bad_date = json.loads(json.dumps(base))
            bad_date["archive_date"] = "2026-7-24"
            cases.append(("bad-date", bad_date))

            wrong_canonical_date = json.loads(json.dumps(base))
            wrong_canonical_date["archive_date"] = "2026-07-23"
            cases.append(("wrong-canonical-date", wrong_canonical_date))

            wrong_runtime = json.loads(json.dumps(base))
            wrong_runtime["runtime_contract"]["python_compatibility"] = "3.12.13"
            cases.append(("wrong-runtime-type", wrong_runtime))

            extra_runtime = json.loads(json.dumps(base))
            extra_runtime["runtime_contract"]["extra"] = "not-allowed"
            cases.append(("extra-runtime-key", extra_runtime))

            repeated_compatibility = json.loads(json.dumps(base))
            repeated_compatibility["runtime_contract"]["python_compatibility"] = [
                "3.12.13",
                "3.12.13",
            ]
            cases.append(("duplicate-compatibility", repeated_compatibility))

            primary_is_compatibility = json.loads(json.dumps(base))
            primary_is_compatibility["runtime_contract"]["python_compatibility"] = [
                "3.11.15"
            ]
            cases.append(("primary-is-compatibility", primary_is_compatibility))

            duplicate_document = json.loads(json.dumps(base))
            duplicate_document["maintained_documents"] *= 2
            cases.append(("duplicate-document", duplicate_document))

            overlap = json.loads(json.dumps(base))
            overlap["historical_documents"] = ["docs/plan.md"]
            cases.append(("overlapping-document", overlap))

            invalid_environment = json.loads(json.dumps(base))
            invalid_environment["platform_environment_names"] = ["bad-name"]
            cases.append(("invalid-environment", invalid_environment))

            duplicate_environment = json.loads(json.dumps(base))
            duplicate_environment["platform_environment_names"] = ["PORT", "PORT"]
            cases.append(("duplicate-environment", duplicate_environment))

            invalid_exemption = json.loads(json.dumps(base))
            invalid_exemption["classification_exemptions"] = ["feed/**/*.md"]
            cases.append(("recursive-exemption", invalid_exemption))

            for label, value in cases:
                with self.subTest(label=label):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_rejects_paths_outside_the_repository(self):
        with TemporaryDirectory() as tmp:
            outer = Path(tmp)
            root = outer / "repo"
            root.mkdir()
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            outside = outer / "outside.md"
            outside.write_text("# Outside\n", encoding="utf-8")
            link = root / "docs" / "linked.md"
            link.symlink_to(outside)
            for label, relative in (
                ("absolute", str(outside)),
                ("parent", "../outside.md"),
                ("backslash", r"docs\plan.md"),
                ("dot-segment", "docs/./plan.md"),
                ("symlink", "docs/linked.md"),
            ):
                with self.subTest(label=label):
                    value = json.loads(json.dumps(base))
                    value["maintained_documents"] = [relative]
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_enforces_command_kind_runtime_and_exact_keys(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            readme = root / "README.md"
            readme.write_text("# Project\n", encoding="utf-8")
            (root / "frontend").mkdir(exist_ok=True)
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "tests.yml").write_text(
                "jobs:\n  frontend:\n    steps: []\n", encoding="utf-8"
            )
            base["maintained_documents"].append("README.md")
            valid_ci = {
                "document": "README.md",
                "cwd": "frontend",
                "command": "npm run lint",
                "kind": "ci",
                "runtime": "node",
                "workflow": ".github/workflows/tests.yml",
                "job": "frontend",
            }
            cases = []
            for label, mutation in (
                ("invalid-kind", {"kind": "maybe"}),
                ("non-string-kind", {"kind": []}),
                ("invalid-runtime", {"runtime": "ruby"}),
                ("non-string-runtime", {"runtime": []}),
                ("runtime-mismatch", {"runtime": "python"}),
                ("cwd-escape", {"cwd": "../frontend"}),
                ("workflow-escape", {"workflow": "../tests.yml"}),
                ("invalid-job", {"job": "bad job"}),
                ("extra-key", {"extra": True}),
                ("glued-semicolon", {"command": "npm run lint;echo injected"}),
                ("glued-pipe", {"command": "npm run lint|cat"}),
                ("redirection", {"command": "npm run lint>captured.txt"}),
                ("command-substitution", {"command": "npm run lint$(echo injected)"}),
                ("backtick-substitution", {"command": "npm run lint`echo injected`"}),
            ):
                item = dict(valid_ci)
                item.update(mutation)
                cases.append((label, [item]))
            missing_job = dict(valid_ci)
            missing_job.pop("job")
            cases.append(("ci-missing-job", [missing_job]))
            entrypoint_with_ci_location = dict(valid_ci)
            entrypoint_with_ci_location["kind"] = "entrypoint"
            cases.append(("entrypoint-with-ci-location", [entrypoint_with_ci_location]))
            cases.append(("duplicate-contract", [valid_ci, dict(valid_ci)]))

            for label, commands in cases:
                with self.subTest(label=label):
                    value = json.loads(json.dumps(base))
                    value["verified_commands"] = commands
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(root, path)

    def test_config_loader_accepts_repository_root_command_cwd(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_valid_config(root)
            base = json.loads(path.read_text(encoding="utf-8"))
            base["verified_commands"] = [
                {
                    "document": "docs/plan.md",
                    "cwd": ".",
                    "command": "python scripts/check_docs.py",
                    "kind": "entrypoint",
                    "runtime": "python",
                }
            ]
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(load_config(root, path), base)

    def test_runtime_contract_detects_version_and_matrix_drift(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend").mkdir()
            (root / "backend").mkdir()
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (root / ".node-version").write_text("20.20.2\n", encoding="utf-8")
            (root / ".python-version").write_text("3.11.15\n", encoding="utf-8")
            backend_runtime = root / "backend" / "runtime.txt"
            backend_runtime.write_text("python-3.11.15\n", encoding="utf-8")
            dockerfile = root / "backend" / "Dockerfile"
            dockerfile.write_text("FROM python:3.11.15-slim\n", encoding="utf-8")
            render = root / "render.yaml"
            render.write_text(
                'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.15"\n',
                encoding="utf-8",
            )
            (root / "frontend" / "package.json").write_text(
                json.dumps(
                    {
                        "packageManager": "npm@10.8.2",
                        "engines": {"node": "20.20.2", "npm": "10.8.2"},
                    }
                ),
                encoding="utf-8",
            )
            workflow = workflows / "tests.yml"
            exact_workflow = (
                "jobs:\n  python:\n    steps:\n"
                "      - uses: actions/setup-python@v6\n"
                "        with:\n"
                "          python-version: ${{ matrix.python_version }}\n"
                'test "$(node --version)" = "v20.20.2"\n'
                'test "$(npm --version)" = "10.8.2"\n'
                '          - python_version: "3.11.15"\n'
                '          - python_version: "3.12.13"\n'
            )
            workflow.write_text(exact_workflow, encoding="utf-8")
            deploy = workflows / "deploy-pages.yml"
            exact_deploy = (
                "steps:\n"
                "  - uses: actions/setup-node@v7\n"
                "    with:\n"
                "      node-version-file: .node-version\n"
                'test "$(node --version)" = "v20.20.2"\n'
                'test "$(npm --version)" = "10.8.2"\n'
            )
            deploy.write_text(exact_deploy, encoding="utf-8")
            production = workflows / "alpha-routine.yml"
            exact_production = (
                "steps:\n"
                "  - uses: actions/setup-python@v6\n"
                "    with:\n"
                "      python-version-file: .python-version\n"
            )
            production.write_text(exact_production, encoding="utf-8")
            self.track(
                root,
                ".github/workflows/tests.yml",
                ".github/workflows/deploy-pages.yml",
                ".github/workflows/alpha-routine.yml",
            )
            contract = {
                "node": "20.20.2",
                "npm": "10.8.2",
                "python_primary": "3.11.15",
                "python_compatibility": ["3.12.13"],
            }
            self.assertEqual(check_runtime_contract(root, contract), [])
            mutations = (
                (root / ".node-version", "20.20.3\n"),
                (root / ".python-version", "3.11.14\n"),
                (backend_runtime, "python-3.11.14\n"),
                (dockerfile, "FROM python:3.11.14-slim\n"),
                (
                    render,
                    'envVars:\n  - key: PYTHON_VERSION\n    value: "3.11.14"\n',
                ),
                (
                    render,
                    'envVars:\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.14"\n'
                    '  - key: UNRELATED_VERSION\n'
                    '    value: "3.11.15"\n',
                ),
                (
                    render,
                    'envVars:\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.15"\n'
                    '  - key: PYTHON_VERSION\n'
                    '    value: "3.11.15"\n',
                ),
                (
                    root / "frontend" / "package.json",
                    '{"packageManager":"npm@10.8.1","engines":{"node":"20.20.2","npm":"10.8.1"}}',
                ),
                (
                    workflow,
                    exact_workflow.replace(
                        '          - python_version: "3.12.13"\n', ""
                    ),
                ),
                (
                    deploy,
                    exact_deploy.replace("v20.20.2", "v20.20.1"),
                ),
                (
                    production,
                    exact_production.replace(
                        "python-version-file: .python-version",
                        'python-version: "3.11.14"',
                    ),
                ),
            )
            for target, replacement in mutations:
                with self.subTest(target=target.name):
                    original = target.read_text(encoding="utf-8")
                    target.write_text(replacement, encoding="utf-8")
                    self.assertTrue(check_runtime_contract(root, contract))
                    target.write_text(original, encoding="utf-8")

    def test_archived_metadata_requires_exact_archive_date(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "archive.md"
            page.write_text(
                "# Archive\n\n"
                "> **Status:** Archived; not current implementation guidance\n"
                "> **Scope:** Historical record.\n",
                encoding="utf-8",
            )
            errors = check_metadata(
                root, [], [], ["archive.md"], archive_date="2026-07-24"
            )
            self.assertTrue(any(item.code == "missing-archive-date" for item in errors))
            page.write_text(
                "# Archive\n\n"
                "> **Status:** Archived; not current implementation guidance\n"
                "> **Scope:** Historical record.\n"
                "> **Archived on:** 2026-07-16\n",
                encoding="utf-8",
            )
            errors = check_metadata(
                root, [], [], ["archive.md"], archive_date="2026-07-24"
            )
            self.assertTrue(any(item.code == "invalid-archive-date" for item in errors))

    def test_cli_rejects_config_path_escape_without_traceback(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            returncode = check_docs_main(["--config", "../outside.json"])
        self.assertEqual(returncode, 2)
        self.assertIn("documentation configuration error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


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


def check_runtime_contract(root: Path, contract: dict) -> list[Diagnostic]:
    errors: list[Diagnostic] = []

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
        assertions = (
            f'test "$(node --version)" = "v{contract["node"]}"',
            f'test "$(npm --version)" = "{contract["npm"]}"',
        )
        for assertion in assertions:
            if assertion not in workflow_text:
                errors.append(
                    Diagnostic(
                        ".github/workflows/tests.yml",
                        1,
                        "workflow-runtime-assertion-drift",
                        f"missing exact assertion: {assertion}",
                    )
                )
        actual_python_matrix = re.findall(
            r'(?m)^\s*-\s+python_version:\s*["\']'
            r"([0-9]+\.[0-9]+\.[0-9]+)"
            r'["\']\s*$',
            workflow_text,
        )
        expected_python_matrix = [
            contract["python_primary"],
            *contract["python_compatibility"],
        ]
        if actual_python_matrix != expected_python_matrix:
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
        required_deploy_lines = (
            "node-version-file: .node-version",
            f'test "$(node --version)" = "v{contract["node"]}"',
            f'test "$(npm --version)" = "{contract["npm"]}"',
        )
        for required in required_deploy_lines:
            if required not in deploy_text:
                errors.append(
                    Diagnostic(
                        ".github/workflows/deploy-pages.yml",
                        1,
                        "deployment-runtime-drift",
                        f"missing exact runtime contract line: {required}",
                    )
                )

    def action_step_blocks(text: str, action: str) -> list[str]:
        lines = text.splitlines()
        blocks: list[str] = []
        for index, line in enumerate(lines):
            if re.search(rf"-\s+uses:\s*{re.escape(action)}@", line) is None:
                continue
            base_indent = len(line) - len(line.lstrip())
            block = [line]
            cursor = index + 1
            while cursor < len(lines):
                candidate = lines[cursor]
                stripped = candidate.lstrip()
                indent = len(candidate) - len(stripped)
                if stripped and indent <= base_indent:
                    break
                block.append(candidate)
                cursor += 1
            blocks.append("\n".join(block))
        return blocks

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
        for block in action_step_blocks(text, "actions/setup-python"):
            allowed = (
                "python-version-file: .python-version" in block
                or "python-version-file: trusted/.python-version" in block
                or (
                    workflow.name == "tests.yml"
                    and "python-version: ${{ matrix.python_version }}" in block
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
        if re.search(r"^> \*\*Last verified commit:\*\* `[^`]+`$", text, re.MULTILINE):
            text = re.sub(r"^> \*\*Last verified commit:\*\* `[^`]+`$", line, text, count=1, flags=re.MULTILINE)
        else:
            text, count = re.subn(r"^(> \*\*Scope:\*\* .+)$", rf"\1\n{line}", text, count=1, flags=re.MULTILINE)
            if count != 1:
                raise ValueError(f"{relative} has no Scope line for stamping")
        path.write_text(text, encoding="utf-8")


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
```

- [ ] **Step 5: Add the bootstrap verification manifest**

Create `docs/verification.json` with the approved program design and its three accepted execution plans under the initial maintained contract. Full-repository link checking and operational checks remain disabled until the later content tasks populate their authoritative pages:

```json
{
  "schema_version": 1,
  "check_all_tracked_markdown": false,
  "archive_date": "2026-07-24",
  "runtime_contract": {
    "node": "20.20.2",
    "npm": "10.8.2",
    "python_primary": "3.11.15",
    "python_compatibility": ["3.12.13"]
  },
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

- [ ] **Step 9: Prove the committed wrapper from a primary checkout layout**

Create a temporary non-linked clone inside the already Docker-visible Stage 1C worktree anchor, run the committed wrapper there, and remove it on every exit. Do not create a new top-level `/private/tmp` bind root: the current Colima daemon exposes the established worktree root but does not reliably discover newly created sibling bind roots.

```bash
set -eu
mkdir -p .superpowers
proof_root=$(mktemp -d "$PWD/.superpowers/primary-proof.XXXXXX")
cleanup_proof() { rm -rf "$proof_root"; }
trap cleanup_proof EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
branch=$(git branch --show-current)
expected_head=$(git rev-parse HEAD)
git clone --no-local --quiet --branch "$branch" --single-branch "$PWD" "$proof_root/repo"
test -d "$proof_root/repo/.git"
test ! -f "$proof_root/repo/.git"
test "$("$proof_root/repo/scripts/run-python311" git rev-parse HEAD)" = "$expected_head"
test "$("$proof_root/repo/scripts/run-python311" git ls-files '*.md' | wc -l | tr -d ' ')" = "$(git ls-files '*.md' | wc -l | tr -d ' ')"
"$proof_root/repo/scripts/run-python311" sh -c '
  set -eu
  tmp=$(mktemp -d)
  trap "rm -rf \"$tmp\"" EXIT
  cd "$tmp"
  git init -q
  printf "probe\n" > sample.txt
  git add sample.txt
  test "$(git ls-files)" = "sample.txt"
'
cleanup_proof
trap - EXIT HUP INT TERM
test ! -e "$proof_root"
test -z "$(find .superpowers -maxdepth 1 -name 'primary-proof.*' -print -quit)"
```

Expected: the standalone clone has a real `.git` directory, the exact committed `HEAD` and Markdown inventory match the source checkout, the independent temporary repository works, and the proof directory is absent afterward. This proves the primary-checkout code path without copying uncommitted files into `main` or changing Colima configuration. It does not waive the explicit checkout-root file-sharing prerequisite.

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

Expected: status shows no tracked changes and may show only the known untracked `AGENTS.md` and `.superpowers/` scratch paths; `git rev-parse HEAD` prints one 40-character SHA. Do not copy it manually into files; the stamping command performs that action after the manifest is updated.

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
- The Next quote/OHLCV route implementation is **Implemented**. The hard-coded `https://stock-analysis-ten-phi.vercel.app` deployment attempted by default is **External**. A custom `NEXT_PUBLIC_EDGE_BASE` or a self-owned hosted deployment is **Optional**. Absent `NEXT_PUBLIC_EDGE_BASE` and a same-origin `*.vercel.app` host, current code attempts that hard-coded deployment; there is no supported current setting that disables this attempt entirely.
- Quote and OHLCV requests have distinct source chains. Quotes use fresh memory/browser cache, optional FastAPI for non-index symbols, Edge for non-crypto symbols, a fresh live snapshot when at least three stock quotes remain, direct Binance/Yahoo paths, then a bounded stale quote. OHLCV uses fresh browser cache, Edge first for every market including crypto, optional FastAPI for non-index symbols, direct Binance/Yahoo paths, then a bounded stale bar series.
- Deterministic analysis has duplicate TypeScript and Python implementations.
- Backend persistence is SQLite by default; PostgreSQL is optional Winter tooling, not a base runtime requirement.
- Feed artifacts have multiple writers and uneven schema coverage. The current `FEED_PUBLICATION_MANIFEST` is only the Stage 1A workflow-local Git-staging allowlist. A reader-facing atomic snapshot manifest written last, completeness validation, and fallback to the previous complete snapshot are **Planned**, not current behavior.

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
> **Archived on:** 2026-07-24
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
AUTOMERGE_ATTESTATION_CONTEXT
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
HEAD_SHA
FRONTEND_RESULT
PYTHON_RESULT
UPDATE_TYPE
PYTHONDONTWRITEBYTECODE
PYTHONUNBUFFERED
PIP_DISABLE_PIP_VERSION_CHECK
PYTHONPATH
PYTHON_VERSION
EXPECTED_UID
EXPECTED_GID
```

Separate user-facing configuration from internal build/workflow plumbing. `NEXT_BUILD_PROFILE`, `STATIC_FEED_SOURCE`, `SMOKE_PORT`, `NEXT_TELEMETRY_DISABLED`, `NODE_ENV`, `FEED_PUBLICATION_MANIFEST`, `PAYLOAD`, `REPO`, `PR_NUMBER`, `REPORT`, `HEAD_SHA`, `AUTOMERGE_ELIGIBLE_LABEL`, `AUTOMERGE_ATTESTATION_CONTEXT`, `PACKAGE_ECOSYSTEM`, `UPDATE_TYPE`, `FRONTEND_RESULT`, `PYTHON_RESULT`, `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `PIP_DISABLE_PIP_VERSION_CHECK`, `PYTHONPATH`, `EXPECTED_UID`, `EXPECTED_GID`, the container-local `HOME`, and Render's pinned `PYTHON_VERSION` are internal execution contracts, not settings most users should export. `EXPECTED_UID` and `EXPECTED_GID` are used by `scripts/run-python311` and the controlled Node/Python container acceptance gates to verify the mounted worktree runs under the host UID/GID. `HEAD_SHA` is consumed by the hardened Dependabot attestation/merge path, `AUTOMERGE_ATTESTATION_CONTEXT` identifies its attestation context, and `FRONTEND_RESULT` / `PYTHON_RESULT` carry matrix outcomes into the aggregate test gate. Distinguish origins precisely: `PORT`, `GITHUB_OUTPUT`, `GITHUB_WORKSPACE`, `GITHUB_REPOSITORY`, and `RUNNER_TEMP` are runner/platform values; `GITHUB_TOKEN` and `GH_TOKEN` are explicitly mapped into workflow environments; and current `GITHUB_RUN_URL` is composed by the workflow from GitHub context rather than injected automatically. State that the current FastAPI clients concatenate `API_BASE` / `NEXT_PUBLIC_API_BASE` literally with `/api/v1/...`, so either value must omit a trailing slash until client normalization is implemented; the Edge path normalizes its selected base before adding route paths. State that each unset endpoint disables or changes its adapter according to current code, except the Edge path: absent a custom or same-origin base, current code still attempts the hard-coded hosted deployment and has no supported disable setting. Do not retain the stale `VERCEL` or `PR_URL` names from pre-Stage-1B prose.

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
## External-state observation (dated; not a repository contract)
## Rollback
## Current gaps before semantic parity
```

Static and server receive equal table columns. Explicitly state that the common UI exists today but semantic parity is a Stage 2 acceptance target. Include the exact, distinct quote and OHLCV fallback chains recorded in Task 2; a configured FastAPI base does not imply that every request actually uses FastAPI. Classify the Vercel facts separately: Next quote/OHLCV route code is **Implemented**, the hard-coded hosted endpoint attempted by default is **External**, and a custom `NEXT_PUBLIC_EDGE_BASE` or self-owned deployment is **Optional**. State that no supported current configuration disables the hard-coded attempt entirely.

Separate repository contracts from a dated external-state observation. Record that the 2026-07-24 audit found: the GitHub `API_BASE` Variable points at the Render service, currently includes a trailing slash, and no `EDGE_BASE` Variable is configured; the canonical single-slash Render health route responded successfully, but the repository's literal `API_BASE + "/api/v1/..."` concatenation produces a double-slash health URL that returned 404, so the configured FastAPI integration must not be called healthy until the Variable is normalized or the clients normalize it; GitHub Pages and the hard-coded Vercel alias responded successfully, but the latest successful Pages deployment and the latest READY production deployment currently bound to that hard-coded alias still represented 2026-06-11 commits rather than Stage 1B (a newer READY preview exists and is not what that alias serves); and the Vercel project setting reported Node 24.x while the repository contract is Node 20.20.2. Label every item observational and drift-prone, link the refresh commands or run/deployment references, do not expose secret values, and require both the `API_BASE` trailing-slash mismatch and the Vercel runtime mismatch to be resolved before relying on those hosted paths in a new production deployment. Railway/Fly remain repository-file-based options only; do not imply a live deployment where none was verified.

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

Under **Current publication limitations**, document that `FEED_PUBLICATION_MANIFEST` is the Stage 1A workflow-local Git-staging allowlist: it constrains which locally validated paths a workflow may stage, but it is not published for readers and provides no snapshot-completeness or rollback contract.

Under **Target manifest publisher**, label the reader-facing design **Planned** and require a versioned manifest that enumerates one complete snapshot, validates completeness before exposure, is written last as the atomic publication point, and lets readers fall back to the previous complete manifest when the newest snapshot is incomplete or invalid. Do not reuse the Stage 1A staging allowlist as if it already satisfied this reader contract.

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
> **Archived on:** 2026-07-24
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

Create `backtest/FEATURES.md` as a short Current compatibility page pointing to `backtest/README.md`, `docs/research/index.md`, and the archived inventory at `../docs/archive/pre-refactor/backtest-features.md`. Add this exact metadata immediately below the title of `docs/archive/pre-refactor/backtest-features.md` without rewriting its body:

```markdown
> **Status:** Archived; not current implementation guidance
> **Scope:** Historical pre-refactor record preserved for provenance.
> **Archived on:** 2026-07-24
```

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

The installation and deployment contract must name exact Python `3.11.15` as primary and `3.12.13` as the compatibility runtime, use the committed hashed requirements locks, and link to the repository-wide Python gates. Short prose may say Python 3.11, but no command, container, CI, or deployment contract may loosen the exact patch versions.

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

Distinguish the two manifest concepts explicitly: current `FEED_PUBLICATION_MANIFEST` is only the Stage 1A workflow-local Git-staging allowlist; the reader-facing complete-snapshot manifest, manifest-written-last publication point, completeness validation, and previous-complete-snapshot fallback are Planned.

- [ ] **Step 3: Register commands in the verification manifest**

Add these exact command contracts. For every `kind: ci` entry, the checker requires the exact command inside the named workflow and job rather than accepting it anywhere in Actions YAML:

```json
[
  {"document":"backend/README.md","cwd":"backend","command":"python -m pip install --require-hashes -r requirements.txt","kind":"entrypoint","runtime":"python"},
  {"document":"backend/README.md","cwd":"backend","command":"python tests/test_backend.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"backend/README.md","cwd":"backend","command":"python tests/test_api.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_validate_feed.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_validation_security.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_ingress.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_validate_feed_cli.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_feed_publication.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"feed/README.md","cwd":".","command":"python scripts/tests/test_workflow_security.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"}
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

Then, from the repository root, execute the exact **Python 3.11 gate** in Shared Interfaces without modification. Expected: the documentation checker passes; all six Python 3.11 lock comparisons match; the ten common process entry points pass (two backend plus eight automation/feed/security commands); and both primary-only lock-consistency process entry points pass, for twelve Python 3.11 process entry points total. This step must not use host Python.

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

- Implemented: Next.js UI routes, the repository's Next quote/OHLCV route implementation, eight market groups plus indexes, quote/OHLCV adapters, local watchlist/alerts/portfolio, rule-based technical panels, Git-backed feed consumption, research/backtest code, the deterministic Actions stock-note fallback, and the local deterministic/non-LLM formula-factor factory.
- Optional: FastAPI, a custom `NEXT_PUBLIC_EDGE_BASE` or self-owned deployment of the Next Edge routes, hosted backend, Winter/PostgreSQL projection.
- External: the hard-coded `https://stock-analysis-ten-phi.vercel.app` deployment attempted by default, public market providers, externally submitted OpenClaw narrative/agent artifacts, Hyperliquid, GitHub Actions scheduling, hosting platforms.
- Planned: the factor-factory LLM proposer, generated cross-language contracts, explicit DataGateway profiles, shared deterministic analysis-core, stock_core, staged atomic feed manifests, full semantic parity CI.

Every row includes a limitation or authority link. Market catalog coverage must not be described as equal provider depth. State next to the Vercel rows that no supported current configuration disables the hard-coded hosted attempt entirely.

The page map lists exactly these eleven implemented routes and no planned screens: `/`, `/symbol`, `/desk`, `/screener`, `/tracker`, `/intel`, `/reports`, `/portfolio`, `/alerts`, `/sources`, and `/help`.

- [ ] **Step 3: Document two equal profiles without claiming current parity**

Use a side-by-side table for Static and Server with rows for prerequisites, primary data path, optional adapters, persistence, deployment variants, build command, smoke command, and current limitations. State:

- Static: exact Node `20.20.2` / npm `10.8.2`, GitHub Pages/local static build, feed and browser-safe sources, and the current Edge behavior described below.
- Server: exact Node `20.20.2` / npm `10.8.2` plus primary Python `3.11.15` (compatibility Python `3.12.13`), the same frontend with FastAPI, SQLite cache/bar store, optional hosted deployment.
- Shared semantic parity is the accepted target; current source order and analysis duplication remain documented gaps.

The matrix and data-source section must also expose the current hidden coupling: when neither `NEXT_PUBLIC_EDGE_BASE` nor same-origin Vercel applies, the frontend attempts the hard-coded external Edge deployment, and no supported current setting disables that attempt entirely. Show the distinct quote and OHLCV source chains from `docs/current-architecture.md`; do not compress them into a fictitious single data layer.

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
npm run test:scripts
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

The Python block is intentionally a compact local smoke subset, not the complete Python CI matrix; the authoritative release gate remains the exact Python 3.11 and 3.12 container gates in this plan. Quick-start development commands may additionally use the existing `npm run dev` and `python -m uvicorn app.main:app --reload --port 8000`; mark them as long-running entry points rather than CI verification.

- [ ] **Step 5: Remove stale and unsafe claims**

Confirm the rewritten file contains none of these strings:

```text
P1 MVP 编码中
全程非 LLM
三者同源一致
全站单一报价数据层
17 个 GitHub Actions
13 个定时任务
AI 情绪分析
AI 助手.*自然语言查询
```

Do not copy Cycle 1–11 narratives, OpenClaw round counts, dated “new feature” lists, or backtest metrics into another README section.

- [ ] **Step 6: Register root commands, stamp, and verify**

Add `README.md` to maintained documents. Register every documented release command against the workflow/job that actually executes it, and register long-running local commands as entry points:

```json
[
  {"document":"README.md","cwd":"frontend","command":"npm ci","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run lint","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run typecheck","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run test:scripts","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run build:static","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run smoke:static","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run build:server","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"frontend","command":"npm run smoke:server","kind":"ci","runtime":"node","workflow":".github/workflows/tests.yml","job":"frontend"},
  {"document":"README.md","cwd":"backend","command":"python tests/test_backend.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":"backend","command":"python tests/test_api.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":".","command":"python scripts/tests/test_chan_engine.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":".","command":"python scripts/tests/test_validate_feed.py","kind":"ci","runtime":"python","workflow":".github/workflows/tests.yml","job":"python"},
  {"document":"README.md","cwd":"frontend","command":"npm run dev","kind":"entrypoint","runtime":"node"},
  {"document":"README.md","cwd":"backend","command":"python -m uvicorn app.main:app --reload --port 8000","kind":"entrypoint","runtime":"python"}
]
```

Run:

```bash
scripts/run-python311 python scripts/check_docs.py --stamp-current --document README.md
scripts/run-python311 python scripts/check_docs.py
scan_status=0
rg -n "P1 MVP 编码中|全程非 LLM|三者同源一致|全站单一报价数据层|17 个 GitHub Actions|13 个定时任务|AI 情绪分析|AI 助手.*自然语言查询" README.md || scan_status=$?
case "$scan_status" in
  0)
    echo "README contains a forbidden stale claim" >&2
    exit 1
    ;;
  1) ;;
  *) exit "$scan_status" ;;
esac
git diff --check
```

Expected: checker passes; the explicit three-state `rg` guard accepts only status 1 (no matches), rejects status 0 (a stale claim matched), propagates tool errors greater than 1, and the whitespace check prints nothing.

- [ ] **Step 7: Execute every documented release command**

From the repository root, execute the exact **Node gate**, exact **Python 3.11 gate**, and exact **Python 3.12 gate** in Shared Interfaces, without modification. The Node gate runs `npm ci` plus all seven documented frontend scripts. The Python gates run the complete runtime matrix, not just the compact README smoke subset. Expected: deterministic installs succeed; lint, typecheck, and `test:scripts` exit 0; both builds and both smoke suites pass; six Python 3.11 plus one Python 3.12 lock comparisons match; and the process matrix passes twelve Python 3.11 plus ten Python 3.12 entry points, twenty-two total. This step must not use host Node or Python.

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
- Modify: `scripts/tests/test_workflow_security.py`
- Create: `.github/workflows/docs.yml`
- Modify: `docs/operations/workflows.md`
- Modify: every maintained document listed by `docs/verification.json` (metadata restamp)

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
          persist-credentials: false
      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
      - name: Verify exact Python, Git, and non-root identity
        run: |
          test "$(python --version 2>&1)" = "Python 3.11.15"
          git --version >/dev/null
          test "$(id -u)" -ne 0
      - name: Unit tests
        run: python scripts/tests/test_check_docs.py
      - name: Repository documentation contract
        run: python scripts/check_docs.py
```

There are deliberately no `paths` filters on either `push` or `pull_request`: changes to source-level environment lookups, workflow files with either `.yml` or `.yaml`, package commands, or runtime pins can invalidate documentation even when no Markdown file changed. `fetch-depth: 0` is mandatory because metadata validation must resolve and prove ancestry for older stamped commits, not merely the pull request tip.

The Stage 1B workflow-policy test intentionally fails closed when a new Python job appears. In the same change, update `scripts/tests/test_workflow_security.py` rather than weakening that policy:

```python
DOCUMENTATION_PYTHON_JOB = ("docs.yml", "docs")
EXPECTED_PYTHON_POLICY_JOBS = set(PRODUCTION_PYTHON_JOBS) | {
    ("tests.yml", "python"),
    DOCUMENTATION_PYTHON_JOB,
}
```

Replace the literal `raw_setup_count == parsed_setup_count == 17` assertion with:

```python
    require_workflow_policy(
        raw_setup_count
        == parsed_setup_count
        == len(EXPECTED_PYTHON_POLICY_JOBS),
        "setup-python raw/parsed occurrence count changed",
    )
```

Extend the canonical-interpreter loop to `set(PRODUCTION_PYTHON_JOBS) | {DOCUMENTATION_PYTHON_JOB}` so every direct interpreter token in the documentation job must be the bare `python` token. After the generic setup inventory/action-pin assertions, require the single documentation setup step to equal `FINAL_SETUP_STANDARD` exactly:

```python
    docs_setup = setup_inventory[DOCUMENTATION_PYTHON_JOB][0][0]["raw"]
    require_workflow_policy(
        docs_setup == FINAL_SETUP_STANDARD,
        "docs.yml/docs setup exception changed",
    )
```

Do not add the documentation job to `PRODUCTION_PYTHON_JOBS`, `DEPENDENCY_JOBS`, the protected production-workflow hash, or the install inventory: it is a separate standard-library policy job with no dependency installation.

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
            r"          fetch-depth: 0\n"
            r"          persist-credentials: false$",
        )
        self.assertIn(
            'test "$(python --version 2>&1)" = "Python 3.11.15"',
            workflow,
        )
        self.assertRegex(
            workflow,
            r"(?m)^      - uses: actions/setup-python@v6\n"
            r"        with:\n"
            r"          python-version-file: .python-version$",
        )
        self.assertIn("git --version >/dev/null", workflow)
        self.assertIn('test "$(id -u)" -ne 0', workflow)
```

- [ ] **Step 5: Track `docs.yml`, add its basename to the workflow inventory, and restamp maintained docs**

Stage the newly created workflow first because the checker intentionally inventories only tracked paths. Add exactly one row keyed by the basename `docs.yml`—not `.github/workflows/docs.yml`—describing its triggers, read-only permission, no generated artifacts, concurrency group, and commands. This makes the final inventory cover 19 tracked workflow basenames while keeping that count out of the root README. Then run:

```bash
git add .github/workflows/docs.yml
scripts/run-python311 python scripts/check_docs.py --stamp-current
scripts/run-python311 python scripts/tests/test_check_docs.py
scripts/run-python311 python scripts/tests/test_workflow_security.py
scripts/run-python311 python scripts/check_docs.py
test "$(git ls-files '.github/workflows/*.yml' '.github/workflows/*.yaml' | wc -l | tr -d ' ')" = "19"
git diff --check
```

Expected: stamping prints the current 40-character baseline; both unittest suites report `OK`; the workflow-policy inventory now recognizes exactly the documentation job in addition to its Stage 1B baseline; checker reports all documentation checks passed; Git reports exactly 19 tracked workflow paths and the inventory has the same 19 basename keys; whitespace check prints nothing.

- [ ] **Step 6: Inspect scope and commit the guard**

Run:

```bash
git status --short
git diff --stat
```

Expected: only the documentation contract, its tests, documentation workflow, workflow inventory, metadata stamps, and link repairs from this task are modified; the known `AGENTS.md` and `.superpowers/` scratch paths remain untracked and unstaged.

Before the commit, run `git diff --name-only` and stage each additional historical or archived Markdown path repaired in Step 3 by its exact printed path. Do not use `git add docs` or `git add .`; the cached whitespace gate below must run only after those exact additions.

Commit:

```bash
git add docs/verification.json scripts/check_docs.py scripts/tests/test_check_docs.py scripts/tests/test_workflow_security.py .github/workflows/docs.yml README.md backend/README.md backtest/README.md backtest/FEATURES.md feed/README.md docs/README.md docs/current-architecture.md docs/architecture.md docs/roadmap.md docs/iteration-log.md docs/rfcs/target-architecture.md docs/configuration.md docs/deployment-matrix.md docs/operations/workflows.md docs/data-contracts/feed.md docs/research/index.md docs/compliance.md docs/deploy-backend.md docs/data-model-api.md docs/endpoints.md docs/working-apis.md docs/need-to-fix.md docs/optimization-2026-06.md docs/positioning.md docs/cost-estimate.md docs/self-improving-alpha-loop.md docs/openclaw-integration.md docs/openclaw-stock-notes.md docs/superpowers/specs/2026-07-16-stock-analysis-refactor-design.md docs/superpowers/plans/2026-07-16-stage-1a-feed-security.md docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md routines/daily-alpha-routine.md routines/methodology.md routines/openclaw-agent-prompts.md routines/openclaw-daily-tasks.md routines/winter-inbox.md
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

From the repository root, execute the exact **Node gate** in Shared Interfaces without modification. Expected: all eight npm process invocations—`npm ci` plus seven npm scripts—exit 0, both smoke commands report successful route checks, the App Router handlers remain present, and verification leaves protected source, lock, declarations, and feed state unchanged.

- [ ] **Step 3: Re-run the exact Python commands documented in README**

From the repository root, execute the exact **Python 3.11 gate** and then the exact **Python 3.12 gate** in Shared Interfaces without modification. Expected: all seven lock comparisons reproduce exactly (six under Python 3.11 plus one under Python 3.12); the ten common process entry points pass on both runtimes; the two primary-only lock-consistency entry points also pass; and the expanded matrix therefore records twelve Python 3.11 plus ten Python 3.12 process entry points, twenty-two total, without creating root-owned worktree files.

- [ ] **Step 4: Confirm repository and documentation status**

```bash
git status --short --branch
git log --oneline -8
```

Expected: branch has no tracked or staged changes; only the known untracked `AGENTS.md` and `.superpowers/` scratch paths may remain; recent history shows the focused Stage 1C commits from this plan.

- [ ] **Step 5: Hand off the completed documentation baseline**

Report:

- the exact baseline SHA shown in maintained document metadata;
- the root README path;
- the current architecture and target RFC paths;
- documentation checker and CI paths;
- all commands executed and their pass status, including the exact Node/npm and both exact Python runtime gates;
- the current Stage 1A staging-allowlist boundary versus the Planned reader-facing manifest boundary;
- the Implemented / External / Optional Vercel split and the lack of a current hard-coded-attempt disable;
- the dated live-deployment observation, including the unresolved `API_BASE` trailing-slash breakage and Vercel Node 24.x versus repository Node 20.20.2 drift;
- any historical page intentionally retained rather than promoted to Current.

Do not claim Stage 2 contracts, DataGateway, analysis-core, or dual-runtime semantic parity are implemented.
