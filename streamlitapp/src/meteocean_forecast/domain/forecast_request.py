from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from meteocean_forecast.domain.model_metadata import ModelMetadata


class HorizonValidationError(ValueError):
    pass


@dataclass
class ForecastRequest:
    metadata: ModelMetadata
    horizon_hours: int
    feature_df: pd.DataFrame | None  # None for univariate; scaled feature df for exogenous

    @classmethod
    def for_univariate(cls, metadata: ModelMetadata, horizon_hours: int) -> "ForecastRequest":
        limit = metadata.max_univariate_horizon_hours
        if not (1 <= horizon_hours <= limit):
            raise HorizonValidationError(
                f"Univariate horizon must be between 1 and {limit} hours; got {horizon_hours}."
            )
        return cls(metadata=metadata, horizon_hours=horizon_hours, feature_df=None)

    @classmethod
    def for_exogenous(
        cls,
        metadata: ModelMetadata,
        feature_df: pd.DataFrame | None,
        horizon_hours: int,
    ) -> "ForecastRequest":
        if feature_df is None:
            raise HorizonValidationError(
                "Exogenous model requires a feature DataFrame; received None."
            )
        limit = len(feature_df)
        if not (1 <= horizon_hours <= limit):
            raise HorizonValidationError(
                f"Exogenous horizon must be between 1 and {limit} (available rows); got {horizon_hours}."
            )
        missing = [c for c in metadata.required_features if c not in feature_df.columns]
        if missing:
            raise HorizonValidationError(
                f"Feature DataFrame is missing required columns: {missing}"
            )
        return cls(metadata=metadata, horizon_hours=horizon_hours, feature_df=feature_df)
