# Workflow Operations

> **Status:** Current
> **Scope:** GitHub Actions triggers, permissions, generated artifacts, writers, and recovery procedures.
> **Last verified commit:** `e74ad00c026b410db9a1438e46c26c09dad32bd8`

## Operating model

GitHub Actions runs tests, builds Pages, produces repository-backed feed artifacts, operates intraday state on the `live` branch, and manages selected issues and Dependabot pull requests.

Most feed workflows are independent writers. Their distinct concurrency groups prevent duplicate runs of the same workflow, but they do not serialize writes across workflows. A writer normally rebases or pulls before pushing; this is conflict handling, not a cross-writer transaction.

Five workflows use `FEED_PUBLICATION_MANIFEST`: alpha routine, Hyperliquid monitor, monthly studies, OpenClaw notes, and feed validation. In those jobs it is a runner-temporary ledger of successfully recorded feed writes and deletions and an allowlist for `git add`. It is not a reader-facing snapshot manifest. Other writers stage explicit paths.

## Workflow inventory

| Basename | Purpose | Trigger | Command or entry point | Write or deploy target | Permissions | Concurrency group | Configuration |
|---|---|---|---|---|---|---|---|
| `alpha-routine.yml` | Produce regular alpha reports and end-of-day factor output | Cron `20 14-21 * * 1-5` and `30 22 * * 1-5`; dispatch input `fast=false` | `run_routine.py` with optional `--fast`; end-of-day `factor_factory.py --publish`; manifest stager | Manifest-recorded feed files in selected checkout and upstream, normally `main` | `contents: write` | `alpha-routine`; cancel false | `.python-version`, `requirements/automation.txt`, `FEED_HMAC_SECRET`, composed `GITHUB_RUN_URL`, `FEED_PUBLICATION_MANIFEST` |
| `chan-stats.yml` | Refresh scheduled Chan statistics | Cron `30 0 * * 6`; push to `main` for `scripts/chan_engine.py`; dispatch | `python scripts/chan_engine.py` | `main` `feed/signals/chan-stats.json` | `contents: write` | `chan-stats`; cancel false | `.python-version`, `backend/requirements.txt` |
| `daily-digest.yml` | Build daily digest history and issue | Cron `30 23 * * 1-5`; dispatch | `python scripts/daily_digest.py` | `main` `feed/screener/history.json`, `feed/stock-notes/stance-history.json`, and Issue | `contents: write`, `issues: write` | `daily-digest`; cancel false | `.python-version`, mapped `GITHUB_TOKEN` |
| `daily-screener.yml` | Run scored market screener and update watch/strength data | Cron `30 22 * * 1-5`; push to `main` for `backend/app/analysis/signals.py` or `scripts/daily_screener.py`; dispatch input `threshold=80` | `daily_screener.py --threshold ... --concurrency 10` | `main` screener, watchlist, RS rank/history files, and deduplicated Issue | `contents: write`, `issues: write` | `daily-screener`; cancel false | `.python-version`, backend requirements, `GH_TOKEN` |
| `dependabot-automerge.yml` | Attest eligible Dependabot updates and enable auto-merge | Pull-request-target opened, synchronize, reopened; cron `45 */6 * * *`; dispatch | Dependabot metadata plus `scripts/dependabot_merge_gate.py` for current PR or sweep | Pull-request label, status, and auto-merge state only | `contents: write`, `pull-requests: write`, `issues: write`, `checks: read`, `statuses: write` | `dependabot-automerge-${{ github.repository }}`; `queue: max`; no cancel key | `.python-version`, built-in `GITHUB_TOKEN`, internal label, context, repo, PR, head, update, ecosystem values |
| `deploy-pages.yml` | Build, smoke-test, and deploy the static profile | Push to `main` for `frontend/**`, `feed/schema/**`, `.node-version`, `.github/workflows/deploy-pages.yml`; dispatch | `npm run build:static`, `npm run smoke:static`, upload Pages artifact, deploy Pages | `github-pages` environment from `frontend/out` | Top-level empty; build `contents: read`; deploy `pages: write`, `id-token: write` | `pages`; cancel true | `.node-version`, Node 20.20.2, npm 10.8.2, `API_BASE`, `EDGE_BASE`, computed base/feed paths, computed public site URL `https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/`, `STATIC_FEED_SOURCE`, `RUNNER_TEMP` |
| `docs.yml` | Validate the complete documentation contract | Push to `main`; every pull request; dispatch | `python scripts/tests/test_check_docs.py`; `python scripts/check_docs.py` | CI checks only; no generated artifacts | `contents: read` | `docs-${{ github.ref }}`; cancel true | `.python-version`, Python 3.11.15, Git, non-root identity |
| `feed-validate.yml` | Validate inbox submissions and merge trusted push/dispatch ingress | Push to `main` for `feed/inbox/**`; pull-request-target opened, synchronize, reopened for same path; repository dispatch `openclaw-report`; dispatch has no job | Trusted validation, `validate_feed.py`, `feed_ingress.py`, merge, manifest stage | PR only validates; push and repository dispatch merge manifest-recorded feed paths to `main` | Top and PR `contents: read`; publisher `contents: write` | `feed-validate-${{ github.event_name }}`; cancel false | `.python-version`, script requirements, `FEED_HMAC_SECRET`, `PAYLOAD`, `RUNNER_TEMP`, `GITHUB_WORKSPACE`, `FEED_PUBLICATION_MANIFEST` |
| `feed-watchdog.yml` | Audit feed freshness, attempt intraday fallback, and report staleness | Cron `0 9,21 * * *` and `25 0-20/1 * * 1-5`; dispatch | `intraday_report.py`; `audit_feed.py --write`; issue shell | `live` intraday latest, `main` `health.json`, and feed-stale Issue | `contents: write`, `issues: write` | `feed-watchdog`; cancel false | `.python-version`, `GH_TOKEN`, `GITHUB_OUTPUT`, `REPORT` |
| `funds-13f.yml` | Refresh tracked fund holdings | Cron `0 10 * * 1,4`; dispatch | `python scripts/funds_13f.py` | `main` `feed/funds` and Issue | `contents: write`, `issues: write` | None declared | `.python-version`, `GH_TOKEN` |
| `hyperliquid-monitor.yml` | Publish Hyperliquid and pre-IPO history intelligence | Cron `10 */2 * * *`; dispatch | `hyperliquid_monitor.py --publish`; `preipo_history.py`; manifest stager | Manifest-recorded crypto, report, index, and derived feed files on selected ref, normally `main` | `contents: write` | `hyperliquid-monitor`; cancel false | `.python-version`, script requirements, `FEED_HMAC_SECRET`, composed `GITHUB_RUN_URL`, manifest; timeout 10 minutes |
| `intraday-report.yml` | Produce and chain the Actions intraday backup | Cron `*/15 0-20 * * 1-5`; push to `main` for `scripts/intraday_report.py`; dispatch | Checkout `main`; three-round `intraday_report.py`; backend health curl; self-dispatch | `live` `feed/intraday/latest.json`; no `main` feed commit | `contents: write`, `actions: write` | `intraday-report`; cancel false | `.python-version`, `API_BASE`, `GH_TOKEN`, `GITHUB_WORKSPACE`, `INTRADAY_OUT`, `INTRADAY_PRODUCER`; timeout 11 minutes |
| `keep-warm.yml` | Attempt periodic FastAPI health request | Cron `*/30 * * * *`; dispatch | Curl `API_BASE/api/v1/health` when configured | External health GET only | None declared; repository or organization default applies | None declared | `API_BASE` |
| `market-snapshot.yml` | Append market history snapshots | Cron `30 7 * * 1-5` and `45 22 * * 1-5`; push to `main` for `scripts/market_snapshot.py` or `.github/workflows/market-snapshot.yml`; dispatch | `python scripts/market_snapshot.py` | `main` `feed/market/history.json` | `contents: write` | `market-snapshot`; cancel false | `.python-version` |
| `monthly-studies.yml` | Run and publish monthly research studies | Cron `0 23 1 * *`; dispatch | `study_pbo.py --publish`; `study_downshift.py --publish`; manifest stager | Manifest feed files, `docs/study-*.md`, and `backtest/sp600_universe.json` on selected ref, normally `main` | `contents: write` | `monthly-studies`; cancel false | `.python-version`, automation requirements, `FEED_HMAC_SECRET`, manifest; timeout 45 minutes |
| `openclaw-notes.yml` | Produce deterministic stock notes and analysis Markdown | Cron `0 1 * * 2-6`; dispatch input `throttle=1.0` | `openclaw_daily.py --mode local --stocks-only`; manifest stage | Manifest-recorded stock notes, index, and screener analysis Markdown on `main` | `contents: write` | `openclaw-notes`; cancel false | `.python-version`, fixed `OPENCLAW_MODEL` provenance label, `OPENCLAW_THROTTLE`, manifest; timeout 40 minutes |
| `openclaw-watchdog.yml` | Check expected premarket and close analysis files and open an issue | Cron `40 13 * * 1-5` and `45 19 * * 1-5`; dispatch | Shell file checks and deduplicated issue command | Issues only | `contents: read`, `issues: write` | None declared | `GH_TOKEN` |
| `premarket-pack.yml` | Build overnight market pack | Cron `40 12 * * 1-5`; push to `main` for `scripts/premarket_pack.py`; dispatch | Fetch live snapshot; `python scripts/premarket_pack.py` | `main` `feed/intraday/overnight.json` | `contents: write` | `premarket-pack`; cancel false | `.python-version` |
| `tests.yml` | Gate frontend and Python contracts | Push to `main` ignoring `feed/crypto/**`, `feed/factory/**`, `feed/funds/**`, `feed/health.json`, `feed/index.json`, `feed/intraday/**`, `feed/market/**`, `feed/reports/**`, `feed/screener/**`, `feed/signals/**`, `feed/stock-notes/**`, `feed/watchlist.json`; every pull request; dispatch | Frontend lint, typecheck, tests, static/server builds and smokes; Python 3.11.15 and 3.12.13 lock/tests; aggregate gate | CI checks only | `contents: read` | `ci-${{ github.ref }}`; cancel true | `.node-version`, exact Node/npm, Python matrix and locks, internal Next, pip, Python, and result values; frontend matrix covers static root, static repository path, and server root with non-local test origins; no secrets |

