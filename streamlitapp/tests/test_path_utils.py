"""Tests for path_utils: source mode vs. frozen PyInstaller bundle."""

from __future__ import annotations

from pathlib import Path

from meteocean_forecast import path_utils

_EXPECTED_SOURCE_BASE = Path(path_utils.__file__).resolve().parents[2]


def test_get_base_dir_source_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", False, raising=False)

    assert path_utils.get_base_dir() == _EXPECTED_SOURCE_BASE


def test_get_base_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_utils.sys, "executable", "/opt/MeteoceanForecast/MeteoceanForecast")

    assert path_utils.get_base_dir() == Path("/opt/MeteoceanForecast")


def test_get_models_dir_source_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", False, raising=False)

    assert path_utils.get_models_dir() == _EXPECTED_SOURCE_BASE / "models"


def test_get_models_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_utils.sys, "executable", "/opt/MeteoceanForecast/MeteoceanForecast")

    assert path_utils.get_models_dir() == Path("/opt/MeteoceanForecast/models")


def test_get_logs_dir_source_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", False, raising=False)

    assert path_utils.get_logs_dir() == _EXPECTED_SOURCE_BASE / "logs"


def test_get_logs_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_utils.sys, "executable", "/opt/MeteoceanForecast/MeteoceanForecast")

    assert path_utils.get_logs_dir() == Path("/opt/MeteoceanForecast/logs")


def test_get_streamlit_config_dir_source_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", False, raising=False)

    assert path_utils.get_streamlit_config_dir() == _EXPECTED_SOURCE_BASE / ".streamlit"


def test_get_streamlit_config_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_utils.sys, "executable", "/opt/MeteoceanForecast/MeteoceanForecast")

    assert path_utils.get_streamlit_config_dir() == Path("/opt/MeteoceanForecast/.streamlit")


def test_get_app_data_dir_source_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", False, raising=False)

    assert path_utils.get_app_data_dir() == _EXPECTED_SOURCE_BASE / "app_data"


def test_get_app_data_dir_frozen_mode(monkeypatch):
    monkeypatch.setattr(path_utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(path_utils.sys, "executable", "/opt/MeteoceanForecast/MeteoceanForecast")

    assert path_utils.get_app_data_dir() == Path("/opt/MeteoceanForecast/app_data")
