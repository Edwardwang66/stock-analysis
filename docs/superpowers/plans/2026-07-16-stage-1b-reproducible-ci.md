# Stage 1B Reproducible Toolchain and CI Implementation Plan

> **Status:** Accepted implementation plan
> **Scope:** Stage 1B reproducible toolchain and CI implementation slice.
> **Last verified commit:** `8cff75b8e31d6b3a07a9d6198e0bc54bcb3b594a`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish deterministic Node and Python installations, explicit static and server frontend builds, offline route smoke tests, and an all-PR CI matrix without changing application behavior or deleting source directories during a build.

**Architecture:** Node and npm are pinned once at the repository root and npm continues to use the existing lockfile. Python keeps human-maintained direct-dependency `.in` files and generated, hash-checked locks for the primary runtime, scheduled research automation, and the CI compatibility runtime; CI regenerates those locks in temporary directories and byte-compares them with the committed outputs. Server builds run against the real frontend tree so Vercel continues to package `frontend/app/api`. Static builds run in a private temporary copy that excludes only `app/api`; the export is copied to a unique same-root stage and published through a validated rename/swap protocol with a canonical hard-link owner, durable transaction state, append-only successor claims, dead-owner recovery, rollback, and atomically retired tombstones.

**Tech Stack:** Node.js 20.20.2, npm 10.8.2, Next.js 14.2.35, TypeScript 5.9.3, ESLint 8.57.1 with `next/core-web-vitals`, Python 3.11.15 primary, Python 3.12.13 compatibility, pip-tools 7.5.2, GitHub Actions.

## Global Constraints

- Stage 1A must be fully implemented and verified before Stage 1B begins. Do not execute the stages in parallel: Stage 1B must merge its changes to shared workflows on top of the Stage 1A security gates and tests.
- Preserve `frontend/app/api/quote/route.ts` and `frontend/app/api/ohlcv/route.ts` in place; Vercel/server builds must still see both handlers.
- A static build may remove `app/api` only from a newly created temporary copy. It must never rename, move, or delete the worktree `frontend/app/api` directory.
- Do not use `VERCEL` as the build-profile selector. `build:static` and `build:server` are the only build entry points and set `NEXT_BUILD_PROFILE` themselves.
- Keep npm as the only JavaScript package manager and `frontend/package-lock.json` as the only JavaScript lockfile.
- Pin Node to 20.20.2 and npm to 10.8.2 because the approved specification requires Node 20. Node 20 is already end-of-life; this pin is a migration risk, not a claim of ongoing upstream support. Upgrading to an actively supported Node line requires a follow-up specification and a separately reviewed change.
- Pin the primary Python runtime to 3.11.15 and test compatibility on exactly 3.12.13.
- Because Render evaluates `rootDir: backend`, declare `PYTHON_VERSION=3.11.15` in `render.yaml`; the root `.python-version` is not a Render version source.
- All application/runtime Python installs used by CI, Docker, Render, and scheduled workflows must consume generated lockfiles with `--require-hashes`; the only bootstrap exception is Task 3's exact `pip==25.2` plus `pip-tools==7.5.2` install used to create the first generation of those locks.
- Generate every committed Python lock with pip-tools 7.5.2, `--allow-unsafe`, `--no-reuse-hashes`, and `--no-header`; CI and the local Python matrix gates must regenerate the applicable locks into a temporary directory and compare them byte-for-byte with `cmp`. The CI compiler input pins `pip==25.2`, the newest pip release officially supported by pip-tools 7.5.2, and `--allow-unsafe` ensures both pip and setuptools are hashed for a clean Python 3.12 venv.
- Before a reproduction compile, copy each committed lock to its temporary output path and compile that existing output without `--upgrade` but with `--no-reuse-hashes`; pip-tools then preserves the reviewed pins while fetching the authoritative hash set again. Seed pins, never hashes. Dependency upgrades are a separate explicit `--upgrade` workflow, not a required-check side effect.
- Every host-mounted Python Docker command must run as the host UID/GID with `HOME=/tmp/home` and `PYTHONDONTWRITEBYTECODE=1`, create `/tmp/venv`, and install and execute through that venv so verification cannot leave root-owned bytecode or environment files in the worktree.
- Host-mounted Python generation and acceptance commands use the full official `python:3.11.15` and `python:3.12.13` images, not the `-slim` variants: the direct-execution suite creates Git repositories. Before creating a venv, every acceptance leg must prove the exact interpreter patch version, `git --version`, a non-root effective UID, and equality with the host UID/GID passed as `EXPECTED_UID`/`EXPECTED_GID`.
- The deployable backend image excludes host bytecode/databases from its context, runs as numeric non-root user `10001:10001`, and uses `exec` so Uvicorn receives termination signals.
- Normal CI and smoke tests must be offline with respect to market-data providers. Localhost HTTP requests are allowed.
- Keep the existing direct-execution Python tests; converting them to pytest is outside Stage 1B.
- Preserve all user-visible features and support the static and self-hosted/server profiles equally with the same core semantics. Internal breaking refactors are allowed only behind the already approved contracts; Task 5 is limited to its exact workflow, OpenClaw boundary, Render, quick-start, test, and plan files.
- Do not add Prettier or perform repository-wide formatting in this stage.
- Do not add semantic-parity, contract-generation, DataGateway, or analysis-core work; those belong to later stages.
- Preserve the user's untracked `AGENTS.md` and all unrelated worktree changes.

---

## File Structure

### Files created

- `.node-version` — canonical Node version used by local version managers and `actions/setup-node`.
- `.python-version` — canonical primary Python version used by local version managers and scheduled jobs.
- `frontend/.npmrc` — strict npm engine and lockfile policy.
- `frontend/.eslintrc.cjs` — Next 14-compatible ESLint baseline.
- `frontend/scripts/build-profile.mjs` — explicit server build and isolated static-copy build orchestrator.
- `frontend/scripts/smoke-static.mjs` — offline assertions over exported HTML routes.
- `frontend/scripts/smoke-server.mjs` — starts `next start`, probes key routes through localhost, and shuts it down.
- `frontend/scripts/tests/build-profile-publication.test.mjs` — publication concurrency, crash-recovery, rollback, and unsafe-path regression coverage.
- `frontend/scripts/tests/smoke-server.test.mjs` — child-owned readiness, bounded I/O, unexpected-exit, and shutdown regression coverage.
- `backend/requirements.in` — direct backend runtime dependencies.
- `scripts/requirements.in` — direct automation/feed dependencies.
- `scripts/requirements-winter-pg.in` — optional Winter PostgreSQL dependency declaration.
- `scripts/requirements-winter-pg.txt` — generated hash lock for the optional Winter PostgreSQL tools.
- `backtest/requirements.in` — direct research/backtest dependencies, including the currently missing scikit-learn declaration.
- `requirements/automation.in` — union of script and backtest dependencies used by research automation.
- `requirements/automation.txt` — generated Python 3.11.15 hash lock used by `alpha-routine` and `monthly-studies`.
- `requirements/ci.in` — union of backend and script dependencies exercised by the current test suite, plus the exact pip-tools version used for lock reproducibility checks.
- `requirements/ci-py311.txt` — generated hash lock for Python 3.11.15 CI.
- `requirements/ci-py312.txt` — generated hash lock for Python 3.12.13 CI.
- `backend/.dockerignore` — exclude local bytecode, virtual environments, test caches, and SQLite files from the production image context.

### Files modified

- `frontend/package.json` — exact dependency versions and stable lint/typecheck/script-test/build/smoke commands.
- `frontend/package-lock.json` — regenerated with Node 20.20.2/npm 10.8.2.
- `frontend/.gitignore` — keep generated outputs and private publication artifacts ignored while tracking `next-env.d.ts`.
- `frontend/next-env.d.ts` — commit the standard Next TypeScript references already present locally.
- `frontend/next.config.mjs` — validate and apply an explicit `NEXT_BUILD_PROFILE`.
- `backend/requirements.txt` — generated Python 3.11.15 hash lock.
- `scripts/requirements.txt` — generated Python 3.11.15 hash lock.
- `backtest/requirements.txt` — generated Python 3.11.15 hash lock.
- `backend/runtime.txt` — primary runtime pin.
- `backend/Dockerfile` — exact Python image and hash-checked install.
- `scripts/tests/test_validate_feed.py` — prove that full JSON Schema validation is active.
- `.github/workflows/tests.yml` — all-PR frontend profile and Python-version matrix.
- `.github/workflows/deploy-pages.yml` — static profile command and static smoke; no source deletion.
- `.github/workflows/alpha-routine.yml`
- `.github/workflows/chan-stats.yml`
- `.github/workflows/daily-digest.yml`
- `.github/workflows/daily-screener.yml`
- `.github/workflows/dependabot-automerge.yml`
- `.github/workflows/feed-validate.yml`
- `.github/workflows/feed-watchdog.yml`
- `.github/workflows/funds-13f.yml`
- `.github/workflows/hyperliquid-monitor.yml`
- `.github/workflows/intraday-report.yml`
- `.github/workflows/market-snapshot.yml`
- `.github/workflows/monthly-studies.yml`
- `.github/workflows/openclaw-notes.yml`
- `.github/workflows/premarket-pack.yml`
- `scripts/openclaw_daily.py` — recognize the optional Winter PostgreSQL configuration before spawning child tools and fail fast once configured.
- `scripts/tests/test_feed_publication.py` — TDD coverage for the optional Winter PostgreSQL boundary, local config compatibility, secrecy, and child failure propagation.
- `scripts/tests/test_workflow_security.py` — job-scoped production Python, Pages, Render, quick-start, checkout-credential, and behavior-preservation policy.
- `render.yaml` — exact Render Python version and hash-checked backend install.
- `backend/README.md` — deterministic backend installation command.
- `docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md` — corrected Task 5 contract and Git-capable acceptance gates.

### Interfaces

- `node scripts/build-profile.mjs static` produces `frontend/out/` while leaving every tracked source file unchanged.
- `node scripts/build-profile.mjs server` produces `frontend/.next/` from the real source tree, including `app/api`.
- `STATIC_FEED_SOURCE=/absolute/path node scripts/build-profile.mjs static` replaces `public/feed` only inside the private static-build copy; the worktree snapshot is never deleted or rewritten.
- `node scripts/smoke-static.mjs` consumes `frontend/out/` and `NEXT_PUBLIC_BASE_PATH`.
- `node scripts/smoke-server.mjs` consumes a completed server build in `frontend/.next/`; by default its own child binds port 0, and an explicit `SMOKE_PORT` must be a valid nonzero port.
- `npm run test:scripts` runs both build-publication and server-smoke lifecycle suites before either build profile in the aggregate `verify` command.
- `requirements/ci-py311.txt` and `requirements/ci-py312.txt` are complete install inputs; CI does not resolve from `.in` files.
- `requirements/automation.txt` is the complete install input for workflows that execute both `scripts/` and `backtest/` modules.
- Python 3.11.15 regenerates and compares the backend, scripts, Winter PostgreSQL, backtest, automation, and `ci-py311` locks; Python 3.12.13 regenerates and compares only `ci-py312`.

### Controlled toolchain execution

The implementation host is not assumed to have the pinned runtimes installed. Before changing any lockfile, run:

```bash
docker --version
docker pull node:20.20.2-bookworm-slim
docker pull python:3.11.15
docker pull python:3.12.13
```

Expected: Docker is available and all three exact images pull successfully. Bootstrap and install steps can require registry, npm, and PyPI (or configured package-mirror) network access unless the relevant images and packages are already cached; the offline requirement applies to application smoke tests and market-data-provider access, not dependency acquisition. All lock generation below runs in those images, so the current host's Node 26/npm 11 and missing `python3.11` cannot silently generate repository locks. If an already-installed local runtime is used instead, its full version must match the corresponding pin exactly before any install or compile command runs.

---

### Task 1: Pin the frontend toolchain and establish ESLint/typecheck gates

**Files:**
- Create: `.node-version`
- Create: `frontend/.npmrc`
- Create: `frontend/.eslintrc.cjs`
- Modify: `frontend/.gitignore`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Add to Git: `frontend/next-env.d.ts`

**Interfaces:**
- Consumes: the current `frontend/package-lock.json` v3 and current resolved application versions.
- Produces: exact Node/npm metadata, a clean-install lock, `npm run lint`, and `npm run typecheck` for later build and CI tasks.

- [ ] **Step 1: Record the failing clean-toolchain assertions**

Run from the repository root:

```bash
test "$(cat .node-version 2>/dev/null)" = "20.20.2"
test -f frontend/.eslintrc.cjs
test -x frontend/node_modules/.bin/eslint
```

Expected: at least the first two commands exit non-zero because the version file and ESLint configuration do not exist. A stale local `node_modules` directory does not satisfy this gate.

- [ ] **Step 2: Add the canonical Node/npm and ESLint configuration**

