# OpenClaw Stock Notes

> **Status:** Current
> **Scope:** Implemented per-symbol stock-note shape, trusted write modes, frontend consumption, and failure boundaries.
> **Last verified commit:** `a8d3d4c1a0ae707fca6c500f4de61a4bad0a8726`

## Current contract

The frontend reads one JSON file per symbol:

```text
feed/stock-notes/<MARKET>-<CODE>.json
```

For example, `US:AAPL` maps to `feed/stock-notes/US-AAPL.json`.

The handwritten frontend interface supports:

```json
{
  "symbol": "US:AAPL",
  "date": "2026-07-24",
  "model": "provenance label",
  "producer": "producer label",
  "stance": "中性",
  "thesis": "Balanced thesis",
  "earnings": "Known earnings context",
  "news": "Known news context",
  "risks": "Material risks",
  "view": "Concise view",
  "sources": [
    {
      "title": "Source title",
      "url": "https://example.invalid/source"
    }
  ]
}
```

Optional current fields include `methodology`, `intraday_update`, and `fundamentals`. The frontend treats the file as JSON matching its interface; there is no stock-note JSON Schema or HMAC validator.

`OPENCLAW_MODEL` populates provenance metadata in generated templates. It does not select or invoke a model.

### stock-analyst 角色 prompt(交给你的 OpenClaw)

```text
For the selected symbol, return one JSON object matching the current stock-note fields.
Separate sourced facts from opinion; include source titles and links for factual claims.
Use stance 看多, 看空, or 中性. State missing data instead of inventing it.
Do not output an order, target price, or personalized investment recommendation.
```

This prompt is operator input, not repository-enforced validation. Review its output before using the privileged write path.

## Implemented write modes

Stock-note mode is selected with `--stock-note`:

```bash
python scripts/openclaw_client.py \
  --mode local \
  --stock-note US:AAPL \
  --report-file note.json
```

- `local` writes the derived path in the current checkout.
- Any non-local mode name, including `--mode github-api` or `--mode dispatch`, uses GitHub Contents API for stock notes.
- Contents writes default to `main` unless `OPENCLAW_BRANCH` overrides it.
- The client reads `GITHUB_TOKEN` first and falls back to `OPENCLAW_TOKEN`.

The stock-note branch does not use report `repository_dispatch`, report HMAC validation, or `feed/inbox/`. A direct note update also does not rebuild `feed/stock-notes/index.json`.

The scheduled `.github/workflows/openclaw-notes.yml` is separate. It runs deterministic OHLCV/SEC-based daily logic locally, records its note/index/analysis paths in the staging ledger, and pushes `main`. Its `OPENCLAW_MODEL` value is a provenance label, not evidence that an external model ran.

## Authentication and trust

Contents API authentication authorizes the token's repository write. It does not validate the note.

Current direct-write limitations include:

- no approved-root containment for a symbol supplied inside a custom note file;
- no stock-note schema validation;
- no HMAC signature check;
- no automatic source, stance, or date validation;
- no automatic note-index rebuild.

Use local and Contents modes only with trusted operators and trusted, reviewed input. Restrict tokens to the intended repository and branch. Do not expose tokens in commands copied into logs or notes.

## Frontend and index behavior

`frontend/lib/feed.ts` derives an individual note path from the requested UI symbol and tries raw GitHub before the bundled feed. The symbol page displays a note when that artifact is available.

`stock-notes/index.json` and stance history are separate artifacts used by broader coverage/digest views. Updating an individual note through the standalone client does not update either one.

The raw/bundled reader performs no schema or signature validation and can mix generations. See [Feed Data Contracts](data-contracts/feed.md).

## Failure behavior

- Missing token in a non-local mode exits before the API call.
- A Contents API error raises and prevents a successful client completion.
- A successful Contents response proves only that GitHub accepted that file update.
- Scheduled daily logic catches per-symbol failures, retries once, logs final failures, and can exit zero with partial or stale coverage.
- Intraday note pushing can log exhausted retries without returning a failing process status.

Verify the note's exact path, content, date, producer, branch commit, and consumer view. Do not use workflow success or the model label as a completeness/quality signal.

## Authority links

- [OpenClaw Report Integration](openclaw-integration.md) — signed report ingress and publication.
- [Feed Data Contracts](data-contracts/feed.md) — feed transport, index, schema, and snapshot limitations.
- [Configuration](configuration.md) — token, branch, model-label, and watchlist settings.
- [Workflow Operations](operations/workflows.md) — scheduled note trigger, staging, and partial-failure behavior.
- [Compliance](compliance.md) — labeling, source, secret, and use boundaries.
