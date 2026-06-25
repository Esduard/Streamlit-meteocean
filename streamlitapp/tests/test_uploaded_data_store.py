from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from meteocean_forecast.data.uploaded_data_store import UploadedDataStore
from meteocean_forecast.features.raw_xlsx_reader import EXPECTED_COLUMNS


def _make_platform_df(
    plat_id: str, value: float, n_rows: int = 5, start: str = "2026-06-01"
) -> pd.DataFrame:
    """A minimal valid raw-schema DataFrame where every numeric column equals `value`."""
    times = pd.date_range(start, periods=n_rows, freq="h")
    data: dict = {"time": times, "plat_id": plat_id}
    for col in EXPECTED_COLUMNS:
        if col in ("time", "plat_id"):
            continue
        data[col] = np.full(n_rows, value)
    return pd.DataFrame(data)


def _write_xlsx(df: pd.DataFrame, path: Path) -> Path:
    df.to_excel(path, index=False, engine="openpyxl")
    return path


@pytest.fixture()
def store(tmp_path) -> UploadedDataStore:
    return UploadedDataStore(tmp_path / "app_data")


def test_ingest_single_file_populates_canonical_and_log(store, tmp_path):
    file_path = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")

    result = store.ingest_files([file_path])

    assert result.rejected == ()
    assert len(result.accepted) == 1
    assert result.accepted[0].plat_id == "PLAT-A"
    assert result.accepted[0].row_count == 5

    canonical = store.load_canonical_dataset()
    assert len(canonical) == 5
    assert (canonical["wav_hs"] == 1.0).all()
    assert store.latest_canonical_timestamp() == canonical["time"].max().to_pydatetime()


def test_ingest_multiple_files_same_batch_averages_overlapping_hours(store, tmp_path):
    file_a = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")
    file_b = _write_xlsx(_make_platform_df("PLAT-B", 3.0), tmp_path / "b.xlsx")

    result = store.ingest_files([file_a, file_b])

    assert len(result.accepted) == 2
    canonical = store.load_canonical_dataset()
    assert len(canonical) == 5
    assert (canonical["wav_hs"] == 2.0).all()  # average of 1.0 and 3.0


def test_late_arriving_platform_recomputes_average_correctly(store, tmp_path):
    file_a = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")
    store.ingest_files([file_a])
    canonical_after_a = store.load_canonical_dataset()
    assert (canonical_after_a["wav_hs"] == 1.0).all()

    file_b = _write_xlsx(_make_platform_df("PLAT-B", 3.0), tmp_path / "b.xlsx")
    store.ingest_files([file_b])

    canonical_after_b = store.load_canonical_dataset()
    assert (canonical_after_b["wav_hs"] == 2.0).all()  # recomputed average, not a blend


def test_reupload_same_platform_and_hour_overwrites_not_duplicates(store, tmp_path):
    file_a1 = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a1.xlsx")
    store.ingest_files([file_a1])

    file_a2 = _write_xlsx(_make_platform_df("PLAT-A", 5.0), tmp_path / "a2.xlsx")
    store.ingest_files([file_a2])

    canonical = store.load_canonical_dataset()
    assert len(canonical) == 5  # not duplicated
    assert (canonical["wav_hs"] == 5.0).all()  # latest value wins


def test_mixed_platform_file_rejected_and_not_merged(store, tmp_path):
    mixed = _make_platform_df("PLAT-A", 1.0)
    mixed.loc[0, "plat_id"] = "PLAT-B"
    file_path = _write_xlsx(mixed, tmp_path / "mixed.xlsx")

    result = store.ingest_files([file_path])

    assert result.accepted == ()
    assert len(result.rejected) == 1
    assert "one platform" in result.rejected[0].reason

    canonical = store.load_canonical_dataset()
    assert canonical.empty


def test_unsupported_file_type_rejected(store, tmp_path):
    bad_file = tmp_path / "notes.txt"
    bad_file.write_text("not an xlsx file")

    result = store.ingest_files([bad_file])

    assert result.accepted == ()
    assert len(result.rejected) == 1
    assert "xlsx" in result.rejected[0].reason.lower()


def test_batch_with_one_bad_file_still_ingests_the_good_one(store, tmp_path):
    good = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "good.xlsx")
    bad = tmp_path / "bad.txt"
    bad.write_text("nope")

    result = store.ingest_files([good, bad])

    assert len(result.accepted) == 1
    assert len(result.rejected) == 1
    assert not store.load_canonical_dataset().empty


def test_original_file_content_is_not_retained(store, tmp_path):
    file_path = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")
    store.ingest_files([file_path])

    app_data_files = {p.name for p in (tmp_path / "app_data").iterdir()}
    assert app_data_files == {
        "staging_data.parquet",
        "canonical_dataset.parquet",
        "upload_log.json",
    }


def test_state_persists_across_separate_store_instances(tmp_path):
    app_data_dir = tmp_path / "app_data"
    file_path = _write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")

    first_store = UploadedDataStore(app_data_dir)
    first_store.ingest_files([file_path])

    second_store = UploadedDataStore(app_data_dir)
    assert len(second_store.upload_log()) == 1
    assert not second_store.load_canonical_dataset().empty
    assert second_store.latest_canonical_timestamp() is not None


def test_no_data_yields_empty_canonical_and_no_latest_timestamp(store):
    assert store.load_canonical_dataset().empty
    assert store.latest_canonical_timestamp() is None
    assert store.upload_log() == []


def test_upload_log_records_filename_platform_and_days_covered(store, tmp_path):
    file_path = _write_xlsx(_make_platform_df("PLAT-A", 1.0, n_rows=30), tmp_path / "a.xlsx")
    store.ingest_files([file_path])

    [entry] = store.upload_log()
    assert entry.original_filename == "a.xlsx"
    assert entry.plat_id == "PLAT-A"
    assert entry.row_count == 30
    assert len(entry.days_covered) >= 1
