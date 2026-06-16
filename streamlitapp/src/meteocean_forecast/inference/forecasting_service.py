from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from meteocean_forecast.config.model_registry import scan_models
from meteocean_forecast.domain.forecast_request import ForecastRequest
from meteocean_forecast.domain.model_metadata import ModelMetadata
from meteocean_forecast.features.feature_engineering import engineer_features, select_and_scale_features
from meteocean_forecast.inference.model_loader import load_prophet_from_json
from meteocean_forecast.inference.prophet_adapter import ProphetAdapter


class ForecastingService:
    """
    Orchestrates model discovery, loading, and inference.

    Instantiate once per app session (use @st.cache_resource in Streamlit).
    """

    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir
        self._all_metadata: list[ModelMetadata] = scan_models(models_dir)
        self._adapters: dict[Path, ProphetAdapter] = {}

        for i, meta in enumerate(self._all_metadata):
            wrapper = load_prophet_from_json(meta.model_path)
            cutoff = wrapper.history_dates.max().to_pydatetime()
            meta = replace(meta, training_cutoff=cutoff)
            self._all_metadata[i] = meta
            self._adapters[meta.model_path] = ProphetAdapter(wrapper, meta)

    @property
    def all_metadata(self) -> list[ModelMetadata]:
        return list(self._all_metadata)

    def get_models_for_target(self, target_variable: str) -> list[ModelMetadata]:
        return [m for m in self._all_metadata if m.target_variable == target_variable]

    def forecast(self, request: ForecastRequest) -> pd.DataFrame:
        adapter = self._adapters[request.metadata.model_path]
        if request.metadata.is_exogenous:
            assert request.feature_df is not None  # validated by ForecastRequest
            return adapter.predict_exogenous(request.feature_df, request.horizon_hours)
        return adapter.predict_univariate(request.horizon_hours)

    def prepare_exogenous_features(
        self, raw_df: pd.DataFrame, metadata: ModelMetadata
    ) -> pd.DataFrame:
        """
        Run the full feature engineering pipeline on raw XLSX data and scale the
        result to the columns expected by the Prophet model (feature_0 … feature_N).
        """
        if metadata.feature_name_map is None:
            raise ValueError(
                f"No feature_name_map defined for model '{metadata.display_name}'. "
                "Add it to FEATURE_NAME_MAPS in config/model_registry.py."
            )
        engineered = engineer_features(raw_df)
        return select_and_scale_features(engineered, list(metadata.feature_name_map))