## Feed writers and ownership

- Report-family writers: alpha routine, Hyperliquid monitor, monthly studies, internal backtests, and validated external ingress.
- Screening and market writers: daily screener, daily digest, Chan stats, market snapshot, premarket pack, funds 13F, and OpenClaw notes.
- Intraday writers: Winter outside Actions plus intraday report and feed watchdog. `live/feed/intraday/latest.json` is separate from main-branch fallback/overnight files.
- Health writer: feed watchdog runs `audit_feed.py --write` for `feed/health.json`.

No workflow owns the whole `feed/` tree. See [Feed Data Contracts](../data-contracts/feed.md) for family-level producers and consumers.

## Branch and commit behavior

Manual writer dispatches should normally run on `main`.

- Alpha routine, Hyperliquid monitor, and monthly studies use the selected checkout and an implicit push after rebase; dispatching another ref can push that ref.
- Several legacy writers explicitly push a local `main` branch and can fail when dispatched from another selected ref.
- Intraday report explicitly checks out `main` before producing the `live` branch artifact.
- Pages can intentionally deploy a selected dispatch ref; its raw feed base also uses the selected ref name.
- Feed validation uses distinct PR-validation and trusted publisher paths. Pull-request-target validation does not merge untrusted content.

Writer commits are operational history. Recover with a reviewed forward corrective or revert commit, not a force push.

