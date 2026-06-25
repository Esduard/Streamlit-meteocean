# Upload Log page

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

A new, dedicated Streamlit "Upload Log" page, separate from the Data Upload page, purely for reviewing upload history. It is read-only — no upload action happens here.

The page reads from `UploadedDataStore.upload_log()` (added in the core-data-ingestion slice) and displays every recorded entry: filename, `plat_id`, days/timestamps covered, and upload time. It also shows the canonical dataset's current latest timestamp (via `UploadedDataStore.latest_canonical_timestamp()`) for reference.

This page exists so the Data Upload page can stay focused purely on the upload action itself, without an upload-history table cluttering it.

## Acceptance criteria

- [x] A new "Upload Log" page exists, reachable from the app's page navigation, separate from "Data Upload".
- [x] The page displays every upload-log entry recorded so far (filename, platform, days covered, upload time).
- [x] The page displays the canonical dataset's current latest timestamp.
- [x] The page performs no upload action and does not mutate any stored data — it only reads.
- [x] If no uploads have happened yet, the page shows a clear empty state rather than an error or blank table.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.upload_log()` and `latest_canonical_timestamp()`) — done, unblocked.

## Comments

**2026-06-24 — Implemented.**

- New read-only page `streamlitapp/app/pages/5_Upload_Log.py` (numbered to sort after Data Upload in the sidebar nav). Follows the same `st.cache_resource` store-factory pattern as `4_Data_Upload.py`.
- Renders every `UploadLogEntry` (filename, platform, days covered joined as a readable string, upload time, row count) in a `st.dataframe` table, plus the canonical dataset's latest timestamp via `latest_canonical_timestamp()`. Empty state (`st.info`) when `upload_log()` returns nothing — no error, no blank table.
- No file uploader, no mutating calls — purely reads `upload_log()` and `latest_canonical_timestamp()`.
- Tests: `tests/test_upload_log_page.py`, driven through `streamlit.testing.v1.AppTest` against the real page file (this page has no `st.file_uploader`, so unlike page 4 it could be fully exercised through `AppTest`, including the populated-table and empty-state cases). Monkeypatches `path_utils.get_app_data_dir` and clears `st.cache_resource` between runs for isolation.
- Full suite green; `ruff check` clean on the new files.
