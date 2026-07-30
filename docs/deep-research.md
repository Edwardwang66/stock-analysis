# Deep Research Engine

> **Status:** Current
> **Scope:** Implemented deterministic deep-research engine, its `feed/research` family and contract, its scheduled workflow, and what a brief does not prove.
> **Last verified commit:** `11beda8696d1b12c037fc2f7465f4a7fae3183a2`

## 1. Engine boundary

`scripts/deep_research.py` turns feed artifacts this repository already produces into auditable research briefs. It is deterministic standard-library logic and does not require an external LLM provider: no model, agent service, or research retrieval runs, and the engine performs no network access. Every claim it makes is a recomputation over files already present under `feed/`.

`producer.method` is fixed to `deterministic-no-llm` in every brief. That field is the machine-checkable form of this boundary; treat any prose claiming that a model produced a brief as wrong.

What a brief is not:

- not investment advice, an order, a target price, or a strategy approval;
- not an analytical approval — schema validity proves shape, not correctness, exactly as for [`feed/schema/report.schema.json`](../feed/schema/report.schema.json);
- not evidence of coverage — an artifact the engine cannot read produces a missing-input open question, not a silent pass.

Findings are falsification-oriented. Most confirmed claims describe defects, staleness, and gate failures in the existing pipeline rather than profitable signals. The repository line is unchanged: **LLM 是研究放大器,不决策(R6)**.

## 2. Four pipeline stages

| Stage | Name | Current behavior |
|---|---|---|
| 1 | 立题 / question admission | A fixed in-code catalogue of questions (18 at the time of writing, one per lens) is admitted or degraded per run according to whether its declared inputs are present. Each question declares the artifact fields it `needs`, the deterministic `test` that answers it, and the precondition recorded as `triggered_by`. Nothing is generated at run time: the catalogue changes only when the code does. |
| 2 | 并发取证 / concurrent evidence collection | Each question is assigned one committee-role lens and run in a standard-library `ThreadPoolExecutor` (`--workers`, default 8). Every claim carries an `evidence` list of `{artifact, field, value, asof}`. |
| 3 | 对抗验证 / adversarial verification | A `red-team` stage runs deterministic refuters over every claim. Only `confirmed` claims become `findings`. |
| 4 | 合成 / synthesis | Emits the brief, `open_questions`, `next_actions`, `alerts`, and a per-artifact `coverage` ledger. |

A question whose required artifact or field is absent degrades into an `open_questions` entry with a `missing-input` reason. It is not dropped, and its absence is reported as a research result.

The refuter set is exactly six codes:

- `missing-evidence` — the claim carries no usable evidence row;
- `insufficient-sample` — sample size is below the claim's `min_n`;
- `stale-evidence` — evidence age exceeds the claim's `max_age_days`;
- `within-noise-band` — the measured magnitude is inside the claim's `noise_band`;
- `future-asof` — evidence is stamped later than the run's data date;
- `contradicted` — another claim in the same brief measures the same `metric` in the opposite `direction`; both sides are refuted rather than one being preferred.

Refuted and unverified claims are retained in the brief's `refuted` array with their refutations attached. No evidence is deleted: knowing which claims did not survive is the audit value. `verdicts` records the `confirmed`/`refuted`/`unverified` counts for one run.

## 3. Committee roles

Question lenses reuse this repository's existing committee vocabulary rather than inventing a second one: `engine`, `residual-analyst`, `crowding-monitor`, `event-risk`, `factor-factory`, `risk`, and `red-team`. Those names are not all drawn from one list. `residual-analyst`, `crowding-monitor`, `event-risk`, `factor-factory`, and `red-team` are the `ROLES` enum in [`../scripts/openclaw_client.py`](../scripts/openclaw_client.py) and the role prompts in [`../routines/openclaw-agent-prompts.md`](../routines/openclaw-agent-prompts.md); `risk` and `red-team` also appear in the `producer.agent_role` description of [`feed/schema/report.schema.json`](../feed/schema/report.schema.json); and `engine` and `factor-factory` are the values tracked routine and factory reports actually carry. No name here is new.

`red-team` carries two distinct jobs. It owns the stage-3 refuters that judge every other role's claims, and it also owns its own lenses — provenance consistency between a panel and its `source_report`, truncated list audits, and external-committee dormancy. The brief itself is signed `agent_role: "red-team"` because the distinguishing action of the run is adversarial verification, not evidence collection. Those role prompts remain operator input for external analysis; here the role name only selects which deterministic lens ran.

