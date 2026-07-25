# Backtest and Research

> **Status:** Current
> **Scope:** Installation, entry points, outputs, and limitations for the Python research subsystem.
> **Last verified commit:** `9d3e39fd8c75d2ea18f6879dc7d74ddbd5efcfd2`

## Scope

This directory contains executable research code for US equities, statistical arbitrage, crypto factors, point-in-time membership experiments, and dated study generation. It is not a production trading engine. The current code entry points are listed below; measured results remain in historical result snapshots and are not repeated here.

## Requirements and installation

The repository runtime contract is Python `3.11.15`. Create an environment with that exact interpreter and install the hash-locked research dependencies from the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backtest/requirements.txt
.venv/bin/python --version
```

The final command must report `Python 3.11.15`. `backtest/requirements.in` is the editable dependency source; `backtest/requirements.txt` is the installation and CI lock. Scripts that publish feed artifacts are run by automation with `requirements/automation.txt`, but direct research execution uses the backtest lock.

## Data and cache boundaries

- A clean checkout has no market-data cache. `data.py`, `cryptodata.py`, and `binancedata.py` require public network services before their analyzers can run.
- Yahoo data is stored in ignored `backtest/data_cache/`. Hyperliquid and Binance data are stored in ignored `backtest/crypto_cache/` and `backtest/binance_cache/`.
- Every `cryptodata.py` and `binancedata.py` CLI run live-selects liquidity and rewrites tracked `crypto_universe.json` or `binance_universe.json`. Existing per-symbol cache files are then reused indefinitely; only missing files are fetched. The CLIs expose no force flag, so delete the relevant cache files or call the fetch functions programmatically with `force=True` to refresh them. `pit_membership.py` and `study_downshift.py` can also rewrite tracked universe snapshots. Review those diffs rather than treating a refresh as disposable cache.
- Cache-only analyzers do not silently reproduce their historical result pages. Most print to stdout. `run.py` overwrites tracked `results/backtest_report.json`; dated study scripts write or overwrite `docs/study-<name>-<date>.md`.
- `--publish` is an explicit additional write to `feed/`. It is not needed for research reproduction.

## Entry-point matrix

All tracked Python files in this directory with a `__main__` entry point are included. “Cache-only” means the script itself does not fetch missing inputs.

| Script | Method | Network and cache boundary | Output or result document | Strongest known limitation |
|---|---|---|---|---|
| [`barrier.py`](barrier.py) | TQM triple-barrier label demonstration | Cache-only; requires Yahoo equity cache | Stdout; historical [`README_tqm.md`](README_tqm.md) | Demonstrates label sensitivity, not execution-grade P&L; exact intraday barrier fills and costs are not modeled. |
| [`binance_pipeline.py`](binance_pipeline.py) | Binance cross-sectional factor pipeline with a calendar split | Cache-only; requires tracked universe and ignored Binance caches | Stdout; historical [`README_binance.md`](README_binance.md) | Uses a current-listed universe, treats a fixed crypto-calendar cadence as “monthly,” and annualizes with a trading-day convention. |
| [`binancedata.py`](binancedata.py) | Binance market and funding loader | Every CLI run live-selects and rewrites the tracked universe; existing ignored cache files are reused indefinitely and only missing files use live mirror/ZIP endpoints. Delete files or call `fetch_klines(..., force=True)` and `fetch_funding(..., force=True)` to refresh | Cache producer; historical [`README_binance.md`](README_binance.md) | Current-volume/current-listed selection creates future-membership and survivorship bias; a newly selected universe can be paired with stale per-symbol caches, and missing funding downloads can be skipped. |
| [`crypto_backtest.py`](crypto_backtest.py) | Hyperliquid factor Rank-IC and Ridge evaluation | Cache-only; requires tracked universe and ignored Hyperliquid caches | Stdout; historical [`README_crypto.md`](README_crypto.md) | Its fixed rebalance-step embargo is not horizon-aware, so long-horizon Ridge labels are not strictly purged. |
| [`crypto_pipeline.py`](crypto_pipeline.py) | Neutralized Hyperliquid factor pipeline | Cache-only; requires tracked universe and ignored Hyperliquid caches | Stdout; historical [`README_crypto_pipeline.md`](README_crypto_pipeline.md) | Selects the factor on the full sample before displaying the final weeks; that block is not an independent holdout. |
| [`crypto_pnl.py`](crypto_pnl.py) | Hyperliquid factor portfolios and Ridge P&L diagnostic | Cache-only; requires tracked universe and ignored Hyperliquid caches | Stdout; historical [`README_crypto.md`](README_crypto.md) | Shares the non-horizon-aware purge boundary and does not model trading costs. |
| [`cryptodata.py`](cryptodata.py) | Hyperliquid candles and funding loader | Every CLI run live-selects and rewrites the tracked universe; existing ignored cache files are reused indefinitely and only missing files use live APIs. Delete files or call `fetch_candles(..., force=True)` and `fetch_funding(..., force=True)` to refresh | Cache producer; historical [`README_crypto.md`](README_crypto.md) and [`README_crypto_pipeline.md`](README_crypto_pipeline.md) | A live-selected universe can be paired with stale per-symbol caches; short, drifting history also prevents byte-for-byte reproduction of old snapshots. |
| [`data.py`](data.py) | Yahoo daily OHLCV acquisition | Uses Yahoo network; writes ignored equity cache | Cache producer; consumers are cataloged below | Unofficial provider/current-symbol availability; its default universe fetch omits the sector ETFs needed by `statarb.py`. |
| [`experiment_regime.py`](experiment_regime.py) | TQM regime and threshold sensitivity | Cache-only; requires equity and SPY caches | Stdout; historical [`README_tqm.md`](README_tqm.md) | Post-hoc sensitivity demonstration, not a held-out strategy estimate. |
| [`factor_factory.py`](factor_factory.py) | Deterministic formula-candidate factory with statistical and cost gates | Cache-only; the workflow prefetches equity prices, the SPY benchmark, and sector ETFs. PIT is read from tracked `pit_sp500.json`, is not refreshed automatically, and a missing/invalid file causes the filter to be skipped after a warning | Stdout; optional feed report; no dedicated Markdown result | The breadth gate is explicitly unimplemented, the split is retrospective, and a missing/stale PIT snapshot weakens membership filtering without stopping the run. |
| [`factor_pipeline.py`](factor_pipeline.py) | Neutralized equity factor IC, layers, and moving holdout | Cache-only; requires equity, sector map, and SPY caches | Stdout; historical [`README_pipeline.md`](README_pipeline.md) | The displayed rolling reconstruction overlaps the factor-selection sample except for the final moving month; it is not an independent multi-month OOS test. |
| [`pit_membership.py`](pit_membership.py) | S&P membership reconstruction and missing-price estimate | Reuses tracked `pit_sp500.json` by default; Wikipedia refresh and Yahoo availability checks use network/cache | Writes a dated study; historical [`study-pit-membership-2026-06-10.md`](../docs/study-pit-membership-2026-06-10.md) | Yahoo/provider failures are counted like unavailable securities, and membership history cannot restore delisted prices. |
| [`run.py`](run.py) | TQM multi-horizon threshold evaluation | Cache-only; requires equity and SPY caches | Overwrites [`results/backtest_report.json`](results/backtest_report.json); historical [`README_tqm.md`](README_tqm.md) | Evaluation is in-sample on current survivors, omits costs, and the JSON has no generation time or data cutoff. The real CLI option is `--horizons` (plural). |
| [`statarb.py`](statarb.py) | Residual/OU statistical arbitrage with modeled costs | Cache-only. From the repository root, prefetch with `cd backtest && ../.venv/bin/python -c "import data,statarb as sa; data.fetch_universe(sa.DEMO_UNIVERSE+sa.SECTOR_ETFS+['SPY'])"` | Stdout; historical [`README_statarb.md`](README_statarb.md) | The post-2025 split was chosen retrospectively; borrow/locate is absent and costs are modeled rather than realized. The code's `build_demo_cache()` hint names no real function. |
| [`study_downshift.py`](study_downshift.py) | Large-cap versus sampled current-small-cap statarb comparison | Uses tracked S&P sample plus Yahoo; fetches small caps, sector ETFs, and SPY but assumes large-universe caches already exist | Writes dated studies; historical [`2026-06-10`](../docs/study-downshift-2026-06-10.md) and [`2026-07-02`](../docs/study-downshift-2026-07-02.md) | The standalone fresh-checkout command is incomplete without a separate large-universe prefetch; survivorship and borrow costs remain. |
| [`study_overnight_gap.py`](study_overnight_gap.py) | HIP-3 overnight proxy information study | Always uses live Hyperliquid data plus Yahoo cache/network; raw Hyperliquid inputs are not frozen | Writes a dated study; historical [`2026-06-10`](../docs/study-overnight-gap-2026-06-10.md) | Proxy agreement is not forward tradable alpha; the short, drifting sample can complete with partial pairs. |
| [`study_pbo.py`](study_pbo.py) | Stat-arb parameter grid and CSCV-PBO | Cache-only; requires prefetched large-universe, sector ETF, and SPY caches | Writes dated studies; historical [`2026-06-10`](../docs/study-pbo-2026-06-10.md) and [`2026-07-02`](../docs/study-pbo-2026-07-02.md) | CSCV consumes the full series including the nominal retrospective holdout and measures only this declared grid, not all project trials. |
| [`study_pit_bite.py`](study_pit_bite.py) | PIT-on/off factor-factory comparison | Uses tracked PIT/universe inputs and Yahoo cache or network | Writes a dated study; historical [`2026-06-10`](../docs/study-pit-bite-2026-06-10.md) | Applies S&P membership to the entire S&P-plus-NDX union, so the comparison also removes NDX-only names; delisted history remains absent. |
| [`walkforward.py`](walkforward.py) | Annual TQM grid and logistic-regression time splits with embargo | Cache-only; requires equity cache | Stdout; historical [`README_tqm.md`](README_tqm.md) | Chronological folds are retrospective research on current survivors, not an untouched prospective test. |
| [`xs_backtest.py`](xs_backtest.py) | Equity cross-sectional Rank-IC, layers, and rolling-IC composite | Cache-only; requires equity and SPY caches | Stdout; historical [`README_xs.md`](README_xs.md) | Single-factor and equal-composite tables are full-sample in-sample; only the rolling-IC weights are past-only. |
| [`xs_portfolio.py`](xs_portfolio.py) | Equity decile long-short P&L | Cache-only; requires equity and SPY caches | Stdout; historical [`README_xs.md`](README_xs.md) | Gross/cost-free; turnover compares row indices rather than ticker identities, and ranking and execution both use the rebalance close. |

Files without `__main__`—`costs.py`, `engine.py`, `factors.py`, `factors_xs.py`, `crypto_factors.py`, and `validation.py`—are imported helpers, not standalone entry points.

## Outputs

Historical Markdown pages are evidence snapshots, not automatically generated current truth. The loader and study commands can modify tracked universe, report, documentation, or feed paths in addition to ignored caches. Before keeping any generated output, inspect `git status`, record the input data cutoff and provider, and confirm that unrelated tracked snapshots did not change.

## Minimal offline verification

The following checks syntax and the tracked JSON result shape without importing dependencies, reading caches, using the network, or regenerating results:

```bash
.venv/bin/python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('backtest').glob('*.py')]"
.venv/bin/python -c "import json,pathlib; json.loads(pathlib.Path('backtest/results/backtest_report.json').read_text(encoding='utf-8'))"
```

This is only an offline integrity check. It does not validate numerical results or reproduce a historical study.

## Research catalog

Use the maintained [Research Index](../docs/research/index.md) to find executable methods, dated result pages, and the strongest known methodological limitation for each study family. The former feature inventory is preserved only for provenance at [the archived pre-refactor page](../docs/archive/pre-refactor/backtest-features.md).

## Reproducibility rules

1. Record the Git commit, exact Python version, hash-locked requirements, command, arguments, provider, data cutoff, tracked universe files, and cache provenance.
2. Treat live-loader output as a new dataset. Do not compare a rerun to a historical page as if inputs were frozen.
3. Treat “holdout” labels as method descriptions, not proof of prospective isolation. Several splits were selected after their dates existed, and some displayed windows overlap factor selection.
4. A dated study script can overwrite the same-day document or create a new unclassified path. Review the body, add historical metadata, and register a new path in `docs/verification.json` before committing it.
5. Run without `--publish` unless a feed write is explicitly intended and separately reviewed.

## Known limitations

- Equity and crypto universes are primarily current constituents or current liquid listings, so survivorship and future-membership bias remain.
- Free providers do not supply complete delisted histories, point-in-time fundamentals, borrow availability, or execution-quality fills.
- Results depend on ignored local caches and live external services; the repository does not retain immutable raw inputs for every study.
- Crypto loader CLIs refresh the tracked universe but reuse existing per-symbol caches indefinitely; refresh caches explicitly before claiming a new data cutoff.
- Some historical claims use stronger OOS or purge language than current code supports. Historical metadata preserves those claims as snapshots rather than current guarantees.
- Research outputs are not investment advice and are not evidence of production readiness.
