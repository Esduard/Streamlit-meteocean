# ADR-0002: Exogenous forecasting reads from a persisted canonical dataset, not per-run uploads

**Status:** Decided

## Context

Previously, file upload was gated by model type: selecting an exogenous model revealed a file uploader on the forecast page, and that single in-memory upload both fed `engineer_features()` for that run and determined the maximum forecast horizon. Univariate models had no upload at all.

This coupling is being removed (see `docs/development_track/decouple_data_2026_06_24.md`). Data upload becomes an independent, persistent feature: users upload `.xlsx` files (one per platform/`plat_id`) over time, and exogenous models calculate their required variables from whatever data is currently available, rather than from a single upload made immediately before running a forecast.

Each upload covers exactly one platform. Multiple platforms can report the same hour, and the app has no fixed roster of platforms — they're discovered dynamically from whatever `plat_id` values appear in uploads. Users may upload all of a day's platforms together or one at a time, in any order, including re-uploading a platform's data for an hour that's already been ingested.

## Decision

Maintain a **canonical dataset**: a single, continuously-growing hourly table, shared across all three target variables (current_speed, wave_height, wind_speed), since one uploaded file already carries the raw columns needed for all three. When multiple platforms report the same hourly timestamp, the canonical dataset stores the average across those platforms for that timestamp.

The canonical dataset is *derived*, not mutated in place. The source of truth is a **staging table** of raw per-`(plat_id, time)` rows, deduplicated last-write-wins (a re-upload of the same platform/hour overwrites the prior value). The canonical dataset is recomputed from staging — grouped by `time`, averaged across platforms — every time new data lands. This avoids the correctness bug of blending a new platform into an already-averaged value without knowing how many platforms originally contributed.

Original uploaded `.xlsx` files are **not retained** (too large to keep indefinitely). Each upload is recorded in a lightweight upload log (filename, `plat_id`, days/timestamps covered, uploaded time) for audit purposes only — it is not re-read at runtime.

Because the upload log and staging table both assume one uploaded file belongs to exactly one platform, ingestion validates that every row in an uploaded file shares the same `plat_id` and rejects the file with a clear error if it contains more than one.

Both the staging table and the canonical dataset are stored as Parquet under a new `app_data/` directory, resolved via a new `get_app_data_dir()` helper in `path_utils.py` (same pattern as the existing `get_models_dir()` / `get_logs_dir()`, portable across dev mode and the PyInstaller executable).

The Data Upload page's file uploader accepts multiple files at once, to encourage uploading a day's platforms together — but the staging/canonical design makes uploading them separately equally correct, just eventually consistent as each arrives.

## Consequences

- The forecast page (`_page_template.py`) no longer renders its own file uploader for exogenous models. It reads the canonical dataset directly and runs `engineer_features()` against it at forecast time. If the canonical dataset doesn't exist yet, the page shows a message directing the user to the Data Upload page instead of blocking on an inline upload.
- The maximum exogenous forecast horizon is now driven by the canonical dataset's latest timestamp, not by a per-run upload.
- Freshness warnings (30/60/90-day thresholds) are based on the canonical dataset's overall `max(time)` across all platforms combined, not per-platform. There is no fixed platform roster in v1, so "platform X hasn't reported" cannot be detected or surfaced — only "the combined dataset is N days stale."
- Re-uploading a platform's data for a previously-ingested hour silently overwrites that platform's contribution to the average for that hour; there's no versioning or conflict UI.
- Univariate models are unaffected — they continue to build their future dataframe internally with no dependency on uploaded data.