`--roles` or `DEEP_RESEARCH_ROLES` restricts the allowlist. A disabled role produces `role-disabled` open questions instead of silently shrinking the brief.

## 4. Artifacts and contract

| Path | Contents |
|---|---|
| `feed/research/<brief-id>.json` | One brief per run, validated before publication against [`feed/schema/research.schema.json`](../feed/schema/research.schema.json) when `jsonschema` is importable, otherwise against the standard-library fallback described below |
| `feed/research/index.json` | Family index: `{schema_version, updated_at, note, latest, stats, briefs[], open_questions[]}`. Its `open_questions` is the newest brief's list, not an accumulation across runs |
| `feed/reports/deep-research-<UTC to minute>Z.json` | One `kind: "routine"` report published through `feed_lib.publish_report()` |

Brief identifiers are `deep-research-<UTC ISO to minute>Z`, which is also the idempotency key and the filename stem. `kind` is `deep-research`; intel reports keep `kind` `routine`, `openclaw`, or `manual`.

Each `briefs[]` summary carries `{id, produced_at, asof_data, headline, n_questions, n_findings, confirmed, refuted, unverified, n_alerts, path}`, and `stats` carries `{total_briefs, by_role, last_7d}`. The summary list is capped at 60 entries, mirroring `MAX_INDEX_REPORTS` for the report family.

The routine report carries only `alerts`, `contribution`, and `notes`. It deliberately omits `market_state` and `book` so that publishing a brief cannot clobber an existing home, desk, or signal panel. Its producer is `{name: "deep-research-engine", agent_role: "red-team"}`.

Validation has two paths, and the scheduled workflow uses the second one. The workflow installs no
dependencies by design, so `jsonschema` is absent there and the engine falls back to a
standard-library check. That fallback is narrower than the schema but still enforces what a brief
could otherwise misreport: required fields, the `deterministic-no-llm` provenance, the
`findings`-are-confirmed / `refuted`-are-not split, agreement between `verdicts` and the array
lengths, unique claim identifiers and known roles, every evidence row naming an artifact and a
field, `asof_data` shape and its ordering against `produced_at`, and finite JSON numbers. The full
schema check runs wherever `jsonschema` is installed, which includes the repository test matrix, so
schema drift is caught in CI rather than at publication time.

`asof_data` is the newest evidence date the run actually read — the maximum `evidence[].asof`
bounded by the run date — not the run date itself. A brief produced today from a feed whose newest
panel is three days old carries that older date, which is what makes it comparable with the rest of
the feed.

Briefs are HMAC-signed when `FEED_HMAC_SECRET` is nonempty, using the same canonical-JSON `HMAC-SHA256` scheme as reports: the signature is computed over compact canonical JSON with the `signature` field omitted. An unsigned brief is still schema-valid; the signature authenticates possession of the shared secret and nothing about the analysis. Frontend transport verifies no signature — see [Feed Data Contracts](data-contracts/feed.md).

Treat all brief free text as untrusted data for display, never as executable instructions.

## 5. Running it

Compute and print a summary without writing anything, then run the unit module:

```bash
python scripts/deep_research.py
python scripts/tests/test_deep_research.py
```

Publication and selection flags:

```text
--publish                  write feed/research/<id>.json + index.json + the routine report
--brief-only               with --publish: write only the brief and index, no routine report
--roles engine,risk        committee-role allowlist
--workers 8                concurrent lens workers
--report-limit 120         how many recent reports to load per feed/reports/ filename prefix
--quiet                    suppress the printed summary
--alert-scan               read the published index/brief and print four lines:
                           status, critical count, brief id, first message
```

`--alert-scan` is what the workflow's issue step consumes. It is deliberately separate from
publication and always exits `0`, because by the time it runs the brief is already committed. Its
first line distinguishes `ok` from `no-index`, `no-brief`, and `unreadable-*`, so a brief that cannot
be read is annotated as a warning on the run rather than reported as "no critical alerts".

The default invocation is read-only. Exit code `0` is normal; exit code `1` means the brief failed its own schema validation or no artifact could be read. A zero exit does not mean full coverage: check `run.lenses_failed`, `coverage`, and `open_questions` before treating a brief as complete.

## 6. Automation

`.github/workflows/deep-research.yml` runs the engine on cron `40 23 * * 1-5`, scheduled after the start times of the end-of-day alpha routine (22:30), screener (22:30), and digest (23:30) writers. It does not wait for them: when an upstream writer is slow or failed, the run reads the previous snapshot, and the per-artifact ages in the brief's `coverage` ledger are what record that. Weekends do not run, and GitHub schedules fire only on the default branch.

