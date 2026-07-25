# FastAPI Market Data Service

> **Status:** Current
> **Scope:** Optional server-profile market-data, cache, OHLCV, and compatibility-analysis service.
> **Last verified commit:** `1f810ef043610ace8025a7ca95ffca0af88816bf`

## Role and optionality

FastAPI is an optional data path for both frontend build profiles. The static application can run without it through Edge, feed, and browser-provider fallbacks; retaining Next.js route handlers in the server profile also does not make FastAPI mandatory. Set `NEXT_PUBLIC_API_BASE` only when an operator owns a reachable deployment, and omit its trailing slash.

The service exposes market data plus deterministic Python calculations. The frontend still has separate TypeScript indicator, signal, Chan, chip, and money-flow implementations, while scheduled Chan statistics use another Python implementation. These are compatibility endpoints, not one proven-identical analysis core; duplication remains until the Stage 3 authority migration.

SEC EDGAR fundamentals are a separate frontend-side path in `frontend/lib/fundamentals.ts`. That path is US-only, can miss ADRs and other issuers without usable SEC XBRL data, and is not a FastAPI route.

## Requirements and installation

Python `3.11.15` is the primary local, container, CI, and Render runtime. Python `3.12.13` is compatibility coverage, not the deployment target. `requirements.in` is the editable direct-dependency source; the committed `requirements.txt` is the hash-locked direct-service install contract.

From `backend/`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --require-hashes -r requirements.txt
```

Stop if `python --version` is not exactly `Python 3.11.15`. CI compatibility uses the repository lock for Python `3.12.13`; do not regenerate or loosen either lock during installation. The repository-wide lock reproduction and runtime commands are the [controlled Python gates](../docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md#controlled-stage-1b-acceptance-gates).

## Run locally

From `backend/`, after installing the locked environment:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The interactive OpenAPI UI is at `/docs`. For a frontend process, set `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`; this enables the adapter but does not force every quote or OHLCV request through FastAPI.

## 运行

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Test locally

Run the two offline backend entry points from `backend/` with the locked Python environment:

```bash
python tests/test_backend.py
python tests/test_api.py
```

The first covers cache, bar-store, provider fallback, circuit breaker, batch, and single-flight behavior. The second uses fake providers to exercise the HTTP routes; neither is a live-provider health check. Use the controlled Python `3.11.15` and `3.12.13` gates for the repository acceptance matrix.

## Configuration

| Name | Default | Current behavior |
|---|---|---|
| `CACHE_DB` | `/tmp/stock_cache.db` | JSON response-cache SQLite path; open failure falls back to process memory. |
| `STORE_DB` | `/tmp/stock_store.db` | OHLCV SQLite path; open failure disables the bar store. |
| `CACHE_STALE_GRACE` | `86400` seconds | Retains expired JSON entries for bounded stale reads. |
| `CACHE_MAX_ENTRIES` | `20000` | JSON-cache cleanup ceiling. |
| `PORT` | Docker default `8000` | Uvicorn bind port in container/Procfile/Render contracts. |
| `NEXT_PUBLIC_API_BASE` | Unset | Frontend-owned public base URL; it must omit a trailing slash. |

See [Configuration](../docs/configuration.md) for ownership and [Deployment Matrix](../docs/deployment-matrix.md) for frontend source selection. These variables do not add authentication, shared persistence, or provider entitlements.

## API routes

All current application routes are unauthenticated `GET` endpoints under `/api/v1`.

| Route | Inputs and limits | Current output |
|---|---|---|
| `/api/v1/health` | None | Uptime plus JSON-cache, bar-store, and active provider-breaker state. |
| `/api/v1/cache` | None | JSON-cache and bar-store state without provider breakers. |
| `/api/v1/search` | Required `q`; blank text returns an empty list; results are deduplicated and capped at 12 | Local crypto/equity matches plus Yahoo and Tencent search results. Search discovers only CRYPTO and US/HK/CN forms; it does not discover IDX/JP/KR/DE/GB even though direct routes accept those markets. |
| `/api/v1/quotes` | Required comma-separated `symbols`; blank items are ignored; maximum 50 nonblank symbols | One result per requested symbol, including per-symbol error rows when providers fail. |
| `/api/v1/ohlcv` | Required `symbol`; `interval=1d`; `range=1y` | Provider OHLCV, normally backed by the SQLite bar store. |
| `/api/v1/analysis` | Required `symbol`; `interval=1d`; `range=1y` | Deterministic Python indicators, signals, score, verdict, and rule-generated summary. |
| `/api/v1/moneyflow` | Required `symbol`; `interval=5m`; `range=1d` | K-line volume/price-direction estimate; not exchange-reported order flow or identified “main-force” activity. |
| `/api/v1/chips` | Required `symbol`; `interval=1d`; `range=1y` | K-line-derived cost-distribution estimate; not exchange-reported holder positions. |
| `/api/v1/chan` | Required `symbol`; `interval=1d`; `range=1y` | Simplified Python Chan structures and MACD-divergence annotations. |

Symbols must contain `MARKET:CODE`. The parser uppercases both parts, accepts only `US`, `HK`, `CN`, `CRYPTO`, `IDX`, `JP`, `KR`, `DE`, or `GB`, and does not validate an exchange-specific code grammar before provider dispatch. Examples include `US:AAPL`, `HK:0700`, `CN:600519`, `CRYPTO:BTCUSDT`, and `IDX:^GSPC`.

Canonical interval names used by the provider and store code are `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`, and `1mo`; canonical ranges are `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, and `max`. The HTTP layer does not enforce those enums. Unsupported or unknown values can be rejected, silently defaulted, or capped differently by a selected provider, so callers must use the canonical values and inspect `source` and returned bar count.

