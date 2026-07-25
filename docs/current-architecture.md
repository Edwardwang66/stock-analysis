# Current Architecture

> **Status:** Current
> **Scope:** Implemented repository architecture before the contract-first refactor.
> **Last verified commit:** `8cff75b8e31d6b3a07a9d6198e0bc54bcb3b594a`

## System boundary

The repository currently combines four implemented systems:

- a Next.js 14 and React 18 UI under `frontend/`;
- an optional FastAPI service under `backend/`;
- repository-backed JSON and Markdown feed artifacts produced by GitHub Actions and local automation;
- Python research, backtesting, screening, and automation under `backtest/` and `scripts/`.

The frontend catalog has eight ordinary market groups—US, CN, HK, CRYPTO, JP, KR, DE, and GB—plus a separate IDX index catalog. Capability depth varies by source and market: the backend has multi-provider chains for some quote paths, single-provider chains for several international markets, and provider-specific limits for OHLCV, search, fundamentals, news, and extended-hours data.

## Current runtime variants

### GitHub Pages static export

`npm run build:static` copies the frontend source tree, excluding `node_modules`, `.next`, and `out`, into a private directory under the system temporary directory. It removes `app/api` only from that temporary copy. When `STATIC_FEED_SOURCE` is configured, the temporary copy's `public/feed` is also removed and replaced from that configured snapshot. The build exports from the temporary tree and publishes its `out` directory back to `frontend/out`; the tracked frontend source and repository `feed/` are not deleted or rewritten by this process.

The Pages workflow assembles a fail-closed feed snapshot from selected repository paths, passes it as `STATIC_FEED_SOURCE`, builds and smoke-tests the static profile, verifies critical exported feed files, and uploads `frontend/out`.

### Vercel Edge-assisted frontend

The repository contains **Implemented** Next route handlers for `GET /api/quote` and `GET /api/ohlcv`, both declared for the Edge runtime. The server build retains these handlers; `frontend/vercel.json` permits a normal Vercel build when frontend files change.

The hard-coded `https://stock-analysis-ten-phi.vercel.app` deployment attempted by default is **External** to the repository. A custom `NEXT_PUBLIC_EDGE_BASE` or a self-owned hosted deployment of the implemented routes is **Optional**. If `NEXT_PUBLIC_EDGE_BASE` is absent and the browser is not already on a same-origin `*.vercel.app` host, an unresolved request that reaches the Edge stage attempts the hard-coded deployment. There is no supported current setting that disables this attempt entirely.

### Frontend with optional FastAPI

Setting `NEXT_PUBLIC_API_BASE` enables browser requests to the optional FastAPI service. The UI can run without it by using Edge, repository feed, browser-safe providers, public CORS proxies, and browser cache. The repository includes a Render blueprint for the backend, but a hosted backend is not required by the static profile.

FastAPI exposes provider routing, response and bar-store caching, search, quotes, OHLCV, and deterministic analysis over HTTP. It is a separate process from Next.js and is not bundled into GitHub Pages.

## Current interactive data paths

Frontend source selection is concentrated in `frontend/lib/datasource.ts`, but the implemented paths still span FastAPI, Next Edge routes, a live-branch quote snapshot, raw repository feed data, direct browser providers, public CORS proxies, in-memory cache, and `localStorage`.

Quote requests use this current sequence:

1. a fresh in-memory quote or a browser-persisted quote still within the market-aware freshness window;
2. optional FastAPI batches for non-IDX symbols;
3. the Edge quote route for unresolved non-crypto symbols;
4. a fresh live-branch snapshot when at least three non-crypto symbols remain unresolved; this set can include IDX symbols;
5. a per-symbol fallback that attempts FastAPI again for unresolved non-IDX symbols;
6. direct browser access to Binance for crypto or Yahoo through the ordered public CORS proxies for other unresolved symbols;
7. only when the per-symbol fetch throws, a persisted quote no older than the bounded ten-minute stale limit.

OHLCV requests use a different sequence:

