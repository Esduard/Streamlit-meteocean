# Core data ingestion: upload, stage, and merge into canonical dataset

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

A single consolidated module/seam, `UploadedDataStore`, that owns the entire upload lifecycle, plus a new Data Upload Streamlit page that drives it. This is the foundational slice — everything else in this track depends on it.

`UploadedDataStore` is constructed against a writable directory (resolved via a new `get_app_data_dir()` helper in the existing path-utilities module, following the same pattern as the existing `get_models_dir()` / `get_logs_dir()` / `get_streamlit_config_dir()` — portable across dev mode and the frozen PyInstaller executable). It exposes:

```python
class UploadedDataStore:
    def ingest_files(self, files: list[UploadedFileLike]) -> IngestResult: ...
    def load_canonical_dataset(self) -> pd.DataFrame: ...
    def latest_canonical_timestamp(self) -> datetime | None: ...
    def upload_log(self) -> list[UploadLogEntry]: ...
```

(Interface agreed during PRD design, not yet implemented — exact module path is an implementation detail; place it sensibly within the existing `meteocean_forecast` package structure.)

Each file passed to `ingest_files()` must parse via the existing `read_raw_xlsx()` (unchanged — reuse it, don't reimplement schema/timestamp validation). After parsing, validate that the file contains exactly one distinct `plat_id`; reject the whole file with a clear error if it contains more than one, before anything is merged.

Maintain a **staging table** of raw rows keyed by `(plat_id, time)`, persisted as Parquet, deduplicated last-write-wins on re-upload of the same platform/hour. The **canonical dataset** (also Parquet) is never mutated in place — it is *derived* from staging by grouping on `time` and averaging across whichever platforms reported that hour, recomputed in full on every `ingest_files()` call. This is the critical correctness property from ADR-0002: when a platform's data for an hour arrives later in a *separate* call, the recompute must produce the true average across all contributing platforms for that hour — not a blend of the new value with a stale previous average.

Record an **upload log** entry per successfully ingested file (filename, `plat_id`, days/timestamps covered, uploaded_at) as JSON. Do not retain the original uploaded file content anywhere.

The Data Upload page:
- Accepts one or more `.xlsx` files in a single upload action (`accept_multiple_files=True`), with copy that encourages uploading a day's platforms together (while uploading separately remains fully correct).
- Surfaces validation errors clearly (unsupported file type, missing/unparseable timestamp column, missing required columns, mixed-platform file).
- After a successful ingest, confirms success and shows the canonical dataset's latest timestamp.

## Acceptance criteria

- [ ] `get_app_data_dir()` exists and resolves a writable directory portable across dev mode and the frozen executable.
- [ ] `UploadedDataStore.ingest_files()` accepts one or more files, validates each via `read_raw_xlsx()`, and rejects any file with more than one distinct `plat_id` (with a clear error, no partial merge).
- [ ] Ingesting a single file populates the staging table, canonical dataset, and upload log correctly.
- [ ] Ingesting multiple files in one call (different platforms, overlapping hours) produces correctly averaged canonical rows for the overlapping hours.
- [ ] Ingesting a platform's data for an hour already covered by a different platform, in a separate later call, recomputes the canonical average correctly across both platforms (not a blend of the new value with the old average).
- [ ] Re-ingesting the same platform's data for an hour it already covered overwrites that platform's prior contribution (last-write-wins), not duplicates it.
- [ ] State persists correctly across two separate `UploadedDataStore` instances pointed at the same directory (simulating an app restart).
- [ ] Original uploaded file content is never written to disk — only the upload log entry survives.
- [ ] The Data Upload page accepts multiple files at once, surfaces validation errors clearly, and shows the canonical dataset's latest timestamp after a successful upload.
- [ ] Unsupported file types are rejected with a user-friendly message.

## Blocked by

None - can start immediately
