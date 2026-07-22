# Stage 1B Reproducible Toolchain and CI Implementation Plan

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
- All application/runtime Python installs used by CI, Docker, Render, and scheduled workflows must consume generated lockfiles with `--require-hashes`; the only bootstrap exception is Task 3's exact pip-tools 7.5.2 install used to create the first generation of those locks.
- Generate every committed Python lock with pip-tools 7.5.2 and `--no-header`; CI and the local Python matrix gates must regenerate the applicable locks into a temporary directory and compare them byte-for-byte with `cmp`.
- Every host-mounted Python Docker command must run as the host UID/GID with `HOME=/tmp/home` and `PYTHONDONTWRITEBYTECODE=1`, create `/tmp/venv`, and install and execute through that venv so verification cannot leave root-owned bytecode or environment files in the worktree.
- The deployable backend image excludes host bytecode/databases from its context, runs as numeric non-root user `10001:10001`, and uses `exec` so Uvicorn receives termination signals.
- Normal CI and smoke tests must be offline with respect to market-data providers. Localhost HTTP requests are allowed.
- Keep the existing direct-execution Python tests; converting them to pytest is outside Stage 1B.
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
- `.github/workflows/feed-validate.yml`
- `.github/workflows/funds-13f.yml`
- `.github/workflows/hyperliquid-monitor.yml`
- `.github/workflows/intraday-report.yml`
- `.github/workflows/market-snapshot.yml`
- `.github/workflows/monthly-studies.yml`
- `.github/workflows/openclaw-notes.yml`
- `.github/workflows/premarket-pack.yml`
- `render.yaml` — exact Render Python version and hash-checked backend install.
- `backend/README.md` — deterministic backend installation command.

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
docker pull python:3.11.15-slim
docker pull python:3.12.13-slim
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
  -v /private/tmp/stock-analysis-codex-stage-1-refactor:/workspace \
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
- Create: `backend/.dockerignore`
- Modify: `backend/runtime.txt`
- Modify: `backend/Dockerfile`

**Interfaces:**
- Consumes: the current imports in `backend/`, `scripts/`, `scripts/winter_pg/`, and `backtest/`.
- Produces: direct dependency declarations plus complete, hash-checked install inputs for production, feed validation, combined script/backtest automation, research, optional PostgreSQL tools, and both CI Python versions.

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
```

Create `scripts/requirements.in`:

```text
# Automation and feed validation. Research engines remain in backtest/requirements.in.
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
pandas>=2,<3
lxml>=5,<7
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
pip-tools==7.5.2
```

- [ ] **Step 3: Generate every committed lock with fixed interpreters and pip-tools**

Generate every primary-runtime lock from the exact Linux runtime used by deployment and CI:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15-slim \
  sh -lc '
    python -m venv /tmp/venv &&
    /tmp/venv/bin/python -m pip install pip-tools==7.5.2 &&
    /tmp/venv/bin/python -c "import sys; assert sys.version_info[:3] == (3, 11, 15), sys.version" &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=backend/requirements.txt backend/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=scripts/requirements.txt scripts/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=scripts/requirements-winter-pg.txt scripts/requirements-winter-pg.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=backtest/requirements.txt backtest/requirements.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/automation.txt requirements/automation.in &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/ci-py311.txt requirements/ci.in
  '
```

Generate the compatibility lock with Python 3.12.13:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13-slim \
  sh -lc '
    python -m venv /tmp/venv &&
    /tmp/venv/bin/python -m pip install pip-tools==7.5.2 &&
    /tmp/venv/bin/python -c "import sys; assert sys.version_info[:3] == (3, 12, 13), sys.version" &&
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file=requirements/ci-py312.txt requirements/ci.in
  '