1. a fresh `localStorage` bar series;
2. the Edge OHLCV route first for every market, including CRYPTO and IDX;
3. optional FastAPI for non-IDX symbols;
4. direct browser access to Binance or Yahoo through the ordered public CORS proxies;
5. only when fetching throws, a persisted bar series no older than the bounded 24-hour stale limit.

A successful fetch that returns an empty bar array is returned as empty; it does not trigger the stale-series exception fallback.

Repository intelligence data has a separate two-source path in `frontend/lib/feed.ts`: raw GitHub `main/feed` is tried first, then the same-origin bundled `public/feed` snapshot. Intraday quotes use the `live` branch separately.

## Frontend pages and responsibilities

| Route | Current responsibility |
|---|---|
| `/` | Multi-market quote board, indexes, watchlists, alert checks, feed freshness, and import/export of local user data. |
| `/symbol` | Quote and OHLCV display, deterministic indicators and signals, Chan/chip/money-flow views, comparisons, alerts, and CSV export. |
| `/desk` | Combined market, overnight, watchlist, event, report, and feed-status workspace. |
| `/intel` | Feed-backed market state, signals, research candidates, reports, fund holdings, and freshness panels. |
| `/screener`, `/tracker`, `/reports` | Scheduled screener results, pick tracking and win-rate views, and Markdown analysis reports. |
| `/portfolio`, `/alerts` | Browser-local simulated holdings and price reminders. |
| `/sources`, `/help` | Data-source health/demos and the product feature map. |

These pages call library modules directly. There is no current application-layer `DataGateway` injected into pages.

## FastAPI routes, providers, cache, and bar store

FastAPI currently exposes:

- `/api/v1/health` and `/api/v1/cache` for process, provider-breaker, cache, and bar-store state;
- `/api/v1/search`, `/api/v1/quotes`, and `/api/v1/ohlcv` for interactive data;
- `/api/v1/analysis`, `/api/v1/moneyflow`, `/api/v1/chips`, and `/api/v1/chan` for deterministic derived calculations.

Provider chains are selected by market. US uses Yahoo with Tencent and Stooq fallbacks; HK and CN use Tencent and Yahoo; CRYPTO uses Binance and OKX; IDX, JP, KR, DE, and GB use Yahoo. The router has per-provider, per-operation circuit breakers, while the store adds single-flight requests, stale-while-revalidate quote behavior, batch refresh, and stale OHLCV fallback.

The optional FastAPI process has two local SQLite facilities. Its JSON cache uses `CACHE_DB` or `/tmp/stock_cache.db` and falls back to process memory when the file cannot be opened. Its OHLCV bar store uses `STORE_DB` or `/tmp/stock_store.db`, incrementally upserts ranges, and is disabled when its database cannot be opened. HTTP GET requests can write both caches. Neither facility is a platform system of record or guaranteed to persist across hosted restarts or instances, and neither is shared with browser `localStorage`.

## Git-backed feed and scheduled producers

The repository `feed/` tree is both a publication artifact and an integration surface. Frontend readers consume JSON and Markdown from the repository, the Pages bundle, and the `live` branch. Scheduled workflows and local scripts produce reports, signals, screeners, market snapshots, fund data, intraday state, research outputs, notes, and health files.

Feed artifacts have multiple writers and uneven schema coverage. `feed/schema/report.schema.json` is an implemented schema used by `feed_lib` and `validate_feed` for report payloads, while many other artifact families use handwritten TypeScript interfaces, producer conventions, or validation specific to a workflow.

The current `FEED_PUBLICATION_MANIFEST` is only the Stage 1A workflow-local Git-staging allowlist. Producer helpers update that temporary manifest with an atomic file replacement, and `scripts/feed_publication.py stage` stages only its recorded paths. Several other workflows still stage explicit feed files directly. This manifest is not a reader-facing snapshot, does not describe artifact completeness or cross-artifact exposure, provides no previous-complete rollback contract, and is not fetched by the frontend.

The current `publish_report` path validates its report, writes the report and any derived files directly, then rebuilds and writes `index.json`. That ordering applies only to this publisher path; the individual file writes are not atomic replacements, and there is no cross-file transaction or complete multi-writer snapshot protocol.

