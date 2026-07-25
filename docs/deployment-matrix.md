# Deployment Matrix

> **Status:** Current
> **Scope:** Supported current deployment variants, commands, dependencies, and limitations.
> **Last verified commit:** `a8d3d4c1a0ae707fca6c500f4de61a4bad0a8726`

## Profile model

The repository has two primary frontend build profiles. They share the current UI, but they do not yet have proven semantic parity across sources, failures, or markets. Semantic parity is a Stage 2 acceptance target.

| Dimension | Static profile | Server profile |
|---|---|---|
| Build command | `npm run build:static` | `npm run build:server` |
| Output/runtime | Exported files in `frontend/out` | Next.js server output |
| Next route handlers | Removed only from the temporary build copy | Retained, including quote and OHLCV Edge handlers |
| Repository feed | Selected snapshot can replace the temporary copy through `STATIC_FEED_SOURCE` | Tracked `frontend/public/feed` unless a separate build step replaces it |
| Optional FastAPI | Supported through `NEXT_PUBLIC_API_BASE` | Supported through `NEXT_PUBLIC_API_BASE` |
| Browser provider fallbacks | Present | Present |
| Deployment examples | GitHub Pages | Next/Vercel plus optional separately hosted FastAPI |
| Authentication | No application auth in the exported UI; external sources have their own boundaries | Implemented Edge and FastAPI routes currently have no application auth |

A static build can use FastAPI, and a server build does not guarantee FastAPI. The build profile selects Next.js output behavior; it does not select one exclusive data plane.

## Static profile

### Local development

`npm run dev` starts the Next development server. It is not a static-file server and does not serve `frontend/out`. The repository currently has no dedicated local command for serving the exported directory.

Validate static behavior by building and inspecting the export:

```bash
cd frontend
npm ci
npm run build:static
npm run smoke:static
```

`smoke:static` checks the exported UI routes, 404 page, and base-path assets directly. The Pages workflow performs separate critical feed-file checks. Neither check makes hosted external services healthy.

### GitHub Pages

`.github/workflows/deploy-pages.yml` creates a temporary fail-closed feed snapshot, maps repository Variables into public build variables, runs the static build and smoke test, verifies critical exported feed files, uploads `frontend/out`, and deploys through GitHub Pages.

The build-profile script copies the frontend into a private temporary directory, removes `app/api` only there, optionally replaces that copy's `public/feed`, and transactionally replaces local `frontend/out` after a successful build. It does not delete tracked route sources or repository `feed/`.

Pages is a generated snapshot plus browser-side data adapters. Feed-only generated commits do not automatically trigger a Pages rebuild except for the workflow's configured paths.

### Optional Edge adapter

The static UI can call a custom `NEXT_PUBLIC_EDGE_BASE`, a same-origin Vercel deployment when running there, or the hard-coded hosted endpoint selected by current code. The exported Pages site has no local Next route handlers.

The custom Edge base has exactly one trailing slash removed before paths are appended. No supported current configuration disables the hard-coded attempt entirely.

## Server profile

### Local Next.js and FastAPI

The two processes are independent:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run dev
```

The FastAPI base must omit a trailing slash. The Next development/server process retains the implemented `/api/quote` and `/api/ohlcv` Edge-compatible route handlers, while FastAPI exposes `/api/v1/...` separately.

After a server build, start production Next with:

```bash
cd frontend
npm run build:server
npm run start
```

### Hosted frontend and hosted FastAPI

`render.yaml` is the tracked FastAPI deployment contract: `backend` is the root directory, dependencies install with hashes, Uvicorn binds to the platform-provided `PORT`, and `/api/v1/health` is the health path. The deploy/runtime Python contract is 3.11.15; Python 3.12.13 is CI compatibility coverage only.

The generic backend Dockerfile and Procfile are building blocks that could be used by other hosts. There is no tracked Railway-specific or Fly-specific application configuration and no live Railway or Fly deployment was verified. Treat them as repository-file-based options, not active deployments.

FastAPI and both implemented Next Edge routes permit cross-origin requests and have no current user authentication or application rate limiting. Operators must not infer a private trust boundary from hosting them.

## Vercel Edge-assisted variant

Three facts have different ownership:

| Classification | Fact | Operational meaning |
|---|---|---|
| **Implemented** | Repository route code for Next `GET /api/quote` and `GET /api/ohlcv` | A server build can deploy these handlers |
| **External** | The hard-coded `https://stock-analysis-ten-phi.vercel.app` endpoint attempted by default | Availability and deployed revision are external state, not guaranteed by this checkout |
| **Optional** | A custom `NEXT_PUBLIC_EDGE_BASE` or a self-owned deployment | Operators can select an owned Edge endpoint |