Create `.node-version`:

```text
20.20.2
```

Create `frontend/.npmrc`:

```ini
engine-strict=true
package-lock=true
save-exact=true
```

Create `frontend/.eslintrc.cjs`:

```js
module.exports = {
  root: true,
  extends: ["next/core-web-vitals"],
  ignorePatterns: [".next/**", "out/**", "node_modules/**", "public/feed/**"],
  rules: {
    // Stage 1B preserves the behavior of the existing effect-heavy pages.
    // Re-enabling this rule requires a separate hook-dependency audit.
    "react-hooks/exhaustive-deps": "off",
  },
};
```

Replace `frontend/.gitignore` with:

```gitignore
node_modules/
.next/
out/
*.tsbuildinfo
.env*.local
```

Add the existing standard `frontend/next-env.d.ts` content to Git:

```ts
/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/building-your-application/configuring/typescript for more information.
```

Replace `frontend/package.json` with this Task 1 state:

```json
{
  "name": "stock-dashboard-frontend",
  "version": "0.1.0",
  "private": true,
  "packageManager": "npm@10.8.2",
  "engines": {
    "node": "20.20.2",
    "npm": "10.8.2"
  },
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint --max-warnings=0",
    "typecheck": "tsc --project tsconfig.json --noEmit --incremental false"
  },
  "dependencies": {
    "lightweight-charts": "4.2.3",
    "next": "14.2.35",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "20.19.43",
    "@types/react": "18.3.31",
    "@types/react-dom": "18.3.7",
    "eslint": "8.57.1",
    "eslint-config-next": "14.2.35",
    "typescript": "5.9.3"
  }
}
```

- [ ] **Step 3: Regenerate the npm lock with the pinned tools**

Run from the repository root in the exact Node image. The tmpfs hides any stale host `node_modules` and prevents Linux packages from replacing the host installation:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --tmpfs /workspace/frontend/node_modules:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace/frontend \
  node:20.20.2-bookworm-slim \
  sh -lc 'node --version && npm --version && npm install --package-lock-only && npm ci && npm ls --depth=0'
```

Expected:

- `node --version` prints `v20.20.2`.
- `npm --version` prints `10.8.2`.
- `npm install --package-lock-only` updates only `package-lock.json`.
- `npm ci` exits 0 from a clean install.
- `npm ls --depth=0` exits 0 with no `invalid`, `extraneous`, or `ELSPROBLEMS` entries.

- [ ] **Step 4: Run the new quality gates**

Run:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --tmpfs /workspace/frontend/node_modules:rw,exec,mode=1777 \
  --volume "$PWD:/workspace" \
  --workdir /workspace/frontend \
  node:20.20.2-bookworm-slim \
  sh -lc 'npm ci && npm run lint && npm run typecheck'
git status --short
```

Expected: lint reports zero errors and zero warnings; typecheck exits 0 and does not create a tracked `tsconfig.tsbuildinfo`; status contains only the intended configuration and lockfile changes plus the pre-existing untracked `AGENTS.md`.

- [ ] **Step 5: Commit the frontend toolchain baseline**

```bash
git add .node-version frontend/.npmrc frontend/.eslintrc.cjs frontend/.gitignore frontend/next-env.d.ts frontend/package.json frontend/package-lock.json
git diff --cached --check
git commit -m "chore: pin frontend toolchain"
```

---

### Task 2: Add explicit, non-destructive build profiles and offline smoke tests

**Files:**
- Create: `frontend/scripts/build-profile.mjs`
- Create: `frontend/scripts/smoke-static.mjs`
- Create: `frontend/scripts/smoke-server.mjs`
- Create: `frontend/scripts/tests/build-profile-publication.test.mjs`
- Create: `frontend/scripts/tests/smoke-server.test.mjs`
- Modify: `frontend/next.config.mjs`
- Modify: `frontend/.gitignore`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: Task 1's exact npm install and the unchanged `frontend/app/api` handlers.
- Produces: `test:scripts`, `build:static`, `build:server`, `smoke`, `smoke:static`, `smoke:server`, and `verify` commands used by CI and Pages deployment.

- [ ] **Step 1: Verify the profile commands are initially absent**

Run:

```bash
cd frontend
npm run build:static
npm run build:server
```

Expected: both commands fail with `Missing script` before this task is implemented.

- [ ] **Step 2: Make the Next configuration profile-driven**

Replace `frontend/next.config.mjs` with:

```js
/** @type {import("next").NextConfig} */
const profile = process.env.NEXT_BUILD_PROFILE ?? "server";
const allowedProfiles = new Set(["static", "server"]);

if (!allowedProfiles.has(profile)) {
  throw new Error(
    `NEXT_BUILD_PROFILE must be "static" or "server", got "${profile}"`,
  );
}

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
if (basePath && (!basePath.startsWith("/") || basePath.endsWith("/"))) {
  throw new Error(
    "NEXT_PUBLIC_BASE_PATH must start with '/' and must not end with '/'",
  );
}

const nextConfig = {
  ...(profile === "static" ? { output: "export" } : {}),
  images: { unoptimized: true },
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
};

export default nextConfig;
```

The default remains `server`, so `next dev`, `next start`, and a Vercel build retain access to the real App Router handlers. Static selection happens only through the build command below.

- [ ] **Step 3: Implement the isolated profile builder**

Create the new script directory first:

```bash
mkdir -p frontend/scripts
```

Implement the contract in `frontend/scripts/build-profile.mjs` and keep its
publication regression coverage in
`frontend/scripts/tests/build-profile-publication.test.mjs`:

- recursively copy the frontend into a private temporary tree, excluding only
  `node_modules`, `.next`, and `out`, and remove `app/api` only from that copy;
- apply `STATIC_FEED_SOURCE` only to the copy's `public/feed`, then build the
  static profile with the pinned local Next binary;
- copy the completed export into a unique same-root `.out-stage-<transaction>`
  directory before touching the published output;
- serialize publication with a validated canonical hard link to immutable
  owner metadata, durable transaction phases, and append-only successor links;
- recover dead owners, validate inode/path/type and phase/shape metadata before
  mutation, swap by rename, roll back failures, and atomically retire completed
  records as tombstones before deletion;
- fail closed on live owners, ambiguous state, unsafe paths, or ownership
  changes, while preserving the primary error alongside cleanup errors.

The build's private-copy API/feed changes never touch the worktree. Publication
touches only ignored `frontend/out/` and validated ignored transaction
artifacts (`.out-stage-*`, `.out-backup-*`, and `.out-publish.lock*`). The test
file is the canonical executable specification for concurrency, crash points,
recovery, rollback, and cleanup safety; do not duplicate the implementation in
this plan.

- [ ] **Step 4: Add deterministic route smoke scripts**

Create `frontend/scripts/smoke-static.mjs`:

```js
import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";

const pages = [
  "index.html",
  "alerts/index.html",
  "desk/index.html",
  "help/index.html",
  "intel/index.html",
  "portfolio/index.html",
  "reports/index.html",
  "screener/index.html",
  "sources/index.html",
  "symbol/index.html",
  "tracker/index.html",
  "404.html",
];

for (const page of pages) {
  const file = new URL(`../out/${page}`, import.meta.url);
  await stat(file);
  const html = await readFile(file, "utf8");
  assert.match(html, /^<!DOCTYPE html>/i, `${page} must be rendered HTML`);
}

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const index = await readFile(new URL("../out/index.html", import.meta.url), "utf8");
assert.ok(
  index.includes(`${basePath}/_next/`),
  `exported assets must use basePath "${basePath}"`,
);

console.log(`static smoke: ${pages.length} routes OK`);
```

Implement the server lifecycle contract in
`frontend/scripts/smoke-server.mjs`, with focused coverage in
`frontend/scripts/tests/smoke-server.test.mjs`:

- launch exactly one `next start` child on loopback and default to child-owned
  port 0; an explicit `SMOKE_PORT` remains available for controlled runs;
- pipe and tee that child's stdout/stderr, parse both its `Local:` URL and
  `Ready` marker from the same child, and never probe before both are observed;
- bound readiness, every fetch, and every response-body read; treat spawn
  errors and any pre-cleanup child exit (including code 0) as failure;
- probe eleven HTML routes and two offline API negative paths;
- begin cleanup with SIGTERM and escalate to SIGKILL if the child does not
  exit, surfacing cleanup failure together with any primary smoke failure.

The lifecycle test file is the canonical executable specification for
port/readiness ownership, occupied ports, black-hole bodies, child exits, and
signal escalation; do not duplicate the implementation in this plan.

- [ ] **Step 5: Expose the stable npm commands**

Keep the exact dependency and engine pins from Task 1. Add these exact script
entries to `frontend/package.json` alongside the existing profile and smoke
commands:

```json
{
  "test:scripts": "node --test scripts/tests/build-profile-publication.test.mjs scripts/tests/smoke-server.test.mjs",
  "verify": "npm run lint && npm run typecheck && npm run test:scripts && npm run build:static && npm run smoke:static && npm run build:server && npm run smoke:server"
}
```

The order is binding: lint, typecheck, script tests, static build/smoke, then
server build/smoke. This integration changes package scripts only and must not
regenerate or otherwise modify `frontend/package-lock.json`.

- [ ] **Step 6: Verify both profiles and prove source preservation**

Run the exact pinned image from the worktree root with a clean ephemeral
installation. Script tests precede both builds:

```bash
docker run --rm \
  --tmpfs /workspace/frontend/node_modules:rw,exec,mode=1777 \
  --mount type=volume,src=stock-analysis-stage1b-npm-cache,dst=/root/.npm \
  -v "$PWD:/workspace" \
  -w /workspace/frontend \
  node:20.20.2-bookworm-slim \
  sh -lc 'node --version && npm --version && npm ci && npm run lint && npm run typecheck && npm run test:scripts && NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run build:static && NEXT_PUBLIC_BASE_PATH=/stock-analysis npm run smoke:static && env -u NEXT_PUBLIC_BASE_PATH npm run build:server && env -u NEXT_PUBLIC_BASE_PATH npm run smoke:server'
```

Then run all preservation and residue assertions:

```bash
test -f frontend/app/api/quote/route.ts
test -f frontend/app/api/ohlcv/route.ts
test -f frontend/.next/BUILD_ID
test "$(shasum -a 256 frontend/package-lock.json | awk '{print $1}')" = "97875c90208b25596cae8ea55482f4c38295aba18b77287f4a11e32208b563d1"
git diff --exit-code HEAD -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts
test -z "$(git status --porcelain=v1 --untracked-files=all -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts)"
test -z "$(find frontend -maxdepth 1 \( -name '.out-stage-*' -o -name '.out-backup-*' -o -name '.out-publish.lock*' \) -print -quit)"
git diff --check
```

Expected: Node prints `v20.20.2`, npm prints `10.8.2`, all script tests pass,
static smoke reports `12 routes OK`, and server smoke prints eleven page passes
plus two offline API negative-path passes. Both handlers and `.next/BUILD_ID`
exist; the lock hash matches; API, bundled feed, lockfile, TypeScript config, and
Next environment declarations have no tracked or untracked drift; no private
publication residue remains; and `git diff --check` exits 0.

- [ ] **Step 7: Commit the profile builds and smoke tests**

```bash
git add frontend/next.config.mjs frontend/package.json frontend/package-lock.json frontend/scripts/build-profile.mjs frontend/scripts/smoke-static.mjs frontend/scripts/smoke-server.mjs
git diff --cached --check
git commit -m "build: add reproducible frontend profiles"
```

- [ ] **Step 8: Commit the reviewed smoke/publication hardening follow-up**

After the exact gate and focused review both pass, stage exactly the hardening
set. `frontend/package-lock.json` is deliberately excluded:

```bash
git add frontend/.gitignore frontend/package.json frontend/scripts/build-profile.mjs frontend/scripts/smoke-server.mjs frontend/scripts/tests/build-profile-publication.test.mjs frontend/scripts/tests/smoke-server.test.mjs docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md
git diff --cached --check
git commit -m "fix: harden frontend smoke and static publish"
```

---

### Task 3: Pin Python and generate hash-checked dependency locks

**Files:**
- Create: `.python-version`
- Create: `backend/requirements.in`
- Modify: `backend/requirements.txt`
- Create: `scripts/requirements.in`
- Modify: `scripts/requirements.txt`
- Create: `scripts/requirements-winter-pg.in`
- Create: `scripts/requirements-winter-pg.txt`
- Create: `backtest/requirements.in`
- Modify: `backtest/requirements.txt`
- Create: `requirements/automation.in`
- Create: `requirements/automation.txt`
- Create: `requirements/ci.in`
- Create: `requirements/ci-py311.txt`
- Create: `requirements/ci-py312.txt`
- Create: `scripts/check_lock_consistency.py`
- Create: `scripts/tests/test_check_lock_consistency.py`
- Create: `backend/.dockerignore`
- Modify: `backend/runtime.txt`
- Modify: `backend/Dockerfile`
- Modify: `docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md` — record the audited direct-dependency corrections used by this task.

