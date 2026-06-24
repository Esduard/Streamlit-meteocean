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

- [ ] No file uploader or upload-related UI appears on the forecast page for exogenous models.
- [ ] Selecting an exogenous model with an existing canonical dataset runs a forecast using features computed from that canonical dataset via the unchanged `engineer_features()` / `prepare_exogenous_features()` path.
- [ ] Selecting an exogenous model with no canonical dataset shows a clear message pointing to the Data Upload page, with no forecast attempted.
- [ ] The selectable forecast horizon for exogenous models is capped by the canonical dataset's latest timestamp.
- [ ] Univariate model selection and forecasting behave exactly as before this change, with no upload-related UI or dependency introduced.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.load_canonical_dataset()` and `latest_canonical_timestamp()`)
