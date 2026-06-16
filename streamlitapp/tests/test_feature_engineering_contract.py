from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from meteocean_forecast.features.feature_engineering import (
    _add_energy_features,
    _add_fourier_feature,
    _add_pca_features,
    _add_seasonal_features,
    _add_uv_components,
    _dir_to_uv,
    engineer_features,
    select_and_scale_features,
)


# ---------------------------------------------------------------------------
# _dir_to_uv
# ---------------------------------------------------------------------------


def test_dir_to_uv_pure_north():
    """Direction 0° (from north), magnitude 1.0 → u≈0, v≈-1."""
    u, v = _dir_to_uv(pd.Series([0.0]), pd.Series([1.0]))
    assert abs(float(u.iloc[0])) < 1e-10
    assert abs(float(v.iloc[0]) - (-1.0)) < 1e-10


def test_dir_to_uv_pure_east():
    """Direction 90°, magnitude 1.0 → u≈-1, v≈0."""
    u, v = _dir_to_uv(pd.Series([90.0]), pd.Series([1.0]))
    assert abs(float(u.iloc[0]) - (-1.0)) < 1e-10
    assert abs(float(v.iloc[0])) < 1e-10


# ---------------------------------------------------------------------------
# _add_uv_components
# ---------------------------------------------------------------------------


def test_add_uv_components_creates_14_columns(raw_df):
    result = _add_uv_components(raw_df)
    uv_cols = [c for c in result.columns if c.endswith("_u") or c.endswith("_v")]
    assert len(uv_cols) == 14


def test_add_uv_components_does_not_mutate_input(raw_df):
    original_cols = list(raw_df.columns)
    _add_uv_components(raw_df)
    assert list(raw_df.columns) == original_cols


# ---------------------------------------------------------------------------
# _add_energy_features
# ---------------------------------------------------------------------------


def test_wave_energy_formula(raw_df):
    df = _add_uv_components(raw_df)
    df = _add_energy_features(df)
    expected = raw_df["wav_hs"].iloc[0] ** 2
    assert abs(df["wave_energy"].iloc[0] - expected) < 1e-10


# ---------------------------------------------------------------------------
# _add_seasonal_features
# ---------------------------------------------------------------------------


def test_seasonal_month_dummies_complete(raw_df):
    """All 12 month columns must exist even if only 1 month in data."""
    single_month = raw_df.head(10).copy()
    result = _add_seasonal_features(single_month)
    for m in range(1, 13):
        assert f"month_{m}" in result.columns, f"month_{m} missing"


def test_southern_hemisphere_seasons_december(raw_df_december):
    result = _add_seasonal_features(raw_df_december)
    assert result["is_summer"].iloc[0] == 1
    assert result["is_winter"].iloc[0] == 0


def test_seasonal_does_not_mutate_input(raw_df):
    original_cols = list(raw_df.columns)
    _add_seasonal_features(raw_df)
    assert list(raw_df.columns) == original_cols


# ---------------------------------------------------------------------------
# _add_fourier_feature
# ---------------------------------------------------------------------------


def test_fourier_feature_added(raw_df):
    result = _add_fourier_feature(raw_df)
    assert "sw_cur_spd_fourier" in result.columns
    assert result["sw_cur_spd_fourier"].notna().all()


def test_fourier_requires_sw_cur_spd(raw_df):
    df_no_cur = raw_df.drop(columns=["sw_cur_spd"])
    with pytest.raises(ValueError, match="sw_cur_spd"):
        _add_fourier_feature(df_no_cur)


# ---------------------------------------------------------------------------
# _add_pca_features
# ---------------------------------------------------------------------------


def test_pca_adds_8_columns(raw_df):
    df = _add_uv_components(raw_df)
    df = _add_energy_features(df)
    result = _add_pca_features(df)
    for i in range(1, 9):
        assert f"PCA_{i}" in result.columns


# ---------------------------------------------------------------------------
# engineer_features (master function)
# ---------------------------------------------------------------------------


def test_engineer_features_has_ds_column(raw_df):
    result = engineer_features(raw_df)
    assert "ds" in result.columns
    assert pd.api.types.is_datetime64_any_dtype(result["ds"])


def test_engineer_features_does_not_mutate_input(raw_df):
    original_cols = list(raw_df.columns)
    engineer_features(raw_df)
    assert list(raw_df.columns) == original_cols


def test_engineer_features_no_time_column(raw_df):
    """After engineer_features the original 'time' column is renamed to 'ds'."""
    result = engineer_features(raw_df)
    assert "time" not in result.columns
    assert "ds" in result.columns


# ---------------------------------------------------------------------------
# select_and_scale_features
# ---------------------------------------------------------------------------


def test_select_and_scale_renames_to_feature_n(raw_df):
    engineered = engineer_features(raw_df)
    feature_map = ["annual_sin", "annual_cos"]
    result = select_and_scale_features(engineered, feature_map)
    assert "feature_0" in result.columns
    assert "feature_1" in result.columns
    assert "ds" in result.columns


def test_select_and_scale_output_shape(raw_df):
    engineered = engineer_features(raw_df)
    feature_map = ["annual_sin", "annual_cos", "annual_phase"]
    result = select_and_scale_features(engineered, feature_map)
    assert result.shape[1] == 4  # ds + 3 features


def test_select_and_scale_raises_on_missing_feature(raw_df):
    engineered = engineer_features(raw_df)
    with pytest.raises(ValueError, match="nonexistent_col"):
        select_and_scale_features(engineered, ["annual_sin", "nonexistent_col"])
