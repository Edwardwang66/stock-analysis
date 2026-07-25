# Repository Feed

> **Status:** Current
> **Scope:** Entry point for repository-backed generated artifacts and their consumers.
> **Last verified commit:** `9e8ea546f3a43456f3579a14b752d27142cdf58e`

## Role

`feed/` is a Git-backed publication surface for scheduled automation, research outputs, OpenClaw submissions, operational state, and frontend readers. It is not one transactional database or a single-writer source of truth. Different producers own different paths, schema coverage is uneven, and readers currently fetch artifacts independently.

Most frontend reads try a configurable remote feed first and then the same relative path from the bundled `frontend/public/feed` snapshot. The remote defaults to raw GitHub `main/feed` but `NEXT_PUBLIC_FEED_BASE` can replace it; the bundle is a fallback, not an authoritative live mirror.

## Artifact families

| Family | Current role | Validation boundary |
|---|---|---|
| `index.json` | Report summaries, latest pointers, statistics, contributions, and freshness | Rebuilt from reports; not a snapshot manifest. |
| `health.json` | Watchdog audit result and selected source freshness | Warnings can coexist with `ok`; not completeness proof. |
| `watchlist.json` | Repository watchlist tiers and symbols | Producer convention. |
| `reports/` | Routine, OpenClaw, and manual report payloads | Only family covered by `schema/report.schema.json`. |
| `signals/` | Report-derived book plus RS, Chan, and Winter outputs | Multiple family-specific shapes. |
| `market/` | Current report-derived state and market history | Producer-specific structures. |
| `factory/` | Submitted factor candidates and provenance | Copied report data; no six-gate semantic enforcement. |
| `screener/` | Scores, histories, win rate, and JSON/Markdown analysis | Mixed producer and file conventions. |
| `stock-notes/` | Per-symbol notes, index, stance history, and updates | Privileged direct-write contract, not report ingress. |
| `intraday/` | Main snapshot, live-branch latest state, and overnight pack | Live latest has no bundled fallback. |
| `crypto/` | Hyperliquid state and pre-IPO history | Producer-specific JSON. |
| `funds/` | Tracked 13F holdings | Producer-specific JSON. |

`schema/` and `inbox/` support report validation and transport; they are not additional reader artifact families.

## Producers and consumers

On a successful report publication, the publisher writes `reports/`, conditionally updates `signals/latest.json`, `market/state.json`, and `factory/candidates.json` only when the corresponding payloads are non-empty/truthy, and rebuilds `index.json` after those writes complete. An empty derived payload does not clear its prior artifact; the prior file remains intact. Separate workflows and scripts write screener, market history, intraday, crypto, funds, notes, health, RS, Chan, and Winter artifacts. Writers are not consolidated, and workflow concurrency groups do not form one cross-writer transaction.

Frontend consumers use handwritten TypeScript interfaces and parse/cast fetched JSON without running the Python report validator. Local routines, GitHub Actions, OpenClaw tools, and optional Winter tooling also read the tree. Winter PostgreSQL is an optional projection and analysis store; it is not the feed authority.

Five workflows currently participate in the Stage 1A publication ledger: `alpha-routine.yml`, `feed-validate.yml`, `hyperliquid-monitor.yml`, `monthly-studies.yml`, and `openclaw-notes.yml`. Other writers still stage explicit files or use separate branches and APIs.

## Report validation

Only `reports/` uses Draft 7 `schema/report.schema.json` version `1.0`. With `jsonschema` installed, validation uses `Draft7Validator` without a `FormatChecker`, so declared `date` and `date-time` formats are descriptive. Without `jsonschema`, validation falls back to selected required-field, kind, producer, and ID checks. Schema validity does not validate analytical claims, candidate gate semantics, or every feed family.

External report ingress is the protected path:

- `openclaw` and `manual` submissions require HMAC-SHA256 under signature-enforcing workflows; a missing secret fails closed, while `signature.key_id` is stored but ignored for key selection;
- an external submission cannot claim `kind=routine`;
- report IDs must match `^[A-Za-z0-9._:-]{6,80}$`, and an existing ID is rejected as a conflict rather than accepted as an idempotent retry;
- strict JSON rejects NaN and Infinity;
- external ingress limits one report to 512 KiB, 400 positions, and 50 factor candidates;
- repository-dispatch ingress resolves an approved inbox root and exclusively creates (`xb`) its inbox file after strict validation; path containment and regular-file checks also constrain later validation and report destinations;
- the merge path checks for an existing report ID before using ordinary `save_json()` writes. That check and write are not one atomic create across workflows; publication-manifest staging separately rejects unrecorded, broad, traversal, symlink, and ambiguous-index paths.

Those protections do not apply to every internal writer. In particular, standalone stock-note mode constructs `feed/stock-notes/<symbol>.json` and writes locally or through GitHub Contents API without equivalent schema, HMAC, or symbol-path containment, and it does not rebuild `stock-notes/index.json`. Treat stock-note direct writes as privileged operations for trusted operators and trusted symbol input.

## Validate locally

Run these exact CI entry points from the repository root in the committed Python `3.11.15` environment:

