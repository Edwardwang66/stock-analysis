# Target Architecture: One Product, Two Runtime Profiles

> **Status:** Accepted; target architecture, not current implementation
> **Scope:** Target boundaries and migration invariants for the repository-wide refactor.
> **Last verified commit:** `f28c966fa399753505b71d38a9c2d5867554b02f`

## Decision

The accepted direction is a contract-first strangler refactor: one product, two first-class runtime profiles, and one domain vocabulary. Existing routes, feed URLs, and command-line entry points remain behind compatibility paths until their replacements satisfy explicit retirement gates.

This document is a target summary. Components marked **Planned** below are not claims about the current repository. Present behavior is documented in [`../current-architecture.md`](../current-architecture.md).

## Goals and non-goals

The accepted target has these goals:

- keep the dashboard and scheduled automation useful while vertical slices migrate;
- give static and server profiles the same contracts and deterministic analysis semantics;
- make source, timestamp, freshness, cache state, and fallback depth visible;
- separate transport, source selection, domain calculation, persistence, publication, and presentation;
- give canonical feed publication one validated writer and a reader-facing atomic snapshot contract;
- replace script-to-script path mutation with a reusable Python package.

The target does not turn the repository into a multi-user SaaS or brokerage system. It does not make Redis, PostgreSQL, TimescaleDB, object storage, or Kubernetes mandatory, rewrite all research in TypeScript, erase historical experiments, or promise identical values from different upstream providers.

## Static and server profiles

**Accepted target:** runtime selection happens once during application bootstrap. Pages and use cases receive a configured gateway instead of inspecting deployment variables or selecting providers themselves.

The **Planned static profile** uses, in order, an explicitly configured Edge adapter when capable and fresh, a published feed artifact when capable and fresh, a browser-safe provider, and finally the freshest stale candidate allowed by policy. An unset endpoint disables its adapter; the target has no hidden deployment URL.

The **Planned server profile** uses a fresh FastAPI result, then a sufficiently fresh published feed artifact, then the freshest allowed stale FastAPI, feed, or server-cache candidate. Both profiles expose the same data envelope and may degrade differently without changing the meaning of a result.

## Contract authority

The current report schema is a real but narrow implementation; it is not the complete authority described here. **Planned:** a canonical cross-language JSON Schema contract set covers symbols and markets, quotes, OHLCV, source metadata, analysis inputs and outputs, feed artifacts and manifests, and typed errors. TypeScript types and Pydantic models are generated from those schemas rather than maintained as parallel handwritten contracts.

Breaking contract changes increment the major schema version. During migration, readers may support the current and immediately preceding major version, while writers emit only the current version. Shared fixtures and cross-language contract tests enforce that boundary.

## DataGateway and adapter boundaries

**Planned:** `DataGateway` is the stable request interface used by frontend application code. Runtime profiles own source priority and freshness policy; adapters own transport, provider-specific symbol mapping, normalization, and capability declarations.

The target dependency direction is UI to application code to `DataGateway`, contracts, and deterministic analysis. FastAPI routes deliver HTTP only, application services orchestrate quote, OHLCV, and search use cases, ports define provider and persistence capabilities, and adapters implement those ports.

Pages do not construct raw GitHub or provider URLs. Provider adapters do not import concrete storage implementations. Unsupported capabilities are skipped explicitly, and data from different providers is not silently stitched unless a response declares itself composite and carries segment provenance.

## Deterministic analysis authority

**Planned:** a framework-independent TypeScript `analysis-core` package becomes the single authority for pure, deterministic, OHLCV-derived calculations displayed by the product. It has no React, fetch, storage, clock, or environment dependency.

Both runtime profiles use `analysis-core` in the browser. Existing FastAPI analysis endpoints remain compatibility facades during migration and retire only after parity gates pass. Batch jobs that require the same user-facing semantics call an `analysis-cli` built from `analysis-core` instead of reimplementing formulas in Python.

Analysis responses include an algorithm version and input digest so a displayed result can be tied to the calculation and input that produced it.

## Python research boundary

**Planned:** reusable Python data, research, and feed logic moves behind the `stock_core` package boundary. Scripts become thin command-line entry points, while `backtest/` owns experiments, configurations, and result production rather than shared libraries.