**Interfaces:**
- Consumes: the current imports in `backend/`, `scripts/`, `scripts/winter_pg/`, and `backtest/`.
- Produces: direct dependency declarations plus complete, hash-checked install inputs for production, feed validation, combined script/backtest automation, research, optional PostgreSQL tools, and both CI Python versions; a tested cross-lock invariant ensures the primary CI and automation environments contain the exact versions from their narrower runtime locks.

- [ ] **Step 1: Demonstrate the current declaration and version gaps**

Run:

```bash
test "$(cat backend/runtime.txt)" = "python-3.11.15"
rg -n '^scikit-learn' backtest/requirements.txt
test -f scripts/requirements-winter-pg.txt
test -f requirements/automation.txt
test -f backend/.dockerignore
rg -n -- '--hash=sha256:' backend/requirements.txt scripts/requirements.txt backtest/requirements.txt
```

Expected: all six checks fail on the current tree: runtime is 3.11.9, scikit-learn is undeclared despite `backtest/walkforward.py` importing it, the Winter PostgreSQL and combined automation locks plus Docker context policy are absent, and existing requirements contain no hashes.

- [ ] **Step 2: Add human-maintained direct dependency inputs**

Create the new requirements directory first:

```bash
mkdir -p requirements
```

Create `.python-version`:

```text
3.11.15
```

Create `backend/requirements.in`:

```text
fastapi==0.139.0
uvicorn[standard]==0.49.0
httpx==0.28.1
pydantic>=2,<3
```

Create `scripts/requirements.in`:

```text
# Feed validation and NumPy automation. Screener/Chan jobs consume the backend lock for HTTPX.
numpy>=1.26,<3
jsonschema>=4,<5
```

Create `scripts/requirements-winter-pg.in`:

```text
# Optional PostgreSQL adapter used only by scripts/winter_pg/.
psycopg2-binary>=2.9,<3
```

Create `backtest/requirements.in`:

```text
numpy>=1.26,<3
scikit-learn>=1.4,<2
```

Create `requirements/automation.in`:

```text
-r ../scripts/requirements.in
-r ../backtest/requirements.in
```

This is the deployment input for workflows that import modules from both trees. Keep the narrower `scripts/requirements.txt` for feed-only jobs and the narrower `backtest/requirements.txt` for research-only use.

Create `requirements/ci.in`:

```text
-r ../backend/requirements.in
-r ../scripts/requirements.in
# pip-tools 7.5.2 officially supports pip through 25.2.
pip==25.2
pip-tools==7.5.2
```

- [ ] **Step 3: Generate every committed lock with fixed interpreters and pip-tools**

Generate every primary-runtime lock from the exact Linux runtime used by deployment and CI:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv &&
    /tmp/venv/bin/python -m pip install pip==25.2 pip-tools==7.5.2 &&
    /tmp/venv/bin/python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version" &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=backend/requirements.txt backend/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=scripts/requirements.txt scripts/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=scripts/requirements-winter-pg.txt scripts/requirements-winter-pg.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=backtest/requirements.txt backtest/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/automation.txt requirements/automation.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/ci-py311.txt requirements/ci.in
  '
```

Generate the compatibility lock with Python 3.12.13:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version"
    git --version
    python -m venv /tmp/venv &&
    /tmp/venv/bin/python -m pip install pip==25.2 pip-tools==7.5.2 &&
    /tmp/venv/bin/python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version" &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/ci-py312.txt requirements/ci.in
  '
```

Expected: every output is header-free, contains only pinned versions, environment markers where required, and a freshly resolved `--hash=sha256:` allowlist per distribution rather than hashes reused from an older output. The two CI locks resolve successfully under their named interpreters, and both include pip-tools 7.5.2 so the installed CI environments can reproduce their own locks.

- [ ] **Step 4: Add a fail-closed cross-lock consistency checker**

First create `scripts/tests/test_check_lock_consistency.py` with temporary lock fixtures and RED assertions for all of these cases:

- multiline hashes plus indented `# via` annotations parse successfully, as does the column-zero unsafe-package preamble emitted before hashed pip/setuptools entries by `--allow-unsafe`;
- normalized names treat `Foo_Bar[extra]` and `foo.bar` as the same distribution while duplicate normalized names in one lock fail;
- missing target packages and same-name version drift fail with source, target, package, and version details;
- identical trimmed marker text passes, a marked source may map to an unmarked target, and the reverse, two different markers, or different whitespace inside a quoted marker literal fail closed;
- dangling continuations, a comment inserted before a hash continuation finishes, missing or malformed SHA-256 hashes, non-exact specifiers, URLs, includes, options, editables, inline comments, and unexpected indented content fail closed;
- the repository contract contains exactly these four subset pairs, and a temporary repository fails when any one pair drifts:
  - `backend/requirements.txt` ⊆ `requirements/ci-py311.txt`
  - `scripts/requirements.txt` ⊆ `requirements/ci-py311.txt`
  - `scripts/requirements.txt` ⊆ `requirements/automation.txt`
  - `backtest/requirements.txt` ⊆ `requirements/automation.txt`

Run the new test before creating the checker. Expected: it fails because `scripts/check_lock_consistency.py` does not exist.