```

Expected: every output is header-free, contains only pinned versions, environment markers where required, and one or more `--hash=sha256:` entries per resolved distribution. The two CI locks resolve successfully under their named interpreters, and both include pip-tools 7.5.2 so the installed CI environments can reproduce their own locks.

- [ ] **Step 4: Pin the backend runtime and enforce hashes in Docker**

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
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.db
*.sqlite
*.sqlite3
```

The numeric runtime identity keeps the image independent of host user databases; the default SQLite files remain writable under `/tmp`, while mounted persistent paths must be granted deliberately by the deployer. `exec` makes Uvicorn receive container stop signals directly.

- [ ] **Step 5: Verify each lock in a clean environment**

Run:

```bash
set -e
for file in backend/requirements.txt scripts/requirements.txt scripts/requirements-winter-pg.txt backtest/requirements.txt requirements/automation.txt requirements/ci-py311.txt requirements/ci-py312.txt; do
  rg -q -- '--hash=sha256:' "$file"
done

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
    /tmp/venv/bin/python -c "import fastapi, httpx, jsonschema, numpy, piptools"
  '

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13-slim \
  sh -lc '
    set -eu
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py312.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
    cmp "$tmp/ci-py312.txt" requirements/ci-py312.txt
    /tmp/venv/bin/python -c "import fastapi, httpx, jsonschema, numpy, piptools"
  '

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
    /tmp/venv/bin/python -m pip install --require-hashes -r scripts/requirements.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/scripts /tmp/venv/bin/python -c "import feed_lib, jsonschema, numpy, validate_feed"
  '

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
    /tmp/venv/bin/python -m pip install --require-hashes -r backtest/requirements.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/backtest /tmp/venv/bin/python -c "import data, lxml, numpy, pandas, sklearn, statarb, walkforward"
  '

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
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/automation.txt
    /tmp/venv/bin/python -m pip check
    PYTHONPATH=/workspace/backtest:/workspace/scripts /tmp/venv/bin/python -c "import factor_factory, feed_lib, run_routine, study_downshift, study_pbo"
  '

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
    /tmp/venv/bin/python -m pip install --require-hashes -r scripts/requirements-winter-pg.txt
    /tmp/venv/bin/python -m pip check
    /tmp/venv/bin/python -c "import psycopg2"
  '

docker build --pull=false --tag stock-analysis-backend:stage1b backend
test "$(docker image inspect stock-analysis-backend:stage1b --format '{{.Config.User}}')" = "10001:10001"
docker run --rm stock-analysis-backend:stage1b \
  sh -c 'test -z "$(find /app \( -name __pycache__ -o -name "*.py[co]" \) -print -quit)"'
docker run --rm stock-analysis-backend:stage1b \
  python -c 'import app.main; print("backend image import OK")'
```

Expected: the hash loop fails immediately if any lock lacks a hash; every install, dependency import, and source-module import exits 0; `pip check` reports `No broken requirements found.` in all six environments; all six Python 3.11 locks and the Python 3.12 CI lock exactly match fresh header-free temporary outputs from their `.in` files. The backend image builds from the scrubbed context, contains no copied bytecode/cache directories, records user `10001:10001`, and imports the application successfully as that non-root user.

- [ ] **Step 6: Commit declarations, generated locks, and runtime pins**

```bash
git add .python-version backend/.dockerignore backend/requirements.in backend/requirements.txt backend/runtime.txt backend/Dockerfile scripts/requirements.in scripts/requirements.txt scripts/requirements-winter-pg.in scripts/requirements-winter-pg.txt backtest/requirements.in backtest/requirements.txt requirements/automation.in requirements/automation.txt requirements/ci.in requirements/ci-py311.txt requirements/ci-py312.txt
git diff --cached --check
git commit -m "build: lock Python dependencies"
```

---

### Task 4: Prove full schema validation and add the all-PR CI matrix

**Files:**
- Modify: `scripts/tests/test_validate_feed.py`
- Modify: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: Task 2's stable frontend commands and Task 3's Python-version-specific CI locks.
- Produces: a regression test that fails without `jsonschema` and required CI jobs for both frontend profiles and both Python runtimes.

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
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.11.15-slim \
  sh -lc '
    set -eu
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

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13-slim \
  sh -lc '
    set -eu
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py312.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
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

