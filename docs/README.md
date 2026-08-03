# Documentation

> **Status:** Current
> **Scope:** Status catalog and navigation for maintained, target, historical, and archived documentation.
> **Last verified commit:** `11beda8696d1b12c037fc2f7465f4a7fae3183a2`

## Start here

- Current implementation authority: [`current-architecture.md`](current-architecture.md)
- Current configuration authority: [`configuration.md`](configuration.md)
- Current deployment authority: [`deployment-matrix.md`](deployment-matrix.md)
- Current workflow authority: [`operations/workflows.md`](operations/workflows.md)
- Current feed-contract authority: [`data-contracts/feed.md`](data-contracts/feed.md)
- Research catalog: [`research/index.md`](research/index.md)
- Accepted target summary: [`rfcs/target-architecture.md`](rfcs/target-architecture.md)
- Full accepted refactor design: [`superpowers/specs/2026-07-16-stock-analysis-refactor-design.md`](superpowers/specs/2026-07-16-stock-analysis-refactor-design.md)
- Repository entry point: [`../README.md`](../README.md)

The current architecture describes what this checkout implements. The target RFC and program design describe accepted migration direction and must not be read as present capability.

## Current system

- [`current-architecture.md`](current-architecture.md) — current runtime variants, data paths, persistence, trust boundaries, and limitations.
- [`../backend/README.md`](../backend/README.md) — optional FastAPI entry points and local runtime notes.
- [`../feed/README.md`](../feed/README.md) — current report-feed conventions and consumer path.
- [`openclaw-integration.md`](openclaw-integration.md) and [`openclaw-stock-notes.md`](openclaw-stock-notes.md) — current external report ingress and stock-note contracts.
- [`deep-research.md`](deep-research.md) — the deterministic deep-research engine, its `feed/research` family, and what a confirmed claim does and does not prove.
- [`../backtest/README.md`](../backtest/README.md) and [`../backtest/FEATURES.md`](../backtest/FEATURES.md) — maintained backtest entry points, capabilities, and recorded limitations.

Subsystem READMEs are useful operational references. When they conflict with the current architecture or source, the verified current architecture and implementation are authoritative.

## Configuration, deployment, operations, and contracts

The maintained operational authorities are:

- [`configuration.md`](configuration.md) — environment variables, secrets, defaults, and ownership.
- [`deployment-matrix.md`](deployment-matrix.md) — static, server, FastAPI, Pages, and Render variants and their current limitations.
- [`operations/workflows.md`](operations/workflows.md) — GitHub Actions triggers, permissions, writers, and recovery.
- [`data-contracts/feed.md`](data-contracts/feed.md) — feed families, producers, consumers, validation, and publication boundaries.
- [`../backend/README.md`](../backend/README.md) — optional backend startup and runtime details.
- [`compliance.md`](compliance.md) — licensing and use constraints.

### Current compatibility routes

These maintained routes preserve former URLs while pointing to current authorities or archived records:

- [`architecture.md`](architecture.md), [`roadmap.md`](roadmap.md), and [`iteration-log.md`](iteration-log.md)
- [`deploy-backend.md`](deploy-backend.md), [`data-model-api.md`](data-model-api.md), [`endpoints.md`](endpoints.md), and [`working-apis.md`](working-apis.md)
- [`need-to-fix.md`](need-to-fix.md) and [`optimization-2026-06.md`](optimization-2026-06.md)
- [`positioning.md`](positioning.md), [`cost-estimate.md`](cost-estimate.md), and [`self-improving-alpha-loop.md`](self-improving-alpha-loop.md)

## Research

- [`research/index.md`](research/index.md) — maintained catalog for research tracks, dated studies, evidence levels, and limitations.
- [`../backtest/README.md`](../backtest/README.md), [`../backtest/README_statarb.md`](../backtest/README_statarb.md), and [`../backtest/README_xs.md`](../backtest/README_xs.md) — major equity research tracks.
- [`../backtest/README_crypto.md`](../backtest/README_crypto.md), [`../backtest/README_crypto_pipeline.md`](../backtest/README_crypto_pipeline.md), and [`../backtest/README_binance.md`](../backtest/README_binance.md) — crypto research tracks.
- [`study-pbo-2026-06-10.md`](study-pbo-2026-06-10.md), [`study-pbo-2026-07-02.md`](study-pbo-2026-07-02.md), [`study-downshift-2026-06-10.md`](study-downshift-2026-06-10.md), and [`study-downshift-2026-07-02.md`](study-downshift-2026-07-02.md) — dated validation snapshots.
- [`study-overnight-gap-2026-06-10.md`](study-overnight-gap-2026-06-10.md), [`study-pit-bite-2026-06-10.md`](study-pit-bite-2026-06-10.md), and [`study-pit-membership-2026-06-10.md`](study-pit-membership-2026-06-10.md) — dated market-structure and point-in-time studies.

Research pages record methods and observations at a particular cutoff. They do not define the current runtime architecture.

## Accepted design and RFCs

- [`rfcs/target-architecture.md`](rfcs/target-architecture.md) — concise accepted target and migration invariants.
- [`superpowers/specs/2026-07-16-stock-analysis-refactor-design.md`](superpowers/specs/2026-07-16-stock-analysis-refactor-design.md) — full accepted program design.
- [`superpowers/plans/2026-07-16-stage-1a-feed-security.md`](superpowers/plans/2026-07-16-stage-1a-feed-security.md) — accepted Stage 1A implementation plan.
- [`superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md`](superpowers/plans/2026-07-16-stage-1b-reproducible-ci.md) — accepted Stage 1B implementation plan.
- [`superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md`](superpowers/plans/2026-07-16-stage-1c-truth-first-docs.md) — accepted Stage 1C implementation plan.

Accepted design records decisions. A component becomes current only after implementation, verification, and a corresponding current-document update.

## Historical snapshots

The following pages preserve useful pre-refactor context but are not current architecture authorities:

- [`hyperliquid-integration.md`](hyperliquid-integration.md) and [`survivorship-bias-data-sources.md`](survivorship-bias-data-sources.md)
- [`../research/ai-agents-skills-market-scan.md`](../research/ai-agents-skills-market-scan.md) and [`../research/quant-factor-deep-research.md`](../research/quant-factor-deep-research.md)
- The dated studies and historical `backtest/README*.md` pages cataloged in [`research/index.md`](research/index.md)

Treat dates, external availability, costs, and deployment observations in these snapshots as time-bound.

## Archived pre-refactor material

- [`archive/iteration-log.md`](archive/iteration-log.md) — preserved continuous-development record.
- [`archive/pre-refactor/roadmap.md`](archive/pre-refactor/roadmap.md) — superseded roadmap preserved for provenance.

Archived pages are not maintained and must not be used as current implementation guidance.

## Documentation maintenance rules

1. Maintained documents declare an exact `Status`, a non-empty `Scope`, and a stamped `Last verified commit`.
2. Current claims must be traceable to repository code, configuration, tests, or workflows at the stamped commit.
3. Target components and migrations are labeled **Accepted** or **Planned**, never presented as implemented.
4. Historical and archived pages retain their original record; current replacements live in maintained documents.
5. Run `scripts/run-python311 python scripts/check_docs.py` after changing maintained documentation or the verification manifest.
