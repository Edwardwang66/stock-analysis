# Feed Data Contracts

> **Status:** Current
> **Scope:** Current repository-backed feed artifacts, the report and research schemas, validation, consumers, and known limitations.
> **Last verified commit:** `11beda8696d1b12c037fc2f7465f4a7fae3183a2`

## Transport and consumers

The `feed/` tree is a Git-backed publication surface used by the frontend, GitHub Actions, local automation, OpenClaw integration, and optional Winter tooling.

For most frontend artifacts, `frontend/lib/feed.ts` tries the configured raw GitHub feed first and then retries the same relative path from the same-origin bundled `public/feed`. Results are cached in memory for 30 seconds by relative path. Fallback is per artifact, not per snapshot, so one page can combine generations.

`getIntradayLive()` is different: it reads `live/feed/intraday/latest.json` remotely and has no bundled fallback. The tracked `frontend/public/feed` tree is partial and can be stale; the Pages workflow constructs a selected temporary snapshot during deployment, while ordinary local/server builds retain the tracked bundle unless another build input replaces it.

Neither raw nor bundled transport verifies a reader-facing signature, manifest, commit identity, or cross-file completeness.

## Artifact families

| Family | Current contents | Principal producers | Principal consumers and validation |
|---|---|---|---|
| `index.json` | Report summaries, contribution log, latest pointers, statistics, freshness | `feed_lib.rebuild_index()` after report publication or merge | Home, desk, intel; structural conventions only |
| `health.json` | Feed audit result, source freshness, issues | `audit_feed.py --write` through feed watchdog | Intel and operators; `ok` means no critical audit issue |
| `watchlist.json` | Persistent watchlist tiers and symbols | Maintainers; daily screener rotates its screener tier | UI, OpenClaw daily, digest |
| `reports/` | Routine, OpenClaw, and manual report JSON | Internal routines, research publishers, Hyperliquid, validated external ingress | Frontend report/intel views; report schema v1.0 |
| `signals/` | Latest report-derived book, RS ranks/history, Chan statistics, Winter outputs | Report publisher, daily screener, Chan workflow, Winter event heat | UI signal and symbol views; family-specific producer conventions |
| `market/` | Report-derived market state and market history | Report publisher, market snapshot workflow | Home, desk, intel; family-specific structures |
| `factory/` | Submitted factor candidates and provenance | Report publisher | Intel; candidates are copied from reports without six-gate semantic enforcement |
| `screener/` | Latest screener JSON, scores, histories, win rate, analysis Markdown | Daily screener/digest, Winter, OpenClaw notes | Screener, tracker, reports, watchdogs; mixed JSON/Markdown conventions |
| `stock-notes/` | Per-symbol notes, note index, stance history | OpenClaw client/daily paths, digest, intraday updater | Symbol page and daily routines; privileged direct-write contract |
| `intraday/` | Live latest snapshot, main fallback, overnight pack | Winter loop, intraday workflow, watchdog, premarket workflow | Home/desk and routines; live latest uses a separate branch |
| `crypto/` | Hyperliquid state and pre-IPO history | Hyperliquid workflow | Intel and report views; producer-specific JSON |
| `funds/` | Tracked fund 13F holdings | Funds workflow | Intel; producer-specific JSON |
| `research/` | Deep-research briefs `<brief-id>.json` and the family `index.json` with brief summaries, statistics, and open questions | `scripts/deep_research.py` through `deep-research.yml` | Intel research panel through `frontend/lib/feed.ts`, plus `feed_lib._artifact_freshness()` and `audit_feed.py`; research schema v1.0 |

`schema/` contains the report and deep-research schemas and `inbox/` is an external-submission transport. They support those two validated families rather than forming additional reader families.

## Report schema v1.0

`feed/schema/report.schema.json` declares Draft 7 report version `1.0`.

Required fields are:

- `schema_version` equal to `1.0`;
- `id`, matching `^[A-Za-z0-9._:-]{6,80}$`;
- `kind`, one of `routine`, `openclaw`, or `manual`;
- `produced_at`;
- `asof_data`;
- `producer` with a required `name`.

