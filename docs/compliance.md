# Compliance

> **Status:** Current
> **Scope:** Personal research, self-hosting, disclosure, licensing, secret-handling, and use boundaries.
> **Last verified commit:** `8cff75b8e31d6b3a07a9d6198e0bc54bcb3b594a`

## Personal research and self-hosting

This repository is scoped to personal market research, experimentation, and self-hosting. Repository availability and implemented routes do not establish permission to operate a public data redistribution service or regulated financial product.

## Upstream licensing and redistribution

Market data, filings, news, fund holdings, model outputs, libraries, and other upstream material remain subject to their providers' terms and licenses. Provider metadata in code or documentation is descriptive; the current router does not enforce licensing or redistribution policy.

The repository has no tracked top-level `LICENSE`, `COPYING`, or `NOTICE`, and the frontend package declares no license field. Do not infer an open-source or commercial redistribution grant from source availability. Review the project code, every dependency, and every upstream data source independently before redistributing any part of the system or its outputs.

## Estimation and latency disclosure

Displayed values can be delayed, estimated, cached, incomplete, or provider-dependent:

- quote fallback can use a persisted value no older than ten minutes, only after a fetch throws;
- OHLCV fallback can use a persisted series no older than 24 hours, only after a fetch throws;
- raw and bundled feed artifacts can come from different generations;
- public CORS proxies and free provider endpoints can fail, throttle, change, or return incomplete data;
- money-flow, chip, factor, signal, and similar derived fields are calculations or proxies, not exchange-certified observations.

Interfaces and exported artifacts should retain source, timestamp, data-as-of, producer, and estimation labels when available. A green health check or workflow does not remove these limitations.

## AI artifact labeling

Artifacts produced or materially transformed by a model should identify the producer, model/provenance label when known, run link when available, generation time, data-as-of date, and any review status.

Do not label every file under `stock-notes/` or every workflow output as AI-generated. The scheduled OpenClaw-notes workflow currently uses deterministic market-data and filing logic while preserving a producer/model provenance label. Deterministic indicators and schema-valid reports are also not evidence of human review, analytical approval, or investment suitability.

## Secret handling

Operators are responsible for protecting tokens, HMAC material, and database credentials.

- Use a secret manager or GitHub Secrets for `FEED_HMAC_SECRET`, repository tokens, and `WINTER_PG_DSN`.
- Never place credentials in `NEXT_PUBLIC_*` variables, committed examples, issue bodies, or logs.
- The root `.gitignore` does not provide a general `.env` exclusion. `frontend/.gitignore` covers only its local environment-file pattern. Check the exact path before creating any credential file.
- Scope remote-write tokens to the selected repository and operation.

The current Edge and FastAPI HTTP routes have no user authentication or application rate limiting. Feed-ingress HMAC does not protect those routes.

## Non-investment-advice statement

Repository code, reports, notes, screeners, alerts, backtests, and visualizations are research artifacts and not investment, legal, tax, accounting, or brokerage advice. Users remain responsible for independent verification, risk controls, execution decisions, and professional advice where appropriate.

## Commercial use

Commercial use requires independent legal review and independent review of project, dependency, market-data, filing, news, model, and redistribution licenses. This document does not make jurisdiction-specific legal conclusions or grant rights held by third parties.
