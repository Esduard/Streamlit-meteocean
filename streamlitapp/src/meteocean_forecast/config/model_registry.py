"""
Model registry: discovers and catalogues Prophet JSON files under streamlitapp/models/.

Directory convention:
    models/<target_variable>/<trial_name>/prophet_model.json

FEATURE_NAME_MAPS maps each trial directory name to the ordered list of human-readable
feature names that correspond to feature_0, feature_1, … in the Prophet model.
This list is the single source of truth for the feature position mapping.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

from meteocean_forecast.domain.model_metadata import ModelMetadata
from meteocean_forecast.inference.model_loader import load_model_metadata

logger = logging.getLogger(__name__)

# Map from model trial directory name → ordered human-readable feature names.
# feature_0 = names[0], feature_1 = names[1], …
FEATURE_NAME_MAPS: dict[str, list[str]] = {
    "prophet_multiplicative_exogenous_trials": [
        "wav_hmax",
        "wav_tp",
        "wav_tmm10",
        "wav_dm",
        "wav_ww_dm",
        "wav_pk1_tmm10",
        "wav_pk2_tmm10",
        "atm_wnd_dir_10m_u",
        "wav_dm_u",
        "wav_pk1_dm_u",
        "wav_pk2_dm_v",
        "wind_current_alignment",
        "annual_sin",
        "annual_cos",
        "annual_phase",
        "is_summer",
        "is_autumn",
        "is_winter",
        "is_spring",
        "wind_align_NBC",
        "wave_align_NBC",
        "wind_prob_NBC",
        "wind_prob_SEC",
        "wind_prob_EUC",
        "wave_prob_NBC",
        "current_prob_NBC",
        "current_prob_SEC",
        "current_prob_EUC",
        "sw_cur_spd_fourier",
    ],
}


def scan_models(models_dir: Path) -> list[ModelMetadata]:
    """
    Walk models_dir looking for prophet_model.json files.

    Expected layout:
        models_dir/<target_variable>/<trial_name>/prophet_model.json

    Returns a list of ModelMetadata sorted by (target_variable, display_name).
    Skips any model that fails to load (logs a warning instead of raising).
    """
    results: list[ModelMetadata] = []

    for json_path in sorted(models_dir.glob("*/*/prophet_model.json")):
        target_variable = json_path.parents[1].name
        try:
            metadata = load_model_metadata(json_path, target_variable, FEATURE_NAME_MAPS)
            results.append(metadata)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"Failed to load model at {json_path}: {exc}. Skipping.",
                stacklevel=2,
            )
            logger.warning("Failed to load model at %s: %s", json_path, exc, exc_info=True)

    return sorted(results, key=lambda m: (m.target_variable, m.display_name))