Optional report sections include market state, engine summary, book, factor candidates, alerts, contribution, notes, and an HMAC signature.

When `jsonschema` is installed, `feed_lib.validate_report()` uses `Draft7Validator` without a `FormatChecker`. The schema-declared `date` and `date-time` formats are therefore descriptive and are not syntax-enforced. When `jsonschema` is unavailable, local validation falls back to selected required-field, kind, producer, and identifier checks rather than full Draft 7 validation.

Candidate `passed_gates`, `decision`, statistics, and explanatory text are data. Current schema/CI does not enforce six-gate investment semantics or consistency between those fields, and publishers copy submitted candidates into `factory/`. A schema-valid report is not an analytical approval.

## Producer and consumer ownership

- Internal report producers call `publish_report()`, which validates a report, writes the report and any derived signal/market/factory files, and then rebuilds `index.json`.
- External report submissions enter through `feed/inbox/` or repository dispatch and are validated before merge.
- Frontend consumers use handwritten TypeScript interfaces and per-artifact fetch functions. They do not run the Python schema validator.
- Scheduled non-report producers own their specific files or directories as listed above.
- Winter PostgreSQL is an optional projection/analysis store; it is not the feed source of truth.

The report publisher writes individual files directly. Its final index rebuild is not a cross-file transaction and does not coordinate other writers.

## External submission authentication

External report ingress treats input as untrusted:

- `openclaw` and `manual` reports require a valid `HMAC-SHA256` signature over canonical JSON with the `signature` field omitted;
- an external submission claiming `kind=routine` is rejected;
- a missing `FEED_HMAC_SECRET` fails closed;
- the verifier uses the configured shared secret; optional `signature.key_id` is stored but is not used to select a key, so automatic key rotation is not implemented.

The standalone report client supports:

- `local`, which writes an inbox file in the checkout;
- `github-api`, which writes a new inbox file through GitHub Contents API, defaulting to `openclaw-inbox`;
- `dispatch`, which submits `repository_dispatch` event `openclaw-report`.

The client signs only when a nonempty secret is configured. An unsigned remote submission can be accepted by the API transport but is rejected by the workflow validator. A dispatch HTTP 204 means the event was accepted, not that publication completed; the client does not poll workflow or commit state.

Manual pull-request submission is a workflow path, not a standalone client mode. Pull-request-target validation reads the submitted files as untrusted data and does not execute the contributor's code.

Stock-note modes are separate privileged direct writes. Local mode writes the checkout and any non-local mode uses the Contents API, normally on `main`; they currently lack equivalent symbol-path containment, schema, and HMAC validation and do not rebuild `stock-notes/index.json`. Restrict them to trusted operators and inputs.

## ID, path, size, and idempotency rules

- Report IDs must be 6–80 characters and use only ASCII letters, digits, `.`, `_`, `:`, and `-`.
- Report and inbox destinations are resolved under approved family roots; path escape and symlink/non-regular staging cases are rejected by the Stage 1A helpers.
- External ingress limits one report to 512 KiB, 400 positions, and 50 factor candidates. Dispatch measures the strict pretty-serialized bytes; file validation measures file bytes.
- Those size/count limits are ingress checks, not JSON Schema rules and not limits applied by every internal producer.
- Non-standard JSON constants such as NaN and Infinity are rejected by strict parse/serialization.
- An ID already present in `feed/reports/` is an idempotency conflict and is rejected. It is not silently skipped or treated as a successful retry.
- Repository-dispatch inbox creation is exclusive. The standalone GitHub Contents report mode does not fetch an existing inbox SHA, so the same path cannot be overwritten as a retry.

The Stage 1A ingress, signature, path, and publication controls are current and are covered by the pinned feed security/publication test suites.

## Index and freshness semantics

`rebuild_index()` lexically orders all reports by `produced_at`.

