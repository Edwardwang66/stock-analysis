# Configuration

> **Status:** Current
> **Scope:** User-settable, secret, and platform-provided configuration used by current code and workflows.
> **Last verified commit:** `e74ad00c026b410db9a1438e46c26c09dad32bd8`

## Configuration rules

Configuration belongs to one of three groups:

- user-facing deployment and runtime settings, such as public frontend bases and backend cache paths;
- repository Variables and Secrets mapped explicitly into GitHub Actions jobs;
- internal execution contracts supplied by build scripts, containers, GitHub Actions, or Render.

Only `NEXT_PUBLIC_*` values are embedded in browser bundles. They must never contain credentials. An endpoint being configured enables an adapter; it does not make that adapter authoritative for every request or prove that the endpoint is healthy.

The FastAPI clients concatenate `API_BASE` or `NEXT_PUBLIC_API_BASE` literally with `/api/v1/...`. Until client normalization is implemented, both values must omit a trailing slash. The Edge selector removes exactly one trailing slash before adding route paths.

## Frontend build-time variables

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `NEXT_PUBLIC_BASE_PATH` | Frontend deployer | Optional | Empty string | No | Next configuration, layout assets, feed fallback, static smoke test |
| `NEXT_PUBLIC_SITE_URL` | Frontend deployer | Required in CI, GitHub Actions, and Vercel builds; optional locally | `VERCEL_PROJECT_PRODUCTION_URL`, then `VERCEL_URL`, then local `http://localhost:3000` fallback | No | Absolute metadata, canonical URLs, and Open Graph share images |
| `NEXT_PUBLIC_API_BASE` | Frontend deployer | Optional | Unset; FastAPI adapter disabled | No | `frontend/lib/datasource.ts`, `frontend/lib/search.ts` |
| `NEXT_PUBLIC_EDGE_BASE` | Frontend deployer | Optional | Same origin on a browser `*.vercel.app` host; otherwise the hard-coded hosted deployment | No | `frontend/lib/datasource.ts` Edge quote and OHLCV stage |
| `NEXT_PUBLIC_FEED_BASE` | Frontend deployer | Optional | Raw GitHub `main/feed` URL for this repository | No | `frontend/lib/feed.ts` |

When nonempty, `NEXT_PUBLIC_BASE_PATH` must begin with `/` and must not end with `/`. `NEXT_PUBLIC_SITE_URL` is the complete public application root: it must be an absolute HTTP(S) URL whose pathname matches `NEXT_PUBLIC_BASE_PATH`, including the repository path and trailing slash when applicable. Explicit `NEXT_PUBLIC_SITE_URL` configuration wins, followed by `VERCEL_PROJECT_PRODUCTION_URL`, then `VERCEL_URL`, then the local fallback. CI, GitHub Actions, and Vercel builds fail without a non-local public root. `NEXT_PUBLIC_API_BASE` must omit a trailing slash. An unset value skips browser calls to FastAPI. `NEXT_PUBLIC_FEED_BASE` changes the raw-feed origin. Most artifact readers retry a failed raw request for the same relative path from the same-origin bundled feed; live intraday is remote-only and has no bundled fallback.

An unset `NEXT_PUBLIC_EDGE_BASE` does not disable Edge requests. When the browser is not already on a same-origin Vercel host, any request that reaches the Edge stage still attempts `https://stock-analysis-ten-phi.vercel.app`. No supported current setting disables that attempt entirely.

## Backend cache and storage variables

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `CACHE_DB` | FastAPI operator | Optional | `/tmp/stock_cache.db` | No | `backend/app/cache.py` |
| `STORE_DB` | FastAPI operator | Optional | `/tmp/stock_store.db` | No | `backend/app/barstore.py` |
| `CACHE_STALE_GRACE` | FastAPI operator | Optional | `86400` seconds | No | JSON cache stale retention |
| `CACHE_MAX_ENTRIES` | FastAPI operator | Optional | `20000` | No | JSON cache cleanup |

If `CACHE_DB` cannot be opened, the response cache falls back to process memory. If `STORE_DB` cannot be opened, the bar store is disabled. Defaults under `/tmp` are local and may be ephemeral on hosted instances.

