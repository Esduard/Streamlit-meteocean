# PRD: Decouple Data Upload from Forecast Model Type

Status: ready-for-agent

Source: `docs/development_track/decouple_data_2026_06_24.md`, `docs/adr/0002-canonical-dataset-for-exogenous-features.md`, `CONTEXT.md` ("Forecasting Data" section).

## Problem Statement

Today, whether a user can upload meteocean data is decided by which model they happen to select. Picking an exogenous model reveals a file uploader on the forecast page; picking a univariate model hides it entirely. That single upload is used once, in memory, for that one forecast run, then discarded.

This creates two problems for the user:

1. They cannot bring in newer observed data without first navigating into an exogenous model's forecast flow — uploading data feels like a side effect of model selection rather than something they can do directly.
2. Every time they want to run an exogenous forecast, they must re-upload data, even if the platform's data hasn't changed since their last visit. There's no sense of "the data the app currently has" — it's re-derived from scratch every run and never persisted, so the app can't tell the user how fresh or stale its data actually is.

## Solution

Introduce data upload as an independent, persistent feature, decoupled from model selection entirely.

Users upload `.xlsx` files — each containing hourly raw meteocean data for one **Platform** — on a dedicated Data Upload page, whenever they have new data, regardless of which model they intend to forecast with later. The app merges every upload into a single, continuously-growing **Canonical dataset** at hourly granularity, averaging across platforms when more than one reports the same hour. Exogenous models read this canonical dataset at forecast time to calculate their required variables — there is no more per-run upload. A separate, read-only Upload Log page lets users review what's been uploaded and when. The main forecast page shows a freshness warning based on the canonical dataset's latest timestamp, so users know how current the data behind their forecast actually is.

## User Stories

1. As a forecast operator, I want to select any model (univariate or exogenous) without being prompted to upload a file first, so that model selection and data management feel like separate concerns.
2. As a forecast operator, I want to upload new platform data at any time, independent of which model I'm about to use, so that I can keep the app's data current on my own schedule.
3. As a data uploader, I want to upload more than one `.xlsx` file in a single action, so that I can submit all of today's platforms together without repeating the upload flow per file.
4. As a data uploader, I want the upload page to clearly invite me to upload all of a day's platforms together, so that I understand the intended workflow even though uploading separately also works.
5. As a data uploader, I want each uploaded file to be rejected with a clear error if it contains more than one platform's data, so that the app's one-file-one-platform assumption is never silently violated.
6. As a data uploader, I want a clear error message when I upload an unsupported file type (not `.xlsx`), so that I understand why the upload failed.
7. As a data uploader, I want a file rejected if it's missing required columns or has an unparseable timestamp, so that bad data never silently enters the canonical dataset.
8. As a data uploader, I want to upload a platform's data for a day that's already covered by other platforms, so that the canonical average for that day correctly includes my platform too.
9. As a data uploader, I want to re-upload a platform's data for an hour I've already submitted, so that I can correct mistakes — with the understanding that my latest upload for that platform/hour silently overwrites the previous one.
10. As a forecast operator, I want the canonical dataset's correctness to not depend on the order I upload platforms in, so that uploading platform B today and platform A tomorrow produces the same averaged result as uploading them together.
11. As a data uploader, I want confirmation that my upload succeeded and to see the resulting latest available timestamp, so that I know the ingestion worked.
12. As a forecast operator, I want to see a freshness warning on the main forecast page reflecting how stale the canonical dataset is, so that I know whether to trust the forecast or go upload newer data first.
13. As a forecast operator, I want the freshness warning to escalate visibly (gray → yellow → red) as data gets older (30/60/90 days), so that I can judge severity at a glance.
14. As a forecast operator, I want a clear "no data available" warning when no data has ever been uploaded, so that I'm not confused by a missing or blank freshness indicator.
15. As a forecast operator selecting an exogenous model, I want my forecast's required variables calculated automatically from the canonical dataset, so that I don't have to upload anything just to run a forecast.
16. As a forecast operator selecting an exogenous model, I want a clear message directing me to the Data Upload page if no canonical dataset exists yet, so that I understand why I can't run a forecast and what to do about it.
17. As a forecast operator, I want my exogenous forecast horizon to be capped by the canonical dataset's latest available timestamp, so that I can't select a horizon the data doesn't support.
18. As a forecast operator selecting a univariate model, I want the forecast page to behave exactly as it does today, with no upload-related UI at all, so that this change doesn't affect a flow that never needed uploads.
19. As a data uploader, I want a separate, dedicated page to review the history of everything I've uploaded (filename, platform, days covered, upload time), so that I can audit past uploads without cluttering the upload action itself.
20. As a data uploader, I want the Upload Log page to be read-only, so that I don't accidentally trigger uploads or mutate data while just reviewing history.
21. As a forecast operator, I want the staging table, canonical dataset, and upload log to survive an app restart, so that previously uploaded data isn't lost between sessions.
22. As an app operator running the packaged executable, I want the new persistent data to be stored in a writable, portable location relative to the executable, so that the feature works identically in development and in the packaged distribution.
23. As a forecast operator, I want the app to never assume a fixed roster of platforms, so that I'm not blocked or warned about a "missing platform" the app has no way of actually knowing about.
24. As a maintainer, I want the original uploaded files to not be retained on disk, so that storage doesn't grow unbounded with large raw files that are no longer needed once ingested.
25. As a maintainer, I want the exogenous feature-engineering code path (`engineer_features`) to remain unchanged, so that this track only changes where its input data comes from, not what it computes.