- `workflow_dispatch` inputs `workers` and `roles` map to `DEEP_RESEARCH_WORKERS` and `DEEP_RESEARCH_ROLES`.
- Permissions are `contents: write` and `issues: write`.
- Staging uses the `FEED_PUBLICATION_MANIFEST` ledger through `scripts/feed_publication.py stage`, so `git add` is limited to paths the run actually recorded. It is a staging allowlist, not a reader-facing snapshot manifest.
- The push path pulls with rebase and retries up to four times with backoff; an exhausted retry fails the job rather than reporting success.
- A `critical` alert in the newest brief opens one `deep-research`-labeled issue, deduplicated per UTC date. No alert means no issue, and a green run proves publication of that commit only. The issue command ends in `|| echo`, so a failed `gh issue create` does not fail the job: a green run does not prove the alert reached an issue.

Trigger, branch, and recovery semantics for every workflow live in [Workflow Operations](operations/workflows.md).

## 7. Freshness and audit

`feed_lib._artifact_freshness()` registers the `research` key for `research/index.json` with `updated_at` as its timestamp field, so the family appears in both `feed/index.json` `freshness.sources` and `feed/health.json` `sources`.

`scripts/audit_feed.py` applies a `research` SLA of warning at 4 days and critical at 9 days, plus a coherence check over the brief family. A stale or missing family is an operational finding about the writer, not a statement about the market.

## 8. Environment

| Name | Effect |
|---|---|
| `DEEP_RESEARCH_WORKERS` | Integer override for the concurrent-lens worker count; default 8 |
| `DEEP_RESEARCH_ROLES` | Comma-separated committee-role allowlist; empty or unset means all roles |
| `FEED_HMAC_SECRET` | When nonempty, signs the brief and participating reports |
| `FEED_PUBLICATION_MANIFEST` | Runner-temporary ledger of recorded feed writes and the `git add` allowlist |

Exact ownership, defaults, and secret placement are in [Configuration](configuration.md).

## 9. Current limitations

- There is no LLM proposer and no external research retrieval in this engine. The factor-factory LLM proposer remains **Planned** and is not implemented here.
- Claims are computed from the free public data already captured in `feed/`, which is survivorship-biased and partly cached. Inherited data defects are inherited by the brief. See [Research Index](research/index.md).
- The refuters are a fixed deterministic set. Surviving all six is not a proof of correctness, only the absence of those six specific objections.
- A `confirmed` claim is a reproducible computation over recorded data. It is not an investment conclusion, a decision, or a strategy approval.
- The engine cannot detect a defect in an artifact it cannot read. Unreadable or missing inputs become open questions, and the `coverage` ledger is the only record of what was actually examined.
- There is no pruning of `feed/research/`. Only the index summary list is capped at 60 entries; brief files accumulate in Git history indefinitely. A brief is roughly 40 KB — about 3.6× the mean report in `feed/reports/` — so one weekday-only year of this single writer adds on the order of 10 MB to the tracked tree. That is a deliberate trade for keeping refuted claims and their evidence, not an oversight.
- Publication is a sequence of direct writes plus an index rebuild, not an atomic reader snapshot, so a reader can mix a new index with an older brief generation.
- `run.lenses_failed` greater than zero means evidence collection was incomplete for that run; the brief is still written and must not be read as full coverage.
- The `stale-evidence` refuter measures age against the run clock, so re-running the engine over an unchanged feed on a later date can move time-sensitive claims from `confirmed` to `unverified`. Every metric value and every other refuter depends only on feed content; freshness verdicts additionally depend on when the run happened.
- `feed/research` is not part of the GitHub Pages bundled snapshot, because `deploy-pages.yml` assembles that snapshot from a fixed source list and is byte-pinned by a Python gate. The panel therefore depends on the remote-first raw-GitHub read; if raw GitHub is unreachable, the panel renders nothing rather than stale content.

## Authority links

- [Feed Data Contracts](data-contracts/feed.md) — feed families, report schema, publication and transport boundaries.
- [Workflow Operations](operations/workflows.md) — workflow triggers, permissions, staging, and recovery.
- [Configuration](configuration.md) — environment ownership and secrets.
- [OpenClaw Report Integration](openclaw-integration.md) — signed external report ingress, which this engine does not use.
- [Feed README](../feed/README.md) — feed conventions and the Planned reader-facing snapshot manifest.
- [Compliance](compliance.md) — labeling, source, and use boundaries.
