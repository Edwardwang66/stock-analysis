# OpenClaw Report Integration

> **Status:** Current
> **Scope:** Implemented external report submission modes, validation, authentication, publication, and failure behavior.
> **Last verified commit:** `8cff75b8e31d6b3a07a9d6198e0bc54bcb3b594a`

## 1. Client boundary

`scripts/openclaw_client.py` is a standalone reference client for report JSON. It does not run an external agent service, select or call an LLM provider, schedule a committee, or verify analytical claims. Its built-in role builders produce example report content; real external analysis must be supplied with `--report-file`.

`OPENCLAW_MODEL` is provenance metadata only. Setting it does not select a model provider.

The implemented report modes are:

| Mode | Transport | Default destination | Publication behavior |
|---|---|---|---|
| `local` | Local filesystem | `feed/inbox/<id>.json` in the checkout | Writes only; no commit or merge |
| `github-api` | GitHub Contents API | New file on `openclaw-inbox` unless `OPENCLAW_BRANCH` overrides it | Requires a later PR or trusted push path; an existing path is not overwritten |
| `dispatch` | GitHub repository dispatch | Event `openclaw-report` | Workflow receives, validates, merges, rebuilds index, and pushes on success |

A manual pull request that changes `feed/inbox/**` is an implemented workflow path, not a client mode.

### 1.2 调度(Orchestrator)

There is no repository-hosted OpenClaw orchestrator. External operators choose their own schedule and analysis implementation.

Repository automation has two relevant but distinct entry points:

- `.github/workflows/feed-validate.yml` receives signed report submissions and publishes accepted reports.
- `.github/workflows/openclaw-notes.yml` runs `openclaw_daily.py --mode local --stocks-only`; it is deterministic OHLCV/SEC logic and does not require an external LLM provider.

The accepted future agent/council design belongs to [the target architecture RFC](rfcs/target-architecture.md). It is not current submission behavior.

## 2. Report contract

Reports use [`feed/schema/report.schema.json`](../feed/schema/report.schema.json), version `1.0`. Current required fields, identifier rules, optional sections, and validation caveats are documented in [Feed Data Contracts](data-contracts/feed.md).

External reports must use `kind=openclaw` or `kind=manual`. External `kind=routine` is rejected.

Schema validation does not approve research semantics:

- Draft 7 date/date-time formats are not checked because the current validator does not install a format checker.
- Candidate `passed_gates`, `decision`, PBO, IC, and t-stat relationships are not enforced by CI.
- Submitted candidates can be copied to `feed/factory/`; no current L6 or six-gate enforcement promotes or rejects them.

Treat all report free text and candidate fields as untrusted data for display and analysis, never as executable instructions.

## 3. Signing and authentication

External ingress requires an `HMAC-SHA256` signature produced from canonical JSON with the `signature` field omitted.

```bash
FEED_HMAC_SECRET=... \
GITHUB_TOKEN=... \
python scripts/openclaw_client.py \
  --mode dispatch \
  --role residual-analyst \
  --report-file report.json
```

The client signs only when `FEED_HMAC_SECRET` is nonempty. It can transport an unsigned report, but the trusted workflow rejects it. A missing workflow secret also fails closed.

`GITHUB_TOKEN` or fallback `OPENCLAW_TOKEN` authenticates the GitHub API transport. Use a fine-grained credential restricted to this repository and the selected operation. HMAC authenticates report possession of the shared secret; it does not grant GitHub write permission.

The optional `signature.key_id` is stored but ignored by the current verifier, which checks only `FEED_HMAC_SECRET`. Automatic key selection and rotation are not implemented.

## 4. Ingress and publication

### Repository dispatch

The client sends `client_payload.report`. The publisher:

1. parses strict JSON from `PAYLOAD`;
2. validates the external report and signature;
3. exclusively creates the approved inbox path;
4. merges accepted content into `feed/reports/`;
5. writes report-derived artifacts and rebuilds `feed/index.json`;
6. stages only paths in the workflow-local publication ledger and pushes.

An HTTP 204 from GitHub means only that the dispatch event was accepted. The client does not poll workflow completion, publication commit, or reader visibility.

### GitHub Contents API

Report Contents mode creates `feed/inbox/<id>.json`, normally on `openclaw-inbox`. It does not fetch an existing file SHA, so retrying the same ID/path fails rather than overwriting it. Open a reviewed pull request to `main`; pull-request-target validation treats the file as data and does not execute contributor code. The trusted `main` push path performs the merge.

### Local and manual pull request

Local mode writes an inbox file only. Validate it before committing:

```bash
FEED_HMAC_SECRET=... \
python scripts/validate_feed.py \
  --require-signature \
  feed/inbox/<id>.json
```

A manual PR follows the same untrusted-file validation boundary. Merging a PR and publishing a report are separate events; verify the trusted follow-up workflow and resulting commit.

## 5. Rejection and idempotency

External ingress currently rejects:

- malformed or non-object JSON;
- required report/schema failures;
- missing or invalid HMAC;
- external `routine` kind;
- invalid or escaping identifiers/paths;
- non-standard JSON constants;
- files over 512 KiB, more than 400 positions, or more than 50 candidates;
- an ID already present in `feed/reports/`.

A duplicate ID is a conflict, not a successful idempotent retry. Create a new valid ID for a distinct submission; investigate transport/workflow state before resubmitting the same analysis.

The fallback validator used by ad-hoc local environments without `jsonschema` is weaker than the pinned workflow environment. Use the pinned repository dependency path for acceptance decisions.

## 6. Daily client distinctions

`scripts/openclaw_daily.py` differs from the standalone client:

- stock notes use local writes or Contents API;
- quant-role reports use local inbox writes or repository dispatch for either non-local mode name;
- per-symbol and per-role exceptions are caught and logged, so a run can exit successfully with partial or stale coverage;
- its optional Winter PostgreSQL archive skips when `WINTER_PG_DSN` is explicitly empty.

Do not infer complete coverage from exit code alone. Check expected files, dates, workflow publication, and index state.

## 7. Security boundaries and current gaps

- External report ingress has HMAC/schema/path boundaries; stock-note direct writes do not share them.
- Edge and FastAPI quote/analysis routes have no application authentication or rate limiting.
- Report publication is a sequence of direct writes plus index rebuild, not an atomic reader snapshot.
- The workflow's `FEED_PUBLICATION_MANIFEST` constrains Git staging only.
- A schema-valid report is not an investment decision, strategy approval, or proof of analytical correctness.

See [Workflow Operations](operations/workflows.md) for trigger and failure semantics, [Configuration](configuration.md) for exact environment ownership, [Feed Data Contracts](data-contracts/feed.md) for artifact/publication boundaries, and [OpenClaw Stock Notes](openclaw-stock-notes.md) for the separate privileged note path.