- `reports` exposes at most 60 summaries.
- `contributions` exposes at most 80 entries.
- Aggregate statistics and the timeline scan all stored reports.
- `freshness.last_report_at` uses the newest report of any kind.
- `latest.report` and `market_data_asof` prefer the newest report with an `engine`; if no report has one, they use the newest report.
- `freshness.stale` means the newest report is more than 36 hours old.

`health.json` is a separate audit result. Its `ok` value means there were no critical audit issues; warnings and informational findings can still exist. The source-freshness map covers selected artifacts, not snapshot completeness, and the watchdog's bundled-feed check only tests the age of the tracked bundled `index.json`.

Neither index freshness nor health proves that all files belong to one complete generation.

## Raw feed and bundled snapshot fallback

For a normal `fetchJson(rel)` call:

1. return the 30-second in-memory value for that relative path when fresh;
2. request `${NEXT_PUBLIC_FEED_BASE or default raw main/feed}/${rel}`;
3. on non-success or exception, request the same relative path from `${NEXT_PUBLIC_BASE_PATH}/feed`;
4. return `null` when both fail.

JSON is parsed but not validated against a reader schema. Each relative path is cached and fetched independently, so fallback can mix raw and bundled generations.

Markdown analysis follows the same raw-then-bundled idea with text checks. Live intraday is remote-only. The Pages bundle is created from selected repository paths during deployment; the tracked bundle used by other builds is not a complete mirror of current `feed/`.

## Validation and publication commands

Validate signed external inbox files:

```bash
FEED_HMAC_SECRET=... \
  python scripts/validate_feed.py --require-signature feed/inbox/example.json
```

Validate and merge trusted inbox files:

```bash
FEED_HMAC_SECRET=... \
  python scripts/validate_feed.py --require-signature --merge feed/inbox/example.json
```

Stage only paths recorded by a participating workflow:

```bash
python scripts/feed_publication.py stage "$FEED_PUBLICATION_MANIFEST"
```

Run the pinned feed regression gate:

```bash
scripts/run-python311 python -m unittest \
  scripts.tests.test_feed_ingress \
  scripts.tests.test_feed_validation_security \
  scripts.tests.test_validate_feed_cli \
  scripts.tests.test_feed_publication
```

Do not put a real HMAC secret in documentation, committed shell files, or logs.

## Current schema coverage

Two families are schema-covered: report artifacts use `feed/schema/report.schema.json` and deep-research briefs use `feed/schema/research.schema.json`, both Draft 7 version `1.0`. CI does not schema-scan every stored report in every workflow, and report date formats are not enforced without a format checker. A brief that passes its schema is a well-formed brief, not an approved analytical conclusion, a strategy approval, or investment advice.

The remaining artifact families rely on TypeScript interfaces, producer-specific structures, handwritten checks, or workflow conventions. A `.json` suffix, successful fetch, or inclusion in `index.json` is not evidence of schema validation.

## Current publication limitations

`FEED_PUBLICATION_MANIFEST` is the Stage 1A workflow-local Git-staging path ledger and allowlist. It constrains which successfully recorded local feed writes/deletions a participating workflow may stage. It does not mean each recorded artifact was schema-validated.

The ledger lives at a runner-temporary path in six workflows. It is not published for readers, is not fetched by the frontend, does not enumerate one complete snapshot, and provides no reader rollback or previous-complete fallback contract.

Other workflows still stage explicit files. Distinct workflow concurrency groups do not serialize those writers. Report publication writes the report and derived artifacts before rebuilding the index, but those file writes are not atomic replacements and there is no multi-writer transaction.

## Target manifest publisher

**Planned:** a reader-facing publisher must:

- assign a version or immutable commit identity to one complete snapshot;
- enumerate immutable or versioned artifact locations with content digests;
- validate required-family and cross-artifact completeness before exposure;
- retain prior complete objects/manifests;
- write the new manifest last as the atomic reader publication point;
- let readers verify entries and fall back to the previous complete manifest when the newest snapshot is missing, incomplete, or invalid.

Writing a manifest last is insufficient if its artifact paths are mutable or prior objects are not retained. The Stage 1A staging ledger must not be reused or renamed as though it already satisfies this reader contract.