An HTTP response from the hard-coded alias proves only reachability. It does not prove that the deployed revision matches this repository baseline, uses the pinned Node runtime, or has data semantics equal to FastAPI.

## Capability and degradation matrix

| Capability | Static profile | Server profile |
|---|---|---|
| Common UI | Present today | Present today |
| Semantic parity | Stage 2 target, not accepted today | Stage 2 target, not accepted today |
| Next quote/OHLCV handlers | Not present in exported files | Implemented |
| Optional FastAPI | Browser calls when configured | Browser calls when configured |
| Raw then bundled feed | Present for most feed artifacts | Present for most feed artifacts |
| Live intraday feed | Remote `live` branch only | Remote `live` branch only |
| Browser providers and proxies | Used as fallbacks | Used as fallbacks |
| Local browser caches | Quote and OHLCV caches | Quote and OHLCV caches |
| Degradation | Can continue without FastAPI using Edge, feed, providers, proxies, and bounded caches | Can continue without FastAPI; retained Next handlers add an owned route option |

Configured FastAPI does not imply that every request actually uses FastAPI.

Quote requests use this exact current sequence:

1. a fresh in-memory quote or browser-persisted quote within its market-aware freshness window;
2. optional FastAPI batches for non-IDX symbols;
3. the Edge quote route for unresolved non-crypto symbols;
4. a fresh live-branch snapshot only when at least three non-crypto symbols remain unresolved; that unresolved set can include IDX symbols;
5. a per-symbol FastAPI attempt for unresolved non-IDX symbols;
6. direct Binance for crypto or Yahoo through the ordered public CORS proxies for other unresolved symbols;
7. only when the per-symbol fetch throws, a persisted quote no older than ten minutes.

OHLCV requests use a distinct sequence:

1. a fresh `localStorage` bar series;
2. the Edge OHLCV route first for every market, including CRYPTO and IDX;
3. optional FastAPI for non-IDX symbols;
4. direct Binance or Yahoo through the ordered public CORS proxies;
5. only when fetching throws, a persisted bar series no older than 24 hours.

A successful OHLCV fetch that returns an empty array remains empty; it does not trigger the stale-series exception fallback.

## Build and smoke-test commands

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
```

`npm run build` aliases the server build. The repository pins Node 20.20.2 and npm 10.8.2. `smoke:server` checks the Next UI and expected error behavior of its route handlers; it does not start or validate FastAPI.

## Configuration matrix

| Configuration | Static profile | Server profile |
|---|---|---|
| `NEXT_BUILD_PROFILE` | Build wrapper sets `static` | Defaults or sets `server` |
| `NEXT_PUBLIC_BASE_PATH` | Required for a non-root Pages path | Usually empty; may be nonempty if host routing requires it |
| `STATIC_FEED_SOURCE` | Optional local input; Pages supplies a temporary snapshot | Not used by the normal server build |
| `NEXT_PUBLIC_API_BASE` | Optional and must omit trailing slash | Optional and must omit trailing slash |
| `NEXT_PUBLIC_EDGE_BASE` | Optional; unset still permits hard-coded attempt | Optional; same-origin Vercel can be selected |
| `NEXT_PUBLIC_FEED_BASE` | Optional raw-feed origin | Optional raw-feed origin |
| `PORT` | Not used by exported files | Render/backend runtime port; Next host has its own runtime configuration |

See [Configuration](configuration.md) for ownership, secrecy, defaults, and all internal execution names.

## Health checks

| Surface | Current repository check | What it proves |
|---|---|---|
| FastAPI | `GET /api/v1/health` | That the selected FastAPI process answered its implemented health route |
| Static export | `npm run smoke:static` | Expected exported UI routes, 404 page, and base-path assets exist |
| Next server | `npm run smoke:server` | UI routes answer and route handlers return expected validation errors |
| GitHub Pages | Pages workflow build, smoke, artifact, and deployment jobs | That a particular workflow run deployed its artifact |
| Vercel | Route-specific request plus provider deployment inspection | Reachability and the inspected deployment revision |

There is no generic repository-defined `/health` endpoint for GitHub Pages or Vercel. Do not use `smoke:server` as evidence that FastAPI is healthy.

For local FastAPI:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
```

