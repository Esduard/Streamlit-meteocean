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

- [ ] `calculate_data_freshness_status()` is a pure function, independently testable with no I/O.
- [ ] Boundary behavior is correct at 29/30/31, 59/60/61, and 89/90/91 days old.
- [ ] The "no canonical dataset exists" case produces a distinct, clear "no data available" status.
- [ ] `render_data_freshness_warning()` is wired into the main forecast page and visibly shows gray/yellow/red/no-data states matching the underlying canonical dataset's latest timestamp.
- [ ] The warning is shown regardless of which target variable or model is currently selected.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.latest_canonical_timestamp()`)
