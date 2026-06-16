"""Load Prophet models from JSON files using prophet.serialize."""

from __future__ import annotations

import json
from pathlib import Path

from meteocean_forecast.domain.model_metadata import ModelMetadata


def load_prophet_from_json(json_path: Path):
    """Load a Prophet model from a JSON file using prophet.serialize.model_from_json."""
    from prophet.serialize import model_from_json

    with open(json_path) as f:
        return model_from_json(f.read())


def load_metadata_json(json_path: Path) -> dict:
    """Read prophet_metadata.json sitting next to prophet_model.json."""
    meta_path = json_path.parent / "prophet_metadata.json"
    with open(meta_path) as f:
        return json.load(f)


def load_model_metadata(
    json_path: Path,
    target_variable: str,
    feature_name_maps: dict[str, list[str]],
) -> ModelMetadata:
    meta = load_metadata_json(json_path)
    model_type = "exogenous" if meta.get("use_exogenous") else "univariate"
    required_features = tuple(meta.get("regressors", []))

    dir_name = json_path.parent.name
    raw_map = feature_name_maps.get(dir_name)
    feature_name_map = tuple(raw_map) if raw_map is not None else None

    return ModelMetadata(
        target_variable=target_variable,
        model_family="prophet",
        model_type=model_type,
        model_path=json_path,
        required_features=required_features,
        feature_name_map=feature_name_map,
        frequency=meta.get("freq", "H"),
        max_univariate_horizon_hours=8760,
        display_name=dir_name,
    )