Expected: all seven committed locks byte-match their runtime-specific temporary regenerations; all twenty test invocations exit 0; the feed test prints `完整 JSON Schema 拒绝额外顶层字段` as passed under both runtimes; no test contacts a live market provider. Lock regeneration adds no test invocation and does not alter the Stage 1A six-script contract in either leg.

- [ ] **Step 4: Replace the test workflow with the full matrix**

Replace `.github/workflows/tests.yml` with:

```yaml
name: CI (reproducible baseline)

on:
  push:
    branches: [main]
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
      - uses: actions/setup-node@v6
        with:
          node-version-file: .node-version
          cache: npm
          cache-dependency-path: frontend/package-lock.json
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
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backend.txt" backend/requirements.in
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/scripts.txt" scripts/requirements.in
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/winter-pg.txt" scripts/requirements-winter-pg.in
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/backtest.txt" backtest/requirements.in
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/automation.txt" requirements/automation.in
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py311.txt" requirements/ci.in
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
          python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
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
```

There are deliberately no `paths` filters: every pull request must receive both frontend profile checks and both Python checks, including dependency-only, documentation-adjacent, workflow, and cross-directory changes. The workflow is a merge of the Stage 1A security gate, not a replacement that drops its six regression scripts.

- [ ] **Step 5: Run the local equivalents of every matrix leg**

Run:

Run the exact Node container command from Task 2 Step 6 and both exact Python container commands from Task 4 Step 3.

Expected: both frontend profiles pass, all seven lock comparisons pass, and all twenty Python test invocations pass. `git status --short` shows no tracked build-artifact changes.

- [ ] **Step 6: Commit the validation regression and CI matrix**

```bash
git add scripts/tests/test_validate_feed.py .github/workflows/tests.yml
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
- Modify: `.github/workflows/feed-validate.yml`
- Modify: `.github/workflows/funds-13f.yml`
- Modify: `.github/workflows/hyperliquid-monitor.yml`
- Modify: `.github/workflows/intraday-report.yml`
- Modify: `.github/workflows/market-snapshot.yml`
- Modify: `.github/workflows/monthly-studies.yml`
- Modify: `.github/workflows/openclaw-notes.yml`
- Modify: `.github/workflows/premarket-pack.yml`
- Modify: `render.yaml`
- Modify: `backend/README.md`

**Interfaces:**
- Consumes: `.node-version`, `.python-version`, generated hash locks including `requirements/automation.txt`, and Task 2's static build/smoke commands.
- Produces: Pages, Render, and scheduled automation paths that use the same reproducible entry points already proven by CI.

- [ ] **Step 1: Capture the policy violations before editing workflows**

Run:

```bash
rg -n 'node-version: 20|python-version: "3\.(11|12)"|(^|[[:space:]])pip install -r|rm -rf app/api' .github/workflows render.yaml backend/README.md
```

Expected: matches include `deploy-pages.yml`'s major-only Node pin and `rm -rf app/api`, mixed 3.11/3.12 workflow pins, bare `pip install`, and the backend README's non-hash install.

- [ ] **Step 2: Normalize every scheduled Python setup to the primary version file**

In each of the following workflows:

```text
.github/workflows/alpha-routine.yml
.github/workflows/chan-stats.yml
.github/workflows/daily-digest.yml
.github/workflows/daily-screener.yml
.github/workflows/feed-validate.yml
.github/workflows/funds-13f.yml
.github/workflows/hyperliquid-monitor.yml
.github/workflows/intraday-report.yml
.github/workflows/market-snapshot.yml
.github/workflows/monthly-studies.yml
.github/workflows/openclaw-notes.yml
.github/workflows/premarket-pack.yml
```

replace the literal version field under `actions/setup-python@v6` with:

```yaml
        with:
          python-version-file: .python-version
