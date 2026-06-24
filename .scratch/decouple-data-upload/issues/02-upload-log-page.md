# Upload Log page

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

A new, dedicated Streamlit "Upload Log" page, separate from the Data Upload page, purely for reviewing upload history. It is read-only — no upload action happens here.

The page reads from `UploadedDataStore.upload_log()` (added in the core-data-ingestion slice) and displays every recorded entry: filename, `plat_id`, days/timestamps covered, and upload time. It also shows the canonical dataset's current latest timestamp (via `UploadedDataStore.latest_canonical_timestamp()`) for reference.

This page exists so the Data Upload page can stay focused purely on the upload action itself, without an upload-history table cluttering it.

## Acceptance criteria

- [ ] A new "Upload Log" page exists, reachable from the app's page navigation, separate from "Data Upload".
- [ ] The page displays every upload-log entry recorded so far (filename, platform, days covered, upload time).
- [ ] The page displays the canonical dataset's current latest timestamp.
- [ ] The page performs no upload action and does not mutate any stored data — it only reads.
- [ ] If no uploads have happened yet, the page shows a clear empty state rather than an error or blank table.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore.upload_log()` and `latest_canonical_timestamp()`)