Then create `scripts/check_lock_consistency.py` as a standard-library-only CLI. `python scripts/check_lock_consistency.py --root .` must use the fixed four-pair repository contract and parse physical lines with an explicit state machine: while idle it accepts blank lines and whole-line comments at any indentation (including pip-tools' unsafe-package preamble); an entry begins with a column-zero exact requirement header, continues with one or more indented SHA-256 hash lines, and only after the last hash may be followed by indented `# via` comments. A comment or any other content may not interrupt an unfinished hash continuation. The parser must not flatten an entry and split on `--hash=`, because that text could occur inside marker content. Normalize names by PEP 503's `[-_.]+` rule, remove validated extras from the identity key, require exact `==` entries with one or more unique 64-hex SHA-256 hashes, reject duplicate normalized packages and unsupported pip syntax, and conservatively compare marker text without attempting to evaluate markers. Only leading and trailing marker whitespace is stripped; content inside the marker, including quoted-literal whitespace, is compared byte-for-byte. Identical trimmed markers pass; a marked source may map to an unmarked target because the target is broader; an unmarked source mapped to a marked target or two different markers fails closed. Contract or parse errors exit 1 with actionable diagnostics; argparse errors exit 2; success exits 0 with one summary line. Winter PostgreSQL and `ci-py312` are deliberately outside these four primary-runtime subset checks.

Run:

```bash
python scripts/tests/test_check_lock_consistency.py
python scripts/check_lock_consistency.py --root .
```

Expected: the unit fixtures pass and the applicable primary-runtime locks satisfy all four subset invariants.

- [ ] **Step 5: Pin the backend runtime and enforce hashes in Docker**

Replace `backend/runtime.txt` with:

```text
python-3.11.15
```

Replace `backend/Dockerfile` with:

```dockerfile
# 通用容器镜像(Render / Railway / Fly / 任意平台均可)
FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt

COPY --chown=10001:10001 app ./app

# 平台通过 $PORT 注入端口(本地默认 8000)
ENV PORT=8000
EXPOSE 8000
USER 10001:10001
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Create `backend/.dockerignore`:

```text
**/__pycache__/
**/*.py[cod]
**/.venv/
**/.pytest_cache/
**/*.db
**/*.db-*
**/*.sqlite
**/*.sqlite-*
**/*.sqlite3
**/*.sqlite3-*
```

The recursive `**/` patterns scrub bytecode, virtualenvs, test caches, main SQLite databases, and their `-wal`/`-shm`/`-journal` sidecars at every context depth rather than only at the context root. The numeric runtime identity keeps the image independent of host user databases; the default SQLite files remain writable under `/tmp`, while mounted persistent paths must be granted deliberately by the deployer. `exec` makes Uvicorn receive container stop signals directly.

- [ ] **Step 6: Verify each lock in a clean environment**

Run:

```bash
set -e
for file in backend/requirements.txt scripts/requirements.txt scripts/requirements-winter-pg.txt backtest/requirements.txt requirements/automation.txt requirements/ci-py311.txt requirements/ci-py312.txt; do
  rg -q -- '--hash=sha256:' "$file"
done
for file in requirements/ci-py311.txt requirements/ci-py312.txt; do
  rg -q '^pip==25\.2' "$file"
  rg -q '^setuptools==' "$file"
done

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -c "from importlib.metadata import version; assert version(\"pip\") == \"25.2\"; version(\"setuptools\")"
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
    /tmp/venv/bin/python scripts/tests/test_check_lock_consistency.py
    /tmp/venv/bin/python scripts/check_lock_consistency.py --root .
    /tmp/venv/bin/python -c "import fastapi, httpx, jsonschema, numpy, piptools, pydantic"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py312.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -c "from importlib.metadata import version; assert version(\"pip\") == \"25.2\"; version(\"setuptools\")"
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    cp requirements/ci-py312.txt "$tmp/ci-py312.txt"
    /tmp/venv/bin/python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
    cmp "$tmp/ci-py312.txt" requirements/ci-py312.txt
    /tmp/venv/bin/python -c "import fastapi, httpx, jsonschema, numpy, piptools, pydantic"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r scripts/requirements.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/scripts /tmp/venv/bin/python -c "import feed_lib, jsonschema, numpy, validate_feed"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r backtest/requirements.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/backtest /tmp/venv/bin/python -c "import data, numpy, sklearn, statarb, walkforward"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/automation.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/backtest:/workspace/scripts /tmp/venv/bin/python -c "import factor_factory, feed_lib, run_routine, study_downshift, study_pbo"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r scripts/requirements-winter-pg.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -c "import psycopg2"
  '

fixture_context="$(mktemp -d)"
trap 'rm -rf "$fixture_context"' EXIT
cp -R backend/. "$fixture_context/"
mkdir -p "$fixture_context/app/nested/__pycache__"
cp backend/app/__init__.py "$fixture_context/app/nested/__pycache__/leak.pyc"
cp backend/app/__init__.py "$fixture_context/app/nested/leak.db"
cp backend/app/__init__.py "$fixture_context/app/nested/leak.db-wal"
cp backend/app/__init__.py "$fixture_context/app/nested/leak.sqlite3-journal"
test -f "$fixture_context/app/nested/__pycache__/leak.pyc"
test -f "$fixture_context/app/nested/leak.db"
test -f "$fixture_context/app/nested/leak.db-wal"
test -f "$fixture_context/app/nested/leak.sqlite3-journal"
docker build --pull=false --tag stock-analysis-backend:stage1b "$fixture_context"
test "$(docker image inspect stock-analysis-backend:stage1b --format '{{.Config.User}}')" = "10001:10001"
docker run --rm stock-analysis-backend:stage1b \
  sh -eu -c 'found="$(find /app \( -name __pycache__ -o -name "*.py[co]" -o -name "*.db" -o -name "*.db-*" -o -name "*.sqlite" -o -name "*.sqlite-*" -o -name "*.sqlite3" -o -name "*.sqlite3-*" \) -print -quit)"; test -z "$found"'
docker run --rm stock-analysis-backend:stage1b \
  python -c 'import app.main; print("backend image import OK")'
```

Expected: the hash loop fails immediately if any lock lacks a hash; every install, dependency import, and source-module import exits 0; `pip check` reports `No broken requirements found.` in all six environments; all six Python 3.11 locks and the Python 3.12 CI lock exactly match temporary outputs reproduced from their `.in` files with the committed pins seeded first and hashes fetched anew. Both CI locks contain hashed `pip==25.2` and setuptools entries, so the Python 3.12 clean install does not rely on an undeclared bootstrap package. The backend image builds from a deliberately polluted temporary context, excludes the nested bytecode, main database, WAL, and rollback-journal fixtures, records user `10001:10001`, and imports the application successfully as that non-root user.

- [ ] **Step 7: Commit declarations, generated locks, runtime pins, and lock consistency checks**

```bash
git add .python-version backend/.dockerignore backend/requirements.in backend/requirements.txt backend/runtime.txt backend/Dockerfile scripts/requirements.in scripts/requirements.txt scripts/requirements-winter-pg.in scripts/requirements-winter-pg.txt scripts/check_lock_consistency.py scripts/tests/test_check_lock_consistency.py backtest/requirements.in backtest/requirements.txt requirements/automation.in requirements/automation.txt requirements/ci.in requirements/ci-py311.txt requirements/ci-py312.txt docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md
git diff --cached --check
git commit -m "build: lock Python dependencies"
```

---

### Task 4: Prove full schema validation and add the all-PR CI matrix

**Files:**
- Modify: `scripts/tests/test_validate_feed.py`
- Modify: `scripts/tests/test_workflow_security.py`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: Task 2's stable frontend commands and Task 3's Python-version-specific CI locks.
- Produces: a regression test that fails without `jsonschema`, required CI jobs for both frontend profiles and both Python runtimes, and one stable aggregate gate for branch protection.

- [ ] **Step 1: Add a test that the Stage 1A fallback validator cannot satisfy**

Insert this block immediately after the existing `缺必填字段拒收` assertion and before the final summary print in `scripts/tests/test_validate_feed.py`:

```python
unexpected_property = write_tmp(
    fl.sign_report(
        mk_report(unexpected_top_level=True),
        SECRET,
    )
)
passed, errs, _ = check_one(unexpected_property, require_sig=False, secret=SECRET)
ok(
    "完整 JSON Schema 拒绝额外顶层字段",
    not passed and any("unexpected_top_level" in e for e in errs),
    str(errs),
)
```

Stage 1A deliberately adds strict ID validation to the fallback, so an invalid ID is no longer a valid dependency probe. The fallback still does not implement the schema's top-level `additionalProperties: false`; this case therefore proves that the declared full validator is installed and active without conflicting with Stage 1A.

- [ ] **Step 2: Run the new test without jsonschema to verify that it fails**

Run:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r backend/requirements.txt
    /tmp/venv/bin/python scripts/tests/test_validate_feed.py
  '
```

Expected: the command exits non-zero at `完整 JSON Schema 拒绝额外顶层字段` because the fallback accepts the unexpected property. This is the intended red test.

- [ ] **Step 3: Run all current Python tests with each full CI lock**

Run:

For each exact runtime image, install its CI lock into `/tmp/venv`, regenerate the applicable lock set into a temporary directory, compare every regenerated lock with its committed output, and then run the two backend tests, the two pre-existing script tests, and all six Stage 1A security tests:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
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

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version"
    git --version
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

Expected: all seven committed locks byte-match their runtime-specific temporary regenerations; all twenty-two process-level test and contract entrypoint invocations exit 0; the Python 3.11-only lock-consistency unit suite and repository CLI prove the four primary-runtime subset invariants, while `ci-py312` remains an independently resolved compatibility lock. The feed test prints `完整 JSON Schema 拒绝额外顶层字段` as passed under both runtimes; no test contacts a live market provider. Lock regeneration adds no test invocation and does not alter the Stage 1A six-script contract in either leg.

- [ ] **Step 4: Replace the test workflow with the full matrix**

Before replacing the workflow, update `scripts/tests/test_workflow_security.py` so its CI-policy regression covers the new contract instead of requiring the old path filters:

- `pull_request` has no `paths` or `paths-ignore` filter.
- `push` targets `main` and ignores exactly the generated feed allowlist shown below; it must not ignore `feed/inbox/**`, `feed/schema/**`, or `feed/README.md`.
- both `actions/checkout@v7` steps set `persist-credentials: false`.
- both frontend matrix legs use `actions/setup-node@v7`, resolve `.node-version`, and fail closed unless the active versions are exactly Node `20.20.2` and npm `10.8.2`.
- the Python matrix runs both `python scripts/tests/test_check_lock_consistency.py` and `python scripts/check_lock_consistency.py --root .` only when `matrix.python_version == '3.11.15'`.
- every `piptools compile` invocation uses `--no-reuse-hashes`, so existing outputs seed reviewed versions but cannot seed a forged or stale hash allowlist.
- the workflow contains the stable `Tests (单元测试闸门)` aggregate job, waits for both matrix jobs with `if: ${{ always() }}`, and fails unless both results are `success`.

Run `python scripts/tests/test_workflow_security.py` before changing the workflow. Expected: the updated policy test fails against the old workflow, proving the regression is red for the intended reasons.

Replace `.github/workflows/tests.yml` with:

```yaml
name: CI (reproducible baseline)

on:
  push:
    branches: [main]
    paths-ignore:
      - "feed/crypto/**"
      - "feed/factory/**"
      - "feed/funds/**"
      - "feed/health.json"
      - "feed/index.json"
      - "feed/intraday/**"
      - "feed/market/**"
      - "feed/reports/**"
      - "feed/screener/**"
      - "feed/signals/**"
      - "feed/stock-notes/**"
      - "feed/watchlist.json"
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  frontend:
    name: Frontend (${{ matrix.profile }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - profile: static
            base_path: /stock-analysis
          - profile: server
            base_path: ""
    defaults:
      run:
        working-directory: frontend
    env:
      # Approved spec still requires Node 20.20.2 even though Node 20 is EOL.
      NEXT_TELEMETRY_DISABLED: "1"
      NEXT_PUBLIC_BASE_PATH: ${{ matrix.base_path }}
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-node@v7
        with:
          node-version-file: .node-version
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Verify exact Node and npm
        run: |
          test "$(node --version)" = "v20.20.2"
          test "$(npm --version)" = "10.8.2"
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test:scripts
      - if: matrix.profile == 'static'
        run: npm run build:static
      - if: matrix.profile == 'static'
        run: npm run smoke:static
      - if: matrix.profile == 'server'
        run: npm run build:server
      - if: matrix.profile == 'server'
        run: npm run smoke:server

  python:
    name: Python (${{ matrix.python_version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - python_version: "3.11.15"
            lockfile: requirements/ci-py311.txt
          - python_version: "3.12.13"
            lockfile: requirements/ci-py312.txt
    env:
      PYTHONDONTWRITEBYTECODE: "1"
      PIP_DISABLE_PIP_VERSION_CHECK: "1"
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python_version }}
          cache: pip
          cache-dependency-path: ${{ matrix.lockfile }}
      - run: python -m pip install --require-hashes -r "${{ matrix.lockfile }}"
      - run: python -m pip check
      - name: Reproduce Python 3.11 locks from direct inputs
        if: matrix.python_version == '3.11.15'
        shell: bash
        run: |
          set -euo pipefail
          tmp="$(mktemp -d)"
          trap 'rm -rf "$tmp"' EXIT
          cp backend/requirements.txt "$tmp/backend.txt"
          cp scripts/requirements.txt "$tmp/scripts.txt"
          cp scripts/requirements-winter-pg.txt "$tmp/winter-pg.txt"
          cp backtest/requirements.txt "$tmp/backtest.txt"
          cp requirements/automation.txt "$tmp/automation.txt"
          cp requirements/ci-py311.txt "$tmp/ci-py311.txt"
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backend.txt" backend/requirements.in
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/scripts.txt" scripts/requirements.in
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/winter-pg.txt" scripts/requirements-winter-pg.in
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backtest.txt" backtest/requirements.in
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/automation.txt" requirements/automation.in
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py311.txt" requirements/ci.in
          cmp "$tmp/backend.txt" backend/requirements.txt
          cmp "$tmp/scripts.txt" scripts/requirements.txt
          cmp "$tmp/winter-pg.txt" scripts/requirements-winter-pg.txt
          cmp "$tmp/backtest.txt" backtest/requirements.txt
          cmp "$tmp/automation.txt" requirements/automation.txt
          cmp "$tmp/ci-py311.txt" requirements/ci-py311.txt
      - name: Reproduce Python 3.12 lock from direct inputs
        if: matrix.python_version == '3.12.13'
        shell: bash
        run: |
          set -euo pipefail
          tmp="$(mktemp -d)"
          trap 'rm -rf "$tmp"' EXIT
          cp requirements/ci-py312.txt "$tmp/ci-py312.txt"
          python -m piptools compile --generate-hashes --allow-unsafe --no-reuse-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
          cmp "$tmp/ci-py312.txt" requirements/ci-py312.txt
      - name: Backend HTTP and data-layer tests
        working-directory: backend
        run: |
          python tests/test_backend.py
          python tests/test_api.py
      - name: Automation and feed-validation tests
        run: |
          python scripts/tests/test_chan_engine.py
          python scripts/tests/test_validate_feed.py
          python scripts/tests/test_feed_validation_security.py
          python scripts/tests/test_feed_ingress.py
          python scripts/tests/test_validate_feed_cli.py
          python scripts/tests/test_feed_publication.py
          python scripts/tests/test_dependabot_merge_gate.py
          python scripts/tests/test_workflow_security.py
      - name: Primary-runtime lock consistency
        if: matrix.python_version == '3.11.15'
        run: |
          python scripts/tests/test_check_lock_consistency.py
          python scripts/check_lock_consistency.py --root .

  gate:
    name: Tests (单元测试闸门)
    if: ${{ always() }}
    needs: [frontend, python]
    runs-on: ubuntu-latest
    steps:
      - name: Require every runtime matrix to pass
        env:
          FRONTEND_RESULT: ${{ needs.frontend.result }}
          PYTHON_RESULT: ${{ needs.python.result }}
        run: |
          test "$FRONTEND_RESULT" = success
          test "$PYTHON_RESULT" = success
```

There are deliberately no pull-request path filters: every pull request must receive both frontend profile checks and both Python checks, including dependency-only, documentation-adjacent, workflow, and cross-directory changes. Main-branch pushes ignore only the explicit generated-feed allowlist above, so robot publication commits do not start all four matrix legs while feed inputs, schemas, documentation, workflows, and source changes remain covered. The workflow is a merge of the Stage 1A security gate, not a replacement that drops its six regression scripts. Configure branch protection, when enabled, against only the stable `Tests (单元测试闸门)` check rather than the four matrix-generated names.

- [ ] **Step 5: Run the local equivalents of every matrix leg**

Run:

Run the exact Node container command from Task 2 Step 6 and both exact Python container commands from Task 4 Step 3.

Expected: both frontend profiles pass, all seven lock comparisons pass, and all twenty-two Python process-level test and contract entrypoint invocations pass. The Python 3.11 leg enforces the four primary-runtime lock subset invariants; the stable aggregate policy is covered by `test_workflow_security.py`, both checkout steps are non-credential-persisting, and `git status --short` shows no tracked build-artifact changes.

- [ ] **Step 6: Commit the validation regression and CI matrix**

```bash
git add scripts/tests/test_validate_feed.py scripts/tests/test_workflow_security.py .github/workflows/tests.yml
git diff --cached --check
git commit -m "ci: test both runtime profiles"
```

---

### Task 5: Wire pinned tools and locks into deployment and scheduled workflows

**Files:**
- Modify: `.github/workflows/deploy-pages.yml`
- Modify: `.github/workflows/alpha-routine.yml`
- Modify: `.github/workflows/chan-stats.yml`
- Modify: `.github/workflows/daily-digest.yml`
- Modify: `.github/workflows/daily-screener.yml`
- Modify: `.github/workflows/dependabot-automerge.yml`
- Modify: `.github/workflows/feed-validate.yml`
- Modify: `.github/workflows/feed-watchdog.yml`
- Modify: `.github/workflows/funds-13f.yml`
- Modify: `.github/workflows/hyperliquid-monitor.yml`
- Modify: `.github/workflows/intraday-report.yml`
- Modify: `.github/workflows/market-snapshot.yml`
- Modify: `.github/workflows/monthly-studies.yml`
- Modify: `.github/workflows/openclaw-notes.yml`
- Modify: `.github/workflows/premarket-pack.yml`
- Modify: `scripts/openclaw_daily.py`
- Modify: `scripts/tests/test_feed_publication.py`
- Modify: `scripts/tests/test_workflow_security.py`
- Modify: `render.yaml`
- Modify: `backend/README.md`
- Modify: `docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md`

**Interfaces:**
- Consumes: `.node-version`, `.python-version`, generated hash locks including `requirements/automation.txt`, Task 2's static build/smoke commands, and the supported local Winter configuration path `~/.config/stock-analysis/openclaw.env`.
- Produces: Pages, Render, and all sixteen production Python jobs wired to pinned, reproducible entry points; a read-only `WINTER_PG_DSN` configuration probe; fail-fast configured PostgreSQL child execution; and a fail-closed inventory for direct Python interpreter tokens and setup-python actions.
- Scope is exactly the twenty product files above plus this plan. Do not modify Task 4's `.github/workflows/tests.yml` or `scripts/tests/test_validate_feed.py`; any version file, direct dependency input, generated lock, frontend source/configuration, Winter PostgreSQL child script, or feed artifact; or controller scratch under `.superpowers/`.
- Non-goals: do not repair funds/intraday/watchdog retry failure semantics, create a global publication queue, change Dependabot concurrency, change authentication or Git-push behavior beyond the explicit non-pushing sweep credential hardening, deploy Pages/Render, or modify a feed artifact. These publication-reliability items remain Stage 2/P1.

- [ ] **Step 1: Snapshot immutable inputs and the behavior that Task 5 is not allowed to change**

Run:

```bash
set -eu
git rev-parse HEAD > /tmp/stage1b-task5-baseline-head
git ls-files -- \
  .node-version .python-version backend/runtime.txt \
  backend/requirements.in backend/requirements.txt \
  scripts/requirements.in scripts/requirements.txt \
  scripts/requirements-winter-pg.in scripts/requirements-winter-pg.txt \
  backtest/requirements.in backtest/requirements.txt \
  requirements frontend feed \
  .github/workflows/tests.yml scripts/tests/test_validate_feed.py \
  | LC_ALL=C sort \
  | while IFS= read -r tracked_file; do shasum -a 256 "$tracked_file"; done \
  > /tmp/stage1b-task5-byte-baseline.sha256
find . -xdev -user root -print | LC_ALL=C sort \
  > /tmp/stage1b-task5-root-owned-baseline

rg -n \
  'actions/setup-node@v[1-6]|node-version: 20|python-version: "3\.(11|12)"|(^|[[:space:]])pip install -r|rm -rf app/api|(^|[[:space:]])python3([[:space:]]|$)' \
  .github/workflows render.yaml backend/README.md
```

Expected: the immutable-input manifest is created from the Task 4 commit. Policy matches include Pages' major-only Node pin and source deletion, mixed 3.11/3.12 workflow pins, bare installs, implicit `python3` commands, and the backend README's non-hash install.

Before any production edit, add a complete protected-workflow snapshot to `scripts/tests/test_workflow_security.py`. The protected set is all fourteen production Python workflow files:

```python
PROTECTED_PYTHON_WORKFLOWS = {
    "alpha-routine.yml",
    "chan-stats.yml",
    "daily-digest.yml",
    "daily-screener.yml",
    "dependabot-automerge.yml",
    "feed-validate.yml",
    "feed-watchdog.yml",
    "funds-13f.yml",
    "hyperliquid-monitor.yml",
    "intraday-report.yml",
    "market-snapshot.yml",
    "monthly-studies.yml",
    "openclaw-notes.yml",
    "premarket-pack.yml",
}
```

Declare the exact sixteen job-to-runtime/lock entries immediately after that set, before any helper refers to them:

```python
PRODUCTION_PYTHON_JOBS = {
    ("alpha-routine.yml", "run"): (".python-version", "requirements/automation.txt"),
    ("monthly-studies.yml", "studies"): (".python-version", "requirements/automation.txt"),
    ("chan-stats.yml", "stats"): (".python-version", "backend/requirements.txt"),
    ("daily-screener.yml", "screen"): (".python-version", "backend/requirements.txt"),
    ("feed-validate.yml", "pr-validate"): (
        "trusted/.python-version",
        "trusted/scripts/requirements.txt",
    ),
    ("feed-validate.yml", "publish"): (".python-version", "scripts/requirements.txt"),
    ("hyperliquid-monitor.yml", "monitor"): (".python-version", "scripts/requirements.txt"),
    ("daily-digest.yml", "digest"): (".python-version", None),
    ("funds-13f.yml", "track"): (".python-version", None),
    ("intraday-report.yml", "report"): (".python-version", None),
    ("market-snapshot.yml", "snapshot"): (".python-version", None),
    ("openclaw-notes.yml", "notes"): (".python-version", None),
    ("premarket-pack.yml", "pack"): (".python-version", None),
    ("feed-watchdog.yml", "audit"): (".python-version", None),
    ("dependabot-automerge.yml", "on-pr"): (".python-version", None),
    ("dependabot-automerge.yml", "sweep"): (".python-version", None),
}
```

Do not derive `PROTECTED_PYTHON_WORKFLOWS` from this later constant: both declarations are explicit, and a test requires that the filenames in the sixteen-entry mapping equal the fourteen-name protected set.

Before implementing the normalizer, embed its approval authority directly in `scripts/tests/test_workflow_security.py`. These are immutable test-source literals, not values learned from `root`, `overrides`, parsed YAML shape, the workflow currently under test, or `PRODUCTION_PYTHON_JOBS`:

```python
BASELINE_MISSING_SETUP_JOBS = {
    ("feed-watchdog.yml", "audit"),
    ("dependabot-automerge.yml", "on-pr"),
    ("dependabot-automerge.yml", "sweep"),
}

DEPENDENCY_JOBS = {
    ("alpha-routine.yml", "run"),
    ("monthly-studies.yml", "studies"),
    ("chan-stats.yml", "stats"),
    ("daily-screener.yml", "screen"),
    ("feed-validate.yml", "pr-validate"),
    ("feed-validate.yml", "publish"),
    ("hyperliquid-monitor.yml", "monitor"),
}

APPROVED_PYTHON_RUN_BODY_KEYS = {
    (
        "dependabot-automerge.yml",
        "on-pr",
        "清理旧资格并撤销 auto-merge",
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "根据 metadata 同步 auto-merge 资格标签",
    ),
    (
        "dependabot-automerge.yml",
        "on-pr",
        "检查 required checks 后启用 auto-merge",
    ),
    (
        "dependabot-automerge.yml",
        "sweep",
        "清扫存量 dependabot PR",
    ),
    ("funds-13f.yml", "track", "提交 + 新披露开 Issue"),
    (
        "intraday-report.yml",
        "report",
        "三轮循环(5 分钟节拍 × 3,内嵌备胎守卫)",
    ),
    (
        "feed-watchdog.yml",
        "audit",
        "三级备胎:live 盘中流 >30 分钟陈旧则就地补跑一轮",
    ),
    ("feed-watchdog.yml", "audit", "运行审计并写 health.json"),
}
```

Define these exact dictionaries/constants next:

- `CURRENT_SETUP_STEPS`: thirteen explicit `(filename, job) -> raw entire step` entries. Five values are the exact `python-version: "3.12"` Task 4 step (`alpha`, `monthly`, both feed jobs, and `hyperliquid`); seven are the exact `python-version: "3.11"` step (`chan`, `daily-screener`, `daily-digest`, `funds`, `intraday`, `market`, and `premarket`); `openclaw-notes/notes` is the same 3.11 raw step with its existing additional blank separator. The three `BASELINE_MISSING_SETUP_JOBS` have no current entry.
- `FINAL_SETUP_STEPS`: sixteen explicit entries. Each value is the exact whole final step shown in Step 5, including `python-version-file`, and, for the seven dependency jobs only, exact cache and lock path. The `openclaw-notes/notes` value alone retains its additional blank separator.
- `CURRENT_INSTALL_STEPS`: seven explicit entries copied byte-for-byte from Task 4. They include the complete `name: 安装依赖` alpha step, complete named trusted-validator step, and five unnamed steps.
- `FINAL_INSTALL_STEPS`: seven explicit entries copied from the exact Step 5 result. They preserve those two names and separators and contain only the classified `python -m pip install --require-hashes -r <exact lock>` command.
- `APPROVED_PYTHON_RUN_BODIES`: exactly the eight keys above. Each value is a three-tuple `(current_body_literal, final_body_literal, current_python3_count)`. Both bodies must be independently embedded triple-quoted literals copied from the audited Task 4 and exact Task 5 forms; never generate either body from the workflow under test. The counts in key order are `2, 2, 1, 1, 1, 1, 2, 1`, totaling eleven.
- `FINAL_SMOKE_STEPS`: exactly two explicit whole-step literals, keyed by alpha and monthly, including the exact common name `Smoke combined automation imports` and respective exact command. Baseline smoke presence is exactly zero.
- `CURRENT_SWEEP_CHECKOUT_STEP` and `FINAL_SWEEP_CHECKOUT_STEP`: the exact one-line Task 4 checkout and exact final checkout containing only `persist-credentials: false`, including separators.

Literal reuse through a fixed test-source string such as `CURRENT_SETUP_311` is permitted, but no value may be read, templated, or inferred from a tested file. Assert these authority invariants before normalization:

```python
assert len(PRODUCTION_PYTHON_JOBS) == 16
assert len(CURRENT_SETUP_STEPS) == 13
assert set(CURRENT_SETUP_STEPS) == (
    set(PRODUCTION_PYTHON_JOBS) - BASELINE_MISSING_SETUP_JOBS
)
assert len(FINAL_SETUP_STEPS) == 16
assert set(FINAL_SETUP_STEPS) == set(PRODUCTION_PYTHON_JOBS)
assert len(CURRENT_INSTALL_STEPS) == 7
assert len(FINAL_INSTALL_STEPS) == 7
assert set(CURRENT_INSTALL_STEPS) == DEPENDENCY_JOBS
assert set(FINAL_INSTALL_STEPS) == DEPENDENCY_JOBS
assert len(APPROVED_PYTHON_RUN_BODIES) == 8
assert set(APPROVED_PYTHON_RUN_BODIES) == APPROVED_PYTHON_RUN_BODY_KEYS
assert sum(item[2] for item in APPROVED_PYTHON_RUN_BODIES.values()) == 11
assert set(FINAL_SMOKE_STEPS) == {
    ("alpha-routine.yml", "run"),
    ("monthly-studies.yml", "studies"),
}
```

Add `normalized_protected_workflows(root, overrides=None) -> dict[str, str]`. It must read the full text of every protected file and preserve every byte except the exact fixed literals above. Implement it as a two-phase, two-state validator:

1. Read every file with `Path.read_bytes().decode("utf-8")`, preserving newline bytes; `overrides` may contain only a protected basename. Locate every job and raw step span exactly once. Inventory every `actions/setup-python@*` step and every executable `pip install`/`python -m pip install` step across all jobs in the protected files, including unclassified/shadow jobs.
2. Before replacing anything, match the **entire fourteen-file set** against one state vector:
   - `BASELINE`: all thirteen `CURRENT_SETUP_STEPS` are present exactly once and immediately after their final checkout; the three missing setup sites have none; all seven current installs are present exactly once; both smoke steps are absent; sweep uses the exact current checkout; and all eight Python bodies equal their current literals.
   - `FINAL`: all sixteen `FINAL_SETUP_STEPS` are present exactly once in the required location; all seven final installs and both final smoke steps are present exactly once in the required order; sweep uses the exact final checkout; and all eight Python bodies equal their final literals.
   - A per-job/category mixture, partial migration, missing required literal, duplicate, near miss, wrong location/input/name/command, or candidate outside the fixed site inventory matches neither state and raises `ValueError`. The normalizer must never independently choose current/final at each site.
   - There is no site-local third option: the thirteen baseline-present setup jobs may never be zero, and only watchdog plus the two Dependabot jobs are zero in `BASELINE`; those three must contain their exact final setup in `FINAL`.
   - Implement the decision as `current_ok = exact_current_sites and candidate_inventory == CURRENT_INVENTORY`, `final_ok = exact_final_sites and candidate_inventory == FINAL_INVENTORY`, then require `current_ok ^ final_ok` before replacement. Inventory counts (`13/7/0/11` versus `16/7/2/0` for setup/install/smoke/`python3`) are supplemental checks, never substitutes for whole-span/body equality.
3. Only after the set is proven wholly `BASELINE` or wholly `FINAL`, replace the state-specific setup steps with `      - __TASK5_ALLOWED_SETUP__`, the entire install steps (including names) in place with `      - __TASK5_ALLOWED_INSTALL__`, both smoke sites with `      - __TASK5_ALLOWED_SMOKE__`, and sweep checkout with:

```yaml
      - uses: actions/checkout@v7
        __TASK5_ALLOWED_SWEEP_CREDENTIAL__
```

Emit the embedded final Python body for every approved run-body site. Collect all non-overlapping replacements against the original raw spans and apply them in descending offset order. Whole-span equality is mandatory; no substring approval or permissive YAML-shape matching is allowed. Protected files may contain no setup/install candidate outside the embedded site inventories. Workflows outside the fourteen-file protected set remain covered by Step 4's independent global inventory.

Bytes outside the explicitly recognized spans and eleven token replacements remain unchanged, so the payload is a complete full-file snapshot, not a selected-step projection. The returned value is exactly `{filename: normalized_full_file_text}`. Serialize it with:

```python
encoded = json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode()
```

Three independent literal-driven line-span implementations over Task 4 `HEAD` and a complete in-memory Task 5 final state reproduce byte-identical payloads: 41,968 normalized source bytes and exactly 43,994 encoded JSON bytes with SHA-256:

```python
PROTECTED_WORKFLOW_SHA256 = (
    "9b634f7b39ea0f1b232bde96db36214b3871618be076f8029d15cce0330d3e35"
)
```

Add `test_all_protected_workflow_behavior_is_unchanged()` to:

- normalize the checked-out protected set, whether it is wholly baseline or wholly final;
- create the opposite complete state in memory by replacing every embedded current literal with its embedded final literal, or vice versa, across the full transition table;
- normalize both states and assert their full dictionaries are byte-identical, their concatenated normalized source is 41,968 bytes, their encoded JSON is 43,994 bytes, and both digests equal `PROTECTED_WORKFLOW_SHA256`.

The opposite-state fixture may apply fixed source constants but may not learn an approved literal from the checked-out files.

Add `test_protected_workflow_normalizer_rejects_unapproved_variants()` and require `ValueError`, before digest comparison, for each independent override:

- delete the exact current setup from one of the thirteen baseline-present jobs; also delete one setup from a complete synthetic final state, including a final-only watchdog setup case;
- make a current setup near miss by changing its literal version/input, and separately duplicate or move an otherwise exact setup;
- make a current install near miss by changing its name or command, and separately delete or duplicate an install;
- append a shadow job in a protected file containing an extra `actions/setup-python@v6` step but no Python command;
- add an install step to a standard-library job or other site outside `DEPENDENCY_JOBS`;
- migrate only one of a multi-token approved Python body, migrate only one complete body/job while the other approved bodies remain current, and reverse only one body in the complete final fixture.

Every case above calls `normalized_protected_workflows(..., overrides=...)` inside `assertRaises(ValueError)`; a changed digest alone is not an acceptable result. Also reject a state in which all eleven Python tokens are final but setup/install/smoke/sweep remain baseline, proving state selection is repository-wide rather than category-local.

Add the existing protected-business table-driven mutation tests using `overrides={filename: mutated_text}` and one exact replacement each:

```python
PROTECTED_WORKFLOW_MUTATIONS = [
    (
        "alpha-routine.yml",
        "python scripts/run_routine.py $ARGS",
        "python scripts/run_routine.py $ARGS --unexpected",
        "unselected producer step",
    ),
    ("alpha-routine.yml", "  contents: write", "  contents: read", "permission"),
    (
        "hyperliquid-monitor.yml",
        "    timeout-minutes: 10",
        "    timeout-minutes: 11",
        "timeout",
    ),
    (
        "alpha-routine.yml",
        "FEED_PUBLICATION_MANIFEST: /tmp/feed-publication-${{ github.run_id }}.json",
        "FEED_PUBLICATION_MANIFEST: /tmp/changed-${{ github.run_id }}.json",
        "environment",
    ),
    (
        "alpha-routine.yml",
        '    - cron: "30 22 * * 1-5"',
        '    - cron: "31 22 * * 1-5"',
        "trigger",
    ),
    (
        "alpha-routine.yml",
        "for i in 1 2 3 4; do",
        "for i in 1 2 3; do",
        "retry",
    ),
]
```

Each old string must occur exactly once; each structurally valid baseline/final mutation remains classifiable but produces a digest different from `PROTECTED_WORKFLOW_SHA256`. Put these cases in `test_protected_workflow_mutations_are_detected()`. Separate exact policies in Steps 4–6 continue to validate every normalized-away setup, install, smoke, and sweep-credential block.

Before Step 2, run only the complete current/final snapshot, structural rejection matrix, and six protected-business mutation categories in this exact focused container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -m unittest \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_all_protected_workflow_behavior_is_unchanged \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_protected_workflow_normalizer_rejects_unapproved_variants \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_protected_workflow_mutations_are_detected
  '
```

Expected: GREEN against both complete current and synthetic-final fixtures. Every deletion, near miss, extra out-of-inventory setup/install, or partial/mixed Python migration raises; each unselected producer, permission, timeout, environment, trigger, and retry mutation remains valid input but changes the complete digest.

- [ ] **Step 2: Write the optional Winter PostgreSQL boundary tests and record RED**

Add `contextlib` and `io` imports plus an `OpenClawPostgresBoundaryTests` class to `scripts/tests/test_feed_publication.py`. Every case uses a temporary `HOME`, creates or omits `.config/stock-analysis/openclaw.env`, restores `os.environ` after the test, patches only `openclaw_daily.subprocess.run`, and captures both stdout and stderr.

Add these exact cases:

```text
test_archive_pg_skips_without_process_or_local_configuration
  no WINTER_PG_DSN and no file; zero child calls; stdout contains
  "[daily] pg skipped: WINTER_PG_DSN not configured"

test_archive_pg_redacts_process_dsn_from_success_stdout_and_stderr
  WINTER_PG_DSN="postgresql://process-secret-marker"; the three successful
  CompletedProcess fakes put that exact DSN respectively in stdout, in stderr
  while stdout is empty, and in both streams; captured output contains the
  existing `[daily] pg `, `[daily] winrate `, and `[daily] event-heat ` prefixes
  plus `[REDACTED]`, but neither captured stream contains the exact DSN

test_archive_pg_preserves_supported_local_configuration
  process key absent; local file contains blank/comment/malformed/non-target lines
  followed by ` WINTER_PG_DSN = 'postgresql://local-secret' `; three calls;
  the successful fakes exercise the same stdout-only, stderr-only, and
  both-stream cases with that exact DSN; environment before/after is identical;
  captured output contains `[REDACTED]` and the three existing prefixes, while
  neither captured stream contains the DSN

test_archive_pg_explicit_empty_process_value_wins
  process key is present with ""; local file has a nonempty value; zero calls

test_archive_pg_first_local_assignment_wins_even_when_empty
  local file first assigns WINTER_PG_DSN="", then assigns a nonempty duplicate;
  zero calls; a file containing only a non-target key also makes zero calls

test_archive_pg_ingest_failure_is_fail_fast
test_archive_pg_winrate_failure_is_fail_fast
test_archive_pg_event_heat_failure_is_fail_fast
  return codes are respectively [7], [0, 8], and [0, 0, 9];
  every failing CompletedProcess puts the exact configured
  "postgresql://failure-secret-marker" in both stdout and stderr; each raises
  subprocess.CalledProcessError with returncode 7, 8, or 9 and records exactly
  1, 2, or 3 unchanged child commands; before the exception, captured output
  contains that child's existing log prefix and `[REDACTED]`; the exact DSN is
  absent from both captured streams and from the exception's `.stdout` and
  `.stderr`, while both exception streams retain `[REDACTED]`
```

The exact command list asserted by every configured case is:

```python
[
    [sys.executable, "scripts/winter_pg/ingest.py"],
    [sys.executable, "scripts/winter_pg/winrate.py", "--if-due"],
    [sys.executable, "scripts/winter_pg/event_heat.py"],
]
```

Use `subprocess.CompletedProcess(command, code, stdout=..., stderr=...)` for fakes and `self.assertRaises(subprocess.CalledProcessError)`. Assertions for `[REDACTED]` and the existing prefix are mandatory so a test cannot pass merely because implementation output was omitted. Run this exact Python 3.11 focused container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python scripts/tests/test_feed_publication.py
  '
```

Expected: the new skip/config/fail-fast cases fail against the current unconditional best-effort `archive_pg()`. Existing feed-publication cases remain green.

- [ ] **Step 3: Implement the minimal read-only configuration probe and fail-fast children**

In `scripts/openclaw_daily.py`, add `from pathlib import Path` if it is not already imported, then add exactly this same-file probe:

```python
def _winter_pg_dsn() -> str | None:
    """Return the exact non-empty DSN the child loaders would resolve."""
    if "WINTER_PG_DSN" in os.environ:
        return os.environ["WINTER_PG_DSN"] or None

    env_file = Path.home() / ".config/stock-analysis/openclaw.env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "WINTER_PG_DSN":
            value = value.strip().strip('"').strip("'")
            return value or None
    return None
```

This is deliberately read-only: it mirrors the child loaders' first-assignment `setdefault` behavior without inserting any value into the parent environment. Do not strip or rewrite a process-environment value; preserve the local file parser's exact `strip().strip('"').strip("'")` behavior; return immediately on the first local target assignment even when it is empty. Replace `archive_pg()` with the same three commands and existing log labels, but:

```python
def archive_pg() -> None:
    """Skip when unconfigured; run configured local warehouse jobs fail-fast."""
    dsn = _winter_pg_dsn()
    if dsn is None:
        print("[daily] pg skipped: WINTER_PG_DSN not configured")
        return

    commands = (
        ([sys.executable, "scripts/winter_pg/ingest.py"], "[daily] pg ", None),
        (
            [sys.executable, "scripts/winter_pg/winrate.py", "--if-due"],
            "[daily] winrate ",
            "not due",
        ),
        (
            [sys.executable, "scripts/winter_pg/event_heat.py"],
            "[daily] event-heat ",
            None,
        ),
    )
    for command, prefix, suppressed in commands:
        result = subprocess.run(
            command,
            cwd=fl.REPO_ROOT,
            capture_output=True,
            text=True,
        )
        safe_stdout = (result.stdout or "").replace(dsn, "[REDACTED]")
        safe_stderr = (result.stderr or "").replace(dsn, "[REDACTED]")
        message = (safe_stdout or safe_stderr).strip()
        if message and (suppressed is None or suppressed not in message):
            print(f"{prefix}{message}")
        result.stdout = safe_stdout
        result.stderr = safe_stderr
        result.check_returncode()
```

Mutating the `CompletedProcess` streams before `check_returncode()` is required: the raised `CalledProcessError.output`/`.stderr` must be sanitized as well as console output. Run the exact focused container again:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python scripts/tests/test_feed_publication.py
  '
```

Expected: all cases pass; an unconfigured Actions run spawns no PostgreSQL child, while a configured local process retains the existing local config path, redacts the exact DSN from success and failure stdout/stderr and the raised exception, logs before propagating child failure, and never mutates the environment. Do not install `scripts/requirements-winter-pg.txt` in any workflow, Render service, or backend environment.

- [ ] **Step 4: Add a fail-closed direct-interpreter/setup-action inventory and record RED**

Use the exact `PRODUCTION_PYTHON_JOBS` mapping already declared before the Step 1 normalizer. Add helpers that inspect every `run:` body returned by `workflow_run_scripts()`, including block scalars and heredocs. Preserve the raw interpreter token and detect bare, quoted, path-qualified, and versioned forms with:

```python
PYTHON_INTERPRETER_TOKEN = re.compile(
    r'''(?x)
    (?<![A-Za-z0-9_./$~{}+\-])
    (?:
      "(?:(?:[^"\r\n]*/)?python(?:3(?:\.\d+)*)?)"
     |
      '(?:(?:[^'\r\n]*/)?python(?:3(?:\.\d+)*)?)'
     |
      (?:
        (?:
          (?:/|\./|\.\./|~/|\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})/)
          (?:[^\s"';&|()<>]+/)*
        )
       |
        (?:[A-Za-z0-9_.~+${}\-]+/)+
      )?
      python(?:3(?:\.\d+)*)?
    )
    (?=$|[\s;&|()<>])
    '''
)
```

Enumerate every job in every `.github/workflows/*.yml`/`*.yaml`; the set of jobs containing any matching direct Python interpreter token must equal `set(PRODUCTION_PYTHON_JOBS) | {("tests.yml", "python")}`. A direct `python`/`python3` token in an unknown job fails closed. In a final production `run:` body, every match's complete raw text must be exactly unquoted, unqualified `python`; therefore absolute/relative paths, quoted paths including `"/tmp/my env/bin/python"`, `$VENV/bin/python`, `${VENV}/bin/python3.12`, quoted bare/versioned tokens, and `python3.12` all fail even though they remain discoverable.

This is deliberately a fail-closed **direct lexical token and setup-action inventory**, not a general Bash/POSIX parser. It does not claim to interpret aliases, functions, `eval`, command variables/substitutions, shebang execution, or split/escaped spellings such as `python\` followed by a newline, `py\thon`, `pyt''hon`, or direct `./script.py`. During Task 5, the fourteen normalized full-file snapshots, exact raw Pages file, frozen `tests.yml`, and exact changed-path set prevent adding or rewriting workflow commands into those forms even though the token regex itself does not parse them. Continue to reject an explicit direct `python`/`python3` token in any unknown job; do not broaden that corrected contract into an arbitrary-shell guarantee.

Independently inventory every step whose `uses` starts with `actions/setup-python@`, including jobs with no Python command. Also inventory every raw `actions/setup-python@` occurrence across every workflow and require a one-to-one correspondence with those parsed step spans, so an occurrence outside a job/step cannot hide. The exact job-key set must be `set(PRODUCTION_PYTHON_JOBS) | {("tests.yml", "python")}`, the raw and parsed occurrence counts must both be exactly seventeen, each key must have exactly one setup action, and every action must be exactly `actions/setup-python@v6`. This global action inventory is separate from Python-command discovery so a shadow setup job cannot hide.

For each classified production job, assert:

- exactly one `actions/setup-python@v6` block;
- its `python-version-file` is exact, it has no literal `python-version`, no `if`, and no `continue-on-error`;
- it occurs after the job's final checkout and before its first Python command;
- dependency jobs have `cache: pip`, exact `cache-dependency-path`, and exactly one unconditional run body `python -m pip install --require-hashes -r <lock>`; the complete install step name is exactly `安装依赖` in `alpha-routine/run`, exactly `Install trusted validator dependencies` in `feed-validate/pr-validate`, and absent in the other five;
- standard-library jobs have no pip install and no setup cache;
- no post-setup production run body invokes `python3`, and no other production workflow install exists; Task 4's exact `tests.yml/python` matrix remains the sole CI exception;
- alpha and monthly contain their exact smoke imports once:
  `PYTHONPATH=backtest:scripts python -c "import factor_factory, feed_lib, run_routine, statarb"` and
  `PYTHONPATH=backtest:scripts python -c "import feed_lib, statarb, study_downshift, study_pbo"`;
- both `feed-validate/pr-validate` checkouts are non-credential-persisting; the trusted base SHA is at `trusted/`; the head repo/SHA is at `submission/` with `allow-unsafe-pr-checkout: true`; setup occurs after both checkouts; and install/execution paths use only `trusted/`, never executable content from `submission/`;
- within the fourteen Task 5 production Python workflows, checkout credentials are false only for both PR-validation checkouts, Dependabot `on-pr`, and Dependabot `sweep`. Every production job that Git-pushes retains credentials; `feed-validate/publish` remains credentialed. Do not include Pages in this Step 4/5 credential gate: the current Pages checkout is intentionally still baseline here, and Step 6's complete byte-exact Pages validator owns its transition to `persist-credentials: false`. Task 4's frozen `tests.yml/frontend` and `tests.yml/python` checkouts are separate exact exceptions: each remains one `actions/checkout@v7` step with only `persist-credentials: false`, and Step 8's Task 4 non-drift check prevents either from changing;
- Dependabot's direct top-level `concurrency` mapping is exactly `group: dependabot-automerge-${{ github.repository }}` followed by `queue: max`; it has no `cancel-in-progress` or other key. Mutations that change `queue`, add `cancel-in-progress`, or add any concurrency key must fail;
- required setup/install steps contain no `if`, `continue-on-error`, `|| true`, or extra setup/install block.
- Task 4's sole exception, `tests.yml/python`, still has exactly one setup-python v6 step with literal structure `python-version: ${{ matrix.python_version }}`, `cache: pip`, and `cache-dependency-path: ${{ matrix.lockfile }}`; it has no `python-version-file`, `if`, or `continue-on-error`.

Add table-driven mutation tests that run the real policy helper, not only the regex:

```python
FORBIDDEN_INTERPRETER_MUTATIONS = (
    "/usr/bin/python scripts/daily_digest.py",
    '"/tmp/venv/bin/python" scripts/daily_digest.py',
    '"/tmp/my env/bin/python" scripts/daily_digest.py',
    "$VENV/bin/python scripts/daily_digest.py",
    "${VENV}/bin/python3.12 scripts/daily_digest.py",
    "'python3.11' scripts/daily_digest.py",
    "python3.12 scripts/daily_digest.py",
)
```

Each replaces the exact canonical `python scripts/daily_digest.py` in a temporary override and must fail through the real policy helper. The test must assert the scanner returns the entire raw mutated token, including quotes, spaces, `$`, or `${...}`, before the policy rejects it. Also require these independent inventory mutations to fail:

- append a shadow job with `actions/setup-python@v5` and no `run:` body;
- insert a second setup-python step into a classified job;
- change the sole setup action in one allowed job from `@v6` to `@v5`.

Finally mutate each normalized-away category and prove its exact semantic policy fails: move a valid setup behind a business step; change one `python-version-file` or cache input; alter the alpha install name or any hashed install command; alter one smoke import list; and change the Dependabot sweep checkout to `persist-credentials: true` or add another checkout input.

Run the exact focused container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python scripts/tests/test_workflow_security.py
  '
```

Expected: RED because watchdog and Dependabot jobs have no setup, literals and `python3` remain, installs are unhashed, and dependency jobs do not match their locks. The complete protected-workflow normalized full-file digest from Step 1 remains green.

- [ ] **Step 5: Normalize all sixteen production Python jobs without changing their business behavior**

Apply the classification literally. A dependency-bearing setup is:

```yaml
      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
          cache: pip
          cache-dependency-path: requirements/automation.txt
      - run: python -m pip install --require-hashes -r requirements/automation.txt
```

Substitute the classified version-file and lock paths for each job. A standard-library setup has only:

```yaml
      - uses: actions/setup-python@v6
        with:
          python-version-file: .python-version
```

The generic dependency example is unnamed only for the five originally unnamed installs. Preserve these two exact named variants:

```yaml
      - name: 安装依赖
        run: python -m pip install --require-hashes -r requirements/automation.txt
```

```yaml
      - name: Install trusted validator dependencies
        run: python -m pip install --require-hashes -r trusted/scripts/requirements.txt
```

Use the first only in `alpha-routine/run`, the second only in `feed-validate/pr-validate`, and no `name` on the other five hashed install steps. Place setup after the final checkout and before the first Python command. In `feed-validate/pr-validate`, use `trusted/.python-version`, `trusted/scripts/requirements.txt`, and the trusted cache path after both checkouts. Replace standalone production `python3` commands with `python`. Add the two exact alpha/monthly smoke-import commands immediately after their hashed installs, each under the exact step name `Smoke combined automation imports`. Add `persist-credentials: false` to the non-pushing Dependabot sweep checkout; leave the already protected Dependabot `on-pr` and feed PR checkouts false; do not change checkout credentials in any pushing job.

Do not change triggers, permissions, timeouts, publication manifests, Git configuration, rebase/push retries, `|| true`, sleep/backoff, worktree behavior, concurrency, or failure handling. In particular, do not repair the known funds exhaustion, intraday swallowing, or watchdog swallowing behavior in this task. Run both focused tests in the exact container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python scripts/tests/test_feed_publication.py
    /tmp/venv/bin/python scripts/tests/test_workflow_security.py
  '
```

Expected: GREEN, including the complete protected-workflow normalized full-file digest and every exact normalized-away policy. No test contacts a live provider.

- [ ] **Step 6: Add the Pages job/step policy, record RED, and replace the workflow**

First add `test_pages_uses_the_complete_isolated_static_profile()` to `scripts/tests/test_workflow_security.py`. Scope every assertion through `on`, `permissions`, `jobs/build`, `jobs/deploy`, and the exact step blocks. Require:

- push paths are exactly `frontend/**`, `feed/schema/**`, `.node-version`, and `.github/workflows/deploy-pages.yml`, plus manual dispatch; ordinary generated feed commits do not trigger Pages;
- workflow permissions are exactly `{}`, build permissions exactly `contents: read`, and deploy permissions exactly `pages: write` plus `id-token: write`;
- one checkout v7 with `persist-credentials: false`, one setup-node v7 with `.node-version` and the frontend npm cache, exact Node/npm assertions, and exactly one unconditional `npm ci`;
- the snapshot step uses only `$RUNNER_TEMP/feed-snapshot`, rejects any missing source, and copies exactly these thirteen entries: `index.json`, `health.json`, `watchlist.json`, `schema`, `reports`, `signals`, `market`, `factory`, `screener`, `stock-notes`, `crypto`, `intraday`, `funds`;
- no step deletes or rewrites `frontend/public/feed` or `frontend/app/api`; the only `rm -rf` target is `"$snapshot"`;
- one unconditional build step supplies `STATIC_FEED_SOURCE`, Pages base, API base, Edge base, and raw feed base, then runs exactly one `npm run build:static` and one `npm run smoke:static`; no default/server build appears;
- an output-verification step requires the same thirteen entries under `out/feed` plus `funds/situational-awareness.json`, `intraday/latest.json`, and `intraday/overnight.json`;
- upload-pages-artifact v5 uploads exactly `frontend/out`, and deploy-pages v5 runs only in the deploy job.

This is a complete structure policy, not a presence check. Define the expected raw UTF-8 workflow text from the exact replacement block below and require byte equality. In addition, parse/scopingly inspect it and require these exact direct-key sets:

```text
top level:             name, on, permissions, concurrency, jobs
on:                    push, workflow_dispatch
push:                  branches, paths
concurrency:           group, cancel-in-progress
jobs:                  build, deploy
build:                 runs-on, permissions, defaults, steps
build.permissions:     contents
build.defaults:        run
build.defaults.run:    working-directory
deploy:                needs, runs-on, permissions, environment, steps
deploy.permissions:    pages, id-token
deploy.environment:    name, url
```

`workflow_dispatch:` is exactly empty and has no inputs; `permissions: {}` is the exact empty inline mapping. Because the existing mapping helper recognizes only a `key:` header, add exact accessors/assertions for those inline and empty forms rather than silently skipping them. Assert inline `branches` and `paths` by their complete raw values.

Require the build step direct-key sets, in exact order, to be:

```text
checkout:              uses, with
setup-node:            uses, with
version assertion:     name, run
snapshot:              name, working-directory, run
npm install:           run
build/smoke:           name, env, run
output verification:   name, run
upload:                uses, with
deploy step:           id, uses
```

The `with` mappings are exact: checkout has only `persist-credentials`; setup-node has only `node-version-file`, `cache`, and `cache-dependency-path`; upload has only `path`; deploy has no `with`. The build/smoke `env` mapping has exactly `STATIC_FEED_SOURCE`, `NEXT_PUBLIC_BASE_PATH`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_EDGE_BASE`, and `NEXT_PUBLIC_FEED_BASE`, with the exact context expressions shown below. No step has an undeclared `if`, `continue-on-error`, `timeout-minutes`, `env`, `with`, or other direct key.

Add mutation tests that each start from the exact expected Pages text and prove the Pages validator rejects:

- an extra top-level key;
- an extra key in either `build` or `deploy`;
- `workflow_dispatch.inputs`;
- checkout `fetch-depth`;
- a wrong setup-node value and an extra setup-node input;
- an extra upload input or any deploy `with`;
- a step-level `if` or `continue-on-error`;
- an extra build environment variable or a substituted/invalid context expression.

Run the method before editing Pages in the exact focused container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -m unittest \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_pages_uses_the_complete_isolated_static_profile
  '
```

Expected: RED on broad permissions, credential persistence, Node major pin, swallowed feed copies, source deletion, default build, missing smoke, and missing output verification.

Replace `.github/workflows/deploy-pages.yml` with:

```yaml
name: Deploy frontend to GitHub Pages

on:
  push:
    branches: [main]
    paths: ["frontend/**", "feed/schema/**", ".node-version", ".github/workflows/deploy-pages.yml"]
  workflow_dispatch:

permissions: {}

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-node@v7
        with:
          node-version-file: .node-version
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Verify exact Node and npm
        run: |
          test "$(node --version)" = "v20.20.2"
          test "$(npm --version)" = "10.8.2"
      - name: Bundle latest feed snapshot
        working-directory: ${{ github.workspace }}
        run: |
          set -euo pipefail
          snapshot="$RUNNER_TEMP/feed-snapshot"
          rm -rf "$snapshot"
          mkdir -p "$snapshot"
          sources=(
            feed/index.json
            feed/health.json
            feed/watchlist.json
            feed/schema
            feed/reports
            feed/signals
            feed/market
            feed/factory
            feed/screener
            feed/stock-notes
            feed/crypto
            feed/intraday
            feed/funds
          )
          for source in "${sources[@]}"; do
            test -e "$source"
          done
          cp -R -- "${sources[@]}" "$snapshot/"
      - run: npm ci
      - name: Build and smoke static profile
        env:
          STATIC_FEED_SOURCE: ${{ runner.temp }}/feed-snapshot
          NEXT_PUBLIC_BASE_PATH: /${{ github.event.repository.name }}
          NEXT_PUBLIC_API_BASE: ${{ vars.API_BASE }}
          NEXT_PUBLIC_EDGE_BASE: ${{ vars.EDGE_BASE }}
          NEXT_PUBLIC_FEED_BASE: https://raw.githubusercontent.com/${{ github.repository }}/${{ github.ref_name }}/feed
        run: |
          npm run build:static
          npm run smoke:static
      - name: Verify complete exported feed snapshot
        run: |
          set -euo pipefail
          entries=(
            index.json
            health.json
            watchlist.json
            schema
            reports
            signals
            market
            factory
            screener
            stock-notes
            crypto
            intraday
            funds
          )
          for entry in "${entries[@]}"; do
            test -e "out/feed/$entry"
          done
          test -f out/feed/funds/situational-awareness.json
          test -f out/feed/intraday/latest.json
          test -f out/feed/intraday/overnight.json
      - uses: actions/upload-pages-artifact@v5
        with:
          path: frontend/out

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```

Run the focused workflow method in the exact container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -m unittest \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_pages_uses_the_complete_isolated_static_profile
  '
```

Expected: GREEN. The only deletion refreshes a runner-temporary snapshot; `build-profile.mjs` overlays it only inside its private frontend copy. Raw GitHub feed data remains live, while the bundled fallback refreshes only on the four explicit path families or manual dispatch. The workflow never deletes or rewrites tracked `frontend/public/feed`, `frontend/app/api`, or another application source path.

- [ ] **Step 7: Add exact Render/quick-start policy, record RED, and consume the backend lock**

Add `test_render_and_backend_quick_start_are_exact()` to `scripts/tests/test_workflow_security.py`. It must compare `render.yaml` to the exact structure below, require one adjacent `PYTHON_VERSION` entry, and assert that the README's ordered command block creates a `python3.11` venv, activates it, performs the exact hash install, and launches with `python -m uvicorn`. Run it first in the exact focused container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -m unittest \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_render_and_backend_quick_start_are_exact
  '
```

Expected: RED on the unhashed Render/README installs, unpinned Render runtime, and direct Uvicorn commands.

Replace `render.yaml` with:

```yaml
# Render Blueprint —— 一键部署后端 FastAPI。
services:
  - type: web
    name: stock-dashboard-api
    runtime: python
    rootDir: backend
    plan: free
    buildCommand: python -m pip install --require-hashes -r requirements.txt
    startCommand: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/v1/health
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.15"
```

The Blueprint owns this pin deliberately: with `rootDir: backend`, Render cannot be assumed to discover the repository-root `.python-version`.

Replace the command block at `backend/README.md:8-14` with:

````markdown
## 运行

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
````

Run the focused policy again in the exact container:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -m unittest \
      scripts.tests.test_workflow_security.WorkflowSecurityTests.test_render_and_backend_quick_start_are_exact
  '
```

Expected: GREEN. Render still has exactly one free web service, `rootDir: backend`, health path `/api/v1/health`, and `autoDeploy: true`; no service is deployed by this task.

- [ ] **Step 8: Run focused, syntax, runtime, non-drift, residue, and exact-scope gates**

Treat the following as the Task 5-scoped semantic equivalent of a workflow linter:

1. all fourteen production Python workflow files pass the complete current/final two-state normalized full-file digest, all structural rejection mutations, and the six protected-behavior digest mutations;
2. all workflow files pass the exact seventeen-job global setup-python inventory, the exact seventeen-job direct-interpreter inventory, and the setup/install/smoke/credential/trusted-PR policies with their quoted-space/variable-path/version/shadow-job mutations;
3. Pages passes raw full-file equality, every direct-key/action-input/context whitelist, and every extra/invalid key/input mutation;
4. Dependabot retains the exact `group` plus `queue: max` concurrency mapping and rejects queue/extra-key mutations;
5. every workflow YAML file receives the Ruby AST parse below as a syntax-only check.

The focused workflow-security file is the semantic gate; Ruby/Psych is only the all-file YAML syntax leg and must not be described as semantic validation. Do not add or download external `actionlint` in this task.

Run:

```bash
set -euo pipefail
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py311.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python scripts/tests/test_feed_publication.py
    /tmp/venv/bin/python scripts/tests/test_workflow_security.py
  '
ruby -e '
  require "yaml"
  Dir[".github/workflows/*.{yml,yaml}"].sort.each do |path|
    abort("empty YAML AST: #{path}") unless YAML.parse_file(path)
  end
  puts "workflow YAML syntax OK"
'

if rg -n \
  'actions/setup-node@v[1-6]|node-version: 20|python-version: "3\.(11|12)"|(^|[[:space:]])pip install -r|rm -rf app/api' \
  .github/workflows render.yaml backend/README.md; then
  echo "forbidden workflow or runtime pattern found" >&2
  exit 1
else
  scan_status=$?
  if [ "$scan_status" -ne 1 ]; then
    echo "workflow/runtime residue scan failed with status $scan_status" >&2
    exit "$scan_status"
  fi
fi
IFS= read -r FORBIDDEN_PYTHON_INTERPRETER_PCRE <<'PCRE'
(?x)(?<![A-Za-z0-9_./$~{}+\-])(?:"(?:(?:[^"\r\n]*/)?python(?:3(?:\.\d+)*)?)"|'(?:(?:[^'\r\n]*/)?python(?:3(?:\.\d+)*)?)'|(?:(?:/|\./|\.\./|~/|\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})/)(?:[^\s"';&|()<>]+/)*|(?:[A-Za-z0-9_.~+${}\-]+/)+)python(?:3(?:\.\d+)*)?|python3(?:\.\d+)*)(?=$|[\s;&|()<>])
PCRE
readonly FORBIDDEN_PYTHON_INTERPRETER_PCRE
if rg -n --pcre2 --glob '*.yml' --glob '*.yaml' -- \
  "$FORBIDDEN_PYTHON_INTERPRETER_PCRE" .github/workflows; then
  echo "forbidden Python interpreter token found" >&2
  exit 1
