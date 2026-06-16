from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from meteocean_forecast.domain.forecast_request import ForecastRequest, HorizonValidationError
from meteocean_forecast.domain.model_metadata import ModelMetadata


def _make_meta(model_type: str = "univariate") -> ModelMetadata:
    return ModelMetadata(
        target_variable="current_speed",
        model_family="prophet",
        model_type=model_type,
        model_path=Path("/fake/path/prophet_best_model.pkl"),
        required_features=("feature_0", "feature_1") if model_type == "exogenous" else (),
        feature_name_map=None,
        frequency="H",
        max_univariate_horizon_hours=8760,
        display_name="test_model",
    )


def _make_feature_df(n_rows: int) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "ds": pd.date_range("2023-01-01", periods=n_rows, freq="h"),
            "feature_0": range(n_rows),
            "feature_1": range(n_rows),
        }
    )
    return df


# ---------------------------------------------------------------------------
# Univariate horizon validation
# ---------------------------------------------------------------------------


def test_univariate_at_limit_passes():
    meta = _make_meta("univariate")
    req = ForecastRequest.for_univariate(meta, 8760)
    assert req.horizon_hours == 8760


def test_univariate_exceeds_limit_raises():
    meta = _make_meta("univariate")
    with pytest.raises(HorizonValidationError, match="8760"):
        ForecastRequest.for_univariate(meta, 8761)


def test_univariate_zero_raises():
    meta = _make_meta("univariate")
    with pytest.raises(HorizonValidationError):
        ForecastRequest.for_univariate(meta, 0)


def test_univariate_negative_raises():
    meta = _make_meta("univariate")
    with pytest.raises(HorizonValidationError):
        ForecastRequest.for_univariate(meta, -1)


def test_univariate_error_message_contains_limit():
    meta = _make_meta("univariate")
    with pytest.raises(HorizonValidationError) as exc_info:
        ForecastRequest.for_univariate(meta, 9999)
    assert "8760" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Exogenous horizon validation
# ---------------------------------------------------------------------------


def test_exogenous_at_df_length_passes():
    meta = _make_meta("exogenous")
    df = _make_feature_df(100)
    req = ForecastRequest.for_exogenous(meta, df, 100)
    assert req.horizon_hours == 100


def test_exogenous_exceeds_df_length_raises():
    meta = _make_meta("exogenous")
    df = _make_feature_df(100)
    with pytest.raises(HorizonValidationError, match="100"):
        ForecastRequest.for_exogenous(meta, df, 101)


def test_exogenous_none_feature_df_raises():
    meta = _make_meta("exogenous")
    with pytest.raises(HorizonValidationError, match="None"):
        ForecastRequest.for_exogenous(meta, None, 24)


def test_exogenous_missing_required_columns_raises():
    meta = _make_meta("exogenous")
    df = _make_feature_df(50).drop(columns=["feature_0"])
    with pytest.raises(HorizonValidationError, match="feature_0"):
        ForecastRequest.for_exogenous(meta, df, 24)


def test_exogenous_zero_horizon_raises():
    meta = _make_meta("exogenous")
    df = _make_feature_df(50)
    with pytest.raises(HorizonValidationError):
        ForecastRequest.for_exogenous(meta, df, 0)
