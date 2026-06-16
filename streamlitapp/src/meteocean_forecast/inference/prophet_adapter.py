from __future__ import annotations

import warnings
from datetime import datetime, timedelta, timezone

import pandas as pd

from meteocean_forecast.domain.model_metadata import ModelMetadata


class ProphetAdapter:
    """Thin wrapper around a loaded ProphetRegressor that provides typed predict methods."""

    def __init__(self, wrapper, metadata: ModelMetadata) -> None:
        self._wrapper = wrapper
        self._metadata = metadata

    def predict_univariate(self, horizon_hours: int) -> pd.DataFrame:
        """
        Build a future hourly dataframe starting from the next full hour after now
        and return Prophet predictions for the next horizon_hours steps.
        """
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0, tzinfo=None)
        start = now + timedelta(hours=1)
        future = pd.DataFrame({"ds": pd.date_range(start=start, periods=horizon_hours, freq="h")})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self._wrapper.predict(future)

        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        result["target_variable"] = self._metadata.target_variable
        return result.reset_index(drop=True)

    def predict_exogenous(
        self, feature_df: pd.DataFrame, horizon_hours: int
    ) -> pd.DataFrame:
        """
        Run Prophet prediction using scaled exogenous feature columns.

        feature_df must have a 'ds' column and all columns listed in
        metadata.required_features (feature_0 … feature_N).
        """
        missing = [
            c for c in self._metadata.required_features if c not in feature_df.columns
        ]
        if missing:
            raise ValueError(
                f"feature_df is missing required columns for Prophet: {missing}"
            )

        input_df = feature_df[["ds", *self._metadata.required_features]].head(horizon_hours).copy()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = self._wrapper.predict(input_df)

        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        result["target_variable"] = self._metadata.target_variable
        return result.reset_index(drop=True)