else
  scan_status=$?
  if [ "$scan_status" -ne 1 ]; then
    echo "interpreter residue scan failed with status $scan_status" >&2
    exit "$scan_status"
  fi
fi
test "$(rg -c '^[[:space:]]+- key: PYTHON_VERSION$' render.yaml)" -eq 1
rg -U -q -- '- key: PYTHON_VERSION\n[[:space:]]+value: "3\.11\.15"' render.yaml
```

Run the exact Node container gate from Task 2 Step 6 and both corrected full-image Python container gates from Task 4 Step 3. The Python preambles must prove Git availability and exact non-root UID/GID before venv creation. Then run:

```bash
set -euo pipefail
test -f frontend/app/api/quote/route.ts
test -f frontend/app/api/ohlcv/route.ts
test -f frontend/.next/BUILD_ID
test "$(shasum -a 256 frontend/package-lock.json | awk '{print $1}')" = "97875c90208b25596cae8ea55482f4c38295aba18b77287f4a11e32208b563d1"
git diff --exit-code "$(cat /tmp/stage1b-task5-baseline-head)" -- \
  .github/workflows/tests.yml scripts/tests/test_validate_feed.py

git ls-files -- \
  .node-version .python-version backend/runtime.txt \
  backend/requirements.in backend/requirements.txt \
  scripts/requirements.in scripts/requirements.txt \
  scripts/requirements-winter-pg.in scripts/requirements-winter-pg.txt \
  backtest/requirements.in backtest/requirements.txt \
  requirements frontend feed \
  .github/workflows/tests.yml scripts/tests/test_validate_feed.py \
  | LC_ALL=C sort \
  | while IFS= read -r tracked_file; do shasum -a 256 "$tracked_file"; done \
  > /tmp/stage1b-task5-byte-current.sha256