## Required Variables and Secrets

- Repository Variable `API_BASE`: optional health and frontend FastAPI base; omit the trailing slash.
- Repository Variable `EDGE_BASE`: optional custom Edge base.
- Secret `FEED_HMAC_SECRET`: required for external report ingress and used by participating report producers when configured.
- Built-in workflow token: `actions/checkout` persists it for ordinary Git pushes; selected steps explicitly map it as `GITHUB_TOKEN` or `GH_TOKEN` for REST, `gh`, issue, dispatch, and pull-request operations.

The exact ownership and defaults are in [Configuration](../configuration.md). Do not echo tokens, HMAC material, or DSNs during reruns.

## Manual dispatch and rerun

1. Confirm the intended branch, especially for a writer.
2. Inspect the most recent run and any generated commit or deployment before rerunning.
3. Prefer rerunning the failed job/run when inputs and checkout are still correct.
4. Use `workflow_dispatch` only after reviewing its branch behavior and inputs.
5. Reconcile remote history before a second writer push.

`feed-validate.yml` declares `workflow_dispatch`, but neither job currently admits that event. A manual dispatch is therefore a green no-op. Use its implemented push, pull-request-target, or repository-dispatch path instead until the workflow is repaired.

## Watchdogs and freshness checks

Feed watchdog has two schedules: general audit runs and hourly weekday intraday recovery windows. It can attempt a live-branch intraday fallback, write main-branch health, and open a deduplicated stale-feed issue.