## Implementation Decisions

- **New consolidated seam — `UploadedDataStore`.** A single module/class owns the entire staging → canonical → log lifecycle and is the only thing the two new pages and the forecast page's exogenous path interact with:

  ```python
  class UploadedDataStore:
      def ingest_files(self, files: list[UploadedFileLike]) -> IngestResult: ...
      def load_canonical_dataset(self) -> pd.DataFrame: ...
      def latest_canonical_timestamp(self) -> datetime | None: ...
      def upload_log(self) -> list[UploadLogEntry]: ...
  ```

  (Interface agreed during the design session, not yet implemented — exact module path/location is an implementation detail for the agent to place sensibly within the existing `meteocean_forecast` package structure.)

- **Staging table is the source of truth.** Raw rows are kept per `(plat_id, time)`, deduplicated last-write-wins on re-upload of the same platform/hour. The canonical dataset is never mutated in place — it's *derived* from staging by grouping on `time` and averaging across whichever platforms reported that hour, recomputed on every `ingest_files()` call. This avoids incorrect incremental-average blending when a platform's data for an already-ingested hour arrives later. See ADR-0002 for the full rationale.
- **One canonical dataset, shared across all three target variables** (current_speed, wave_height, wind_speed) — a single upload already carries the raw columns needed for all three, per `raw_xlsx_reader.EXPECTED_COLUMNS`.
- **Storage format:** Parquet for the staging table and canonical dataset (typed dtypes, native datetime handling); JSON for the upload log (filename, `plat_id`, days/timestamps covered, uploaded_at).
- **No raw file retention.** Only the upload log entry survives per upload; the original `.xlsx` is never written to disk.
- **New `get_app_data_dir()` helper** in the existing path-utilities module, following the same pattern as the existing `get_models_dir()` / `get_logs_dir()` / `get_streamlit_config_dir()` — portable across dev mode and the frozen PyInstaller executable.
- **Mixed-platform validation.** Each uploaded file must contain exactly one distinct `plat_id` across all rows; reject otherwise with a clear error, before any merge into staging.
- **Reuse `read_raw_xlsx()` unchanged** for per-file schema/timestamp validation and parsing — no new timestamp-column resolver is needed since the schema is already fixed.
- **Multi-file upload widget** (`accept_multiple_files=True`) on the Data Upload page.
- **No fixed platform roster.** Platforms are discovered dynamically from whatever `plat_id` values appear in uploads; there is no way to detect "platform X is missing" in this track.
- **Two new Streamlit pages:**
  - **Data Upload** — multi-file uploader, per-file `plat_id` validation, shows the canonical dataset's latest timestamp after ingestion. No upload-history table here.
  - **Upload Log** — read-only, shows every upload-log entry plus the canonical dataset's current latest timestamp. No upload action on this page.
