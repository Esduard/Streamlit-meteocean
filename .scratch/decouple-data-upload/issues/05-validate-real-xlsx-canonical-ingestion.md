# Validate real XLSX files ingest into the canonical dataset

Status: ready-for-agent

## Parent

`.scratch/decouple-data-upload/PRD.md`

## What to build

Add tests that exercise the actual raw `.xlsx` platform files under `data_raw_xlsx/` through the real upload ingestion path and prove they can be converted into the persisted canonical dataset expected by the decoupled upload PRD.

This issue is intentionally about the real file format, not synthetic DataFrames. The current unit tests cover merge behavior with generated frames; this issue should verify that files shaped like the user's real uploads can be opened by `read_raw_xlsx()`, passed into `UploadedDataStore.ingest_files()`, concatenated/merged through staging, and materialized as the canonical dataset.

Use the existing schema gate:

```python
meteocean_forecast.features.raw_xlsx_reader.read_raw_xlsx()
```

Do not add a separate header resolver in `UploadedDataStore`. If real fixture files expose known alternate long headers, they should be handled in `raw_xlsx_reader` only, where `_RENAME_MAP` already documents the current allowed aliases:

- `atm_wnd_spd_10m (vel de vento)` -> `atm_wnd_spd_10m`
- `wav_hs (altura de onda)` -> `wav_hs`
- `sw_cur_spd (vel. Corrente)` -> `sw_cur_spd`

The test suite should also include a control case for an invalid header variant: create or mutate a test `.xlsx` so that one or more required headers do not match `EXPECTED_COLUMNS` and are not in the allowed rename map. That file must be rejected, and the test should pass because the rejection is correct.

## Acceptance criteria

- [x] A test discovers or explicitly enumerates the real platform XLSX files in `data_raw_xlsx/` and ingests them through `UploadedDataStore.ingest_files()` using a `tmp_path` app-data directory.
- [x] Every valid real platform file is accepted by ingestion, using `read_raw_xlsx()` as the only parsing/schema-validation path.
- [x] The resulting canonical dataset is non-empty, has a parseable/sorted `time` column, contains all `EXPECTED_COLUMNS`, and can be loaded through `UploadedDataStore.load_canonical_dataset()`.
- [x] Multiple valid platform files ingested in one call produce one canonical row per timestamp, with numeric values averaged across contributing platforms according to the existing staging-to-canonical rules.
- [x] The upload log records one successful entry per accepted real file, including original filename, platform id, row count, and days covered.
- [x] A deliberately invalid `.xlsx` with unknown/mismatched required header names is rejected with a clear missing-column/schema error.
- [x] The invalid-header control file does not partially merge anything into staging or canonical data when ingested by itself.
- [x] If one real fixture uses known alternate long headers, the test documents that these aliases are accepted only because `raw_xlsx_reader._RENAME_MAP` normalizes them.
- [x] No raw uploaded `.xlsx` file is copied into the app-data directory as part of the test; only the persisted staging/canonical/log files may appear there.

## Suggested test shape

Add a focused test module, for example:

```text
streamlitapp/tests/test_real_xlsx_canonical_ingestion.py
```

Suggested cases:

- `test_real_platform_xlsx_files_ingest_into_canonical_dataset`
  - locate the `data_raw_xlsx/*.xlsx` fixtures from the repository root;
  - ingest all valid files in one `UploadedDataStore(tmp_path / "app_data")` call;
  - assert no rejected files, one accepted result per fixture, non-empty canonical output, expected columns, and upload-log entries.
- `test_invalid_header_xlsx_is_rejected_without_merging`
  - build a minimal XLSX from `EXPECTED_COLUMNS`, then rename one required column to an unknown name;
  - call `ingest_files()`;
  - assert zero accepted files, one rejected file, a missing-column/schema reason, and an empty canonical dataset.

If one of the real files currently fails because it has truly incorrect headers, do not silently broaden the schema. Treat that file as the invalid-header control unless the product owner confirms those headers are a supported real-world variant. The starting assumption for this issue is: exact `EXPECTED_COLUMNS` plus the explicitly documented `_RENAME_MAP` aliases are valid; other required-header mismatches are invalid.

## Blocked by