```bash
python scripts/tests/test_validate_feed.py
python scripts/tests/test_feed_validation_security.py
python scripts/tests/test_feed_ingress.py
python scripts/tests/test_validate_feed_cli.py
python scripts/tests/test_feed_publication.py
python scripts/tests/test_workflow_security.py
```

These tests cover report schema behavior, strict parsing, HMAC and ingress boundaries, path containment, the publication ledger, and workflow policy. They do not validate the current contents or semantics of all 12 artifact families. Use the repository-wide [controlled Python gate](../docs/superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md#controlled-stage-1b-acceptance-gates) for lock reproduction and the full process matrix.

## Publication entry points

Internal report producers call `feed_lib.publish_report()`: optionally sign, then validate and direct-write the report; when the corresponding payloads are non-empty/truthy, it conditionally writes `signals/latest.json`, `market/state.json`, and `factory/candidates.json`. On a successful publish, after the report and any derived writes complete, it rebuilds `index.json`. Empty derived payloads leave prior derived artifacts intact. These are ordinary direct writes, not atomic replacements or a cross-file transaction. Writing the index last in this one path does not make it a reader manifest and does not coordinate other writers.

Signed external inbox files are validated and merged with:

```bash
FEED_HMAC_SECRET=... python scripts/validate_feed.py --require-signature --merge feed/inbox/example.json
```

Participating workflows set `FEED_PUBLICATION_MANIFEST` to a runner-local `/tmp` file. Successful feed writes/deletions record closed paths, and the workflow runs:

```bash
python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
```

The current manifest is only a workflow-local path ledger and Git-staging allowlist. It checks the paths a participating workflow may stage; it does not schema-validate or semantically approve them, is not committed or fetched by readers, and does not enumerate one complete feed generation.

The `feed-validate.yml` manual `workflow_dispatch` trigger currently selects neither validation job because both job conditions exclude that event; a manual run is therefore a no-op. Use the documented push, pull-request, or `openclaw-report` dispatch paths instead.

## Freshness and fallback

For most JSON, `frontend/lib/feed.ts` keeps a 30-second in-memory cache by relative path, requests `<REMOTE>/<path>`, and on non-success or exception requests the same relative path from the same-origin bundle. `REMOTE` defaults to raw GitHub `main/feed` and is replaced wholesale by `NEXT_PUBLIC_FEED_BASE` when configured. JSON is parsed and cast but not checked against a reader schema. Each path is independent, so a page can mix remote and bundled artifacts from different generations.

`getIntradayLive()` has no bundled fallback. Its base is produced by replacing the exact `/main/feed` substring in `REMOTE` with `/live/feed`; if a custom base does not contain that substring, the custom base is left unchanged and receives `/intraday/latest.json`. The tracked `frontend/public/feed` tree is partial and can be stale. The Pages workflow builds a selected temporary bundle, but its push trigger covers `frontend/**`, `feed/schema/**`, `.node-version`, and the workflow file—not generated feed artifacts outside `feed/schema`. Its export checks prove declared paths and a few critical files exist, not schema validity, cross-file completeness, or common generation identity.

`index.json` freshness is based on report timestamps, and `health.json` audits selected sources. Neither proves that all required families exist, are mutually consistent, or belong to one publication. The watchdog audit step currently pipes through `tee` without `pipefail`, so its recorded exit status can mask a failing Python audit.

## Current limitations

- Report schema coverage does not extend to the other artifact families, and the validator does not enforce declared date formats.
- Writers are not consolidated; direct writes, explicit staging, workflow-ledger staging, GitHub API writes, and a live branch coexist.
- Report publication is not atomic, cross-writer serialization is absent, and readers can mix generations through per-path fallback.
- External-report HMAC, size, ID, and path controls must not be inferred for stock notes or unrelated internal producers.
- The bundled snapshot is partial/stale between Pages deployments, and generated artifact-only changes outside `feed/schema` do not refresh it automatically.
- General CI ignores most generated feed artifact paths, but not `feed/schema`; focused producer workflows and local tests remain separate.
- Freshness, health, directory existence, and an index written last are not completeness or rollback guarantees.

The reader-facing complete-snapshot manifest is **Planned**: it must identify one immutable/versioned generation, enumerate artifacts and digests, validate required-family and cross-artifact completeness, retain the previous complete snapshot, and be written last as the reader publication point. Readers must verify it and fall back to the previous complete manifest when the newest generation is missing or invalid. None of that is current behavior, and the Stage 1A staging ledger must not be renamed or reused as if it already provided it.

## Authoritative documentation

- [Feed Data Contracts](../docs/data-contracts/feed.md) defines report fields, ingress limits, writer ownership, fallback, freshness, and current publication boundaries.
- [Workflow Operations](../docs/operations/workflows.md) inventories triggers, permissions, generated paths, and recovery procedures.
- [Configuration](../docs/configuration.md) owns `FEED_HMAC_SECRET`, feed base URLs, branch/options, and platform variables.
- [Current Architecture](../docs/current-architecture.md) places the feed among frontend, FastAPI, research, automation, and trust boundaries.