## GitHub repository Variables

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `API_BASE` | Repository administrator | Optional | Unset | No | Pages build mapping, backend health and keep-warm workflow calls |
| `EDGE_BASE` | Repository administrator | Optional | Unset | No | Pages build mapping to `NEXT_PUBLIC_EDGE_BASE` |

`API_BASE` must omit a trailing slash because current workflow and frontend clients append `/api/v1/...` literally. An unset `API_BASE` skips workflow health calls and leaves the Pages frontend without FastAPI. An unset `EDGE_BASE` leaves `NEXT_PUBLIC_EDGE_BASE` empty, after which the current browser Edge selector can still choose same-origin Vercel or the hard-coded hosted deployment.

## Feed and OpenClaw secrets and options

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `FEED_HMAC_SECRET` | Repository and OpenClaw operators | Required for external report ingress; otherwise optional | Unset | Yes | Report signing, ingress, validation, participating feed writers |
| `GITHUB_TOKEN` | GitHub Actions or OpenClaw operator | Required for selected remote write modes | Workflow token or unset locally | Yes | OpenClaw client, daily digest, workflow API calls |
| `GH_TOKEN` | GitHub Actions | Required by workflow `gh` CLI steps that map it | Explicitly mapped workflow token | Yes | Screener, watchdog, intraday, and related `gh` commands |
| `GITHUB_REPOSITORY` | GitHub Actions | Platform-provided | Current `owner/repository` | No | Repository-scoped scripts and workflow commands |
| `GITHUB_RUN_URL` | Workflow or local operator | Optional | Consumer-specific empty/local value | No | Report provenance |
| `OPENCLAW_MODEL` | OpenClaw operator | Optional | `OpenClaw` in scripts; workflows may set a fixed label | No | Report and stock-note producer metadata |
| `OPENCLAW_RUN_URL` | OpenClaw operator | Optional | Empty in `openclaw_client.py`; `local-openclaw-daily` in `openclaw_daily.py` | No | Producer provenance |
| `OPENCLAW_BRANCH` | OpenClaw operator | Optional | Consumer-specific: stock-note Contents writes use `main`; report Contents writes use `openclaw-inbox`; dispatch ignores it | No | GitHub Contents API modes |
| `OPENCLAW_REPO` | OpenClaw operator | Optional | `edwardwang66/stock-analysis` | No | Remote OpenClaw submission target |
| `OPENCLAW_TOKEN` | OpenClaw operator | Required for non-local modes when `GITHUB_TOKEN` is absent | Unset | Yes | GitHub API authentication fallback |
| `OPENCLAW_WATCHLIST` | OpenClaw operator | Optional | Unset | No | Legacy symbols that supplement the primary `feed/watchlist.json` selection |
| `OPENCLAW_THROTTLE` | OpenClaw operator | Optional | `0` seconds in the script; scheduled workflow dispatch defaults to `1.0` | No | Per-symbol delay in `openclaw_daily.py` |

GitHub does not automatically inject `GITHUB_RUN_URL`; current workflows compose it from GitHub context before passing it to producers. `GITHUB_TOKEN` and `GH_TOKEN` are explicitly mapped into workflow environments rather than treated as ordinary repository Variables.

`FEED_HMAC_SECRET` is fail-closed for external `openclaw` and `manual` report ingress: a missing or invalid signature is rejected. The separate stock-note local and Contents API modes are privileged direct-write paths and must receive only trusted operator input; they do not currently provide equivalent path containment, schema, or HMAC validation.

## Intraday and Winter options

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `INTRADAY_OUT` | Intraday producer | Optional | Repository `feed/intraday/latest.json`; workflows override to a live checkout | No | `scripts/intraday_report.py`, Winter loop |
| `INTRADAY_PRODUCER` | Intraday producer | Optional | `winter-loop` | No | Intraday artifact provenance |
| `WINTER_PG_DSN` | Winter operator | Required by direct Winter PostgreSQL tools; optional for OpenClaw daily archive | Unset | Yes | Winter ingest, event heat, win-rate, OpenClaw daily archive |
| `WINTER_INTRADAY_LATEST` | Winter operator | Optional | Repository `feed/intraday/latest.json` | No | Winter PostgreSQL ingest |
| `PORT` | Render or container operator | Platform-provided when hosted; optional in the Docker image | Docker uses `8000`; Render and Procfile rely on injected `$PORT` | No | Uvicorn bind port |