- `.scratch/decouple-data-upload/issues/01-core-data-ingestion.md` (needs `UploadedDataStore` and canonical persistence) - done, unblocked.

## Comments

This issue was split out after the core ingestion work because the first pass used synthetic XLSX files generated in tests. Those tests are good for merge semantics, but they do not prove that the actual platform export files in `data_raw_xlsx/` still match the canonical upload contract.

**2026-06-25 — Implemented.**

- Investigation surfaced a real bug: `read_raw_xlsx()` could not parse *any* of the 6 real files in `data_raw_xlsx/`. Every platform export has a 3-row metadata block above the actual data — a `depth`/`single_level` classification row, a real header row whose first cell is literally `"variable"` instead of `"time"`, and a spurious placeholder row (`"time"` in the first cell, blank elsewhere) — so plain `header=0` parsing produced nonsense columns (`Unnamed: 2`, etc.) and rejected every file.
- Fixed in `meteocean_forecast/features/raw_xlsx_reader.py` only (per the issue's instruction not to add a second header resolver in `UploadedDataStore`): `read_raw_xlsx()` now peeks the first couple of rows (cheap — `nrows=2`) to detect whether the real header lives at row 0 (ordinary uploads, including all synthetic test fixtures) or row 1 (the real export shape), then does exactly one full read with that header row. If the detected header's first cell is literally `"variable"`, it's renamed to `"time"`. The existing `_RENAME_MAP` long-alias normalization and the existing NaT-drop logic are unchanged and still run afterward — the latter automatically discards the leftover placeholder row (its `"time"` value fails to parse, so it's dropped along with any row with an unparseable timestamp).
  - This two-step peek-then-read was specifically needed for performance: each real file is ~87.7k rows, and a naive "try header=0, fall back to header=1" approach means a full second read (openpyxl takes ~22s/file regardless of header row, since `header` only changes which row becomes the column index, not how much is read) — doubling runtime across 6 files. The `nrows`-bounded peek avoided that.
- Confirmed `era5_..._FZA-M-59 - PUC.xlsx` is the one real fixture using the documented long Portuguese header aliases (`atm_wnd_spd_10m (vel de vento)`, `wav_hs (altura de onda)`, `sw_cur_spd (vel. Corrente)`); the other 5 already use the short canonical names. No new aliases were added — the existing `_RENAME_MAP` already covered it.
- New test module `tests/test_real_xlsx_canonical_ingestion.py`:
  - `test_real_platform_xlsx_files_ingest_into_canonical_dataset` — ingests all 6 real files in one `UploadedDataStore(tmp_path / "app_data")` call; asserts zero rejections, one accepted entry per file (with platform id, row count, days covered), a non-empty canonical dataset containing all `EXPECTED_COLUMNS` except `plat_id` (canonical rows are cross-platform averages and never carry `plat_id`, per `docs/adr/0002`), a sorted/parseable/duplicate-free `time` column, a value spot-check that one canonical cell equals the mean of that timestamp's contributing platforms (read from the persisted staging parquet, not by re-parsing xlsx), correct upload-log entries, and that only `staging_data.parquet` / `canonical_dataset.parquet` / `upload_log.json` exist under `app_data/` (no raw `.xlsx` retained).
  - `test_invalid_header_xlsx_is_rejected_without_merging` — synthetic file (via the existing `raw_df` fixture) with `wav_hs` renamed to an unknown header; asserts it's rejected with a `wav_hs`-naming missing-column error and that canonical/log stay empty.
  - `test_real_alias_fixture_is_accepted_only_via_documented_rename_map` — reads `FZA-M-59` directly through `read_raw_xlsx()` and asserts its columns normalize to exactly `EXPECTED_COLUMNS`, documenting that acceptance depends solely on `_RENAME_MAP`.
  - The whole module is skipped (not failed) if `data_raw_xlsx/` isn't present in a given checkout.
- Full suite: 88 passed (85 pre-existing + 3 new); the real-file module takes ~2:45 since it parses ~87.7k-row `.xlsx` files via `openpyxl`, which is inherently slow regardless of this fix — flagging this as a maybe-future "the real-fixture suite is slow" concern, not something this issue's scope covers fixing further (e.g. caching a pre-parsed fixture, or running it as a separate marked/opt-in suite).
- `ruff check` clean on both changed/new files.