OpenClaw watchdog checks for expected dated premarket and close Markdown. It diagnoses missing files, not their analytical correctness or completeness.

Keep-warm skips when `API_BASE` is absent. When configured, its curl failure is swallowed, so a successful workflow run does not prove backend health.

The intraday workflow's producer, push, health, and self-chain failures are best-effort. Scheduled and watchdog runs are part of recovery, but they do not establish a delivery guarantee.

## Failure diagnosis

- `feed-watchdog.yml` runs the audit through `tee` after `set +e` without pipefail. `$?` records `tee`, so a successful `tee` masks a failing `audit_feed.py`; critical audit failures do not currently reliably drive issue creation. Inspect the audit output and `feed/health.json` directly.
- `funds-13f.yml` retries pushes three times but has no final success flag. It can exhaust retries, continue, open an issue, and finish successfully without updating `main`.
- `openclaw-notes.yml` catches per-symbol failures, retries once, prints final failures, and can publish partial or stale coverage with exit zero.
- `openclaw-watchdog.yml` swallows issue-creation failure. Inspect the issue list instead of treating the run result as proof.
- Hyperliquid and several study publishers print a failed `publish_report()` result without exiting nonzero. Alpha `run_routine.py` is the participating writer that propagates failed report validation.
- Daily screener treats watchlist update and some issue creation failures as nonblocking. Daily digest degrades individual data fetch failures but does not swallow every issue API failure.
- Intraday and feed-watchdog live pushes are best-effort. Confirm the `live` branch artifact timestamp and producer field.

For any writer, compare the run's checked-out SHA, resulting commit, remote branch tip, and expected paths. A green workflow is not sufficient when its script intentionally swallows a failure.

## Security and rollback invariants

- Keep workflow permissions scoped to the job's actual reads and writes.
- Preserve pull-request-target isolation: untrusted PR code is data to validation, never shell to execute.
- External report ingress remains fail-closed for missing/invalid HMAC and rejects invalid identifiers, paths, size/count limits, external `routine` kind, and duplicate IDs.
- `FEED_PUBLICATION_MANIFEST` constrains staging only in participating workflows. Do not describe it as validation, atomic reader publication, or rollback.
- Do not add broad `git add feed` behavior to a writer.
- Roll back through a reviewed revert/corrective commit. Recheck any issue or deployment side effect separately.

## Change checklist

- Update the inventory row when a workflow basename, trigger, permissions, concurrency, command, target, or configuration changes.
- Identify the exact feed families and branch a new writer can modify.
- Decide whether the writer participates in the staging ledger or stages explicit paths.
- Add policy tests for exact workflow/job/step structure, not only command substrings.
- Verify branch selection, conflict handling, failure propagation, and rerun behavior.
- Run the workflow security tests and the documentation checker.

## Current limitations

- Different per-workflow concurrency groups do not serialize main-branch writers.
- There is no reader-facing atomic feed snapshot or cross-writer rollback manifest.
- Generated-feed commits excluded by test `paths-ignore` do not receive the general CI gate; Pages also does not rebuild for ordinary feed-only changes.
- Several workflows intentionally or accidentally swallow producer, push, curl, self-dispatch, or issue failures.
- Feed watchdog's pipeline status handling currently masks the audit command's failure.
- Feed validation's manual dispatch is a no-op.
- Legacy explicit-path writers do not receive the staging-ledger boundary.