`WINTER_PG_DSN` enables an independent optional projection; it is not FastAPI storage. Some direct tools can read a local Winter configuration when the environment name is absent. An explicitly empty process value disables the OpenClaw daily PostgreSQL archive rather than falling through to a local configuration file.

## Platform-provided variables

These names are internal execution contracts, not settings most users should export.

| Name | Owner | Requirement | Default | Secret | Consumers |
|---|---|---|---|---|---|
| `CI` | CI platform | Platform-provided deployment flag | Deployment mode only when exactly `true` | No | Public-site URL resolver |
| `GITHUB_ACTIONS` | GitHub Actions | Platform-provided deployment flag | Deployment mode only when exactly `true` | No | Public-site URL resolver |
| `VERCEL` | Vercel | Platform-provided deployment flag | Deployment mode only when exactly `1` | No | Public-site URL resolver |
| `VERCEL_PROJECT_PRODUCTION_URL` | Vercel | Platform-provided | Stable production hostname, without a scheme | No | Public-site URL resolver fallback after `NEXT_PUBLIC_SITE_URL` |
| `VERCEL_URL` | Vercel | Platform-provided | Current deployment hostname, without a scheme | No | Public-site URL resolver fallback after `VERCEL_PROJECT_PRODUCTION_URL` |
| `NEXT_BUILD_PROFILE` | Frontend build scripts | Internal, optional | `server` | No | Next configuration and profile builder |
| `STATIC_FEED_SOURCE` | Pages build workflow | Internal, optional | Unset | No | Temporary static-profile feed snapshot replacement |
| `SMOKE_PORT` | Server smoke test | Internal, optional | Unset selects an ephemeral port; explicit `0` is rejected | No | `frontend/scripts/smoke-server.mjs` |
| `NEXT_TELEMETRY_DISABLED` | Build workflow | Internal, optional | Repository build wrapper sets `1` | No | Child Next build |
| `NODE_ENV` | Node and Next tooling | Internal, tool-provided | Tool-dependent | No | Next build and runtime |
| `AUTOMERGE_ELIGIBLE_LABEL` | Dependabot workflow | Internal, fixed | `dependencies:auto-merge-eligible` | No | Hardened eligibility label path |
| `AUTOMERGE_ATTESTATION_CONTEXT` | Dependabot workflow | Internal, fixed | `dependabot/auto-merge-eligible` | No | Hardened attestation status path |
| `GITHUB_OUTPUT` | GitHub Actions runner | Platform-provided | Per-step command file | No | Step outputs |
| `GITHUB_WORKSPACE` | GitHub Actions runner | Platform-provided | Checked-out workspace path | No | Workflow scripts and live checkout handling |
| `RUNNER_TEMP` | GitHub Actions runner | Platform-provided | Runner temporary directory | No | Snapshot, report, and temporary index paths |
| `HOME` | User, container, or runner | Platform-provided | Environment-specific home directory | No | Python and Node tooling plus Winter/OpenClaw config and cache paths |
| `FEED_PUBLICATION_MANIFEST` | Participating feed workflows | Internal, optional | Unset; participating workflows set a runner-temporary JSON path | No | Workflow-local path ledger and staging allowlist |
| `PAYLOAD` | Feed dispatch workflow | Internal, event-derived | Missing payload is rejected | No; untrusted event content | `scripts/feed_ingress.py` |
| `REPO` | Dependabot workflow | Internal, context-derived | Current repository | No | Merge-gate API calls |
| `PR_NUMBER` | Dependabot workflow | Internal, event-derived | Current pull request or sweep item | No | Merge gate |
| `REPORT` | Feed watchdog | Internal, step-derived | Multiline audit output | No | Issue body and diagnostic output |
| `HEAD_SHA` | Dependabot workflow | Internal, event-derived | Attested pull-request head | No | Hardened attestation and merge path |
| `FRONTEND_RESULT` | Test workflow | Internal, needs-derived | Frontend matrix result | No | Aggregate test gate |
| `PYTHON_RESULT` | Test workflow | Internal, needs-derived | Python matrix result | No | Aggregate test gate |
| `PACKAGE_ECOSYSTEM` | Dependabot workflow | Internal, metadata-derived | Current dependency ecosystem | No | Eligibility policy |
| `UPDATE_TYPE` | Dependabot workflow | Internal, metadata-derived | Current semantic update type | No | Eligibility policy |
| `PYTHONDONTWRITEBYTECODE` | Python containers and workflows | Internal, optional | Repository gates set `1` | No | Controlled Python runs |
| `PYTHONUNBUFFERED` | Backend container | Internal, optional | Docker image sets `1` | No | Uvicorn container logs |
| `PIP_DISABLE_PIP_VERSION_CHECK` | Python dependency gates | Internal, optional | Repository gates set `1` | No | Deterministic pip runs |
| `PYTHONPATH` | Python workflows | Internal, optional | Workflow-selected repository paths | No | Script and test imports |
| `PYTHON_VERSION` | Render | Internal, pinned | `3.11.15` | No | Render Python runtime |
| `EXPECTED_UID` | `scripts/run-python311` | Internal, required in its container check | Host UID | No | Mounted-worktree UID assertion |
| `EXPECTED_GID` | `scripts/run-python311` | Internal, required in its container check | Host GID | No | Mounted-worktree GID assertion |

