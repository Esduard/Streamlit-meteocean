# Development Track: Decouple Data Upload from Forecast Model Type

> Revised after a grilling/domain-modeling session on 2026-06-24. The original version of this doc scoped out feature engineering and persistent storage entirely; that scope has since been superseded. See `docs/adr/0002-canonical-dataset-for-exogenous-features.md` and the "Forecasting Data" section of `CONTEXT.md` for the resolved design this doc now describes.

## 1. Context

The application is a Python Streamlit forecasting website. It currently loads trained forecasting model files and displays forecast results from the current day up to a user-selected horizon.

The application supports two broad model modes:

1. **Univariate models**

   * Do not require an uploaded file, ever.
   * Generate forecasts using only the trained model and internal model history.

2. **Exogenous models**

   * Require exogenous variables to run a forecast.
   * Today, those variables are calculated from a single file uploaded inline on the forecast page immediately before running the forecast — model type directly gates whether an uploader appears at all.

This development track removes that gate. Exogenous models still need exogenous variables — but those variables are now calculated from a **persisted canonical dataset** that the app maintains independently of any specific forecast run, rather than from a one-off upload tied to that run.

## 2. Goal

Create an independent data upload and monitoring flow, and make exogenous forecasting consume it directly.

The user uploads `.xlsx` files — each containing hourly raw meteocean data for a single platform (`plat_id`) — on a dedicated **Data Upload** page, at any time, independent of which model or target variable they're about to forecast. The app merges uploads from possibly-different platforms into one continuously-growing **canonical dataset** at hourly granularity. Exogenous models read this canonical dataset at forecast time to calculate their required variables. The main forecast page shows a data freshness warning based on the canonical dataset's latest timestamp. A separate **Upload Log** page lets the user review the full history of what's been uploaded.

## 3. Current State

* The app can load trained model files.
* The app can show forecast results for a selected forecast horizon.
* The frontend already displays the model's training cutoff timestamp.
* Exogenous models currently render an inline file uploader on the forecast page (`_page_template.py`, gated on `selected_meta.is_exogenous`); that single upload is parsed and immediately fed to `engineer_features()` for that run only, in memory. Nothing is persisted.
* Univariate models have no upload dependency.

This track removes the inline uploader and the model-type gate entirely, replacing them with the persistent flow described below.

## 4. New Conceptual Design

Data availability is now fully independent of model type, and feature engineering runs at *forecast time* against whatever data is currently available — not against a fresh per-run upload.

```text
All models:
    can be selected and loaded normally, with no upload precondition

Data Upload page:
    accepts one or more .xlsx files at once (one platform per file)
    rejects any file containing more than one plat_id
    appends each file's rows into a staging table, keyed by (plat_id, time)
        - last-write-wins per (plat_id, time) on re-upload
    derives the canonical dataset from staging:
        - groups by time, averages across whichever platforms reported that hour
    records an upload-log entry (filename, plat_id, days covered, uploaded_at)
        - does NOT retain the original file

Main Forecast page:
    exogenous models read the canonical dataset directly and run
    engineer_features() against it at forecast time
    if no canonical dataset exists yet, shows a message pointing to Data Upload
    shows a freshness warning based on canonical dataset's overall max(time)
```

## 5. Scope of This Development Track

### In scope

* A dedicated Streamlit "Data Upload" page for upload and freshness monitoring.
* A separate dedicated "Upload Log" page for reviewing the history of uploaded files.
* Accepting one or more `.xlsx` files per upload action.
* Validating each file contains exactly one `plat_id`; rejecting mixed-platform files with a clear message.
* A staging table of raw per-`(plat_id, time)` rows (Parquet), used as the source of truth for re-derivation.
* A canonical dataset (Parquet), derived from staging by averaging across platforms per hourly timestamp, shared across all three target variables.
* An upload log (JSON) recording filename, `plat_id`, days/timestamps covered, and upload time per file — no retention of the original file.
* A `get_app_data_dir()` helper in `path_utils.py`, following the existing pattern of `get_models_dir()` / `get_logs_dir()`, portable across dev mode and the PyInstaller executable.
* Removing the inline file uploader from the forecast page for exogenous models; exogenous models read the canonical dataset and run `engineer_features()` at forecast time instead.
* Freshness warnings on the main forecast page, based on the canonical dataset's overall latest timestamp.