- **Forecast page changes (`_page_template.py`):** remove the inline file uploader and the `is_exogenous`-gated upload block entirely. For exogenous models, source `raw_df` for `ForecastingService.prepare_exogenous_features()` from `UploadedDataStore.load_canonical_dataset()` instead of an in-memory upload. If no canonical dataset exists, show a message pointing to the Data Upload page instead of blocking inline.
- **Forecast horizon cap for exogenous models** now derives from `UploadedDataStore.latest_canonical_timestamp()` instead of the length of a per-run uploaded feature DataFrame.
- **Freshness thresholds** stay as specified in the dev track: 30/60/90 days → gray/yellow/red, calculated from the canonical dataset's overall `max(time)` (not per-platform), via configurable constants (`STALE_DATA_DAYS_GRAY`, `STALE_DATA_DAYS_YELLOW`, `STALE_DATA_DAYS_RED`).
- **`engineer_features()` itself is unchanged** — only the source of its input `raw_df` changes.

## Testing Decisions

- Tests should exercise behavior through `UploadedDataStore` directly (constructed against a `tmp_path`), never by driving the Streamlit UI — this matches existing practice in the repo (e.g. `test_horizon_validation.py` tests `ForecastRequest` as a pure object with no UI involved; `_page_template.py` has no direct tests today).
- Good tests here assert on the *resulting* canonical dataset, upload log, and latest timestamp — not on internal staging-table mechanics — so the staging/recompute strategy could be swapped later without breaking tests, as long as the externally observable merge behavior stays correct.
- Required coverage for `UploadedDataStore`:
  - Ingesting a single file populates the canonical dataset and upload log correctly.
  - Ingesting multiple files in one call (different platforms, overlapping hours) produces correctly averaged canonical rows for the overlapping hours.
  - Ingesting a platform's data for an hour already covered by a different platform, in a *separate* later call, recomputes the canonical average correctly across both platforms (the core correctness case from ADR-0002 — must not just blend the new value with the old average).
  - Re-ingesting the same platform's data for an hour it already covered overwrites that platform's prior contribution (last-write-wins), not duplicates it.
  - A file containing more than one `plat_id` is rejected, and nothing from it is merged into staging or canonical.
  - State persists correctly across two separate `UploadedDataStore` instances pointed at the same directory (simulating an app restart).
- Freshness logic (`calculate_data_freshness_status`) should be tested as a pure function: boundary tests at 29/30/31, 59/60/61, 89/90/91 days, and the "no data" case.
- `ForecastingService.prepare_exogenous_features()` itself needs no new tests — its contract (raw `DataFrame` in, engineered/scaled `DataFrame` out) is unchanged and already covered by `test_feature_engineering_contract.py`. Only add a test confirming the forecast path correctly sources its `raw_df` from `UploadedDataStore.load_canonical_dataset()`.
- No Streamlit UI testing is in scope, consistent with current practice — the two new pages and the forecast page's wiring are thin and should delegate everything testable to `UploadedDataStore` and the freshness function.

## Out of Scope

- Any change to the `engineer_features()` pipeline itself (PCA/scaler refitting, regressor logic) — only its input source changes.
- Model retraining.
- A fixed/known roster of platforms, or detecting/warning about a specific missing platform.
- Per-platform freshness display — only the combined canonical dataset's freshness is shown.
- Retaining original uploaded `.xlsx` files on disk.
- Any conflict-resolution UI for re-uploaded platform/hour data — overwrite is silent, per ADR-0002.
- Redesigning app navigation beyond adding the two new pages.
- Automated Streamlit UI/browser testing.

## Further Notes

- This PRD supersedes the original (pre-revision) scope of `docs/development_track/decouple_data_2026_06_24.md`, which had explicitly excluded feature engineering and persistent storage from this track. That scoping was revised during a `/grill-with-docs` session on 2026-06-24 after clarifying that exogenous models must calculate variables from currently-available data, not a per-run upload — see ADR-0002 for the full rationale and the dev track doc for the detailed user-flow and acceptance criteria this PRD is based on.
- `CONTEXT.md` already defines **Platform** and **Canonical dataset** under "Forecasting Data" — use these terms, not synonyms, in code comments, UI copy, and commit messages for this track.