Python remains authoritative for research and backtesting methods that are not interactive dashboard semantics. A research result exposed in the UI carries a distinct method identifier, method version, data cutoff, and input identity. Scripts and backtests no longer mutate `sys.path` to import one another.

## Feed publisher and manifest target

**Planned:** jobs write into an isolated run directory and cannot publish canonical artifacts directly. The single publisher validates schema, signature where required, destination path, size, identifier, and idempotency before atomically replacing artifacts.

A reader-facing `FeedManifest` is written last and identifies the complete snapshot by run ID, generation time, manifest schema version, artifact path and schema version, SHA-256 digest, size, producer, and method metadata. Readers fetch the manifest first and accept only listed artifacts. If the new snapshot is incomplete or invalid, they continue to use the previous complete manifest.

This atomic snapshot manifest is different from the current Stage 1A workflow-local Git-staging allowlist. Publication stages only its recorded allowlist and never uses a broad feed-tree add. The accepted low-cost transport moves routine generated artifacts to a dedicated data branch while retaining contracts, fixtures, and documentation on the source branch.

## Security and observability invariants

The accepted target fails closed at trust boundaries:

- external submissions require a valid HMAC signature when the contract calls for one;
- artifact identifiers use an allowlisted character set and resolved destinations stay within the approved root;
- malformed contracts, invalid symbols, and contract mismatches do not trigger provider cycling that hides the fault;
- credentials stay in runtime configuration and never appear in artifacts, logs, or browser bundles;
- security fixes are not rolled back to fail-open behavior.

Every result exposes provider, fetch and market timestamps, freshness, cache state, fallback depth, and warnings. Shared error categories distinguish invalid requests, unsupported capabilities, rate limits, upstream failures, contract mismatches, and stale-only results. Static adapters apply scoped backoff and local caching; server mode centralizes circuit breakers, single-flight, cache policy, and provider health.

## Migration stages and retirement gates

The accepted program proceeds in four stages:

1. establish security, reproducible runtime baselines, truthful documentation, and release checks;
2. add schemas, generated models, shared fixtures, `DataGateway`, runtime profiles, and quote/OHLCV vertical slices;
3. extract `analysis-core` and `analysis-cli`, introduce `stock_core`, and add staged atomic feed publication;
4. split large UI/application boundaries and remove only retired compatibility code, duplicated snapshots, and obsolete documents.

An old path retires only after all known callers migrate, static and server CI pass, repository search or telemetry shows no remaining use, the replacement completes a full scheduled automation cycle, and a rollback path is available. Feed retirement additionally requires the previous complete manifest to remain usable. The retirement ledger records each old file, API, environment variable, workflow, replacement, and removal condition.

## Differences from the current system

| Boundary | Current system | Accepted target |
|---|---|---|
| Runtime selection | Source selection is concentrated in `frontend/lib/datasource.ts` but still branches across caches, FastAPI, Edge, raw feed, and browser sources. | **Planned:** bootstrap selects one profile and injects `DataGateway`. |
| Cross-language contracts | Frontend types, Pydantic models, feed JSON, and the report schema have uneven authority and coverage. | **Planned:** JSON Schema is canonical and generates language models. |
| Deterministic analysis | TypeScript frontend, FastAPI Python, and automation Python contain overlapping implementations. | **Planned:** `analysis-core` is authoritative; `analysis-cli` serves batch parity. |
| Python reuse | Scripts and backtests share implementation through direct imports and `sys.path` changes. | **Planned:** reusable logic lives in `stock_core`; CLIs and experiments depend on it. |
| Feed publication | Multiple writers update Git-backed paths; the Stage 1A manifest limits Git staging but is not a reader snapshot. | **Planned:** one publisher writes artifacts atomically and writes a reader-facing manifest last. |
| Edge configuration | Current frontend code can attempt a hard-coded deployment URL. | **Planned:** adapters are enabled only by explicit configuration. |

## Full program design

The complete accepted decision, alternatives, component map, data envelope, test matrix, rollback rules, and acceptance criteria are in [`../superpowers/specs/2026-07-16-stock-analysis-refactor-design.md`](../superpowers/specs/2026-07-16-stock-analysis-refactor-design.md).
