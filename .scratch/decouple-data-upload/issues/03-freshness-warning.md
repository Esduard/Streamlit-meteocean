# Freshness warning on the main forecast page

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

A pure freshness-status function plus a small render helper, wired into the main forecast page, showing how stale the canonical dataset is.

`calculate_data_freshness_status(latest_timestamp, now)` is a pure function (no I/O) that maps a latest-timestamp (or `None`, if no canonical dataset exists yet) to a status/severity using configurable day thresholds:

```python
STALE_DATA_DAYS_GRAY = 30
STALE_DATA_DAYS_YELLOW = 60
STALE_DATA_DAYS_RED = 90
```

| Condition                                 | Status               | UI Severity    |
| ------------------------------------------ | --------------------- | --------------- |
| No canonical dataset exists                | Missing data warning | Gray            |
| Latest timestamp less than 30 days old     | OK                    | Normal / green  |
| 30 days or more without new data           | Stale data warning    | Gray            |
| 60 days or more without new data           | Medium warning        | Yellow          |
| 90 days or more without new data           | Critical warning      | Red             |

`render_data_freshness_warning()` reads `UploadedDataStore.latest_canonical_timestamp()`, calls the status function, and renders the appropriate message/severity on the main forecast page (e.g. above or near the model-selection controls), independent of which model or target variable is selected.

## Acceptance criteria

- [x] `calculate_data_freshness_status()` is a pure function, independently testable with no I/O.
- [x] Boundary behavior is correct at 29/30/31, 59/60/61, and 89/90/91 days old.
- [x] The "no canonical dataset exists" case produces a distinct, clear "no data available" status.
- [x] `render_data_freshness_warning()` is wired into the main forecast page and visibly shows gray/yellow/red/no-data states matching the underlying canonical dataset's latest timestamp.
- [x] The warning is shown regardless of which target variable or model is currently selected.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.latest_canonical_timestamp()`) — done, unblocked.

## Comments

**2026-06-24 — Implemented.**

- New module `streamlitapp/src/meteocean_forecast/domain/freshness.py`: `STALE_DATA_DAYS_GRAY/YELLOW/RED` constants, `FreshnessSeverity` enum (`OK`, `NO_DATA`, `GRAY`, `YELLOW`, `RED`), a frozen `FreshnessStatus` dataclass (severity + message + `age_days`), the pure `calculate_data_freshness_status(latest_timestamp, now)`, and the I/O-performing `render_data_freshness_warning()` (constructs `UploadedDataStore(path_utils.get_app_data_dir())`, calls `latest_canonical_timestamp()` + `datetime.now()`, renders `st.error`/`st.warning`/`st.info`/`st.caption` per severity — unobtrusive, never blocks the page).
- Threshold boundaries are inclusive at the lower bound of each tier (29d → OK, 30d → gray, 59d → gray, 60d → yellow, 89d → yellow, 90d → red), matching the issue's table.
- Built as a standalone module first (no page wiring) to avoid a concurrent-edit conflict with issue 04, which was touching the same shared `_page_template.py` at the same time. Wired in immediately after both were done: `render_data_freshness_warning()` is called at the top of `render_forecast_page()` in `streamlitapp/app/_page_template.py`, right after the page title and before model selection — so it renders identically regardless of which target variable or model is selected, and before any exogenous/univariate branching.
- Tests: `tests/test_freshness_status.py` covers the `None` case, fresh/OK case, the full 29/30/31/59/60/61/89/90/91 boundary matrix (parametrized), and that `age_days` is reported correctly. All pure-function, no I/O, no Streamlit dependency in the test.
- Full suite green (85 tests); `ruff check` clean.