```

For the isolated `pr-validate` job in `.github/workflows/feed-validate.yml`, the trusted checkout lives below `trusted/`; use `python-version-file: trusted/.python-version` in that job and `.python-version` in its `publish` job. This intentionally moves scheduled production jobs to Python 3.11.15. Python 3.12.13 remains a compatibility-only CI leg in `.github/workflows/tests.yml`.

- [ ] **Step 3: Make every scheduled dependency install hash-checked**

Use these exact commands in the named workflows:

```text
.github/workflows/alpha-routine.yml:
python -m pip install --require-hashes -r requirements/automation.txt
PYTHONPATH=backtest:scripts python -c "import factor_factory, feed_lib, run_routine, statarb"

.github/workflows/feed-validate.yml:
python -m pip install --require-hashes -r trusted/scripts/requirements.txt
python -m pip install --require-hashes -r scripts/requirements.txt

.github/workflows/monthly-studies.yml:
python -m pip install --require-hashes -r requirements/automation.txt
PYTHONPATH=backtest:scripts python -c "import feed_lib, statarb, study_downshift, study_pbo"

.github/workflows/hyperliquid-monitor.yml:
python -m pip install --require-hashes -r scripts/requirements.txt

.github/workflows/chan-stats.yml:
python -m pip install --require-hashes -r backend/requirements.txt

.github/workflows/daily-screener.yml:
python -m pip install --require-hashes -r backend/requirements.txt
```

Workflows with no third-party imports keep no install step; do not add unnecessary packages to them.

- [ ] **Step 4: Replace the Pages workflow with the proven static profile**

Replace `.github/workflows/deploy-pages.yml` with:

```yaml
name: Deploy frontend to GitHub Pages