`EXPECTED_UID` and `EXPECTED_GID` are tracked consumers of `scripts/run-python311`. The controlled Node/Python acceptance gates use the same host-identity concept, but those plan commands are not additional tracked runtime or workflow consumers.

## Defaults and fallback behavior

- No `NEXT_PUBLIC_API_BASE`: FastAPI quote, OHLCV, search, and health calls are skipped.
- No `NEXT_PUBLIC_EDGE_BASE`: same-origin Vercel is selected when applicable; otherwise the hard-coded external deployment remains the Edge attempt.
- No `NEXT_PUBLIC_FEED_BASE`: feed artifacts are requested from raw GitHub `main/feed`, then most artifact readers retry the same relative path from the bundled snapshot.
- No `FEED_HMAC_SECRET`: local trusted routine producers can emit unsigned reports, but external report validation fails closed.
- `WINTER_PG_DSN` is consumer-specific: an explicitly empty value makes OpenClaw daily skip its optional archive; direct Winter tools require a DSN from the environment or their supported local-file fallback and otherwise stop.
- No usable cache database: FastAPI degrades to process memory; no usable bar-store database disables the bar store.

Endpoint fallback is adapter-specific. Configuring FastAPI does not force all requests through it: quote and OHLCV chains retain Edge, live-feed, browser-provider, proxy, and bounded stale-cache behavior documented in the [deployment matrix](deployment-matrix.md).

## Local examples

Frontend with local FastAPI:

```bash
cd frontend
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run dev
```

Backend with explicit local databases:

```bash
cd backend
CACHE_DB=/tmp/stock-cache-dev.db STORE_DB=/tmp/stock-store-dev.db \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Static profile with a prepared feed snapshot:

```bash
cd frontend
NEXT_PUBLIC_BASE_PATH=/stock-analysis \
NEXT_PUBLIC_SITE_URL=https://edwardwang66.github.io/stock-analysis/ \
STATIC_FEED_SOURCE=/absolute/path/to/feed-snapshot \
  npm run build:static
```

Do not put real tokens, HMAC secrets, or database credentials in shell history, committed files, browser-visible variables, examples, or issue bodies.

## Secret handling

- Store `FEED_HMAC_SECRET` and workflow credentials in GitHub Secrets or an equivalent secret manager.
- Treat `WINTER_PG_DSN` as a secret because it can contain database credentials.
- Give OpenClaw tokens only the repository permissions required by the selected mode.
- Never use a secret in a `NEXT_PUBLIC_*` variable; those values are shipped to browsers.
- Do not print secret values during health checks or operational diagnosis.

The implemented Edge and FastAPI HTTP routes have no application authentication boundary. A secret used for feed ingress does not authenticate quote, OHLCV, search, analysis, or health routes.

## Verification

Use the pinned repository checker after changing configuration use or documentation:

```bash
scripts/run-python311 python scripts/check_docs.py
```

For build-profile behavior, run:

```bash
cd frontend
npm run test:scripts
npm run build:static
npm run smoke:static
npm run build:server
npm run smoke:server
```

Repository discovery and this inventory must change together. The documentation gate compares discovered environment names with this maintained authority and treats the configured platform-provided names separately.
