"""Validate that the real platform XLSX exports in `data_raw_xlsx/` ingest
into the canonical dataset through the real upload path, not just synthetic
DataFrames (see .scratch/decouple-data-upload/issues/05-validate-real-xlsx-canonical-ingestion.md).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from meteocean_forecast.data.uploaded_data_store import UploadedDataStore
from meteocean_forecast.features.raw_xlsx_reader import EXPECTED_COLUMNS, read_raw_xlsx

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_XLSX_DIR = _REPO_ROOT / "data_raw_xlsx"
_REAL_XLSX_FILES = sorted(_REAL_XLSX_DIR.glob("*.xlsx"))

# This fixture's header row uses the long Portuguese aliases
# ("atm_wnd_spd_10m (vel de vento)", "wav_hs (altura de onda)",
# "sw_cur_spd (vel. Corrente)") that raw_xlsx_reader._RENAME_MAP normalises;
# the other real fixtures already use the short canonical names.
_ALIAS_FIXTURE_NAME = "era5_wnd_wav_and_cmems_re_bra_cur2d_FZA-M-59 - PUC.xlsx"

# Canonical rows are derived by averaging numeric columns across platforms
# per timestamp (see docs/adr/0002), so plat_id never appears in the
# canonical dataset even though it's a required column on upload.
_CANONICAL_EXPECTED_COLUMNS = [c for c in EXPECTED_COLUMNS if c != "plat_id"]

pytestmark = pytest.mark.skipif(
    not _REAL_XLSX_FILES, reason="data_raw_xlsx/*.xlsx fixtures not present in this checkout"
)


@pytest.fixture()
def store(tmp_path) -> UploadedDataStore:
    return UploadedDataStore(tmp_path / "app_data")


def test_real_platform_xlsx_files_ingest_into_canonical_dataset(store):
    assert any(f.name == _ALIAS_FIXTURE_NAME for f in _REAL_XLSX_FILES), (
        "expected the long-header-alias fixture to be present so this test also "
        "exercises raw_xlsx_reader._RENAME_MAP against a real file"
    )

    result = store.ingest_files(list(_REAL_XLSX_FILES))

    assert result.rejected == ()
    assert len(result.accepted) == len(_REAL_XLSX_FILES)
    assert {entry.original_filename for entry in result.accepted} == {
        f.name for f in _REAL_XLSX_FILES
    }
    for entry in result.accepted:
        assert entry.row_count > 0
        assert len(entry.days_covered) > 0
        assert entry.plat_id  # discovered from the file, not hardcoded

    canonical = store.load_canonical_dataset()
    assert not canonical.empty
    for col in _CANONICAL_EXPECTED_COLUMNS:
        assert col in canonical.columns

    parsed_time = pd.to_datetime(canonical["time"])
    assert parsed_time.is_monotonic_increasing
    assert parsed_time.notna().all()

    # One row per timestamp: 6 platforms reporting the same hourly series
    # must merge into one averaged canonical row per hour, not 6 rows.
    assert canonical["time"].duplicated().sum() == 0

    # Spot-check that canonical values are the cross-platform average, per
    # the staging-to-canonical rule in docs/adr/0002, using the persisted
    # staging table directly so this doesn't re-parse the xlsx files.
    staging = pd.read_parquet(store._base_dir / "staging_data.parquet")
    assert staging["plat_id"].nunique() == len(_REAL_XLSX_FILES)
    sample_time = canonical["time"].iloc[0]
    expected_wav_hs = staging.loc[staging["time"] == sample_time, "wav_hs"].mean()
    actual_wav_hs = canonical.loc[canonical["time"] == sample_time, "wav_hs"].iloc[0]
    assert actual_wav_hs == pytest.approx(expected_wav_hs)

    log_entries = {entry.original_filename: entry for entry in store.upload_log()}
    assert set(log_entries) == {f.name for f in _REAL_XLSX_FILES}
    for entry in log_entries.values():
        assert entry.row_count > 0
        assert len(entry.days_covered) > 0

    # No raw uploaded file content is retained in app_data — only the
    # persisted staging/canonical/log files.
    app_data_files = {p.name for p in store._base_dir.iterdir()}
    assert app_data_files == {
        "staging_data.parquet",
        "canonical_dataset.parquet",
        "upload_log.json",
    }


def test_invalid_header_xlsx_is_rejected_without_merging(store, tmp_path, raw_df):
    # Rename a required column to an unknown header that isn't EXPECTED_COLUMNS
    # and isn't in raw_xlsx_reader._RENAME_MAP either.
    invalid = raw_df.rename(columns={"wav_hs": "significant_wave_height_unknown"})
    bad_file = tmp_path / "invalid_headers.xlsx"
    invalid.to_excel(bad_file, index=False, engine="openpyxl")

    result = store.ingest_files([bad_file])

    assert result.accepted == ()
    assert len(result.rejected) == 1
    assert result.rejected[0].filename == "invalid_headers.xlsx"
    assert "wav_hs" in result.rejected[0].reason

    assert store.load_canonical_dataset().empty
    assert store.upload_log() == []


def test_real_alias_fixture_is_accepted_only_via_documented_rename_map(store):
    """FZA-M-59 uses the long Portuguese header variants. Confirm read_raw_xlsx
    accepts it solely because of the documented _RENAME_MAP aliases, by
    checking the columns it normalises to match EXPECTED_COLUMNS exactly."""
    alias_file = next(f for f in _REAL_XLSX_FILES if f.name == _ALIAS_FIXTURE_NAME)

    df = read_raw_xlsx(alias_file)

    assert list(df.columns) == EXPECTED_COLUMNS
    assert not df.empty
