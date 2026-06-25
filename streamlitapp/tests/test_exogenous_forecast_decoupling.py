"""
Tests for issue 04: exogenous forecasting must source its raw data from the
canonical UploadedDataStore dataset, not an inline per-run file uploader.

Drives a real forecast page (`pages/1_Current_Speed.py`, which delegates to
`_page_template.render_forecast_page`) through `streamlit.testing.v1.AppTest`,
with a fake `ForecastingService` injected via session_state (duck-typed —
`_page_template` never imports `ForecastingService` for type checks) so the
test doesn't depend on real trained Prophet models on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from meteocean_forecast import path_utils
from meteocean_forecast.data.uploaded_data_store import UploadedDataStore
from meteocean_forecast.domain.model_metadata import ModelMetadata
from meteocean_forecast.features.raw_xlsx_reader import EXPECTED_COLUMNS

_APP_DIR = Path(__file__).resolve().parents[1] / "app"
_PAGE_PATH = _APP_DIR / "pages" / "1_Current_Speed.py"
_FEATURE_ROWS = 50

# `1_Current_Speed.py` does `from _page_template import ...`, relying on `streamlit
# run`'s multipage mechanism to put the app dir on sys.path. AppTest executes the
# script directly without that mechanism, so it must be added here.
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))


def _exogenous_meta() -> ModelMetadata:
    return ModelMetadata(
        target_variable="current_speed",
        model_family="prophet",
        model_type="exogenous",
        model_path=Path("/fake/exogenous/prophet_model.json"),
        required_features=(),
        feature_name_map=None,
        frequency="H",
        max_univariate_horizon_hours=8760,
        display_name="fake_exogenous_model",
    )


def _univariate_meta() -> ModelMetadata:
    return ModelMetadata(
        target_variable="current_speed",
        model_family="prophet",
        model_type="univariate",
        model_path=Path("/fake/univariate/prophet_model.json"),
        required_features=(),
        feature_name_map=None,
        frequency="H",
        max_univariate_horizon_hours=8760,
        display_name="fake_univariate_model",
    )


class _FakeService:
    """Duck-typed stand-in for ForecastingService; only the methods the page calls."""

    def __init__(self, models: list[ModelMetadata]) -> None:
        self._models = models

    def get_models_for_target(self, target_variable: str) -> list[ModelMetadata]:
        return self._models

    def prepare_exogenous_features(
        self, raw_df: pd.DataFrame, metadata: ModelMetadata
    ) -> pd.DataFrame:
        return pd.DataFrame(
            {"ds": pd.date_range("2026-01-01", periods=_FEATURE_ROWS, freq="h")}
        )

    def forecast(self, request) -> pd.DataFrame:
        raise AssertionError("forecast() should not be called by these tests")


def _make_platform_df(plat_id: str, value: float, n_rows: int = 5) -> pd.DataFrame:
    times = pd.date_range("2026-06-01", periods=n_rows, freq="h")
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
    """Point the app data dir at `app_data_dir`; return a fresh AppTest for page 1."""

    def _factory(app_data_dir: Path, service) -> AppTest:
        app_data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(path_utils, "get_app_data_dir", lambda: app_data_dir)
        st.cache_resource.clear()
        at = AppTest.from_file(str(_PAGE_PATH))
        at.session_state["service"] = service
        return at

    return _factory


def test_no_canonical_dataset_points_to_data_upload_page(page_pointing_at, tmp_path):
    service = _FakeService([_exogenous_meta()])
    at = page_pointing_at(tmp_path / "empty_app_data", service)

    at.run()

    assert not at.exception
    assert len(at.file_uploader) == 0
    assert any("Data Upload" in info.value for info in at.info)
    assert len(at.slider) == 0


def test_existing_canonical_dataset_runs_through_engineered_features(page_pointing_at, tmp_path):
    app_data_dir = tmp_path / "app_data"
    store = UploadedDataStore(app_data_dir)
    store.ingest_files([_write_xlsx(_make_platform_df("PLAT-A", 1.0), tmp_path / "a.xlsx")])
    latest = store.latest_canonical_timestamp()
    assert latest is not None

    service = _FakeService([_exogenous_meta()])
    at = page_pointing_at(app_data_dir, service)

    at.run()

    assert not at.exception
    assert len(at.file_uploader) == 0
    assert not at.info  # no "missing data" message once a canonical dataset exists
    [horizon_slider] = at.slider
    assert horizon_slider.max == _FEATURE_ROWS
    assert any("canonical dataset" in cap.value for cap in at.caption)


def test_univariate_model_unaffected_by_canonical_dataset_state(page_pointing_at, tmp_path):
    service = _FakeService([_univariate_meta()])
    at = page_pointing_at(tmp_path / "empty_app_data", service)

    at.run()

    assert not at.exception
    assert len(at.file_uploader) == 0
    # The freshness warning (issue 03) is independent of model type and may still
    # show a "no canonical dataset" info message; what must NOT appear is issue 04's
    # exogenous-specific message gating the forecast itself behind an upload.
    assert not any("forecasting with this model" in info.value for info in at.info)
    [horizon_slider] = at.slider
    assert horizon_slider.max == 8760