on:
  push:
    branches: [main]
    paths: ["frontend/**", "feed/schema/**", ".node-version", ".github/workflows/deploy-pages.yml"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v6
        with:
          node-version-file: .node-version
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Bundle latest feed snapshot
        working-directory: ${{ github.workspace }}
        run: |
          snapshot="$RUNNER_TEMP/feed-snapshot"
          rm -rf "$snapshot"
          mkdir -p "$snapshot"
          cp -r feed/index.json feed/health.json feed/watchlist.json feed/schema feed/reports feed/signals feed/market feed/factory feed/screener feed/stock-notes feed/intraday feed/crypto feed/funds "$snapshot/"
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
      - uses: actions/upload-pages-artifact@v5
        with:
          path: frontend/out

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```

The only `rm -rf` left here refreshes a runner-temporary feed snapshot. `build-profile.mjs` overlays that snapshot only inside its private frontend copy. The workflow does not delete or rewrite tracked `frontend/public/feed`, `frontend/app/api`, or any other application source path.

- [ ] **Step 5: Make Render and the backend quick start consume the backend lock**

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
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
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
uvicorn app.main:app --reload --port 8000
```
````

- [ ] **Step 6: Run repository-wide policy and behavior verification**

Run:

```bash
set -e
! rg -n 'node-version: 20|python-version: "3\.(11|12)"|(^|[[:space:]])pip install -r|rm -rf app/api' .github/workflows render.yaml backend/README.md
for file in .github/workflows/deploy-pages.yml .github/workflows/tests.yml; do
  rg -q 'node-version-file: \.node-version' "$file"
done
for file in .github/workflows/alpha-routine.yml .github/workflows/chan-stats.yml .github/workflows/daily-digest.yml .github/workflows/daily-screener.yml .github/workflows/feed-validate.yml .github/workflows/funds-13f.yml .github/workflows/hyperliquid-monitor.yml .github/workflows/intraday-report.yml .github/workflows/market-snapshot.yml .github/workflows/monthly-studies.yml .github/workflows/openclaw-notes.yml .github/workflows/premarket-pack.yml; do
  rg -q 'python-version-file: \.python-version' "$file"
done
rg -n 'python-version-file: trusted/\.python-version' .github/workflows/feed-validate.yml
test "$(rg -c '^[[:space:]]+- key: PYTHON_VERSION$' render.yaml)" -eq 1
rg -U -n -- '- key: PYTHON_VERSION\n[[:space:]]+value: "3\.11\.15"' render.yaml
test "$(rg -c 'python -m pip install --require-hashes -r requirements/automation\.txt' .github/workflows/alpha-routine.yml)" -eq 1
test "$(rg -c 'python -m pip install --require-hashes -r requirements/automation\.txt' .github/workflows/monthly-studies.yml)" -eq 1
test "$(rg -c 'PYTHONPATH=backtest:scripts python -c' .github/workflows/alpha-routine.yml)" -eq 1
test "$(rg -c 'PYTHONPATH=backtest:scripts python -c' .github/workflows/monthly-studies.yml)" -eq 1
```

Then run the exact Node container gate from Task 2 Step 6 and both exact Python container gates from Task 4 Step 3. Finally run:

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

Expected:

- the negative policy scan exits 0 because it finds no prohibited patterns;
- every listed scheduled workflow reads `.python-version`;
- Render declares exactly one adjacent `PYTHON_VERSION: 3.11.15` entry in its Blueprint, independent of the repository-root version file;
- `alpha-routine` and `monthly-studies` each install the combined automation lock and smoke-import their `backtest/` and `scripts/` modules exactly once;
- both frontend profiles pass and the real `app/api` handlers remain present;
- both Python versions reproduce their applicable locks and pass all current tests with no broken requirements;
- API/feed/lock/config inputs remain byte-stable and no private publication residue remains;
- `git diff --check` reports no whitespace errors;
- only intended tracked files plus the pre-existing untracked `AGENTS.md` appear in status.

- [ ] **Step 7: Commit deployment and scheduled-workflow integration**

```bash
git add .github/workflows/deploy-pages.yml .github/workflows/alpha-routine.yml .github/workflows/chan-stats.yml .github/workflows/daily-digest.yml .github/workflows/daily-screener.yml .github/workflows/feed-validate.yml .github/workflows/funds-13f.yml .github/workflows/hyperliquid-monitor.yml .github/workflows/intraday-report.yml .github/workflows/market-snapshot.yml .github/workflows/monthly-studies.yml .github/workflows/openclaw-notes.yml .github/workflows/premarket-pack.yml render.yaml backend/README.md
git diff --cached --check
git commit -m "ci: use pinned toolchains everywhere"
```

---

## Final Acceptance Gate

After all six commits, run the exact Node container gate from Task 2 Step 6 and the following two-runtime Python gates once more from a clean checkout. These are intentionally explicit here so the final run cannot fall back to a root/system Python install:

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

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/home \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD:/workspace" \
  --workdir /workspace \
  python:3.12.13-slim \
  sh -lc '
    set -eu
    python -m venv /tmp/venv
    /tmp/venv/bin/python -m pip install --require-hashes -r requirements/ci-py312.txt
    /tmp/venv/bin/python -m pip check
    tmp="$(mktemp -d)"
    trap "rm -rf \"$tmp\"" EXIT
    /tmp/venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --no-strip-extras --no-header --output-file="$tmp/ci-py312.txt" requirements/ci.in
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

Expected: all commands exit 0; script tests pass before either build; static smoke reports 12 routes; server smoke reports eleven page passes and two API-route passes; all seven lock comparisons and all twenty Python test invocations pass; API/feed/lock/config inputs remain byte-stable; no publication residue or tracked generated artifact is introduced by verification. After this local final gate passes, push the feature branch; require the actual GitHub `Frontend (static)`, `Frontend (server)`, `Python (3.11.15)`, and `Python (3.12.13)` jobs to succeed before merge.
