"""
Tests for ProphetAdapter and ForecastingService — fully mocked, no pkl needed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from meteocean_forecast.domain.forecast_request import ForecastRequest
from meteocean_forecast.domain.model_metadata import ModelMetadata
from meteocean_forecast.inference.prophet_adapter import ProphetAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meta(model_type: str = "univariate") -> ModelMetadata:
    required = ("feature_0", "feature_1") if model_type == "exogenous" else ()
    return ModelMetadata(
        target_variable="current_speed",
        model_family="prophet",
        model_type=model_type,
        model_path=Path("/fake/prophet_model.json"),
        required_features=required,
        feature_name_map=None,
        frequency="H",
        max_univariate_horizon_hours=8760,
        display_name="test_model",
    )


def _make_prophet_forecast(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ds": pd.date_range("2023-01-01", periods=n, freq="h"),
            "yhat": [1.0] * n,
            "yhat_lower": [0.8] * n,
            "yhat_upper": [1.2] * n,
            "trend": [1.0] * n,
        }
    )


def _make_wrapper(model_type: str = "univariate"):
    wrapper = MagicMock()
    n = 24
    forecast_df = _make_prophet_forecast(n)

    wrapper.make_future_dataframe.return_value = pd.DataFrame(
        {"ds": pd.date_range("2023-01-01", periods=n, freq="h")}
    )
    wrapper.predict.return_value = forecast_df
    return wrapper


# ---------------------------------------------------------------------------
# ProphetAdapter — univariate
# ---------------------------------------------------------------------------


def test_univariate_output_has_correct_columns():
    meta = _make_meta("univariate")
    wrapper = _make_wrapper("univariate")
    adapter = ProphetAdapter(wrapper, meta)

    result = adapter.predict_univariate(24)
    assert set(result.columns) == {"ds", "yhat", "yhat_lower", "yhat_upper", "target_variable"}


def test_univariate_returns_n_rows():
    meta = _make_meta("univariate")
    wrapper = _make_wrapper("univariate")
    adapter = ProphetAdapter(wrapper, meta)

    result = adapter.predict_univariate(24)
    assert len(result) == 24


def test_univariate_target_variable_column():
    meta = _make_meta("univariate")
    wrapper = _make_wrapper("univariate")
    adapter = ProphetAdapter(wrapper, meta)

    result = adapter.predict_univariate(5)
    assert (result["target_variable"] == "current_speed").all()


# ---------------------------------------------------------------------------
# ProphetAdapter — exogenous
# ---------------------------------------------------------------------------


def _make_feature_df(n_rows: int = 50) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ds": pd.date_range("2023-01-01", periods=n_rows, freq="h"),
            "feature_0": range(n_rows),
            "feature_1": range(n_rows),
        }
    )


def test_exogenous_output_has_correct_columns():
    meta = _make_meta("exogenous")
    wrapper = _make_wrapper("exogenous")
    adapter = ProphetAdapter(wrapper, meta)

    result = adapter.predict_exogenous(_make_feature_df(), 24)
    assert set(result.columns) == {"ds", "yhat", "yhat_lower", "yhat_upper", "target_variable"}


def test_exogenous_validates_missing_columns():
    meta = _make_meta("exogenous")
    wrapper = _make_wrapper("exogenous")
    adapter = ProphetAdapter(wrapper, meta)

    df_missing = _make_feature_df().drop(columns=["feature_0"])
    with pytest.raises(ValueError, match="feature_0"):
        adapter.predict_exogenous(df_missing, 10)


def test_exogenous_passes_only_required_columns_to_prophet():
    """Prophet predict() must receive only ['ds', 'feature_0', 'feature_1']."""
    meta = _make_meta("exogenous")
    wrapper = _make_wrapper("exogenous")
    adapter = ProphetAdapter(wrapper, meta)

    df = _make_feature_df()
    df["extra_col"] = 99  # should be stripped

    adapter.predict_exogenous(df, 24)

    call_args = wrapper.predict.call_args[0][0]
    assert "extra_col" not in call_args.columns
    assert "ds" in call_args.columns
    assert "feature_0" in call_args.columns


# ---------------------------------------------------------------------------
# ForecastingService routing (mocked at service level)
# ---------------------------------------------------------------------------


def test_service_routes_univariate(tmp_path):
    """ForecastingService.forecast routes to predict_univariate for univariate requests."""
    meta = _make_meta("univariate")
    wrapper = _make_wrapper("univariate")

    with (
        patch("meteocean_forecast.inference.forecasting_service.scan_models", return_value=[meta]),
        patch("meteocean_forecast.inference.forecasting_service.load_prophet_from_json", return_value=wrapper),
    ):
        from meteocean_forecast.inference.forecasting_service import ForecastingService

        service = ForecastingService(tmp_path)
        request = ForecastRequest.for_univariate(meta, 24)
        result = service.forecast(request)

    assert "yhat" in result.columns
    wrapper.predict.assert_called_once()
    wrapper.make_future_dataframe.assert_not_called()


def test_service_routes_exogenous(tmp_path):
    """ForecastingService.forecast routes to predict_exogenous for exogenous requests."""
    meta = _make_meta("exogenous")
    wrapper = _make_wrapper("exogenous")
    feature_df = _make_feature_df(50)

    with (
        patch("meteocean_forecast.inference.forecasting_service.scan_models", return_value=[meta]),
        patch("meteocean_forecast.inference.forecasting_service.load_prophet_from_json", return_value=wrapper),
    ):
        from meteocean_forecast.inference.forecasting_service import ForecastingService

        service = ForecastingService(tmp_path)
        request = ForecastRequest.for_exogenous(meta, feature_df, 24)
        result = service.forecast(request)

    assert "yhat" in result.columns
    wrapper.predict.assert_called_once()