## Providers and market coverage

| Market | Quote/OHLCV chain | Important boundary |
|---|---|---|
| US | Yahoo → Tencent → Stooq | Tencent is quote-only for US in this adapter; Stooq is delayed daily fallback. |
| HK, CN | Tencent → Yahoo | Tencent supports batch quotes; intraday OHLCV returns a fixed window of about 320 bars and period OHLCV is capped at 800 bars. Public endpoints are unofficial and intended for personal research. |
| CRYPTO | Binance mirror → OKX | Public spot-style pairs; OKX candle fallback is capped at 300 rows and Binance at 1000. |
| IDX | Yahoo | Yahoo code is passed through, for example `^GSPC` or `000001.SS`. |
| JP, KR, DE, GB | Yahoo | Single-provider suffix mapping; market registration is not equal coverage across all data features. |

Provider failures are tracked per provider and operation. Three consecutive failures open a 120-second circuit breaker; if every source is cooling, the chain still attempts a half-open pass. Licensing flags are descriptive only and do not prevent routing or redistribution.

Search coverage is narrower than direct `MARKET:CODE` coverage: the local lists cover CRYPTO plus selected US/HK/CN names, Yahoo search maps only unqualified US symbols and `.HK`/`.SS`/`.SZ`, and Tencent search maps CN/HK/US.

## SQLite cache and bar store

The JSON cache stores search, quote, and derived-computation payloads. Search entries are fresh for 24 hours. Quote freshness is market-session aware: 15 seconds while open and 300 seconds while closed; stale quote responses can be returned during a 45-second open-session or one-hour closed-session cap while a single background refresh runs. Derived calculations have two- or five-minute server cache lifetimes.

The separate bar store upserts `(symbol, interval, timestamp)` rows, normalizes daily/weekly/monthly timestamps, retains intraday rows for 35 days, and refreshes a short tail after the requested range is marked covered. If providers fail and stored rows exist, OHLCV can be returned with a `stale` source marker; the backend does not apply an age ceiling to that stored fallback.

Both databases are process-local SQLite by default and `/tmp` can be ephemeral across hosted restarts. Neither is shared across instances or with browser storage. The bar-store `full_days` field is a requested-range high-water mark, not verified historical coverage: provider caps or short histories can mark a range covered even when fewer days were returned. Treat bar count and source as evidence; do not treat the high-water mark as completeness.

## Deployment

`render.yaml` is the tracked Render contract: `rootDir: backend`, hash-locked installation, Python `3.11.15`, Uvicorn on `$PORT`, and `/api/v1/health` as the health path. `backend/Dockerfile` pins `python:3.11.15-slim`, installs the same hash lock, and runs as UID/GID `10001`; `backend/runtime.txt` also pins `python-3.11.15`.

Python `3.12.13` remains CI compatibility coverage. The Dockerfile and Procfile are generic building blocks for other hosts, but the repository has no Railway- or Fly-specific deployment configuration and does not prove a live deployment there. A reachable health route proves only that one process responded, not that frontend configuration, revision identity, providers, or every market path is healthy.

## Current limitations

- FastAPI allows any origin for `GET`, has no user authentication, and has no application rate limiting. Do not expose it as a private or multi-tenant boundary without additional controls.
- Yahoo, Tencent, Stooq, Binance, and OKX availability, licensing, history depth, and symbol coverage are external and uneven. Provider metadata is not an enforcement gate.
- Search cannot discover all direct-route markets, symbol code syntax is not exchange-validated, and interval/range values are not route-level enums.
- Python and TypeScript compatibility analysis can drift; there is no current generated contract or parity gate.
- Money flow and chip distribution are OHLCV-derived heuristics, not exchange position, account, trade-tape, or order-flow truth.
- SQLite defaults are ephemeral and the requested-range bar-store high-water mark can overstate actual provider coverage.
- SEC fundamentals are US-only frontend data and are neither a FastAPI capability nor equal global fundamental coverage.
