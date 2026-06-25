from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from meteocean_forecast import path_utils
from meteocean_forecast.data.uploaded_data_store import UploadedDataStore
from meteocean_forecast.features.raw_xlsx_reader import EXPECTED_COLUMNS

_PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "pages" / "5_Upload_Log.py"


def _make_platform_df(
    plat_id: str, value: float, n_rows: int = 5, start: str = "2026-06-01"
) -> pd.DataFrame:
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
def page_pointing_at(monkeypatch):
    """Point the app's data dir at `app_data_dir`; return a fresh AppTest for the page."""

    def _factory(app_data_dir: Path) -> AppTest:
        app_data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(path_utils, "get_app_data_dir", lambda: app_data_dir)
        # The page caches its store via st.cache_resource keyed by module globals; clear
        # it so a previous run's store (pointed at a different dir) is not reused.
        st.cache_resource.clear()
        return AppTest.from_file(str(_PAGE_PATH))

    return _factory


def test_empty_state_shows_message_and_no_exception(page_pointing_at, tmp_path):
    at = page_pointing_at(tmp_path / "empty_app_data")
    at.run()

    assert not at.exception
    assert any("No uploads have been recorded" in info.value for info in at.info)
    assert any("No data has been uploaded yet" in cap.value for cap in at.caption)
    assert len(at.dataframe) == 0


def test_populated_state_shows_log_entries_and_latest_timestamp(page_pointing_at, tmp_path):
    app_data_dir = tmp_path / "app_data"
    store = UploadedDataStore(app_data_dir)
    store.ingest_files([_write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")])
    store.ingest_files([_write_xlsx(_make_platform_df("PLAT-B", 3.0), tmp_path / "b.xlsx")])

    latest = store.latest_canonical_timestamp()
    assert latest is not None

    at = page_pointing_at(app_data_dir)
    at.run()

    assert not at.exception
    assert len(at.dataframe) == 1
    table = at.dataframe[0].value
    assert list(table["Platform"]) == ["PLAT-A", "PLAT-B"]
    assert set(table["Filename"]) == {"a.xlsx", "b.xlsx"}

    latest_str = latest.strftime("%Y-%m-%d %H:%M")
    assert any(latest_str in cap.value for cap in at.caption)
    assert not at.info