cmp /tmp/stage1b-task5-byte-baseline.sha256 /tmp/stage1b-task5-byte-current.sha256
find . -xdev -user root -print | LC_ALL=C sort \
  > /tmp/stage1b-task5-root-owned-current
cmp /tmp/stage1b-task5-root-owned-baseline /tmp/stage1b-task5-root-owned-current

test -z "$(git status --porcelain=v1 --untracked-files=all -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts)"
test -z "$(find frontend -maxdepth 1 \( -name '.out-stage-*' -o -name '.out-backup-*' -o -name '.out-publish.lock*' \) -print -quit)"

cat > /tmp/stage1b-task5-expected-paths <<'EOF'
.github/workflows/alpha-routine.yml
.github/workflows/chan-stats.yml
.github/workflows/daily-digest.yml
.github/workflows/daily-screener.yml
.github/workflows/dependabot-automerge.yml
.github/workflows/deploy-pages.yml
.github/workflows/feed-validate.yml
.github/workflows/feed-watchdog.yml
.github/workflows/funds-13f.yml
.github/workflows/hyperliquid-monitor.yml
.github/workflows/intraday-report.yml
.github/workflows/market-snapshot.yml
.github/workflows/monthly-studies.yml
.github/workflows/openclaw-notes.yml
.github/workflows/premarket-pack.yml
backend/README.md
docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md
render.yaml
scripts/openclaw_daily.py
scripts/tests/test_feed_publication.py
scripts/tests/test_workflow_security.py
EOF
git diff --name-only "$(cat /tmp/stage1b-task5-baseline-head)" -- \
  | LC_ALL=C sort > /tmp/stage1b-task5-actual-paths