A reader-facing atomic snapshot manifest written last, completeness validation across the snapshot, and fallback to the previous complete snapshot are **Planned**. They are not current behavior.

## Research and backtest subsystem

`backtest/` contains multiple research programs rather than one service: factor and cross-sectional studies, walk-forward and PBO validation, statistical-arbitrage experiments, crypto pipelines, point-in-time membership work, and checked-in result artifacts. Individual scripts download or reuse market-data caches and expose separate command-line entry points.

`scripts/` contains scheduled producers and operational CLIs for screening, routine reports, feed validation and ingress, OpenClaw notes, market and intraday snapshots, Hyperliquid monitoring, fund holdings, feed audit, and Chan statistics. Some backtests publish reports into `feed/`, and workflows commit selected outputs.

Reusable Python boundaries are not packaged consistently. Several scripts and studies modify `sys.path` to import sibling code from `scripts/` or `backtest/`.

## State and persistence

The browser persists quote and bar caches, watchlists, alerts, simulated holdings, language/timezone, and selected UI preferences in `localStorage`; this state is local to a browser profile and is not synchronized by the product.

FastAPI uses the two local SQLite facilities for response cache and OHLCV bars when they are available. Repository feed files and Git history persist automation output. PostgreSQL is an independent optional Winter projection and local analysis warehouse under `scripts/winter_pg/`, enabled through `WINTER_PG_DSN` and a separate dependency lock; it is not FastAPI persistence, a base frontend or backend requirement, or a current TimescaleDB dependency.

## Current trust boundaries

The static browser crosses directly to public providers, CORS proxies, the external or self-hosted Edge endpoint, raw GitHub content, and an optional FastAPI deployment. Both implemented Next Edge handlers allow any origin and have no authentication boundary. `frontend/lib/feed.ts` accepts the first successful raw or bundled feed response; there is no reader-facing signed snapshot manifest.

FastAPI accepts cross-origin GET requests from any origin and calls provider endpoints with server-side networking. It has request validation, provider failure handling, and caches, but no user authentication or application rate-limiting boundary in the current route set. Provider licensing metadata is descriptive and is not enforced as a routing gate.

External OpenClaw report ingress is constrained by schema, identifier/path validation, and HMAC verification when signature enforcement is enabled. GitHub Actions jobs that publish use scoped repository credentials; Stage 1A-enabled writers stage a recorded allowlist, while legacy explicit-file writers remain separate publication paths.

## Known duplication and semantic drift

- Deterministic indicators, signals, and Chan logic exist in frontend TypeScript and backend Python; `scripts/chan_engine.py` contains another Python implementation for scheduled statistics.
- Symbol models, provider mapping, cache/freshness rules, and result shapes are handwritten in more than one language.
- Quote and OHLCV requests use different source priorities, and feed reads use another path.
- Feed ownership is distributed across workflows and scripts, with one report schema but no complete artifact contract set.
- Research and automation share modules through mutable import paths rather than a stable Python package.

Comments in several implementations describe intended parity, but there is no current single generated contract or parity gate that makes one implementation authoritative.

## Current limitations

- There is no implemented `DataGateway`, generated cross-language model pipeline, `analysis-core`, `stock_core`, or reader-facing atomic feed manifest.
- The default Edge attempt is hidden behind a hard-coded external URL and cannot be explicitly disabled.
- Static operation depends on browser-reachable external services and can degrade differently from FastAPI.
- SQLite defaults under `/tmp` can be cold or ephemeral after a hosted process restart.
- Feed consumers cannot prove that multiple files belong to one complete publication snapshot.
- Market presence in the catalog does not imply equal quote, OHLCV, search, fundamentals, news, or extended-hours coverage.

## Target architecture

The accepted target is summarized in [`rfcs/target-architecture.md`](rfcs/target-architecture.md). It is a migration design, not current implementation guidance. The complete accepted program design is [`superpowers/specs/2026-07-16-stock-analysis-refactor-design.md`](superpowers/specs/2026-07-16-stock-analysis-refactor-design.md).
