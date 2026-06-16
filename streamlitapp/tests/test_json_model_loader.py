"""Tests for JSON-based model loader functions."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from meteocean_forecast.inference.model_loader import load_metadata_json, load_model_metadata
from meteocean_forecast.config.model_registry import scan_models


def _write_metadata(directory: Path, use_exogenous: bool, regressors: list[str]) -> Path:
    meta = {"use_exogenous": use_exogenous, "regressors": regressors, "freq": "H"}
    meta_path = directory / "prophet_metadata.json"
    meta_path.write_text(json.dumps(meta))
    return meta_path


def _write_model_json(directory: Path) -> Path:
    model_path = directory / "prophet_model.json"
    model_path.write_text("{}")
    return model_path


# ---------------------------------------------------------------------------
# load_metadata_json
# ---------------------------------------------------------------------------


def test_load_metadata_json_reads_use_exogenous(tmp_path):
    _write_model_json(tmp_path)
    _write_metadata(tmp_path, use_exogenous=True, regressors=["feature_0", "feature_1"])

    result = load_metadata_json(tmp_path / "prophet_model.json")

    assert result["use_exogenous"] is True
    assert result["regressors"] == ["feature_0", "feature_1"]


# ---------------------------------------------------------------------------
# load_model_metadata
# ---------------------------------------------------------------------------


def test_load_model_metadata_exogenous(tmp_path):
    trial_dir = tmp_path / "current_speed" / "my_trial"
    trial_dir.mkdir(parents=True)
    _write_model_json(trial_dir)
    _write_metadata(trial_dir, use_exogenous=True, regressors=["feature_0", "feature_1"])

    meta = load_model_metadata(trial_dir / "prophet_model.json", "current_speed", {})

    assert meta.model_type == "exogenous"
    assert meta.required_features == ("feature_0", "feature_1")


def test_load_model_metadata_univariate(tmp_path):
    trial_dir = tmp_path / "wave_height" / "univariate_trial"
    trial_dir.mkdir(parents=True)
    _write_model_json(trial_dir)
    _write_metadata(trial_dir, use_exogenous=False, regressors=[])

    meta = load_model_metadata(trial_dir / "prophet_model.json", "wave_height", {})

    assert meta.model_type == "univariate"
    assert meta.required_features == ()


# ---------------------------------------------------------------------------
# scan_models
# ---------------------------------------------------------------------------


def test_scan_models_finds_json(tmp_path):
    trial_dir = tmp_path / "current_speed" / "my_trial"
    trial_dir.mkdir(parents=True)
    _write_model_json(trial_dir)
    _write_metadata(trial_dir, use_exogenous=False, regressors=[])

    with patch("meteocean_forecast.config.model_registry.load_model_metadata") as mock_load:
        from meteocean_forecast.domain.model_metadata import ModelMetadata

        mock_load.return_value = ModelMetadata(
            target_variable="current_speed",
            model_family="prophet",
            model_type="univariate",
            model_path=trial_dir / "prophet_model.json",
            required_features=(),
            feature_name_map=None,
            frequency="H",
            max_univariate_horizon_hours=8760,
            display_name="my_trial",
        )
        results = scan_models(tmp_path)

    assert len(results) == 1
    assert results[0].target_variable == "current_speed"
    assert results[0].display_name == "my_trial"


def test_scan_models_skips_malformed_metadata(tmp_path):
    trial_dir = tmp_path / "current_speed" / "bad_trial"
    trial_dir.mkdir(parents=True)
    _write_model_json(trial_dir)
    (trial_dir / "prophet_metadata.json").write_text("")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        results = scan_models(tmp_path)

    assert results == []
    assert any("bad_trial" in str(w.message) or "Skipping" in str(w.message) for w in caught)