LC_ALL=C sort /tmp/stage1b-task5-expected-paths \
  > /tmp/stage1b-task5-expected-paths.sorted
cmp /tmp/stage1b-task5-expected-paths.sorted /tmp/stage1b-task5-actual-paths

git diff --check
git status --short
```

Expected:

- both focused files pass, including exact OpenClaw DSN redaction, byte-identical complete current/final workflow snapshots, structural-rejection and protected-behavior mutations, both exact seventeen-job inventories, quoted-space/`$VENV`/`${VENV}`/version direct-interpreter mutations, setup/install/smoke/feed-trust/credential policies, Pages full-file/direct-key/input/context mutations, Render, README, and unchanged publication/retry behavior;
- Dependabot retains exactly `group: dependabot-automerge-${{ github.repository }}` plus `queue: max`; every workflow parses as YAML in the syntax leg, the task-scoped semantic gate passes, and the negative policy scan finds no prohibited pattern;
- all sixteen jobs read the correct version file; exactly seven install their exact hashed lock and nine install nothing;
- Render declares exactly one adjacent `PYTHON_VERSION: 3.11.15` entry in its Blueprint, independent of the repository-root version file;
- `alpha-routine` and `monthly-studies` each install the combined automation lock and smoke-import their `backtest/` and `scripts/` modules exactly once;
- both frontend profiles pass and the real `app/api` handlers remain present;
- both full Python images expose Git, run under the exact non-root host identity, reproduce their applicable locks, pass all twenty-two current process-level entrypoints with no broken requirements, and create no new root-owned worktree path;
- Task 4 workflow/tests, all version/lock/direct-input/frontend/feed bytes, and the package-lock hash remain unchanged;
- the diff contains exactly the twenty Task 5 product files plus this plan, no private publication residue remains, and `.superpowers/` is neither staged nor included;
- `git diff --check` reports no whitespace errors;
- no Pages/Render deployment occurs. Funds/intraday/watchdog retry reliability, a global publication queue, and Dependabot concurrency remain recorded Stage 2/P1 work, not silently changed here.

- [ ] **Step 9: Stage only the exact Task 5 scope and commit**

```bash
git add \
  .github/workflows/alpha-routine.yml \
  .github/workflows/chan-stats.yml \
  .github/workflows/daily-digest.yml \
  .github/workflows/daily-screener.yml \
  .github/workflows/dependabot-automerge.yml \
  .github/workflows/deploy-pages.yml \
  .github/workflows/feed-validate.yml \
  .github/workflows/feed-watchdog.yml \
  .github/workflows/funds-13f.yml \
  .github/workflows/hyperliquid-monitor.yml \
  .github/workflows/intraday-report.yml \
  .github/workflows/market-snapshot.yml \
  .github/workflows/monthly-studies.yml \
  .github/workflows/openclaw-notes.yml \
  .github/workflows/premarket-pack.yml \
  backend/README.md \
  docs/superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md \
  render.yaml \
  scripts/openclaw_daily.py \
  scripts/tests/test_feed_publication.py \
  scripts/tests/test_workflow_security.py