For an environment value, normalize it before a manual diagnostic, then separately test the literal client construction:

```bash
curl -fsS "${API_BASE%/}/api/v1/health"
curl -sS -o /dev/null -w '%{http_code}\n' "${API_BASE}/api/v1/health"
```

The second command intentionally reproduces current literal concatenation when `API_BASE` ends in `/`.

## External-state observation (dated; not a repository contract)

The following observations were collected on **2026-07-24**. They are observational, drift-prone external state and must be refreshed before making a deployment decision:

- The GitHub `API_BASE` Variable pointed to the Render service and included a trailing slash. No `EDGE_BASE` Variable was configured. The value itself is intentionally not reproduced here.
- The canonical single-slash Render `/api/v1/health` route returned HTTP 200. The double-slash URL produced by current literal `API_BASE + "/api/v1/..."` construction returned HTTP 404. The configured FastAPI integration therefore must not be called healthy until the Variable loses its trailing slash or clients normalize it.
- GitHub Pages and the hard-coded Vercel alias returned successfully.
- The latest successful Pages deployment and the latest READY production deployment bound to the hard-coded alias represented commits from 2026-06-11 rather than Stage 1B. A newer READY Vercel preview existed, but the hard-coded alias did not serve it.
- The Vercel project setting reported Node 24.x, while the repository contract is Node 20.20.2.

Before relying on these hosted paths for a new production deployment, resolve both the `API_BASE` trailing-slash mismatch and the Vercel runtime mismatch, then verify the deployed commit.

Refresh references:

- [GitHub Pages workflow history](https://github.com/edwardwang66/stock-analysis/actions/workflows/deploy-pages.yml)
- [GitHub Pages deployment records](https://github.com/edwardwang66/stock-analysis/deployments/github-pages)
- [Hard-coded Vercel alias](https://stock-analysis-ten-phi.vercel.app)

Refresh provider state without printing secret values:

```bash
gh variable list --repo edwardwang66/stock-analysis
gh run list --repo edwardwang66/stock-analysis --workflow deploy-pages.yml --limit 10
vercel project inspect stock-analysis
vercel inspect https://stock-analysis-ten-phi.vercel.app
```

## Rollback

- Frontend or backend code: create a reviewed revert or corrective commit and redeploy that commit.
- Pages: rerun or deploy a known-good commit through the Pages workflow after checking its feed snapshot.
- Vercel or Render: use the provider's deployment history only after confirming revision and runtime settings; the repository does not automate hosted rollback.
- Feed: publish a forward corrective or revert commit. Do not force-push shared feed history.

The local static builder's transactional replacement of `frontend/out` protects local publication from a partial build. It is not a hosted rollback mechanism.

## Current gaps before semantic parity

- Static and server source selection can produce different results or failure timing; Stage 2 must define and test parity.
- The hard-coded external Edge attempt is not explicitly configurable off.
- FastAPI bases are not normalized before `/api/v1/...` concatenation.
- The raw and bundled feed paths can expose artifacts from different generations.
- Neither Edge nor FastAPI has application authentication or rate limiting.
- Hosted commit and runtime alignment remain external-state checks.
- Market catalog presence does not imply equal quote, OHLCV, search, fundamentals, news, or extended-hours coverage.
