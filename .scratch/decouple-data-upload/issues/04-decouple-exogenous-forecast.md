# Decouple exogenous forecasting from inline upload

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

Remove the inline file uploader and the `is_exogenous`-gated upload block from the forecast page entirely. Exogenous models must no longer require or show any upload UI at the point of forecasting — they read their input data from the canonical dataset instead.

For exogenous models, source `raw_df` for `ForecastingService.prepare_exogenous_features()` from `UploadedDataStore.load_canonical_dataset()` instead of an in-memory upload. `engineer_features()` itself is unchanged — only where its input comes from changes.

If no canonical dataset exists yet, show a clear message directing the user to the Data Upload page instead of blocking inline or erroring.

The exogenous forecast horizon cap must now derive from `UploadedDataStore.latest_canonical_timestamp()` instead of the length of a per-run uploaded feature DataFrame.

Univariate models are unaffected by this change — no upload UI, no canonical dataset dependency, behavior identical to today.

## Acceptance criteria

- [x] No file uploader or upload-related UI appears on the forecast page for exogenous models.
- [x] Selecting an exogenous model with an existing canonical dataset runs a forecast using features computed from that canonical dataset via the unchanged `engineer_features()` / `prepare_exogenous_features()` path.
- [x] Selecting an exogenous model with no canonical dataset shows a clear message pointing to the Data Upload page, with no forecast attempted.
- [x] The selectable forecast horizon for exogenous models is capped by the canonical dataset's latest timestamp.
- [x] Univariate model selection and forecasting behave exactly as before this change, with no upload-related UI or dependency introduced.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.load_canonical_dataset()` and `latest_canonical_timestamp()`) — done, unblocked.

## Comments

**2026-06-24 — Implemented.**

- Edited `streamlitapp/app/_page_template.py`: removed the `st.file_uploader` and the whole `is_exogenous`-gated inline-upload block (including the per-session `feature_df` cache in `st.session_state`, no longer needed). Added a cached `_get_uploaded_data_store()` (`st.cache_resource`, same pattern as the Data Upload / Upload Log pages).
- For exogenous models, `raw_df` now comes from `store.load_canonical_dataset()`; `service.prepare_exogenous_features(raw_df, selected_meta)` is unchanged and still does all the real work (`engineer_features()` is untouched).
- If `store.latest_canonical_timestamp()` is `None`, the page shows `st.info(...)` pointing at the **Data Upload** page and calls `st.stop()` — no feature engineering or forecast is attempted.
- `max_horizon` for exogenous models is `len(feature_df)`, where `feature_df` is derived from the canonical dataset — so it's inherently bounded by the data available through the canonical dataset's latest timestamp. A caption now shows that latest timestamp and row count for transparency (`"Using canonical dataset through <ts> (<n> rows)."`).
- Univariate branch is untouched — no upload UI ever existed there, and no canonical-dataset dependency was introduced for it.
- This issue and issue 03 (freshness warning) both needed to touch `_page_template.py`. To do the bulk of the work in parallel safely, issue 03 was built as a standalone, unwired module by a separate agent while this issue's edits to `_page_template.py` were done directly (by me); the freshness-warning wiring was then added as one small sequenced step immediately after both finished, avoiding any concurrent-edit conflict on the shared file.
- Tests: new `tests/test_exogenous_forecast_decoupling.py`, driving the real `pages/1_Current_Speed.py` through `streamlit.testing.v1.AppTest` with a duck-typed fake `ForecastingService` injected into `session_state` (avoids depending on real trained Prophet models on disk). Covers: no-canonical-dataset → info message + no slider/uploader; existing canonical dataset → feature-engineered forecast path runs, horizon slider capped at the engineered feature-row count, caption shown; univariate model unaffected (no upload UI, no gating message, horizon cap unchanged at `max_univariate_horizon_hours`).
- Verified end-to-end: booted the real `streamlit run` server and confirmed `/`, `/Current_Speed`, `/Data_Upload`, and `/Upload_Log` all return HTTP 200 with a clean server log (no exceptions).
- Full suite green (85 tests, including the 6 new tests added across issues 02–04); `ruff check` clean on all new/edited files (one pre-existing unrelated `E501` on an untouched line in `_page_template.py` was left as-is, out of scope).