git diff --cached --check
git diff --cached --name-only | LC_ALL=C sort \
  | cmp /tmp/stage1b-task5-expected-paths.sorted -
git commit -m "ci: use pinned toolchains everywhere"
```

---

## Final Acceptance Gate

After the Task 5 commit, run the exact Node container gate from Task 2 Step 6 and the following two-runtime Python gates once more from a clean checkout. These are intentionally explicit here so the final run cannot fall back to a root/system Python install or a Git-less slim image:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version"
    git --version
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

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env EXPECTED_UID="$(id -u)" \
  --env EXPECTED_GID="$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13 \
  sh -lc '
    set -eu
    test "$(id -u)" = "$EXPECTED_UID"
    test "$(id -g)" = "$EXPECTED_GID"
    test "$(id -u)" -ne 0
    python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version"
    git --version
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

Then run:

```bash
test -f frontend/app/api/quote/route.ts
test -f frontend/app/api/ohlcv/route.ts
test -f frontend/.next/BUILD_ID
test "$(shasum -a 256 frontend/package-lock.json | awk '{print $1}')" = "97875c90208b25596cae8ea55482f4c38295aba18b77287f4a11e32208b563d1"
git diff --exit-code HEAD -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts
test -z "$(git status --porcelain=v1 --untracked-files=all -- frontend/app/api frontend/public/feed frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts)"
test -z "$(find frontend -maxdepth 1 \( -name '.out-stage-*' -o -name '.out-backup-*' -o -name '.out-publish.lock*' \) -print -quit)"
git diff --check
git status --short
```

Expected: all commands exit 0; script tests pass before either build; static smoke reports 12 routes; server smoke reports eleven page passes and two API-route passes; all seven lock comparisons and all twenty-two Python process-level test and contract entrypoint invocations pass; the four primary-runtime cross-lock invariants hold; API/feed/lock/config inputs remain byte-stable; no publication residue or tracked generated artifact is introduced by verification. After this local final gate passes, push the feature branch; require the actual GitHub `Frontend (static)`, `Frontend (server)`, `Python (3.11.15)`, `Python (3.12.13)`, and stable `Tests (单元测试闸门)` jobs to succeed before merge.