### Out of scope for now

* Retraining models.
* Changing the core forecasting algorithm.
* A fixed/known roster of platforms — platforms are discovered dynamically from whatever `plat_id` values appear in uploads. The app cannot detect "platform X is missing" in v1, only "the combined dataset is N days stale."
* Per-platform freshness display — only the combined canonical dataset's freshness is shown.
* Redesigning the entire application navigation beyond adding the Data Upload page.
* Removing existing model loading behavior that doesn't directly conflict with this track.

## 6. Expected User Flow

### 6.1 Main Forecast Page

The user opens the application and can still:

* Select target variable.
* Select model.
* Select forecast horizon (capped, for exogenous models, by the canonical dataset's latest timestamp).
* Run or view forecast results.

For exogenous models, the page no longer renders a file uploader. It reads the canonical dataset and computes features via `engineer_features()`. If no canonical dataset exists yet, the page shows a message directing the user to the Data Upload page instead of blocking inline.

The page shows a data freshness warning based on the canonical dataset's latest timestamp:

```text
Uploaded data is up to date.
Latest data timestamp: 2026-05-18 14:00
```

```text
Warning: data is more than 30 days old.
Latest data timestamp: 2026-04-10 09:00
```

```text
Warning: data is more than 60 days old.
Latest data timestamp: 2026-03-01 03:00
```

```text
Critical warning: data is more than 90 days old.
Latest data timestamp: 2026-01-01 00:00
```

### 6.2 Data Upload Page

A new page, **Data Upload**.

This page should allow the user to:

* See the model training cutoff timestamp already available in the application.
* See the latest timestamp available in the canonical dataset.
* Upload one or more `.xlsx` files at once (the UI should encourage uploading all of a day's platforms together, though uploading separately is fully supported and correct).
* See a clear error if any uploaded file contains more than one `plat_id`.
* Confirm that files were ingested successfully.
* See the latest timestamp in the canonical dataset after ingestion.

This page does not show the historical upload log — that lives on the separate Upload Log page (section 6.3).

The staging table, canonical dataset, and upload log must persist across app restarts.

### 6.3 Upload Log Page

A new page, **Upload Log**, dedicated purely to reviewing upload history. Kept separate from Data Upload so that page stays focused on the upload action itself.

This page should allow the user to:

* See every upload-log entry recorded so far (filename, `plat_id`, days covered, upload time).
* See the canonical dataset's current latest timestamp for reference.

No upload action happens on this page — it is read-only.

## 7. Freshness Warning Rules

Calculated from the canonical dataset's overall `max(time)` across all platforms combined — not per-platform.

If no canonical dataset exists, show a clear warning that no data is available yet.

| Condition                                           | Status               | UI Severity    |
| ---------------------------------------------------- | --------------------- | --------------- |
| No canonical dataset exists                          | Missing data warning | Gray            |
| Latest timestamp is less than 30 days old            | OK                    | Normal / green  |
| 30 days or more without new data                     | Stale data warning    | Gray            |
| 60 days or more without new data                     | Medium warning        | Yellow          |
| 90 days or more without new data                     | Critical warning      | Red             |

Suggested constants (easy to configure in code):

```python
STALE_DATA_DAYS_GRAY = 30
STALE_DATA_DAYS_YELLOW = 60
STALE_DATA_DAYS_RED = 90
```

## 8. File Upload Requirements

The upload page accepts one or more files with extension `.xlsx` (`st.file_uploader(..., accept_multiple_files=True)`).

Each file must pass the existing `read_raw_xlsx()` validation (40 required columns including `time` and `plat_id`).

Each file must contain exactly one distinct `plat_id` value across all its rows. Reject files with more than one, with a clear message — the staging/upload-log design assumes one file = one platform.

The app should reject unsupported file types and mixed-platform files with user-friendly messages.

The app should not say "this is required only for exogenous models" — uploaded data is a general, independent feature.

## 9. Local Storage Requirements

All persistent data lives under a new writable folder resolved by `get_app_data_dir()` (mirrors `get_models_dir()` / `get_logs_dir()` in `path_utils.py`, portable for both dev mode and the PyInstaller executable):

```text
app_data/
  staging_data.parquet       # one row per (plat_id, time); raw values; source of truth
  canonical_dataset.parquet  # one row per time; averaged across platforms; consumed by engineer_features()
  upload_log.json            # audit trail: filename, plat_id, days covered, uploaded_at
```

Original uploaded `.xlsx` files are **not retained** — they're too large to keep indefinitely. Only the upload log entry survives.

## 10. Metadata Requirements (Upload Log)

```json
{
  "uploads": [
    {
      "original_filename": "platform_a_june_2026.xlsx",
      "plat_id": "PLAT-001",
      "days_covered": ["2026-06-18", "2026-06-19", "2026-06-20"],
      "uploaded_at": "2026-06-24T14:30:00",
      "row_count": 72
    }
  ],
  "latest_canonical_timestamp": "2026-06-20T23:00:00"
}
```

The upload log lets the app and the user know:

* Which files were uploaded, for which platform, and when.
* What days each file covered.
* The canonical dataset's current latest timestamp (recomputed after every ingest).

## 11. Timestamp and Platform Detection

No generic timestamp-column resolver is needed — `read_raw_xlsx()` already enforces a fixed schema with a `time` column and validates it during parsing (drops unparseable rows above a 5% threshold, sorts, and warns on non-hourly gaps). Reuse it unchanged for each file in a multi-file upload.

After parsing, validate that the file's `plat_id` column contains exactly one distinct value; reject otherwise.

## 12. Main Page Integration

The main forecast page should not parse Excel files or know about staging/upload internals. It should call small helpers that read the canonical dataset and upload log:

```python
load_canonical_dataset()
get_latest_canonical_timestamp()
calculate_data_freshness_status(latest_timestamp)
render_data_freshness_warning()
```

For exogenous models, the forecast execution path should call `engineer_features(load_canonical_dataset())` directly — it should not reference the upload flow at all.

## 13. Decoupling from Exogenous Model Logic

* Remove the inline file uploader and the `if selected_meta.is_exogenous: render uploader` block from `_page_template.py`.
* Exogenous models remain internally identified as exogenous (via `ModelMetadata.model_type` / `is_exogenous`), but that flag now only controls *which features are computed*, not *whether an uploader is shown*.
* If the canonical dataset doesn't exist or doesn't cover enough of the requested horizon, show a clear message pointing to the Data Upload page rather than blocking inline.
* Existing forecast behavior for univariate models is unaffected.

## 14. Implementation Strategy

1. Add `get_app_data_dir()` to `path_utils.py`.
2. Add a staging-table module: append rows from a parsed upload, dedupe by `(plat_id, time)` last-write-wins, persist as Parquet.
3. Add a canonical-dataset module: derive from staging by grouping on `time` and averaging across platforms; persist as Parquet.
4. Add an upload-log module: append an entry per ingested file; persist as JSON.
5. Add the Data Upload Streamlit page: multi-file uploader, per-file `plat_id` validation, calls into staging/canonical/upload-log modules, displays latest canonical timestamp after ingestion.
6. Add the Upload Log Streamlit page: read-only display of all upload-log entries and the canonical dataset's latest timestamp.
7. Add freshness helpers (`calculate_data_freshness_status`, `render_data_freshness_warning`) and wire them into the main forecast page.
8. Remove the inline uploader and `is_exogenous` upload gate from `_page_template.py`; wire exogenous forecast execution to `engineer_features(load_canonical_dataset())`.
9. Update the exogenous forecast horizon cap to derive from the canonical dataset's latest timestamp instead of a per-run upload.
10. Test both univariate and exogenous flows, including multi-file upload, late/separate platform uploads, and mixed-platform rejection.

## 15. Acceptance Criteria

This track is complete when:

* There is a separate Data Upload page accepting one or more `.xlsx` files per action.
* Files with more than one `plat_id` are rejected with a clear message.
* Uploaded rows are merged into a staging table and a derived canonical dataset that both persist across app restarts.
* An upload log records filename, platform, days covered, and upload time per file; original files are not retained.
* The Data Upload page displays the canonical dataset's latest timestamp after ingestion.
* A separate Upload Log page displays the full upload-log history, read-only.
* The main forecast page displays a freshness warning driven by the canonical dataset's overall latest timestamp, with correct 30/60/90-day thresholds.
* Exogenous model selection no longer renders or depends on an inline file uploader.
* Exogenous forecasts run `engineer_features()` against the canonical dataset at forecast time.
* Uploading the same platform's data for an hour already in staging correctly overwrites that platform's contribution, and the canonical average for that hour is recomputed correctly when other platforms also reported it.
* Univariate models and exogenous models can still be selected and forecast normally.

## 16. Manual Test Cases

### Test 1: Upload valid `.xlsx`, single platform

Given a valid Excel file with one `plat_id` and a parsable `time` column
When the user uploads it on the Data Upload page
Then the rows should be merged into staging
And the canonical dataset should be recomputed
And the upload log should record the new entry

### Test 2: Restart persistence

Given files were uploaded and ingested successfully
When the application is closed and reopened
Then the staging table, canonical dataset, and upload log should still be available

### Test 3: Unsupported file type

Given a user tries to upload a `.csv` or `.txt` file
Then the app should reject the file with a user-friendly message

### Test 4: Mixed-platform file rejected

Given a `.xlsx` file containing rows for more than one `plat_id`
When the user uploads it
Then the app should reject the file with a clear error
And nothing from that file should be merged into staging

### Test 5: Multi-file upload, same day

Given the user selects multiple `.xlsx` files (different platforms, overlapping hours) in one upload action
Then all files should be validated and merged
And the canonical dataset for overlapping hours should reflect the average across those platforms

### Test 6: Late/separate platform upload

Given platform A's data for a given hour is already in the canonical dataset (averaged alone)
When platform B's data for that same hour is uploaded later, separately
Then staging should now hold both platforms' rows for that hour
And the canonical dataset for that hour should be recomputed as the average of A and B, not a blend of B with A's old average

### Test 7: Main page freshness warning

Given the canonical dataset's latest timestamp is more than 30 / 60 / 90 days old
Then the main forecast page should show the gray / yellow / red warning respectively

Given no canonical dataset exists
Then the main forecast page should show a clear "no data available" warning

### Test 8: Model type independence

Given the user selects a univariate model
Then no upload-related UI should appear on the forecast page

Given the user selects an exogenous model
Then no inline uploader should appear on the forecast page
And the forecast should run using the canonical dataset, or show a message pointing to the Data Upload page if none exists

## 17. Developer Notes for Claude Code

Preserve existing behavior unless it directly conflicts with this track.

Prefer small helper functions over embedding staging, canonical-dataset, upload-log, and freshness logic directly inside Streamlit page code.

Avoid hardcoding absolute paths — use `get_app_data_dir()`.

Make the local data directory compatible with both development mode and executable mode.

Do not implement retraining.

Do not implement a fixed platform roster or per-platform freshness in v1.

Reuse `read_raw_xlsx()` unchanged for per-file parsing; only add the single-`plat_id` validation on top of it.

This track now is:

```text
upload (1+ files) -> validate single plat_id per file -> staging table -> derive canonical dataset
  -> upload log -> freshness warning -> exogenous forecast reads canonical dataset at forecast time
```

## 18. Suggested Deliverables

* `get_app_data_dir()` helper in `path_utils.py`.
* Staging-table module (append, dedupe by `(plat_id, time)`, persist Parquet).
* Canonical-dataset module (derive from staging by averaging per timestamp, persist Parquet).
* Upload-log module (append entry, persist JSON).
* New Data Upload Streamlit page (multi-file upload, validation, latest canonical timestamp).
* New Upload Log Streamlit page (read-only history of uploads).
* Freshness status helper and main-forecast-page warning component.
* Removal of the inline uploader and `is_exogenous` upload gate from `_page_template.py`; exogenous forecast execution wired to `engineer_features(load_canonical_dataset())`.
* Tests covering staging dedup/recompute correctness, mixed-platform rejection, multi-file upload, and freshness thresholds.
